"""OpenAI-compatible LLM client adapter.

Covers: OpenAI, Groq, Together.ai, and any other OpenAI-compatible endpoint.
Set `base_url` to point at an alternative host; the protocol is identical.
"""

from __future__ import annotations

import json
from typing import Any

from .base import LLMClient, LLMResponse, ToolCall

_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o":          128000,
    "gpt-4-turbo":     128000,
    "gpt-4":             8192,
    "gpt-3.5-turbo":   16385,
    "o1":              128000,
    "o3":              200000,
    "llama-3.3":       131072,
    "llama-3.1":        32768,
    "mixtral":          32768,
    "gemma2":            8192,
}
_DEFAULT_CONTEXT_WINDOW = 32768


def _guess_context_window(model: str) -> int:
    model_lower = model.lower()
    for prefix, size in _CONTEXT_WINDOWS.items():
        if model_lower.startswith(prefix):
            return size
    return _DEFAULT_CONTEXT_WINDOW


class OpenAIClient(LLMClient):
    """Adapter for OpenAI-compatible APIs."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        provider: str = "openai",
    ) -> None:
        try:
            import openai as _openai
        except ImportError as exc:
            raise ImportError(
                "openai package is required. "
                "Install with: pip install 'claude-code-travel-agent[openai]'"
            ) from exc

        self._client = _openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._provider = provider
        self._context_window = _guess_context_window(model)

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        # OpenAI is the canonical format. Only normalise the 'tool' role messages
        # to include `tool_call_id` (OpenAI requires this field).
        normalised = []
        for msg in messages:
            if msg.get("role") == "tool":
                normalised.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id") or msg.get("name", ""),
                    "content": msg.get("content", ""),
                })
            else:
                normalised.append(msg)

        kwargs: dict[str, Any] = {"model": self._model, "messages": normalised}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message
        content = msg.content or ""

        tool_calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(ToolCall(name=tc.function.name, arguments=args, id=tc.id))

        usage: dict = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(content=content, tool_calls=tool_calls, usage=usage)
