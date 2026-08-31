from __future__ import annotations

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

fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = Mock()
sys.modules.setdefault("boto3", fake_boto3)

from alexa import lambda_function


def pairing_event(code: str | None) -> dict:
    slots = {}
    if code is not None:
        slots["code"] = {"name": "code", "value": code}
    return {
        "version": "1.0",
        "session": {
            "new": True,
            "sessionId": "session-pairing-123",
            "application": {"applicationId": "amzn1.ask.skill.test-skill"},
            "user": {"userId": "amzn1.ask.account.private-user"},
        },
        "context": {
            "System": {
                "application": {"applicationId": "amzn1.ask.skill.test-skill"},
                "user": {"userId": "amzn1.ask.account.private-user"},
            }
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "request-pairing-123",
            "intent": {"name": "LinkAlexaIntent", "slots": slots},
        },
    }


class AlexaPairingTests(unittest.TestCase):
    def test_pairing_intent_claims_six_digit_code(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"operation": "pair_claim", "linked": True},
        ) as invoke:
            response = lambda_function.lambda_handler(pairing_event("482731"), None)

        self.assertEqual("pair_claim", invoke.call_args.args[1]["operation"])
        self.assertEqual("482731", invoke.call_args.args[1]["code"])
        self.assertIn("Connected", response["response"]["outputSpeech"]["text"])

    def test_pairing_intent_rejects_non_six_digit_code_without_runtime_call(self):
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(pairing_event("123"), None)

        invoke.assert_not_called()
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertIn("six digits", response["response"]["outputSpeech"]["text"])

    def test_pairing_intent_reports_expired_code(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"operation": "pair_claim", "linked": False},
        ):
            response = lambda_function.lambda_handler(pairing_event("482731"), None)

        self.assertIn("invalid or expired", response["response"]["outputSpeech"]["text"])


if __name__ == "__main__":
    unittest.main()
