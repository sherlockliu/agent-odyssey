import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve } from 'path';
import { homedir } from 'os';

export interface UserProfileData {
  name?: string;
  homeAirport?: string;
  preferredAirlines?: string[];
  preferredHotelChains?: string[];
  seatPreference?: string;
  interests?: string[];
  budgetDefaults?: {
    flights?: 'budget' | 'economy' | 'business' | 'first';
    hotels?: 'budget' | 'mid-range' | 'luxury';
  };
  pastTrips?: string[];
}

const PROFILE_DIR = resolve(homedir(), '.travel-agent');
const PROFILE_PATH = resolve(PROFILE_DIR, 'profile.json');

export class UserProfile {
  private data: UserProfileData = {};

  async load(): Promise<void> {
    if (!existsSync(PROFILE_DIR)) {
      mkdirSync(PROFILE_DIR, { recursive: true });
    }
    if (existsSync(PROFILE_PATH)) {
      try {
        this.data = JSON.parse(readFileSync(PROFILE_PATH, 'utf-8')) as UserProfileData;
      } catch {
        this.data = {};
      }
    }
  }

  async save(): Promise<void> {
    if (!existsSync(PROFILE_DIR)) {
      mkdirSync(PROFILE_DIR, { recursive: true });
    }
    writeFileSync(PROFILE_PATH, JSON.stringify(this.data, null, 2), 'utf-8');
  }

  update(fields: Partial<UserProfileData>): void {
    this.data = { ...this.data, ...fields };
  }

  get(): UserProfileData {
    return { ...this.data };
  }

  asContextMessage(): string {
    if (Object.keys(this.data).length === 0) return '';
    const lines: string[] = [];
    if (this.data.name) lines.push(`Name: ${this.data.name}`);
    if (this.data.homeAirport) lines.push(`Home airport: ${this.data.homeAirport}`);
    if (this.data.preferredAirlines?.length) lines.push(`Preferred airlines: ${this.data.preferredAirlines.join(', ')}`);
    if (this.data.interests?.length) lines.push(`Interests: ${this.data.interests.join(', ')}`);
    if (this.data.budgetDefaults) {
      const b = this.data.budgetDefaults;
      lines.push(`Budget preferences: flights=${b.flights ?? 'any'}, hotels=${b.hotels ?? 'any'}`);
    }
    return lines.join('\n');
  }
}
