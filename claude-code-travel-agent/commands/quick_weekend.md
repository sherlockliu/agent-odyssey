# /quick-weekend Command

## Description
Plan a standard weekend trip quickly. Searches flights and hotels in one pass.

## Trigger
User types: `/quick-weekend` or "plan a quick weekend trip"

## Steps
1. Ask: "Which city?" (if not specified)
2. Ask: "Which weekend?" (e.g. "next weekend", "April 18-20")
3. Infer home airport from user profile (or ask if not set)
4. Search flights: Friday evening departure → Sunday evening return
5. Search hotels: 2 nights, mid-range (≤ $200/night)
6. Present top 2 flight + top 2 hotel options as packages
7. Ask user to pick or adjust
8. Add selected items to a new itinerary

## Notes
- If user profile has preferred airlines/chains, filter for those first
- Keep the interaction to ≤ 3 back-and-forth turns
- Create trip ID as: `weekend_{city}_{date}` e.g. `weekend_nyc_20260418`
