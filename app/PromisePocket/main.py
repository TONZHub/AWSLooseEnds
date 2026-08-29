"""Amazon Bedrock AgentCore Runtime entrypoint for Promise Pocket."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from promise_pocket.agent import build_agent, build_clarification_agent
from promise_pocket.service import CommitmentService
from promise_pocket.settings import Settings
from promise_pocket.storage import build_store


app = BedrockAgentCoreApp()
settings = Settings.from_environment()
service = CommitmentService(build_store(settings))


def _actor_id(payload: dict[str, Any], context: Any | None) -> str:
    """Resolve identity supplied by an IAM-authorized invocation adapter.

    AgentCore's ``runtimeUserId`` binds user-scoped credentials but is not
    currently exposed on the Python RequestContext. The Alexa Lambda therefore
    sends the same pseudonymous ID in this payload as well. Runtime IAM controls
    which adapters may invoke this entrypoint; prompt text never selects it.
    """

    actor_id = payload.get("actor_id")
    if settings.local_dev and not actor_id:
        actor_id = settings.dev_actor
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError(
            "actor_id from an IAM-authorized invocation adapter is required"
        )
    return actor_id.strip()


def _parse_now(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, str):
        raise ValueError("now must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("now must include a UTC offset")
    return parsed


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any | None = None) -> dict[str, Any]:
    """Capture through Strands or review deterministically."""

    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    actor_id = _actor_id(payload, context)
    operation = payload.get("operation", "capture")

    if operation == "review":
        items = service.review(actor_id=actor_id, now=_parse_now(payload.get("now")))
        return {
            "operation": "review",
            "attention_required": bool(items),
            "items": [item.model_dump(mode="json") for item in items],
        }

    if operation == "clarify":
        commitment_id = payload.get("commitment_id")
        answer = payload.get("answer")
        if not isinstance(commitment_id, str) or not commitment_id:
            raise ValueError("commitment_id is required for clarification")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("answer is required for clarification")
        existing = service.get(actor_id=actor_id, commitment_id=commitment_id)
        if existing is None:
            raise ValueError("commitment was not found for this actor")
        timezone_name = payload.get("timezone") or settings.timezone_name
        invocation_time = datetime.now(timezone.utc).isoformat()
        updated_ids: list[str] = []
        agent = build_clarification_agent(
            service,
            settings.model_id,
            actor_id,
            commitment_id,
            on_update=updated_ids.append,
        )
        result = agent(
            f"Invocation time in UTC: {invocation_time}\n"
            f"User timezone: {timezone_name}\n"
            f"Original commitment: {existing.raw_text}\n"
            f"Follow-up answer: {answer.strip()}"
        )
        return {
            "operation": "clarify",
            "result": result.message,
            "updated_commitment_ids": updated_ids,
        }

    if operation != "capture":
        raise ValueError("operation must be capture, clarify, or review")

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required for capture")

    timezone_name = payload.get("timezone") or settings.timezone_name
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise ValueError("timezone must be a non-empty IANA timezone name")

    invocation_time = datetime.now(timezone.utc).isoformat()
    contextual_prompt = (
        f"Invocation time in UTC: {invocation_time}\n"
        f"User timezone: {timezone_name}\n"
        f"User message: {prompt.strip()}"
    )

    # A fresh agent prevents in-process conversation history from crossing
    # actors. AgentCore Memory can provide scoped continuity in a later slice.
    captured_commitment_ids: list[str] = []
    agent = build_agent(
        service=service,
        model_id=settings.model_id,
        on_capture=captured_commitment_ids.append,
    )
    result = agent(
        contextual_prompt,
        actor_id=actor_id,
        timezone_name=timezone_name,
        invocation_time=invocation_time,
        captured_commitment_ids=[],
    )

    return {
        "operation": "capture",
        "result": result.message,
        "captured_commitment_ids": captured_commitment_ids,
        "captured_commitments": [
            service.get(actor_id=actor_id, commitment_id=commitment_id).model_dump(
                mode="json"
            )
            for commitment_id in captured_commitment_ids
        ],
    }


if __name__ == "__main__":
    app.run()
