# Decision Record Repeated Fixture Pilot 0001

## Status

Pilot evidence note. Not an accepted benchmark result, model qualification,
architecture decision, validator requirement, or approval to implement a batch
runner.

This note records the first manual pilot for
[Decision Record Repeated Fixture Study](decision-record-repeated-fixture-study.md).
Raw run and trace outputs were kept outside the repository.

## Experiment Definition

Experiment:

- `decision-record-repeated-fixture-study`

Fixture:

- `structurally_valid_but_not_accepted`

Protocol:

- `decision_review@0.1.0`

Resource:

- provider: `ollama`
- model label: `qwen3:4b`
- local endpoint: `http://localhost:11434`

Repetitions:

- 3

Run output location:

- `/tmp/delibra-decision-record-pilot/structurally_valid_but_not_accepted/qwen3-4b/`

The raw output path is local and non-durable. It is recorded here only to make
the pilot inspectable during the current session.

## Input Shape

The input asked the existing `decision_review` preset to review a decision that
is structurally complete but not accepted, because security review and support
policy approval remain pending.

It also asked the final synthesis to include a machine-readable
`decision_record` JSON object with exactly these fields:

- `decision`
- `status`
- `options_considered`
- `reasons`
- `consequences`
- `uncertainties`
- `pending_conditions`

## Evidence Dossier

```yaml
experiment_id: decision-record-repeated-fixture-study
pilot_id: pilot-0001
status: draft
fixture:
  id: structurally_valid_but_not_accepted
  expected_structural_result: valid
  expected_acceptance_implication: pending_review_or_rejected
resource:
  provider: ollama
  model_label: qwen3:4b
runs:
  total: 3
  completed: 3
  failed: 0
artifacts:
  per_run: 7
  trace_events_per_run: 38
durations_seconds:
  run_1: 226.092
  run_2: 206.896
  run_3: 192.268
measurements:
  exact_json_decision_record_found: 0
  extraction_failure_count: 3
  final_artifact_preserved_not_accepted_status: 2
  final_artifact_confused_acceptance_status: 1
  structural_contract_directly_evaluable: 0
oracle:
  expected_fixture_classification_directly_tested: false
  reason: no final artifact produced the requested exact decision_record JSON object
human_review:
  required: true
  performed: partial
limitations:
  - existing protocol produces synthesis, not decision_record
  - extraction was manual and lightweight
  - no deterministic validator exists
  - local model version is only exposed as qwen3:4b
```

## Measurements

All three runs completed successfully and produced the expected Delibra protocol
shape:

| Run | Duration seconds | Artifacts | Trace events | Final artifact |
|---|---:|---:|---:|---|
| 1 | 226.092 | 7 | 38 | `artifact_0007` |
| 2 | 206.896 | 7 | 38 | `artifact_0007` |
| 3 | 192.268 | 7 | 38 | `artifact_0007` |

Mechanical observations:

- `role_reviews` produced three review artifacts in every run.
- `critique_reviews` produced two critique artifacts in every run.
- `final` produced one synthesis artifact in every run.
- The exact provider token usage, cost, and provider-side model version were not
  persisted in durable run or trace records.

## Structural Evaluation

Direct structural evaluation failed for all three repetitions because no final
artifact contained an exact machine-readable `decision_record` JSON object with
the requested fields.

Classification:

| Run | Directly evaluable as `decision_record` | Structural result |
|---|---|---|
| 1 | no | extraction failure |
| 2 | no | extraction failure |
| 3 | no | extraction failure |

This does not prove the model cannot produce a `decision_record`. It shows that
the existing `decision_review@0.1.0` preset plus input-level formatting request
is not a clean enough instrument for direct structural evaluation.

## Status Preservation Review

The fixture expected a structurally valid but not accepted decision.

Manual review of final artifacts:

| Run | Observed final status behavior |
|---|---|
| 1 | Confused the status by presenting the decision as accepted with conditions. |
| 2 | Preserved a not-accepted status in prose, but did not produce the required JSON record. |
| 3 | Preserved a not-accepted status in prose, but did not produce the required JSON record. |

Interpretation:

- Status preservation can be inspected in prose.
- Structural validity cannot be evaluated directly from these final artifacts.
- The protocol is currently a weak instrument for the intended structural
  experiment.

## Observations

### Observation 1

Under pilot conditions, evidence supports that `decision_review@0.1.0` with
`ollama/qwen3:4b` did not reliably produce an exact `decision_record` structure
from an input-level formatting request.

Limitations:

- one fixture only;
- one local model only;
- no protocol variant designed to produce structured records;
- no deterministic extractor or validator.

### Observation 2

Under pilot conditions, status preservation was partially visible in prose:
two final artifacts preserved that the decision was not accepted, while one
final artifact converted the status into accepted-with-conditions.

Limitations:

- this was manual review, not a structural oracle result;
- exact status values from the local contract were not produced;
- the result may reflect prompt/protocol mismatch more than resource capability.

### Observation 3

The `Evidence` concept was useful in practice: the pilot produced measurements
and review notes that support observations without treating any single run as a
standalone fact.

Limitations:

- the evidence dossier is still manually assembled;
- no repeated independent experiment exists yet.

## Critical Review

What the evidence supports:

- The existing preset is adequate for producing completed Delibra runs and
  inspectable artifacts.
- It is not yet adequate as a direct instrument for `decision_record` structural
  evaluation.
- The distinction between measurement, evidence, and observation was useful in
  writing this note.

What remains indeterminate:

- Whether `qwen3:4b` can produce valid `decision_record` JSON under a protocol
  explicitly designed for that output.
- Whether another resource would follow the input-level JSON request more
  reliably.
- Whether the local contract is sufficient once exact structured records exist.

Concepts that proved useful:

- `evidence`;
- `structural_evaluation`;
- `task_oracle_evaluation`;
- `resource x protocol interaction`;
- separation between structural validity and acceptance status.

Concepts not yet exercised:

- `KnowledgeCandidate`;
- `Replication`;
- LLM judges;
- heuristics beyond status preservation;
- adaptive routing or escalation.

## Next Step

The next experiment should not be a batch runner.

Recommended next step:

1. Create one protocol or prompt variant whose final step explicitly produces a
   `decision_record` object.
2. Keep the same fixture and resource.
3. Run three repetitions again.
4. Compare whether extraction failures disappear.

This tests whether the first failure was mainly a protocol/instrument problem
before attributing it to resource capability.
