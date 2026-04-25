# /model — Switch LLM provider and model at runtime

Switch to a different LLM provider or model without restarting the agent.

## Usage

```
/model <provider> <model-name>
/model <model-name>              (shorthand — keeps current provider for ollama)
```

## Examples

```
/model ollama qwen3:16b                  → switch to larger Ollama model
/model anthropic claude-opus-4-5         → switch to Anthropic Claude
/model anthropic claude-sonnet-4-5       → switch to Claude Sonnet
/model openai gpt-4o                     → switch to OpenAI GPT-4o
/model groq llama-3.3-70b-versatile      → switch to Groq (fast inference)
/model together meta-llama/Llama-3-70b-chat-hf  → switch to Together.ai
/model gemini gemini-2.0-flash           → switch to Google Gemini
```

## How to execute this command

1. Parse the argument after `/model`:
   - If two words: first is provider, second is model name.
   - If one word containing a colon (like `qwen3:16b`): treat as Ollama model shorthand.
   - If one word without colon: treat as model name for the current provider.

2. Validate the provider is one of: ollama, anthropic, openai, groq, together, gemini.
   If unknown, say so and list supported providers.

3. Check that the required API key / host is configured in config.py for that provider.
   - anthropic → needs ANTHROPIC_API_KEY
   - openai    → needs OPENAI_API_KEY
   - groq      → needs GROQ_API_KEY
   - together  → needs TOGETHER_API_KEY
   - gemini    → needs GEMINI_API_KEY
   - ollama    → needs Ollama running locally

4. Create a new LLMClient and update the session.

5. Confirm to the user:
   "✓ Switched to {provider}/{model}. All subsequent messages will use this model."

6. If the provider requires a key that is not set, say:
   "⚠ {PROVIDER_API_KEY} is not set. Set it in your environment and restart, or run:
   export {PROVIDER_API_KEY}=your-key-here"
   Do NOT proceed with the switch in that case.
