from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import getaddresses
import re
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from settings import WatcherSettings
from store import GoogleConnection


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def build_oauth_flow(
    settings: WatcherSettings,
    *,
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=GMAIL_SCOPES,
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def credentials_for_connection(
    settings: WatcherSettings,
    connection: GoogleConnection,
) -> Credentials:
    scopes = [scope for scope in connection.scopes.split(" ") if scope]
    return Credentials(
        token=None,
        refresh_token=connection.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=scopes or GMAIL_SCOPES,
    )


def google_profile(credentials: Credentials) -> dict[str, Any]:
    gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    return gmail.users().getProfile(userId="me").execute()


def list_sent_messages(
    credentials: Credentials,
    *,
    after_epoch_seconds: int,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    """Fetch recent sent messages in a source-neutral shape for AgentCore."""

    gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    response = (
        gmail.users()
        .messages()
        .list(
            userId="me",
            q=f"in:sent after:{after_epoch_seconds}",
            maxResults=max_results,
        )
        .execute()
    )

    messages: list[dict[str, Any]] = []
    for stub in response.get("messages", []):
        message = (
            gmail.users()
            .messages()
            .get(userId="me", id=stub["id"], format="full")
            .execute()
        )
        parsed = _message_to_source(message)
        if parsed is not None:
            messages.append(parsed)

    return sorted(messages, key=lambda item: item["occurred_at"])


def _message_to_source(message: dict[str, Any]) -> dict[str, Any] | None:
    payload = message.get("payload") or {}
    body = _extract_text(payload).strip()
    if not body:
        # Gmail's snippet is intentionally a last-resort fallback. It is still
        # source text, but the Arbiter may be less confident because it is short.
        body = str(message.get("snippet") or "").strip()
    if not body:
        return None

    headers = {
        str(header.get("name", "")).casefold(): str(header.get("value", ""))
        for header in payload.get("headers", [])
    }
    address_headers = [
        value
        for value in (
            headers.get("to", ""),
            headers.get("cc", ""),
            headers.get("bcc", ""),
        )
        if value.strip()
    ]
    participants = [
        address
        for _, address in getaddresses(address_headers)
        if address
    ]
    internal_ms = int(message.get("internalDate") or 0)
    occurred_at = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc)

    return {
        "source": "gmail",
        "source_id": str(message["id"]),
        "direction": "sent",
        "body": body,
        "subject": headers.get("subject") or None,
        "participants": participants,
        "occurred_at": occurred_at.isoformat(),
    }


def _extract_text(part: dict[str, Any]) -> str:
    mime_type = str(part.get("mimeType") or "")
    body = part.get("body") or {}
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return _decode_urlsafe(data)

    plain_parts: list[str] = []
    html_parts: list[str] = []
    for child in part.get("parts", []) or []:
        child_mime = str(child.get("mimeType") or "")
        text = _extract_text(child)
        if not text:
            continue
        if child_mime == "text/html":
            html_parts.append(text)
        else:
            plain_parts.append(text)

    if plain_parts:
        return "\n".join(plain_parts)
    if html_parts:
        return "\n".join(html_parts)

    if mime_type == "text/html" and data:
        html = _decode_urlsafe(data)
        return _strip_html(html)
    if data and mime_type.startswith("text/"):
        return _decode_urlsafe(data)
    return ""


def _decode_urlsafe(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode(
        "utf-8", errors="replace"
    )


def _strip_html(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()
