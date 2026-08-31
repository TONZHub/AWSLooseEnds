"""Claude/Strands Arbiter for Pocket Promise v2.

The model may *propose* candidate commitments from one outgoing source message.
It never confirms, completes, cancels, or otherwise mutates commitment state.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from strands import Agent, ToolContext, tool

from .ingest_v2 import CandidateIngestor, PromiseExtraction, SourceMessage
from .ledger_v2 import PromiseLedger
from .time_resolution import resolve_due_at


ARBITER_PROMPT = """
You are the Pocket Promise Arbiter.

You receive one message written and sent by the user. Your only job is to decide
whether the user undertook a future obligation in that message.

A commitment means the user has taken responsibility for a future action,
deliverable, decision, payment, booking, communication, or follow-up.

Call propose_promise_candidate only when the outgoing message contains a real
commitment. Do not call it for:
- wishes, hopes, brainstorming, or possibilities;
- questions or requests directed at somebody else;
- promises made by another person quoted in the message;
- actions the user says are already complete;
- vague social language with no action the user owns.

When you do call the tool:
- deliverable must be a short faithful description of what the user undertook;
- supporting_text must be an exact excerpt from the user's message that proves
  the commitment, not a paraphrase;
- people may include only explicitly named people or exact addresses present in
  the message. Never emit generic labels such as user, sender, recipient, me, or you;
- do not calculate, normalize, or invent a deadline yourself;
- time_phrase must be the exact timing words from the user's message, such as
  "tomorrow by 3 PM" or "Tuesday at noon". Use null when no timing words exist;
- confidence measures confidence that a genuine user-owned commitment exists;
- evidence_hint should briefly describe what later digital evidence might suggest
  fulfillment, without claiming that fulfillment has happened;
- reason should briefly explain why the language is or is not a commitment.

If there is no commitment, do not call the tool. Respond briefly that no candidate
was proposed. A model judgment is never user confirmation.
""".strip()


def make_candidate_tool(
    ingestor: CandidateIngestor,
    on_candidate: Callable[[str], None] | None = None,
):
    @tool(context=True)
    def propose_promise_candidate(
        deliverable: str,
        supporting_text: str,
        confidence: float,
        reason: str,
        tool_context: ToolContext,
        time_phrase: str | None = None,
        people: list[str] | None = None,
        evidence_hint: str | None = None,
    ) -> dict[str, Any]:
        """Propose one user-owned future obligation found in an outgoing message.

        Args:
            deliverable: Short faithful description of the promised action.
            supporting_text: Exact source excerpt proving the commitment.
            confidence: Confidence from 0.0 to 1.0 that this is a commitment.
            reason: Brief explanation for the judgment.
            time_phrase: Exact timing words from the source message, or null.
            people: Explicitly named people or addresses involved in the commitment.
            evidence_hint: Later evidence that might suggest fulfillment.
            tool_context: Strands invocation context; supplied by the framework.
        """

        actor_id = tool_context.invocation_state.get("actor_id")
        raw_message = tool_context.invocation_state.get("source_message")
        timezone_name = tool_context.invocation_state.get("timezone_name")
        if not isinstance(actor_id, str) or not actor_id:
            raise ValueError("trusted actor_id is missing from invocation state")
        if not isinstance(timezone_name, str) or not timezone_name:
            raise ValueError("trusted timezone_name is missing from invocation state")
        message = SourceMessage.model_validate(raw_message)

        extraction = PromiseExtraction(
            is_commitment=True,
            deliverable=deliverable,
            people=people or [],
            due_at=resolve_due_at(
                time_phrase=time_phrase,
                occurred_at=message.occurred_at,
                timezone_name=timezone_name,
            ),
            confidence=confidence,
            supporting_text=supporting_text,
            evidence_hint=evidence_hint,
            reason=reason,
        )
        candidate = ingestor.apply(
            actor_id=actor_id,
            message=message,
            extraction=extraction,
        )
        if candidate is None:
            return {
                "stored": False,
                "reason": "candidate did not pass deterministic ingestion guardrails",
            }
        if on_candidate is not None:
            on_candidate(candidate.commitment_id)
        return {
            "stored": True,
            "candidate": candidate.model_dump(mode="json"),
        }

    return propose_promise_candidate


def build_arbiter_agent(
    ledger: PromiseLedger,
    model_id: str,
    on_candidate: Callable[[str], None] | None = None,
    minimum_confidence: float = 0.70,
) -> Agent:
    ingestor = CandidateIngestor(
        ledger,
        minimum_confidence=minimum_confidence,
    )
    return Agent(
        model=model_id,
        tools=[make_candidate_tool(ingestor, on_candidate=on_candidate)],
        system_prompt=ARBITER_PROMPT,
        callback_handler=None,
    )


def arbitrate_outgoing_message(
    agent: Agent,
    *,
    actor_id: str,
    message: SourceMessage,
    timezone_name: str,
) -> str:
    """Run one source message through the Arbiter with trusted source metadata."""

    result = agent(
        "Analyze this outgoing message for a user-owned future commitment.\n"
        f"Message timestamp: {message.occurred_at.isoformat()}\n"
        f"User timezone: {timezone_name}\n"
        f"Subject: {message.subject or '(none)'}\n"
        f"Body:\n{message.body}",
        actor_id=actor_id,
        source_message=message.model_dump(mode="json"),
        timezone_name=timezone_name,
    )
    return result.message
