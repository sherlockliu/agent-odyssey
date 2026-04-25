# Architecture

Design and implementation notes for the claude-code-travel-agent.

---

## File Map

```
claude-code-travel-agent/
│
├── main.py                 Entry point — creates TUI, wires agent
├── agent.py                ReAct loop (run_agent function)
├── config.py               Provider configuration, paths, modes
├── tui.py                  Full-screen Textual TUI
│
├── llm/                    LLM abstraction layer
│   ├── base.py             LLMClient ABC, LLMResponse, ToolCall dataclasses
│   ├── __init__.py         create_client() factory
│   ├── ollama_client.py    Ollama provider
│   ├── anthropic_client.py Anthropic Claude (+ prompt caching)
│   ├── openai_client.py    OpenAI / Groq / Together shared adapter
│   └── gemini_client.py    Google Gemini
│
├── tools/                  Tool layer
│   ├── provider.py         ToolProvider ABC
│   ├── registry.py         ToolRegistry — aggregates, dispatches
│   ├── llm_fallback.py     LLM-generated results when mock data has no match
│   ├── search_flights.py   Searches flights (dummy_data/flights.json)
│   ├── search_hotels.py    Searches hotels (dummy_data/hotels.json)
│   ├── search_destinations.py
│   ├── update_itinerary.py Budget guard + itinerary update
│   ├── view_itinerary.py
│   ├── save_context.py
│   └── providers/
│       ├── builtin.py      BuiltinToolProvider — wraps the above functions
│       ├── activities.py   Activities tool provider
│       ├── weather.py      Weather provider (Open-Meteo or mock)
│       └── online_dest.py  Extended destination search
│
├── memory/                 Memory layer
│   ├── todo.py             TodoList — working memory, synced from message history
│   ├── trip_context.py     TripContext — session memory, saved to JSON per trip
│   ├── user_profile.py     UserProfile — permanent preferences at ~/.travel-agent/
│   └── compressor.py       Compress conversation history when context ~80% full
│
├── safety/
│   └── injection_filter.py  Regex-based prompt injection detection
│
├── skills/                 Auto-loaded context files
│   ├── business_travel.md
│   └── family_travel.md
│
├── commands/               User-triggered slash command templates
│   ├── quick_weekend.md
│   ├── export_itinerary.md
│   └── model.md
│
└── dummy_data/             Simulated travel data (no API key needed)
    ├── flights.json         53 routes (SFO, JFK, LHR, BCN, NRT, DXB, SIN, ...)
    ├── hotels.json          43 properties (13 cities)
    ├── activities.json      60 entries (13 cities)
    └── destinations.json    14 destinations
```

---

## ReAct Loop

The entire agent logic lives in `agent.py:run_agent()`. It is a single `while True` loop with no framework, no graph, no state machine.

```
def run_agent(user_input, trip_context, mode, print_fn, h2a_queue):

    messages = [
        system_prompt,
        trip_context_block,
        skill_blocks (if keyword match),
        command_block (if /command prefix),
        conversation_history,
        user_message,
    ]

    while True:
        compress_if_needed(messages)

        response = llm_client.chat(messages, tools=registry.get_all_definitions())
        # response: LLMResponse(content, tool_calls, usage)

        if response.tool_calls:
            for tc in response.tool_calls:
                detect_injection(tc)          # safety check
                result = registry.dispatch(tc.name, tc.arguments)
                messages.append(tool_result(result))
            todo.sync_from_messages(messages)  # update TODO list

        else:
            print_fn(response.content)         # final answer
            trip_context.update_history(...)
            break
```

**Key properties:**
- No framework — one function, one loop, plain Python
- Every iteration is one LLM call → zero, one, or many tool calls → one more LLM call
- Tools communicate via plain text (not structured data) — the LLM reads the result as a human would
- Memory and safety are side effects — they don't change the control flow

---

## LLM Abstraction

```
LLMClient (ABC)
├── context_window: int
├── provider_name: str
├── model_name: str
└── chat(messages, tools) → LLMResponse

LLMResponse
├── content: str          # assistant text (empty when only tool calls)
├── tool_calls: list[ToolCall]
└── usage: dict           # prompt_tokens, completion_tokens, total_tokens
                          # + cache_read_tokens, cache_creation_tokens (Anthropic)

ToolCall (dataclass)
├── name: str
├── arguments: dict
└── id: str | None        # Anthropic requires round-tripping the call id
```

All providers recieve messages in OpenAI format (list of dicts with `role` + `content`). Each provider adapter translates to its native wire format internally. The agent loop never imports a provider SDK directly.

**Provider matrix:**

| Provider | SDK | Auth | Special features |
|----------|-----|------|-----------------|
| Ollama | `ollama` | none | Local, private |
| Anthropic | `anthropic` | API key | Prompt caching, cache_control |
| OpenAI | `openai` | API key | — |
| Groq | `openai` (compat) | API key | Very fast |
| Together | `openai` (compat) | API key | Open models |
| Gemini | `google-generativeai` | API key | — |

---

## Tool Layer

```
ToolProvider (ABC)
├── get_definitions() → list[dict]    # OpenAI tool schemas
├── can_handle(name: str) → bool
└── execute(name: str, args: dict) → str   # plain text, never raises

ToolRegistry
├── register(provider)
├── get_all_definitions() → list[dict]    # merged from all providers
├── dispatch(name, args) → str            # routes to owning provider
└── list_tool_names() → list[str]
```

Providers registered in `config.py:ENABLED_TOOL_PROVIDERS` are instantiated in the agent startup and registered with the `ToolRegistry` in order. The first provider that returns `can_handle(name) == True` is used.

**Tool contract:** every tool function takes typed arguments and returns a plain text string. No exceptions — errors are returned as text. This is intentional: the LLM reads error messages as natural language and adapts.

**LLM fallback:** when mock data returns no results (e.g. a flight route not in `flights.json`), `tools/llm_fallback.py` is called to generate a plausible result. Results are labelled `[AI-generated]`. This keeps demo interactions working without requiring a complete dataset.

---

## Memory Tiers

| Tier | Class | Storage | Lifetime | Used for |
|------|-------|---------|----------|----------|
| Working | `TodoList` | In-memory (message history) | Session only | TODO list, visible in every response |
| Session | `TripContext` | JSON file per trip | Persists across restarts | Destination, dates, budget, itinerary |
| Permanent | `UserProfile` | JSON file | Forever | Home airport, preferred airlines, interests |

**Context compression:** `memory/compressor.py` checks token usage after each LLM call. When history reaches 80% of the context window, it calls the LLM to summarise the conversation, resets the history to the summary + last few messages, and logs `🗜️ Context compressed`.

---

## Safety Layer

`safety/injection_filter.py` runs on every tool call's arguments before dispatch.

It scans argument strings for:
- System prompt override attempts (`ignore all previous instructions`, `new persona`)
- Shell injection patterns (backticks, `$()`, pipes in argument strings)
- Override keywords (`disregard`, `forget`, `pretend you`)

The filter handles both `ToolCall` dataclass and raw dict inputs (legacy format). If injection is detected, the tool call is blocked and the agent receives an error string instead of a result.

Budget guards in `update_itinerary.py` provide a second safety layer that is deterministic: the check is arithmetic code, not an LLM instruction, so the model cannot "decide" to ignore it.

---

## TUI Design

`tui.py` uses [Textual](https://textual.textualize.io/) 6.x.

```
TravelAgentApp (App)
├── RichLog #transcript          Scrollable conversation log
├── Static #metadata-row         Mode / trip / model / context count
├── OptionList #suggestions      Floating slash-command autocomplete
└── Horizontal #input-row
    ├── ComposerInput (TextArea) Multi-line input
    └── Static #hint             Keyboard hint label
```

**Key design decisions:**

1. **Suggestions above input** — `#suggestions` is composed before `#input-row` in the layout so the popup floats above the text area, not below it.

2. **Shift+Enter via BINDINGS** — `ComposerInput` uses `BINDINGS = [Binding("shift+enter", "insert_newline")]`. Textual resolves BINDINGS before key handlers, which is more reliable than overriding `_on_key` for modifier keys.

3. **Async `_on_key`** — Textual 6.x made the internal `_on_key` async. The override must also be `async def _on_key(self, event)` or the call chain breaks silently.

4. **Mouse scrolling** — `TravelAgentApp` handles `on_mouse_scroll_up` / `on_mouse_scroll_down` at the app level to forward wheel events to `#transcript` regardless of which widget has focus. `mouse=True` must be set on `App.run()`.

5. **Cogitation line** — after each LLM call, a status line is printed:
   ```
   ✻ Cogitated for 3.1s • 1617 prompt • 312 completion • 88 tok/s
     (1 cached, 0 cache-write)
   ```
   The cache stats are zero for non-Anthropic providers.

---

## Prompt Token Budget

Every API call is a new stateless HTTP request. Tool schemas must be sent every time.

```
System prompt            ~120 tokens    (trimmed; no bullet lists)
11 tool schemas          ~1,300 tokens  (JSON definitions, fixed every call)
Trip context             ~100–300 tokens (grows as itinerary builds)
Conversation history     variable       (compressed at 80% usage)
User message             variable
```

This is why the first call shows ~1,600 prompt tokens even for "hi".

**Anthropic prompt caching** (`AnthropicClient`) adds `cache_control: ephemeral` to the system content block and the last tool definition. Subsequent calls within 5 minutes pay ~1/10 the input token cost for the cached portion. Cache metrics are surfaced in the cogitation line.

---

## UserProfile: Two Update Paths

The profile is a persistent JSON file (`~/.travel-agent/profile.json`) holding
home airport, preferred airlines/hotels, seat preference, budget defaults, and
interests. It can be updated two ways.

### Path A — User-direct (`/profile set ...`)

```
User: /profile set airport SFO

tui.py _handle_slash_command()
  └─ dispatches to _cmd_profile("set airport SFO")
        │
        ├─ looks up field alias: "airport" → key "home_airport"
        ├─ calls profile.data["home_airport"] = "SFO"
        ├─ calls profile.save()                    ← writes JSON to disk
        └─ shows "[green]✓ Home Airport set to: SFO[/green]"
```

`/profile` with no args starts the interactive Q&A. The command is forwarded to the agent with the `profile.md` command template injected as a system message. The agent walks through missing fields one at a time, calling `update_profile(source='explicit')` for each answer.

### Path B — Agent-inferred from conversation

```v
User: "I usually fly out of SFO"

agent.py ReAct loop
  └─ LLM detects home airport signal, emits tool call:
        update_profile(field="home_airport", value="SFO", source="inferred")
              │
              ▼
        tools/update_profile.py::update_profile()
              │
              ├─ source == "inferred"  →  UserProfile.stage_update("home_airport", "SFO")
              │     stored in class-level _pending dict (not written to disk yet)
              │     returns confirmation prompt string
              │
              └─ returns: "I noticed: Home Airport = 'SFO'. Save to your profile? (yes/no)"

Agent presents confirmation to user
  ├─ User: "yes"
  │     └─ agent calls confirm_profile_update(field="home_airport")
  │             UserProfile.confirm_staged()  →  applies field, writes to disk
  │
  └─ User: "no"
        └─ agent calls discard_profile_update(field="home_airport")
                clears _pending[field], profile unchanged
```

**Key design rule:** inferred values are never silently written. `source='inferred'` stores in `UserProfile._pending` (a class variable, shared across all instances within the process) and returns a confirmation prompt that the agent reads aloud. The `SYSTEM_PROMPT` instructs the model to always use `source='inferred'` for detected preferences.

### Inferrable vs. explicit-only fields

| Field | Inferred? | Example signal |
|---|---|---|
| `home_airport` | ✅ with confirm | "flying from SFO" |
| `seat_preference` | ✅ with confirm | "I always take a window seat" |
| `preferred_airlines` | ✅ with confirm | "I have United miles" |
| `preferred_hotel_chains` | ✅ with confirm | "I collect IHG points" |
| `interests` | ✅ with confirm | "I love food and museums" |
| `avoid` | ✅ with confirm | "I hate long layovers" |
| `budget_defaults` | ⚠️ ask explicitly | Too fuzzy to infer reliably |
| `past_trips` | Agent auto-adds | After export — no confirm needed |

---

## Activity Panel: Seeing What the Agent Is Doing

The TUI surfaces the agent's internal state via the `thinking_fn` callback, which `agent.py` calls at key points in the ReAct loop. Each status maps to a dim hint line in the transcript.

**Events emitted per loop iteration:**

```
thinking_fn("loop_start",     stats={"iteration": n})
thinking_fn("context_loaded", stats={"skills": [...], "command": "..."})
thinking_fn("thinking")           ← about to ask the model
  → LLM call (blocking)
thinking_fn("done",           stats={prompt_tokens, completion_tokens, ...})

For each tool call the model emits:
  print_fn("🔧 Calling tool: <name>")   ← immediately visible
  print_fn("   Arguments: {...}")
  thinking_fn("profile_update", stats={"action": ..., "args": ..., "result": ...})
  print_fn("   Result: ...")

After all tool calls in that round:
  todo.sync_from_messages(messages)
  thinking_fn("todo_updated", stats={"items": [{"status": ..., "task": ...}]})

  → next loop_start if the model made more tool calls
```

**What each event shows in the TUI:**

| Event | Example line |
|---|---|
| `loop_start` (n > 1) | `↩  Loop 2 — continuing...` |
| `context_loaded` | `📚 Skills: Business Travel  •  ⚡ Command: /profile` |
| `thinking` | `⚙  Asking model...` |
| `done` | `✻ Cogitated for 1.2s  •  1617 prompt  •  312 completion  •  88 tok/s` |
| `compression` | `🗜  Compressing context: 42 messages → summarizing...` |
| `steered` | echoes the injected user message inline |
| `profile_update` (inferred) | `👤 Profile (staged for confirm): home_airport = 'SFO'` |
| `profile_update` (explicit) | `👤 Profile saved: home_airport = 'SFO'` |
| `profile_update` (confirmed) | `👤 Profile confirmed: home_airport` |
| `todo_updated` | `📋 TODO: [ ] Search flights  [→] Compare hotels  [✓] Set destination` |

**TODO list parsing:** `todo.sync_from_messages()` scans the last assistant message for lines matching `[ ]`, `[→]`, `[✓]`, or `[x]` patterns and rebuilds the list from scratch. If the model surfaces a TODO block in its reasoning, those items are parsed and shown live in the transcript.

---

## Adding Features

Checklist for common additions:

**New tool:**
1. Write `tools/my_tool.py` — function returns plain text, never raises
2. Add to `BuiltinToolProvider.get_definitions()` and `execute()` in `tools/providers/builtin.py`
3. Or create a new `ToolProvider` subclass and register in `config.py:ENABLED_TOOL_PROVIDERS`

**New LLM provider:**
1. Implement `LLMClient` in `llm/my_provider.py`
2. Add a factory case in `llm/__init__.py:create_client()`
3. Add connection config in `config.py:LLM_PROVIDER_CONFIGS`

**New skill:**
1. Create `skills/my_skill.md` with context rules
2. Add trigger keywords to `_load_skills()` in `agent.py`

**New slash command:**
1. Create `commands/my_command.md` with the workflow template
2. Register in the slash command handler in `agent.py` or `tui.py`

**MCP server:**
See the `McpToolProvider` template in `README.md`. Wrap the server as a `ToolProvider`, instantiate with the server command, and register with the `ToolRegistry`.
