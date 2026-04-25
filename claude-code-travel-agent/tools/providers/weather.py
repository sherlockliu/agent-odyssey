"""Weather tool provider.

Provides `get_weather(city, date_range)` to the agent.

Mode selection (set in config.py WEATHER_CONFIG):
  "mock" — returns canned data; no network calls, no API key needed.
  "api"  — calls Open-Meteo (https://open-meteo.com/), which is free and
            requires no API key. Set WEATHER_API_KEY in config if you switch
            to a paid provider (e.g. WeatherAPI.com).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from ..provider import ToolProvider


# ---------------------------------------------------------------------------
# Mock data — a representative sample for common travel destinations.
# ---------------------------------------------------------------------------

_MOCK_WEATHER: dict[str, dict] = {
    "tokyo": {
        "current": "Partly cloudy, 18°C (64°F)",
        "forecast": "Mild spring weather. Light rain expected mid-week.",
        "humidity": "62%",
        "best_for": "cherry blossoms (late March–April), moderate crowds",
    },
    "paris": {
        "current": "Overcast, 14°C (57°F)",
        "forecast": "Cool with occasional showers. Pack a light jacket.",
        "humidity": "75%",
        "best_for": "mild sightseeing weather, fewer tourists than summer",
    },
    "new york": {
        "current": "Sunny, 12°C (54°F)",
        "forecast": "Clear skies through the weekend, cooler evenings.",
        "humidity": "55%",
        "best_for": "comfortable walking weather, spring blossoms",
    },
    "bali": {
        "current": "Hot and humid, 31°C (88°F)",
        "forecast": "Tropical showers in the afternoon, sunny mornings.",
        "humidity": "85%",
        "best_for": "beach and temple visits; bring rain gear for afternoons",
    },
    "london": {
        "current": "Drizzling, 11°C (52°F)",
        "forecast": "Typical British weather — mix of sun and showers.",
        "humidity": "80%",
        "best_for": "museum visits; outdoor parks between showers",
    },
    "sydney": {
        "current": "Warm and sunny, 24°C (75°F)",
        "forecast": "Lovely autumn weather. Cool evenings approaching.",
        "humidity": "60%",
        "best_for": "beach walks, harbour cruises, outdoor dining",
    },
    "amsterdam": {
        "current": "Cool and windy, 10°C (50°F)",
        "forecast": "Breezy with sunny spells. Tulip season begins.",
        "humidity": "72%",
        "best_for": "cycling, canal tours, Keukenhof tulip gardens nearby",
    },
    "bangkok": {
        "current": "Hot and sunny, 34°C (93°F)",
        "forecast": "Dry season. Very hot; stay hydrated.",
        "humidity": "65%",
        "best_for": "temple visits in the morning, indoor attractions midday",
    },
    "rome": {
        "current": "Mild and sunny, 20°C (68°F)",
        "forecast": "Beautiful spring weather, ideal for sightseeing.",
        "humidity": "50%",
        "best_for": "outdoor ruins, gelato, early morning Colosseum visits",
    },
    "barcelona": {
        "current": "Warm and sunny, 22°C (72°F)",
        "forecast": "Excellent weather all week. Light breeze off the sea.",
        "humidity": "55%",
        "best_for": "beach, Sagrada Família, open-air dining",
    },
}

_FALLBACK_WEATHER = {
    "current": "Weather data not available for this city in mock mode.",
    "forecast": "Enable API mode or add mock data for this city.",
    "humidity": "N/A",
    "best_for": "Check a local weather service for accurate conditions.",
}


def _mock_get_weather(city: str, date_range: str = "") -> str:
    key = city.lower().strip()
    data = _MOCK_WEATHER.get(key, _FALLBACK_WEATHER)
    range_note = f" during {date_range}" if date_range else ""
    return (
        f"Weather for {city.title()}{range_note}:\n"
        f"  Current conditions : {data['current']}\n"
        f"  Forecast           : {data['forecast']}\n"
        f"  Humidity           : {data['humidity']}\n"
        f"  Travel tip         : {data['best_for']}\n"
        f"\n[Data source: mock — set WEATHER_MODE=api for live forecasts]"
    )


def _api_get_weather(city: str, date_range: str = "", api_url: str = "") -> str:
    """
    Fetch weather from Open-Meteo (free, no key).
    Uses geocoding to resolve city name → lat/lon, then gets the forecast.
    Falls back to mock data on any error.
    """
    try:
        import urllib.request
        import urllib.parse

        # Step 1: Geocode city name.
        geo_params = urllib.parse.urlencode({"name": city, "count": 1, "format": "json"})
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?{geo_params}"
        with urllib.request.urlopen(geo_url, timeout=5) as resp:  # noqa: S310
            geo_data = json.loads(resp.read())

        results = geo_data.get("results", [])
        if not results:
            return _mock_get_weather(city, date_range)

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        city_name = results[0].get("name", city)

        # Step 2: Fetch forecast.
        today = date.today()
        end = today + timedelta(days=7)
        wx_params = urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
            "temperature_unit": "celsius",
            "start_date": today.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "auto",
            "format": "json",
        })
        wx_url = f"{api_url or 'https://api.open-meteo.com/v1/forecast'}?{wx_params}"
        with urllib.request.urlopen(wx_url, timeout=5) as resp:  # noqa: S310
            wx_data = json.loads(resp.read())

        daily = wx_data.get("daily", {})
        temps_max = daily.get("temperature_2m_max", [])
        temps_min = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_probability_max", [])
        dates_ = daily.get("time", [])

        lines = [f"7-day weather forecast for {city_name}:"]
        for i, d in enumerate(dates_[:7]):
            hi = f"{temps_max[i]:.0f}" if i < len(temps_max) else "?"
            lo = f"{temps_min[i]:.0f}" if i < len(temps_min) else "?"
            rain = f"{precip[i]}%" if i < len(precip) else "?"
            lines.append(f"  {d}: {lo}–{hi}°C, rain chance {rain}")
        return "\n".join(lines)

    except Exception as exc:
        return _mock_get_weather(city, date_range) + f"\n[API call failed: {exc}]"


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------

class WeatherToolProvider(ToolProvider):
    """Provides real-time or mock weather data to the travel agent."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self._mode = cfg.get("mode", "mock")
        self._api_key = cfg.get("api_key")
        self._api_url = cfg.get("api_url", "https://api.open-meteo.com/v1/forecast")

    def get_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": (
                        "Get current weather conditions and a 7-day forecast for a city. "
                        "Use this when the user asks about weather, climate, or best time to visit."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "City name, e.g. 'Tokyo' or 'New York'",
                            },
                            "date_range": {
                                "type": "string",
                                "description": "Optional date range, e.g. 'April 5–12' or '2026-04-05 to 2026-04-12'",
                            },
                        },
                        "required": ["city"],
                    },
                },
            }
        ]

    def can_handle(self, name: str) -> bool:
        return name == "get_weather"

    def execute(self, name: str, arguments: dict) -> str:
        if name != "get_weather":
            return f"Error: WeatherToolProvider cannot handle '{name}'"
        city = arguments.get("city", "")
        if not city:
            return "Error: 'city' argument is required for get_weather"
        date_range = arguments.get("date_range", "")
        if self._mode == "api":
            return _api_get_weather(city, date_range, self._api_url)
        return _mock_get_weather(city, date_range)
