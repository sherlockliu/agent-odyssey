import { ToolDefinition } from './types.js';

export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    name: 'search_destinations',
    description: 'Search for travel destinations based on interests, budget, and trip preferences.',
    input_schema: {
      type: 'object',
      properties: {
        interests: { type: 'array', items: { type: 'string' }, description: 'List of traveler interests (e.g. beaches, history, food)' },
        budget_level: { type: 'string', enum: ['budget', 'medium', 'luxury'], description: 'Budget level for the trip' },
        trip_length_days: { type: 'integer', description: 'Number of days for the trip' },
        region: { type: 'string', description: 'Preferred region or continent (optional)' },
      },
      required: ['interests'],
    },
  },
  {
    name: 'search_flights',
    description: 'Search for available flights between two cities.',
    input_schema: {
      type: 'object',
      properties: {
        origin: { type: 'string', description: 'Departure city or airport code' },
        destination: { type: 'string', description: 'Arrival city or airport code' },
        date: { type: 'string', description: 'Travel date in YYYY-MM-DD format' },
        return_date: { type: 'string', description: 'Return date for round trips (optional)' },
        passengers: { type: 'integer', description: 'Number of passengers', default: 1 },
        cabin_class: { type: 'string', enum: ['economy', 'business', 'first'], default: 'economy' },
      },
      required: ['origin', 'destination', 'date'],
    },
  },
  {
    name: 'search_hotels',
    description: 'Search for hotels at the destination.',
    input_schema: {
      type: 'object',
      properties: {
        destination: { type: 'string', description: 'City or area to search hotels' },
        check_in: { type: 'string', description: 'Check-in date YYYY-MM-DD' },
        check_out: { type: 'string', description: 'Check-out date YYYY-MM-DD' },
        guests: { type: 'integer', description: 'Number of guests', default: 1 },
        budget_per_night: { type: 'number', description: 'Maximum budget per night in USD' },
        stars: { type: 'integer', description: 'Minimum star rating (1-5)' },
      },
      required: ['destination'],
    },
  },
  {
    name: 'view_itinerary',
    description: 'View the current trip itinerary.',
    input_schema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'update_itinerary',
    description: 'Add or update items in the trip itinerary.',
    input_schema: {
      type: 'object',
      properties: {
        destination: { type: 'string', description: 'Trip destination' },
        dates: {
          type: 'object',
          properties: {
            start: { type: 'string', description: 'Start date YYYY-MM-DD' },
            end: { type: 'string', description: 'End date YYYY-MM-DD' },
          },
        },
        budget: { type: 'number', description: 'Total trip budget in USD' },
        items: {
          type: 'array',
          description: 'Itinerary items to add',
          items: {
            type: 'object',
            properties: {
              day: { type: 'integer' },
              activity: { type: 'string' },
              details: { type: 'string' },
            },
            required: ['day', 'activity'],
          },
        },
        note: { type: 'string', description: 'Note to add to the trip' },
      },
    },
  },
  {
    name: 'export_itinerary',
    description: 'Export the current itinerary to a markdown file.',
    input_schema: {
      type: 'object',
      properties: {
        filename: { type: 'string', description: 'Output filename (without extension)' },
      },
    },
  },
  {
    name: 'get_profile',
    description: 'Get the current user travel profile and preferences.',
    input_schema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'update_profile',
    description: 'Update user travel preferences and profile.',
    input_schema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'User name' },
        home_airport: { type: 'string', description: 'Home airport code (e.g. SFO, JFK)' },
        preferred_airlines: { type: 'array', items: { type: 'string' }, description: 'Preferred airline names or codes' },
        seat_preference: { type: 'string', enum: ['window', 'aisle', 'middle', 'no preference'] },
        interests: { type: 'array', items: { type: 'string' }, description: 'Travel interests' },
        budget_flights: { type: 'string', enum: ['budget', 'economy', 'business', 'first'] },
        budget_hotels: { type: 'string', enum: ['budget', 'mid-range', 'luxury'] },
      },
    },
  },
  {
    name: 'get_weather',
    description: 'Get weather information for a destination.',
    input_schema: {
      type: 'object',
      properties: {
        city: { type: 'string', description: 'City name' },
        date_range: { type: 'string', description: 'Date range (e.g. "next week", "July 2026")' },
      },
      required: ['city'],
    },
  },
  {
    name: 'search_activities',
    description: 'Search for activities and attractions at a destination.',
    input_schema: {
      type: 'object',
      properties: {
        location: { type: 'string', description: 'City or area to search' },
        category: { type: 'string', description: 'Activity category (e.g. museums, outdoor, food, nightlife)' },
        budget_per_person: { type: 'number', description: 'Max budget per person in USD' },
      },
      required: ['location'],
    },
  },
];
