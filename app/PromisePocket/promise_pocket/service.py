"""Deterministic preference storage and replacement policy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .models import Preference, utc_now
from .storage import PreferenceStore


class PreferenceService:
    def __init__(
        self,
        store: PreferenceStore,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._clock = clock

    def get(self, *, actor_id: str, preference_id: str) -> Preference | None:
        return self._store.get(actor_id, preference_id)

    def capture(
        self,
        *,
        actor_id: str,
        preference_key: str,
        category: str,
        statement: str,
        raw_text: str,
        tags: list[str],
        source: str = "chat",
    ) -> Preference:
        """Create or replace an explicit preference with the same stable key."""

        now = self._clock()
        normalized_key = preference_key.strip().casefold().replace(" ", "-")

        existing = next(
            (
                item
                for item in self._store.list_for_actor(actor_id)
                if item.active and item.preference_key == normalized_key
            ),
            None,
        )

        if existing is not None:
            updated = existing.model_copy(
                update={
                    "category": category,
                    "statement": statement,
                    "raw_text": raw_text,
                    "tags": tags,
                    "source": source,
                    "active": True,
                    "updated_at": now,
                }
            )
            self._store.save(updated)
            return updated

        preference = Preference(
            actor_id=actor_id,
            preference_key=normalized_key,
            category=category,
            statement=statement,
            raw_text=raw_text,
            tags=tags,
            source=source,
            created_at=now,
            updated_at=now,
        )
        self._store.save(preference)
        return preference

    def list_preferences(self, *, actor_id: str) -> list[Preference]:
        return sorted(
            [item for item in self._store.list_for_actor(actor_id) if item.active],
            key=lambda item: (item.category.casefold(), item.preference_key),
        )

    def forget(self, *, actor_id: str, preference_id: str) -> Preference:
        preference = self._store.get(actor_id, preference_id)
        if preference is None:
            raise ValueError("preference was not found for this actor")
        updated = preference.model_copy(
            update={"active": False, "updated_at": self._clock()}
        )
        self._store.save(updated)
        return updated
