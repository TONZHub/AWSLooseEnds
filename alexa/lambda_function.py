"""Thin Alexa Custom Skill adapter for the Promise Pocket AgentCore runtime."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN", "")
ALEXA_SKILL_ID = os.environ.get("ALEXA_SKILL_ID", "")
DEFAULT_TIMEZONE = os.environ.get("LOOSE_ENDS_TIMEZONE", "America/New_York")
LWA_CLIENT_ID = os.environ.get("LWA_CLIENT_ID", "")

_agentcore = None


def _agentcore_client():
    global _agentcore
    if _agentcore is None:
        _agentcore = boto3.client("bedrock-agentcore")
    return _agentcore


def _speech(
    text: str,
    *,
    end_session: bool = True,
    reprompt: str | None = None,
    session_attributes: dict[str, Any] | None = None,
):
    response: dict[str, Any] = {
        "outputSpeech": {"type": "PlainText", "text": text},
        "shouldEndSession": end_session,
    }
    if reprompt:
        response["reprompt"] = {
            "outputSpeech": {"type": "PlainText", "text": reprompt}
        }
    payload = {"version": "1.0", "response": response}
    if session_attributes:
        payload["sessionAttributes"] = session_attributes
    return payload


def _first_turn(event: dict[str, Any], text: str) -> str:
    """Identify the skill when Alexa routes directly into a new session."""
    if event.get("session", {}).get("new") is True:
        return f"Promise Pocket here. {text}"
    return text


def _verify_skill(event: dict[str, Any]) -> None:
    application_id = (
        event.get("context", {})
        .get("System", {})
        .get("application", {})
        .get("applicationId")
    ) or event.get("session", {}).get("application", {}).get("applicationId")
    if not ALEXA_SKILL_ID or application_id != ALEXA_SKILL_ID:
        raise ValueError("request application ID does not match this skill")


def _hashed_actor_id(prefix: str, source: str) -> str:
    return f"{prefix}-" + hashlib.sha256(source.encode()).hexdigest()


def _alexa_access_token(event: dict[str, Any]) -> str | None:
    token = (
        event.get("context", {})
        .get("System", {})
        .get("user", {})
        .get("accessToken")
    ) or event.get("session", {}).get("user", {}).get("accessToken")
    return token if isinstance(token, str) and token else None


def _read_lwa_json(request: Request) -> dict[str, Any]:
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Login with Amazon returned an invalid response")
    return payload


def _linked_amazon_actor_id(access_token: str) -> str:
    if not LWA_CLIENT_ID:
        raise RuntimeError("LWA_CLIENT_ID is not configured")

    token_info_url = "https://api.amazon.com/auth/o2/tokeninfo?" + urlencode(
        {"access_token": access_token}
    )
    token_info = _read_lwa_json(
        Request(token_info_url, headers={"Accept": "application/json"})
    )
    if token_info.get("aud") != LWA_CLIENT_ID:
        raise ValueError("Login with Amazon token audience does not match")

    profile = _read_lwa_json(
        Request(
            "https://api.amazon.com/user/profile",
            headers={
                "Accept": "application/json",
                "Accept-Language": "en-US",
                "Authorization": f"Bearer {access_token}",
            },
        )
    )
    user_id = profile.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("Login with Amazon profile is missing user_id")
    return _hashed_actor_id("amazon", user_id)


def _actor_id(event: dict[str, Any]) -> str:
    access_token = _alexa_access_token(event)
    if access_token:
        # Account linking and the Android app use the same LWA security profile,
        # so both surfaces resolve to one pseudonymous ledger identity.
        return _linked_amazon_actor_id(access_token)

    alexa_user_id = (
        event.get("context", {}).get("System", {}).get("user", {}).get("userId")
        or event.get("session", {}).get("user", {}).get("userId")
    )
    if not isinstance(alexa_user_id, str) or not alexa_user_id:
        raise ValueError("Alexa user ID is missing")
    # Keep Amazon's opaque identifier out of the commitment ledger and logs.
    return _hashed_actor_id("alexa", alexa_user_id)


def _session_id(event: dict[str, Any]) -> str:
    source = event.get("session", {}).get("sessionId") or event["request"]["requestId"]
    # AgentCore session IDs must be at least 33 characters and are safest as a
    # stable, character-limited digest.
    return "alexa-session-" + hashlib.sha256(source.encode()).hexdigest()


def _read_runtime_response(response: dict[str, Any]) -> dict[str, Any]:
    body = response["response"]
    raw = body.read() if hasattr(body, "read") else b"".join(body)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _invoke(event: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not AGENT_RUNTIME_ARN:
        raise RuntimeError("AGENT_RUNTIME_ARN is not configured")
    actor_id = _actor_id(event)
    trusted_payload = {**payload, "actor_id": actor_id}
    response = _agentcore_client().invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=_session_id(event),
        runtimeUserId=actor_id,
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(trusted_payload).encode("utf-8"),
    )
    if response.get("statusCode") != 200:
        raise RuntimeError(f"AgentCore returned {response.get('statusCode')}")
    return _read_runtime_response(response)


def _slot_value(intent: dict[str, Any], name: str) -> str | None:
    value = intent.get("slots", {}).get(name, {}).get("value")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _capture(event: dict[str, Any], intent: dict[str, Any]):
    commitment = _slot_value(intent, "commitment")
    if not commitment:
        return _speech(
            _first_turn(event, "What should I hold onto?"),
            end_session=False,
            reprompt="Tell me the promise or task you want me to remember.",
        )
    result = _invoke(
        event,
        {"operation": "capture", "prompt": commitment, "timezone": DEFAULT_TIMEZONE},
    )
    if result.get("captured_commitment_ids"):
        captured = result.get("captured_commitments") or []
        if captured and captured[0].get("missing_information"):
            question = captured[0]["missing_information"][0]
            return _speech(
                _first_turn(event, question),
                end_session=False,
                reprompt=question,
                session_attributes={
                    "pendingCommitmentId": captured[0]["commitment_id"]
                },
            )
        return _speech(
            _first_turn(event, "Got it. I tucked that loose end away.")
        )
    return _speech(
        _first_turn(
            event,
            "I didn't hear a definite commitment there. What should I keep track of?",
        ),
        end_session=False,
        reprompt="Tell me what you need to do and when.",
    )


def _review(event: dict[str, Any]):
    result = _invoke(event, {"operation": "review"})
    items = result.get("items", [])
    if not items:
        return _speech(_first_turn(event, "Nothing needs you right now."))
    prompts = [item.get("prompt") or item.get("summary") for item in items[:3]]
    prompts = [prompt for prompt in prompts if isinstance(prompt, str)]
    if len(items) > 3:
        prompts.append(f"And {len(items) - 3} more.")
    return _speech(_first_turn(event, " ".join(prompts)))


def _clarify(event: dict[str, Any], intent: dict[str, Any]):
    commitment_id = event.get("session", {}).get("attributes", {}).get(
        "pendingCommitmentId"
    )
    answer = _slot_value(intent, "answer")
    if not commitment_id or not answer:
        return _speech("What time should I use?", end_session=False)
    result = _invoke(
        event,
        {
            "operation": "clarify",
            "commitment_id": commitment_id,
            "answer": answer,
            "timezone": DEFAULT_TIMEZONE,
        },
    )
    if result.get("updated_commitment_ids"):
        return _speech("Perfect. I added the time to that loose end.")
    return _speech("I still need a specific time.", end_session=False)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    try:
        _verify_skill(event)
        request = event.get("request", {})
        request_type = request.get("type")
        if request_type == "LaunchRequest":
            return _speech(
                "Promise Pocket is listening. What should I hold onto?",
                end_session=False,
                reprompt="Tell me a promise or task to remember.",
            )
        if request_type == "SessionEndedRequest":
            return {"version": "1.0", "response": {}}
        if request_type != "IntentRequest":
            return _speech("I couldn't understand that request.")

        intent = request.get("intent", {})
        name = intent.get("name")
        if name == "CaptureCommitmentIntent":
            return _capture(event, intent)
        if name == "ReviewPromisePocketIntent":
            return _review(event)
        if name == "ClarifyCommitmentIntent":
            return _clarify(event, intent)
        if name == "AMAZON.HelpIntent":
            return _speech(
                _first_turn(
                    event, "Say, remember that I need to call Mom tomorrow."
                ),
                end_session=False,
                reprompt="What should I remember?",
            )
        if name in {"AMAZON.CancelIntent", "AMAZON.StopIntent"}:
            return _speech("Okay. Your promises will wait here.")
        return _speech(
            _first_turn(
                event, "Try saying, remember that I need to call Mom tomorrow."
            )
        )
    except Exception:
        LOGGER.exception("Alexa request failed")
        return _speech("Promise Pocket hit a snag. Please try again in a moment.")
