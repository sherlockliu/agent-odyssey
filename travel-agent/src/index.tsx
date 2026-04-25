import React from 'react';
import { render } from 'ink';
import { App } from './app/App.js';

if (!process.stdin.isTTY) {
  console.error('✈ Travel Agent requires an interactive terminal (TTY).');
  console.error('Run it directly: npm run dev');
  process.exit(1);
}

const { waitUntilExit } = render(<App />);
waitUntilExit().then(() => process.exit(0));
