import { ToolProvider, ToolDefinition } from '../types.js';
import { TOOL_DEFINITIONS } from '../definitions.js';

const WEATHER_CONDITIONS = [
  'Sunny, 24°C — perfect weather for sightseeing',
  'Partly cloudy, 20°C — comfortable for outdoor activities',
  'Clear skies, 28°C — warm and sunny',
  'Light rain expected, 18°C — bring a light jacket',
  'Overcast but dry, 22°C — good for walking tours',
  'Warm and humid, 30°C — stay hydrated',
];

export class WeatherProvider implements ToolProvider {
  getDefinitions(): ToolDefinition[] {
    return TOOL_DEFINITIONS.filter(d => d.name === 'get_weather');
  }

  canHandle(name: string): boolean {
    return name === 'get_weather';
  }

  async execute(_name: string, args: Record<string, unknown>): Promise<string> {
    const city = args['city'] as string ?? 'the destination';
    const dateRange = args['date_range'] as string | undefined;

    const condition = WEATHER_CONDITIONS[Math.floor(Math.random() * WEATHER_CONDITIONS.length)];
    const period = dateRange ? ` during ${dateRange}` : '';

    return `Weather forecast for ${city}${period}:\n${condition}\n\nNote: This is simulated data for demonstration purposes.`;
  }
}
