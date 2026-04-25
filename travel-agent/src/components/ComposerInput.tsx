import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';

interface ComposerInputProps {
  onSubmit: (value: string) => void;
  disabled: boolean;
  placeholder?: string;
}

const CLAUDE_COLOR = '#d77757';
const INACTIVE_COLOR = '#505050';

export function ComposerInput({ onSubmit, disabled, placeholder = 'Type a message…' }: ComposerInputProps) {
  const [value, setValue] = useState('');
  const [cursorVisible, setCursorVisible] = useState(true);

  // Blinking cursor at 530ms interval (matches most terminal cursors)
  useEffect(() => {
    if (disabled) return;
    const id = setInterval(() => setCursorVisible(v => !v), 530);
    return () => clearInterval(id);
  }, [disabled]);

  useInput((input, key) => {
    if (disabled) return;

    if (key.return) {
      if (value.trim()) {
        onSubmit(value.trim());
        setValue('');
      }
      return;
    }

    if (key.backspace || key.delete) {
      setValue(prev => prev.slice(0, -1));
      return;
    }

    if (key.escape) {
      setValue('');
      return;
    }

    if (!key.ctrl && !key.meta && input) {
      setValue(prev => prev + input);
    }
  });

  const showPlaceholder = !value && !disabled;
  const borderColor = disabled ? INACTIVE_COLOR : CLAUDE_COLOR;
  // Show cursor block: visible when cursorVisible, invisible (space) otherwise
  const cursor = disabled ? '' : (cursorVisible ? '█' : ' ');

  return (
    <Box borderStyle="round" borderColor={borderColor} paddingX={1} marginTop={1}>
      <Text bold color={disabled ? INACTIVE_COLOR : CLAUDE_COLOR}>{'❯ '}</Text>
      {showPlaceholder
        ? <>
            <Text color={INACTIVE_COLOR} dimColor>{placeholder}</Text>
            <Text color={CLAUDE_COLOR}>{cursor}</Text>
          </>
        : <>
            <Text color="white">{value}</Text>
            <Text color={CLAUDE_COLOR}>{cursor}</Text>
          </>
      }
    </Box>
  );
}
