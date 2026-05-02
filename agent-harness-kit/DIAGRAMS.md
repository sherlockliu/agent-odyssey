# Agent Harness — Architecture Diagrams

Six Mermaid diagrams covering the complete agent harness architecture. All diagrams render natively on GitHub, VS Code (with Mermaid Preview), and Notion.

---

## Diagram 1: System Architecture Overview

The full runtime data flow — all six components and how they interconnect when an agent is running. The dialog loop is the center; every other component either feeds into it or extends it.

```mermaid
flowchart TD
    User([User Input]) --> Loop

    subgraph Loop["Dialog Loop — while(true) AsyncGenerator"]
        S1[Phase 1: State Snapshot] --> S2
        S2[Phase 2: Preprocess\ncheck context size] --> S3
        S3[Phase 3: LLM API Call] --> S4{Tool calls?}
        S4 -->|No| Done([Stream Final Response])
        S4 -->|Yes| S5[Phase 4: Execute Tools]
        S5 --> S6[Phase 5: Atomic State Write]
        S6 --> S1
    end

    subgraph Permissions["Permission Pipeline"]
        P1[Stage 1: Validate Input] --> P2
        P2[Stage 2: Rule Match\ndeny wins] --> P3
        P3[Stage 3: Tool Check] --> P4
        P4[Stage 4: User Confirm]
    end

    subgraph Tools["Tool System"]
        TR[Tool Registry] --> TP1[BuiltinProvider]
        TR --> TP2[WeatherProvider]
        TR --> TP3[ActivitiesProvider]
        TP1 & TP2 & TP3 --> Exec{Concurrency?}
        Exec -->|read-only| Par[Promise.all]
        Exec -->|write| Ser[Serialize / Queue]
    end

    subgraph Context["Context Management"]
        CM1{Utilization?} -->|85%| Warn[Warn Operator]
        CM1 -->|90%| Comp[Compression Cascade\nSnip → MicroCompact\n→ Collapse → AutoCompact]
        CM1 -->|95%| Block[Block New Input]
        CM1 -->|100%| Abort[Abort Session]
        Comp -->|3 failures| CB[Circuit Breaker: Stop]
    end

    subgraph Memory["Memory System"]
        MT["4 Types: user / feedback\nproject / reference"]
        MI["Index: MEMORY.md\n≤200 lines / 25KB"]
        MF["Background Fork\nnon-blocking extraction"]
        MT --- MI --- MF
    end

    subgraph Hooks["Hook System"]
        E1([SessionStart]) --> HT
        E2([PreToolUse]) --> HT
        E3([PostToolUse]) --> HT
        E4([PreCompact]) --> HT
        E5([Stop]) --> HT
        HT["Hook Types\nCommand · Prompt · Agent\nHTTP · Function"]
    end

    subgraph Config["Configuration — 6 Layers"]
        direction LR
        C1[policySettings] --> C2[flagSettings] --> C3[localSettings]
        C3 --> C4[projectSettings] --> C5[userSettings] --> C6[pluginSettings]
    end

    S2 <-->|"check / trigger"| Context
    S3 <-->|API call| LLM[(LLM Provider\nAnthropic · Gemini · Ollama)]
    S5 -->|"tool call"| Permissions
    Permissions -->|"approved"| Tools
    E2 -.->|"fires before"| Permissions
    E3 -.->|"fires after"| Tools
    Done -.->|"session end"| Memory
    Config -.->|"loaded at start"| Loop

    style Loop fill:#1e293b,stroke:#3b82f6,color:#fff
    style Permissions fill:#1e293b,stroke:#f59e0b,color:#fff
    style Tools fill:#1e293b,stroke:#10b981,color:#fff
    style Context fill:#1e293b,stroke:#8b5cf6,color:#fff
    style Memory fill:#1e293b,stroke:#06b6d4,color:#fff
    style Hooks fill:#1e293b,stroke:#f97316,color:#fff
    style Config fill:#1e293b,stroke:#6b7280,color:#fff
```

> **SPEC.md reference:** § Component Dependency Order, § Component 1–7

---

## Diagram 2: Dialog Loop — Phase-by-Phase

The internal anatomy of the loop with all five phases and every termination path. State is read-only at the top and written atomically at the bottom — never mutated mid-iteration.

```mermaid
flowchart LR
    Start([Initial Message]) --> Init["Create initial State\n{messages, turnCount: 0,\nlastContinueReason: null}"]
    Init --> P1

    subgraph Iteration["Single Loop Iteration"]
        P1["Phase 1: Snapshot\nconst {messages, turnCount} = state\n(read-only)"] --> P2
        P2["Phase 2: Preprocess\ncheck context utilization\nrun compression if ≥90%"] --> P3
        P3["Phase 3: LLM Call\nawait callModel(processed, deps)\nyield {type: 'thinking'}"] --> Check{Tool calls?}
        Check -->|"0 tool calls"| TermNormal["Terminate: normal\nyield assistant_message\nbreak"]
        Check -->|"≥1 tool calls"| P4
        P4["Phase 4: Execute Tools\nfor each toolCall:\n  check permissions\n  yield tool_call event\n  dispatch\n  yield tool_result event"] --> P5
        P5["Phase 5: Atomic State Write\nstate = {\n  messages: [...old, response, ...results],\n  turnCount: turnCount + 1,\n  lastContinueReason: 'tool_results'\n}"] --> P1
    end

    TermNormal --> Persist["Persist history\ntripContext.updateHistory(messages)\nawait tripContext.save()"]

    P2 -->|"context ≥95%"| TermCtx["Terminate: context_overflow"]
    P3 -->|"API error"| TermAPI["Terminate: api_error"]
    P4 -->|"tool errors ≥ limit"| TermTool["Terminate: tool_error_limit"]
    P1 -->|"turnCount ≥ maxTurns"| TermMax["Terminate: max_turns"]
    P1 -->|"AbortController.signal"| TermAbort["Terminate: user_abort"]
    P3 -->|"stop_reason = end_turn\nno tool calls"| TermNormal

    TermCtx & TermAPI & TermTool & TermMax & TermAbort --> Cleanup["Cleanup:\ncancel in-flight tools\nrelease refs\nlog reason"]
    Cleanup --> Persist

    style Iteration fill:#1e293b,stroke:#3b82f6,color:#fff
    style TermNormal fill:#166534,stroke:#22c55e,color:#fff
    style TermCtx fill:#7f1d1d,stroke:#ef4444,color:#fff
    style TermAPI fill:#7f1d1d,stroke:#ef4444,color:#fff
    style TermTool fill:#7f1d1d,stroke:#ef4444,color:#fff
    style TermMax fill:#78350f,stroke:#f59e0b,color:#fff
    style TermAbort fill:#78350f,stroke:#f59e0b,color:#fff
```

> **SPEC.md reference:** § Component 1: Dialog Loop

---

## Diagram 3: Permission Pipeline — 4-Stage Flow

Every tool call passes through four stages in order. Any stage can short-circuit. Deny always wins over allow regardless of stage. Stage 1 fails safe on bad input — routes to `ask`, never crashes.

```mermaid
flowchart TD
    TC([Tool Call Request]) --> Mode

    subgraph Mode["Permission Mode"]
        M1["default — confirm writes"]
        M2["plan — deny all writes"]
        M3["auto — AI classifier"]
        M4["bypass — CI/CD + explicit denies"]
    end

    Mode --> S1

    subgraph Pipeline["4-Stage Permission Pipeline"]
        S1["Stage 1: Input Validation\ntool.schema.safeParse(input)"]
        S1 -->|invalid| ASK1["→ ask\nfail-safe, not crash"]
        S1 -->|valid| S2

        S2["Stage 2: Rule Matching\nmatchRules(tool.name, data, context.rules)\npriority: deny > ask > allow"]
        S2 -->|deny| DENY["→ deny\ndeny always wins"]
        S2 -->|allow| ALLOW["→ allow"]
        S2 -->|passthrough| S3

        S3["Stage 3: Tool-Level Check\ntool.checkPermissions(input, context)"]
        S3 -->|result| OUT3["→ result\n(allow / deny / ask)"]
        S3 -->|passthrough| S4

        S4["Stage 4: User Confirmation\nrequestUserConfirmation(tool.name, data)"]
        S4 -->|approved| ALLOW2["→ allow"]
        S4 -->|denied| DENY2["→ deny"]
    end

    subgraph Ctx["PermissionContext — immutable"]
        CTX["{ rules, mode, sessionId, ... }\nevery update = new object\nnever mutate in place"]
    end

    S2 <-.->|"reads rules from"| Ctx
    S3 <-.->|"reads context from"| Ctx
    M2 -.->|"forces deny at S3\nfor all write tools"| S3

    ALLOW & ALLOW2 --> Execute([Execute Tool])
    DENY & DENY2 --> Blocked([Return Error to Loop])
    ASK1 & OUT3 --> Confirm([Show User Confirmation])

    style Pipeline fill:#1e293b,stroke:#f59e0b,color:#fff
    style Ctx fill:#1e293b,stroke:#6b7280,color:#fff
    style DENY fill:#7f1d1d,stroke:#ef4444,color:#fff
    style DENY2 fill:#7f1d1d,stroke:#ef4444,color:#fff
    style ALLOW fill:#166534,stroke:#22c55e,color:#fff
    style ALLOW2 fill:#166534,stroke:#22c55e,color:#fff
    style ASK1 fill:#78350f,stroke:#f59e0b,color:#fff
    style Execute fill:#166534,stroke:#22c55e,color:#fff
    style Blocked fill:#7f1d1d,stroke:#ef4444,color:#fff
```

> **SPEC.md reference:** § Component 3: Permission Pipeline

---

## Diagram 4: Tool System — Interface, Registry, Concurrency

The five-element tool contract, the factory pattern, the provider registry, and how read vs write tools are dispatched differently at execution time.

```mermaid
classDiagram
    class Tool {
        +string name
        +ZodSchema schema
        +checkPermissions(input, ctx) PermissionResult
        +call(input) Promise~TOutput~
        +renderResult(result) string
    }

    class ToolRegistry {
        -providers: ToolProvider[]
        +register(provider) void
        +getDefinitions() ToolDefinition[]
        +dispatch(name, args) Promise~string~
    }

    class ToolProvider {
        <<interface>>
        +getDefinitions() ToolDefinition[]
        +canHandle(name) boolean
        +execute(name, args) Promise~string~
    }

    class BuiltinProvider {
        +execute() search_destinations\nsearch_flights\nsearch_hotels\nview_itinerary\nupdate_itinerary\nexport_itinerary
    }

    class WeatherProvider {
        +execute() get_weather
    }

    class ActivitiesProvider {
        +execute() search_activities
    }

    class buildTool {
        <<factory>>
        +defaults: checkPermissions→passthrough\nrenderResult→JSON.stringify
    }

    ToolRegistry o-- ToolProvider : registers
    ToolProvider <|.. BuiltinProvider
    ToolProvider <|.. WeatherProvider
    ToolProvider <|.. ActivitiesProvider
    buildTool ..> Tool : creates with safe defaults
    BuiltinProvider ..> Tool : implements
```

```mermaid
flowchart LR
    Dispatch["ToolRegistry.dispatch(name, args)"] --> Classify{Concurrency\nclassification?}

    Classify -->|"read-only"| Par["Promise.all\n(parallel execution)"]
    Classify -->|"write"| Ser["Sequential / Queue\n(serialize per resource)"]

    Par --> R1[Tool A result]
    Par --> R2[Tool B result]
    Par --> R3[Tool C result]

    Ser --> W1[Tool D result] --> W2[Tool E result]

    R1 & R2 & R3 & W2 --> Render["renderResult()\nhuman-readable string\n(not raw JSON)"]
    Render --> Loop([Back to Dialog Loop])

    subgraph Examples["Classification Examples"]
        RO["Read-only: search_flights\nsearch_hotels\nview_itinerary\nget_weather"]
        WR["Write: update_itinerary\nexport_itinerary\nbookFlight (future)\nbookHotel (future)"]
    end

    style Par fill:#166534,stroke:#22c55e,color:#fff
    style Ser fill:#78350f,stroke:#f59e0b,color:#fff
    style RO fill:#166534,stroke:#22c55e,color:#fff
    style WR fill:#78350f,stroke:#f59e0b,color:#fff
```

> **SPEC.md reference:** § Component 2: Tool System

---

## Diagram 5: Memory System + Context Compression Lifecycle

Two state machines that govern how the harness manages information over time: the memory extraction lifecycle (cross-session persistence) and the context compression cascade (single-session overflow handling).

```mermaid
stateDiagram-v2
    [*] --> Idle: Session starts
    Idle --> Recording: User sends first message
    Recording --> Recording: Each turn appends to conversation
    Recording --> CheckMutex: Session ends (Stop event)

    CheckMutex --> SkipExtraction: Main agent wrote\nmemory files this session\n(mutex held)
    CheckMutex --> ForkExtraction: No memory writes\nthis session

    ForkExtraction --> BackgroundFork: Spawn restricted\nsub-agent\n(non-blocking)
    BackgroundFork --> Analyzing: Sub-agent reads conversation
    Analyzing --> Writing: Identifies memorable\nuser / feedback / project / reference

    Writing --> IndexUpdate: Write memory files\nUpdate MEMORY.md index
    IndexUpdate --> ValidateSize: Check index size
    ValidateSize --> Done: ≤200 lines / 25KB
    ValidateSize --> Prune: >200 lines / 25KB → prune oldest

    Prune --> Done
    SkipExtraction --> Done
    Done --> [*]

    note right of Writing
        Absolute dates only
        (never "next Tuesday")
        4 types only: user /
        feedback / project / reference
    end note

    note right of BackgroundFork
        Main session continues
        unblocked during extraction
    end note
```

```mermaid
stateDiagram-v2
    [*] --> Normal: Session starts

    Normal --> Normal: Each turn adds tokens
    Normal --> Warn: Utilization reaches 85%

    Warn --> Warn: Continue with warning
    Warn --> Level1: Utilization reaches 90%

    Level1: Snip (Level 1)
    Level1 --> Normal: Success — utilization drops
    Level1 --> Level2: Snip insufficient

    Level2: MicroCompact (Level 2)
    Level2 --> Normal: Success
    Level2 --> Level3: Still above threshold

    Level3: Collapse (Level 3)\nproactive restructuring
    Level3 --> Normal: Success
    Level3 --> Level4: Still above threshold

    Level4: AutoCompact (Level 4)\nfull LLM summary
    Level4 --> Normal: Success — fresh context
    Level4 --> CircuitBreaker: 3 consecutive\ncompression failures

    CircuitBreaker: Circuit Breaker\nStop attempting compression\nlog + alert operator
    CircuitBreaker --> Blocked: Utilization reaches 95%

    Blocked --> Abort: Utilization reaches 100%
    Abort --> [*]: Session terminated

    note right of Level1
        Post-compression budget:
        50K total, 5K per file
        Prevents immediate re-inflation
    end note

    note right of CircuitBreaker
        Without this: broken API state
        generates thousands of
        wasted API calls
    end note
```

> **SPEC.md reference:** § Component 5: Memory System, § Component 6: Context Management

---

## Diagram 6: Hook System + Multi-Agent Patterns

The hook system's lifecycle event bus and how the five hook types connect to it. Plus the two multi-agent coordination patterns (Fork and Coordinator) and where they fit in the harness.

```mermaid
flowchart TD
    subgraph Events["Lifecycle Event Bus"]
        E1([SessionStart])
        E2([PreToolUse])
        E3([PostToolUse])
        E4([PreCompact])
        E5([Stop])
    end

    subgraph HookTypes["Hook Types — ordered by latency"]
        HT1["Command hook\nShell script execution\nLatency: ms\nUse for: validation, logging, transforms"]
        HT2["Function hook\nSDK runtime callback\nLatency: ms\nUse for: in-process logic"]
        HT3["HTTP hook\nWebhook call\nLatency: network\nUse for: CI/CD, notifications"]
        HT4["Prompt hook\nLLM evaluation\nLatency: seconds\nUse for: complex content decisions"]
        HT5["Agent hook\nMulti-step LLM\nLatency: seconds–min\nUse for: investigation workflows"]
    end

    subgraph Output["Hook Output Protocol"]
        OP["Structured JSON:\n{ decision, updatedInput, additionalContext }\n+ exit code\nBoth channels are read"]
    end

    subgraph Priority["Hook Priority"]
        PR["userSettings\n  > projectSettings\n    > localSettings"]
    end

    E1 & E2 & E3 & E4 & E5 -->|"subscribe by event name"| HT1
    E1 & E2 & E3 & E4 & E5 --> HT2
    E1 & E3 & E5 --> HT3
    E2 & E3 --> HT4
    E2 --> HT5

    HT1 & HT2 & HT3 & HT4 & HT5 --> OP

    style Events fill:#1e293b,stroke:#f97316,color:#fff
    style HookTypes fill:#1e293b,stroke:#f97316,color:#fff
    style HT1 fill:#1e3a2f,stroke:#22c55e,color:#fff
    style HT2 fill:#1e3a2f,stroke:#22c55e,color:#fff
    style HT3 fill:#1c2a3a,stroke:#3b82f6,color:#fff
    style HT4 fill:#2d1f3a,stroke:#a78bfa,color:#fff
    style HT5 fill:#3a1f1f,stroke:#f87171,color:#fff
```

```mermaid
flowchart TD
    subgraph Fork["Fork Pattern — Parallel Subtasks"]
        FC([Coordinator]) -->|"shared prefix\n+ scoped tools"| FA[Sub-Agent A\nExplore type]
        FC -->|"shared prefix\n+ scoped tools"| FB[Sub-Agent B\nExplore type]
        FC -->|"shared prefix\n+ scoped tools| FCC[Sub-Agent C\nPlan type]
        FA -->|"plain text result"| Merge[Coordinator merges results]
        FB -->|"plain text result"| Merge
        FCC -->|"plain text result"| Merge
        Merge --> FOut([Final response])
    end

    subgraph Coord["Coordinator Pattern — Enterprise Orchestration"]
        CC([Coordinator Agent\ndoes NOT execute tools]) -->|"delegates to"| CS1[Specialist A\nGeneral Purpose]
        CC -->|"delegates to"| CS2[Specialist B\nGeneral Purpose]
        CC -->|"delegates to"| CS3[Specialist C\nVerification]
        CS1 & CS2 & CS3 -->|"reports back"| CC
        CC --> COut([Synthesized output])
    end

    subgraph Depth["Depth Limit — enforced in code"]
        D1[Coordinator\nDepth 0] --> D2[Sub-Agent\nDepth 1]
        D2 --> D3[Sub-Sub-Agent\nDepth 2]
        D3 -. "depth ≥ 3\nHARD STOP" .-> D4[❌ Cannot spawn]
    end

    subgraph Types["4 Built-in Agent Types"]
        AT1["Explore\nread-only tools\ncheaper model\nno CLAUDE.md"]
        AT2["Plan\nread-only tools\nstructured output\narchitecture decisions"]
        AT3["General Purpose\nfull tool set\nimplementation tasks"]
        AT4["Verification\nno/read-only tools\nadversarial testing\nruns in background"]
    end

    style Fork fill:#1e293b,stroke:#3b82f6,color:#fff
    style Coord fill:#1e293b,stroke:#8b5cf6,color:#fff
    style Depth fill:#1e293b,stroke:#ef4444,color:#fff
    style D4 fill:#7f1d1d,stroke:#ef4444,color:#fff
    style AT1 fill:#1e3a2f,stroke:#22c55e,color:#fff
    style AT2 fill:#1c2a3a,stroke:#3b82f6,color:#fff
    style AT3 fill:#2d1f3a,stroke:#a78bfa,color:#fff
    style AT4 fill:#3a1f1f,stroke:#f87171,color:#fff
```

> **SPEC.md reference:** § Component 7: Hook System, § Component 8: Multi-Agent Patterns

---

## Quick Reference: Component Build Order

The dependency graph that determines which component to build first.

```mermaid
flowchart LR
    L["1. Dialog Loop\n(no deps)"]
    T["2. Tool System\n(needs: Loop)"]
    P["3. Permission Pipeline\n(needs: Tools)"]
    C["4. Context Management\n(needs: Loop + Tools)"]
    M["5. Memory System\n(needs: Context)"]
    H["6. Hook System\n(needs: Permissions + Tools)"]

    L --> T
    T --> P
    L --> C
    T --> C
    C --> M
    P --> H
    T --> H

    style L fill:#1e293b,stroke:#3b82f6,color:#fff
    style T fill:#1e293b,stroke:#10b981,color:#fff
    style P fill:#1e293b,stroke:#f59e0b,color:#fff
    style C fill:#1e293b,stroke:#8b5cf6,color:#fff
    style M fill:#1e293b,stroke:#06b6d4,color:#fff
    style H fill:#1e293b,stroke:#f97316,color:#fff
```

> **SPEC.md reference:** § Component Dependency Order
