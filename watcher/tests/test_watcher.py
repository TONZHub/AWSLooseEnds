from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cryptography.fernet import Fernet

from google_client import _message_to_source
from store import ConnectionStore


NOW = datetime(2026, 8, 30, 18, 30, tzinfo=timezone.utc)


class ConnectionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name) / "watcher.sqlite3"
        self.key = Fernet.generate_key().decode("utf-8")
        self.store = ConnectionStore(str(self.path), self.key)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_refresh_token_round_trips_but_public_status_does_not_expose_it(self):
        self.store.save_google_connection(
            actor_id="amazon-demo",
            email="demo@example.com",
            refresh_token="super-secret-refresh-token",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        connection = self.store.list_google_connections()[0]
        public = self.store.public_status()[0]

        self.assertEqual("super-secret-refresh-token", connection.refresh_token)
        self.assertNotIn("refresh_token", public)
        self.assertNotIn(b"super-secret-refresh-token", self.path.read_bytes())

    def test_oauth_state_is_one_time_and_expires(self):
        self.store.save_oauth_state(
            state="good-state",
            actor_id="amazon-demo",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

        self.assertEqual("amazon-demo", self.store.consume_oauth_state("good-state"))
        self.assertIsNone(self.store.consume_oauth_state("good-state"))

        self.store.save_oauth_state(
            state="expired-state",
            actor_id="amazon-demo",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        self.assertIsNone(self.store.consume_oauth_state("expired-state"))


class GmailParsingTests(unittest.TestCase):
    def test_sent_message_becomes_source_message(self):
        body = "Hey Jordan, I'll send the final mockups Tuesday."
        encoded = base64.urlsafe_b64encode(body.encode("utf-8")).decode("ascii")
        message = {
            "id": "gmail-123",
            "internalDate": str(int(NOW.timestamp() * 1000)),
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Mockups"},
                    {"name": "To", "value": "Jordan <jordan@example.com>"},
                ],
                "body": {"data": encoded},
            },
        }

        parsed = _message_to_source(message)

        self.assertEqual("gmail", parsed["source"])
        self.assertEqual("gmail-123", parsed["source_id"])
        self.assertEqual("sent", parsed["direction"])
        self.assertEqual(body, parsed["body"])
        self.assertEqual(["jordan@example.com"], parsed["participants"])
        self.assertEqual("Mockups", parsed["subject"])


if __name__ == "__main__":
    unittest.main()
