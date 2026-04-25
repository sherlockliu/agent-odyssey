"""Built-in travel tool provider — wraps the original 8 travel-planning tools."""

from __future__ import annotations

from ..provider import ToolProvider


class BuiltinToolProvider(ToolProvider):
    """
    Wraps the original 8 built-in tools using relative imports to avoid any
    circular import issue with tools/__init__.py.
    """

    def __init__(self) -> None:
        # Relative imports resolve to the sibling modules (tools/search_*.py etc.)
        # without going through tools/__init__.py — safe during __init__.py init.
        from ..search_destinations import search_destinations
        from ..search_flights import search_flights
        from ..search_hotels import search_hotels
        from ..view_itinerary import view_itinerary
        from ..update_itinerary import update_itinerary
        from ..save_context import save_context, load_context
        from ..export_itinerary import export_itinerary
        from ..update_profile import get_profile, update_profile, confirm_profile_update, discard_profile_update

        self._registry: dict = {
            "search_destinations": search_destinations,
            "search_flights": search_flights,
            "search_hotels": search_hotels,
            "view_itinerary": view_itinerary,
            "update_itinerary": update_itinerary,
            "save_context": save_context,
            "load_context": load_context,
            "export_itinerary": export_itinerary,
            "get_profile": get_profile,
            "update_profile": update_profile,
            "confirm_profile_update": confirm_profile_update,
            "discard_profile_update": discard_profile_update,
        }

    def get_definitions(self) -> list[dict]:
        return _BUILTIN_TOOL_DEFINITIONS

    def can_handle(self, name: str) -> bool:
        return name in self._registry

    def execute(self, name: str, arguments: dict) -> str:
        fn = self._registry.get(name)
        if fn is None:
            return f"Error: '{name}' not found in builtin tools"
        try:
            return fn(**arguments)
        except TypeError as exc:
            return f"Error calling tool '{name}': {exc}"
        except Exception as exc:
            return f"Tool '{name}' failed: {exc}"


# ---------------------------------------------------------------------------
# Tool definitions (moved here from tools/__init__.py for modularity)
# ---------------------------------------------------------------------------

_BUILTIN_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_destinations",
            "description": "Recommend travel destinations based on user interests, budget, and trip length.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interests": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of interests, e.g. ['museums', 'food', 'beaches']",
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Budget level for the trip",
                    },
                    "trip_length_days": {
                        "type": "integer",
                        "description": "Number of days for the trip",
                    },
                },
                "required": ["interests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search available flights between two cities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin airport code, e.g. SFO",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination airport code, e.g. JFK",
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD format",
                    },
                    "return_date": {
                        "type": "string",
                        "description": "Return date in YYYY-MM-DD format (optional)",
                    },
                    "passengers": {
                        "type": "integer",
                        "description": "Number of passengers",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price per person in USD",
                    },
                },
                "required": ["origin", "destination", "departure_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search available hotels in a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'New York'",
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format",
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format",
                    },
                    "guests": {
                        "type": "integer",
                        "description": "Number of guests",
                    },
                    "max_price_per_night": {
                        "type": "number",
                        "description": "Maximum price per night in USD",
                    },
                    "chain": {
                        "type": "string",
                        "description": "Preferred hotel chain (optional), e.g. 'Hilton'",
                    },
                },
                "required": ["city", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_itinerary",
            "description": "View the current trip itinerary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {
                        "type": "string",
                        "description": "Trip ID to view",
                    },
                },
                "required": ["trip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_itinerary",
            "description": "Add or remove items from the trip itinerary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {
                        "type": "string",
                        "description": "Trip ID to update",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "clear"],
                        "description": "Action to perform",
                    },
                    "items": {
                        "type": "array",
                        "description": "Items to add/remove",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "name": {"type": "string"},
                                "est_cost": {"type": "number"},
                                "notes": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["trip_id", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_context",
            "description": "Save the current trip context to disk for later resumption.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                    "destination": {"type": "string"},
                    "dates": {"type": "object"},
                    "budget_total": {"type": "number"},
                    "notes": {"type": "string"},
                },
                "required": ["trip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_context",
            "description": "Load a previously saved trip context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {"type": "string"},
                },
                "required": ["trip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_itinerary",
            "description": "Export the trip itinerary to a text file on the user's Desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trip_id": {
                        "type": "string",
                        "description": "Trip ID to export",
                    },
                },
                "required": ["trip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description": "Read the current user profile (preferences, home airport, budget defaults).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": (
                "Update a user profile field. "
                "Use source='explicit' when the user directly commands it. "
                "Use source='inferred' when you detect a preference from conversation — "
                "the tool will stage the value and return a confirmation prompt to ask the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": (
                            "Profile field: home_airport, name, seat_preference, "
                            "preferred_airlines, preferred_hotel_chains, interests, avoid, "
                            "flight_max_usd, hotel_max_per_night_usd"
                        ),
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to set. For list fields, use comma-separated strings.",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["explicit", "inferred"],
                        "description": "'explicit' saves immediately; 'inferred' stages for confirmation.",
                    },
                },
                "required": ["field", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_profile_update",
            "description": "Commit a staged profile value after the user says yes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "The field that was staged by a previous update_profile(source='inferred') call.",
                    },
                },
                "required": ["field"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discard_profile_update",
            "description": "Discard a staged profile value after the user says no.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "The field to discard.",
                    },
                },
                "required": ["field"],
            },
        },
    },
]
