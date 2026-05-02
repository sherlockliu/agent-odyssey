# Agent Harness Kit

A portable, tool-agnostic spec and skill set for building production AI agent harnesses. Drop this into any project and wire up the skill for your AI coding tool.

## What's in the kit

```
agent-harness-kit/
├── SPEC.md                          The core spec — design rules, anti-patterns, checklists
└── skills/
    ├── claude/
    │   ├── SKILL.md                 Claude Code skill (/build-agent)
    │   └── CLAUDE.md                Add to your project's CLAUDE.md
    ├── gemini/
    │   └── GEMINI.md                Drop into project root
    └── codex/
        └── system-prompt.md         Paste as system prompt or project instructions
```

`SPEC.md` covers 10 components with design rules and named anti-patterns:
Dialog Loop · Tool System · Permission Pipeline · Configuration · Memory · Context Management · Hooks · Multi-Agent · Streaming · Plan Mode

---

## Setup

### Claude Code

**Option A — `/build-agent` skill (recommended)**

1. Copy `skills/claude/SKILL.md` into your project:
   ```bash
   mkdir -p .claude/skills/build-agent
   cp agent-harness-kit/skills/claude/SKILL.md .claude/skills/build-agent/
   ```

2. Add the CLAUDE.md content to your project's `CLAUDE.md`:
   ```bash
   cat agent-harness-kit/skills/claude/CLAUDE.md >> CLAUDE.md
   ```

3. Run `/build-agent` in Claude Code to start a guided session.

**Option B — Conversational (no skill)**

Copy `SPEC.md` to your project root. Claude Code will automatically apply it when you mention agent architecture in conversation (via `CLAUDE.md` instruction).

---

### Gemini CLI

```bash
cp agent-harness-kit/skills/gemini/GEMINI.md ./GEMINI.md
```

Gemini reads `GEMINI.md` from the project root as persistent project context.

---

### Codex / ChatGPT / OpenAI API

Open `skills/codex/system-prompt.md` and paste the contents into:
- ChatGPT: Project Instructions
- OpenAI API: `system` message
- Any OpenAI-compatible tool: system prompt field

---

## Workflow

### Starting a new agent project

1. Set up the skill for your AI tool (above)
2. Describe your agent to the AI: what it does, what tools it needs, what side effects it has
3. The AI will guide you through the 6 components in dependency order, applying spec rules at each step

### Auditing existing agent code

1. Set up the skill
2. Say: "Audit this codebase against the agent harness spec"
3. The AI will produce a gap report: compliant / partial / missing / anti-pattern for each component

---

## The five core principles (quick reference)

1. **Loops over recursion** — `while(true)`, not recursive agent turns
2. **Schema-driven** — Zod schema is the single source of truth
3. **Progressive permissions** — 4 stages, deny wins, fail-safe on error
4. **Streaming first** — `AsyncGenerator` from loop to output
5. **Pluggable extensions** — hooks at lifecycle events

---

## Moving to its own repo

This kit is self-contained. To use it outside this project:

```bash
cp -r agent-harness-kit/ /path/to/your/new/agent-project/
```

Or add it as a git submodule:
```bash
git submodule add <this-repo-url> agent-harness-kit
```
