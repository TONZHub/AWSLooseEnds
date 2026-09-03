"""Pocket Promise v2: durable lifecycle for detected human commitments.

This module intentionally does not know about Gmail, Alexa, Render, or a model provider.
Adapters may create candidate records and attach evidence; only explicit user
confirmation promotes a candidate into an active promise.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PromiseState(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    LIKELY_DONE = "likely_done"
    OVERDUE = "overdue"
    DONE = "done"
    CANCELED = "canceled"


class PromiseEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=80)
    source_id: str | None = Field(default=None, max_length=512)
    summary: str = Field(min_length=1, max_length=1000)
    supporting_text: str | None = Field(default=None, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    observed_at: datetime = Field(default_factory=utc_now)

    @field_validator("observed_at")
    @classmethod
    def require_aware_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must include a UTC offset")
        return value


class PromiseRecord(BaseModel):
    """One possible or confirmed obligation owned by one actor.

    ``commitment_id`` intentionally retains the existing DynamoDB sort-key name
    so the v2 ledger can reuse the deployed table during the hackathon pivot.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    commitment_id: str = Field(default_factory=lambda: uuid4().hex)
    actor_id: str = Field(min_length=1)
    deliverable: str = Field(min_length=1, max_length=500)
    raw_text: str = Field(min_length=1, max_length=8000)
    people: list[str] = Field(default_factory=list)
    due_at: datetime | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(min_length=1, max_length=80)
    source_id: str | None = Field(default=None, max_length=512)
    evidence_hint: str | None = Field(default=None, max_length=1000)
    status: PromiseState = PromiseState.CANDIDATE
    evidence: list[PromiseEvidence] = Field(default_factory=list)
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("due_at", "confirmed_at", "completed_at", "created_at", "updated_at")
    @classmethod
    def require_aware_datetimes(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("datetime values must include a UTC offset")
        return value

    @field_validator("people")
    @classmethod
    def remove_empty_duplicate_people(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result


class PromiseLedgerStore(Protocol):
    def save(self, record: PromiseRecord) -> None: ...

    def get(self, actor_id: str, commitment_id: str) -> PromiseRecord | None: ...

    def list_for_actor(self, actor_id: str) -> list[PromiseRecord]: ...


class InMemoryPromiseLedgerStore:
    def __init__(self) -> None:
        self._items: dict[str, PromiseRecord] = {}

    def save(self, record: PromiseRecord) -> None:
        self._items[record.commitment_id] = record

    def get(self, actor_id: str, commitment_id: str) -> PromiseRecord | None:
        item = self._items.get(commitment_id)
        return item if item is not None and item.actor_id == actor_id else None

    def list_for_actor(self, actor_id: str) -> list[PromiseRecord]:
        return [item for item in self._items.values() if item.actor_id == actor_id]


class InvalidPromiseTransition(ValueError):
    pass


class PromiseLedger:
    """Deterministic lifecycle policy; models may propose, humans confirm."""

    def __init__(
        self,
        store: PromiseLedgerStore,
        clock=utc_now,
    ) -> None:
        self._store = store
        self._clock = clock

    def get(self, *, actor_id: str, commitment_id: str) -> PromiseRecord | None:
        return self._store.get(actor_id, commitment_id)

    def list_for_actor(self, *, actor_id: str) -> list[PromiseRecord]:
        return self._store.list_for_actor(actor_id)

    def create_candidate(
        self,
        *,
        actor_id: str,
        deliverable: str,
        raw_text: str,
        confidence: float,
        source: str,
        source_id: str | None = None,
        people: list[str] | None = None,
        due_at: datetime | None = None,
        evidence_hint: str | None = None,
    ) -> PromiseRecord:
        # Pollers are expected to see the same message repeatedly. A stable
        # source ID makes ingestion idempotent instead of creating duplicates.
        if source_id:
            for existing in self._store.list_for_actor(actor_id):
                if existing.source == source and existing.source_id == source_id:
                    return existing

        now = self._clock()
        record = PromiseRecord(
            actor_id=actor_id,
            deliverable=deliverable,
            raw_text=raw_text,
            people=people or [],
            due_at=due_at,
            confidence=confidence,
            source=source,
            source_id=source_id,
            evidence_hint=evidence_hint,
            status=PromiseState.CANDIDATE,
            created_at=now,
            updated_at=now,
        )
        self._store.save(record)
        return record

    def confirm(self, *, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status is not PromiseState.CANDIDATE:
            raise InvalidPromiseTransition(
                f"cannot confirm promise from state {record.status.value}"
            )
        now = self._clock()
        return self._save(record, status=PromiseState.ACTIVE, confirmed_at=now, updated_at=now)

    def cancel(self, *, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status in {PromiseState.DONE, PromiseState.CANCELED}:
            raise InvalidPromiseTransition(
                f"cannot cancel promise from state {record.status.value}"
            )
        return self._save(record, status=PromiseState.CANCELED, updated_at=self._clock())

    def mark_overdue(self, *, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status is not PromiseState.ACTIVE:
            raise InvalidPromiseTransition(
                f"cannot mark overdue from state {record.status.value}"
            )
        return self._save(record, status=PromiseState.OVERDUE, updated_at=self._clock())

    def evaluate_overdue(
        self,
        *,
        actor_id: str,
        now: datetime | None = None,
    ) -> list[PromiseRecord]:
        """Move due, unresolved ACTIVE promises to OVERDUE.

        A deadline is considered passed only when ``now`` is strictly later
        than ``due_at``. Repeated evaluations are idempotent because only
        ACTIVE records are eligible for the transition.
        """

        evaluated_at = now or self._clock()
        if evaluated_at.tzinfo is None:
            raise ValueError("now must include a UTC offset")

        transitioned: list[PromiseRecord] = []
        for record in self._store.list_for_actor(actor_id):
            if (
                record.status is PromiseState.ACTIVE
                and record.due_at is not None
                and evaluated_at > record.due_at
            ):
                transitioned.append(
                    self._save(
                        record,
                        status=PromiseState.OVERDUE,
                        updated_at=evaluated_at,
                    )
                )
        return transitioned

    def prepare_overdue_nudges(
        self,
        *,
        actor_id: str,
        now: datetime | None = None,
    ) -> list[dict[str, str]]:
        """Prepare, but do not send, nudges for unresolved overdue promises."""

        self.evaluate_overdue(actor_id=actor_id, now=now)
        return [
            {
                "commitment_id": record.commitment_id,
                "deliverable": record.deliverable,
                "due_at": record.due_at.isoformat(),
                "message": f"Still unresolved: {record.deliverable}",
            }
            for record in self._store.list_for_actor(actor_id)
            if record.status is PromiseState.OVERDUE and record.due_at is not None
        ]

    def mark_likely_done(
        self,
        *,
        actor_id: str,
        commitment_id: str,
        evidence: PromiseEvidence,
    ) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status not in {
            PromiseState.ACTIVE,
            PromiseState.OVERDUE,
            PromiseState.LIKELY_DONE,
        }:
            raise InvalidPromiseTransition(
                f"cannot mark likely done from state {record.status.value}"
            )
        if any(e.source == evidence.source and e.source_id == evidence.source_id for e in record.evidence):
            return record
        return self._save(
            record,
            status=PromiseState.LIKELY_DONE,
            evidence=[*record.evidence, evidence],
            updated_at=self._clock(),
        )

    def reopen(self, *, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status is not PromiseState.LIKELY_DONE:
            raise InvalidPromiseTransition(
                f"cannot reopen promise from state {record.status.value}"
            )
        return self._save(record, status=PromiseState.ACTIVE, updated_at=self._clock())

    def mark_done(self, *, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._require(actor_id, commitment_id)
        if record.status not in {
            PromiseState.ACTIVE,
            PromiseState.OVERDUE,
            PromiseState.LIKELY_DONE,
        }:
            raise InvalidPromiseTransition(
                f"cannot complete promise from state {record.status.value}"
            )
        now = self._clock()
        return self._save(
            record,
            status=PromiseState.DONE,
            completed_at=now,
            updated_at=now,
        )

    def _require(self, actor_id: str, commitment_id: str) -> PromiseRecord:
        record = self._store.get(actor_id, commitment_id)
        if record is None:
            raise ValueError("promise was not found for this actor")
        return record

    def _save(self, record: PromiseRecord, **updates) -> PromiseRecord:
        updated = record.model_copy(update=updates)
        self._store.save(updated)
        return updated
