"""Tool registry — aggregates multiple ToolProviders behind a single dispatch surface."""

from __future__ import annotations

from .provider import ToolProvider


class ToolRegistry:
    """
    Holds a list of ToolProviders and routes tool calls to the right one.

    Providers are checked in registration order; the first provider that
    reports can_handle(name) == True is used. This means builtin tools have
    priority by default, and external providers can be appended to extend
    the tool surface without touching existing code.
    """

    def __init__(self) -> None:
        self._providers: list[ToolProvider] = []

    def register(self, provider: ToolProvider) -> None:
        """Append a provider. Later-registered providers have lower priority."""
        self._providers.append(provider)

    def get_all_definitions(self) -> list[dict]:
        """Return the merged list of tool definitions from all providers."""
        defs: list[dict] = []
        for provider in self._providers:
            defs.extend(provider.get_definitions())
        return defs

    def dispatch(self, name: str, arguments: dict) -> str:
        """
        Route a tool call to the owning provider and return the plain text result.
        Returns an error string (never raises) if no provider handles the tool.
        """
        for provider in self._providers:
            if provider.can_handle(name):
                try:
                    return provider.execute(name, arguments)
                except Exception as exc:
                    return f"Tool '{name}' failed unexpectedly: {exc}"

        available = self.list_tool_names()
        return (
            f"Error: unknown tool '{name}'. "
            f"Available tools: {', '.join(available)}"
        )

    def list_tool_names(self) -> list[str]:
        """Return a flat list of all registered tool names."""
        return [
            defn["function"]["name"]
            for provider in self._providers
            for defn in provider.get_definitions()
        ]
