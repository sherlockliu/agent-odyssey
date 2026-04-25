import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'fs';
import { resolve } from 'path';
import { homedir } from 'os';
import { Message } from '../llm/types.js';

export interface ItineraryItem {
  day: number;
  activity: string;
  details?: string;
}

export interface TripContextData {
  tripId: string;
  createdAt: string;
  destination?: string;
  dates?: { start?: string; end?: string };
  budget?: number;
  currency?: string;
  itinerary: ItineraryItem[];
  notes: string[];
  conversationHistory: Array<{ role: string; content: unknown }>;
}

const TRIPS_DIR = resolve(homedir(), '.travel-agent', 'trips');

function generateTripId(): string {
  return `trip_${Date.now().toString(36)}`;
}

export class TripContext {
  tripId: string;
  private data: TripContextData;

  constructor() {
    this.tripId = generateTripId();
    this.data = {
      tripId: this.tripId,
      createdAt: new Date().toISOString(),
      itinerary: [],
      notes: [],
      conversationHistory: [],
    };
  }

  async load(tripId?: string): Promise<void> {
    if (!existsSync(TRIPS_DIR)) {
      mkdirSync(TRIPS_DIR, { recursive: true });
    }

    if (tripId) {
      // Load specific trip
      const path = resolve(TRIPS_DIR, `${tripId}.json`);
      if (existsSync(path)) {
        this.data = JSON.parse(readFileSync(path, 'utf-8')) as TripContextData;
        this.tripId = this.data.tripId;
      }
    }
    // Otherwise use the freshly created trip (no auto-resume for simplicity)
  }

  async save(): Promise<void> {
    if (!existsSync(TRIPS_DIR)) {
      mkdirSync(TRIPS_DIR, { recursive: true });
    }
    const path = resolve(TRIPS_DIR, `${this.tripId}.json`);
    writeFileSync(path, JSON.stringify(this.data, null, 2), 'utf-8');
  }

  getConversationHistory(): Message[] {
    // Filter to only user/assistant messages (skip system)
    return this.data.conversationHistory
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({
        role: m.role as 'user' | 'assistant',
        content: typeof m.content === 'string' ? m.content : JSON.stringify(m.content),
      }));
  }

  updateHistory(messages: Message[]): void {
    // Persist only user/assistant messages (skip system)
    this.data.conversationHistory = messages
      .filter(m => m.role !== 'system')
      .map(m => ({
        role: m.role,
        content: m.content,
        ...(m.tool_call_id ? { tool_call_id: m.tool_call_id } : {}),
      }));
  }

  // Getters for tool access
  getDestination(): string | undefined { return this.data.destination; }
  getDates(): { start?: string; end?: string } | undefined { return this.data.dates; }
  getBudget(): number | undefined { return this.data.budget; }
  getItinerary(): ItineraryItem[] { return this.data.itinerary; }
  getNotes(): string[] { return this.data.notes; }

  // Setters for tool use
  setDestination(dest: string): void { this.data.destination = dest; }
  setDates(dates: { start?: string; end?: string }): void { this.data.dates = dates; }
  setBudget(budget: number, currency = 'USD'): void {
    this.data.budget = budget;
    this.data.currency = currency;
  }
  addItineraryItem(item: ItineraryItem): void { this.data.itinerary.push(item); }
  setItinerary(items: ItineraryItem[]): void { this.data.itinerary = items; }
  addNote(note: string): void { this.data.notes.push(note); }

  asContextMessage(): string {
    const lines: string[] = [];
    if (this.data.destination) lines.push(`Destination: ${this.data.destination}`);
    if (this.data.dates?.start) lines.push(`Travel dates: ${this.data.dates.start}${this.data.dates.end ? ' to ' + this.data.dates.end : ''}`);
    if (this.data.budget) lines.push(`Budget: ${this.data.currency ?? 'USD'} ${this.data.budget}`);
    if (this.data.itinerary.length > 0) {
      lines.push('Itinerary:');
      for (const item of this.data.itinerary) {
        lines.push(`  Day ${item.day}: ${item.activity}${item.details ? ' - ' + item.details : ''}`);
      }
    }
    if (this.data.notes.length > 0) {
      lines.push('Notes: ' + this.data.notes.join('; '));
    }
    return lines.join('\n') || '';
  }

  static listTrips(): string[] {
    if (!existsSync(TRIPS_DIR)) return [];
    return readdirSync(TRIPS_DIR)
      .filter(f => f.endsWith('.json'))
      .map(f => f.replace('.json', ''));
  }
}
