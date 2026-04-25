import { ToolProvider, ToolDefinition } from './types.js';

export class ToolRegistry {
  private providers: ToolProvider[] = [];

  register(provider: ToolProvider): void {
    this.providers.push(provider);
  }

  getDefinitions(): ToolDefinition[] {
    return this.providers.flatMap(p => p.getDefinitions());
  }

  async dispatch(name: string, args: Record<string, unknown>): Promise<string> {
    for (const provider of this.providers) {
      if (provider.canHandle(name)) {
        return provider.execute(name, args);
      }
    }
    return `Unknown tool: ${name}`;
  }
}
