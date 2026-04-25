import React from 'react';
import { Box, Text } from 'ink';

interface StatusBarProps {
  mode: string;
  tripId: string;
  model: string;
  tokens: number;
}

const SUBTLE_COLOR = '#505050';

export function StatusBar({ mode, tripId, model, tokens }: StatusBarProps) {
  const tokenStr = tokens > 0 ? ` · ${tokens} tokens` : '';
  return (
    <Box paddingX={1} marginTop={0}>
      <Text color={SUBTLE_COLOR} dimColor>
        {`${mode} · ${tripId} · ${model}${tokenStr}`}
        {'  '}
        <Text color={SUBTLE_COLOR} dimColor>ctrl+c to exit</Text>
      </Text>
    </Box>
  );
}
