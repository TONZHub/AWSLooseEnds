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

    def arbitrate_message(
        self,
        *,
        actor_id: str,
        source_message: dict[str, Any],
    ) -> dict[str, Any]:
        source_id = str(source_message.get("source_id") or "unknown")
        session_id = "watcher-session-" + hashlib.sha256(
            f"{actor_id}:{source_id}".encode("utf-8")
        ).hexdigest()
        payload = {
            "operation": "v2_arbitrate",
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
