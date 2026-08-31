from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class WatcherSettings:
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    token_encryption_key: str
    database_path: str
    demo_actor_id: str
    admin_key: str
    agent_runtime_arn: str
    aws_region: str | None
    timezone_name: str
    poll_interval_seconds: int
    alexa_proactive_client_id: str
    alexa_proactive_client_secret: str
    alexa_proactive_endpoint: str

    @classmethod
    def from_environment(cls) -> "WatcherSettings":
        poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "600"))
        if poll_interval < 60:
            raise ValueError("POLL_INTERVAL_SECONDS must be at least 60")

        settings = cls(
            google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            google_redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", ""),
            token_encryption_key=os.getenv("TOKEN_ENCRYPTION_KEY", ""),
            database_path=os.getenv(
                "DATABASE_PATH", "/var/data/pocket-promise.sqlite3"
            ),
            demo_actor_id=os.getenv("DEMO_ACTOR_ID", ""),
            admin_key=os.getenv("WATCHER_ADMIN_KEY", ""),
            agent_runtime_arn=os.getenv("AGENT_RUNTIME_ARN", ""),
            aws_region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
            timezone_name=os.getenv("POCKET_PROMISE_TIMEZONE", "America/New_York"),
            poll_interval_seconds=poll_interval,
            alexa_proactive_client_id=os.getenv("ALEXA_PROACTIVE_CLIENT_ID", ""),
            alexa_proactive_client_secret=os.getenv("ALEXA_PROACTIVE_CLIENT_SECRET", ""),
            alexa_proactive_endpoint=os.getenv(
                "ALEXA_PROACTIVE_ENDPOINT",
                "https://api.amazonalexa.com/v1/proactiveEvents/stages/development",
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        required = {
            "GOOGLE_CLIENT_ID": self.google_client_id,
            "GOOGLE_CLIENT_SECRET": self.google_client_secret,
            "GOOGLE_REDIRECT_URI": self.google_redirect_uri,
            "TOKEN_ENCRYPTION_KEY": self.token_encryption_key,
            "DEMO_ACTOR_ID": self.demo_actor_id,
            "WATCHER_ADMIN_KEY": self.admin_key,
            "AGENT_RUNTIME_ARN": self.agent_runtime_arn,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required watcher settings: " + ", ".join(sorted(missing))
            )
        proactive_values = (
            self.alexa_proactive_client_id,
            self.alexa_proactive_client_secret,
        )
        if any(proactive_values) and not all(proactive_values):
            raise RuntimeError(
                "ALEXA_PROACTIVE_CLIENT_ID and ALEXA_PROACTIVE_CLIENT_SECRET "
                "must be configured together"
            )

    @property
    def proactive_notifications_enabled(self) -> bool:
        return bool(
            self.alexa_proactive_client_id and self.alexa_proactive_client_secret
        )
