import React from 'react';
import { Box, Text } from 'ink';
import { MarkdownText } from './MarkdownText.js';

export type MessageRole = 'user' | 'assistant' | 'tool_call' | 'tool_result';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  toolName?: string;
  args?: Record<string, unknown>;
}

interface MessageProps {
  message: ChatMessage;
}

const CLAUDE_COLOR = '#d77757';
const SUBTLE_COLOR = '#666666';
const DIM_COLOR = '#505050';

export function Message({ message }: MessageProps) {
  if (message.role === 'user') {
    return (
      <Box marginBottom={1}>
        <Text bold color={CLAUDE_COLOR}>{'❯ '}</Text>
        <Text bold color="white">{message.content}</Text>
      </Box>
    );
  }

  if (message.role === 'assistant') {
    return (
      <Box marginBottom={1} flexDirection="column" paddingLeft={2}>
        <MarkdownText>{message.content}</MarkdownText>
      </Box>
    );
  }

  if (message.role === 'tool_call') {
    const argsStr = message.args
      ? Object.entries(message.args)
          .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
          .join(', ')
      : '';
    const preview = argsStr.length > 60 ? argsStr.slice(0, 57) + '…' : argsStr;
    return (
      <Box>
        <Text color={CLAUDE_COLOR} dimColor>{'  ⏺ '}</Text>
        <Text color={SUBTLE_COLOR}>{message.toolName}</Text>
        {preview ? <Text color={DIM_COLOR}>{'(' + preview + ')'}</Text> : null}
      </Box>
    );
  }

  if (message.role === 'tool_result') {
    const preview = message.content.length > 100
      ? message.content.slice(0, 97) + '…'
      : message.content;
    return (
      <Box marginBottom={1} paddingLeft={5}>
        <Text dimColor color={DIM_COLOR}>{preview}</Text>
      </Box>
    );
  }

  return null;
}
