from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from urllib import parse, request


class AlexaProactiveClient:
    def __init__(self, *, client_id: str, client_secret: str, endpoint: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._endpoint = endpoint

    def send_overdue_alert(
        self, *, actor_id: str, commitment_ids: list[str]
    ) -> str:
        if not commitment_ids:
            raise ValueError("at least one commitment is required")
        now = datetime.now(timezone.utc)
        digest = hashlib.sha256(
            f"{actor_id}:{','.join(sorted(commitment_ids))}".encode()
        ).hexdigest()[:32]
        reference_id = f"receipts~{digest}"
        payload = {
            "timestamp": _timestamp(now),
            "referenceId": reference_id,
            "expiryTime": _timestamp(now + timedelta(hours=1)),
            "event": {
                "name": "AMAZON.MessageAlert.Activated",
                "payload": {
                    "state": {"status": "UNREAD", "freshness": "OVERDUE"},
                    "messageGroup": {
                        "creator": {"name": "Receipts"},
                        "count": len(commitment_ids),
                    },
                },
            },
            "relevantAudience": {"type": "Multicast", "payload": {}},
        }
        response = _post(
            self._endpoint,
            body=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
        )
        if response.status != 202:
            raise RuntimeError(f"Alexa proactive event returned HTTP {response.status}")
        return reference_id

    def _access_token(self) -> str:
        body = parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "alexa::proactive_events",
            }
        ).encode()
        response = _post(
            "https://api.amazon.com/auth/o2/token",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data: Any = json.loads(response.read().decode())
        token = data.get("access_token") if isinstance(data, dict) else None
        if response.status != 200 or not isinstance(token, str) or not token:
            raise RuntimeError("Alexa proactive-events token request failed")
        return token


def _post(url: str, *, body: bytes, headers: dict[str, str]):
    outbound = request.Request(url, data=body, headers=headers, method="POST")
    return request.urlopen(outbound, timeout=15)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
