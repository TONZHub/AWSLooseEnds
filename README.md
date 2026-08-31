# Receipts (Android)

**A quiet place for the things you mean to do.**

Receipts captures commitments in ordinary language, keeps an exact local ledger of them in Room, and interrupts only when a person genuinely needs to act, clarify, decide, approve, send, or pay.

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
- **Offline-First Room Database**: Structured local persistence with `CommitmentEntity`.
- **Gemini API Integration**: Uses `gemini-3.5-flash` with structured JSON output for parsing when configured, backed by an intelligent local heuristic parser.
- **Polished Material 3 UI**: Soft Sand & Slate palette, responsive status chips, quick capture bar, and custom adaptive app launcher icons.
- **OAuth-Free Alexa Pairing**: A short-lived, single-use six-digit code connects an Alexa device identity to the intended ledger without Login with Amazon.

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

## Pair Alexa without account linking

The watcher can generate a single-use pairing code for its configured demo
ledger:

1. Open the admin-protected watcher route `/alexa/pair`.
2. Say `Alexa, tell Receipts to link code 482731`, replacing the example
   with the displayed six digits.
3. Alexa claims the code through AgentCore and binds its pseudonymous skill user
   identity to that ledger.

Codes expire after ten minutes and can be claimed only once. Login with Amazon,
an OAuth token proxy, and an Amazon profile permission are not required.
