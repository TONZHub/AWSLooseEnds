from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from loose_ends.models import AttentionReason, Commitment
from loose_ends.service import CommitmentService
from loose_ends.storage import InMemoryCommitmentStore, LocalJsonCommitmentStore


NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


class CommitmentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryCommitmentStore()
        self.service = CommitmentService(self.store, clock=lambda: NOW)

    def capture(self, **overrides):
        values = {
            "actor_id": "zoe",
            "summary": "Call the dentist for Mom",
            "raw_text": "I promised Mom I would call the dentist tomorrow at noon",
            "due_at": NOW + timedelta(days=1),
            "people": ["Mom"],
            "human_action_required": True,
            "missing_information": [],
        }
        values.update(overrides)
        return self.service.capture(**values)

    def test_capture_persists_exact_commitment(self):
        captured = self.capture()

        stored = self.store.list_for_actor("zoe")
        self.assertEqual([captured.commitment_id], [item.commitment_id for item in stored])
        self.assertEqual(["Mom"], stored[0].people)
        self.assertEqual(NOW + timedelta(days=1), stored[0].due_at)

    def test_future_commitment_does_not_interrupt(self):
        self.capture()

        self.assertEqual([], self.service.review(actor_id="zoe", now=NOW))

    def test_due_human_action_interrupts(self):
        captured = self.capture(due_at=NOW - timedelta(minutes=1))

        attention = self.service.review(actor_id="zoe", now=NOW)
        self.assertEqual(1, len(attention))
        self.assertEqual(captured.commitment_id, attention[0].commitment_id)
        self.assertEqual(AttentionReason.DUE, attention[0].reason)

    def test_due_agent_safe_work_stays_quiet(self):
        self.capture(
            summary="Prepare dentist options",
            due_at=NOW - timedelta(minutes=1),
            human_action_required=False,
        )

        self.assertEqual([], self.service.review(actor_id="zoe", now=NOW))

    def test_missing_information_surfaces_one_question(self):
        self.capture(
            due_at=None,
            missing_information=["When should I bring this back?"],
        )

        attention = self.service.review(actor_id="zoe", now=NOW)
        self.assertEqual(AttentionReason.CLARIFICATION, attention[0].reason)
        self.assertEqual("When should I bring this back?", attention[0].prompt)

    def test_model_cannot_invent_clock_time_for_date_only_words(self):
        captured = self.capture(
            raw_text="I need to call the pharmacy tomorrow",
            due_at=NOW + timedelta(hours=15),
        )

        self.assertIsNone(captured.due_at)
        self.assertEqual(
            ["What time should I bring this back?"],
            captured.missing_information,
        )

    def test_actor_records_are_isolated(self):
        self.capture(actor_id="zoe", due_at=NOW - timedelta(minutes=1))
        self.capture(actor_id="someone-else", due_at=NOW - timedelta(minutes=1))

        attention = self.service.review(actor_id="zoe", now=NOW)
        self.assertEqual(1, len(attention))

    def test_naive_deadline_is_rejected(self):
        with self.assertRaises(ValidationError):
            Commitment(
                actor_id="zoe",
                summary="Call the dentist",
                raw_text="Call the dentist tomorrow",
                due_at=datetime(2026, 8, 30, 9, 0),
                human_action_required=True,
            )


class LocalJsonStoreTests(unittest.TestCase):
    def test_records_survive_store_recreation(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "commitments.json"
            first = LocalJsonCommitmentStore(path)
            commitment = Commitment(
                actor_id="zoe",
                summary="Call the dentist for Mom",
                raw_text="I promised Mom I would call the dentist tomorrow",
                due_at=NOW + timedelta(days=1),
                people=["Mom"],
                human_action_required=True,
                created_at=NOW,
                updated_at=NOW,
            )
            first.save(commitment)

            second = LocalJsonCommitmentStore(path)
            restored = second.list_for_actor("zoe")
            self.assertEqual(commitment, restored[0])


if __name__ == "__main__":
    unittest.main()
