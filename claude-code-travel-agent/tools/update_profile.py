"""Tools for reading and updating the user profile.

Two update modes:
  source='explicit'  — user commanded it (/profile set ...) → save immediately
  source='inferred'  — agent detected it from conversation  → stage for confirmation
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Field-type metadata
# ---------------------------------------------------------------------------
_LIST_FIELDS = {"preferred_airlines", "preferred_hotel_chains", "interests", "avoid"}
_BUDGET_FIELDS = {"flight_max_usd", "hotel_max_per_night_usd"}
# All other fields are plain strings: name, home_airport, seat_preference


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def get_profile() -> str:
    """Return the current user profile as a human-readable string."""
    from memory.user_profile import UserProfile
    return UserProfile().as_context_message()


def update_profile(field: str, value: str, source: str = "explicit") -> str:
    """Update or stage a user profile field.

    Args:
        field:  Profile field name, e.g. 'home_airport', 'interests', 'seat_preference'.
                Budget sub-fields: 'flight_max_usd', 'hotel_max_per_night_usd'.
        value:  New value. For list fields, use comma-separated strings, e.g. 'United,Delta'.
        source: 'explicit' saves immediately; 'inferred' stages and asks for confirmation.

    Returns a plain-text result the agent reads aloud.
    """
    from memory.user_profile import UserProfile
    profile = UserProfile()

    if source == "inferred":
        return profile.stage_update(field, value)

    _apply_field(profile, field, value)
    profile.save()
    human = field.replace("_", " ").title()
    return f"Profile updated: {human} = {value!r}. Saved to profile."


def confirm_profile_update(field: str) -> str:
    """Commit a previously staged (inferred) profile value.

    Call this after the user says 'yes' to a staged preference.
    """
    from memory.user_profile import UserProfile
    profile = UserProfile()
    return profile.confirm_staged(field)


def discard_profile_update(field: str) -> str:
    """Discard a staged (inferred) profile value.

    Call this when the user says 'no' to a staged preference.
    """
    from memory.user_profile import UserProfile
    profile = UserProfile()
    if field in profile._pending:
        value = profile._pending.pop(field)
        human = field.replace("_", " ").title()
        return f"Discarded staged update: {human} = {value!r}. Profile unchanged."
    return f"Nothing pending for '{field}'."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_field(profile, field: str, value: str) -> None:
    """Write a value into profile.data with correct type handling."""
    if field in _LIST_FIELDS:
        new_items = [v.strip() for v in value.split(",") if v.strip()]
        existing: list = profile.data.get(field, [])
        # Merge — avoid duplicates while preserving order.
        for item in new_items:
            if item not in existing:
                existing.append(item)
        profile.data[field] = existing

    elif field in _BUDGET_FIELDS:
        try:
            amount = int(value.replace("$", "").replace(",", "").strip())
            profile.data.setdefault("budget_defaults", {})[field] = amount
        except ValueError:
            pass  # leave unchanged on bad input

    else:
        profile.data[field] = value
