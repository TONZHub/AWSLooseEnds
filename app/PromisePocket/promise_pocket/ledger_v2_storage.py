"""Storage adapters for the Pocket Promise v2 ledger."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .ledger_v2 import InMemoryPromiseLedgerStore, PromiseLedgerStore, PromiseRecord
from .settings import Settings


RECORD_TYPE = "promise_v2"


def _dynamodb_safe(value: Any) -> Any:
    """Convert JSON-shaped model data into values accepted by boto3 DynamoDB.

    boto3's DynamoDB serializer rejects Python ``float`` values. Pocket Promise
    uses floats for confidence scores, so convert them to exact decimal strings
    before writing while preserving the surrounding structure.
    """

    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _dynamodb_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_dynamodb_safe(item) for item in value]
    return value


class DynamoDbPromiseLedgerStore(PromiseLedgerStore):
    """Reuse the deployed commitment table without rewriting legacy records.

    The existing table is keyed by ``actor_id`` + ``commitment_id``. V2 records
    keep those physical key names and add ``record_type=promise_v2`` so old
    reminder-era commitment items may safely coexist during the hackathon pivot.
    """

    def __init__(self, table_name: str, region_name: str | None = None) -> None:
        import boto3

        self._table = boto3.resource("dynamodb", region_name=region_name).Table(
            table_name
        )

    @staticmethod
    def _to_item(record: PromiseRecord) -> dict[str, Any]:
        item = _dynamodb_safe(record.model_dump(mode="json"))
        item["record_type"] = RECORD_TYPE
        # Preserve the old derived attributes in case the deployed table has
        # indexes or tooling that expects them.
        item["actor_status"] = f"{record.actor_id}#{record.status.value}"
        item["next_review_at"] = (
            record.due_at.isoformat()
            if record.due_at is not None
            else "9999-12-31T23:59:59+00:00"
        )
        return item

    @staticmethod
    def _from_item(item: dict[str, Any]) -> PromiseRecord | None:
        if item.get("record_type") != RECORD_TYPE:
            return None
        payload = dict(item)
        payload.pop("record_type", None)
        payload.pop("actor_status", None)
        payload.pop("next_review_at", None)
        return PromiseRecord.model_validate(payload)

    def save(self, record: PromiseRecord) -> None:
        self._table.put_item(Item=self._to_item(record))

    def get(self, actor_id: str, commitment_id: str) -> PromiseRecord | None:
        response = self._table.get_item(
            Key={"actor_id": actor_id, "commitment_id": commitment_id}
        )
        item = response.get("Item")
        if item is None:
            return None
        return self._from_item(item)

    def list_for_actor(self, actor_id: str) -> list[PromiseRecord]:
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

        records: list[PromiseRecord] = []
        for item in items:
            record = self._from_item(item)
            if record is not None:
                records.append(record)
        return records


def build_ledger_v2_store(settings: Settings) -> PromiseLedgerStore:
    if settings.table_name:
        return DynamoDbPromiseLedgerStore(
            table_name=settings.table_name,
            region_name=settings.region_name,
        )
    if settings.local_dev:
        return InMemoryPromiseLedgerStore()
    raise RuntimeError(
        "LOOSE_ENDS_TABLE is required for the Pocket Promise v2 ledger"
    )
