# Promise Pocket (Android)

**A quiet place for the things you mean to do.**

Promise Pocket captures commitments in ordinary language, keeps an exact local ledger of them in Room, and interrupts only when a person genuinely needs to act, clarify, decide, approve, send, or pay.

> “I promised Mom I’d call the dentist tomorrow at noon.”

That becomes a structured loose end, waits without nagging, and surfaces with zero noise when it actually needs you.

---

## Features

- **Natural Promise Capture**: Speak or type ordinary commitments (e.g. *"I promised Mom I'd call the dentist tomorrow at noon"*).
- **Fail-Closed Timing Clarification**: If a date is mentioned without an explicit clock time, the deterministic policy flags it for precise clarification rather than hallucinating a deadline.
- **Deterministic Review Policy**: Pure, zero-model deterministic evaluation of active commitments against the clock, categorizing items by:
  - **Needs Clarification**: Commitments with missing details or unanchored timing.
  - **Due Now**: Actionable items whose exact deadline has arrived.
  - **Blocked**: Promises blocked by an external reason.
- **Autonomous Safe Work vs Human Action**: Distinguishes between work that requires direct human intervention (calling, paying, deciding) versus quiet background agent preparation.
- **Offline-First Room Database**: Structured persistence with `CommitmentEntity` and isolation between the local ledger and an optional signed-in Amazon identity.
- **Gemini API Integration**: Uses `gemini-3.5-flash` with structured JSON output for parsing when configured, backed by an intelligent local heuristic parser.
- **Polished Material 3 UI**: Soft Sand & Slate palette, responsive status chips, quick capture bar, and custom adaptive app launcher icons.
- **Login with Amazon**: Optional Amazon identity in the Android app, with the same pseudonymous actor contract used by account-linked Alexa requests.

---

## Repository Structure

```text
app/
  src/main/
    java/com/example/promisepocket/
      data/
        local/        Room Database, DAO, Converters
        model/        CommitmentEntity, AttentionItem, Status enums
        remote/       Gemini REST API & DTO models
        repository/   CommitmentRepository
      domain/         CommitmentService (Review & Capture logic), PromiseParser, TimeUtils
      ui/
        components/   AttentionBanner, CommitmentCard, ClarificationDialog, QuickCaptureBar
        screens/      MainScreen
        theme/        Color, Typography, Theme
        viewmodel/    PromisePocketViewModel
      MainActivity.kt
    res/              Vector drawables, Adaptive Icons, Strings
  src/test/           JUnit domain & policy unit tests
```

---

## Running the Unit Tests

Execute unit tests directly with Gradle:

```bash
gradle :app:testDebugUnitTest
```

## Configure Login with Amazon

The code and official Login with Amazon 3.1.6 SDK are included. A working build
still needs an API key tied to the exact Android package and signing certificate:

1. In the Login with Amazon console, create or select the **Promise Pocket**
   security profile and add Android settings.
2. Register package `com.aistudio.promisepocket.kzpxtq` with both the MD5 and
   SHA-256 fingerprints from the keystore used to sign the APK.
3. Copy `app/src/main/assets/api_key.txt.example` to
   `app/src/main/assets/api_key.txt`, then replace its contents with the generated
   Android API key. The real file is gitignored.
4. Use the same security profile for Alexa account linking. Configure an
   authorization-code grant with:
   - Authorization URI: `https://www.amazon.com/ap/oa`
   - Access Token URI: `https://api.amazon.com/auth/o2/token`
   - Scope: `profile:user_id`
   - Client ID and secret: the Login with Amazon security profile credentials
5. Redeploy `infra/alexa-template.yaml` with that client ID as
   `LoginWithAmazonClientId` so Lambda verifies each linked token before using it.

Unlinked Alexa users keep the existing skill-scoped identity. Linked Alexa
requests and Android sign-in hash the Login with Amazon `user_id` into the same
`amazon-…` actor ID; the raw Amazon identifier and access token are never stored
in the commitment ledger.

Amazon sign-in establishes shared identity. The current Android ledger remains
offline-first in Room until the cloud sync milestone is implemented.
