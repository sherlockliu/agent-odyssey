import { Anthropic } from '@anthropic-ai/sdk';
import { LLMClient, LLMResponse, Message, ToolDefinition, ToolCall } from './types.js';
import { ANTHROPIC_API_KEY } from '../config.js';

// SDK types accessed via Anthropic namespace
type MessageParam = Anthropic.Messages.MessageParam;
type ContentBlock = Anthropic.Messages.ContentBlock;

export class AnthropicClient implements LLMClient {
  readonly providerName = 'anthropic';
  readonly modelName: string;
  readonly contextWindow = 200000;

  private client: Anthropic;

  constructor(model: string) {
    this.modelName = model;
    this.client = new Anthropic({ apiKey: ANTHROPIC_API_KEY });
  }

  async chat(messages: Message[], tools: ToolDefinition[]): Promise<LLMResponse> {
    const systemMessages = messages.filter(m => m.role === 'system');
    const conversationMessages = messages.filter(m => m.role !== 'system');

    const systemText = systemMessages
      .map(m => (typeof m.content === 'string' ? m.content : ''))
      .join('\n\n');

    const anthropicMessages = this.convertMessages(conversationMessages);

    const createParams: Anthropic.Messages.MessageCreateParamsNonStreaming = {
      model: this.modelName,
      max_tokens: 4096,
      messages: anthropicMessages,
    };

    if (systemText) createParams.system = systemText;
    if (tools.length > 0) {
      createParams.tools = tools.map(t => ({
        name: t.name,
        description: t.description,
        input_schema: t.input_schema as { type: 'object'; properties: Record<string, unknown> },
      }));
    }

    const response = await this.client.messages.create(createParams);

    const toolCalls: ToolCall[] = [];
    let content = '';

    for (const block of response.content) {
      if (block.type === 'text') {
        content += block.text;
      } else if (block.type === 'tool_use') {
        toolCalls.push({
          id: block.id,
          name: block.name,
          arguments: block.input as Record<string, unknown>,
        });
      }
    }

    return {
      content,
      toolCalls,
      usage: {
        promptTokens: response.usage.input_tokens,
        completionTokens: response.usage.output_tokens,
        totalTokens: response.usage.input_tokens + response.usage.output_tokens,
      },
    };
  }

  private convertMessages(messages: Message[]): MessageParam[] {
    const result: MessageParam[] = [];

    for (const msg of messages) {
      if (msg.role === 'user') {
        if (msg.tool_call_id) {
          result.push({
            role: 'user',
            content: [{
              type: 'tool_result',
              tool_use_id: msg.tool_call_id,
              content: typeof msg.content === 'string' ? msg.content : '',
            }],
          });
        } else {
          result.push({
            role: 'user',
            content: typeof msg.content === 'string' ? msg.content : '',
          });
        }
      } else if (msg.role === 'assistant') {
        if (Array.isArray(msg.content)) {
          result.push({
            role: 'assistant',
            content: msg.content as ContentBlock[],
          });
        } else {
          result.push({
            role: 'assistant',
            content: msg.content as string,
          });
        }
      }
    }

    return result;
  }
}
