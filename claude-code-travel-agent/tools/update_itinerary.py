"""Add, remove, or clear items in the trip itinerary."""

import json
from pathlib import Path

from config import TRIPS_DIR


def _load(trip_id: str) -> dict:
    path = TRIPS_DIR / f"{trip_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "trip_id": trip_id,
        "destination": None,
        "dates": {},
        "budget": {"total": 0},
        "itinerary": [],
    }


def _save(trip_id: str, data: dict) -> None:
    TRIPS_DIR.mkdir(parents=True, exist_ok=True)
    (TRIPS_DIR / f"{trip_id}.json").write_text(json.dumps(data, indent=2))


def update_itinerary(
    trip_id: str,
    action: str,
    items: list[dict] | None = None,
) -> str:
    """Modify the trip itinerary. Returns plain text confirmation."""

    data = _load(trip_id)
    current = data.get("itinerary", [])

    if action == "clear":
        data["itinerary"] = []
        _save(trip_id, data)
        return f"Itinerary for '{trip_id}' cleared."

    if action == "add":
        if not items:
            return "Error: 'add' action requires items."

        # Budget guard: warn before adding if it would overspend
        budget_total = data.get("budget", {}).get("total", 0)
        if budget_total:
            existing_spend = sum(i.get("est_cost", 0) for i in current)
            new_spend = sum(i.get("est_cost", 0) for i in items)
            remaining_before = budget_total - existing_spend
            if new_spend > remaining_before:
                names = ", ".join(i.get("name", i.get("id", "?")) for i in items)
                return (
                    f"⚠  Budget warning: adding {names} (est. ${new_spend:,.0f}) "
                    f"would exceed your remaining budget (${remaining_before:,.0f}).\n"
                    f"Options: pick a cheaper alternative, shorten your stay, or increase your budget."
                )

        for item in items:
            current.append(item)
        data["itinerary"] = current
        _save(trip_id, data)

        total_est = sum(i.get("est_cost", 0) for i in current)
        added_names = ", ".join(i.get("name", i.get("id", "?")) for i in items)

        lines = [
            f"Added to itinerary: {added_names}",
            f"",
            f"Current itinerary ({len(current)} items):",
        ]
        for item in current:
            name = item.get("name", item.get("id", "Unknown"))
            cost = item.get("est_cost", 0)
            lines.append(f"  ✓ {name}  (est. ${cost:,.0f})")

        lines.append(f"")
        lines.append(f"Estimated total: ${total_est:,.0f}")
        if budget_total:
            remaining = budget_total - total_est
            lines.append(f"Remaining budget: ${remaining:,.0f} of ${budget_total:,.0f}")
        return "\n".join(lines)

    if action == "remove":
        if not items:
            return "Error: 'remove' action requires items."
        remove_names = {i.get("name", i.get("id", "")).lower() for i in items}
        before = len(current)
        current = [
            i for i in current
            if i.get("name", i.get("id", "")).lower() not in remove_names
        ]
        removed = before - len(current)
        data["itinerary"] = current
        _save(trip_id, data)
        return f"Removed {removed} item(s) from itinerary. {len(current)} items remaining."

    return f"Unknown action '{action}'. Use 'add', 'remove', or 'clear'."
