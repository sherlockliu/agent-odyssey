"""Core ReAct agent loop for the travel planning agent."""

import queue
import time
from typing import TYPE_CHECKING

from config import LLM_PROVIDER, LLM_MODEL, LLM_PROVIDER_CONFIGS, MODES, DEFAULT_MODE
from tools import dispatch_tool, get_tool_definitions

if TYPE_CHECKING:
    from llm.base import LLMClient
    from memory.user_profile import UserProfile
from memory.todo import TodoList
from memory.trip_context import TripContext
from memory.compressor import compress_if_needed
from safety import detect_injection

SYSTEM_PROMPT = """You are a travel planning assistant.

Help users discover destinations, search flights and hotels (dummy data PoC),
build itineraries, and track budgets. You do NOT book anything.

## Rules
- Use tools to search — never invent prices or flight numbers
- Present options with trade-offs, not just the cheapest
- Ask for confirmation before big itinerary changes
- Do NOT show internal TODO lists in your final response
- Use get_weather for climate questions, search_activities for things to do,
  search_destinations_online for visa/safety/transport tips
- When a user mentions a personal preference (home airport, seat type, airline
  loyalty, hotel chain, travel interests), call update_profile with
  source='inferred' to stage and confirm it — never silently discard preferences
"""


def _load_skills(user_input: str) -> tuple[list[str], list[str]]:
    """Auto-detect and load relevant skill files. Returns (skill_contents, skill_names)."""
    from pathlib import Path
    skills_dir = Path(__file__).parent / "skills"
    loaded_contents = []
    loaded_names = []

    keywords = {
        "business_travel.md": ["business", "conference", "work travel", "meeting", "client", "offsite"],
        "family_travel.md": ["kid", "child", "family", "toddler", "baby", "school break"],
    }

    input_lower = user_input.lower()
    for filename, triggers in keywords.items():
        if any(kw in input_lower for kw in triggers):
            skill_path = skills_dir / filename
            if skill_path.exists():
                loaded_contents.append(skill_path.read_text())
                loaded_names.append(filename.replace(".md", "").replace("_", " ").title())

    return loaded_contents, loaded_names


def _handle_command(user_input: str) -> str | None:
    """Check if input is a slash command. Return the command template or None."""
    from pathlib import Path
    commands_dir = Path(__file__).parent / "commands"

    command_map = {
        "/quick-weekend": "quick_weekend.md",
        "/export": "export_itinerary.md",
        "/profile": "profile.md",
    }

    for command, filename in command_map.items():
        if user_input.strip().startswith(command):
            path = commands_dir / filename
            if path.exists():
                return path.read_text()
    return None


def run_agent(
    user_input: str,
    trip_context: TripContext,
    mode: str = DEFAULT_MODE,
    print_fn=print,
    thinking_fn=None,       # Optional callback for thinking status
    steering_queue=None,    # Optional queue.Queue for mid-loop user steering (h2A pattern)
    llm_client: "LLMClient | None" = None,  # If None, created from config
    user_profile: "UserProfile | None" = None,  # If provided, injected as system context
) -> None:
    """
    Run the ReAct loop for a single user turn.
    Prints responses via print_fn (allows testing/capture).
    thinking_fn is called with elapsed time for status updates.
    steering_queue: if provided, the loop checks it before each model call and
    injects any pending user messages — enabling mid-task steering (h2A pattern).
    """
    # Build (or reuse) the LLM client.
    if llm_client is None:
        from llm import create_client
        provider_cfg = LLM_PROVIDER_CONFIGS.get(LLM_PROVIDER, {})
        llm_client = create_client(LLM_PROVIDER, LLM_MODEL, **provider_cfg)

    todo = TodoList()

    # Build system messages (rebuilt each turn with fresh context)
    skill_contents, skill_names = _load_skills(user_input)
    skill_messages = [
        {"role": "system", "content": skill}
        for skill in skill_contents
    ]

    mode_instruction = MODES.get(mode, MODES[DEFAULT_MODE])
    system_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + [{"role": "system", "content": f"Mode: {mode_instruction}"}]
        + [{"role": "system", "content": trip_context.as_context_message()}]
        + ([{"role": "system", "content": user_profile.as_context_message()}] if user_profile else [])
        + skill_messages
    )

    # Load conversation history and add current user input
    conversation_history = trip_context.get_conversation_history()
    messages = system_messages + conversation_history + [{"role": "user", "content": user_input}]

    # Check for slash command — inject as additional context
    command_template = _handle_command(user_input)
    command_name = None
    if command_template:
        messages.append({
            "role": "system",
            "content": f"[Slash command detected]\n{command_template}",
        })
        # Extract command name
        for cmd in ["/quick-weekend", "/export", "/profile"]:
            if user_input.strip().startswith(cmd):
                command_name = cmd
                break

    # Show what was loaded if anything
    if thinking_fn:
        context_info = {}
        if skill_names:
            context_info["skills"] = skill_names
        if command_name:
            context_info["command"] = command_name
        if context_info:
            thinking_fn("context_loaded", 0, context_info)

    tools = get_tool_definitions()
    loop_iteration = 0

    while True:
        loop_iteration += 1
        # ── h2A: mid-task steering ──────────────────────────────────────
        # Drain any user messages queued while a tool was running.
        # Inject them into history before calling the model — the model
        # sees the interjection and can adjust its approach.
        if steering_queue is not None:
            while True:
                try:
                    steered_input = steering_queue.get_nowait()
                    messages.append({"role": "user", "content": steered_input})
                    if thinking_fn:
                        thinking_fn("steered", 0, {"message": steered_input})
                except queue.Empty:
                    break

        # Compress context if getting large
        def compression_cb(status: str, old_count: int, new_count: int):
            if thinking_fn:
                thinking_fn("compression", 0, {"status": status, "old": old_count, "new": new_count})

        messages = compress_if_needed(
            messages, trip_context, compression_cb,
            context_window=llm_client.context_window,
        )

        # Track cogitation time
        start_time = time.time()
        if thinking_fn:
            thinking_fn("loop_start", 0, {"iteration": loop_iteration})
            thinking_fn("thinking")

        # Call the LLM via the provider-agnostic client.
        llm_response = llm_client.chat(messages=messages, tools=tools)

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Build stats from normalised usage dict.
        usage = llm_response.usage
        stats = {
            "elapsed": elapsed,
            "prompt_tokens":        usage.get("prompt_tokens", 0),
            "completion_tokens":    usage.get("completion_tokens", 0),
            "total_tokens":         usage.get("total_tokens", 0),
            "cache_read_tokens":    usage.get("cache_read_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_tokens", 0),
        }
        if stats["completion_tokens"] > 0 and elapsed > 0:
            stats["tokens_per_sec"] = stats["completion_tokens"] / elapsed
        else:
            stats["tokens_per_sec"] = 0

        if thinking_fn:
            thinking_fn("done", elapsed, stats)

        # Reconstruct an OpenAI-style assistant message dict for the history.
        assistant_msg: dict = {"role": "assistant", "content": llm_response.content}
        if llm_response.tool_calls:
            assistant_msg["tool_calls"] = [
                {"id": tc.id or tc.name, "function": {"name": tc.name, "arguments": tc.arguments}}
                for tc in llm_response.tool_calls
            ]
        messages.append(assistant_msg)

        # No tool calls → final text response, done.
        if not llm_response.tool_calls:
            if llm_response.content:
                print_fn(llm_response.content)
            break

        # Show reasoning/inner monologue if present.
        if llm_response.content:
            print_fn(f"[dim]💭 {llm_response.content}[/dim]\n")

        # Execute each tool call in order.
        for tool_call in llm_response.tool_calls:
            fn_name = tool_call.name
            fn_args = tool_call.arguments

            # Show what tool is being called - IMMEDIATELY
            print_fn(f"[bold cyan]🔧 Calling tool:[/bold cyan] {fn_name}")
            print_fn(f"[dim]   Arguments: {fn_args}[/dim]")

            # Safety check
            if detect_injection(tool_call):
                result = f"[BLOCKED] Tool call '{fn_name}' blocked: potential injection detected."
                print_fn(f"\n⚠  {result}")
            else:
                result = dispatch_tool(fn_name, fn_args)
                # Show result summary (first 200 chars) - IMMEDIATELY
                result_preview = result[:200] + "..." if len(result) > 200 else result
                print_fn(f"[dim]   Result: {result_preview}[/dim]\n")

                # Emit a profile event so the TUI can highlight profile changes.
                if thinking_fn and fn_name in (
                    "update_profile", "confirm_profile_update", "discard_profile_update"
                ):
                    thinking_fn("profile_update", 0, {
                        "action": fn_name,
                        "args": fn_args,
                        "result": result,
                    })

            messages.append({
                "role": "tool",
                "content": result,
                "name": fn_name,           # used by Ollama
                "tool_call_id": tool_call.id or fn_name,  # used by OpenAI / Anthropic
            })

        # Sync TODO state after each tool round
        todo.sync_from_messages(messages)
        if thinking_fn:
            items = todo.as_list()
            if items:
                thinking_fn("todo_updated", 0, {"items": items})

    # Save conversation history after this turn completes
    trip_context.update_conversation_history(messages)
