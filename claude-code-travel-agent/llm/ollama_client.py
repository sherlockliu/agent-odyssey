"""Ollama LLM client adapter."""

from __future__ import annotations

import ollama

from .base import LLMClient, LLMResponse, ToolCall

# Approximate context windows keyed by model name prefix.
_CONTEXT_WINDOWS: dict[str, int] = {
    "qwen3":     32000,
    "qwen2.5":   32000,
    "llama3.3": 131072,
    "llama3.2":   4096,
    "llama3.1":   8192,
    "llama3":     8192,
    "gemma3":    32000,
    "mistral":   32000,
    "phi4":      16000,
    "deepseek":  65536,
}
_DEFAULT_CONTEXT_WINDOW = 32000


def _guess_context_window(model: str) -> int:
    model_lower = model.lower()
    for prefix, size in _CONTEXT_WINDOWS.items():
        if model_lower.startswith(prefix):
            return size
    return _DEFAULT_CONTEXT_WINDOW


class OllamaClient(LLMClient):
    """Thin adapter around the ollama Python client."""

    def __init__(self, model: str, host: str = "http://localhost:11434") -> None:
        self._model = model
        self._host = host
        self._context_window = _guess_context_window(model)

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        kwargs: dict = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools

        response = ollama.chat(**kwargs)
        msg = response["message"]

        raw_tool_calls = msg.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                name=tc["function"]["name"],
                arguments=tc["function"]["arguments"],
                id=tc.get("id"),
            )
            for tc in raw_tool_calls
        ]

        usage = {
            "prompt_tokens": response.get("prompt_eval_count", 0),
            "completion_tokens": response.get("eval_count", 0),
            "total_tokens": (
                response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
            ),
        }

        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            usage=usage,
        )
