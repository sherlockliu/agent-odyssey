import { LLMClient } from './types.js';
import { AnthropicClient } from './anthropic.js';
import { OllamaClient } from './ollama.js';
import { GeminiClient } from './gemini.js';

export function createClient(provider: string, model: string): LLMClient {
  switch (provider) {
    case 'anthropic':
      return new AnthropicClient(model);
    case 'ollama':
      return new OllamaClient(model);
    case 'gemini':
      return new GeminiClient(model);
    default:
      throw new Error(`Unknown LLM provider: ${provider}`);
  }
}

export type { LLMClient } from './types.js';
