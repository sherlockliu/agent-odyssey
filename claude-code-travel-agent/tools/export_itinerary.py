"""Export a trip itinerary to a text file on the user's Desktop."""

import json
from pathlib import Path

from config import TRIPS_DIR


def export_itinerary(trip_id: str) -> str:
    """
    Format the itinerary and write it to ~/Desktop/{trip_id}_itinerary.txt.
    Returns plain text confirming the export path, or an error message.
    """
    path = TRIPS_DIR / f"{trip_id}.json"
    if not path.exists():
        return f"No itinerary found for trip '{trip_id}'. Nothing to export."

    data = json.loads(path.read_text())
    items = data.get("itinerary", [])
    budget = data.get("budget", {})

    destination = data.get("destination", "Unknown destination")
    dates = data.get("dates", {})
    date_range = ""
    if dates.get("start") and dates.get("end"):
        date_range = f" | {dates['start']} → {dates['end']}"

    lines = [
        "═" * 50,
        f"  TRIP: {destination.upper()}{date_range}",
        f"  Trip ID: {trip_id}",
        "═" * 50,
        "",
    ]

    if items:
        by_type: dict[str, list] = {}
        for item in items:
            t = item.get("type", "other").upper()
            by_type.setdefault(t, []).append(item)

        total_cost = 0.0
        for item_type, group in by_type.items():
            lines.append(item_type)
            for item in group:
                cost = item.get("est_cost", 0)
                total_cost += cost
                name = item.get("name", item.get("id", "Unknown"))
                notes = f" — {item['notes']}" if item.get("notes") else ""
                lines.append(f"  ✓ {name}{notes}  (est. ${cost:,.0f})")
            lines.append("")

        lines.append("BUDGET SUMMARY")
        budget_total = budget.get("total", 0)
        if budget_total:
            remaining = budget_total - total_cost
            lines.append(f"  Total budget:     ${budget_total:,.0f}")
            lines.append(f"  Estimated spend:  ${total_cost:,.0f}")
            lines.append(f"  Remaining:        ${remaining:,.0f}")
        else:
            lines.append(f"  Estimated spend:  ${total_cost:,.0f}")
        lines.append("")
    else:
        lines.append("(No items in itinerary yet.)")
        lines.append("")

    lines.append("NOTE: All prices are estimates. Book directly to confirm.")
    lines.append("═" * 50)

    content = "\n".join(lines)

    # Write to Desktop
    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    out_path = desktop / f"{trip_id}_itinerary.txt"
    out_path.write_text(content, encoding="utf-8")

    return f"Itinerary exported to: {out_path}\n\n{content}"
