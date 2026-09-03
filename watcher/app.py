from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import logging
from pathlib import Path
import secrets
from secrets import compare_digest
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, Field

from agentcore_client import PocketPromiseAgentCoreClient
from alexa_proactive import AlexaProactiveClient
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
alexa_proactive = (
    AlexaProactiveClient(
        client_id=settings.alexa_proactive_client_id,
        client_secret=settings.alexa_proactive_client_secret,
        endpoint=settings.alexa_proactive_endpoint,
    )
    if settings.proactive_notifications_enabled
    else None
)
security = HTTPBasic()
mobile_security = HTTPBearer(auto_error=False)
FAVICON_PATH = Path(__file__).with_name("favicon.png")


class MobileLinkRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    installation_id: str = Field(min_length=16, max_length=200)


class MobileCaptureRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    source_id: str = Field(min_length=8, max_length=200)


def require_mobile_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(mobile_security),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="mobile link required")
    actor_id = store.mobile_actor_for_token(credentials.credentials)
    if actor_id is None:
        raise HTTPException(status_code=401, detail="mobile link expired")
    return actor_id


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
    nudges = overdue.get("nudges") or []
    pending_nudges = store.pending_nudges(
        actor_id=connection.actor_id,
        nudges=nudges,
    )
    notification_reference = None
    if alexa_proactive is not None and pending_nudges:
        commitment_ids = [item["commitment_id"] for item in pending_nudges]
        notification_reference = await asyncio.to_thread(
            alexa_proactive.send_overdue_alert,
            actor_id=connection.actor_id,
            commitment_ids=commitment_ids,
        )
        store.mark_nudges_sent(
            actor_id=connection.actor_id,
            commitment_ids=commitment_ids,
            reference_id=notification_reference,
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
        "nudges_prepared": nudges,
        "nudges_pending": len(pending_nudges),
        "notification_reference": notification_reference,
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


app = FastAPI(title="Receipts Watcher", lifespan=lifespan)


RECEIPTS_CSS = """
  :root { --ink:#11100e; --paper:#eee6ce; --paper-2:#d9ceb0; --red:#b62922;
    --yellow:#f2d83d; --muted:#746d5f; color-scheme:dark; }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; color:var(--ink); background:#050505;
    font-family:"Courier New",Courier,monospace;
    background-image:radial-gradient(circle at 50% 20%,#24211c 0,#090909 48%,#000 100%); }
  body::before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.16;
    background-image:repeating-linear-gradient(8deg,transparent 0 5px,#fff 6px,transparent 7px); }
  a { color:inherit; }
  .stage { width:min(940px,calc(100% - 28px)); margin:clamp(28px,6vw,72px) auto; position:relative; }
  .paper { position:relative; overflow:hidden; padding:clamp(28px,6vw,72px); background:var(--paper);
    box-shadow:14px 15px 0 rgba(182,41,34,.72),0 28px 80px #000;
    clip-path:polygon(0 1.2%,3% 0,7% 1%,12% .2%,18% 1.1%,25% .3%,31% .8%,39% 0,46% 1%,54% .2%,61% .9%,68% .1%,75% .8%,82% 0,89% .9%,95% .2%,100% 1%,99.3% 98.8%,94% 100%,87% 99%,80% 99.8%,73% 99%,66% 100%,58% 99.1%,51% 100%,43% 99%,35% 99.8%,28% 99%,20% 100%,12% 99.1%,5% 100%,.7% 98.7%); }
  .paper::before { content:""; position:absolute; inset:0; pointer-events:none; opacity:.12;
    background:repeating-radial-gradient(circle at 15% 30%,#000 0 1px,transparent 1px 5px); }
  .tape { position:absolute; z-index:2; width:112px; height:30px; top:-12px; left:12%;
    background:rgba(225,215,174,.72); transform:rotate(-4deg); box-shadow:0 1px 4px #0005; }
  .tape.right { left:auto; right:10%; transform:rotate(5deg); }
  .eyebrow,.stamp { text-transform:uppercase; letter-spacing:.22em; font-size:.72rem; font-weight:700; }
  .eyebrow::before { content:""; display:inline-block; width:8px; height:8px; margin-right:10px;
    border-radius:50%; background:var(--red); box-shadow:0 0 12px var(--red); animation:pulse 1.8s infinite; }
  @keyframes pulse { 50% { opacity:.25; } }
  .wordmark { display:flex; flex-wrap:wrap; align-items:center; gap:2px; margin:32px 0 24px;
    font-family:Georgia,serif; font-size:clamp(3.1rem,11vw,7.2rem); line-height:.88; }
  .cut { display:inline-block; padding:.03em .1em .08em; background:#eee9dc; border:2px solid #171717;
    box-shadow:3px 4px 0 #171717; transform:rotate(-3deg); }
  .cut:nth-child(2n) { font-family:Impact,Haettenschweiler,sans-serif; background:var(--red); color:#f5ebd4; transform:rotate(3deg); }
  .cut:nth-child(3n) { background:#111; color:var(--yellow); transform:rotate(-1deg); }
  .cut:nth-child(5n) { font-style:italic; color:var(--red); transform:rotate(4deg); }
  .admin-link { text-decoration:none; color:inherit; cursor:default; }
  .admin-link:hover,.admin-link:focus { text-decoration:none; color:inherit; outline:none; }
  .lede { max-width:720px; font:clamp(1.05rem,2vw,1.35rem)/1.65 Georgia,serif; }
  .highlight { display:inline-block; padding:0 .24em; color:var(--yellow); background:#111; font-weight:900; transform:rotate(-1deg); }
  .evidence { margin:32px 0 24px; padding:24px; color:#eee6ce; background:#111; border-left:5px solid var(--red);
    box-shadow:7px 8px 0 var(--red); }
  .evidence p { font:italic 1.02rem/1.6 Georgia,serif; }
  .actions { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:32px 0; }
  .action { display:block; min-height:112px; padding:20px; text-decoration:none; border:2px solid #111;
    background:#f5efdd; box-shadow:5px 6px 0 #111; transition:transform .15s,box-shadow .15s; }
  .action:hover,.action:focus-visible { transform:translate(-2px,-3px) rotate(-.4deg); box-shadow:8px 10px 0 var(--red); outline:none; }
  .action strong { display:block; margin-bottom:10px; text-transform:uppercase; letter-spacing:.08em; }
  .action small { color:#544e43; line-height:1.45; }
  .source-auth { margin:32px 0; padding:24px; border:2px solid #111; background:#f5efdd;
    box-shadow:7px 8px 0 var(--red); }
  .source-auth label { display:block; margin-bottom:9px; text-transform:uppercase; letter-spacing:.12em; font-weight:700; }
  .source-auth input { width:100%; padding:13px 14px; color:#111; background:#fffdf5; border:2px solid #111;
    border-radius:0; font:1rem "Courier New",monospace; }
  .source-auth input:focus-visible { outline:3px solid var(--yellow); outline-offset:2px; }
  .source-auth .meta { display:block; margin:9px 0 18px; }
  .google-button { display:flex; align-items:center; justify-content:center; gap:12px; width:100%; min-height:48px;
    padding:10px 16px; color:#202124; background:#fff; border:1px solid #747775; border-radius:4px;
    box-shadow:2px 3px 0 #111; font:600 .95rem Arial,sans-serif; cursor:pointer; }
  .google-button:hover,.google-button:focus-visible { background:#f8faff; outline:3px solid var(--yellow); outline-offset:2px; }
  .google-button img { width:20px; height:20px; }
  .auth-error { margin:0 0 16px; padding:10px 12px; color:#f5ebd4; background:var(--red); font-weight:700; }
  .code { margin:24px 0; padding:18px; text-align:center; background:#111; color:var(--paper); border-left:7px solid var(--red); }
  .code strong { display:block; color:var(--yellow); font:700 clamp(2.5rem,10vw,5.5rem)/1 "Courier New",monospace; letter-spacing:.24em; }
  .meta { color:var(--muted); font-size:.78rem; line-height:1.6; overflow-wrap:anywhere; }
  footer { display:flex; justify-content:space-between; gap:20px; margin-top:42px; padding-top:18px; border-top:1px solid #918875; color:var(--muted); font-size:.72rem; }
  footer a { text-decoration-thickness:2px; }
  @media (max-width:600px) {
    .paper { padding:40px 22px 32px; }
    .wordmark { margin-top:24px; }
    footer { flex-direction:column; }
  }
  @media (max-width:450px) {
    .wordmark { flex-wrap:nowrap; gap:1px; font-size:clamp(1.8rem,10vw,2.8rem); }
  }
  @media (prefers-reduced-motion:reduce) { * { animation:none!important; transition:none!important; } }
"""


def receipts_wordmark() -> str:
    return """<div class="wordmark" aria-label="Receipts">
      <a href="/admin" class="cut admin-link" title="Receipts">R</a><span class="cut">e</span><span class="cut">C</span>
      <span class="cut">i</span><span class="cut">E</span><span class="cut">PT</span><span class="cut">S</span>
    </div>"""


def receipts_page(*, title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{title} · Receipts</title><link rel="icon" type="image/png" sizes="64x64" href="/favicon.png">
      <style>{RECEIPTS_CSS}</style></head>
      <body><main class="stage"><i class="tape" aria-hidden="true"></i><i class="tape right" aria-hidden="true"></i>
      <article class="paper"><div class="eyebrow">the watcher is alive</div>{receipts_wordmark()}{body}
      <footer><span>DO NOT DISCARD · REF RCPT-001</span><a href="/privacy">Privacy</a><em>we have the receipts.</em></footer>
      </article></main></body></html>"""


def require_admin(
    credentials: HTTPBasicCredentials = Depends(security),
) -> None:
    if not settings.admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="watcher admin key is not configured on this instance",
        )
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


@app.get("/favicon.png", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return receipts_page(
        title="Evidence ledger",
        body="""
          <p class="lede">Every promise captured becomes <span class="highlight">EVIDENCE.</span>
          Every deadline—recorded. The ledger does not sleep.</p>
          <section class="evidence"><div class="stamp">intercepted · awaiting statement</div>
          <p>“I said I would do it. Receipts remembers the part that matters.”</p></section>
          <nav class="actions" aria-label="Receipts actions">
            <a class="action" href="/connect/google"><strong>Connect Gmail</strong><small>Watch authorized sent mail for commitments and evidence of follow-through.</small></a>
            <a class="action" href="/alexa/pair"><strong>Pair Alexa</strong><small>Generate a short-lived code. No Login with Amazon required.</small></a>
            <a class="action" href="/mobile/pair"><strong>Pair Android</strong><small>Issue a one-time code that connects the phone to this evidence ledger.</small></a>
            <a class="action" href="/status"><strong>Watcher status</strong><small>Inspect connected sources and the last completed scan.</small></a>
          </nav>
        """,
    )


@app.get("/alexa/pair", response_class=HTMLResponse)
def alexa_pair() -> str:
    result = agentcore.create_alexa_pairing(actor_id=settings.demo_actor_id)
    code = result.get("code")
    expires_at = result.get("expires_at")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=502, detail="AgentCore returned an invalid pairing code")
    if not isinstance(expires_at, str) or not expires_at:
        raise HTTPException(status_code=502, detail="AgentCore returned an invalid expiry")

    return receipts_page(
        title="Pair Alexa",
        body=f"""
          <p class="lede">Read this one-time evidence code to Alexa:</p>
          <div class="code"><span class="stamp">pairing exhibit</span><strong>{code}</strong></div>
          <section class="evidence"><div class="stamp">statement</div>
          <p>“Alexa, tell my receipts to link code {code}.”</p></section>
          <p class="meta">Single-use. Expires at {expires_at}. After Alexa confirms the connection,
          anything captured through this Alexa identity resolves to the selected ledger.</p>
          <nav class="actions" aria-label="Pairing actions">
            <a class="action" href="/alexa/pair"><strong>Issue another code</strong><small>Invalidate nothing; create a fresh ten-minute pairing exhibit.</small></a>
            <a class="action" href="/"><strong>Return to the ledger</strong><small>Back to source connections and watcher status.</small></a>
          </nav>
        """,
    )


@app.get("/mobile/pair", response_class=HTMLResponse)
def mobile_pair() -> str:
    result = agentcore.create_alexa_pairing(actor_id=settings.demo_actor_id)
    code = result.get("code")
    expires_at = result.get("expires_at")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=502, detail="AgentCore returned an invalid pairing code")
    return receipts_page(
        title="Pair Android",
        body=f"""
          <p class="lede">Enter this one-time evidence code in the Receipts app:</p>
          <div class="code"><span class="stamp">mobile pairing exhibit</span><strong>{code}</strong></div>
          <section class="evidence"><p>The code expires at {expires_at}. The phone receives a revocable token; the raw pairing code is never stored.</p></section>
          <nav class="actions"><a class="action" href="/mobile/pair"><strong>Issue another code</strong><small>Create a fresh ten-minute mobile pairing exhibit.</small></a></nav>
        """,
    )


def google_connect_page(*, invalid_key: bool = False) -> str:
    error_html = (
        '<p class="auth-error" role="alert">That access key did not match the ledger.</p>'
        if invalid_key
        else ""
    )
    key_field = (
        """
        <label for="access-key">Evidence desk access key</label>
        <input id="access-key" name="access_key" type="password" required
          autocomplete="current-password" aria-describedby="access-key-note">
        <small class="meta" id="access-key-note">This protects the configured demo ledger before Google authorization begins.</small>
        """
        if settings.admin_key
        else ""
    )
    return receipts_page(
        title="Connect Gmail",
        body=f"""
          <p class="lede">Authorize a new <span class="highlight">SOURCE.</span>
          Receipts will inspect authorized sent mail for promises and evidence of follow-through.</p>
          <section class="evidence"><div class="stamp">chain of custody</div>
          <p>Read-only Gmail access. Full messages are inspected in transit and are not stored by the watcher.</p></section>
          <form class="source-auth" method="post" action="/connect/google">
            {error_html}
            {key_field}
            <button class="google-button" type="submit">
              <img src="https://developers.google.com/identity/images/g-logo.png" alt="" referrerpolicy="no-referrer">
              Continue with Google
            </button>
          </form>
          <p class="meta">The next screen belongs to Google, so its account chooser cannot wear the Receipts theme.
          You will return here with a connection receipt when authorization finishes.</p>
        """,
    )


@app.post("/api/mobile/v1/link")
def mobile_link(payload: MobileLinkRequest) -> dict:
    installation_hash = hashlib.sha256(payload.installation_id.encode()).hexdigest()
    actor_id = f"mobile-{installation_hash}"
    result = agentcore.claim_pairing(actor_id=actor_id, code=payload.code)
    if result.get("linked") is not True:
        raise HTTPException(status_code=400, detail="invalid or expired pairing code")
    token = store.issue_mobile_session(
        installation_id=payload.installation_id,
        actor_id=actor_id,
    )
    return {"linked": True, "token": token, "actor_id": actor_id}


@app.get("/api/mobile/v1/commitments")
def mobile_commitments(actor_id: str = Depends(require_mobile_actor)) -> dict:
    return agentcore.list_commitments(actor_id=actor_id)


@app.post("/api/mobile/v1/capture")
def mobile_capture(
    payload: MobileCaptureRequest,
    actor_id: str = Depends(require_mobile_actor),
) -> dict:
    return agentcore.capture_mobile_message(
        actor_id=actor_id,
        source_id=payload.source_id,
        text=payload.text,
    )


@app.post("/api/mobile/v1/commitments/{commitment_id}/{action}")
def mobile_transition(
    commitment_id: str,
    action: str,
    actor_id: str = Depends(require_mobile_actor),
) -> dict:
    if action not in {"confirm", "done", "reopen", "cancel"}:
        raise HTTPException(status_code=404, detail="unsupported commitment action")
    return agentcore.transition_commitment(
        actor_id=actor_id,
        commitment_id=commitment_id,
        action=action,
    )


@app.post("/api/mobile/v1/unlink")
def mobile_unlink(
    credentials: HTTPAuthorizationCredentials | None = Depends(mobile_security),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="missing authorization token")
    revoked = store.revoke_mobile_session(credentials.credentials)
    return {"unlinked": True, "revoked": revoked}


def begin_google_authorization() -> RedirectResponse:
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


@app.get("/connect/google", response_class=HTMLResponse)
def google_connect() -> str:
    return google_connect_page()


@app.post("/connect/google", response_model=None)
async def google_connect_submit(request: Request) -> Response:
    body = await request.body()
    values = parse_qs(body[:4096].decode("utf-8", errors="replace"), keep_blank_values=True)
    access_key = str((values.get("access_key") or [""])[0])
    if settings.admin_key and not compare_digest(access_key, settings.admin_key):
        return HTMLResponse(google_connect_page(invalid_key=True), status_code=401)
    return begin_google_authorization()


@app.get("/auth/google/start")
def google_auth_start() -> RedirectResponse:
    return begin_google_authorization()


@app.get("/auth/google/callback", response_class=HTMLResponse)
def google_auth_callback(
    state: str = Query(...),
    code: str | None = Query(None),
    error: str | None = Query(None),
) -> str:
    # The callback is protected by high-entropy, single-use OAuth state plus PKCE.
    oauth_context = store.consume_oauth_state(state)
    if oauth_context is None:
        raise HTTPException(status_code=400, detail="invalid or expired OAuth state")
    if error:
        return receipts_page(
            title="Google connection canceled",
            body="""
              <p class="lede"><span class="highlight">NO SOURCE ADDED.</span>
              Google authorization was canceled. The ledger remains unchanged.</p>
              <nav class="actions" aria-label="Connection actions">
                <a class="action" href="/connect/google"><strong>Try again</strong><small>Return to the source authorization desk.</small></a>
                <a class="action" href="/"><strong>Return to Receipts</strong><small>Back to the evidence ledger.</small></a>
              </nav>
            """,
        )
    if not code:
        raise HTTPException(status_code=400, detail="Google returned no authorization code")

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
    return receipts_page(
        title="Gmail connected",
        body=f"""
          <p class="lede"><span class="highlight">SOURCE CONNECTED.</span> Receipts can now inspect
          authorized sent mail for {email}.</p>
          <section class="evidence"><div class="stamp">chain of custody</div>
          <p>The Google refresh token is encrypted. Full email bodies are not persisted by the watcher.</p></section>
          <nav class="actions" aria-label="Connection actions">
            <a class="action" href="/"><strong>Return to Receipts</strong><small>View connections, pair Alexa, or inspect watcher status.</small></a>
          </nav>
        """,
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy() -> str:
    return receipts_page(
        title="Privacy notice",
        body="""
          <p class="lede">Receipts keeps evidence of commitments—not a secret archive of your life.</p>
          <section class="evidence"><div class="stamp">plain-language notice</div>
          <p>Receipts processes commitments you intentionally capture and authorized sent Gmail messages.
          Alexa contributes an opaque device identity. Pairing codes are short-lived and single-use.
          Refresh tokens are encrypted, and the watcher does not persist full emails.</p></section>
          <p class="meta">Receipts does not use Login with Amazon, sell personal information, or use it for advertising.</p>
          <nav class="actions"><a class="action" href="/"><strong>Return to Receipts</strong><small>Back to the evidence desk.</small></a></nav>
        """,
    )


@app.post("/scan-now", dependencies=[Depends(require_admin)])
async def scan_now() -> dict:
    return {"results": await scan_all_connections()}


@app.get("/status")
def watcher_status() -> dict:
    return {
        "poll_interval_seconds": settings.poll_interval_seconds,
        "connections": store.public_status(),
    }


@app.get("/admin", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
def admin_desk() -> str:
    connections = store.public_status()
    session_count = store.mobile_session_count()
    conn_items = "".join(
        f"<li><strong>{c['email']}</strong> (actor: <code>{c['actor_id']}</code>) — last checked: {c['last_checked_at'] or 'never'}</li>"
        for c in connections
    ) or "<li>No external sources connected yet.</li>"
    return receipts_page(
        title="Admin Desk",
        body=f"""
          <p class="lede"><span class="highlight">WATCHER DESK (ADMIN).</span> Restricted access.</p>
          <section class="evidence"><div class="stamp">system state</div>
          <p>Poll interval: <strong>{settings.poll_interval_seconds}s</strong> · Database: <code>{settings.database_path}</code></p>
          <p>Active mobile sessions: <strong>{session_count}</strong> · Connected sources: <strong>{len(connections)}</strong></p>
          <ul style="margin:12px 0;padding-left:20px;font-family:inherit;font-size:.9rem;line-height:1.6">
            {conn_items}
          </ul>
          </section>
          <nav class="actions" aria-label="Admin actions">
            <form action="/admin/scan-now" method="post" style="display:contents">
              <button type="submit" class="action" style="text-align:left;font-family:inherit;font-size:inherit;cursor:pointer">
                <strong>Trigger Scan Now</strong>
                <small>Run an immediate scan and evidence reconciliation cycle across all accounts.</small>
              </button>
            </form>
            <a class="action" href="/status"><strong>Raw Status JSON</strong><small>Inspect JSON endpoint response.</small></a>
            <a class="action" href="/"><strong>Public Evidence Desk</strong><small>Return to public user landing page.</small></a>
          </nav>
        """,
    )


@app.post("/admin/scan-now", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
async def admin_scan_now() -> str:
    results = await scan_all_connections()
    summary = "<br>".join(
        f"• {r.get('email', 'unknown')}: checked {r.get('messages_checked', 0)} messages, "
        f"{r.get('candidates_seen', 0)} candidates, {r.get('likely_done_seen', 0)} likely done"
        for r in results
    ) or "No connections to scan."
    return receipts_page(
        title="Scan Completed",
        body=f"""
          <p class="lede"><span class="highlight">SCAN COMPLETED.</span> All connections reconciled.</p>
          <section class="evidence"><div class="stamp">scan output</div>
          <p>{summary}</p>
          </section>
          <nav class="actions" aria-label="Admin scan actions">
            <a class="action" href="/admin"><strong>Return to Admin Desk</strong><small>Back to watcher administration.</small></a>
            <a class="action" href="/"><strong>Public Ledger</strong><small>Back to home.</small></a>
          </nav>
        """,
    )
