# /profile Command

## Description
Show or update the traveller profile. The profile persists across all sessions.

## Trigger
User types `/profile` (show) or `/profile set <field> <value>` (update).

## Fields

| Field alias | Profile key | Type | Example |
|---|---|---|---|
| `name` | `name` | string | Alice |
| `airport` | `home_airport` | string | SFO |
| `seat` | `seat_preference` | string | window / aisle / middle |
| `airlines` | `preferred_airlines` | list | United,Delta |
| `hotels` | `preferred_hotel_chains` | list | Marriott,Hilton |
| `interests` | `interests` | list | hiking,food,culture |
| `avoid` | `avoid` | list | long-haul,crowds |
| `flight_budget` | `budget_defaults.flight_max_usd` | integer | 1200 |
| `hotel_budget` | `budget_defaults.hotel_max_per_night_usd` | integer | 350 |

## Interactive setup flow (Q&A mode)

If the user just types `/profile` with no arguments, walk through these questions
**one at a time** (skip any already set in the profile):

1. "What's your home airport? (e.g. SFO, JFK, LHR)"
   → call `update_profile(field="home_airport", value=<answer>, source="explicit")`

2. "Any seat preference? (window / aisle / middle, or skip)"
   → call `update_profile(field="seat_preference", value=<answer>, source="explicit")`

3. "Preferred airlines? (comma-separated, or skip)"
   → call `update_profile(field="preferred_airlines", value=<answer>, source="explicit")`

4. "Preferred hotel chains? (comma-separated, or skip)"
   → call `update_profile(field="preferred_hotel_chains", value=<answer>, source="explicit")`

5. "What are your travel interests? (e.g. food, museums, beaches, hiking)"
   → call `update_profile(field="interests", value=<answer>, source="explicit")`

6. "Anything you want to avoid? (e.g. long-haul, layovers, crowds)"
   → call `update_profile(field="avoid", value=<answer>, source="explicit")`

7. "Maximum flight budget? (USD, or skip)"
   → call `update_profile(field="flight_max_usd", value=<answer>, source="explicit")`

8. "Maximum hotel budget per night? (USD, or skip)"
   → call `update_profile(field="hotel_max_per_night_usd", value=<answer>, source="explicit")`

After all steps: show the updated profile with `get_profile()` and confirm:
"Your profile has been saved. I'll use these preferences for all future searches."

## Notes
- Accept "skip" or empty answers — leave those fields unchanged
- If `/profile set <field> <value>` is used, skip the Q&A and set directly
- After any update, confirm what was saved: "Saved: home airport = SFO"
- Never show the raw file path to the user
