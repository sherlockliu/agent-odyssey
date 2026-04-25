import React from 'react';
import { Static } from 'ink';
import { Message, ChatMessage } from './Message.js';

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <Static items={messages}>
      {(message) => <Message key={message.id} message={message} />}
    </Static>
  );
}
