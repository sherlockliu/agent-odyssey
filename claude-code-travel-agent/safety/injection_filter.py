"""Prompt injection detection for tool call parameters."""

import json
import re

INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|all)\s+instructions",
    r"you\s+are\s+now",
    r"disregard\s+(all|the|previous)",
    r"system\s+prompt",
    r"<\|.*?\|>",          # Special tokens (e.g. <|system|>)
    r"\[INST\]",            # Llama instruction tokens
    r"###\s*(System|Instruction)",
]


def detect_injection(tool_call) -> bool:
    """Return True if the tool call parameters look like a prompt injection attempt."""
    # Support both ToolCall dataclass and raw OpenAI-style dict
    if hasattr(tool_call, "arguments"):
        params = tool_call.arguments
    else:
        params = tool_call.get("function", {}).get("arguments", {})
    if isinstance(params, dict):
        params_str = json.dumps(params)
    else:
        params_str = str(params)

    return any(
        re.search(pattern, params_str, re.IGNORECASE)
        for pattern in INJECTION_PATTERNS
    )
