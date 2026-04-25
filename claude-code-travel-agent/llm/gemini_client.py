"""Google Gemini LLM client adapter.

Uses Gemini's OpenAI-compatible endpoint, so it reuses OpenAIClient and avoids
an extra google-generativeai dependency.
Reference: https://ai.google.dev/gemini-api/docs/openai
"""

from __future__ import annotations

import copy
import os

from .openai_client import OpenAIClient
from .base import LLMResponse

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

_CONTEXT_WINDOWS: dict[str, int] = {
    "gemini-2.5-flash":         1_000_000,
    "gemini-2.5-pro":           1_000_000,
    "gemini-2.0-flash":         1_000_000,
    "gemini-2.0-flash-lite":    1_000_000,
}
_DEFAULT_CONTEXT_WINDOW = 1_000_000


def _guess_context_window(model: str) -> int:
    model_lower = model.lower()
    for prefix, size in _CONTEXT_WINDOWS.items():
        if model_lower.startswith(prefix):
            return size
    return _DEFAULT_CONTEXT_WINDOW


class GeminiClient(OpenAIClient):
    """
    Gemini via its OpenAI-compatible REST endpoint.
    Inherits all logic from OpenAIClient; only the base_url, provider label, and
    context window lookup are overridden.
    """

    def __init__(self, model: str, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY") or ""
        super().__init__(
            model=model,
            api_key=resolved_key,
            base_url=_GEMINI_BASE_URL,
            provider="gemini",
        )
        # Override context window with Gemini-specific lookup.
        self._context_window = _guess_context_window(model)

    @property
    def provider_name(self) -> str:
        return "gemini"

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> "LLMResponse":  # type: ignore[override]
        """Sanitize tool schemas before sending — Gemini rejects empty 'required' arrays."""
        sanitized_tools: list[dict] | None = None
        if tools:
            sanitized_tools = []
            for tool in tools:
                t = copy.deepcopy(tool)
                params = t.get("function", {}).get("parameters", {})
                # Remove empty 'required' list — Gemini errors on []
                if "required" in params and params["required"] == []:
                    del params["required"]
                sanitized_tools.append(t)
        return super().chat(messages=messages, tools=sanitized_tools)
