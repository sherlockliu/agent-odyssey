"""Anthropic Claude LLM client adapter."""

from __future__ import annotations

import json
from typing import Any

from .base import LLMClient, LLMResponse, ToolCall

_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-opus-4":      200000,
    "claude-sonnet-4":    200000,
    "claude-haiku-3-5":   200000,
    "claude-haiku-3":     200000,
    "claude-3-5-sonnet":  200000,
    "claude-3-5-haiku":   200000,
    "claude-3-opus":      200000,
    "claude-3-sonnet":    200000,
    "claude-3-haiku":     200000,
}
_DEFAULT_CONTEXT_WINDOW = 200000


def _guess_context_window(model: str) -> int:
    model_lower = model.lower()
    for prefix, size in _CONTEXT_WINDOWS.items():
        if model_lower.startswith(prefix):
            return size
    return _DEFAULT_CONTEXT_WINDOW


def _convert_tool_definitions(openai_tools: list[dict], cache_last: bool = False) -> list[dict]:
    """Convert OpenAI-style tool definitions to Anthropic format.

    When cache_last=True, a cache_control breakpoint is added to the last tool so
    Anthropic will cache everything up to and including the tool list on the first
    call and reuse it on subsequent calls (reducing cost ~10x and latency).
    """
    result = []
    for i, tool in enumerate(openai_tools):
        fn = tool.get("function", {})
        entry: dict = {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        }
        if cache_last and i == len(openai_tools) - 1:
            entry["cache_control"] = {"type": "ephemeral"}
        result.append(entry)
    return result


def _convert_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """
    Split OpenAI-style messages into (system_string, anthropic_conversation_list).

    - system messages → concatenated into a single `system=` string
    - tool role messages → converted to `tool_result` content blocks in a user turn
    - assistant messages with tool_calls → converted to content blocks with `tool_use` blocks
    """
    system_parts: list[str] = []
    anthropic_msgs: list[dict] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content") or ""

        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if role == "tool":
            # Tool results become tool_result content blocks inside a user turn.
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id") or msg.get("name", "unknown"),
                "content": content,
            }
            # Append to an existing user turn with tool_result content, or start a new one.
            if (
                anthropic_msgs
                and anthropic_msgs[-1]["role"] == "user"
                and isinstance(anthropic_msgs[-1]["content"], list)
            ):
                anthropic_msgs[-1]["content"].append(tool_result_block)
            else:
                anthropic_msgs.append({"role": "user", "content": [tool_result_block]})
            continue

        if role == "assistant":
            raw_tool_calls = msg.get("tool_calls") or []
            content_blocks: list[dict] = []
            if content:
                content_blocks.append({"type": "text", "text": content})
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                # Use the stored id to enable correct tool_result roundtrip.
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or fn.get("name", "unknown"),
                    "name": fn.get("name", ""),
                    "input": args,
                })
            anthropic_msgs.append({
                "role": "assistant",
                "content": content_blocks if content_blocks else (content or ""),
            })
            continue

        # user role — plain string content.
        anthropic_msgs.append({"role": "user", "content": content})

    return "\n\n".join(system_parts), anthropic_msgs


class AnthropicClient(LLMClient):
    """Adapter for Anthropic Claude models via the anthropic SDK.

    Prompt caching is enabled by default (cache_tools=True). On the first call the
    server stores the system prompt + tool schema prefix; every subsequent call that
    sends the identical prefix is served from cache at ~1/10 the token cost and lower
    latency. The cache TTL is 5 minutes (ephemeral). Tool definitions are static
    within a session, so nearly every turn after the first benefits from the cache.
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 4096,
        cache_tools: bool = True,
    ) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required. "
                "Install with: pip install 'claude-code-travel-agent[anthropic]'"
            ) from exc

        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._context_window = _guess_context_window(model)
        self._cache_tools = cache_tools

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
        system_text, conv_msgs = _convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": conv_msgs,
        }
        if system_text:
            # Add a cache breakpoint on the system prompt so it's cached together
            # with the tool schemas (they form one contiguous cacheable prefix).
            if self._cache_tools:
                kwargs["system"] = [
                    {"type": "text", "text": system_text,
                     "cache_control": {"type": "ephemeral"}},
                ]
            else:
                kwargs["system"] = system_text
        if tools:
            kwargs["tools"] = _convert_tool_definitions(tools, cache_last=self._cache_tools)

        response = self._client.messages.create(**kwargs)

        content_text = ""
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    name=block.name,
                    arguments=block.input,
                    id=block.id,
                ))

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            # Prompt-cache metrics (0 when caching disabled or Anthropic not used)
            "cache_creation_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read_tokens":     getattr(response.usage, "cache_read_input_tokens",     0) or 0,
        }

        return LLMResponse(content=content_text, tool_calls=tool_calls, usage=usage)
