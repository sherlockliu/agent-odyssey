# Agent Harness Design Reference

When designing or building AI agent infrastructure in this project:

1. **Read `SPEC.md`** — look for it at `agent-harness-kit/SPEC.md` or the project root. Read it before making any architectural recommendations.
2. **Apply the design rules** from the relevant component section for each piece of agent infrastructure you're working on.
3. **Flag anti-patterns** — if you see code that matches a named anti-pattern in the spec, call it out with the spec section reference.
4. **Follow the component build order**: Dialog Loop → Tool System → Permission Pipeline → Context Management → Memory System → Hook System

## When to apply these rules

Apply spec rules when working on any of:
- Agent loop implementations (any `while` loop processing LLM responses)
- Tool definitions and dispatch systems
- Permission or approval workflows
- Context window or compression logic
- Memory persistence and retrieval
- Hook or extension systems
- Multi-agent coordination

## Quick reference: five core principles

1. **Loops over recursion** — agent core is `while(true)`, not recursive calls
2. **Schema-driven** — one schema definition drives validation, permissions, and model documentation
3. **Progressive permissions** — 4 stages, fail-fast, deny wins over allow always
4. **Streaming first** — `AsyncGenerator` from loop to UI, never buffer full responses
5. **Pluggable extensions** — hooks at lifecycle events, operators customize without forking

## Decision tree: do you need a full harness?

```
Does the agent act on intermediate results?
  No → Simple API call
  Yes ↓

Does it have side effects (files, commands, network)?
  No → Simple API call
  Yes ↓

Does it need cost control, security, or multi-turn state?
  No → Function Calling
  Yes → Full Agent Harness (apply SPEC.md)
```
