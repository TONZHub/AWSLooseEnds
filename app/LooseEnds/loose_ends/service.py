"""Deterministic commitment capture and attention policy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import re

from .models import (
    AttentionItem,
    AttentionReason,
    Commitment,
    CommitmentStatus,
    utc_now,
)
from .storage import CommitmentStore


def _has_explicit_clock_time(text: str) -> bool:
    return bool(
        re.search(r"\b(?:noon|midnight)\b", text, re.IGNORECASE)
        or re.search(
            r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(r"\bat\s+\d{1,2}(?::\d{2})?\b", text, re.IGNORECASE)
    )


class CommitmentService:
    def __init__(
        self,
        store: CommitmentStore,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store
        self._clock = clock

    def capture(
        self,
        *,
        actor_id: str,
        summary: str,
        raw_text: str,
        due_at: datetime | None,
        people: list[str],
        human_action_required: bool,
        missing_information: list[str],
    ) -> Commitment:
        now = self._clock()
        questions = list(missing_information)
        if due_at is not None and not _has_explicit_clock_time(raw_text):
            due_at = None
            if not questions:
                questions.append("What time should I bring this back?")
        commitment = Commitment(
            actor_id=actor_id,
            summary=summary,
            raw_text=raw_text,
            due_at=due_at,
            people=people,
            human_action_required=human_action_required,
            missing_information=questions,
            created_at=now,
            updated_at=now,
        )
        self._store.save(commitment)
        return commitment

    def review(self, *, actor_id: str, now: datetime | None = None) -> list[AttentionItem]:
        review_time = now or self._clock()
        if review_time.tzinfo is None:
            raise ValueError("review time must include a UTC offset")

        attention: list[AttentionItem] = []
        for commitment in self._store.list_for_actor(actor_id):
            if commitment.status is not CommitmentStatus.PENDING:
                continue

            if commitment.missing_information:
                attention.append(
                    AttentionItem(
                        commitment_id=commitment.commitment_id,
                        summary=commitment.summary,
                        reason=AttentionReason.CLARIFICATION,
                        prompt=commitment.missing_information[0],
                        due_at=commitment.due_at,
                    )
                )
                continue

            if commitment.blocked_reason:
                attention.append(
                    AttentionItem(
                        commitment_id=commitment.commitment_id,
                        summary=commitment.summary,
                        reason=AttentionReason.BLOCKED,
                        prompt=commitment.blocked_reason,
                        due_at=commitment.due_at,
                    )
                )
                continue

            if (
                commitment.human_action_required
                and commitment.due_at is not None
                and commitment.due_at <= review_time
            ):
                attention.append(
                    AttentionItem(
                        commitment_id=commitment.commitment_id,
                        summary=commitment.summary,
                        reason=AttentionReason.DUE,
                        prompt=f"This needs you now: {commitment.summary}",
                        due_at=commitment.due_at,
                    )
                )

        return sorted(
            attention,
            key=lambda item: (
                item.due_at is None,
                item.due_at or review_time,
                item.commitment_id,
            ),
        )
