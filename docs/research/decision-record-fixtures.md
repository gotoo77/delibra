# Decision Record Representative Fixtures

## Status

Experimental fixture definition. No validator or accepted schema is defined yet.

## Purpose

Define the distinctions the `decision_record` domain must support before
designing its local contract or validation implementation.

These fixtures describe intended cases, not final JSON examples. They should
guide the next contract discussion without prematurely fixing the representation.

## Fixture: valid_structural_decision_record

Expected classification: structurally valid.

Properties:

- states an explicit decision;
- identifies considered options;
- records reasons for the chosen option;
- records expected consequences;
- records material uncertainties;
- declares a decision status.

This fixture does not prove that the decision should be accepted.

## Fixture: missing_required_fields

Expected classification: structurally invalid.

Properties:

- omits one or more elements required for a usable decision record;
- may otherwise contain plausible decision-oriented prose.

The fixture should reveal which omissions are deterministic contract
violations.

## Fixture: no_explicit_decision

Expected classification: structurally invalid.

Properties:

- contains context, analysis, alternatives, or recommendations;
- does not state what was actually decided.

This fixture distinguishes a decision record from an analysis document.

## Fixture: options_without_reasons

Expected classification: structurally invalid or structurally incomplete.

Properties:

- states a decision;
- lists alternatives;
- provides no reasons connecting the evidence and alternatives to the decision.

This fixture tests whether reasons belong to the structural contract rather
than to later qualitative review.

## Fixture: structurally_valid_but_not_accepted

Expected classification:

- structurally valid;
- not accepted.

Properties:

- contains all required decision-record elements;
- explicitly indicates that approval, policy review, human judgment, or another
  external condition remains outstanding;
- must not be promoted merely because structural validation succeeds.

This fixture exists to test the distinction:

```text
structurally_valid != accepted
```

## Fixture: contradictory_status

Expected classification: structurally invalid or structurally inconsistent.

Properties:

- contains the required decision-record elements;
- states or implies that the decision is approved;
- also states that mandatory approval, policy review, or human judgment remains
  outstanding.

This fixture tests a deterministic consistency rule that is not just field
presence and does not require judging whether the decision is good.

## Questions Exposed By The Fixtures

- Which fields are genuinely required?
- Are reasons mandatory structure or qualitative content?
- Are uncertainties required, optional, or status-dependent?
- Is status part of the record or part of a separate acceptance process?
- Can validation produce warnings in addition to errors?
- Who or what determines acceptance?
- Does the structurally valid fixture need an explicit `accepted` field at all?

## Non-Goals

- no `decision_record` validator;
- no final JSON schema;
- no generic validation abstraction;
- no automatic acceptance policy;
- no claim that decision quality is deterministically measurable.

## Completion Criterion

This fixture definition is sufficient when a future local contract can be
evaluated against these cases while the exact schema remains open.
