"""Tool registry and dispatcher.

Public surface (dispatch_tool / get_tool_definitions) is unchanged.
Internally, calls are routed through a ToolRegistry populated from
ENABLED_TOOL_PROVIDERS in config.py so new providers can be added
without touching agent.py or this file.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Keep direct function imports and TOOL_REGISTRY for backward compatibility.
# External code or tests that import these directly still work.
# ---------------------------------------------------------------------------
from .search_destinations import search_destinations
from .search_flights import search_flights
from .search_hotels import search_hotels
from .view_itinerary import view_itinerary
from .update_itinerary import update_itinerary
from .save_context import save_context, load_context
from .export_itinerary import export_itinerary

TOOL_REGISTRY = {
    "search_destinations": search_destinations,
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "view_itinerary": view_itinerary,
    "update_itinerary": update_itinerary,
    "save_context": save_context,
    "load_context": load_context,
    "export_itinerary": export_itinerary,
}


# ---------------------------------------------------------------------------
# Build the extensible ToolRegistry from config.
# ---------------------------------------------------------------------------

def _build_registry():
    from tools.registry import ToolRegistry
    from config import ENABLED_TOOL_PROVIDERS

    registry = ToolRegistry()
    for provider_name in ENABLED_TOOL_PROVIDERS:
        if provider_name == "builtin":
            from tools.providers.builtin import BuiltinToolProvider
            registry.register(BuiltinToolProvider())
        elif provider_name == "weather":
            from tools.providers.weather import WeatherToolProvider
            from config import WEATHER_CONFIG
            registry.register(WeatherToolProvider(WEATHER_CONFIG))
        elif provider_name == "activities":
            from tools.providers.activities import ActivitiesToolProvider
            from config import ACTIVITIES_CONFIG
            registry.register(ActivitiesToolProvider(ACTIVITIES_CONFIG))
        elif provider_name == "online_destinations":
            from tools.providers.online_destinations import OnlineDestinationProvider
            from config import ONLINE_DESTINATIONS_CONFIG
            registry.register(OnlineDestinationProvider(ONLINE_DESTINATIONS_CONFIG))
    return registry


_registry = _build_registry()


def dispatch_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call through the ToolRegistry. Returns plain text result."""
    return _registry.dispatch(name, arguments)


def _legacy_dispatch_tool(name: str, arguments: dict) -> str:
    """Original dispatch_tool kept for reference — not called by agent."""
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(TOOL_REGISTRY.keys())}"
    try:
        return fn(**arguments)
    except TypeError as e:
        return f"Error calling tool '{name}': {e}"
    except Exception as e:
        return f"Tool '{name}' failed: {e}"



def get_tool_definitions() -> list[dict]:
    """Return all tool definitions from all registered providers."""
    return _registry.get_all_definitions()
