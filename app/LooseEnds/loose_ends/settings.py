"""Environment-backed configuration with a fail-closed deployed mode."""

from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_MODEL_ID = "us.amazon.nova-lite-v1:0"


@dataclass(frozen=True, slots=True)
class Settings:
    local_dev: bool
    local_path: str
    table_name: str | None
    region_name: str | None
    dev_actor: str | None
    timezone_name: str
    model_id: str

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            local_dev=os.getenv("LOCAL_DEV") == "1",
            local_path=os.getenv(
                "LOOSE_ENDS_LOCAL_PATH", ".data/commitments.json"
            ),
            table_name=os.getenv("LOOSE_ENDS_TABLE"),
            region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
            dev_actor=os.getenv("LOOSE_ENDS_DEV_ACTOR"),
            timezone_name=os.getenv("LOOSE_ENDS_TIMEZONE", "UTC"),
            model_id=os.getenv("MODEL_ID", DEFAULT_MODEL_ID),
        )
