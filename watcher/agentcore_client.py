from __future__ import annotations

import hashlib
import json
from typing import Any

import boto3

from settings import WatcherSettings


class PocketPromiseAgentCoreClient:
    def __init__(self, settings: WatcherSettings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "bedrock-agentcore",
            region_name=settings.aws_region,
        )

    def _invoke_operation(
        self,
        *,
        operation: str,
        actor_id: str,
        extra_payload: dict[str, Any] | None = None,
        session_seed: str | None = None,
    ) -> dict[str, Any]:
        seed = session_seed or operation
        digest = hashlib.sha256(
            f"{operation}:{actor_id}:{seed}".encode("utf-8")
        ).hexdigest()
        safe_operation = operation.replace("_", "-")
        payload = {
            "operation": operation,
            "actor_id": actor_id,
            **(extra_payload or {}),
        }
        response = self._client.invoke_agent_runtime(
            agentRuntimeArn=self._settings.agent_runtime_arn,
            qualifier="DEFAULT",
            runtimeSessionId=f"watcher-{safe_operation}-{digest}",
            runtimeUserId=actor_id,
            contentType="application/json",
            accept="application/json",
            payload=json.dumps(payload).encode("utf-8"),
        )
        if response.get("statusCode") != 200:
            raise RuntimeError(
                f"AgentCore returned status {response.get('statusCode')}"
            )
        body = response["response"]
        raw = body.read() if hasattr(body, "read") else b"".join(body)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("AgentCore returned a non-object response")
        return result

    def _invoke_source_operation(
        self,
        *,
        operation: str,
        actor_id: str,
        source_message: dict[str, Any],
    ) -> dict[str, Any]:
        source_id = str(source_message.get("source_id") or "unknown")
        return self._invoke_operation(
            operation=operation,
            actor_id=actor_id,
            extra_payload={
                "source_message": source_message,
                "timezone": self._settings.timezone_name,
            },
            session_seed=source_id,
        )

    def arbitrate_message(
        self,
        *,
        actor_id: str,
        source_message: dict[str, Any],
    ) -> dict[str, Any]:
        return self._invoke_source_operation(
            operation="v2_arbitrate",
            actor_id=actor_id,
            source_message=source_message,
        )

    def reconcile_message(
        self,
        *,
        actor_id: str,
        source_message: dict[str, Any],
    ) -> dict[str, Any]:
        return self._invoke_source_operation(
            operation="v2_reconcile",
            actor_id=actor_id,
            source_message=source_message,
        )

    def prepare_overdue_nudges(self, *, actor_id: str) -> dict[str, Any]:
        return self._invoke_operation(
            operation="v2_overdue",
            actor_id=actor_id,
        )

    def create_alexa_pairing(self, *, actor_id: str) -> dict[str, Any]:
        return self._invoke_operation(
            operation="pair_create",
            actor_id=actor_id,
        )

    def claim_pairing(self, *, actor_id: str, code: str) -> dict[str, Any]:
        return self._invoke_operation(
            operation="pair_claim",
            actor_id=actor_id,
            extra_payload={"code": code},
            session_seed=code,
        )

    def list_commitments(self, *, actor_id: str) -> dict[str, Any]:
        return self._invoke_operation(operation="v2_list", actor_id=actor_id)

    def capture_mobile_message(
        self, *, actor_id: str, source_id: str, text: str
    ) -> dict[str, Any]:
        return self._invoke_source_operation(
            operation="v2_arbitrate",
            actor_id=actor_id,
            source_message={
                "source": "android",
                "source_id": source_id,
                "direction": "outgoing",
                "body": text,
                "participants": [],
            },
        )

    def transition_commitment(
        self, *, actor_id: str, commitment_id: str, action: str
    ) -> dict[str, Any]:
        operations = {
            "done": "v2_done",
            "reopen": "v2_reopen",
            "cancel": "v2_cancel",
            "confirm": "v2_confirm",
        }
        operation = operations.get(action)
        if operation is None:
            raise ValueError(f"unsupported commitment action: {action}")
        return self._invoke_operation(
            operation=operation,
            actor_id=actor_id,
            extra_payload={"commitment_id": commitment_id},
            session_seed=commitment_id,
        )
