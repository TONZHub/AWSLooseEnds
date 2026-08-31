from datetime import datetime, timedelta, timezone
import unittest

from pydantic import ValidationError

from promise_pocket.ledger_v2 import (
    InMemoryPromiseLedgerStore,
    InvalidPromiseTransition,
    PromiseEvidence,
    PromiseLedger,
    PromiseRecord,
    PromiseState,
)
from promise_pocket.ledger_v2_storage import DynamoDbPromiseLedgerStore


NOW = datetime(2026, 8, 30, 17, 0, tzinfo=timezone.utc)


class PromiseLedgerV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryPromiseLedgerStore()
        self.ledger = PromiseLedger(self.store, clock=lambda: NOW)

    def candidate(self, **overrides):
        values = {
            "actor_id": "zoe",
            "deliverable": "send the final mockups",
            "raw_text": "I'll get the final mockups over to you by Tuesday evening.",
            "confidence": 0.94,
            "source": "gmail",
            "source_id": "gmail-message-123",
            "people": ["Jordan"],
            "due_at": NOW + timedelta(days=2),
            "evidence_hint": "Look for a later outgoing message with the final mockups attached.",
        }
        values.update(overrides)
        return self.ledger.create_candidate(**values)

    def test_detected_message_starts_as_candidate(self):
        record = self.candidate()

        self.assertEqual(PromiseState.CANDIDATE, record.status)
        self.assertIsNone(record.confirmed_at)
        self.assertEqual("send the final mockups", record.deliverable)
        self.assertEqual(["Jordan"], record.people)

    def test_user_confirmation_promotes_candidate_to_active(self):
        record = self.candidate()

        active = self.ledger.confirm(
            actor_id="zoe",
            commitment_id=record.commitment_id,
        )

        self.assertEqual(PromiseState.ACTIVE, active.status)
        self.assertEqual(NOW, active.confirmed_at)

    def test_same_source_message_is_idempotent(self):
        first = self.candidate()
        second = self.candidate()

        self.assertEqual(first.commitment_id, second.commitment_id)
        self.assertEqual(1, len(self.ledger.list_for_actor(actor_id="zoe")))

    def test_evidence_marks_likely_done_but_not_done(self):
        record = self.candidate()
        active = self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)
        evidence = PromiseEvidence(
            kind="outgoing_attachment",
            source="gmail",
            source_id="gmail-message-456",
            summary="A later outgoing email to Jordan contains an attachment named final-mockups.pdf.",
            confidence=0.89,
            observed_at=NOW + timedelta(days=1),
        )

        likely_done = self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=active.commitment_id,
            evidence=evidence,
        )

        self.assertEqual(PromiseState.LIKELY_DONE, likely_done.status)
        self.assertIsNone(likely_done.completed_at)
        self.assertEqual([evidence], likely_done.evidence)

    def test_user_can_confirm_likely_done_as_done(self):
        record = self.candidate()
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)
        likely_done = self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=record.commitment_id,
            evidence=PromiseEvidence(
                kind="reply",
                source="gmail",
                summary="Jordan replied thanks after receiving the mockups.",
                confidence=0.92,
                observed_at=NOW,
            ),
        )

        done = self.ledger.mark_done(
            actor_id="zoe",
            commitment_id=likely_done.commitment_id,
        )

        self.assertEqual(PromiseState.DONE, done.status)
        self.assertEqual(NOW, done.completed_at)

    def test_likely_done_can_be_reopened_when_evidence_is_wrong(self):
        record = self.candidate()
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)
        self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=record.commitment_id,
            evidence=PromiseEvidence(
                kind="weak_match",
                source="gmail",
                summary="A related message may have contained the deliverable.",
                confidence=0.61,
                observed_at=NOW,
            ),
        )

        reopened = self.ledger.reopen(
            actor_id="zoe",
            commitment_id=record.commitment_id,
        )

        self.assertEqual(PromiseState.ACTIVE, reopened.status)

    def test_candidate_cannot_be_marked_done_without_confirmation(self):
        record = self.candidate()

        with self.assertRaises(InvalidPromiseTransition):
            self.ledger.mark_done(
                actor_id="zoe",
                commitment_id=record.commitment_id,
            )

    def test_actor_records_are_isolated(self):
        zoe = self.candidate()
        other = self.candidate(
            actor_id="someone-else",
            source_id="gmail-message-other",
        )

        self.assertEqual(
            [zoe.commitment_id],
            [item.commitment_id for item in self.ledger.list_for_actor(actor_id="zoe")],
        )
        self.assertIsNone(
            self.ledger.get(actor_id="zoe", commitment_id=other.commitment_id)
        )

    def test_naive_deadline_is_rejected(self):
        with self.assertRaises(ValidationError):
            PromiseRecord(
                actor_id="zoe",
                deliverable="send the mockups",
                raw_text="I'll send the mockups Tuesday",
                confidence=0.9,
                source="gmail",
                due_at=datetime(2026, 9, 1, 18, 0),
            )

    def test_active_promise_becomes_overdue_only_after_due_time(self):
        record = self.candidate(due_at=NOW)
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)

        self.assertEqual([], self.ledger.evaluate_overdue(actor_id="zoe", now=NOW))
        transitioned = self.ledger.evaluate_overdue(
            actor_id="zoe", now=NOW + timedelta(microseconds=1)
        )

        self.assertEqual([record.commitment_id], [item.commitment_id for item in transitioned])
        self.assertEqual(PromiseState.OVERDUE, transitioned[0].status)

    def test_overdue_comparison_respects_timezone_offsets(self):
        eastern = timezone(timedelta(hours=-4))
        record = self.candidate(due_at=datetime(2026, 8, 30, 13, 0, tzinfo=eastern))
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)

        transitioned = self.ledger.evaluate_overdue(
            actor_id="zoe",
            now=datetime(2026, 8, 30, 17, 0, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(1, len(transitioned))

    def test_overdue_evaluation_is_idempotent(self):
        record = self.candidate(due_at=NOW - timedelta(minutes=1))
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)

        first = self.ledger.evaluate_overdue(actor_id="zoe", now=NOW)
        second = self.ledger.evaluate_overdue(actor_id="zoe", now=NOW)

        self.assertEqual(1, len(first))
        self.assertEqual([], second)

    def test_nudges_include_only_unresolved_overdue_promises(self):
        overdue = self.candidate(due_at=NOW - timedelta(minutes=1))
        self.ledger.confirm(actor_id="zoe", commitment_id=overdue.commitment_id)
        done = self.candidate(
            source_id="done-message", due_at=NOW - timedelta(minutes=2)
        )
        self.ledger.confirm(actor_id="zoe", commitment_id=done.commitment_id)
        self.ledger.mark_done(actor_id="zoe", commitment_id=done.commitment_id)

        nudges = self.ledger.prepare_overdue_nudges(actor_id="zoe", now=NOW)

        self.assertEqual([overdue.commitment_id], [item["commitment_id"] for item in nudges])

    def test_likely_done_promise_is_never_nudged(self):
        record = self.candidate(due_at=NOW - timedelta(minutes=1))
        self.ledger.confirm(actor_id="zoe", commitment_id=record.commitment_id)
        self.ledger.mark_likely_done(
            actor_id="zoe",
            commitment_id=record.commitment_id,
            evidence=PromiseEvidence(
                kind="handoff",
                source="gmail",
                summary="The promised item appears to have been sent.",
                confidence=0.9,
                observed_at=NOW,
            ),
        )

        self.assertEqual([], self.ledger.prepare_overdue_nudges(actor_id="zoe", now=NOW))


class DynamoDbV2CompatibilityTests(unittest.TestCase):
    def record(self):
        return PromiseRecord(
            actor_id="zoe",
            deliverable="send the final mockups",
            raw_text="I'll send the final mockups by Tuesday evening.",
            people=["Jordan"],
            due_at=NOW + timedelta(days=2),
            confidence=0.94,
            source="gmail",
            source_id="gmail-message-123",
            status=PromiseState.ACTIVE,
            confirmed_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )

    def test_v2_item_keeps_existing_table_keys_and_marks_record_type(self):
        record = self.record()

        item = DynamoDbPromiseLedgerStore._to_item(record)

        self.assertEqual("zoe", item["actor_id"])
        self.assertEqual(record.commitment_id, item["commitment_id"])
        self.assertEqual("promise_v2", item["record_type"])
        self.assertEqual("zoe#active", item["actor_status"])

    def test_v2_item_round_trips(self):
        record = self.record()
        item = DynamoDbPromiseLedgerStore._to_item(record)

        restored = DynamoDbPromiseLedgerStore._from_item(item)

        self.assertEqual(record, restored)

    def test_legacy_commitment_item_is_ignored(self):
        legacy_item = {
            "actor_id": "zoe",
            "commitment_id": "legacy-123",
            "summary": "Call Mom",
            "status": "pending",
        }

        self.assertIsNone(DynamoDbPromiseLedgerStore._from_item(legacy_item))


if __name__ == "__main__":
    unittest.main()
