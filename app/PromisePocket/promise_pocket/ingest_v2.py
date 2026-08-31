"""Source-agnostic ingestion contract for Pocket Promise v2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .ledger_v2 import PromiseLedger, PromiseRecord


_GENERIC_PEOPLE = {
    "user",
    "the user",
    "sender",
    "the sender",
    "recipient",
    "the recipient",
    "me",
    "you",
}


class SourceMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=512)
    direction: Literal["sent", "received"]
    body: str = Field(min_length=1, max_length=50000)
    subject: str | None = Field(default=None, max_length=1000)
    participants: list[str] = Field(default_factory=list)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_aware_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a UTC offset")
        return value


class PromiseExtraction(BaseModel):
    """Structured judgment produced by the Arbiter model for one source item."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_commitment: bool
    deliverable: str | None = Field(default=None, max_length=500)
    people: list[str] = Field(default_factory=list)
    due_at: datetime | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_text: str | None = Field(default=None, max_length=2000)
    evidence_hint: str | None = Field(default=None, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("due_at")
    @classmethod
    def require_aware_due_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("due_at must include a UTC offset")
        return value

    @model_validator(mode="after")
    def require_commitment_fields(self):
        if self.is_commitment:
            if not self.deliverable:
                raise ValueError("deliverable is required for a commitment")
            if not self.supporting_text:
                raise ValueError("supporting_text is required for a commitment")
        return self


def _clean_people(values: list[str]) -> list[str]:
    """Keep explicit people/addresses while dropping model-invented role labels."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in _GENERIC_PEOPLE or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


class CandidateIngestor:
    """Apply model judgments without letting the model bypass user consent."""

    def __init__(self, ledger: PromiseLedger, minimum_confidence: float = 0.70) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self._ledger = ledger
        self._minimum_confidence = minimum_confidence

    def apply(
        self,
        *,
        actor_id: str,
        message: SourceMessage,
        extraction: PromiseExtraction,
    ) -> PromiseRecord | None:
        # V0 only detects obligations in things the user actually sent. A
        # promise made *to* the user by somebody else is not the user's burden.
        if message.direction != "sent":
            return None
        if not extraction.is_commitment:
            return None
        if extraction.confidence < self._minimum_confidence:
            return None

        return self._ledger.create_candidate(
            actor_id=actor_id,
            deliverable=extraction.deliverable or "",
            # Store the model-identified exact snippet, not the entire email.
            raw_text=extraction.supporting_text or "",
            confidence=extraction.confidence,
            source=message.source,
            source_id=message.source_id,
            people=_clean_people(extraction.people),
            due_at=extraction.due_at,
            evidence_hint=extraction.evidence_hint,
        )
