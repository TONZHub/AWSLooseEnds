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

    def _invoke_source_operation(
        self,
        *,
        operation: str,
        actor_id: str,
        source_message: dict[str, Any],
    ) -> dict[str, Any]:
        source_id = str(source_message.get("source_id") or "unknown")
        digest = hashlib.sha256(
            f"{operation}:{actor_id}:{source_id}".encode("utf-8")
        ).hexdigest()
        session_id = f"watcher-{operation}-{digest}"
        payload = {
            "operation": operation,
            "actor_id": actor_id,
            "source_message": source_message,
            "timezone": self._settings.timezone_name,
        }
        response = self._client.invoke_agent_runtime(
            agentRuntimeArn=self._settings.agent_runtime_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
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
