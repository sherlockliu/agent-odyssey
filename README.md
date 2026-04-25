# Agent Samples

A growing collection of AI agent implementations demonstrating real-world design patterns for building with large language models. Each sample is a fully working agent you can run locally, study, and adapt.

> **Work in progress** — we'll keep adding new agents covering different architectures, use cases, and languages.

---

## Samples

### [claude-code-travel-agent](./claude-code-travel-agent) — Python

A travel-planning assistant built in Python with a full-screen terminal UI (Textual). Demonstrates all 10 core Claude Code agent design patterns:

- ReAct loop (Reason + Act)
- Uniform tool interface
- Multi-tier memory (in-session, per-trip, permanent profile)
- Automatic context compression
- Autonomy dial (passive / default / proactive modes)
- Skills and slash commands
- Simple file-based infrastructure
- Explicit todo-list planning
- Layered safety (prompt injection detection, budget guards)

Supports 6 LLM providers: Ollama (local), Anthropic Claude, OpenAI, Groq, Together AI, Google Gemini.

**Quick start:**
```bash
cd claude-code-travel-agent
just install
just run           # Ollama (local, free)
just run-claude    # Anthropic Claude
just run-gemini    # Google Gemini
```

---

### [travel-agent](./travel-agent) — TypeScript

The same travel-planning agent re-implemented in TypeScript with a React/Ink terminal UI. Shows that the same agent design patterns apply cleanly across languages and ecosystems.

Supports: Anthropic Claude, Google Gemini, Ollama.

**Quick start:**
```bash
cd travel-agent
cp .env.example .env   # fill in your API key
npm install
npm run dev
```

---

## Design Patterns Demonstrated

| Pattern | Description |
|---------|-------------|
| Master loop | Single `while` loop: think → call tools → observe → repeat |
| Uniform tool interface | All tools accept JSON, return plain text |
| Memory by time scale | RAM (session), JSON file (trip), JSON file (user profile) |
| Compress before truncate | Auto-compress conversation history at 80% context limit |
| Autonomy dial | User-controlled passive / default / proactive modes |
| Extension via skills | Auto-loaded markdown context files triggered by keywords |
| Extension via commands | User-triggered `/command` templates |
| Simple infra | No database — plain JSON files, no external dependencies |
| Explicit plans | TodoList kept in sync after every tool call |
| Layered safety | Injection detection + domain-level guards (budget limits) |

---

## Prerequisites

- **Python agent**: Python 3.11+, [just](https://github.com/casey/just) task runner
- **TypeScript agent**: Node.js 18+, npm
- An LLM provider (Ollama for free local inference, or any cloud provider key)

---

## Contributing

Samples should be self-contained, runnable, and focus on teaching one or more agent design patterns clearly. Each sample lives in its own subdirectory with its own README.
