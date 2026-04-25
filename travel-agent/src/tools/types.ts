import { ToolDefinition } from '../llm/types.js';

export interface ToolProvider {
  getDefinitions(): ToolDefinition[];
  canHandle(name: string): boolean;
  execute(name: string, args: Record<string, unknown>): Promise<string>;
}

export type { ToolDefinition };
