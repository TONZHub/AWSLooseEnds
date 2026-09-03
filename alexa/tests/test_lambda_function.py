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


def event(intent_name=None, commitment=None, *, new_session=True):
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
    payload = {
        "version": "1.0",
        "session": {
            "new": new_session,
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
    return payload


class AlexaAdapterTests(unittest.TestCase):
    def test_interaction_model_includes_natural_core_phrases(self):
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "interaction-model.json"
        )
        with open(model_path, encoding="utf-8") as model_file:
            language_model = json.load(model_file)["interactionModel"]["languageModel"]
            self.assertEqual("my receipts", language_model["invocationName"])
            intents = {
                intent["name"]: set(intent.get("samples", []))
                for intent in language_model["intents"]
            }

        expected = {
            "CaptureCommitmentIntent": {"track {commitment}", "add {commitment}"},
            "LinkAlexaIntent": {"my code is {code}", "use code {code}"},
            "ReviewPromisePocketIntent": {
                "review my promises",
                "check my commitments",
                "what needs my attention",
                "review my receipts",
            },
            "CompleteReviewedPromiseIntent": {"complete it", "close it"},
            "KeepPromiseOpenIntent": {"leave it open", "keep tracking it"},
        }
        for intent_name, samples in expected.items():
            self.assertTrue(samples.issubset(intents[intent_name]))

    def test_launch_invites_capture(self):
        response = lambda_function.lambda_handler(event(), None)
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertIn("Receipts is listening", response["response"]["outputSpeech"]["text"])

    def test_proactive_subscription_change_is_acknowledged_silently(self):
        request = event()
        request["request"] = {
            "type": "AlexaSkillEvent.ProactiveSubscriptionChanged",
            "requestId": "subscription-123",
            "body": {
                "subscriptions": [
                    {"eventName": "AMAZON.MessageAlert.Activated"}
                ]
            },
        }

        response = lambda_function.lambda_handler(request, None)

        self.assertEqual({"version": "1.0", "response": {}}, response)

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
        self.assertTrue(
            response["response"]["outputSpeech"]["text"].startswith(
                "Receipts here."
            )
        )
        self.assertIn("tucked", response["response"]["outputSpeech"]["text"])

    def test_follow_up_turn_does_not_repeat_brand_prefix(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"captured_commitment_ids": ["commitment-1"]},
        ):
            response = lambda_function.lambda_handler(
                event(
                    "CaptureCommitmentIntent",
                    "call Mom tomorrow",
                    new_session=False,
                ),
                None,
            )
        self.assertEqual(
            "Got it. I tucked that loose end away.",
            response["response"]["outputSpeech"]["text"],
        )

    def test_first_turn_fallback_identifies_promise_pocket(self):
        response = lambda_function.lambda_handler(event("UnknownIntent"), None)
        self.assertTrue(
            response["response"]["outputSpeech"]["text"].startswith(
                "Receipts here."
            )
        )

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
        request = event("ClarifyCommitmentIntent", new_session=False)
        request["session"]["attributes"] = {
            "pendingCommitmentId": "commitment-1"
        }
        request["request"]["intent"]["slots"] = {
            "answer": {"name": "answer", "value": "10:00"}
        }
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"updated_commitment_ids": ["commitment-1"]},
        ) as invoke:
            response = lambda_function.lambda_handler(request, None)
        self.assertEqual("clarify", invoke.call_args.args[1]["operation"])
        self.assertIn("added the time", response["response"]["outputSpeech"]["text"])

    def test_clarification_missing_time_slot_preserves_pending_commitment(self):
        request = event("ClarifyCommitmentIntent", new_session=False)
        request["session"]["attributes"] = {
            "pendingCommitmentId": "commitment-1"
        }
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(request, None)
        invoke.assert_not_called()
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertEqual(
            "commitment-1", response["sessionAttributes"]["pendingCommitmentId"]
        )
        self.assertIn("What time", response["response"]["outputSpeech"]["text"])

    def test_orphaned_clarification_recovers_as_fresh_capture_prompt(self):
        request = event("ClarifyCommitmentIntent")
        request["request"]["intent"]["slots"] = {
            "answer": {"name": "answer", "value": "09:00"}
        }
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(request, None)
        invoke.assert_not_called()
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertEqual(
            "Receipts here. What should I hold onto?",
            response["response"]["outputSpeech"]["text"],
        )
        self.assertIn(
            "promise or task",
            response["response"]["reprompt"]["outputSpeech"]["text"],
        )

    def test_unsuccessful_clarification_preserves_pending_commitment(self):
        request = event("ClarifyCommitmentIntent", new_session=False)
        request["session"]["attributes"] = {
            "pendingCommitmentId": "commitment-1"
        }
        request["request"]["intent"]["slots"] = {
            "answer": {"name": "answer", "value": "09:00"}
        }
        with patch.object(lambda_function, "_invoke", return_value={}):
            response = lambda_function.lambda_handler(request, None)
        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertEqual(
            "commitment-1", response["sessionAttributes"]["pendingCommitmentId"]
        )
        self.assertIn("specific time", response["response"]["outputSpeech"]["text"])

    def test_review_stays_quiet_when_nothing_needs_attention(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={"attention_required": False, "items": []},
        ) as invoke:
            response = lambda_function.lambda_handler(
                event("ReviewPromisePocketIntent"), None
            )
        self.assertEqual("v2_review", invoke.call_args.args[1]["operation"])
        self.assertEqual(
            "Receipts here. Nothing needs you right now.",
            response["response"]["outputSpeech"]["text"],
        )

    def test_review_asks_about_one_v2_item_and_preserves_context(self):
        with patch.object(
            lambda_function,
            "_invoke",
            return_value={
                "attention_required": True,
                "items": [
                    {
                        "commitment_id": "promise-1",
                        "kind": "confirm_likely_done",
                        "prompt": "It looks like you sent the document. Should I mark it done?",
                    },
                    {
                        "commitment_id": "promise-2",
                        "kind": "resolve_overdue",
                        "prompt": "Another promise is overdue. Did you finish it?",
                    },
                ],
            },
        ):
            response = lambda_function.lambda_handler(
                event("ReviewPromisePocketIntent"), None
            )

        self.assertFalse(response["response"]["shouldEndSession"])
        self.assertIn("sent the document", response["response"]["outputSpeech"]["text"])
        self.assertNotIn("Another promise", response["response"]["outputSpeech"]["text"])
        self.assertEqual(
            "promise-1",
            response["sessionAttributes"][lambda_function.PENDING_REVIEW_ID],
        )
        self.assertEqual(
            "confirm_likely_done",
            response["sessionAttributes"][lambda_function.PENDING_REVIEW_KIND],
        )

    def review_answer_event(self, intent_name: str, review_kind: str):
        request = event(intent_name, new_session=False)
        request["session"]["attributes"] = {
            lambda_function.PENDING_REVIEW_ID: "promise-1",
            lambda_function.PENDING_REVIEW_KIND: review_kind,
        }
        return request

    def test_yes_confirms_candidate(self):
        request = self.review_answer_event("AMAZON.YesIntent", "confirm_candidate")
        with patch.object(lambda_function, "_invoke", return_value={}) as invoke:
            response = lambda_function.lambda_handler(request, None)

        self.assertEqual("v2_confirm", invoke.call_args.args[1]["operation"])
        self.assertEqual("promise-1", invoke.call_args.args[1]["commitment_id"])
        self.assertIn("track", response["response"]["outputSpeech"]["text"])

    def test_no_rejects_candidate(self):
        request = self.review_answer_event("AMAZON.NoIntent", "confirm_candidate")
        with patch.object(lambda_function, "_invoke", return_value={}) as invoke:
            lambda_function.lambda_handler(request, None)

        self.assertEqual("v2_cancel", invoke.call_args.args[1]["operation"])

    def test_yes_marks_likely_done_promise_done(self):
        request = self.review_answer_event(
            "CompleteReviewedPromiseIntent",
            "confirm_likely_done",
        )
        with patch.object(lambda_function, "_invoke", return_value={}) as invoke:
            lambda_function.lambda_handler(request, None)

        self.assertEqual("v2_done", invoke.call_args.args[1]["operation"])

    def test_no_reopens_likely_done_promise(self):
        request = self.review_answer_event(
            "KeepPromiseOpenIntent",
            "confirm_likely_done",
        )
        with patch.object(lambda_function, "_invoke", return_value={}) as invoke:
            lambda_function.lambda_handler(request, None)

        self.assertEqual("v2_reopen", invoke.call_args.args[1]["operation"])

    def test_yes_marks_overdue_promise_done(self):
        request = self.review_answer_event("AMAZON.YesIntent", "resolve_overdue")
        with patch.object(lambda_function, "_invoke", return_value={}) as invoke:
            lambda_function.lambda_handler(request, None)

        self.assertEqual("v2_done", invoke.call_args.args[1]["operation"])

    def test_no_keeps_overdue_promise_open_without_mutation(self):
        request = self.review_answer_event("AMAZON.NoIntent", "resolve_overdue")
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(request, None)

        invoke.assert_not_called()
        self.assertIn("keep", response["response"]["outputSpeech"]["text"])

    def test_yes_without_review_context_does_not_mutate_a_promise(self):
        with patch.object(lambda_function, "_invoke") as invoke:
            response = lambda_function.lambda_handler(
                event("AMAZON.YesIntent", new_session=False), None
            )

        invoke.assert_not_called()
        self.assertIn("review", response["response"]["outputSpeech"]["text"])

    def test_interaction_model_includes_review_answers(self):
        model_path = os.path.join(
            os.path.dirname(lambda_function.__file__),
            "interaction-model.json",
        )
        with open(model_path, encoding="utf-8") as model_file:
            model = json.load(model_file)
        intent_names = {
            intent["name"]
            for intent in model["interactionModel"]["languageModel"]["intents"]
        }

        self.assertIn("AMAZON.YesIntent", intent_names)
        self.assertIn("AMAZON.NoIntent", intent_names)
        self.assertIn("CompleteReviewedPromiseIntent", intent_names)
        self.assertIn("KeepPromiseOpenIntent", intent_names)

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

    def test_access_token_does_not_change_pairing_source_identity(self):
        request = event()
        request["session"]["user"]["accessToken"] = "Atza|stale-linked-token"
        request["context"]["System"]["user"]["accessToken"] = (
            "Atza|stale-linked-token"
        )

        self.assertTrue(lambda_function._actor_id(request).startswith("alexa-"))

    def test_eventbridge_scheduled_event_runs_quiet_overdue_review(self):
        scheduled_event = {
            "version": "0",
            "id": "event-123",
            "detail-type": "Scheduled Event",
            "source": "aws.events",
            "time": "2026-09-03T12:00:00Z",
            "region": "us-east-1",
            "resources": ["arn:aws:events:us-east-1:123456789012:rule/ReceiptsQuietReviewSchedule"],
            "detail": {},
        }
        body = BytesIO(
            json.dumps({
                "operation": "v2_overdue",
                "overdue_ids": ["c-1"],
                "nudges": [{"commitment_id": "c-1", "message": "Still unresolved"}],
            }).encode()
        )
        client = Mock()
        client.invoke_agent_runtime.return_value = {
            "statusCode": 200,
            "response": body,
        }
        with patch.object(lambda_function, "_agentcore_client", return_value=client):
            result = lambda_function.lambda_handler(scheduled_event, None)
        self.assertEqual("ok", result["status"])
        self.assertEqual(1, result["overdue_count"])
        self.assertEqual(1, result["nudges_prepared"])


if __name__ == "__main__":
    unittest.main()
