"""Local deterministic reviewer, useful before the AgentCore runtime is live."""

from __future__ import annotations

import argparse
from datetime import datetime
import json

from .service import CommitmentService
from .settings import Settings
from .storage import build_store


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("time must include a UTC offset")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Return only Promise Pocket items that need human attention."
    )
    parser.add_argument("--actor", required=True)
    parser.add_argument("--now", type=_aware_datetime)
    args = parser.parse_args()

    settings = Settings.from_environment()
    service = CommitmentService(build_store(settings))
    items = service.review(actor_id=args.actor, now=args.now)
    print(
        json.dumps(
            [item.model_dump(mode="json") for item in items],
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
