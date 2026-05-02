# Agent Harness Specification

> Version: 1.0.0
> Purpose: Design rules, anti-patterns, and checklists for building production AI agent harnesses.
> Usage: Load this file into any AI coding assistant before designing or building agent infrastructure.

---

## Architecture Decision Tree

Use this before building anything.

```
Does the agent need to act on intermediate results?
  No  → Simple API call
  Yes ↓

Does it involve side effects (files, commands, network)?
  No  → Simple API call
  Yes ↓

Does it need cost control, security, or multi-turn state?
  No  → Function Calling (single-turn tool use)
  Yes → Agent Harness
```

| Pattern | Use when | Examples |
|---|---|---|
| Simple API call | Input → output, no side effects | Translation, classification, summarization |
| Function Calling | Single-turn, ≤2 tool calls | Q&A with web search |
| Agent Harness | Multi-turn loop with side effects + control needs | Code editing, ops automation, research |

Rule of thumb: if the system needs "observe → think → act → observe again," build a harness.

---

## Component Dependency Order

Build in this sequence. Each component depends on what came before.

```
1. Dialog Loop          — no dependencies
2. Tool System          — depends on: Loop
3. Permission Pipeline  — depends on: Tools
4. Context Management   — depends on: Loop + Tools
5. Memory System        — depends on: Context Management
6. Hook System          — depends on: Permissions + Tools
```

Do not skip ahead. You cannot implement permissions without tools. You cannot implement memory without context management.

---

## Component 1: Dialog Loop

**Core Rule:** The agent's core is a `while(true)` loop, not a call stack. Never use recursion for the agent turn.

**Design Rules:**
- Use `AsyncGenerator<StreamEvent>` as the loop signature — streaming, cancellability, and backpressure in one abstraction
- Read a state snapshot at the top of each iteration; write a new state object at the bottom; never mutate state mid-iteration
- Propagate `AbortController` to every async operation inside the loop (model call, tool execution, compression)
- Inject external dependencies (`callModel`, `compressor`) as parameters, not module-level imports — makes the loop testable without mocking
- Define all termination conditions explicitly: `max_turns`, `tool_error_limit`, `context_overflow`, `user_abort`, `model_stop`, and 5+ domain-specific conditions

**Anti-Patterns:**
- **Recursive agent turn:** Cannot abort mid-recursion; state recovery requires unwinding the call stack; impossible to inspect in-flight state
- **Global or instance state:** Makes concurrent sessions interfere; use function-local state or explicit state objects passed between iterations
- **Mutating the message array mid-turn:** Leads to torn state if an error occurs partway through

**Minimal Interface:**
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string | ContentBlock[]
}

interface State {
  messages: Message[]
  turnCount: number
  lastContinueReason: string | null
}

async function* dialogLoop(
  initialMessage: string,
  deps: QueryDeps
): AsyncGenerator<StreamEvent>
```

**Skeleton:**
```typescript
async function* dialogLoop(initialMessage, deps) {
  let state: State = {
    messages: [{ role: 'user', content: initialMessage }],
    turnCount: 0,
    lastContinueReason: null,
  }

  while (true) {
    const { messages, turnCount } = state          // snapshot
    const processed = await preprocess(messages)   // compress if needed
    const response = yield* callModel(processed, deps)

    if (response.toolCalls.length === 0) break      // terminal: no tools

    const toolResults = yield* executeTools(response.toolCalls)

    state = {                                       // atomic write
      messages: [...messages, response.message, ...toolResults],
      turnCount: turnCount + 1,
      lastContinueReason: 'tool_results',
    }
  }
}
```

**Checklist:**
- [ ] Loop, not recursion
- [ ] `AbortController` passed to model call and all tool executions
- [ ] All termination conditions defined and handled
- [ ] State written atomically at end of iteration, never mutated mid-turn
- [ ] External dependencies injected as parameters, not imported directly

---

## Component 2: Tool System

**Core Rule:** Every tool is defined by five elements: name, schema, permission check, execution logic, result renderer. No tool skips any element.

**Design Rules:**
- Zod schema is the single source of truth — drives runtime validation, permission logic, and the JSON Schema sent to the model; never maintain a separate schema
- Use a factory function `buildTool()` with safe defaults (passthrough permissions, JSON renderer) — every tool gets the same baseline contract
- Classify every tool before writing it: **read-only** (parallel-safe) or **write** (must serialize); never run two write tools on the same resource concurrently
- Register tools in a central registry; for large sets (>15 tools), implement deferred loading — do not send all schemas on every turn
- Tool names are **add-only** — renames add an alias while keeping the old name; never remove a name the model may have learned

**Anti-Patterns:**
- **Separate validation and documentation schemas:** They will drift; the model will hallucinate input formats
- **Sending all 50 schemas on every turn:** Wastes tokens; degrades model tool selection; use deferred loading with a discovery tool
- **Parallel write tools on same resource:** Race conditions; use a work queue or explicit serialization per resource

**Minimal Interface:**
```typescript
interface Tool<TInput, TOutput> {
  name: string
  schema: ZodSchema<TInput>
  checkPermissions: (input: TInput, ctx: PermissionContext) => PermissionResult
  call: (input: TInput) => Promise<TOutput>
  renderResult: (result: TOutput) => string
}

function buildTool<T>(partial: Partial<Tool<T, unknown>>): Tool<T, unknown> {
  return {
    checkPermissions: () => ({ type: 'passthrough' }),
    renderResult: (r) => JSON.stringify(r),
    ...partial,
  }
}
```

**Checklist:**
- [ ] Zod schema is the only place validation logic lives
- [ ] Every tool has an explicit concurrency classification (read / write)
- [ ] Read-only tools can parallelize; write tools serialize per resource
- [ ] `buildTool()` factory used — no tool bypasses the default contract
- [ ] Tool result rendering is human-readable, not raw JSON blobs
- [ ] Deferred loading implemented if tool count > 15

---

## Component 3: Permission Pipeline

**Core Rule:** Four stages, in order. Each stage can short-circuit. Deny always wins over allow, regardless of source or order.

**Design Rules:**
- Stage 1 (input validation): invalid input → `ask`, not `deny` and not crash — fail-safe, not fail-stop
- Stage 2 (rule matching): check deny rules first, always; `deny > ask > allow` in priority
- Stage 3 (tool-level context check): tool's `checkPermissions` runs only if Stage 2 returned `passthrough`
- Stage 4 (user confirmation): last resort; anything not resolved earlier reaches the user
- `PermissionContext` is immutable — every update produces a new object, never mutates in place
- Permission modes tune friction level: `default` (confirm write ops), `plan` (deny all writes), `auto` (AI classifier handles approvals), `bypassPermissions` (CI/CD with explicit deny rules)
- Use `bypassPermissions` only when paired with explicit deny rules for irreversible operations

**Anti-Patterns:**
- **Crash on invalid input (Stage 1):** Routes the user to a confusing error instead of a confirmation prompt
- **Allow rules checked before deny rules:** A mismatched allow rule can inadvertently grant access that a deny rule should block
- **Mutable `PermissionContext`:** Partial updates during a multi-stage check can produce inconsistent decisions
- **`bypassPermissions` without deny rules:** Removes all safety without adding it back explicitly

**Minimal Interface:**
```typescript
type PermissionOutcome =
  | { type: 'allow' }
  | { type: 'deny'; reason: string }
  | { type: 'ask'; context: string }
  | { type: 'passthrough' }

async function checkToolPermission(
  tool: Tool,
  input: unknown,
  context: PermissionContext     // immutable
): Promise<PermissionOutcome>
```

**Checklist:**
- [ ] Stage 1 routes invalid input to `ask`, not crash
- [ ] Deny rules evaluated before allow rules
- [ ] `PermissionContext` is never mutated mid-check
- [ ] All four stages present and ordered correctly
- [ ] `bypassPermissions` paired with explicit deny rules for dangerous ops
- [ ] Permission mode is runtime-configurable without loop restart

---

## Component 4: Configuration System

**Core Rule:** Six layers, ascending priority. Arrays concatenate and deduplicate across layers. Scalars shadow (highest layer wins).

**Layer priority (lowest → highest):**
```
1. pluginSettings     — plugin defaults
2. userSettings       — user's personal config (~/.config)
3. projectSettings    — project-level config (committed to VCS)
4. localSettings      — machine-local overrides (gitignored)
5. flagSettings       — CLI flags (per-invocation)
6. policySettings     — enterprise policy (cannot be overridden)
```

**Design Rules:**
- Arrays (allow-lists, hook lists, permissions) **concatenate and deduplicate** — never override between layers
- Scalars (model, temperature, timeout) **shadow** — highest-priority layer wins
- `localSettings` is gitignored; `projectSettings` is committed; never commit personal preferences
- `policySettings` is the security lock — no lower layer can override it
- CLI flags inject into `flagSettings` — one-time overrides without touching persistent config
- Use a minimalist store pattern: `get/set/subscribe` with reference equality; avoid heavy state management libraries until proven necessary

**Anti-Patterns:**
- **Flat config with no merge semantics:** Arrays stomp each other; team settings fight user settings
- **Committing `localSettings` to VCS:** Personal machine paths and API keys leak into shared config
- **Attempting to revoke a lower-layer rule by omission:** Arrays concatenate; omitting a rule in a higher layer does not remove it. Use explicit `deny` rules to override
- **`policySettings` in user-editable files:** Enterprise security requirements are neutralized

**Checklist:**
- [ ] Six-layer hierarchy with defined merge semantics
- [ ] Arrays concatenate; scalars shadow
- [ ] `localSettings` is in `.gitignore`
- [ ] `policySettings` sourced from a location users cannot edit
- [ ] CLI flags map to `flagSettings` layer

---

## Component 5: Memory System

**Core Rule:** Store only information that cannot be derived from current project state at runtime. Everything else is noise.

**Four memory types (closed system — no custom types):**
```typescript
type MemoryType = 'user' | 'feedback' | 'project' | 'reference'
```

| Type | What it stores | When to save |
|---|---|---|
| `user` | Who they are, role, expertise, preferences | Learning something about the user |
| `feedback` | Validated rules: what to do/avoid (+ why) | Correction OR confirmed non-obvious approach |
| `project` | Decisions, goals, constraints, key dates | Learning why something was done |
| `reference` | Pointers to external systems | Learning where something lives |

**Design Rules:**
- Memory index (`MEMORY.md`) hard limits: **200 lines, 25KB** — truncated beyond this; keep it concise
- Store absolute dates — never relative references ("next Tuesday" → "2026-05-15")
- Record both **corrections** and **confirmations** in `feedback` — only recording failures creates overly cautious behavior
- Extract memories via the **Fork pattern**: a restricted sub-agent processes the conversation after it ends; never block the main session for memory extraction
- Mutex rule: if the main agent wrote a memory file during the session, skip background extraction for that file
- **Memory is a clue, not a conclusion** — verify file paths before acting; trust "why" memories directly; verify "what" memories against current state

**Anti-Patterns:**
- **Saving everything:** Buries signal in noise; bloats context on next load
- **Relative date references:** Uninterpretable after time passes
- **Blocking main session for memory extraction:** Adds latency to every turn
- **Saving code patterns, file paths, or architecture as memory:** Derivable from current state; will go stale
- **Only recording corrections in `feedback`:** Creates a bias toward excessive caution; confirmed approaches matter too

**Checklist:**
- [ ] Memory index under 200 lines / 25KB
- [ ] Only four memory types used
- [ ] All dates are absolute (YYYY-MM-DD)
- [ ] Memory extraction happens in a background fork, not in the main loop
- [ ] Before acting on a memory that names a file or flag, verify it still exists

---

## Component 6: Context Management

**Core Rule:** Reserve output tokens before filling the context window. Never plan to the headline model size.

**Effective window formula:**
```
Effective Window = Model Context Limit - Reserved Output Tokens
Reserved Output Tokens = min(model_max_output, 20000)
```

**Four-level compression cascade (apply in order):**
```
Level 1: Snip          — manually remove old/large tool results; zero cost
Level 2: MicroCompact  — time-triggered cleanup of expired cache segments
Level 3: Collapse      — proactive restructuring at 90% utilization
Level 4: AutoCompact   — full LLM summary; last resort
```

**Design Rules:**
- Compress **proactively at natural milestones** with guidance about what to preserve — do not wait until forced
- Apply compression at **90% utilization threshold** (not 95% or 100%)
- **Circuit breaker:** 3 consecutive compression failures → stop attempting; log and notify; without it, a broken state generates thousands of wasted API calls
- **Post-compression token budget:** 50K total, 5K per file — prevents immediately re-inflating context after compression
- System prompt must be **stable (identical text) across turns** to enable LLM provider prefix caching
- Track four thresholds: 85% = warn operator, 90% = trigger compression, 95% = block new input, 100% = abort

**Anti-Patterns:**
- **Using headline model context size as the planning budget:** Leaves no room for model output; causes failures at the last moment
- **Naive FIFO truncation:** Loses decision history, error records, and established patterns; future turns make worse decisions
- **No circuit breaker:** A broken compression API causes a retry storm before the session terminates
- **Reading large files immediately after compression:** Immediately re-inflates what was just compressed; enforce post-compression per-file budget

**Checklist:**
- [ ] Effective window calculated with reserved output tokens
- [ ] Compression triggered at 90%, not on overflow
- [ ] Circuit breaker: 3 consecutive failures → stop and alert
- [ ] Post-compression budget enforced (50K total, 5K/file)
- [ ] System prompt is stable text across turns
- [ ] Four utilization thresholds defined and handled (85/90/95/100%)

---

## Component 7: Hook System

**Core Rule:** Hooks are the extension mechanism. Operators customize agent behavior at lifecycle events without modifying core code.

**Five hook types (ordered by latency and capability):**
| Type | Latency | Capability | Use for |
|---|---|---|---|
| Command | ms | Shell script | Validation, audit logging, simple transforms |
| Prompt | seconds | LLM evaluation | Complex content decisions, classification |
| Agent | seconds-min | Multi-step LLM | Investigation, remediation workflows |
| HTTP | network | Webhook call | CI/CD integration, external notifications |
| Function | ms | SDK callback | Runtime-injected logic in the same process |

**Design Rules:**
- Hook output protocol: structured JSON with `decision`, `updatedInput`, `additionalContext` fields + exit code — both channels are read; exit code alone is not sufficient
- Key lifecycle events: `SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`, `Stop`
- Priority: `userSettings > projectSettings > localSettings`
- Three security layers: global disable → managed-hooks-only mode → workspace trust
- **Start with Command hooks**; reach for Prompt hooks only when script logic is insufficient; use Agent hooks only for multi-step investigation
- **Async hooks** (`async: true`) do not block the loop and do not surface failures to users — log them server-side
- Observer + Chain-of-Responsibility: hooks subscribe to events by name; any hook can block propagation via `decision: "block"`

**Anti-Patterns:**
- **Using Prompt/Agent hooks for simple decisions a shell script can make:** Adds 1-5 seconds of latency per tool call for no benefit
- **Synchronous hooks for audit/telemetry:** Adds latency without user-facing benefit; make audit hooks async
- **Not logging async hook failures:** Hooks appear to work when they're silently failing
- **Putting security-critical logic in `localSettings` hooks:** Lower-priority settings; can be overridden by project settings

**Checklist:**
- [ ] Hook output includes structured JSON (not just exit code)
- [ ] Audit and telemetry hooks are `async: true`
- [ ] Async hook failures are logged server-side
- [ ] Command hooks used first; Prompt/Agent hooks only when scripts are insufficient
- [ ] Key lifecycle events covered: `PreToolUse`, `PostToolUse`, `Stop`

---

## Component 8: Multi-Agent Patterns

**Core Rule:** Sub-agents receive the minimum necessary context and the minimum necessary tools. Never pass the full conversation history or full tool set.

**Two coordination patterns:**

**Fork pattern** (parallel subtasks):
- Coordinator spawns specialist agents with a shared prefix (enables provider prefix caching)
- Each sub-agent gets a scoped tool set — only the tools it needs
- Sub-agent results returned as plain text to the coordinator
- Maximum depth: **3 levels**

**Coordinator pattern** (enterprise orchestration):
- One coordinator agent; specialist sub-agents handle domain-specific execution
- Coordinator does **not** execute tools directly — it delegates
- Coordinator tracks progress; sub-agents are stateless within their task

**Four built-in agent types (scope to the minimum necessary):**
| Type | Model | Tools | Use for |
|---|---|---|---|
| Explore | Cheaper | Read-only | Codebase research, file search |
| Plan | Full | Read-only | Architecture decisions, structured output |
| General Purpose | Full | All | Implementation, complex tasks |
| Verification | Full | None / read-only | Adversarial testing, review |

**Design Rules:**
- Pass only the minimum shared prefix to sub-agents, not the full conversation
- Sub-agent tool sets are scoped: read-only agents cannot get write tools
- Enforce a hard nesting depth limit of **≤3 levels** in code, not just convention
- Omit global assistant instructions (e.g., `CLAUDE.md`) from sub-agent context for token efficiency when not needed
- Sub-agent results must be returned as plain text summaries — never as raw message arrays

**Anti-Patterns:**
- **Using General Purpose for read-only tasks:** Wastes tokens loading write tool schemas; risks accidental modifications; use Explore
- **Sending full conversation history to every sub-agent:** Wastes tokens; defeats prefix caching; may leak irrelevant context
- **Nesting more than 3 levels:** Becomes undebuggable; cost explodes; no practical benefit beyond 2 levels for most tasks
- **Stateful sub-agents that call each other:** Creates coordination complexity and circular dependency risk

**Checklist:**
- [ ] Sub-agent tool sets are scoped to minimum necessary
- [ ] Sub-agents receive shared prefix, not full history
- [ ] Nesting depth limit enforced in code (≤3 levels)
- [ ] Read-only tasks use Explore or Plan type, not General Purpose
- [ ] Sub-agent results returned as plain text summaries

---

## Component 9: Streaming Architecture

**Core Rule:** Session state lives in instance properties of a `QueryEngine` class. State is never passed through function parameters.

**Design Rules:**
- `QueryEngine` owns all persistent session state: `messages`, `abortController`, `deniedPermissions`, `usage`, `fileStateCache`, `discoveredSkills`
- `submitMessage` is an `AsyncGenerator<StreamEvent>` — callers consume incrementally, not after full completion
- A new `AbortController` is created per `submitMessage` call; the instance holds the reference so any component can cancel
- Concurrent read-only tools can run via `Promise.all`; write tools must be serialized (explicit queue or sequential execution)
- Stream output as tokens arrive — do not buffer the full response before emitting

**Anti-Patterns:**
- **Passing session state through deep function parameter chains:** State becomes fragmented; components cannot cancel each other; debugging requires tracing through call frames
- **Returning `Promise<FullResult>` instead of `AsyncGenerator<StreamEvent>`:** UI cannot show progress; users experience a blank screen until completion
- **Running write tools in parallel via `Promise.all`:** Race conditions on shared resources; non-deterministic state after tool execution

**Minimal Interface:**
```typescript
class QueryEngine {
  private messages: Message[]
  private abortController: AbortController
  private deniedPermissions: Set<string>
  private usage: TokenUsage
  private fileStateCache: Map<string, FileState>

  async *submitMessage(input: string): AsyncGenerator<StreamEvent> {
    // Each call is a new turn; instance state persists between turns
  }
}
```

**Checklist:**
- [ ] All session state stored as instance properties, not function arguments
- [ ] `submitMessage` returns `AsyncGenerator`, not `Promise`
- [ ] New `AbortController` created per turn and stored on instance
- [ ] Read-only tools parallelized; write tools serialized
- [ ] First token streamed to UI before completion

---

## Component 10: Plan Mode

**Core Rule:** Plan Mode enforces a read-only exploration phase before execution. It is not a suggestion — write operations are denied at the permission pipeline level.

**Implementation:**
- On entering Plan Mode: save current permission mode as `prePlanMode`, switch permission mode to `plan`
- In `plan` mode: write tools return `deny` at Stage 3 of the permission pipeline
- On exiting Plan Mode (`ExitPlanMode` / approval): restore `prePlanMode`, begin execution

**Six-step behavioral sequence (do not reorder):**
```
1. Broad exploration  — read widely; do not form conclusions yet
2. Pattern recognition — identify similar existing implementations
3. Consider alternatives — generate 2-3 approaches before committing
4. Clarify ambiguities — ask questions while still in read-only phase
5. Concrete plan — specific files, functions, sequence of changes
6. Present for approval — show plan; await explicit approval before acting
```

**Design Rules:**
- Use Plan Mode for: multi-file changes, architectural decisions, tasks where the correct approach is not obvious from the description
- Exploration in Plan Mode is zero-cost for error correction — read as widely as needed
- Present a concrete plan (specific files, functions, order of changes) before requesting approval — "I'll look into it" is not a plan
- Never begin execution before receiving explicit approval — `ExitPlanMode` is the gate

**Anti-Patterns:**
- **Modifying files during the planning phase:** Defeats the purpose; errors are no longer zero-cost to correct
- **Skipping Plan Mode on multi-file changes:** The most expensive mistakes happen in the first few turns before understanding the full picture
- **Presenting a vague plan ("I'll update the relevant files"):** Users approve without knowing what will change; leads to surprises

**Checklist:**
- [ ] Write tools denied at permission pipeline level during planning (not just by convention)
- [ ] Exploration is broad before becoming focused
- [ ] Plan names specific files and functions before presenting for approval
- [ ] Execution does not begin before explicit approval

---

## Production Checklist

Use before shipping any agent harness to production.

**Loop and State**
- [ ] Loop, not recursion — state recovery and abort work correctly
- [ ] All termination conditions defined and handled
- [ ] `AbortController` propagated to all async operations
- [ ] State written atomically at end of iteration, never mutated mid-turn

**Tools**
- [ ] Zod schema is the single source of truth for input validation
- [ ] Concurrency safety classification correct for each tool
- [ ] Read-only tools can parallelize; write tools serialize
- [ ] Tool result rendering is human-readable, not raw JSON

**Permissions**
- [ ] Stage 1 fails safe (invalid input → ask, not crash)
- [ ] Deny rules checked before allow rules, always
- [ ] `PermissionContext` is immutable — no mutation mid-check
- [ ] `bypassPermissions` mode paired with explicit deny rules for dangerous operations

**Context**
- [ ] Effective window formula accounts for reserved output tokens
- [ ] Circuit breaker prevents compression retry storms
- [ ] Post-compression budget prevents immediate re-inflation
- [ ] System prompt is stable across turns (cache-friendly prefix)

**Memory**
- [ ] Memory index under 200 lines / 25KB
- [ ] Absolute dates in all memory entries
- [ ] Background extraction does not block main session
- [ ] Memory verified before acting (clue, not conclusion)

**Operations**
- [ ] Token usage tracked and surfaced to operators
- [ ] Session termination reason logged for every session
- [ ] Hook failures logged; async hook failures do not surface to users
- [ ] Dependency failures (MCP, external APIs) degrade gracefully, not crash

---

## Five Core Principles

**1. Loops over recursion.** The agent's core is `while(true)`, not a call stack. State recovery, abort control, and in-flight inspection all require it.

**2. Schema-driven, not hard-coded.** Zod schemas are the single source of truth for validation, permissions, and model documentation. One definition; no drift.

**3. Progressive permissions.** Four stages, fail-fast. Deny wins always. Early rejection at the cheapest checkpoint.

**4. Streaming first.** `AsyncGenerator` from loop to output. Every component is incremental and cancellable. Never buffer a full response.

**5. Pluggable extensions.** Hook system at lifecycle events. Operators customize without forking core code.
