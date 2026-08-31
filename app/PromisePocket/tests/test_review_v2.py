from datetime import datetime, timedelta, timezone
import unittest

from promise_pocket.ledger_v2 import (
    InMemoryPromiseLedgerStore,
    PromiseEvidence,
    PromiseLedger,
    PromiseState,
)
from promise_pocket.review_v2 import PromiseReviewKind, build_review_queue


NOW = datetime(2026, 8, 31, 14, 0, tzinfo=timezone.utc)


class PromiseReviewV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = PromiseLedger(
            InMemoryPromiseLedgerStore(),
            clock=lambda: NOW,
        )

    def candidate(self, source_id: str, **overrides):
        values = {
            "actor_id": "zoe",
            "deliverable": "send the revised document",
            "raw_text": "I promise I'll send the revised document.",
            "confidence": 0.95,
            "source": "gmail",
            "source_id": source_id,
            "due_at": NOW + timedelta(hours=1),
        }
        values.update(overrides)
        return self.ledger.create_candidate(**values)

    def test_queue_prioritizes_likely_done_then_overdue_then_candidate(self):
        candidate = self.candidate("candidate")

        overdue = self.candidate(
            "overdue",
            deliverable="send the signed contract",
            due_at=NOW - timedelta(seconds=1),
        )
        self.ledger.confirm(actor_id="zoe", commitment_id=overdue.commitment_id)

        likely_done = self.candidate(
            "likely-done",
            deliverable="send the final mockup",
        )
        self.ledger.confirm(
            actor_id="zoe",
            commitment_id=likely_done.commitment_id,
        )
        self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=likely_done.commitment_id,
            evidence=PromiseEvidence(
                kind="handoff",
                source="gmail",
                summary="The final mockup appears to have been sent.",
                confidence=0.95,
                observed_at=NOW,
            ),
        )

        queue = build_review_queue(self.ledger, actor_id="zoe", now=NOW)

        self.assertEqual(
            [
                PromiseReviewKind.CONFIRM_LIKELY_DONE,
                PromiseReviewKind.RESOLVE_OVERDUE,
                PromiseReviewKind.CONFIRM_CANDIDATE,
            ],
            [item.kind for item in queue],
        )
        self.assertEqual(
            [likely_done.commitment_id, overdue.commitment_id, candidate.commitment_id],
            [item.commitment_id for item in queue],
        )

    def test_review_never_marks_likely_done_record_done(self):
        record = self.candidate("likely-done")
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)
        self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=record.commitment_id,
            evidence=PromiseEvidence(
                kind="handoff",
                source="gmail",
                summary="The deliverable appears to have been sent.",
                confidence=0.9,
                observed_at=NOW,
            ),
        )

        queue = build_review_queue(self.ledger, actor_id="zoe", now=NOW)
        stored = self.ledger.get(actor_id="zoe", commitment_id=record.commitment_id)

        self.assertEqual(1, len(queue))
        self.assertEqual(PromiseState.LIKELY_DONE, stored.status)
        self.assertIsNone(stored.completed_at)

    def test_active_promise_at_exact_deadline_is_not_reviewed(self):
        record = self.candidate("boundary", due_at=NOW)
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)

        queue = build_review_queue(self.ledger, actor_id="zoe", now=NOW)

        self.assertEqual([], queue)
        self.assertEqual(
            PromiseState.ACTIVE,
            self.ledger.get(actor_id="zoe", commitment_id=record.commitment_id).status,
        )

    def test_done_and_canceled_promises_are_not_reviewed(self):
        done = self.candidate("done")
        self.ledger.confirm(actor_id="zoe", commitment_id=done.commitment_id)
        self.ledger.mark_done(actor_id="zoe", commitment_id=done.commitment_id)
        canceled = self.candidate("canceled")
        self.ledger.cancel(actor_id="zoe", commitment_id=canceled.commitment_id)

        self.assertEqual(
            [],
            build_review_queue(self.ledger, actor_id="zoe", now=NOW),
        )

    def test_review_is_actor_isolated(self):
        self.candidate("zoe")
        self.candidate("other", actor_id="someone-else")

        queue = build_review_queue(self.ledger, actor_id="zoe", now=NOW)

        self.assertEqual(1, len(queue))
        self.assertEqual("send the revised document", queue[0].deliverable)


if __name__ == "__main__":
    unittest.main()
