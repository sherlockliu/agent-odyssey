# CLAUDE.md — Agent Samples

Guidelines for working in this repository with Claude Code.

## Repository Structure

```
agent-samples/
├── claude-code-travel-agent/   Python agent (Textual TUI, 6 LLM providers)
├── travel-agent/               TypeScript agent (React/Ink TUI)
├── README.md                   Collection overview
└── CLAUDE.md                   This file
```

Each sample is fully self-contained with its own dependencies, tooling, and README.

## Working with the Python Agent (`claude-code-travel-agent`)

- **Task runner**: `just` — run `just` to list all commands
- **Install**: `just install` (creates `.venv` via Poetry)
- **Run**: `just run` (Ollama), `just run-claude`, `just run-gemini`, etc.
- **Env config**: copy `.env.sample` → `.env` and fill in API keys
- **Never commit `.env`** — it's in `.gitignore`; use `.env.sample` as the template

Key directories:
- `agent.py` — ReAct loop (start here when reading the code)
- `tools/` — tool definitions; each tool returns plain `str`
- `memory/` — three-tier memory (todo, trip context, user profile)
- `llm/` — provider abstractions (add new providers here)
- `safety/` — prompt injection filter
- `skills/` — markdown files auto-loaded based on conversation keywords
- `commands/` — slash command templates

## Working with the TypeScript Agent (`travel-agent`)

- **Install**: `npm install`
- **Run**: `npm run dev`
- **Type check**: `npm run typecheck`
- **Env config**: copy `.env.example` → `.env` and fill in API keys
- **Never commit `.env`** — it's in `.gitignore`; use `.env.example` as the template

Key directories:
- `src/agent/loop.ts` — ReAct loop
- `src/tools/` — tool definitions
- `src/memory/` — trip context and user profile
- `src/llm/` — provider abstractions
- `src/safety/` — injection filter
- `src/components/` — Ink/React TUI components

## Adding a New Sample

1. Create a new subdirectory: `my-agent-sample/`
2. Include a `README.md` explaining what pattern(s) it demonstrates
3. Include a `.gitignore` that excludes `.env`, build artifacts, and virtual envs
4. Include a `.env.example` (or `.env.sample`) with empty placeholder values — never real keys
5. Update the root `README.md` to add an entry for the new sample

## Security Rules

- **Never commit real API keys** — put them in `.env` (gitignored), not in `.env.example`
- **Never commit `.travel-agent/`** — contains personal trip data and conversation history
- Dummy data lives in `dummy_data/*.json` — safe to commit

## Dummy Data

Both agents ship with offline mock data in `dummy_data/`:
- `flights.json` — 53 routes
- `hotels.json` — 43 properties
- `activities.json` — 60 activities
- `destinations.json` — 14 destinations

This means both agents work without any API key (using Ollama for the LLM).
