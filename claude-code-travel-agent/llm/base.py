"""Base abstractions for LLM providers — provider-agnostic message and response types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """Normalised tool call returned by any LLM provider."""

    name: str
    arguments: dict
    id: str | None = None  # Provider-assigned call id (Anthropic requires roundtrip)


@dataclass
class LLMResponse:
    """Normalised response from any LLM provider."""

    content: str                          # Text content (may be empty when only tool calls)
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)  # prompt_tokens, completion_tokens, total_tokens


class LLMClient(ABC):
    """
    Abstract base for all LLM provider clients.

    The contract is identical to the Claude Code "uniform tool interface" pattern:
    messages in OpenAI-style list format → LLMResponse out.
    Each provider adapter translates to its native wire format internally.
    """

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Maximum context window in tokens."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier string, e.g. 'ollama', 'anthropic', 'gemini'."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model name string, e.g. 'qwen3:8b', 'claude-opus-4-5'."""
        ...

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """
        Send a conversation to the LLM and return a normalised LLMResponse.

        messages: OpenAI-style list — each dict has 'role' (system/user/assistant/tool)
                  and 'content'. Tool result messages also have 'name' and 'tool_call_id'.
        tools:    OpenAI-style function tool definitions list (optional).
        """
        ...

    def display_name(self) -> str:
        """Human-readable '{provider}/{model}' label for UI display."""
        return f"{self.provider_name}/{self.model_name}"
