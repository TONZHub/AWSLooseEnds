from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
import secrets
from secrets import compare_digest

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from agentcore_client import PocketPromiseAgentCoreClient
from google_client import (
    GMAIL_SCOPES,
    build_oauth_flow,
    credentials_for_connection,
    google_profile,
    list_sent_messages,
)
from settings import WatcherSettings
from store import ConnectionStore, GoogleConnection


LOGGER = logging.getLogger("pocket-promise-watcher")
logging.basicConfig(level=logging.INFO)

settings = WatcherSettings.from_environment()
store = ConnectionStore(settings.database_path, settings.token_encryption_key)
agentcore = PocketPromiseAgentCoreClient(settings)
security = HTTPBasic()


async def scan_connection(connection: GoogleConnection) -> dict:
    scan_started = datetime.now(timezone.utc)
    # First connection looks back one hour. Later scans overlap by two minutes;
    # the v2 ledger is source-idempotent, so overlap is safer than missed mail.
    baseline = connection.last_checked_at or (scan_started - timedelta(hours=1))
    after_epoch = max(0, int(baseline.timestamp()) - 120)

    credentials = credentials_for_connection(settings, connection)
    messages = await asyncio.to_thread(
        list_sent_messages,
        credentials,
        after_epoch_seconds=after_epoch,
    )

    candidate_count = 0
    likely_done_count = 0
    for message in messages:
        arbitration = await asyncio.to_thread(
            agentcore.arbitrate_message,
            actor_id=connection.actor_id,
            source_message=message,
        )
        candidate_count += len(arbitration.get("candidate_ids") or [])

        # Reconciliation is separate from detection. The same outgoing message
        # may be irrelevant to commitments, may create a new candidate, or may
        # provide evidence that an already-active promise was fulfilled. The
        # runtime only evaluates ACTIVE/OVERDUE promises and never marks DONE.
        reconciliation = await asyncio.to_thread(
            agentcore.reconcile_message,
            actor_id=connection.actor_id,
            source_message=message,
        )
        likely_done_count += len(reconciliation.get("likely_done_ids") or [])

    # Prepare proactive reminders only after reconciliation has had a chance to
    # move fulfilled promises to LIKELY_DONE. This path returns nudge payloads;
    # it deliberately does not deliver them.
    overdue = await asyncio.to_thread(
        agentcore.prepare_overdue_nudges,
        actor_id=connection.actor_id,
    )

    # Only advance the cursor after every discovered message made it through
    # AgentCore. If anything raises, the overlap will retry the batch next time.
    store.update_last_checked(actor_id=connection.actor_id, checked_at=scan_started)
    return {
        "email": connection.email,
        "messages_checked": len(messages),
        "candidates_seen": candidate_count,
        "likely_done_seen": likely_done_count,
        "overdue_seen": len(overdue.get("overdue_ids") or []),
        "nudges_prepared": overdue.get("nudges") or [],
        "checked_at": scan_started.isoformat(),
    }


async def scan_all_connections() -> list[dict]:
    results: list[dict] = []
    for connection in store.list_google_connections():
        try:
            results.append(await scan_connection(connection))
        except Exception:
            LOGGER.exception("Watcher scan failed for %s", connection.email)
            results.append({"email": connection.email, "error": "scan failed"})
    return results


async def watcher_loop() -> None:
    while True:
        try:
            await scan_all_connections()
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Watcher loop failed")
        await asyncio.sleep(settings.poll_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(watcher_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Pocket Promise Watcher", lifespan=lifespan)


def require_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> None:
    username_ok = compare_digest(credentials.username, "admin")
    password_ok = compare_digest(credentials.password, settings.admin_key)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid watcher admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "pocket-promise-watcher"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <html><body style="font-family: sans-serif; max-width: 720px; margin: 3rem auto;">
      <h1>Pocket Promise Watcher</h1>
      <p>The watcher is alive.</p>
      <p><a href="/auth/google/start">Connect the demo Gmail account</a> (admin protected)</p>
    </body></html>
    """


@app.get("/auth/google/start", dependencies=[Depends(require_admin)])
def google_auth_start() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    store.save_oauth_state(
        state=state,
        actor_id=settings.demo_actor_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        code_verifier=code_verifier,
    )
    flow = build_oauth_flow(
        settings,
        state=state,
        code_verifier=code_verifier,
    )
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback", response_class=HTMLResponse)
def google_auth_callback(
    state: str = Query(...),
    code: str = Query(...),
) -> str:
    # The callback is protected by the high-entropy, single-use OAuth state that
    # could only be created by the admin-protected start route.
    oauth_context = store.consume_oauth_state(state)
    if oauth_context is None:
        raise HTTPException(status_code=400, detail="invalid or expired OAuth state")

    flow = build_oauth_flow(
        settings,
        state=state,
        code_verifier=oauth_context.code_verifier,
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    if not credentials.refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return a refresh token; reconnect and grant consent",
        )

    profile = google_profile(credentials)
    email = str(profile.get("emailAddress") or "unknown")
    store.save_google_connection(
        actor_id=oauth_context.actor_id,
        email=email,
        refresh_token=credentials.refresh_token,
        scopes=list(credentials.scopes or GMAIL_SCOPES),
    )
    return (
        "<html><body style='font-family:sans-serif;max-width:720px;margin:3rem auto;'>"
        "<h1>Gmail connected.</h1>"
        f"<p>Pocket Promise can now watch sent mail for {email}.</p>"
        "<p>The watcher stores the Google refresh token encrypted and does not persist full emails.</p>"
        "</body></html>"
    )


@app.post("/scan-now", dependencies=[Depends(require_admin)])
async def scan_now() -> dict:
    return {"results": await scan_all_connections()}


@app.get("/status", dependencies=[Depends(require_admin)])
def watcher_status() -> dict:
    return {
        "poll_interval_seconds": settings.poll_interval_seconds,
        "connections": store.public_status(),
    }
