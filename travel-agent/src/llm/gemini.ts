import { GoogleGenerativeAI, FunctionCallingMode } from '@google/generative-ai';
import type { FunctionDeclaration, Tool as GeminiTool } from '@google/generative-ai';
import { LLMClient, LLMResponse, Message, ToolDefinition, ToolCall } from './types.js';

const GEMINI_API_KEY = process.env['GEMINI_API_KEY'] ?? process.env['GOOGLE_API_KEY'] ?? '';

const MODEL_CONTEXT: Record<string, number> = {
  'gemini-2.5-flash': 1048576,
  'gemini-2.5-pro': 1048576,
  'gemini-2.0-flash': 1048576,
  'gemini-1.5-flash': 1048576,
  'gemini-1.5-pro': 2097152,
};

export class GeminiClient implements LLMClient {
  readonly providerName = 'gemini';
  readonly modelName: string;
  readonly contextWindow: number;

  private genAI: GoogleGenerativeAI;

  constructor(model: string) {
    this.modelName = model;
    this.contextWindow = MODEL_CONTEXT[model] ?? 1048576;
    this.genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
  }

  async chat(messages: Message[], tools: ToolDefinition[]): Promise<LLMResponse> {
    const systemMessages = messages.filter(m => m.role === 'system');
    const conversationMessages = messages.filter(m => m.role !== 'system');

    const systemInstruction = systemMessages
      .map(m => (typeof m.content === 'string' ? m.content : ''))
      .join('\n\n');

    const geminiTools: GeminiTool[] = tools.length > 0
      ? [{
          functionDeclarations: tools.map(t => ({
            name: t.name,
            description: t.description,
            parameters: t.input_schema as FunctionDeclaration['parameters'],
          })),
        }]
      : [];

    const modelConfig: Record<string, unknown> = {
      model: this.modelName,
    };
    if (systemInstruction) modelConfig['systemInstruction'] = systemInstruction;
    if (geminiTools.length > 0) {
      modelConfig['tools'] = geminiTools;
      modelConfig['toolConfig'] = { functionCallingConfig: { mode: FunctionCallingMode.AUTO } };
    }

    const model = this.genAI.getGenerativeModel(modelConfig as unknown as Parameters<typeof this.genAI.getGenerativeModel>[0]);

    // Convert messages to Gemini history format
    const { history, lastUserMsg } = this.convertMessages(conversationMessages);

    const chat = model.startChat({ history });
    const result = await chat.sendMessage(lastUserMsg);
    const response = result.response;

    const toolCalls: ToolCall[] = [];
    let content = '';

    for (const part of response.candidates?.[0]?.content?.parts ?? []) {
      if (part.text) {
        content += part.text;
      } else if (part.functionCall) {
        toolCalls.push({
          id: `gemini_${part.functionCall.name}_${Date.now()}`,
          name: part.functionCall.name,
          arguments: (part.functionCall.args ?? {}) as Record<string, unknown>,
        });
      }
    }

    const usage = response.usageMetadata;
    return {
      content,
      toolCalls,
      usage: {
        promptTokens: usage?.promptTokenCount ?? 0,
        completionTokens: usage?.candidatesTokenCount ?? 0,
        totalTokens: usage?.totalTokenCount ?? 0,
      },
    };
  }

  private convertMessages(messages: Message[]): {
    history: Array<{ role: string; parts: Array<{ text: string }> }>;
    lastUserMsg: string;
  } {
    // Gemini requires history to end before the last user message
    // We send all but the last user message as history, then the last as sendMessage
    const filtered = messages.filter(m => m.role === 'user' || m.role === 'assistant');

    if (filtered.length === 0) {
      return { history: [], lastUserMsg: '' };
    }

    const last = filtered[filtered.length - 1];
    const lastUserMsg = typeof last?.content === 'string' ? last.content : '';

    const history = filtered.slice(0, -1).map(m => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: typeof m.content === 'string' ? m.content : JSON.stringify(m.content) }],
    }));

    return { history, lastUserMsg };
  }
}
