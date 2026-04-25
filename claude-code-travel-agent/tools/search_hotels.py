"""Search available hotels using dummy data."""

import json
from datetime import datetime
from pathlib import Path

from config import DUMMY_DATA_DIR

_HOTELS = json.loads((DUMMY_DATA_DIR / "hotels.json").read_text())


def _nights(check_in: str, check_out: str) -> int:
    try:
        fmt = "%Y-%m-%d"
        return max(1, (datetime.strptime(check_out, fmt) - datetime.strptime(check_in, fmt)).days)
    except ValueError:
        return 1


def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
    max_price_per_night: float = 9999,
    chain: str = "",
) -> str:
    """Search hotels in a city. Returns plain text results."""

    city_lower = city.lower()
    matches = [
        h for h in _HOTELS
        if city_lower in h["city"].lower()
        and h["price_per_night"] <= max_price_per_night
        and (not chain or chain.lower() in h["chain"].lower())
    ]

    if not matches:
        # No mock data for this city — ask the LLM to generate plausible options.
        from tools.llm_fallback import generate_hotel_results
        return generate_hotel_results(
            city, check_in, check_out, guests, max_price_per_night
        )

    matches.sort(key=lambda h: (-h["rating"], h["price_per_night"]))
    num_nights = _nights(check_in, check_out)

    lines = [
        f"Found {len(matches)} hotel(s) in {city} "
        f"({check_in} → {check_out}, {num_nights} night(s)):\n"
    ]
    for i, hotel in enumerate(matches[:5], 1):
        total = hotel["price_per_night"] * num_nights
        chain_note = f" — {hotel['chain']} loyalty eligible" if hotel["chain"] != "Independent" else ""
        lines.append(
            f"{i}. {hotel['name']} ({hotel['stars']}★) — Rating: {hotel['rating']}/10\n"
            f"   {hotel['neighborhood']}{chain_note}\n"
            f"   ${hotel['price_per_night']}/night × {num_nights} = ${total:,} total\n"
            f"   Amenities: {', '.join(hotel['amenities'][:4])}\n"
            f"   {hotel['description']}\n"
            f"   Hotel ID: {hotel['id']}\n"
        )

    lines.append("Note: Prices are estimates from dummy data. Verify with hotel before booking.")
    return "\n".join(lines)
