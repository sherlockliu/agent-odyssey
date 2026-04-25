import React from 'react';
import { Box, Text } from 'ink';
import Spinner from 'ink-spinner';

interface ThinkingBarProps {
  label?: string;
}

const CLAUDE_COLOR = '#d77757';

export function ThinkingBar({ label = 'Thinking…' }: ThinkingBarProps) {
  return (
    <Box paddingLeft={2} marginBottom={1}>
      <Text color={CLAUDE_COLOR}>
        <Spinner type="dots" />
      </Text>
      <Text color={CLAUDE_COLOR} dimColor>{' ' + label}</Text>
    </Box>
  );
}
