import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// Load .env from project root
const envPath = resolve(__dirname, '..', '.env');
if (existsSync(envPath)) {
  const envContent = readFileSync(envPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
    if (!(key in process.env)) process.env[key] = value;
  }
}

export const LLM_PROVIDER = (process.env['LLM_PROVIDER'] ?? 'anthropic') as 'anthropic' | 'ollama' | 'gemini';
export const LLM_MODEL = process.env['LLM_MODEL'] ?? 'claude-haiku-3-5-20241022';
export const ANTHROPIC_API_KEY = process.env['ANTHROPIC_API_KEY'] ?? '';
export const OLLAMA_HOST = process.env['OLLAMA_HOST'] ?? 'http://localhost:11434';
export const WEATHER_MODE = (process.env['WEATHER_MODE'] ?? 'mock') as 'mock' | 'api';
export const ACTIVITIES_MODE = (process.env['ACTIVITIES_MODE'] ?? 'mock') as 'mock' | 'api';

export const MODES = {
  passive: 'Answer questions only. Do not proactively search or suggest.',
  default: 'Guide the user through planning. Suggest next steps, confirm before committing.',
  proactive: 'Plan the full trip autonomously based on stated preferences. Present at the end.',
} as const;

export type AgentMode = keyof typeof MODES;
export const DEFAULT_MODE: AgentMode = 'default';

export const COMPRESS_THRESHOLD = 0.80;
export const CONTEXT_WINDOW_LIMIT = 32000;
