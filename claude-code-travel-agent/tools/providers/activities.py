"""Activities tool provider.

Provides `search_activities(city, interests, date)` to the travel agent.

Mode selection (set in config.py ACTIVITIES_CONFIG):
  "mock" — returns curated data from dummy_data/activities.json.
  "api"  — hook for a real activities API (Ticketmaster, Viator, etc.).
           Set TICKETMASTER_API_KEY and ACTIVITIES_MODE=api in environment.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..provider import ToolProvider

_DUMMY_DATA_DIR = Path(__file__).parent.parent.parent / "dummy_data"


def _load_activities() -> list[dict]:
    path = _DUMMY_DATA_DIR / "activities.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def _mock_search_activities(
    city: str,
    interests: list[str] | None = None,
    date: str = "",
) -> str:
    all_activities = _load_activities()
    city_lower = city.lower().strip()
    interests_lower = [i.lower() for i in (interests or [])]

    # Filter by city.
    city_activities = [
        a for a in all_activities
        if a.get("city", "").lower() == city_lower
    ]

    if not city_activities:
        from tools.llm_fallback import generate_activity_results
        return generate_activity_results(city, interests or [])

    # Score by interest match.
    def score(activity: dict) -> int:
        if not interests_lower:
            return 1
        tags = [t.lower() for t in activity.get("tags", [])]
        return sum(1 for interest in interests_lower if any(interest in tag for tag in tags))

    ranked = sorted(city_activities, key=score, reverse=True)[:6]

    date_note = f" on {date}" if date else ""
    lines = [f"Things to do in {city.title()}{date_note}:\n"]
    for i, act in enumerate(ranked, 1):
        name = act.get("name", "Unknown")
        category = act.get("category", "")
        price = act.get("price_usd", 0)
        duration = act.get("duration_hours", "")
        desc = act.get("description", "")
        tags = ", ".join(act.get("tags", [])[:3])

        price_str = f"${price:.0f}" if price else "Free"
        dur_str = f"{duration}h" if duration else ""

        lines.append(
            f"{i}. {name}  [{category}]\n"
            f"   {desc}\n"
            f"   Price: {price_str}  •  Duration: {dur_str}  •  Tags: {tags}\n"
        )

    lines.append("[Data source: mock — set ACTIVITIES_MODE=api for live results]")
    return "\n".join(lines)


def _api_search_activities(
    city: str,
    interests: list[str] | None = None,
    date: str = "",
    api_key: str = "",
) -> str:
    """
    Placeholder for a real activities API call (e.g. Ticketmaster Discovery API).
    Falls back to mock data until an API key is configured.
    """
    if not api_key:
        return _mock_search_activities(city, interests, date) + "\n[API key not set — using mock data]"

    # TODO: implement Ticketmaster / Viator API call here when api_key is available.
    # Example endpoint: https://app.ticketmaster.com/discovery/v2/events.json
    return _mock_search_activities(city, interests, date) + "\n[API integration pending]"


class ActivitiesToolProvider(ToolProvider):
    """Provides activity and event search for travel destinations."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self._mode = cfg.get("mode", "mock")
        self._api_key = cfg.get("api_key", "")

    def get_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_activities",
                    "description": (
                        "Search for things to do, attractions, tours, and events in a city. "
                        "Use this when the user asks what to do, things to see, or activities."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City to search activities in, e.g. 'Tokyo'",
                            },
                            "interests": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Interests to filter by, e.g. ['food', 'museums', 'outdoor']",
                            },
                            "date": {
                                "type": "string",
                                "description": "Optional specific date, e.g. '2026-04-10'",
                            },
                        },
                        "required": ["city"],
                    },
                },
            }
        ]

    def can_handle(self, name: str) -> bool:
        return name == "search_activities"

    def execute(self, name: str, arguments: dict) -> str:
        if name != "search_activities":
            return f"Error: ActivitiesToolProvider cannot handle '{name}'"
        city = arguments.get("city", "")
        if not city:
            return "Error: 'city' argument is required for search_activities"
        interests = arguments.get("interests")
        date = arguments.get("date", "")
        if self._mode == "api":
            return _api_search_activities(city, interests, date, self._api_key)
        return _mock_search_activities(city, interests, date)
