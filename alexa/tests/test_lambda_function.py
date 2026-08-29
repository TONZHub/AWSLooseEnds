from __future__ import annotations

from io import BytesIO
import json
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("ALEXA_SKILL_ID", "amzn1.ask.skill.test-skill")
os.environ.setdefault(
    "AGENT_RUNTIME_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/LooseEnds",
)

# Lambda includes boto3. Keep these unit tests dependency-free by supplying the
# tiny import surface before loading the adapter.
fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = Mock()
sys.modules.setdefault("boto3", fake_boto3)

from alexa import lambda_function


def event(intent_name=None, commitment=None):
    request = {"type": "LaunchRequest", "requestId": "request-123"}
    if intent_name:
        slots = {}
        if commitment is not None:
            slots["commitment"] = {"name": "commitment", "value": commitment}
        request = {
            "type": "IntentRequest",
            "requestId": "request-123",
            "intent": {"name": intent_name, "slots": slots},
        }
    return {
        "version": "1.0",
        "session": {
            "sessionId": "session-123",
            "application": {"applicationId": "amzn1.ask.skill.test-skill"},
            "user": {"userId": "amzn1.ask.account.private-user"},
        },
        "context": {
            "System": {
                "application": {"applicationId": "amzn1.ask.skill.test-skill"},
                "user": {"userId": "amzn1.ask.account.private-user"},
            }
        },
        "request": request,
    }


class AlexaAdapterTests(unittest.TestCase):
    def test_launch_invites_capture(self):
        response = lambda_function.lambda_handler(event(), None)
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertIn("Promise Pocket is listening", response["response"]["outputSpeech"]["text"])

    def test_wrong_skill_is_rejected_without_invoking_runtime(self):
        request = event("CaptureCommitmentIntent", "call Mom")
        request["context"]["System"]["application"]["applicationId"] = "wrong"
        request["session"]["application"]["applicationId"] = "wrong"
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(request, None)
        invoke.assert_not_called()
        self.assertIn("snag", response["response"]["outputSpeech"]["text"])

    def test_capture_forwards_text_and_confirms(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"captured_commitment_ids": ["commitment-1"]},
        ) as invoke:
            response = lambda_function.lambda_handler(
                event("CaptureCommitmentIntent", "call Mom tomorrow"), None
            )
        self.assertEqual("capture", invoke.call_args.args[1]["operation"])
        self.assertEqual("call Mom tomorrow", invoke.call_args.args[1]["prompt"])
        self.assertIn("tucked", response["response"]["outputSpeech"]["text"])

    def test_capture_with_missing_time_keeps_session_open(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={
                "captured_commitment_ids": ["commitment-1"],
                "captured_commitments": [
                    {
                        "commitment_id": "commitment-1",
                        "missing_information": ["What time should I bring this back?"],
                    }
                ],
            },
        ):
            response = lambda_function.lambda_handler(
                event("CaptureCommitmentIntent", "call the vet tomorrow"), None
            )
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertEqual(
            "commitment-1", response["sessionAttributes"]["pendingCommitmentId"]
        )

    def test_clarification_updates_pending_commitment(self):
        request = event("ClarifyCommitmentIntent")
        request["session"]["attributes"] = {
            "pendingCommitmentId": "commitment-1"
        }
        request["request"]["intent"]["slots"] = {
            "answer": {"name": "answer", "value": "at 10 A.M."}
        }
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"updated_commitment_ids": ["commitment-1"]},
        ) as invoke:
            response = lambda_function.lambda_handler(request, None)
        self.assertEqual("clarify", invoke.call_args.args[1]["operation"])
        self.assertIn("added the time", response["response"]["outputSpeech"]["text"])

    def test_review_stays_quiet_when_nothing_needs_attention(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"attention_required": False, "items": []},
        ):
            response = lambda_function.lambda_handler(
                event("ReviewPromisePocketIntent"), None
            )
        self.assertEqual(
            "Nothing needs you right now.",
            response["response"]["outputSpeech"]["text"],
        )

    def test_runtime_invocation_binds_hashed_user_identity(self):
        body = BytesIO(json.dumps({"captured_commitment_ids": ["one"]}).encode())
        client = Mock()
        client.invoke_agent_runtime.return_value = {
            "statusCode": 200,
            "response": body,
        }
        with patch.object(lambda_function, "_agentcore_client", return_value=client):
            result = lambda_function._invoke(event(), {"operation": "review"})
        call = client.invoke_agent_runtime.call_args.kwargs
        self.assertTrue(call["runtimeUserId"].startswith("alexa-"))
        payload = json.loads(call["payload"])
        self.assertEqual(call["runtimeUserId"], payload["actor_id"])
        self.assertGreaterEqual(len(call["runtimeSessionId"]), 33)
        self.assertEqual(["one"], result["captured_commitment_ids"])


if __name__ == "__main__":
    unittest.main()
