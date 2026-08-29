"""Validated Promise Pocket records and attention requests."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommitmentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELED = "canceled"


class AttentionReason(StrEnum):
    CLARIFICATION = "clarification"
    DUE = "due"
    BLOCKED = "blocked"


class Commitment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    commitment_id: str = Field(default_factory=lambda: uuid4().hex)
    actor_id: str = Field(min_length=1)
    summary: str = Field(min_length=1, max_length=240)
    raw_text: str = Field(min_length=1, max_length=4000)
    due_at: datetime | None = None
    people: list[str] = Field(default_factory=list)
    human_action_required: bool
    missing_information: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    source: str = "chat"
    status: CommitmentStatus = CommitmentStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("due_at", "created_at", "updated_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime values must include a UTC offset")
        return value

    @field_validator("people", "missing_information")
    @classmethod
    def remove_empty_duplicates(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                result.append(normalized)
                seen.add(key)
        return result

    @property
    def next_review_at(self) -> datetime | None:
        if self.missing_information or self.blocked_reason:
            return self.created_at
        return self.due_at


class AttentionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commitment_id: str
    summary: str
    reason: AttentionReason
    prompt: str
    due_at: datetime | None = None
