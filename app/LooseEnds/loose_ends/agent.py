"""Strands agent and its single v0 tool."""

from __future__ import annotations

from datetime import datetime
from collections.abc import Callable
from typing import Any

from strands import Agent, ToolContext, tool

from .service import CommitmentService


SYSTEM_PROMPT = """
You are Loose Ends, a quiet memory for real commitments.

Your job in this version is narrow:
1. Notice when the user expresses a promise, obligation, deadline, or follow-up.
2. Normalize it without changing its meaning.
3. Call capture_commitment exactly once for each distinct commitment.
4. Confirm what was captured in one calm sentence.

Rules:
- Do not capture wishes, brainstorming, or casual possibilities as commitments.
- Never invent a person, deadline, or missing fact.
- Convert relative times to an absolute ISO-8601 datetime with a UTC offset using
  the invocation time and user timezone supplied in the message.
- If timing or another material detail is missing, keep due_at null and put one
  concise question in missing_information.
- human_action_required is true when the user must personally act, decide,
  approve, send, pay, book, or communicate.
- Loose Ends may eventually research, organize, or draft safely, but this version
  performs no external side effects.
- The actor identity comes from trusted invocation state. Never ask for it and
  never place it in tool arguments.
- If there is no commitment, do not call the tool. Say so briefly.
""".strip()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("due_at must include a UTC offset")
    return parsed


def make_capture_tool(
    service: CommitmentService,
    on_capture: Callable[[str], None] | None = None,
):
    @tool(context=True)
    def capture_commitment(
        summary: str,
        raw_text: str,
        human_action_required: bool,
        tool_context: ToolContext,
        due_at: str | None = None,
        people: list[str] | None = None,
        missing_information: list[str] | None = None,
    ) -> dict[str, Any]:
        """Store one commitment extracted from the user's own words.

        Args:
            summary: Short, faithful description of the commitment.
            raw_text: Exact user wording that established the commitment.
            human_action_required: Whether the person must personally act or approve.
            due_at: Absolute ISO-8601 deadline with UTC offset, or null if unknown.
            people: People explicitly involved in the commitment.
            missing_information: Concise questions for materially missing details.
            tool_context: Strands invocation context; supplied by the framework.
        """

        actor_id = tool_context.invocation_state.get("actor_id")
        if not isinstance(actor_id, str) or not actor_id:
            raise ValueError("trusted actor_id is missing from invocation state")

        commitment = service.capture(
            actor_id=actor_id,
            summary=summary,
            raw_text=raw_text,
            due_at=_parse_optional_datetime(due_at),
            people=people or [],
            human_action_required=human_action_required,
            missing_information=missing_information or [],
        )

        if on_capture is not None:
            on_capture(commitment.commitment_id)

        captured_ids = tool_context.invocation_state.setdefault(
            "captured_commitment_ids", []
        )
        captured_ids.append(commitment.commitment_id)
        return commitment.model_dump(mode="json")

    return capture_commitment


def build_agent(
    service: CommitmentService,
    model_id: str,
    on_capture: Callable[[str], None] | None = None,
) -> Agent:
    return Agent(
        model=model_id,
        tools=[make_capture_tool(service, on_capture=on_capture)],
        system_prompt=SYSTEM_PROMPT,
        callback_handler=None,
    )
