"""Session-level trip state — saved to disk after each major action."""

import json
from datetime import datetime
from pathlib import Path

from config import TRIPS_DIR


class TripContext:
    def __init__(self, trip_id: str) -> None:
        self.trip_id = trip_id
        self.path = TRIPS_DIR / f"{trip_id}.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {
            "trip_id": self.trip_id,
            "created_at": datetime.now().isoformat(),
            "destination": None,
            "dates": {},
            "budget": {"total": 0},
            "itinerary": [],
            "preferences": {},
            "notes": "",
            "conversation_history": [],  # Store full message history
        }

    def save(self) -> None:
        TRIPS_DIR.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = datetime.now().isoformat()
        self.path.write_text(json.dumps(self.data, indent=2))

    def as_context_message(self) -> str:
        """Return a system message summarising the current trip state."""
        if not self.data.get("destination"):
            return "No active trip context. Help the user decide where and when to travel."

        items = self.data.get("itinerary", [])
        total_est = sum(i.get("est_cost", 0) for i in items)
        budget = self.data.get("budget", {}).get("total", 0)

        lines = [
            f"Active trip: {self.data['destination']}",
            f"Dates: {self.data.get('dates', {})}",
            f"Budget: ${budget:,.0f} total, ${total_est:,.0f} estimated spend so far",
            f"Itinerary items: {len(items)}",
        ]
        if items:
            for item in items:
                name = item.get("name", item.get("id", "?"))
                lines.append(f"  - {name} (est. ${item.get('est_cost', 0):,.0f})")
        if self.data.get("notes"):
            lines.append(f"Notes: {self.data['notes']}")
        return "\n".join(lines)

    @classmethod
    def list_trips(cls) -> list[str]:
        """List all saved trip IDs."""
        if not TRIPS_DIR.exists():
            return []
        return [p.stem for p in TRIPS_DIR.glob("*.json")]

    def get_conversation_history(self) -> list[dict]:
        """Get the full conversation history for this trip."""
        return self.data.get("conversation_history", [])

    def update_conversation_history(self, messages: list[dict]) -> None:
        """Update the conversation history and save."""
        # Filter out system messages (we rebuild those each time) - only keep user/assistant/tool
        # Convert any Message objects to dicts to ensure JSON serializability
        filtered = []
        for msg in messages:
            if msg.get("role") in ("user", "assistant", "tool"):
                # Convert to plain dict if it's not already
                if hasattr(msg, '__dict__'):
                    # It's an object, convert to dict
                    msg_dict = {
                        "role": msg.get("role") if hasattr(msg, 'get') else getattr(msg, 'role', None),
                        "content": msg.get("content") if hasattr(msg, 'get') else getattr(msg, 'content', ''),
                    }
                    # Preserve tool_calls if present - convert to dicts
                    if hasattr(msg, 'get'):
                        if msg.get("tool_calls"):
                            msg_dict["tool_calls"] = [
                                {
                                    "function": {
                                        "name": tc.get("function", {}).get("name"),
                                        "arguments": tc.get("function", {}).get("arguments"),
                                    }
                                } if isinstance(tc, dict) else {
                                    "function": {
                                        "name": getattr(tc.function, 'name', ''),
                                        "arguments": getattr(tc.function, 'arguments', {}),
                                    }
                                }
                                for tc in msg["tool_calls"]
                            ]
                        if msg.get("name"):
                            msg_dict["name"] = msg["name"]
                    filtered.append(msg_dict)
                elif isinstance(msg, dict):
                    # Already a dict, but need to convert tool_calls objects
                    msg_dict = {"role": msg["role"]}
                    if "content" in msg:
                        msg_dict["content"] = msg["content"]
                    if "tool_calls" in msg and msg["tool_calls"]:
                        # Convert ToolCall objects to dicts
                        msg_dict["tool_calls"] = [
                            {
                                "function": {
                                    "name": tc.get("function", {}).get("name") if isinstance(tc, dict) else getattr(tc.function, 'name', ''),
                                    "arguments": tc.get("function", {}).get("arguments") if isinstance(tc, dict) else getattr(tc.function, 'arguments', {}),
                                }
                            }
                            for tc in msg["tool_calls"]
                        ]
                    if "name" in msg:
                        msg_dict["name"] = msg["name"]
                    filtered.append(msg_dict)
        
        self.data["conversation_history"] = filtered
        self.save()
