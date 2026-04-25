import React from 'react';
import { Box, Text } from 'ink';

interface HeaderProps {
  model: string;
}

// Claude Code's exact brand color: rgb(215, 119, 87)
const CLAUDE_COLOR = '#d77757';

export function Header({ model }: HeaderProps) {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box justifyContent="space-between">
        <Text color={CLAUDE_COLOR} bold>{'✻ claude-code-travel-agent'}</Text>
        <Text color="#666666">{model}</Text>
      </Box>
    </Box>
  );
}
