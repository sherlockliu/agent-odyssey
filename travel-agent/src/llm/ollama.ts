import { LLMClient, LLMResponse, Message, ToolDefinition } from './types.js';
import { OLLAMA_HOST } from '../config.js';

export class OllamaClient implements LLMClient {
  readonly providerName = 'ollama';
  readonly modelName: string;
  readonly contextWindow = 8192;

  constructor(model: string) {
    this.modelName = model;
  }

  async chat(messages: Message[], tools: ToolDefinition[]): Promise<LLMResponse> {
    const systemMessages = messages.filter(m => m.role === 'system');
    const conversationMessages = messages.filter(m => m.role !== 'system');

    const ollamaMessages = conversationMessages.map(m => ({
      role: m.role === 'tool' ? 'user' : m.role,
      content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content),
    }));

    if (systemMessages.length > 0) {
      ollamaMessages.unshift({
        role: 'system',
        content: systemMessages.map(m => (typeof m.content === 'string' ? m.content : '')).join('\n\n'),
      });
    }

    const body: Record<string, unknown> = {
      model: this.modelName,
      messages: ollamaMessages,
      stream: false,
    };

    if (tools.length > 0) {
      body['tools'] = tools.map(t => ({
        type: 'function',
        function: {
          name: t.name,
          description: t.description,
          parameters: t.input_schema,
        },
      }));
    }

    const resp = await fetch(`${OLLAMA_HOST}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) throw new Error(`Ollama error: ${resp.statusText}`);
    const data = await resp.json() as {
      message: { content: string; tool_calls?: Array<{ function: { name: string; arguments: Record<string, unknown> } }> };
      prompt_eval_count?: number;
      eval_count?: number;
    };

    const toolCalls = (data.message.tool_calls ?? []).map((tc, i) => ({
      id: `ollama_${i}_${Date.now()}`,
      name: tc.function.name,
      arguments: tc.function.arguments,
    }));

    const promptTokens = data.prompt_eval_count ?? 0;
    const completionTokens = data.eval_count ?? 0;

    return {
      content: data.message.content ?? '',
      toolCalls,
      usage: { promptTokens, completionTokens, totalTokens: promptTokens + completionTokens },
    };
  }
}
