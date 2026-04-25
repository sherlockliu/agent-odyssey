"""LLM-powered fallback data generator.

When the local dummy_data JSON files have no matching records, these functions
ask the active LLM to invent plausible travel data so the PoC user flow
continues without breaking.

The generated text matches the exact format that the real tools produce,
so the agent can interpret the results identically.
"""

from __future__ import annotations

_client = None  # module-level lazy singleton


def _get_client():
    global _client
    if _client is None:
        from config import LLM_PROVIDER, LLM_MODEL, LLM_PROVIDER_CONFIGS
        from llm import create_client
        cfg = LLM_PROVIDER_CONFIGS.get(LLM_PROVIDER, {})
        _client = create_client(LLM_PROVIDER, LLM_MODEL, **cfg)
    return _client


def _chat(prompt: str) -> str:
    client = _get_client()
    response = client.chat(
        messages=[{"role": "user", "content": prompt}],
        tools=None,
    )
    return response.content.strip()


def _rough_nights(check_in: str, check_out: str) -> int:
    try:
        from datetime import datetime
        return max(1, (datetime.strptime(check_out, "%Y-%m-%d") -
                       datetime.strptime(check_in, "%Y-%m-%d")).days)
    except Exception:
        return 1


def generate_flight_results(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
    passengers: int,
    max_price: float,
) -> str:
    """Ask the LLM to invent 3 plausible flights for a route not in the mock data."""
    budget_note = f" with a max budget of £{max_price:.0f}/person" if max_price < 9999 else ""
    return_note = f", returning {return_date}" if return_date else ""
    prompt = (
        f"Generate 3 realistic flight options from {origin} to {destination}, "
        f"departing {departure_date}{return_note}, {passengers} passenger(s){budget_note}.\n"
        f"Format EXACTLY like this (no extra text):\n\n"
        f"1. [Airline] [FlightNum]\n"
        f"   Departs: {departure_date} at HH:MM AM/PM (nonstop or N stop(s))\n"
        f"   Returns: {(return_date + ' ') if return_date else ''}HH:MM → HH:MM (nonstop)\n"
        f"   Price: £NNN/person × {passengers} = £NNN total\n"
        f"   Flight ID: XX-NNN-{origin.upper()}-{destination.upper()}\n\n"
        f"Use realistic airlines for this route and plausible prices."
    )
    try:
        text = _chat(prompt)
        header = (
            f"Found 3 flight option(s) from {origin.upper()} to {destination.upper()}"
            f"{budget_note} [AI-generated — add to dummy_data/flights.json to persist]:\n\n"
        )
        return header + text
    except Exception as exc:
        return (
            f"No flights found from {origin.upper()} to {destination.upper()}{budget_note}.\n"
            f"(AI fallback also failed: {exc})"
        )


def generate_hotel_results(
    city: str,
    check_in: str,
    check_out: str,
    guests: int,
    max_price_per_night: float,
) -> str:
    """Ask the LLM to invent 3 plausible hotels for a city not in the mock data."""
    num_nights = _rough_nights(check_in, check_out)
    budget_note = f" under £{max_price_per_night:.0f}/night" if max_price_per_night < 9999 else ""
    prompt = (
        f"Generate 3 realistic hotel options in {city} for {guests} guest(s), "
        f"check-in {check_in}, check-out {check_out} ({num_nights} nights){budget_note}.\n"
        f"Format EXACTLY like this (no extra text):\n\n"
        f"1. [Hotel Name] (N★) — Rating: N.N/10\n"
        f"   [Neighborhood] — [Chain or Independent]\n"
        f"   £NNN/night × {num_nights} = £NNN total\n"
        f"   Amenities: amenity1, amenity2, amenity3\n"
        f"   [One-sentence description]\n"
        f"   Hotel ID: hyphenated-id\n\n"
        f"Use real neighborhoods in {city} and plausible prices."
    )
    try:
        text = _chat(prompt)
        header = (
            f"Found 3 hotel option(s) in {city} "
            f"({check_in} → {check_out}, {num_nights} night(s))"
            f"{budget_note} [AI-generated — add to dummy_data/hotels.json to persist]:\n\n"
        )
        return header + text
    except Exception as exc:
        return (
            f"No hotels found in {city}{budget_note}.\n"
            f"(AI fallback also failed: {exc})"
        )


def generate_activity_results(city: str, interests: list[str]) -> str:
    """Ask the LLM to invent 5 plausible activities for a city not in the mock data."""
    interest_note = f" focused on: {', '.join(interests)}" if interests else ""
    prompt = (
        f"Generate 5 realistic things to do in {city}{interest_note}.\n"
        f"Format EXACTLY like this (no extra text):\n\n"
        f"1. [Activity Name]  [[Category]]\n"
        f"   [One-sentence description]\n"
        f"   Price: £NN or Free  •  Duration: Nh  •  Tags: tag1, tag2, tag3\n\n"
        f"Use real attractions and plausible prices."
    )
    try:
        text = _chat(prompt)
        header = (
            f"Things to do in {city.title()}{interest_note} "
            f"[AI-generated — add to dummy_data/activities.json to persist]:\n\n"
        )
        return header + text
    except Exception as exc:
        return (
            f"No activities found for '{city}'.\n"
            f"(AI fallback also failed: {exc})"
        )
