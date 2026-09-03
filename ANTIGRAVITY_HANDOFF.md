# Receipts: Antigravity handoff

This is the continuation point for **Receipts**, whose repository and internal
package names still say `PromisePocket` / `promise_pocket` in several places.
The product promise is: capture commitments, keep an exact ledger, and surface
only moments that require a person to clarify, act, approve, send, or pay.

## Find the project

- Local checkout: `C:\Users\r2o\Documents\Codex\2026-08-31\ha\work\PromisePocket`
- GitHub: `https://github.com/TONZHub/PromisePocket.git`
- Current branch at handoff: `fix/alexa-natural-utterances`
- Current commit: `db2bb36` (`Checkpoint Receipts mobile pairing API`)
- Working tree was clean when this handoff was written on 2026-09-02.

Before changing anything, confirm whether this branch is meant to be merged or
whether work should continue on a new branch. Do not assume `main` contains the
mobile-pairing checkpoint.

## What exists now

- Python domain core in `app/PromisePocket/promise_pocket/`: exact v2 ledger,
  ingestion, deterministic review, reconciliation, pairing, storage, and an
  AgentCore/Strands entry point.
- Render watcher in `watcher/`: Gmail OAuth/read-only sent-mail scanning,
  encrypted tokens, SQLite persistence, AgentCore client, admin routes, Alexa
  pairing, mobile pairing/API routes, and proactive Alexa delivery support.
- Alexa adapter in `alexa/`: capture/review intents, state-specific yes/no
  authority gates, six-digit OAuth-free pairing, tests, and interaction model.
- Android app in `app/`: Room-backed local UI plus recently added remote mobile
  session/client classes. A second older/minimal Android tree also exists at
  `android-app/`; establish which one is canonical before editing both.
- Infrastructure in `infra/`, Render configuration in `render.yaml`, and CI in
  `.github/workflows/ci.yml`.

Recent milestones are visible in commits `fe18bb3` (Alexa proactive overdue
notifications) and `db2bb36` (mobile pairing API). These landed after parts of
`docs/ROADMAP.md` and `docs/POCKET_PROMISE_V2.md` were written, so their unchecked
or “not built yet” lists are not fully authoritative.

## Highest-value next slice

Finish one real mobile vertical slice against the shared v2 ledger:

1. Decide the canonical Android source tree (`app/` is the one CI currently
   tests with `:app:testDebugUnitTest`).
2. Wire the new `ReceiptsMobileClient` and `MobileSessionStore` into the
   ViewModel/repository and UI.
3. Complete the `/mobile/pair` -> `/api/mobile/v1/link` flow using a short-lived,
   single-use code; store only the returned mobile session token on-device.
4. Load commitments through `/api/mobile/v1/commitments`, capture through
   `/api/mobile/v1/capture`, and expose only the permitted explicit actions via
   `/api/mobile/v1/commitments/{commitment_id}/{action}`.
5. Add Android tests for pairing, unauthorized/expired sessions, list/capture,
   and candidate confirmation. Then exercise one physical-device path.

Preserve the core authority rule: a model may propose a `CANDIDATE`, but only an
explicit human action may promote it to `ACTIVE` or mark it `DONE`. Do not add a
shortcut that lets prompt text, Alexa yes/no without signed session context, or
the mobile client choose another actor/ledger.

## Known gaps and sharp edges

- AWS/AgentCore and DynamoDB deployment still need a real end-to-end check.
- Render secrets and Google OAuth testing status must be configured externally.
  Never commit them. See `.env.example`, `render.yaml`, and
  `docs/POCKET_PROMISE_V2.md` for variable names.
- Production unlinking and multi-user pairing management are unfinished.
- Android candidate-confirmation UI and mobile notifications are unfinished.
- Evidence reconciliation against later Gmail/Drive activity is unfinished.
- Public Google OAuth verification is unfinished; testing-mode refresh tokens
  can expire after seven days.
- `app/src/main/.../GeminiService.kt` still contains a placeholder backend URL;
  verify whether that older direct-Gemini path should be removed, isolated, or
  updated rather than silently shipping it.
- `metadata.json`, package names, docs, Render service names, and Java/Kotlin
  namespaces still contain Promise Pocket naming. User-facing copy is Receipts;
  rename internals only as a deliberate migration.

## Verification

CI is the reference because this machine did not expose a Python launcher when
the handoff was written.

```bash
# Domain
cd app/PromisePocket
python -m pip install .
python -m unittest discover -s tests -v

# Watcher
cd ../../watcher
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v

# Alexa (from repo root)
PYTHONPATH=. python -m unittest discover -s alexa/tests -v

# Android (JDK 21 / Gradle 8.10.2)
gradle :app:testDebugUnitTest :app:assembleDebug --stacktrace
```

After local tests, verify the deployed spine manually:

1. `/healthz` is healthy.
2. Create a mobile or Alexa pairing code and prove it is single-use and expires.
3. Capture a plain-language promise into the intended ledger.
4. Confirm it explicitly; review before due time should stay quiet.
5. Review after due time should produce exactly one attention item.
6. Confirm no call, message, booking, payment, or completion claim occurs without
   explicit human approval.

## Read next

1. `README.md` for the product overview and pairing demo.
2. `docs/POCKET_PROMISE_V2.md` for the Gmail -> candidate -> active -> done flow.
3. `docs/ARCHITECTURE.md` for trust boundaries and identity rules.
4. `docs/ROADMAP.md` for the milestone map, interpreted alongside recent commits.
5. Commit `db2bb36` and its tests for the newest mobile API contract.

If time is tight, finish and demonstrate the shared-ledger mobile flow before
attempting broad renames or additional integrations. The differentiator is the
quiet, deterministic consent boundary—not the number of surfaces.
