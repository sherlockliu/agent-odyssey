# Agent Harness Design Reference

When designing or building AI agent infrastructure in this project:

1. **Read `SPEC.md`** (in `agent-harness-kit/SPEC.md` or the project root) before making any architectural recommendations
2. **Apply the design rules** from the relevant component section — do not invent alternatives without checking the spec first
3. **Flag anti-patterns** — if you see code that matches a named anti-pattern in the spec, call it out immediately with the spec reference
4. **Follow the component order** when scaffolding: Loop → Tools → Permissions → Context → Memory → Hooks

## When to apply these rules

- Any file in `src/agent/`, `src/tools/`, `src/memory/`, `src/permissions/`, or equivalent
- Any class named `*Agent`, `*Loop`, `*Tool`, `*Permission*`, `*Memory*`, `*Hook*`
- Any `AsyncGenerator` function that processes LLM responses
- Any tool dispatch, registry, or factory pattern

## Quick reference: the five core principles

1. **Loops over recursion** — `while(true)`, not recursive agent turns
2. **Schema-driven** — Zod schema is the single source of truth
3. **Progressive permissions** — 4 stages, deny wins, fail-safe on error
4. **Streaming first** — `AsyncGenerator` from loop to output
5. **Pluggable extensions** — hooks at lifecycle events, not hardcoded behavior

## For interactive scaffolding

Use `/build-agent` to get a guided design session with intake questions, scaffold or audit mode, and an anti-pattern audit at the end.
