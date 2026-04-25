# /export Command

## Description
Print a formatted trip itinerary to the terminal.

## Trigger
User types: `/export`, "export my itinerary", "show me the full plan", "print the trip"

## Steps
1. If no active trip_id, ask: "Which trip would you like to export?"
2. Call `view_itinerary(trip_id)` to get the formatted plan
3. Display the result prominently in the terminal
4. Offer: "Would you like to save this to a file?"
5. If yes, write the output to `~/Desktop/{trip_id}_itinerary.txt`

## Format Notes
- Use the formatted output from view_itinerary (already includes dividers)
- Remind the user that all prices are estimates
- Include trip ID at the top for reference
