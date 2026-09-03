from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from google_client import _message_to_source
from agentcore_client import PocketPromiseAgentCoreClient
from alexa_proactive import AlexaProactiveClient
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

    def test_reconnect_resets_scan_cursor(self):
        self.store.save_google_connection(
            actor_id="amazon-demo",
            email="first@example.com",
            refresh_token="first-refresh-token",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        self.store.update_last_checked(actor_id="amazon-demo", checked_at=NOW)
        self.assertEqual(NOW, self.store.list_google_connections()[0].last_checked_at)

        self.store.save_google_connection(
            actor_id="amazon-demo",
            email="second@example.com",
            refresh_token="second-refresh-token",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        reconnected = self.store.list_google_connections()[0]
        self.assertEqual("second@example.com", reconnected.email)
        self.assertEqual("second-refresh-token", reconnected.refresh_token)
        self.assertIsNone(reconnected.last_checked_at)

    def test_proactive_nudges_are_delivered_only_once(self):
        nudges = [
            {"commitment_id": "promise-1", "message": "Still unresolved"},
            {"commitment_id": "promise-2", "message": "Still unresolved"},
        ]
        self.assertEqual(
            nudges, self.store.pending_nudges(actor_id="zoe", nudges=nudges)
        )
        self.store.mark_nudges_sent(
            actor_id="zoe",
            commitment_ids=["promise-1"],
            reference_id="receipts~one",
        )
        self.assertEqual(
            [nudges[1]], self.store.pending_nudges(actor_id="zoe", nudges=nudges)
        )

    def test_mobile_session_token_is_hashed_and_resolves_actor(self):
        token = self.store.issue_mobile_session(
            installation_id="installation-1234567890",
            actor_id="mobile-demo",
        )

        self.assertEqual("mobile-demo", self.store.mobile_actor_for_token(token))
        self.assertIsNone(self.store.mobile_actor_for_token("wrong-token"))
        self.assertNotIn(token.encode(), self.path.read_bytes())

    def test_mobile_session_revocation_invalidates_token(self):
        token = self.store.issue_mobile_session(
            installation_id="installation-1234567890",
            actor_id="mobile-demo",
        )
        self.assertEqual("mobile-demo", self.store.mobile_actor_for_token(token))
        self.assertTrue(self.store.revoke_mobile_session(token))
        self.assertIsNone(self.store.mobile_actor_for_token(token))
        self.assertFalse(self.store.revoke_mobile_session(token))

    def test_mobile_session_count(self):
        self.assertEqual(0, self.store.mobile_session_count())
        self.store.issue_mobile_session(
            installation_id="install-1",
            actor_id="mobile-1",
        )
        self.assertEqual(1, self.store.mobile_session_count())
        self.store.issue_mobile_session(
            installation_id="install-2",
            actor_id="mobile-2",
        )
        self.assertEqual(2, self.store.mobile_session_count())

    def test_oauth_state_is_one_time_and_preserves_pkce_verifier(self):
        self.store.save_oauth_state(
            state="good-state",
            actor_id="amazon-demo",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            code_verifier="verifier-1234567890",
        )

        context = self.store.consume_oauth_state("good-state")
        self.assertIsNotNone(context)
        self.assertEqual("amazon-demo", context.actor_id)
        self.assertEqual("verifier-1234567890", context.code_verifier)
        self.assertIsNone(self.store.consume_oauth_state("good-state"))

        self.store.save_oauth_state(
            state="expired-state",
            actor_id="amazon-demo",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            code_verifier="expired-verifier",
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


class AgentCoreClientTests(unittest.TestCase):
    @patch("agentcore_client.boto3.client")
    def test_overdue_operation_only_prepares_nudges(self, build_client):
        runtime = build_client.return_value
        runtime.invoke_agent_runtime.return_value = {
            "statusCode": 200,
            "response": io.BytesIO(
                json.dumps(
                    {
                        "operation": "v2_overdue",
                        "overdue_ids": ["promise-1"],
                        "nudges": [{"commitment_id": "promise-1"}],
                    }
                ).encode("utf-8")
            ),
        }
        settings = SimpleNamespace(
            aws_region="us-east-1",
            agent_runtime_arn="arn:example",
        )
        client = PocketPromiseAgentCoreClient(settings)

        result = client.prepare_overdue_nudges(actor_id="zoe")

        self.assertEqual(["promise-1"], result["overdue_ids"])
        request = runtime.invoke_agent_runtime.call_args.kwargs
        self.assertEqual(
            {"operation": "v2_overdue", "actor_id": "zoe"},
            json.loads(request["payload"]),
        )
        self.assertNotIn("notification", request)

    @patch("agentcore_client.boto3.client")
    def test_mobile_pair_claim_binds_runtime_identity(self, build_client):
        runtime = build_client.return_value
        runtime.invoke_agent_runtime.return_value = {
            "statusCode": 200,
            "response": io.BytesIO(
                json.dumps({"operation": "pair_claim", "linked": True}).encode()
            ),
        }
        client = PocketPromiseAgentCoreClient(
            SimpleNamespace(aws_region="us-east-1", agent_runtime_arn="arn:example")
        )

        result = client.claim_pairing(actor_id="mobile-demo", code="123456")

        self.assertTrue(result["linked"])
        request = runtime.invoke_agent_runtime.call_args.kwargs
        self.assertEqual("mobile-demo", request["runtimeUserId"])
        self.assertEqual(
            {"operation": "pair_claim", "actor_id": "mobile-demo", "code": "123456"},
            json.loads(request["payload"]),
        )


class AlexaProactiveClientTests(unittest.TestCase):
    @patch("alexa_proactive._post")
    def test_overdue_alert_uses_message_schema_and_multicast(self, post):
        token_response = SimpleNamespace(
            status=200,
            read=lambda: json.dumps({"access_token": "token"}).encode(),
        )
        accepted_response = SimpleNamespace(status=202)
        post.side_effect = [token_response, accepted_response]
        client = AlexaProactiveClient(
            client_id="client",
            client_secret="secret",
            endpoint="https://example.test/development",
        )

        reference = client.send_overdue_alert(
            actor_id="zoe", commitment_ids=["promise-1", "promise-2"]
        )

        self.assertTrue(reference.startswith("receipts~"))
        event_call = post.call_args_list[1]
        payload = json.loads(event_call.kwargs["body"])
        self.assertEqual("AMAZON.MessageAlert.Activated", payload["event"]["name"])
        self.assertEqual(2, payload["event"]["payload"]["messageGroup"]["count"])
        self.assertEqual(
            {"type": "Multicast", "payload": {}}, payload["relevantAudience"]
        )


class WatcherAppAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        from cryptography.fernet import Fernet
        os.environ.setdefault(
            "AGENT_RUNTIME_ARN",
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/LooseEnds",
        )
        os.environ.setdefault("DEMO_ACTOR_ID", "demo-actor")
        os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
        os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
        os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost/auth/google/callback")
        os.environ.setdefault("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
        os.environ.setdefault("DATABASE_PATH", str(Path(TemporaryDirectory().name) / "test.sqlite3"))

        from fastapi.testclient import TestClient
        import app as watcher_app
        cls.app = watcher_app.app
        cls.client = TestClient(cls.app, raise_server_exceptions=False)
        cls.watcher_app = watcher_app

    def setUp(self):
        self.app = self.__class__.app
        self.client = self.__class__.client
        self.watcher_app = self.__class__.watcher_app

    def test_public_endpoints_do_not_require_authentication(self):
        with patch.object(
            self.watcher_app.agentcore,
            "create_alexa_pairing",
            return_value={"code": "123456", "expires_at": "2026-09-03T13:00:00Z"},
        ):
            alexa_resp = self.client.get("/alexa/pair")
            self.assertEqual(200, alexa_resp.status_code)
            self.assertIn("123456", alexa_resp.text)

            mobile_resp = self.client.get("/mobile/pair")
            self.assertEqual(200, mobile_resp.status_code)
            self.assertIn("123456", mobile_resp.text)
            self.assertIn("Return to the ledger", mobile_resp.text)

        status_resp = self.client.get("/status")
        self.assertEqual(200, status_resp.status_code)
        self.assertIn("poll_interval_seconds", status_resp.json())

    def test_admin_desk_requires_authentication(self):
        fake_settings = SimpleNamespace(
            admin_key="secret-test-key",
            poll_interval_seconds=600,
            database_path="/tmp/test.sqlite3",
        )
        with patch.object(self.watcher_app, "settings", fake_settings):
            # Without credentials
            unauth_resp = self.client.get("/admin")
            self.assertEqual(401, unauth_resp.status_code)

            # With wrong credentials
            wrong_resp = self.client.get("/admin", auth=("admin", "wrong-password"))
            self.assertEqual(401, wrong_resp.status_code)

            # With correct credentials
            auth_resp = self.client.get("/admin", auth=("admin", "secret-test-key"))
            self.assertEqual(200, auth_resp.status_code)
            self.assertIn("WATCHER DESK (ADMIN)", auth_resp.text)

    def test_wordmark_has_invisible_admin_link(self):
        resp = self.client.get("/")
        self.assertEqual(200, resp.status_code)
        self.assertIn('<a href="/admin" class="cut admin-link"', resp.text)
        self.assertIn("actions-2x2", resp.text)

    def test_connect_google_endpoints(self):
        resp = self.client.get("/connect/google")
        self.assertEqual(200, resp.status_code)
        self.assertIn("Connect Gmail", resp.text)
        self.assertIn("verified app", resp.text)
        self.assertNotIn("access-key", resp.text)

        with patch.object(self.watcher_app, "begin_google_authorization") as begin_auth:
            from fastapi.responses import RedirectResponse
            begin_auth.return_value = RedirectResponse("https://accounts.google.com/test", status_code=303)

            # Test POST /connect/google
            post_resp = self.client.post("/connect/google", data={}, follow_redirects=False)
            self.assertIn(post_resp.status_code, (302, 303, 307))

            # Test GET /auth/google/start
            start_resp = self.client.get("/auth/google/start", follow_redirects=False)
            self.assertIn(start_resp.status_code, (302, 303, 307))


if __name__ == "__main__":
    unittest.main()
