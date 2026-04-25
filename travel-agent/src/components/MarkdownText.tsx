import React from 'react';
import { Box, Text } from 'ink';

// Renders inline markdown: **bold**, *italic*, `code`
function InlineText({ text, baseColor }: { text: string; baseColor?: string }) {
  // Split on bold, italic, and inline code markers
  const parts: React.ReactNode[] = [];
  // Regex: **bold** | *italic* | `code`
  const pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(
        <Text key={key++} color={baseColor}>{text.slice(last, match.index)}</Text>
      );
    }
    if (match[2] !== undefined) {
      // **bold**
      parts.push(<Text key={key++} bold color={baseColor}>{match[2]}</Text>);
    } else if (match[3] !== undefined) {
      // *italic*
      parts.push(<Text key={key++} italic color={baseColor}>{match[3]}</Text>);
    } else if (match[4] !== undefined) {
      // `code`
      parts.push(<Text key={key++} color="#10b981">{match[4]}</Text>);
    }
    last = match.index + match[0].length;
  }

  if (last < text.length) {
    parts.push(<Text key={key++} color={baseColor}>{text.slice(last)}</Text>);
  }

  return <Text>{parts}</Text>;
}

interface MarkdownTextProps {
  children: string;
}

export function MarkdownText({ children }: MarkdownTextProps) {
  const lines = children.split('\n');
  const nodes: React.ReactNode[] = [];
  let key = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!;

    // H1
    if (/^# (.+)/.test(line)) {
      const content = line.replace(/^# /, '');
      nodes.push(
        <Box key={key++} marginBottom={1}>
          <Text bold color="white">{content}</Text>
        </Box>
      );
      continue;
    }

    // H2
    if (/^## (.+)/.test(line)) {
      const content = line.replace(/^## /, '');
      nodes.push(
        <Box key={key++} marginBottom={1}>
          <Text bold color="white">{content}</Text>
        </Box>
      );
      continue;
    }

    // H3
    if (/^### (.+)/.test(line)) {
      const content = line.replace(/^### /, '');
      nodes.push(
        <Box key={key++}>
          <Text bold dimColor>{content}</Text>
        </Box>
      );
      continue;
    }

    // Unordered list item: - or * at start
    if (/^(\s*)[*-] (.+)/.test(line)) {
      const indent = line.match(/^(\s*)/)?.[1]?.length ?? 0;
      const content = line.replace(/^\s*[*-] /, '');
      nodes.push(
        <Box key={key++} paddingLeft={indent}>
          <Text color="#d77757">{'• '}</Text>
          <InlineText text={content} />
        </Box>
      );
      continue;
    }

    // Numbered list item
    if (/^\d+\. (.+)/.test(line)) {
      const num = line.match(/^(\d+)\./)?.[1];
      const content = line.replace(/^\d+\. /, '');
      nodes.push(
        <Box key={key++}>
          <Text color="#d77757">{num + '. '}</Text>
          <InlineText text={content} />
        </Box>
      );
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      nodes.push(
        <Box key={key++} marginY={1}>
          <Text dimColor>{'─'.repeat(40)}</Text>
        </Box>
      );
      continue;
    }

    // Blank line → spacing
    if (line.trim() === '') {
      // Only add space if not the first/last line
      if (i > 0 && i < lines.length - 1) {
        nodes.push(<Box key={key++} marginBottom={0}><Text>{' '}</Text></Box>);
      }
      continue;
    }

    // Normal text with inline parsing
    nodes.push(
      <Box key={key++} flexWrap="wrap">
        <InlineText text={line} />
      </Box>
    );
  }

  return <Box flexDirection="column">{nodes}</Box>;
}
