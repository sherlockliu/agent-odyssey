import { LLMClient, Message } from '../llm/types.js';
import { ToolRegistry } from '../tools/registry.js';
import { TripContext } from '../memory/tripContext.js';
import { UserProfile } from '../memory/userProfile.js';
import { AgentMode, MODES } from '../config.js';
import { detectInjection } from '../safety/injectionFilter.js';

export type AgentEvent =
  | { type: 'thinking' }
  | { type: 'tool_call'; name: string; args: Record<string, unknown> }
  | { type: 'tool_result'; result: string }
  | { type: 'assistant_message'; content: string; tokens?: number };

function buildSystemPrompt(
  tripContext: TripContext,
  userProfile: UserProfile,
  mode: AgentMode,
): string {
  const modeInstruction = MODES[mode];

  const basePrompt = `You are an expert travel planning assistant. You help users plan trips by searching for destinations, flights, hotels, and activities.

MODE: ${mode.toUpperCase()}
${modeInstruction}

CAPABILITIES:
- Search destinations, flights, hotels, and activities
- Build and update trip itineraries
- Track user preferences and travel history
- Provide weather information
- Export itineraries to markdown

Always be helpful, specific, and proactive about the user's needs.`;

  const contextMsg = tripContext.asContextMessage();
  const profileMsg = userProfile.asContextMessage();

  const parts = [basePrompt];
  if (contextMsg) parts.push('\nCURRENT TRIP CONTEXT:\n' + contextMsg);
  if (profileMsg) parts.push('\nUSER PROFILE:\n' + profileMsg);

  return parts.join('\n\n');
}

function toolResultMessage(toolUseId: string, result: string): Message {
  return {
    role: 'user',
    content: result,
    tool_call_id: toolUseId,
  };
}

export async function* runAgentLoop(
  userMessage: string,
  tripContext: TripContext,
  userProfile: UserProfile,
  registry: ToolRegistry,
  llmClient: LLMClient,
  mode: AgentMode,
): AsyncGenerator<AgentEvent> {
  const systemPrompt = buildSystemPrompt(tripContext, userProfile, mode);

  // Build messages: system + conversation history + new user message
  const history = tripContext.getConversationHistory();
  const messages: Message[] = [
    { role: 'system', content: systemPrompt },
    ...history,
    { role: 'user', content: userMessage },
  ];

  let totalTokens = 0;

  // ReAct loop
  while (true) {
    yield { type: 'thinking' };

    const response = await llmClient.chat(messages, registry.getDefinitions());
    totalTokens += response.usage.totalTokens;

    if (response.toolCalls.length === 0) {
      // Final text response — done
      yield {
        type: 'assistant_message',
        content: response.content,
        tokens: totalTokens,
      };
      // Append to messages for history persistence
      messages.push({ role: 'assistant', content: response.content });
      break;
    }

    // Build assistant content blocks for Anthropic format
    const assistantContentBlocks = [];
    if (response.content) {
      assistantContentBlocks.push({ type: 'text' as const, text: response.content });
    }
    for (const tc of response.toolCalls) {
      assistantContentBlocks.push({
        type: 'tool_use' as const,
        id: tc.id,
        name: tc.name,
        input: tc.arguments,
      });
    }
    messages.push({ role: 'assistant', content: assistantContentBlocks });

    // Execute each tool call
    for (const toolCall of response.toolCalls) {
      yield { type: 'tool_call', name: toolCall.name, args: toolCall.arguments };

      // Safety check
      if (detectInjection(JSON.stringify(toolCall.arguments))) {
        const blocked = '[BLOCKED: prompt injection detected in tool arguments]';
        yield { type: 'tool_result', result: blocked };
        messages.push(toolResultMessage(toolCall.id, blocked));
        continue;
      }

      let result: string;
      try {
        result = await registry.dispatch(toolCall.name, toolCall.arguments);
      } catch (err) {
        result = `Tool error: ${err instanceof Error ? err.message : String(err)}`;
      }

      yield { type: 'tool_result', result };
      messages.push(toolResultMessage(toolCall.id, result));
    }
  }

  // Persist conversation history
  tripContext.updateHistory(messages);
  await tripContext.save();
}
