"""Long-term user preferences — loaded at session start."""

import json
from pathlib import Path

from config import PROFILE_PATH

DEFAULT_PROFILE = {
    "name": "",
    "home_airport": "",
    "preferred_airlines": [],
    "preferred_hotel_chains": [],
    "loyalty_programs": {},
    "seat_preference": "window",
    "budget_defaults": {
        "flight_max_usd": 800,
        "hotel_max_per_night_usd": 250,
    },
    "avoid": [],
    "interests": [],
    "past_trips": [],
}


class UserProfile:
    # Class-level staging dict: inferred values awaiting user confirmation.
    # Shared across all instances within a process session.
    _pending: dict[str, str] = {}

    def __init__(self) -> None:
        self.data = self._load()

    def _load(self) -> dict:
        if PROFILE_PATH.exists():
            return {**DEFAULT_PROFILE, **json.loads(PROFILE_PATH.read_text())}
        return DEFAULT_PROFILE.copy()

    def save(self) -> None:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(self.data, indent=2))

    def as_context_message(self) -> str:
        """Return a system message with user preferences."""
        lines = ["User profile:"]
        if self.data.get("name"):
            lines.append(f"  Name: {self.data['name']}")
        if self.data.get("home_airport"):
            lines.append(f"  Home airport: {self.data['home_airport']}")
        if self.data.get("interests"):
            lines.append(f"  Interests: {', '.join(self.data['interests'])}")
        if self.data.get("preferred_airlines"):
            lines.append(f"  Preferred airlines: {', '.join(self.data['preferred_airlines'])}")
        if self.data.get("preferred_hotel_chains"):
            lines.append(f"  Preferred hotel chains: {', '.join(self.data['preferred_hotel_chains'])}")

        defaults = self.data.get("budget_defaults", {})
        if defaults:
            lines.append(
                f"  Budget defaults: flights max ${defaults.get('flight_max_usd', 0)}, "
                f"hotel max ${defaults.get('hotel_max_per_night_usd', 0)}/night"
            )
        if self.data.get("avoid"):
            lines.append(f"  Avoid: {', '.join(self.data['avoid'])}")
        if self.data.get("past_trips"):
            lines.append(f"  Past trips: {len(self.data['past_trips'])} recorded")

        if len(lines) == 1:
            return "No user profile set. Ask the user for their home airport and preferences."
        return "\n".join(lines)

    def stage_update(self, field: str, value: str) -> str:
        """Hold an inferred value until the user confirms. Returns a confirmation prompt."""
        UserProfile._pending[field] = value
        human = field.replace("_", " ").title()
        return (
            f"I noticed you mentioned {human}: {value!r}. "
            f"Would you like me to save this to your profile? (yes/no)"
        )

    def confirm_staged(self, field: str) -> str:
        """Commit a previously staged value to disk."""
        if field not in UserProfile._pending:
            return f"No pending update for '{field}'. Nothing was saved."
        value = UserProfile._pending.pop(field)
        from tools.update_profile import _apply_field
        _apply_field(self, field, value)
        self.save()
        human = field.replace("_", " ").title()
        return f"Saved to profile: {human} = {value!r}"

    def pending_fields(self) -> dict[str, str]:
        """Return a copy of all currently staged (unconfirmed) fields."""
        return dict(UserProfile._pending)

    def update(self, **kwargs) -> None:
        """Update profile fields and save."""
        self.data.update(kwargs)
        self.save()
