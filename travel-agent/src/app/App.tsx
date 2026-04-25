import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, useApp } from 'ink';
import { Header } from '../components/Header.js';
import { MessageList } from '../components/MessageList.js';
import { ThinkingBar } from '../components/ThinkingBar.js';
import { ComposerInput } from '../components/ComposerInput.js';
import { StatusBar } from '../components/StatusBar.js';
import { ChatMessage } from '../components/Message.js';
import { runAgentLoop } from '../agent/loop.js';
import { createClient } from '../llm/index.js';
import { ToolRegistry } from '../tools/registry.js';
import { BuiltinProvider } from '../tools/providers/builtin.js';
import { WeatherProvider } from '../tools/providers/weather.js';
import { ActivitiesProvider } from '../tools/providers/activities.js';
import { TripContext } from '../memory/tripContext.js';
import { UserProfile } from '../memory/userProfile.js';
import { LLM_MODEL, LLM_PROVIDER, DEFAULT_MODE } from '../config.js';

let messageCounter = 0;
function makeId() {
  return `msg_${++messageCounter}_${Date.now()}`;
}

export function App() {
  const { exit } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [tokens, setTokens] = useState(0);
  const [mode] = useState(DEFAULT_MODE);
  const [thinkingLabel, setThinkingLabel] = useState('Thinking…');

  // Refs for stable access in async handlers
  const tripCtxRef = useRef<TripContext | null>(null);
  const profileRef = useRef<UserProfile | null>(null);
  const registryRef = useRef<ToolRegistry | null>(null);
  const llmRef = useRef<ReturnType<typeof createClient> | null>(null);
  const tripIdRef = useRef<string>('initializing…');
  const [tripId, setTripId] = useState('initializing…');
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    async function init() {
      try {
        const profile = new UserProfile();
        await profile.load();
        profileRef.current = profile;

        const tripCtx = new TripContext();
        await tripCtx.load();
        tripCtxRef.current = tripCtx;
        tripIdRef.current = tripCtx.tripId;
        setTripId(tripCtx.tripId);

        const registry = new ToolRegistry();
        registry.register(new BuiltinProvider(tripCtx));
        registry.register(new WeatherProvider());
        registry.register(new ActivitiesProvider());
        registryRef.current = registry;

        llmRef.current = createClient(LLM_PROVIDER, LLM_MODEL);

        setInitialized(true);

        setMessages([{
          id: makeId(),
          role: 'assistant',
          content: `Welcome! I'm your travel planning assistant. Tell me where you'd like to go and I'll help you plan the perfect trip.\n\nTry: "Plan a weekend trip to Tokyo for 2 people, $3000 budget"`,
        }]);
      } catch (err) {
        setMessages([{
          id: makeId(),
          role: 'assistant',
          content: `Error initializing: ${err instanceof Error ? err.message : String(err)}\n\nMake sure ANTHROPIC_API_KEY is set in your .env file.`,
        }]);
        setInitialized(true);
      }
    }
    init();
  }, []);

  const handleSubmit = useCallback(async (input: string) => {
    if (!initialized || isThinking) return;

    const tripCtx = tripCtxRef.current;
    const profile = profileRef.current;
    const registry = registryRef.current;
    const llm = llmRef.current;

    if (!tripCtx || !profile || !registry || !llm) return;

    setIsThinking(true);
    setMessages(prev => [...prev, { id: makeId(), role: 'user', content: input }]);

    try {
      for await (const event of runAgentLoop(input, tripCtx, profile, registry, llm, mode)) {
        if (event.type === 'thinking') {
          setThinkingLabel('Thinking…');
        } else if (event.type === 'tool_call') {
          setThinkingLabel(`Calling ${event.name}…`);
          setMessages(prev => [...prev, {
            id: makeId(),
            role: 'tool_call',
            content: '',
            toolName: event.name,
            args: event.args,
          }]);
        } else if (event.type === 'tool_result') {
          setMessages(prev => [...prev, {
            id: makeId(),
            role: 'tool_result',
            content: event.result,
          }]);
          setThinkingLabel('Thinking…');
        } else if (event.type === 'assistant_message') {
          setMessages(prev => [...prev, {
            id: makeId(),
            role: 'assistant',
            content: event.content,
          }]);
          if (event.tokens) setTokens(prev => prev + event.tokens!);
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: makeId(),
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : String(err)}`,
      }]);
    } finally {
      setIsThinking(false);
    }
  }, [initialized, isThinking, mode]);

  return (
    <Box flexDirection="column">
      <Header model={LLM_MODEL} />
      <MessageList messages={messages} />
      {isThinking && <ThinkingBar label={thinkingLabel} />}
      <ComposerInput onSubmit={handleSubmit} disabled={isThinking || !initialized} />
      <StatusBar mode={mode} tripId={tripId} model={LLM_MODEL} tokens={tokens} />
    </Box>
  );
}
