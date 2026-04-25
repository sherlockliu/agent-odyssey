import { readFileSync } from 'fs';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import { ToolProvider, ToolDefinition } from '../types.js';
import { TOOL_DEFINITIONS } from '../definitions.js';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const DATA_DIR = resolve(__dirname, '..', '..', '..', 'dummy_data');

export class ActivitiesProvider implements ToolProvider {
  getDefinitions(): ToolDefinition[] {
    return TOOL_DEFINITIONS.filter(d => d.name === 'search_activities');
  }

  canHandle(name: string): boolean {
    return name === 'search_activities';
  }

  async execute(_name: string, args: Record<string, unknown>): Promise<string> {
    const location = (args['location'] as string ?? '').toLowerCase();
    const category = (args['category'] as string | undefined)?.toLowerCase();
    const maxBudget = args['budget_per_person'] as number | undefined;

    const activities = JSON.parse(readFileSync(resolve(DATA_DIR, 'activities.json'), 'utf-8')) as Array<{
      name: string; city: string; category: string; price: number;
      duration: string; description: string; rating: number;
    }>;

    let filtered = activities.filter(a =>
      a.city.toLowerCase().includes(location) || location === ''
    );

    if (category) {
      filtered = filtered.filter(a => a.category.toLowerCase().includes(category));
    }
    if (maxBudget) {
      filtered = filtered.filter(a => a.price <= maxBudget);
    }

    const results = filtered.slice(0, 6);
    if (results.length === 0) {
      return `No activities found in ${location}${category ? ` for category: ${category}` : ''}.`;
    }

    return `Activities in ${location}:\n` + results.map(a =>
      `• ${a.name} (${a.category}) — $${a.price}/person, ${a.duration}\n  ${a.description} ⭐ ${a.rating}`
    ).join('\n');
  }
}
