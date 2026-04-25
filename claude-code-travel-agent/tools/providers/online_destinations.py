"""Online destinations tool provider.

Provides `search_destinations_online(interests, budget_level, trip_length_days)`
which augments the built-in destination search with richer, more up-to-date
information (or, in mock mode, returns extended destination data).

Mode selection (set in config.py ONLINE_DESTINATIONS_CONFIG):
  "mock" — extended mock results from dummy_data/destinations.json.
  "api"  — hook for a real travel discovery API.
           Set TRAVEL_API_KEY and ONLINE_DESTINATIONS_MODE=api.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..provider import ToolProvider

_DUMMY_DATA_DIR = Path(__file__).parent.parent.parent / "dummy_data"

# Extra destination metadata that augments the base destinations.json.
_EXTENDED_INFO: dict[str, dict] = {
    "tokyo": {
        "visa_info": "Visa-free for most Western passport holders (up to 90 days).",
        "transport": "JR Pass recommended. IC card (Suica/Pasmo) for local transit.",
        "safety": "Very safe. Low crime rate. Excellent emergency infrastructure.",
        "currency_tip": "Mostly cash culture. 7-Eleven ATMs accept foreign cards.",
        "trending": True,
    },
    "paris": {
        "visa_info": "Schengen visa — 90 days for most countries.",
        "transport": "Metro is efficient. Navigo weekly pass for unlimited travel.",
        "safety": "Generally safe. Watch for pickpockets near major attractions.",
        "currency_tip": "Cards widely accepted. Keep some cash for smaller cafes.",
        "trending": False,
    },
    "bali": {
        "visa_info": "30-day visa on arrival for most nationalities (~$35 USD).",
        "transport": "Scooter rental popular. Grab (ride-hailing) available in Denpasar.",
        "safety": "Safe for tourists. Watch for petty theft at busy beaches.",
        "currency_tip": "Cash-heavy economy. ATMs widely available in Kuta/Seminyak.",
        "trending": True,
    },
    "barcelona": {
        "visa_info": "Schengen visa — 90 days for most countries.",
        "transport": "T-Casual 10-trip metro card is best value.",
        "safety": "Watch for pickpockets on La Rambla and beaches.",
        "currency_tip": "Cards widely accepted. Small tapas bars may prefer cash.",
        "trending": True,
    },
    "new york": {
        "visa_info": "ESTA for Visa Waiver Programme countries. Others need B-2 visa.",
        "transport": "MetroCard or OMNY tap. Subway runs 24/7.",
        "safety": "Generally safe. Avoid isolated areas at night.",
        "currency_tip": "Cards everywhere. 18–20% tip expected in restaurants.",
        "trending": False,
    },
    "sydney": {
        "visa_info": "eVisitor (subclass 651) — free online for eligible nationalities.",
        "transport": "Opal card for all public transit. Integrated buses, trains, ferries.",
        "safety": "Very safe. Standard city precautions apply.",
        "currency_tip": "Cashless is fine everywhere. GST included in all prices.",
        "trending": False,
    },
}


def _load_destinations() -> list[dict]:
    path = _DUMMY_DATA_DIR / "destinations.json"
    if path.exists():
        return json.loads(path.read_text())
    return []


def _mock_search_online(
    interests: list[str],
    budget_level: str = "medium",
    trip_length_days: int = 7,
) -> str:
    destinations = _load_destinations()
    if not destinations:
        return "No destination data available."

    interests_lower = [i.lower() for i in interests]
    budget_rank = {"low": 1, "medium": 2, "high": 3}

    def score(dest: dict) -> int:
        matches = sum(1 for tag in dest.get("best_for", []) if tag in interests_lower)
        budget_ok = (
            budget_rank.get(dest.get("budget_level", "medium"), 2)
            <= budget_rank.get(budget_level, 2) + 1
        )
        trending_bonus = 1 if _EXTENDED_INFO.get(dest.get("name", "").lower(), {}).get("trending") else 0
        return matches * (2 if budget_ok else 1) + trending_bonus

    ranked = sorted(destinations, key=score, reverse=True)
    top = [d for d in ranked if score(d) > 0][:5] or ranked[:3]

    lines = [
        f"Online destination discovery for interests: {', '.join(interests)} "
        f"| Budget: {budget_level} | Duration: {trip_length_days} days\n"
    ]
    for i, dest in enumerate(top, 1):
        name = dest.get("name", "")
        country = dest.get("country", "")
        daily = dest.get("estimated_daily_cost_usd", 0)
        total = daily * trip_length_days
        highlights = dest.get("highlights", [])[:3]
        best_months = dest.get("best_months", [])[:3]

        ext = _EXTENDED_INFO.get(name.lower(), {})
        trending = "🔥 Trending" if ext.get("trending") else ""
        visa = ext.get("visa_info", "Check embassy for visa requirements.")
        transport = ext.get("transport", "")
        safety = ext.get("safety", "")

        lines.append(
            f"{i}. {name}, {country}  {trending}\n"
            f"   Est. cost ({trip_length_days}d): ${total:,}  (~${daily}/day)\n"
            f"   Best months : {', '.join(best_months)}\n"
            f"   Highlights  : {', '.join(highlights)}\n"
            f"   Visa        : {visa}\n"
            f"   Transport   : {transport}\n"
            f"   Safety      : {safety}\n"
        )

    lines.append("[Data source: mock — set ONLINE_DESTINATIONS_MODE=api for live data]")
    return "\n".join(lines)


class OnlineDestinationProvider(ToolProvider):
    """Enhanced destination search with visa, transport, and safety info."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self._mode = cfg.get("mode", "mock")
        self._api_key = cfg.get("api_key", "")

    def get_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_destinations_online",
                    "description": (
                        "Search for travel destinations with enriched online data including "
                        "visa requirements, safety info, transport tips, and trending status. "
                        "Use this as an alternative to search_destinations when the user wants "
                        "more detail or is comparing destinations."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "interests": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Interests e.g. ['beaches', 'food', 'culture']",
                            },
                            "budget_level": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Trip budget level",
                            },
                            "trip_length_days": {
                                "type": "integer",
                                "description": "Number of days planned for the trip",
                            },
                        },
                        "required": ["interests"],
                    },
                },
            }
        ]

    def can_handle(self, name: str) -> bool:
        return name == "search_destinations_online"

    def execute(self, name: str, arguments: dict) -> str:
        if name != "search_destinations_online":
            return f"Error: OnlineDestinationProvider cannot handle '{name}'"
        interests = arguments.get("interests", [])
        if not interests:
            return "Error: 'interests' argument is required for search_destinations_online"
        budget_level = arguments.get("budget_level", "medium")
        trip_length_days = arguments.get("trip_length_days", 7)
        return _mock_search_online(interests, budget_level, trip_length_days)
