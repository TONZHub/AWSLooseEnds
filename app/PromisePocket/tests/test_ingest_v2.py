from datetime import datetime, timedelta, timezone
import unittest

from pydantic import ValidationError

from promise_pocket.ingest_v2 import CandidateIngestor, PromiseExtraction, SourceMessage
from promise_pocket.ledger_v2 import InMemoryPromiseLedgerStore, PromiseLedger, PromiseState


NOW = datetime(2026, 8, 30, 18, 0, tzinfo=timezone.utc)


class CandidateIngestorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryPromiseLedgerStore()
        self.ledger = PromiseLedger(self.store, clock=lambda: NOW)
        self.ingestor = CandidateIngestor(self.ledger, minimum_confidence=0.70)

    def message(self, **overrides):
        values = {
            "source": "gmail",
            "source_id": "gmail-msg-1",
            "direction": "sent",
            "body": "Hey Jordan, absolutely — I'll get the final mockups over to you by Tuesday evening. Thanks!",
            "subject": "Re: final mockups",
            "participants": ["Jordan"],
            "occurred_at": NOW,
        }
        values.update(overrides)
        return SourceMessage(**values)

    def extraction(self, **overrides):
        values = {
            "is_commitment": True,
            "deliverable": "send the final mockups",
            "people": ["Jordan"],
            "due_at": NOW + timedelta(days=2),
            "confidence": 0.94,
            "supporting_text": "I'll get the final mockups over to you by Tuesday evening.",
            "evidence_hint": "Look for a later outgoing message or attachment containing the final mockups.",
            "reason": "The sender explicitly promises a deliverable with a deadline.",
        }
        values.update(overrides)
        return PromiseExtraction(**values)

    def test_high_confidence_sent_commitment_creates_candidate(self):
        record = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            extraction=self.extraction(),
        )

        self.assertIsNotNone(record)
        self.assertEqual(PromiseState.CANDIDATE, record.status)
        self.assertEqual("gmail", record.source)
        self.assertEqual("gmail-msg-1", record.source_id)
        self.assertEqual(
            "I'll get the final mockups over to you by Tuesday evening.",
            record.raw_text,
        )

    def test_received_message_does_not_create_users_commitment(self):
        record = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(direction="received"),
            extraction=self.extraction(),
        )

        self.assertIsNone(record)
        self.assertEqual([], self.ledger.list_for_actor(actor_id="zoe"))

    def test_non_commitment_is_ignored(self):
        record = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            extraction=self.extraction(
                is_commitment=False,
                deliverable=None,
                supporting_text=None,
                confidence=0.99,
                reason="The sender is brainstorming, not promising an action.",
            ),
        )

        self.assertIsNone(record)

    def test_low_confidence_commitment_is_ignored(self):
        record = self.ingestor.apply(
            actor_id="zoe",
            message=self.message(),
            extraction=self.extraction(confidence=0.45),
        )

        self.assertIsNone(record)

    def test_model_must_provide_exact_supporting_text(self):
        with self.assertRaises(ValidationError):
            self.extraction(supporting_text=None)

    def test_ingestion_stores_snippet_not_entire_email(self):
        message = self.message(
            body="Private preamble. I'll send the final mockups Tuesday. Private footer."
        )
        extraction = self.extraction(
            supporting_text="I'll send the final mockups Tuesday."
        )

        record = self.ingestor.apply(
            actor_id="zoe",
            message=message,
            extraction=extraction,
        )

        self.assertEqual("I'll send the final mockups Tuesday.", record.raw_text)
        self.assertNotIn("Private preamble", record.raw_text)


if __name__ == "__main__":
    unittest.main()
