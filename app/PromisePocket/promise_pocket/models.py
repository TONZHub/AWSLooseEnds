"""Validated user-owned preference records for Promise Pocket."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Preference(BaseModel):
    """One explicit preference the user asked Promise Pocket to remember.

    ``commitment_id`` is retained as the physical DynamoDB sort key so the
    existing hackathon table can be reused without an infrastructure migration.
    Product-facing code should use ``preference_id``.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    commitment_id: str = Field(default_factory=lambda: uuid4().hex)
    actor_id: str = Field(min_length=1)
    preference_key: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    statement: str = Field(min_length=1, max_length=500)
    raw_text: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list)
    source: str = "chat"
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def preference_id(self) -> str:
        return self.commitment_id

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("datetime values must include a UTC offset")
        return value

    @field_validator("preference_key")
    @classmethod
    def normalize_preference_key(cls, value: str) -> str:
        return value.strip().casefold().replace(" ", "-")

    @field_validator("tags")
    @classmethod
    def remove_empty_duplicate_tags(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                result.append(normalized)
                seen.add(key)
        return result
