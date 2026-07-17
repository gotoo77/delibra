# Decision Record Repeated Fixture Pilot 0002

## Status

Pilot evidence note. Not an accepted benchmark result, model qualification,
architecture decision, validator requirement, or approval to implement a batch
runner.

This note records the second manual pilot for
[Decision Record Repeated Fixture Study](decision-record-repeated-fixture-study.md).
It tests the recommendation from
[Pilot 0001](decision-record-repeated-fixture-pilot-0001.md): before comparing
resources, qualify whether the protocol produces the object being evaluated.

Raw run and trace outputs were kept outside the repository.

## Experiment Definition

Experiment:

- `decision-record-repeated-fixture-study`

Fixture:

- `structurally_valid_but_not_accepted`

Protocol:

- `decision_record_structured_review@0.1.0`
- source: [decision-record-structured-review-protocol.yaml](decision-record-structured-review-protocol.yaml)

Resource:

- provider: `ollama`
- model label: `qwen3:4b`
- local endpoint: `http://localhost:11434`

Repetitions:

- 3

Run output location:

- `/tmp/delibra-decision-record-pilot/structured-protocol/qwen3-4b/`

The raw output path is local and non-durable. It is recorded here only to make
the pilot inspectable during the current session.

## Protocol Change From Pilot 0001

Pilot 0001 used `decision_review@0.1.0`, which produces a final synthesis. The
input requested a `decision_record`, but the protocol itself did not make that
object the final artifact target.

Pilot 0002 uses an experimental protocol whose final output is
`decision_record` and whose final instruction requires one JSON object with the
local contract fields.

This is a protocol/instrument change, not a resource change.

## Evidence Dossier

```yaml
experiment_id: decision-record-repeated-fixture-study
pilot_id: pilot-0002
status: draft
fixture:
  id: structurally_valid_but_not_accepted
  expected_structural_result: valid
  expected_acceptance_implication: pending_review_or_rejected
resource:
  provider: ollama
  model_label: qwen3:4b
protocol:
  id: decision_record_structured_review
  version: 0.1.0
runs:
  total: 3
  completed: 3
  failed: 0
artifacts:
  per_run: 4
  trace_events_per_run: 24
durations_seconds:
  run_1: 190.769
  run_2: 188.807
  run_3: 199.347
measurements:
  exact_json_decision_record_found: 3
  extraction_failure_count: 0
  structural_contract_directly_evaluable: 3
  structural_valid_count: 3
  status_pending_review_count: 3
  missing_required_fields_count: 0
  extra_fields_count: 0
oracle:
  expected_fixture_classification_directly_tested: true
  expected_fixture_classification_matched: 3
human_review:
  required: true
  performed: partial
limitations:
  - one fixture only
  - one local resource only
  - validation used a scratch script, not production code
  - local model version is only exposed as qwen3:4b
```

## Measurements

All three runs completed successfully and produced the expected protocol shape:

| Run | Duration seconds | Artifacts | Trace events | Final artifact | JSON parse | Structural result | Status |
|---|---:|---:|---:|---|---|---|---|
| 1 | 190.769 | 4 | 24 | `artifact_0004` | ok | valid | `pending_review` |
| 2 | 188.807 | 4 | 24 | `artifact_0004` | ok | valid | `pending_review` |
| 3 | 199.347 | 4 | 24 | `artifact_0004` | ok | valid | `pending_review` |

Mechanical comparison with Pilot 0001:

| Pilot | Protocol | Runs | Artifacts/run | Trace events/run | Durations seconds | Directly evaluable records |
|---|---|---:|---:|---:|---|---:|
| 0001 | `decision_review@0.1.0` | 3 | 7 | 38 | 226.092, 206.896, 192.268 | 0/3 |
| 0002 | `decision_record_structured_review@0.1.0` | 3 | 4 | 24 | 190.769, 188.807, 199.347 | 3/3 |

The structured protocol reduced artifact count and trace events, but the run
duration remained near three minutes per repetition with `qwen3:4b`.

## Structural Evaluation

A scratch validation script checked the final artifact content for:

- valid JSON parsing;
- exactly the seven local contract fields;
- allowed `status`;
- non-empty `decision`;
- non-empty `options_considered`;
- non-empty `reasons`;
- non-empty `consequences`;
- list-valued `uncertainties`;
- list-valued `pending_conditions`.

Result:

| Run | Missing fields | Extra fields | Structural result |
|---|---|---|
| 1 | none | none | valid |
| 2 | none | none | valid |
| 3 | none | none | valid |

## Status Preservation Review

The fixture expected a structurally valid but not accepted decision.

All three final records used:

```text
status = pending_review
```

All three final records included non-empty pending conditions for security
review and support policy approval.

Interpretation:

- The protocol variant produced records that were directly structurally
  evaluable.
- The expected non-accepted status was preserved in all three repetitions.
- Under these pilot conditions, the previous extraction failure appears to have
  been primarily an instrument/protocol problem rather than evidence that the
  resource cannot produce the target structure.

## Observations

### Observation 1

Under Pilot 0002 conditions, evidence supports that changing the protocol target
from final synthesis to explicit `decision_record` production changed direct
structural evaluability from `0/3` to `3/3` with the same fixture and resource.

Limitations:

- one fixture only;
- one resource only;
- the protocol also reduced step count, so the change is not isolated to final
  instruction wording.

### Observation 2

Under Pilot 0002 conditions, `ollama/qwen3:4b` produced structurally valid
`decision_record` JSON in all three repetitions when the protocol explicitly
made that object the final target.

Limitations:

- this is not a global resource qualification;
- it does not prove decision quality;
- it does not test invalid fixtures;
- it does not test another resource.

### Observation 3

The strongest result of Pilot 0001 and Pilot 0002 together is methodological:

> Before comparing cognitive resources, verify that the protocol reliably
> produces the object submitted to evaluation.

This is an evaluation-readiness precondition, not a new production abstraction.

### Observation 4

Pilot 0002 also exposes a second evaluation-readiness precondition:

> A resource comparison is meaningful only after both the production instrument
> and the measurement instrument have been qualified for the target object.

The production instrument is the Delibra protocol. The measurement instrument is
the extraction or validation procedure. The cognitive resource should not be the
first object blamed when either instrument is unqualified.

In this pilot, the first mechanical validation attempt failed because of an
analysis-script quoting error. The script was corrected before interpreting the
experiment. That incident did not affect the generated artifacts, but it showed
that the measurement instrument also requires qualification.

## Critical Review

What the evidence supports:

- Protocol/instrument qualification matters before resource comparison.
- The same resource and fixture moved from extraction failure to direct
  structural evaluability when the protocol was changed.
- `Evidence` remained useful as a layer between raw runs and observations.
- The experimental loop generated a negative result, a protocol change, and a
  comparative pilot without implementing a batch runner.
- The current structured protocol behaves as a producer or normalizer of a
  `decision_record`, not as a classifier of invalid records.

What remains indeterminate:

- Whether the structured protocol handles invalid fixtures correctly.
- Whether another resource would perform similarly.
- Whether the output remains valid under longer or more ambiguous inputs.
- Whether a deterministic validator should exist, and where it would belong.
- Whether the shorter protocol loses review quality that matters for other
  decision-review uses.
- Whether the next experiment should evaluate, repair, normalize, or preserve
  invalid source records.

Concepts that proved useful:

- `evidence`;
- `structural_evaluation`;
- `task_oracle_evaluation`;
- `resource x protocol interaction`;
- `evaluation readiness`;
- separation between protocol qualification and resource qualification;
- separation between production instrument, measurement instrument, and
  cognitive resource.

Concepts still not exercised:

- `KnowledgeCandidate`;
- `Replication`;
- LLM judges;
- invalid fixture evaluation;
- multi-resource comparison;
- adaptive routing or escalation.

## Next Step

Do not compare resources yet.

Do not run the remaining five fixtures yet. The structured protocol now appears
to be a producer or normalizer of valid `decision_record` objects. Several
remaining fixtures are intentionally invalid. If they are submitted to this
protocol, a valid output could mean the protocol repaired the input, not that
the fixture oracle was wrong.

Before extending fixture coverage, define the transformation semantics of the
next instrument:

| Instrument role | Input expectation | Output expectation | Suitable next question |
|---|---|---|---|
| Generator | decision scenario | valid `decision_record` | Can the resource produce the contract from a scenario? |
| Normalizer | incomplete or messy decision material | repaired valid `decision_record` | Can the resource repair while preserving source intent? |
| Classifier | existing candidate record | classification and failure codes | Can the resource or evaluator identify invalidity without repair? |
| Validator | existing candidate record | deterministic pass/fail/warnings | Can local rules classify the record reproducibly? |
| Preservation instrument | invalid fixture description | representation preserving invalidity | Can the system avoid silently repairing the test case? |

Recommended next step:

1. Decide whether the next experiment is about generation, normalization,
   classification, validation, or preservation.
2. Align fixture inputs and oracle expectations with that instrument role.
3. Only then run additional fixtures.
4. Only after that, decide whether a reusable validator or batch helper is
   justified.

This keeps the next experiment focused on transformation semantics and
evaluation readiness rather than model ranking.
