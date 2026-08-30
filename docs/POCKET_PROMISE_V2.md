# Pocket Promise v2 — Hackathon Runbook

Pocket Promise v2 watches user-authorized digital sources for commitments the
user made, proposes them as candidates, keeps confirmed promises in a durable
ledger, and later reconciles evidence of follow-through.

## Current vertical slice

```text
Gmail SENT mail
    ↓
Render watcher (10-minute poll)
    ↓
Nova / AgentCore Arbiter
    ↓
CANDIDATE
    ↓ explicit user confirmation
ACTIVE
    ↓
LIKELY_DONE / OVERDUE
    ↓ user confirms
DONE
```

The model may create a `CANDIDATE`. It may never silently promote that candidate
to `ACTIVE` or claim completion as fact.

## Google Cloud setup

1. Create or select a Google Cloud project.
2. Enable **Gmail API**.
3. Configure the OAuth consent screen as **External / Testing** for the hackathon.
4. Add the demo Google account as a test user.
5. Add only this Gmail scope:
   `https://www.googleapis.com/auth/gmail.readonly`
6. Create an OAuth **Web application** client.
7. Add the Render callback as an authorized redirect URI:
   `https://<your-render-service>.onrender.com/auth/google/callback`
8. Put the client ID and client secret into Render environment variables.

Google's Testing publishing status limits the app to configured test users and
non-basic authorizations expire after seven days, including offline refresh
tokens. That is acceptable for the hackathon demo but is not a production
account-linking strategy.

## Render setup

The root `render.yaml` defines one always-on web service with a 1 GB persistent
disk. The service runs a single watcher loop every ten minutes; SQLite lives on
`/var/data` so OAuth connection state survives deploys/restarts.

Required secret environment variables:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `TOKEN_ENCRYPTION_KEY`
- `DEMO_ACTOR_ID`
- `WATCHER_ADMIN_KEY`
- `AGENT_RUNTIME_ARN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Generate a Fernet key locally:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate an admin key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

For the first watcher smoke test, `DEMO_ACTOR_ID` may be a controlled demo
identity. Before the cross-device demo, replace it with the canonical actor ID
used by the Android/Alexa identity bridge.

The AWS credential used by Render should be a dedicated least-privilege identity
that can invoke only the deployed AgentCore runtime. Do not put an administrator
AWS key on Render.

## First end-to-end test

1. Deploy the Render service.
2. Verify `/healthz` returns `ok: true`.
3. Open `/auth/google/start` and authorize the test Gmail account.
4. Send an email such as:
   `I'll send you the final mockups by Tuesday evening.`
5. Either wait for the watcher interval or POST `/scan-now` with the
   `X-Watcher-Admin-Key` header.
6. Inspect the v2 ledger. Expected state: `candidate`.
7. Confirm the candidate through the v2 API/app. Expected state: `active`.

## Data minimization in this slice

- The watcher reads only `in:sent` Gmail results.
- Full message content is sent transiently to the Arbiter but is not stored in
  the watcher database.
- The ledger stores the exact supporting excerpt selected by the Arbiter rather
  than the full email/thread.
- Google refresh tokens are encrypted before being written to SQLite.
- OAuth state tokens are single-use and expire after ten minutes.

## Not built yet

- Production user/account identity bridging.
- Android candidate-confirmation UI and push notifications.
- Evidence reconciliation against later mail/Drive activity.
- Alexa v2 review/enforcement flow.
- Public Google OAuth verification.
