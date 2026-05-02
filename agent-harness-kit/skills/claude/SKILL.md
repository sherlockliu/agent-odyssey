---
name: build-agent
description: Guides the design and implementation of a production AI agent harness using established architecture patterns
version: 1.0.0
auto_invoke: false
---

# Build Agent Skill

This skill helps you design and build a production-grade AI agent harness. It applies the architecture patterns in `SPEC.md` to your specific use case — either scaffolding a new project or auditing an existing one.

## First Action (Required)

**Before anything else, read `SPEC.md`.** Look for it at:
1. `agent-harness-kit/SPEC.md` (if the kit folder is in the project)
2. `SPEC.md` at the project root (if it was copied there)

Do not proceed until you have read the spec. All design guidance lives there.

## Intake

Ask the following questions before making any recommendations:

1. **What does the agent do?** (one sentence — what task is it performing autonomously?)
2. **What tools does it need?** (files, shell, network, database, APIs — list them)
3. **What side effects does it have?** (what can it change, delete, or send?)
4. **What permission model do you need?** (who approves actions, and which ones?)
5. **Is there existing code to work with, or are you starting fresh?**

If starting fresh → **Scaffold Mode**
If existing code → **Audit Mode**

---

## Scaffold Mode (New Project)

Walk through the six components in dependency order. For each component, apply the relevant spec section before generating any code.

**Step 1 — Dialog Loop**
Read: Spec § Component 1
- Generate the loop skeleton with `AsyncGenerator<StreamEvent>`
- Inject all external dependencies as parameters
- Define termination conditions specific to this agent's use case
- Set up `AbortController` threading

**Step 2 — Tool System**
Read: Spec § Component 2
- List every tool the agent needs based on intake answers
- Classify each: read-only or write
- Generate `buildTool()` factory and one complete tool as a template
- Note which tools are safe to parallelize

**Step 3 — Permission Pipeline**
Read: Spec § Component 3
- Map each tool to a permission mode (default / auto / bypass)
- Generate the four-stage pipeline
- Add deny rules for any irreversible operations (delete, send, charge)

**Step 4 — Context Management**
Read: Spec § Component 6
- Calculate effective window for the target model
- Add compression hooks at the 90% threshold
- Set up the circuit breaker

**Step 5 — Memory System** (if the agent needs cross-session persistence)
Read: Spec § Component 5
- Identify what information cannot be derived from project state at runtime
- Map each type to the correct memory category (user / feedback / project / reference)
- Set up background extraction fork

**Step 6 — Hook System** (if operators need to customize behavior)
Read: Spec § Component 7
- Identify lifecycle events that need hooks
- Start with Command hooks; escalate to Prompt only if necessary

---

## Audit Mode (Existing Code)

Read the existing agent code, then check it against the spec. Generate a gap report.

**For each component in the spec:**
- Does the implementation exist?
- Does it follow the design rules?
- Does it violate any named anti-pattern?

Output format for each finding:
```
Component: [name]
Status: [✅ compliant | ⚠️ partial | ❌ missing | 🔴 anti-pattern]
Finding: [one sentence]
Spec reference: § Component N
Action: [what to fix, or "none required"]
```

Prioritize findings: 🔴 anti-patterns first, ❌ missing components second, ⚠️ partial implementations third.

---

## Anti-Pattern Audit (Run at End of Every Session)

After scaffold or audit mode completes, run through this list explicitly:

**Loop**
- [ ] Is the core implemented as a loop (not recursion)?
- [ ] Is state written atomically, not mutated mid-iteration?

**Tools**
- [ ] Is the Zod schema the single source of truth (no separate validation)?
- [ ] Are write tools serialized (no `Promise.all` on writes)?

**Permissions**
- [ ] Does Stage 1 fail-safe on invalid input (not crash)?
- [ ] Are deny rules evaluated before allow rules?

**Context**
- [ ] Does the effective window calculation subtract reserved output tokens?
- [ ] Is there a circuit breaker on compression retries?

**Memory**
- [ ] Are there any relative date references ("next week", "yesterday")?
- [ ] Is memory extraction blocking the main session?

**Multi-Agent** (if sub-agents are used)
- [ ] Are sub-agents receiving full conversation history instead of the minimum prefix?
- [ ] Are read-only tasks using General Purpose instead of Explore type?

Report any violations with spec section reference and suggested fix.

---

## Code Output Conventions

- Language: TypeScript by default (switch to Python if the user's project uses Python)
- Every generated code block includes a comment citing which spec rule it implements
- Generate only the skeleton unless the user explicitly asks for full implementation
- Prefer showing the interface contract before the implementation

Example:
```typescript
// Spec § Component 1: AsyncGenerator as loop signature
async function* dialogLoop(
  initialMessage: string,
  deps: QueryDeps
): AsyncGenerator<StreamEvent> {
  // ...
}
```
