"""Deterministic human-review queue for Pocket Promise v2."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from .ledger_v2 import PromiseLedger, PromiseRecord, PromiseState, utc_now


class PromiseReviewKind(StrEnum):
    CONFIRM_CANDIDATE = "confirm_candidate"
    CONFIRM_LIKELY_DONE = "confirm_likely_done"
    RESOLVE_OVERDUE = "resolve_overdue"


class PromiseReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commitment_id: str
    kind: PromiseReviewKind
    status: PromiseState
    deliverable: str
    prompt: str
    due_at: datetime | None = None


_PRIORITY = {
    PromiseState.LIKELY_DONE: 0,
    PromiseState.OVERDUE: 1,
    PromiseState.CANDIDATE: 2,
}


def _spoken_deliverable(record: PromiseRecord) -> str:
    text = record.deliverable.strip().rstrip(".!?").strip()
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        return text[0].lower() + text[1:]
    return text


def _review_item(record: PromiseRecord) -> PromiseReviewItem | None:
    spoken_deliverable = _spoken_deliverable(record)
    if record.status is PromiseState.LIKELY_DONE:
        return PromiseReviewItem(
            commitment_id=record.commitment_id,
            kind=PromiseReviewKind.CONFIRM_LIKELY_DONE,
            status=record.status,
            deliverable=record.deliverable,
            prompt=(
                f"It looks like you may have finished {spoken_deliverable}. "
                "Should I mark it done?"
            ),
            due_at=record.due_at,
        )
    if record.status is PromiseState.OVERDUE:
        return PromiseReviewItem(
            commitment_id=record.commitment_id,
            kind=PromiseReviewKind.RESOLVE_OVERDUE,
            status=record.status,
            deliverable=record.deliverable,
            prompt=(
                f"This promise is overdue: {spoken_deliverable}. "
                "Have you finished it?"
            ),
            due_at=record.due_at,
        )
    if record.status is PromiseState.CANDIDATE:
        return PromiseReviewItem(
            commitment_id=record.commitment_id,
            kind=PromiseReviewKind.CONFIRM_CANDIDATE,
            status=record.status,
            deliverable=record.deliverable,
            prompt=(
                f"I noticed you promised to {spoken_deliverable}. "
                "Should I track that?"
            ),
            due_at=record.due_at,
        )
    return None


def build_review_queue(
    ledger: PromiseLedger,
    *,
    actor_id: str,
    now: datetime | None = None,
) -> list[PromiseReviewItem]:
    """Return reviewable promises without claiming a human decision.

    Deadline evaluation is deterministic and may move ACTIVE records to
    OVERDUE. No review item can transition a promise to ACTIVE or DONE.
    """

    review_time = now or utc_now()
    if review_time.tzinfo is None:
        raise ValueError("now must include a UTC offset")
    ledger.evaluate_overdue(actor_id=actor_id, now=review_time)

    records = ledger.list_for_actor(actor_id=actor_id)
    records.sort(
        key=lambda record: (
            _PRIORITY.get(record.status, 99),
            (
                record.due_at.astimezone(timezone.utc)
                if record.due_at is not None
                else datetime.max.replace(tzinfo=timezone.utc)
            ),
            record.created_at.astimezone(timezone.utc),
            record.commitment_id,
        )
    )
    return [
        item
        for record in records
        if (item := _review_item(record)) is not None
    ]
