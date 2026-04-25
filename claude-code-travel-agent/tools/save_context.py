"""Save and load trip context to/from disk."""

import json
from datetime import datetime
from pathlib import Path

from config import TRIPS_DIR


def save_context(
    trip_id: str,
    destination: str = "",
    dates: dict | None = None,
    budget_total: float = 0,
    notes: str = "",
) -> str:
    """Save or update trip planning context. Returns plain text confirmation."""

    TRIPS_DIR.mkdir(parents=True, exist_ok=True)
    path = TRIPS_DIR / f"{trip_id}.json"

    # Load existing or start fresh
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {
            "trip_id": trip_id,
            "created_at": datetime.now().isoformat(),
            "itinerary": [],
            "budget": {"total": 0},
        }

    if destination:
        data["destination"] = destination
    if dates:
        data["dates"] = dates
    if budget_total:
        data.setdefault("budget", {})["total"] = budget_total
    if notes:
        data["notes"] = notes

    data["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(data, indent=2))

    return (
        f"Trip context saved: {trip_id}\n"
        f"  Destination: {data.get('destination', 'not set')}\n"
        f"  Dates: {data.get('dates', {})}\n"
        f"  Budget: ${data.get('budget', {}).get('total', 0):,.0f}\n"
        f"  Saved to: {path}"
    )


def load_context(trip_id: str) -> str:
    """Load trip context from disk. Returns plain text summary."""

    path = TRIPS_DIR / f"{trip_id}.json"
    if not path.exists():
        return f"No saved context found for trip '{trip_id}'."

    data = json.loads(path.read_text())
    items = data.get("itinerary", [])
    total_est = sum(i.get("est_cost", 0) for i in items)

    lines = [
        f"Loaded trip context: {trip_id}",
        f"  Destination: {data.get('destination', 'not set')}",
        f"  Dates: {data.get('dates', {})}",
        f"  Budget: ${data.get('budget', {}).get('total', 0):,.0f}",
        f"  Itinerary items: {len(items)} (est. ${total_est:,.0f})",
    ]
    if data.get("notes"):
        lines.append(f"  Notes: {data['notes']}")
    return "\n".join(lines)
