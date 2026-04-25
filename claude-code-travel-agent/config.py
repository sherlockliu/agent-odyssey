"""Configuration for the travel agent."""

import os
from pathlib import Path


# ── Load .env file (stdlib, no python-dotenv needed) ─────────────────────────
def _load_dotenv(path: Path = Path(__file__).parent / ".env") -> None:
    """Parse KEY=value lines from .env. Shell env always takes priority."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# ── LLM provider ─────────────────────────────────────────────────────────────
# Which provider and model to use.  Override with environment variables or
# the /model command at runtime.
# Supported providers: ollama | anthropic | openai | groq | together | gemini
LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "ollama")
LLM_MODEL:    str = os.environ.get("LLM_MODEL",    "qwen3:8b")

# Per-provider connection / auth settings.
LLM_PROVIDER_CONFIGS: dict[str, dict] = {
    "ollama": {
        "host": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
    },
    "anthropic": {
        "api_key":    os.environ.get("ANTHROPIC_API_KEY"),
        "max_tokens": 4096,
    },
    "openai": {
        "api_key":  os.environ.get("OPENAI_API_KEY"),
        "base_url": os.environ.get("OPENAI_BASE_URL"),
    },
    "groq": {
        "api_key":  os.environ.get("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
    },
    "together": {
        "api_key":  os.environ.get("TOGETHER_API_KEY"),
        "base_url": "https://api.together.xyz/v1",
    },
    "gemini": {
        "api_key": os.environ.get("GEMINI_API_KEY"),
    },
}

# Backward-compat aliases (used by compressor and legacy code).
OLLAMA_MODEL: str = LLM_MODEL
OLLAMA_HOST:  str = LLM_PROVIDER_CONFIGS["ollama"]["host"]  # type: ignore[assignment]

# ── Context window management ─────────────────────────────────────────────────
CONTEXT_WINDOW_LIMIT: int   = 32000  # Fallback; overridden by LLMClient.context_window
COMPRESS_THRESHOLD:   float = 0.80   # Compress when 80% full
TOKENS_PER_CHAR:      float = 0.25   # Rough estimate: 1 token ≈ 4 chars

# ── Memory paths ──────────────────────────────────────────────────────────────
PROJECT_DIR      = Path(__file__).parent
TRAVEL_AGENT_DIR = PROJECT_DIR / ".travel-agent"
TRIPS_DIR        = TRAVEL_AGENT_DIR / "trips"
PROFILE_PATH     = TRAVEL_AGENT_DIR / "profile.json"

# ── Dummy / test data ─────────────────────────────────────────────────────────
DUMMY_DATA_DIR = Path(__file__).parent / "dummy_data"

# ── Agent modes ───────────────────────────────────────────────────────────────
MODES = {
    "passive":   "Answer questions only. Do not proactively search or suggest.",
    "default":   "Guide the user through planning. Suggest next steps, confirm before committing.",
    "proactive": "Plan the full trip autonomously based on stated preferences. Present at the end.",
}
DEFAULT_MODE = "default"

# ── Tool providers ────────────────────────────────────────────────────────────
# Ordered list of provider names to register. First-registered wins on dispatch.
ENABLED_TOOL_PROVIDERS: list[str] = [
    "builtin",
    "weather",
    "activities",
    "online_destinations",
]

# Per-tool-provider config. mode="mock" requires no API key.
WEATHER_CONFIG: dict = {
    "mode":    os.environ.get("WEATHER_MODE", "mock"),   # "mock" | "api"
    "api_key": os.environ.get("WEATHER_API_KEY"),        # not required for Open-Meteo
    "api_url": "https://api.open-meteo.com/v1/forecast",
}

ACTIVITIES_CONFIG: dict = {
    "mode":    os.environ.get("ACTIVITIES_MODE", "mock"),  # "mock" | "api"
    "api_key": os.environ.get("TICKETMASTER_API_KEY"),
}

ONLINE_DESTINATIONS_CONFIG: dict = {
    "mode":    os.environ.get("ONLINE_DESTINATIONS_MODE", "mock"),  # "mock" | "api"
    "api_key": os.environ.get("TRAVEL_API_KEY"),
}
