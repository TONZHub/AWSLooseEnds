"""Exact Promise Pocket stores for local development and DynamoDB."""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path
from threading import Lock
from typing import Protocol

from .models import Commitment
from .settings import Settings


class CommitmentStore(Protocol):
    def save(self, commitment: Commitment) -> None: ...

    def list_for_actor(self, actor_id: str) -> list[Commitment]: ...

    def get(self, actor_id: str, commitment_id: str) -> Commitment | None: ...


class InMemoryCommitmentStore:
    def __init__(self, commitments: Iterable[Commitment] = ()) -> None:
        self._items = {item.commitment_id: item for item in commitments}

    def save(self, commitment: Commitment) -> None:
        self._items[commitment.commitment_id] = commitment

    def list_for_actor(self, actor_id: str) -> list[Commitment]:
        return [item for item in self._items.values() if item.actor_id == actor_id]

    def get(self, actor_id: str, commitment_id: str) -> Commitment | None:
        item = self._items.get(commitment_id)
        return item if item is not None and item.actor_id == actor_id else None


class LocalJsonCommitmentStore:
    """Small, durable local store. Not safe for a deployed multi-process runtime."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = Lock()

    def _read(self) -> list[Commitment]:
        if not self._path.exists():
            return []
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("local commitment file must contain a JSON array")
        return [Commitment.model_validate(item) for item in payload]

    def save(self, commitment: Commitment) -> None:
        with self._lock:
            items = self._read()
            by_id = {item.commitment_id: item for item in items}
            by_id[commitment.commitment_id] = commitment
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(self._path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(
                    [item.model_dump(mode="json") for item in by_id.values()],
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(self._path)

    def list_for_actor(self, actor_id: str) -> list[Commitment]:
        with self._lock:
            return [item for item in self._read() if item.actor_id == actor_id]

    def get(self, actor_id: str, commitment_id: str) -> Commitment | None:
        with self._lock:
            return next(
                (
                    item
                    for item in self._read()
                    if item.actor_id == actor_id
                    and item.commitment_id == commitment_id
                ),
                None,
            )


class DynamoDbCommitmentStore:
    def __init__(self, table_name: str, region_name: str | None = None) -> None:
        import boto3

        self._table = boto3.resource("dynamodb", region_name=region_name).Table(
            table_name
        )

    @staticmethod
    def _to_item(commitment: Commitment) -> dict:
        item = commitment.model_dump(mode="json")
        item["actor_status"] = f"{commitment.actor_id}#{commitment.status.value}"
        item["next_review_at"] = (
            commitment.next_review_at.isoformat()
            if commitment.next_review_at is not None
            else "9999-12-31T23:59:59+00:00"
        )
        return item

    def save(self, commitment: Commitment) -> None:
        self._table.put_item(Item=self._to_item(commitment))

    def list_for_actor(self, actor_id: str) -> list[Commitment]:
        from boto3.dynamodb.conditions import Key

        response = self._table.query(
            KeyConditionExpression=Key("actor_id").eq(actor_id)
        )
        items = list(response.get("Items", []))
        while response.get("LastEvaluatedKey"):
            response = self._table.query(
                KeyConditionExpression=Key("actor_id").eq(actor_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        for item in items:
            item.pop("actor_status", None)
            item.pop("next_review_at", None)
        return [Commitment.model_validate(item) for item in items]

    def get(self, actor_id: str, commitment_id: str) -> Commitment | None:
        response = self._table.get_item(
            Key={"actor_id": actor_id, "commitment_id": commitment_id}
        )
        item = response.get("Item")
        if item is None:
            return None
        item.pop("actor_status", None)
        item.pop("next_review_at", None)
        return Commitment.model_validate(item)


def build_store(settings: Settings) -> CommitmentStore:
    if settings.table_name:
        return DynamoDbCommitmentStore(
            table_name=settings.table_name,
            region_name=settings.region_name,
        )
    if settings.local_dev:
        return LocalJsonCommitmentStore(settings.local_path)
    raise RuntimeError(
        "LOOSE_ENDS_TABLE is required outside local development; refusing "
        "to use ephemeral runtime storage"
    )
