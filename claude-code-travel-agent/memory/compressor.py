"""Context window compressor — summarise and reset when the window fills up."""

from config import CONTEXT_WINDOW_LIMIT, COMPRESS_THRESHOLD, TOKENS_PER_CHAR


def _estimate_tokens(messages: list[dict]) -> int:
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    return int(total_chars * TOKENS_PER_CHAR)


def compress_if_needed(
    messages: list[dict],
    trip_context,
    compression_callback=None,
    context_window: int | None = None,
) -> list[dict]:
    """
    If the message history is getting large, summarise it and reset.
    Preserves system messages and injects the summary as context.
    Returns the (possibly compressed) message list.
    If compression_callback is provided, calls it with (status, old_count, new_count).
    context_window: override the default CONTEXT_WINDOW_LIMIT (pass llm_client.context_window).
    """
    limit = context_window if context_window is not None else CONTEXT_WINDOW_LIMIT
    estimated = _estimate_tokens(messages)
    threshold = int(limit * COMPRESS_THRESHOLD)

    if estimated < threshold:
        return messages

    original_count = len(messages)
    
    # Separate system messages from conversation
    system_msgs = [m for m in messages if m.get("role") == "system"]
    convo_msgs = [m for m in messages if m.get("role") != "system"]

    if not convo_msgs:
        return messages

    # Notify about compression
    if compression_callback:
        compression_callback("compressing", original_count, estimated)

    # Ask the model to summarise the conversation
    summary_prompt = (
        "Summarise this travel planning conversation. Preserve:\n"
        "1. The user's destination and dates\n"
        "2. Budget constraints discussed\n"
        "3. Flights and hotels the user liked or selected\n"
        "4. Any preferences stated (seat type, hotel chain, etc.)\n"
        "5. Outstanding TODO items not yet completed\n\n"
        "Conversation:\n"
        + "\n".join(f"{m['role'].upper()}: {m.get('content', '')}" for m in convo_msgs[-30:])
    )

    try:
        from llm import create_client
        from config import LLM_PROVIDER, LLM_MODEL, LLM_PROVIDER_CONFIGS
        client = create_client(LLM_PROVIDER, LLM_MODEL, **LLM_PROVIDER_CONFIGS.get(LLM_PROVIDER, {}))
        resp = client.chat(messages=[{"role": "user", "content": summary_prompt}])
        summary = resp.content
    except Exception:
        # If compression fails, just keep the last 10 messages
        fallback = system_msgs + convo_msgs[-10:]
        if compression_callback:
            compression_callback("compressed", original_count, len(fallback))
        return fallback

    # Save summary to trip context
    if trip_context is not None:
        trip_context.data.setdefault("session_summaries", []).append(summary)
        trip_context.save()

    # Build fresh message history
    compressed = system_msgs + [
        {
            "role": "system",
            "content": f"[Context compressed — previous session summary]\n{summary}",
        }
    ]
    
    if compression_callback:
        compression_callback("compressed", original_count, len(compressed))
    
    return compressed
