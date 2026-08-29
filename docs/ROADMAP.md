# Build sequence

## M0 — Bones and local vertical slice

- [x] Define the product boundary and non-goals.
- [x] Capture one commitment through one Strands tool.
- [x] Validate and persist exact domain records.
- [x] Review pending records with a deterministic interruption policy.
- [x] Cover due, future, ambiguous, autonomous, and actor-isolation cases.

## M1 — AWS end-to-end

- [ ] Finish AWS account and CLI configuration.
- [ ] Provision the DynamoDB table and managed access policy.
- [ ] Add the table environment variable and policy ARN to AgentCore config.
- [ ] Run `agentcore validate` and `agentcore deploy --dry-run`.
- [ ] Deploy the Strands agent to AgentCore Runtime.
- [ ] Capture the dentist promise and verify its DynamoDB record.
- [ ] Invoke deterministic review before and after the due time.

Definition of done: the same commitment survives a runtime restart and appears only when the test clock makes it actionable.

## M1.5 — Alexa voice front door

- [x] Add a thin Alexa Lambda adapter over the AgentCore API.
- [x] Add a Custom Skill interaction model for capture and review.
- [x] Bind the Lambda trigger to one Alexa Skill ID.
- [x] Pass a pseudonymous Alexa actor through AgentCore runtime identity.
- [ ] Deploy the adapter and paste its Lambda ARN into the Alexa endpoint.
- [ ] Run capture and quiet-review tests in the Alexa simulator.

## M2 — Quiet scheduled review

- [ ] Trigger review on a schedule with EventBridge.
- [ ] Add one attention delivery adapter.
- [ ] Emit no notification when review returns no items.
- [ ] Deduplicate repeated attention for the same state.
- [ ] Add CloudWatch traces and a small evaluation set for false captures and needless interruptions.

## M3 — Safe assistance and approval gates

- [ ] Model safe preparation separately from external action.
- [ ] Allow research, organization, and drafting without interrupting.
- [ ] Require explicit approval before sending, buying, booking, paying, or deciding.
- [ ] Record every requested and granted approval.

## Demo spine

1. Say: “I promised Mom I’d call the dentist tomorrow.”
2. Show the normalized DynamoDB record.
3. Review before the deadline: no interruption.
4. Review after the deadline: one human attention item.
5. Show that Promise Pocket did not call, send, book, or pay on the user’s behalf.
