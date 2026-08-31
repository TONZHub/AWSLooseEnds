from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import secrets
from secrets import compare_digest

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
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
FAVICON_PATH = Path(__file__).with_name("favicon.png")


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
  .code { margin:24px 0; padding:18px; text-align:center; background:#111; color:var(--paper); border-left:7px solid var(--red); }
  .code strong { display:block; color:var(--yellow); font:700 clamp(2.5rem,10vw,5.5rem)/1 "Courier New",monospace; letter-spacing:.24em; }
  .meta { color:var(--muted); font-size:.78rem; line-height:1.6; overflow-wrap:anywhere; }
  footer { display:flex; justify-content:space-between; gap:20px; margin-top:42px; padding-top:18px; border-top:1px solid #918875; color:var(--muted); font-size:.72rem; }
  footer a { text-decoration-thickness:2px; }
  @media (max-width:600px) { .paper { padding:40px 22px 32px; } .wordmark { margin-top:24px; } footer { flex-direction:column; } }
  @media (prefers-reduced-motion:reduce) { * { animation:none!important; transition:none!important; } }
"""


def receipts_wordmark() -> str:
    return """<div class="wordmark" aria-label="Receipts">
      <span class="cut">R</span><span class="cut">e</span><span class="cut">C</span>
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
            <a class="action" href="/auth/google/start"><strong>Connect Gmail</strong><small>Watch authorized sent mail for commitments and evidence of follow-through.</small></a>
            <a class="action" href="/alexa/pair"><strong>Pair Alexa</strong><small>Generate a short-lived code. No Login with Amazon required.</small></a>
            <a class="action" href="/status"><strong>Watcher status</strong><small>Inspect connected sources and the last completed scan.</small></a>
          </nav>
        """,
    )


@app.get("/alexa/pair", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
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
          <p>“Alexa, tell Receipts to link code {code}.”</p></section>
          <p class="meta">Single-use. Expires at {expires_at}. After Alexa confirms the connection,
          anything captured through this Alexa identity resolves to the selected ledger.</p>
          <nav class="actions" aria-label="Pairing actions">
            <a class="action" href="/alexa/pair"><strong>Issue another code</strong><small>Invalidate nothing; create a fresh ten-minute pairing exhibit.</small></a>
            <a class="action" href="/"><strong>Return to the ledger</strong><small>Back to source connections and watcher status.</small></a>
          </nav>
        """,
    )


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


@app.get("/status", dependencies=[Depends(require_admin)])
def watcher_status() -> dict:
    return {
        "poll_interval_seconds": settings.poll_interval_seconds,
        "connections": store.public_status(),
    }
