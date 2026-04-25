"""Search available flights using dummy data."""

import json
from pathlib import Path

from config import DUMMY_DATA_DIR

_FLIGHTS = json.loads((DUMMY_DATA_DIR / "flights.json").read_text())


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    passengers: int = 1,
    max_price: float = 9999,
) -> str:
    """Search flights between two cities. Returns plain text results."""

    matches = [
        f for f in _FLIGHTS
        if f["origin"].upper() == origin.upper()
        and f["destination"].upper() == destination.upper()
        and f["price"] * passengers <= max_price
    ]

    if not matches:
        # No mock data for this route — ask the LLM to generate plausible options.
        from tools.llm_fallback import generate_flight_results
        return generate_flight_results(
            origin, destination, departure_date, return_date, passengers, max_price
        )

    matches.sort(key=lambda f: f["price"])

    budget_note = f" (max ${max_price:.0f}/person)" if max_price < 9999 else ""
    lines = [
        f"Found {len(matches)} flight(s) from {origin.upper()} to {destination.upper()}{budget_note}:\n"
    ]
    for i, flight in enumerate(matches[:5], 1):
        total = flight["price"] * passengers
        pax_note = f" × {passengers} = ${total:,} total" if passengers > 1 else ""
        lines.append(
            f"{i}. {flight['airline']} {flight['flight_number']}\n"
            f"   Departs: {departure_date} at {flight['departure_time']} ({flight['stops']})\n"
            f"   Returns: {return_date + ' ' if return_date else ''}{flight['return_time']}\n"
            f"   Price: ${flight['price']}/person{pax_note}\n"
            f"   Flight ID: {flight['id']}\n"
        )

    lines.append("Note: Prices are estimates from dummy data. Verify with airline before booking.")
    return "\n".join(lines)
