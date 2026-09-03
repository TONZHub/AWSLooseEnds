from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import secrets
import sqlite3

from cryptography.fernet import Fernet


@dataclass(frozen=True, slots=True)
class GoogleConnection:
    actor_id: str
    email: str
    refresh_token: str
    scopes: str
    last_checked_at: datetime | None


@dataclass(frozen=True, slots=True)
class OAuthStateContext:
    actor_id: str
    code_verifier: str


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
        with closing(self._connect()) as db, db:
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
                    expires_at TEXT NOT NULL,
                    code_verifier TEXT
                )
                """
            )
            columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(oauth_states)")
            }
            if "code_verifier" not in columns:
                db.execute("ALTER TABLE oauth_states ADD COLUMN code_verifier TEXT")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS proactive_notifications (
                    actor_id TEXT NOT NULL,
                    commitment_id TEXT NOT NULL,
                    reference_id TEXT NOT NULL,
                    sent_at TEXT NOT NULL,
                    PRIMARY KEY(actor_id, commitment_id)
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS mobile_sessions (
                    token_hash TEXT PRIMARY KEY,
                    installation_hash TEXT NOT NULL UNIQUE,
                    actor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_oauth_state(
        self,
        *,
        state: str,
        actor_id: str,
        expires_at: datetime,
        code_verifier: str,
    ) -> None:
        with closing(self._connect()) as db, db:
            db.execute(
                """
                INSERT OR REPLACE INTO oauth_states(
                    state, actor_id, expires_at, code_verifier
                ) VALUES(?, ?, ?, ?)
                """,
                (state, actor_id, expires_at.isoformat(), code_verifier),
            )

    def consume_oauth_state(self, state: str) -> OAuthStateContext | None:
        now = datetime.now(timezone.utc)
        with closing(self._connect()) as db, db:
            row = db.execute(
                """
                SELECT actor_id, expires_at, code_verifier
                FROM oauth_states
                WHERE state = ?
                """,
                (state,),
            ).fetchone()
            db.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= now:
            return None
        code_verifier = str(row["code_verifier"] or "")
        if not code_verifier:
            return None
        return OAuthStateContext(
            actor_id=str(row["actor_id"]),
            code_verifier=code_verifier,
        )

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
        with closing(self._connect()) as db, db:
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
        with closing(self._connect()) as db, db:
            rows = db.execute(
                "SELECT actor_id, email, refresh_token, scopes, last_checked_at FROM google_connections"
            ).fetchall()
        return [self._decode_connection(row) for row in rows]

    def update_last_checked(self, *, actor_id: str, checked_at: datetime) -> None:
        with closing(self._connect()) as db, db:
            db.execute(
                "UPDATE google_connections SET last_checked_at = ?, updated_at = ? WHERE actor_id = ?",
                (checked_at.isoformat(), datetime.now(timezone.utc).isoformat(), actor_id),
            )

    def pending_nudges(
        self, *, actor_id: str, nudges: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        valid_ids = [
            item["commitment_id"]
            for item in nudges
            if isinstance(item.get("commitment_id"), str)
            and item["commitment_id"]
        ]
        if not valid_ids:
            return []
        placeholders = ",".join("?" for _ in valid_ids)
        with closing(self._connect()) as db:
            sent = {
                str(row[0])
                for row in db.execute(
                    f"""SELECT commitment_id FROM proactive_notifications
                    WHERE actor_id = ? AND commitment_id IN ({placeholders})""",
                    (actor_id, *valid_ids),
                )
            }
        return [item for item in nudges if item.get("commitment_id") not in sent]

    def mark_nudges_sent(
        self,
        *,
        actor_id: str,
        commitment_ids: list[str],
        reference_id: str,
    ) -> None:
        sent_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            db.executemany(
                """INSERT OR IGNORE INTO proactive_notifications(
                    actor_id, commitment_id, reference_id, sent_at
                ) VALUES(?, ?, ?, ?)""",
                [
                    (actor_id, commitment_id, reference_id, sent_at)
                    for commitment_id in commitment_ids
                ],
            )

    def public_status(self) -> list[dict[str, str | None]]:
        with closing(self._connect()) as db, db:
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

    def issue_mobile_session(self, *, installation_id: str, actor_id: str) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        installation_hash = hashlib.sha256(installation_id.encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            db.execute(
                "DELETE FROM mobile_sessions WHERE installation_hash = ?",
                (installation_hash,),
            )
            db.execute(
                """INSERT INTO mobile_sessions(
                    token_hash, installation_hash, actor_id, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?)""",
                (token_hash, installation_hash, actor_id, now, now),
            )
        return token

    def mobile_actor_for_token(self, token: str) -> str | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with closing(self._connect()) as db, db:
            row = db.execute(
                "SELECT actor_id FROM mobile_sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
            if row is not None:
                db.execute(
                    "UPDATE mobile_sessions SET updated_at = ? WHERE token_hash = ?",
                    (datetime.now(timezone.utc).isoformat(), token_hash),
                )
        return str(row["actor_id"]) if row is not None else None

    def revoke_mobile_session(self, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "DELETE FROM mobile_sessions WHERE token_hash = ?",
                (token_hash,),
            )
            return cursor.rowcount > 0

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
