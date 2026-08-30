from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from cryptography.fernet import Fernet


@dataclass(frozen=True, slots=True)
class GoogleConnection:
    actor_id: str
    email: str
    refresh_token: str
    scopes: str
    last_checked_at: datetime | None


class ConnectionStore:
    def __init__(self, database_path: str, encryption_key: str) -> None:
        self._path = Path(database_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(encryption_key.encode("utf-8"))
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS google_connections (
                    actor_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    refresh_token BLOB NOT NULL,
                    scopes TEXT NOT NULL,
                    last_checked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

    def save_oauth_state(
        self,
        *,
        state: str,
        actor_id: str,
        expires_at: datetime,
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO oauth_states(state, actor_id, expires_at) VALUES(?, ?, ?)",
                (state, actor_id, expires_at.isoformat()),
            )

    def consume_oauth_state(self, state: str) -> str | None:
        now = datetime.now(timezone.utc)
        with self._connect() as db:
            row = db.execute(
                "SELECT actor_id, expires_at FROM oauth_states WHERE state = ?",
                (state,),
            ).fetchone()
            db.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= now:
            return None
        return str(row["actor_id"])

    def save_google_connection(
        self,
        *,
        actor_id: str,
        email: str,
        refresh_token: str,
        scopes: list[str],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        encrypted = self._fernet.encrypt(refresh_token.encode("utf-8"))
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO google_connections(
                    actor_id, email, refresh_token, scopes, last_checked_at,
                    created_at, updated_at
                ) VALUES(?, ?, ?, ?, NULL, ?, ?)
                ON CONFLICT(actor_id) DO UPDATE SET
                    email = excluded.email,
                    refresh_token = excluded.refresh_token,
                    scopes = excluded.scopes,
                    last_checked_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (actor_id, email, encrypted, " ".join(scopes), now, now),
            )

    def list_google_connections(self) -> list[GoogleConnection]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT actor_id, email, refresh_token, scopes, last_checked_at FROM google_connections"
            ).fetchall()
        return [self._decode_connection(row) for row in rows]

    def update_last_checked(self, *, actor_id: str, checked_at: datetime) -> None:
        with self._connect() as db:
            db.execute(
                "UPDATE google_connections SET last_checked_at = ?, updated_at = ? WHERE actor_id = ?",
                (checked_at.isoformat(), datetime.now(timezone.utc).isoformat(), actor_id),
            )

    def public_status(self) -> list[dict[str, str | None]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT actor_id, email, last_checked_at FROM google_connections ORDER BY email"
            ).fetchall()
        return [
            {
                "actor_id": str(row["actor_id"]),
                "email": str(row["email"]),
                "last_checked_at": row["last_checked_at"],
            }
            for row in rows
        ]

    def _decode_connection(self, row: sqlite3.Row) -> GoogleConnection:
        decrypted = self._fernet.decrypt(row["refresh_token"]).decode("utf-8")
        last_checked_at = (
            datetime.fromisoformat(row["last_checked_at"])
            if row["last_checked_at"]
            else None
        )
        return GoogleConnection(
            actor_id=str(row["actor_id"]),
            email=str(row["email"]),
            refresh_token=decrypted,
            scopes=str(row["scopes"]),
            last_checked_at=last_checked_at,
        )
