"""Abstract base class for tool providers.

Mirrors the Claude Code "uniform tool interface" pattern:
  JSON in → plain text out, no exceptions (errors returned as strings).

Each provider is a self-contained group of tools. New external services
(weather APIs, activity databases, booking engines, etc.) are added by
implementing this interface and registering the provider in config.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolProvider(ABC):
    """
    A self-contained collection of related tools.

    Providers are registered in ToolRegistry. The registry presents a flat
    surface to the agent — it calls dispatch() and get_all_definitions()
    without knowing which provider owns which tool.
    """

    @abstractmethod
    def get_definitions(self) -> list[dict]:
        """Return OpenAI-style tool definition dicts for all tools in this provider."""
        ...

    @abstractmethod
    def can_handle(self, name: str) -> bool:
        """Return True if this provider owns the tool with the given name."""
        ...

    @abstractmethod
    def execute(self, name: str, arguments: dict) -> str:
        """
        Execute the named tool and return a plain text result.
        Must never raise — return error descriptions as plain text strings.
        """
        ...
