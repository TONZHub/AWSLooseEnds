from datetime import datetime, timedelta, timezone
import unittest

from promise_pocket.ingest_v2 import SourceMessage
from promise_pocket.ledger_v2 import InMemoryPromiseLedgerStore, PromiseLedger, PromiseState
from promise_pocket.reconcile_v2 import EvidenceIngestor, EvidenceProposal


NOW = datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)


class EvidenceReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryPromiseLedgerStore()
        self.ledger = PromiseLedger(self.store, clock=lambda: NOW)
        self.ingestor = EvidenceIngestor(self.ledger, minimum_confidence=0.80)

    def active_promise(self):
        candidate = self.ledger.create_candidate(
            actor_id="zoe",
            deliverable="send the revised document",
            raw_text="I promise I'll send you the revised document tomorrow by 3 PM.",
            confidence=0.95,
            source="gmail",
            source_id="promise-message",
            due_at=NOW + timedelta(hours=18),
        )
        return self.ledger.confirm(
            actor_id="zoe",
            commitment_id=candidate.commitment_id,
        )

    def message(self, **overrides):
        values = {
            "source": "gmail",
            "source_id": "fulfillment-message",
            "direction": "sent",
            "body": "Here's the revised document. Let me know if you need anything else.",
            "subject": "Re: revised document",
            "participants": ["jordan@example.com"],
            "occurred_at": NOW + timedelta(hours=1),
        }
        values.update(overrides)
        return SourceMessage(**values)

    def proposal(self, commitment_id: str, **overrides):
        values = {
            "commitment_id": commitment_id,
            "evidence_kind": "handoff_message",
            "summary": "The user appears to hand off the revised document.",
            "supporting_text": "Here's the revised document.",
            "confidence": 0.94,
            "reason": "The later outgoing message directly presents the promised deliverable.",
        }
        values.update(overrides)
        return EvidenceProposal(**values)

    def test_clear_later_handoff_marks_active_promise_likely_done(self):
        active = self.active_promise()

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            proposal=self.proposal(active.commitment_id),
        )

        self.assertIsNotNone(updated)
        self.assertEqual(PromiseState.LIKELY_DONE, updated.status)
        self.assertIsNone(updated.completed_at)
        self.assertEqual(1, len(updated.evidence))
        self.assertEqual("gmail", updated.evidence[0].source)
        self.assertEqual("fulfillment-message", updated.evidence[0].source_id)
        self.assertEqual("Here's the revised document.", updated.evidence[0].supporting_text)

    def test_original_promise_message_cannot_be_its_own_evidence(self):
        active = self.active_promise()
        original = self.message(
            source_id="promise-message",
            body="I promise I'll send you the revised document tomorrow by 3 PM.",
        )

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=original,
            proposal=self.proposal(
                active.commitment_id,
                supporting_text="I promise I'll send you the revised document tomorrow by 3 PM.",
            ),
        )

        self.assertIsNone(updated)
        self.assertEqual(PromiseState.ACTIVE, self.ledger.get(actor_id="zoe", commitment_id=active.commitment_id).status)

    def test_candidate_is_not_reconciled_before_user_confirmation(self):
        candidate = self.ledger.create_candidate(
            actor_id="zoe",
            deliverable="send the revised document",
            raw_text="I'll send the revised document.",
            confidence=0.95,
            source="gmail",
            source_id="promise-message",
        )

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            proposal=self.proposal(candidate.commitment_id),
        )

        self.assertIsNone(updated)
        self.assertEqual(PromiseState.CANDIDATE, candidate.status)

    def test_weak_evidence_is_ignored(self):
        active = self.active_promise()

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            proposal=self.proposal(active.commitment_id, confidence=0.55),
        )

        self.assertIsNone(updated)

    def test_supporting_text_must_be_exact_source_excerpt(self):
        active = self.active_promise()

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            proposal=self.proposal(
                active.commitment_id,
                supporting_text="I sent the revised document.",
            ),
        )

        self.assertIsNone(updated)

    def test_clearly_older_message_is_not_fulfillment_evidence(self):
        active = self.active_promise()

        updated = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(occurred_at=NOW - timedelta(hours=1)),
            proposal=self.proposal(active.commitment_id),
        )

        self.assertIsNone(updated)


if __name__ == "__main__":
    unittest.main()
