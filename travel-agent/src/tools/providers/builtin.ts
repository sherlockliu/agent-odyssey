import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import { ToolProvider, ToolDefinition } from '../types.js';
import { TripContext } from '../../memory/tripContext.js';
import { TOOL_DEFINITIONS } from '../definitions.js';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const DATA_DIR = resolve(__dirname, '..', '..', '..', 'dummy_data');

function loadJson(filename: string): unknown {
  return JSON.parse(readFileSync(resolve(DATA_DIR, filename), 'utf-8'));
}

const BUILTIN_TOOLS = new Set([
  'search_destinations', 'search_flights', 'search_hotels',
  'view_itinerary', 'update_itinerary', 'export_itinerary',
  'get_profile', 'update_profile',
]);

export class BuiltinProvider implements ToolProvider {
  private tripContext: TripContext;

  constructor(tripContext: TripContext) {
    this.tripContext = tripContext;
  }

  getDefinitions(): ToolDefinition[] {
    return TOOL_DEFINITIONS.filter(d => BUILTIN_TOOLS.has(d.name));
  }

  canHandle(name: string): boolean {
    return BUILTIN_TOOLS.has(name);
  }

  async execute(name: string, args: Record<string, unknown>): Promise<string> {
    switch (name) {
      case 'search_destinations': return this.searchDestinations(args);
      case 'search_flights': return this.searchFlights(args);
      case 'search_hotels': return this.searchHotels(args);
      case 'view_itinerary': return this.viewItinerary();
      case 'update_itinerary': return this.updateItinerary(args);
      case 'export_itinerary': return this.exportItinerary(args);
      case 'get_profile': return this.getProfile();
      case 'update_profile': return this.updateProfile(args);
      default: return `Unknown tool: ${name}`;
    }
  }

  private searchDestinations(args: Record<string, unknown>): string {
    const destinations = loadJson('destinations.json') as Array<{
      name: string; country: string; region: string; tags: string[];
      budget_level: string; best_for: string[]; description: string;
    }>;

    const interests = (args['interests'] as string[] | undefined) ?? [];
    const budgetLevel = args['budget_level'] as string | undefined;
    const region = args['region'] as string | undefined;

    let filtered = destinations;

    if (budgetLevel) {
      filtered = filtered.filter(d => d.budget_level === budgetLevel || d.budget_level === 'varies');
    }
    if (region) {
      filtered = filtered.filter(d =>
        d.region.toLowerCase().includes(region.toLowerCase()) ||
        d.country.toLowerCase().includes(region.toLowerCase())
      );
    }
    if (interests.length > 0) {
      filtered = filtered.filter(d =>
        interests.some(i => d.tags.some(t => t.toLowerCase().includes(i.toLowerCase())) ||
          d.best_for.some(b => b.toLowerCase().includes(i.toLowerCase())))
      );
    }

    const results = filtered.slice(0, 5);
    if (results.length === 0) return 'No destinations found matching your criteria.';

    return 'Found destinations:\n' + results.map(d =>
      `• ${d.name}, ${d.country} (${d.region}) — ${d.description}\n  Tags: ${d.tags.join(', ')}`
    ).join('\n');
  }

  private searchFlights(args: Record<string, unknown>): string {
    const flights = loadJson('flights.json') as Array<{
      airline: string; flight_number: string; origin: string; destination: string;
      departure: string; arrival: string; duration: string;
      price_economy: number; price_business: number; stops: number;
    }>;

    const origin = (args['origin'] as string ?? '').toUpperCase();
    const destination = (args['destination'] as string ?? '').toUpperCase();
    const passengers = (args['passengers'] as number | undefined) ?? 1;
    const cabinClass = (args['cabin_class'] as string | undefined) ?? 'economy';

    const matches = flights.filter(f =>
      (f.origin.toUpperCase().includes(origin) || origin === '') &&
      (f.destination.toUpperCase().includes(destination) || destination === '')
    ).slice(0, 5);

    if (matches.length === 0) {
      // Return generic options when no specific match
      return `No direct flights found from ${origin} to ${destination}. Consider connecting flights or nearby airports.`;
    }

    const priceKey = cabinClass === 'economy' ? 'price_economy' : 'price_business';
    return `Available flights from ${origin} to ${destination}:\n` + matches.map(f => {
      const price = f[priceKey as keyof typeof f] as number;
      const total = price * passengers;
      return `• ${f.airline} ${f.flight_number}: ${f.departure} → ${f.arrival} (${f.duration}), ${f.stops === 0 ? 'nonstop' : f.stops + ' stop(s)'}\n  ${cabinClass}: $${price}/person = $${total} total for ${passengers} passenger(s)`;
    }).join('\n');
  }

  private searchHotels(args: Record<string, unknown>): string {
    const hotels = loadJson('hotels.json') as Array<{
      name: string; city: string; stars: number; price_per_night: number;
      amenities: string[]; description: string; neighborhood: string;
    }>;

    const destination = (args['destination'] as string ?? '').toLowerCase();
    const maxBudget = args['budget_per_night'] as number | undefined;
    const minStars = (args['stars'] as number | undefined) ?? 1;

    let filtered = hotels.filter(h =>
      h.city.toLowerCase().includes(destination) ||
      destination === ''
    );

    if (maxBudget) filtered = filtered.filter(h => h.price_per_night <= maxBudget);
    if (minStars > 1) filtered = filtered.filter(h => h.stars >= minStars);

    const results = filtered.slice(0, 5);
    if (results.length === 0) return `No hotels found in ${destination} matching your criteria.`;

    return `Hotels in ${destination}:\n` + results.map(h =>
      `• ${h.name} (${'★'.repeat(h.stars)}) — $${h.price_per_night}/night\n  ${h.neighborhood}: ${h.description}\n  Amenities: ${h.amenities.join(', ')}`
    ).join('\n');
  }

  private viewItinerary(): string {
    const msg = this.tripContext.asContextMessage();
    return msg || 'No itinerary yet. Start by searching for destinations, flights, or hotels.';
  }

  private updateItinerary(args: Record<string, unknown>): string {
    const updates: string[] = [];

    if (args['destination']) {
      this.tripContext.setDestination(args['destination'] as string);
      updates.push(`destination: ${args['destination']}`);
    }
    if (args['dates']) {
      this.tripContext.setDates(args['dates'] as { start?: string; end?: string });
      updates.push(`dates: ${JSON.stringify(args['dates'])}`);
    }
    if (args['budget']) {
      this.tripContext.setBudget(args['budget'] as number);
      updates.push(`budget: $${args['budget']}`);
    }
    if (args['items'] && Array.isArray(args['items'])) {
      for (const item of args['items'] as Array<{ day: number; activity: string; details?: string }>) {
        this.tripContext.addItineraryItem(item);
      }
      updates.push(`${(args['items'] as unknown[]).length} itinerary item(s) added`);
    }
    if (args['note']) {
      this.tripContext.addNote(args['note'] as string);
      updates.push(`note added`);
    }

    if (updates.length === 0) return 'No changes made to itinerary.';
    return `Itinerary updated: ${updates.join(', ')}`;
  }

  private exportItinerary(args: Record<string, unknown>): string {
    const itinerary = this.tripContext.getItinerary();
    const destination = this.tripContext.getDestination() ?? 'Unknown';
    const dates = this.tripContext.getDates();
    const budget = this.tripContext.getBudget();

    const lines = [
      `# Trip to ${destination}`,
      '',
      dates?.start ? `**Dates:** ${dates.start}${dates.end ? ' to ' + dates.end : ''}` : '',
      budget ? `**Budget:** $${budget}` : '',
      '',
      '## Itinerary',
      '',
    ].filter(l => l !== undefined);

    if (itinerary.length === 0) {
      lines.push('*No itinerary items yet.*');
    } else {
      for (const item of itinerary) {
        lines.push(`### Day ${item.day}`);
        lines.push(`- ${item.activity}${item.details ? ': ' + item.details : ''}`);
      }
    }

    const filename = (args['filename'] as string | undefined) ?? `trip-${destination.toLowerCase().replace(/\s+/g, '-')}`;
    const path = resolve(process.cwd(), `${filename}.md`);

    try {
      writeFileSync(path, lines.join('\n'), 'utf-8');
      return `Itinerary exported to ${path}`;
    } catch {
      return `Itinerary content:\n${lines.join('\n')}`;
    }
  }

  private getProfile(): string {
    return 'Profile retrieval is handled by App initialization. Use update_profile to set preferences.';
  }

  private updateProfile(args: Record<string, unknown>): string {
    const updates: Record<string, unknown> = {};
    if (args['name']) updates['name'] = args['name'];
    if (args['home_airport']) updates['homeAirport'] = args['home_airport'];
    if (args['preferred_airlines']) updates['preferredAirlines'] = args['preferred_airlines'];
    if (args['seat_preference']) updates['seatPreference'] = args['seat_preference'];
    if (args['interests']) updates['interests'] = args['interests'];
    if (args['budget_flights'] || args['budget_hotels']) {
      updates['budgetDefaults'] = {
        flights: args['budget_flights'],
        hotels: args['budget_hotels'],
      };
    }
    return `Profile updated with: ${Object.keys(updates).join(', ')}`;
  }
}
