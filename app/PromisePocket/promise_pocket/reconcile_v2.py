"""Evidence reconciliation for Pocket Promise v2.

The model may propose evidence that a later outgoing source message appears to
fulfill an already-active promise. Deterministic guardrails decide whether that
evidence is allowed to move the promise to ``likely_done``. The model never
marks a promise factually done.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from strands import Agent, ToolContext, tool

from .ingest_v2 import SourceMessage
from .ledger_v2 import PromiseEvidence, PromiseLedger, PromiseRecord, PromiseState


EVIDENCE_PROMPT = """
You are the Pocket Promise evidence reconciler.

You receive one later outgoing message written and sent by the user, plus the
user's currently ACTIVE or OVERDUE promises. Decide whether the new message is
credible evidence that one or more of those promises was likely fulfilled.

Call propose_promise_evidence only when the outgoing message itself contains
clear evidence of fulfillment. Examples include actually sending or delivering
the promised item, explicitly stating that the promised action was just
completed, or a concrete handoff message such as "Here's the revised document."

Do not call the tool for:
- another promise or plan to do the work later;
- reminders, intentions, or repeated deadline language;
- vague progress updates such as "working on it";
- messages that only share keywords with the promise;
- evidence for a promise not included in the supplied active-promise list;
- the original message that created the promise.

When you do call the tool:
- commitment_id must exactly match one supplied active promise;
- evidence_kind should be a short category such as outgoing_delivery,
  completion_statement, or handoff_message;
- supporting_text must be an exact excerpt from the new outgoing message;
- summary must briefly explain what the new message appears to prove;
- confidence is confidence that this message is evidence of fulfillment;
- reason should briefly explain the match.

A successful tool call only means LIKELY_DONE. Never claim the promise is
factually DONE; final completion remains a user-authorized transition.
""".strip()


class EvidenceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    commitment_id: str = Field(min_length=1)
    evidence_kind: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=1000)
    supporting_text: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=1000)


class EvidenceIngestor:
    """Apply evidence proposals without letting the model declare completion."""

    def __init__(self, ledger: PromiseLedger, minimum_confidence: float = 0.80) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self._ledger = ledger
        self._minimum_confidence = minimum_confidence

    def apply(
        self,
        *,
        actor_id: str,
        message: SourceMessage,
        proposal: EvidenceProposal,
    ) -> PromiseRecord | None:
        if message.direction != "sent":
            return None
        if proposal.confidence < self._minimum_confidence:
            return None
        if proposal.supporting_text not in message.body:
            return None

        record = self._ledger.get(
            actor_id=actor_id,
            commitment_id=proposal.commitment_id,
        )
        if record is None:
            return None
        if record.status not in {PromiseState.ACTIVE, PromiseState.OVERDUE}:
            return None
        if (
            record.source_id
            and record.source == message.source
            and record.source_id == message.source_id
        ):
            return None

        # Source timestamps can precede ingestion by a short polling delay, so
        # allow a small margin while rejecting clearly older messages.
        if message.occurred_at < record.created_at - timedelta(minutes=5):
            return None

        evidence = PromiseEvidence(
            kind=proposal.evidence_kind,
            source=message.source,
            source_id=message.source_id,
            summary=proposal.summary,
            supporting_text=proposal.supporting_text,
            confidence=proposal.confidence,
            observed_at=message.occurred_at,
        )
        return self._ledger.mark_likely_done(
            actor_id=actor_id,
            commitment_id=record.commitment_id,
            evidence=evidence,
        )


def make_evidence_tool(
    ingestor: EvidenceIngestor,
    on_likely_done: Callable[[str], None] | None = None,
):
    @tool(context=True)
    def propose_promise_evidence(
        commitment_id: str,
        evidence_kind: str,
        summary: str,
        supporting_text: str,
        confidence: float,
        reason: str,
        tool_context: ToolContext,
    ) -> dict[str, Any]:
        """Propose evidence that a later outgoing message likely fulfills a promise.

        Args:
            commitment_id: Exact active promise ID supplied in the prompt.
            evidence_kind: Short category describing the evidence.
            summary: Brief description of what the evidence appears to prove.
            supporting_text: Exact excerpt from the new outgoing source message.
            confidence: Confidence from 0.0 to 1.0 that this is fulfillment evidence.
            reason: Brief explanation connecting the evidence to the promise.
            tool_context: Strands invocation context; supplied by the framework.
        """

        actor_id = tool_context.invocation_state.get("actor_id")
        raw_message = tool_context.invocation_state.get("source_message")
        allowed_ids = tool_context.invocation_state.get("active_commitment_ids") or []
        if not isinstance(actor_id, str) or not actor_id:
            raise ValueError("trusted actor_id is missing from invocation state")
        if commitment_id not in allowed_ids:
            return {"stored": False, "reason": "commitment is not active for this reconciliation"}

        message = SourceMessage.model_validate(raw_message)
        proposal = EvidenceProposal(
            commitment_id=commitment_id,
            evidence_kind=evidence_kind,
            summary=summary,
            supporting_text=supporting_text,
            confidence=confidence,
            reason=reason,
        )
        updated = ingestor.apply(
            actor_id=actor_id,
            message=message,
            proposal=proposal,
        )
        if updated is None:
            return {
                "stored": False,
                "reason": "evidence did not pass deterministic reconciliation guardrails",
            }
        if on_likely_done is not None:
            on_likely_done(updated.commitment_id)
        return {
            "stored": True,
            "promise": updated.model_dump(mode="json"),
        }

    return propose_promise_evidence


def build_evidence_agent(
    ledger: PromiseLedger,
    model_id: str,
    on_likely_done: Callable[[str], None] | None = None,
    minimum_confidence: float = 0.80,
) -> Agent:
    ingestor = EvidenceIngestor(
        ledger,
        minimum_confidence=minimum_confidence,
    )
    return Agent(
        model=model_id,
        tools=[make_evidence_tool(ingestor, on_likely_done=on_likely_done)],
        system_prompt=EVIDENCE_PROMPT,
        callback_handler=None,
    )


def reconcile_outgoing_message(
    agent: Agent,
    *,
    actor_id: str,
    message: SourceMessage,
    active_promises: list[PromiseRecord],
) -> str:
    """Run one outgoing message against a bounded set of active promises."""

    promise_context = [
        {
            "commitment_id": record.commitment_id,
            "deliverable": record.deliverable,
            "original_wording": record.raw_text,
            "people": record.people,
            "due_at": record.due_at.isoformat() if record.due_at else None,
            "evidence_hint": record.evidence_hint,
            "status": record.status.value,
        }
        for record in active_promises
    ]
    result = agent(
        "Check this later outgoing message for evidence that it fulfills any active promise.\n"
        f"Active promises:\n{json.dumps(promise_context, ensure_ascii=False)}\n"
        f"New message timestamp: {message.occurred_at.isoformat()}\n"
        f"Subject: {message.subject or '(none)'}\n"
        f"Body:\n{message.body}",
        actor_id=actor_id,
        source_message=message.model_dump(mode="json"),
        active_commitment_ids=[record.commitment_id for record in active_promises],
    )
    return result.message
