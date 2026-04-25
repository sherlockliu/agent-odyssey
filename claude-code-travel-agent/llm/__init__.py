"""LLM provider factory — create an LLMClient from provider + model strings."""

from __future__ import annotations

from .base import LLMClient, LLMResponse, ToolCall


def create_client(provider: str, model: str, **kwargs) -> LLMClient:
    """
    Factory: instantiate the right LLMClient for the given provider.

    provider: 'ollama' | 'anthropic' | 'openai' | 'groq' | 'together' | 'gemini'
    model:    model name string (provider-specific)
    kwargs:   provider-specific options forwarded to the client constructor
              e.g. host=, api_key=, base_url=, max_tokens=

    Raises ValueError for unknown providers.
    Raises ImportError (from the client module) if the required SDK is missing.
    """
    p = provider.lower()

    if p == "ollama":
        from .ollama_client import OllamaClient
        return OllamaClient(
            model=model,
            host=kwargs.get("host", "http://localhost:11434"),
        )

    if p == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(
            model=model,
            api_key=kwargs.get("api_key"),
            max_tokens=kwargs.get("max_tokens", 4096),
        )

    if p in ("openai", "groq", "together"):
        from .openai_client import OpenAIClient
        return OpenAIClient(
            model=model,
            api_key=kwargs.get("api_key"),
            base_url=kwargs.get("base_url"),
            provider=p,
        )

    if p == "gemini":
        from .gemini_client import GeminiClient
        return GeminiClient(model=model, api_key=kwargs.get("api_key"))

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Supported providers: ollama, anthropic, openai, groq, together, gemini"
    )


__all__ = ["create_client", "LLMClient", "LLMResponse", "ToolCall"]
