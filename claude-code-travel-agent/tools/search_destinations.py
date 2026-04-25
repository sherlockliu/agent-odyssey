"""Search and recommend travel destinations."""

import json
from pathlib import Path

from config import DUMMY_DATA_DIR

_DESTINATIONS = json.loads((DUMMY_DATA_DIR / "destinations.json").read_text())

BUDGET_RANK = {"low": 1, "medium": 2, "high": 3}


def search_destinations(
    interests: list[str],
    budget_level: str = "medium",
    trip_length_days: int = 5,
) -> str:
    """Recommend destinations matching interests and budget. Returns plain text."""

    interests_lower = [i.lower() for i in interests]

    def score(dest: dict) -> int:
        matches = sum(1 for tag in dest["best_for"] if tag in interests_lower)
        budget_ok = BUDGET_RANK.get(dest["budget_level"], 2) <= BUDGET_RANK.get(budget_level, 2) + 1
        return matches * (2 if budget_ok else 1)

    ranked = sorted(_DESTINATIONS, key=score, reverse=True)
    top = [d for d in ranked if score(d) > 0][:5] or ranked[:5]

    est_cost = trip_length_days

    lines = [
        f"Top destination recommendations based on your interests ({', '.join(interests)}):\n"
    ]
    for i, dest in enumerate(top, 1):
        daily = dest["estimated_daily_cost_usd"]
        total = daily * trip_length_days
        lines.append(
            f"{i}. {dest['name']}, {dest['country']}\n"
            f"   Best for: {', '.join(dest['best_for'][:4])}\n"
            f"   Estimated cost ({trip_length_days} days): ${total:,} (~${daily}/day)\n"
            f"   Best time to visit: {', '.join(dest['best_months'][:3])}\n"
            f"   Highlights: {', '.join(dest['highlights'][:3])}\n"
        )
    return "\n".join(lines)
