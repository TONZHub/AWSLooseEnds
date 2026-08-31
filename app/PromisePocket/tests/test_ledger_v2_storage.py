from datetime import datetime, timezone
from decimal import Decimal
import unittest

from promise_pocket.ledger_v2 import PromiseEvidence, PromiseRecord
from promise_pocket.ledger_v2_storage import DynamoDbPromiseLedgerStore


class LedgerV2StorageTests(unittest.TestCase):
    def test_confidence_floats_are_converted_for_dynamodb(self):
        record = PromiseRecord(
            actor_id="actor",
            deliverable="send the mockup",
            raw_text="I promise I'll send the mockup tomorrow.",
            confidence=0.95,
            source="gmail",
            source_id="message-1",
            due_at=datetime(2026, 8, 31, 21, 0, tzinfo=timezone.utc),
            evidence=[
                PromiseEvidence(
                    kind="email",
                    source="gmail",
                    source_id="message-2",
                    summary="Possible completion evidence",
                    confidence=0.8,
                )
            ],
        )

        item = DynamoDbPromiseLedgerStore._to_item(record)

        self.assertEqual(Decimal("0.95"), item["confidence"])
        self.assertEqual(Decimal("0.8"), item["evidence"][0]["confidence"])

    def test_dynamodb_decimal_confidence_round_trips_through_model(self):
        record = PromiseRecord(
            actor_id="actor",
            deliverable="send the mockup",
            raw_text="I promise I'll send the mockup tomorrow.",
            confidence=0.95,
            source="gmail",
            source_id="message-1",
        )
        item = DynamoDbPromiseLedgerStore._to_item(record)

        restored = DynamoDbPromiseLedgerStore._from_item(item)

        self.assertIsNotNone(restored)
        self.assertAlmostEqual(0.95, restored.confidence)


if __name__ == "__main__":
    unittest.main()
