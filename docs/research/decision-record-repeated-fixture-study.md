# Decision Record Repeated Fixture Study

## Status

Experimental definition. Not an architecture decision, accepted experiment
format, validator specification, benchmark, product requirement, or approval to
implement a batch runner.

This document is the first concrete test of the
[Cognitive Resource Research Roadmap](cognitive-resource-research-roadmap.md).
It should be treated as a small research paper for a manual pilot: it defines
the question, hypothesis, falsification criteria, experimental design, evidence
shape, interpretation rules, and next experiment before running at scale.

No production code, runtime change, provider change, preset change, schema, or
new Delibra core concept is authorized by this document.

## Research Question

Under a fixed `decision_record` local contract, can repeated Delibra runs across
selected cognitive resources produce structurally valid decision records while
preserving the distinction between structural validity and acceptance status?

Secondary questions:

- Which failures are deterministic contract failures, and which require human
  interpretation?
- Does repetition reveal stable behavior or high variance for each resource
  configuration?
- Does the evidence support any scoped capability claim about extraction,
  constraint preservation, or status coherence?
- Which parts of the research roadmap vocabulary are actually useful when faced
  with concrete results?

## Hypothesis

A `decision_record` can be evaluated for structural conformance and local
status coherence without deciding whether the underlying decision is good or
accepted.

In this experiment, at least one resource configuration should be able to
produce structurally valid `decision_record` artifacts for the closed fixture
set with enough consistency to create an evidence dossier. The dossier should
also expose whether the roadmap concepts `measurement`, `evidence`,
`observation`, and `knowledge candidate` are useful distinctions rather than
decorative vocabulary.

## Falsification Criteria

The hypothesis is weakened or falsified if any of the following occurs:

- The local contract cannot classify the six representative fixtures without
  ambiguity.
- Structural validity and acceptance status cannot be separated in practice.
- Most failures require subjective interpretation rather than local structural
  checks.
- Repeated runs produce variance so high that no scoped observation can be made.
- The experiment cannot produce an evidence dossier distinct from raw runs and
  informal observations.
- The useful result is only a qualitative human impression, with no reproducible
  measurement layer.
- The pilot shows that `decision_record` is a poor instrument for testing
  repeated fixture evaluation.

The hypothesis is not falsified merely because a resource performs poorly. A
poor or unstable resource can still produce useful evidence.

## Experimental Design

### Fixture Set

Use the six fixtures defined in
[Decision Record Representative Fixtures](decision-record-fixtures.md):

- `valid_structural_decision_record`
- `missing_required_fields`
- `no_explicit_decision`
- `options_without_reasons`
- `structurally_valid_but_not_accepted`
- `contradictory_status`

For the pilot, these fixtures remain closed and versioned by document reference.
If concrete input texts are created later, they should preserve the intended
classification from the fixture note and be referenced from a separate fixture
section or file.

### Local Contract

Use the local contract defined in
[Decision Record Local Contract](decision-record-contract.md).

Required fields:

- `decision`
- `status`
- `options_considered`
- `reasons`
- `consequences`
- `uncertainties`
- `pending_conditions`

Status values:

- `proposed`
- `pending_review`
- `accepted`
- `rejected`

Structural validity does not imply acceptance.

### Protocol Under Test

Initial candidate:

- `decision_review@0.1.0`

This protocol produces a final synthesis, not a formal `decision_record`
artifact. The pilot must therefore either:

- ask the model through input constraints to produce a `decision_record` in the
  final synthesis; or
- create a manual extraction step outside Delibra for the pilot report.

This is a limitation of the experiment. It should not be hidden by adding a new
runtime primitive or changing the preset prematurely.

### Resources

Candidate resource configurations should be recorded externally to durable
Delibra core records.

Minimum pilot:

- one mock run to validate command mechanics only;
- one real local or remote LLM configuration if available;
- optional second real configuration only if cost and setup are low.

Resource labels must include, when available:

- provider;
- exposed model label;
- local or remote status;
- command date;
- runtime version or repository commit;
- relevant environment settings that affect generation.

If a provider does not expose a stable model version, the evidence dossier must
say so.

### Repetition

Manual pilot:

- one fixture;
- one real resource configuration;
- three repetitions.

First complete study:

- six fixtures;
- at least two resource configurations;
- at least three repetitions per fixture/resource pair.

Do not implement a batch runner until manual execution proves repeated metadata
collection is a real friction.

### Controlled Variables

- fixture identity;
- fixture text, once concrete fixture texts exist;
- protocol id and version;
- requested language;
- local contract version;
- evaluation plan version;
- repetition count;
- run command shape;
- output storage convention outside the repository.

### Free Or Uncontrolled Variables

- remote model backend version when not exposed;
- provider-side serving changes;
- model nondeterminism;
- hidden provider safety or formatting behavior;
- local hardware performance for local models;
- human evaluator fatigue or interpretation variance;
- prompt sensitivity caused by the current protocol not producing a formal
  `decision_record` artifact.

## Evaluation Plan

### structural_evaluation

Evaluate the candidate `decision_record` against the local contract:

- required fields present;
- required field types usable;
- `decision` non-empty;
- `options_considered` non-empty;
- `reasons` non-empty;
- `consequences` non-empty;
- `uncertainties` present as a list;
- `pending_conditions` present as a list;
- `status` belongs to the allowed set.

Output:

- `valid`;
- `invalid`;
- stable failure codes where possible;
- extraction failure when no candidate record can be isolated.

### task_oracle_evaluation

Compare expected fixture classification with observed classification:

| Fixture | Expected structural result | Expected acceptance implication |
|---|---|---|
| `valid_structural_decision_record` | valid | not automatically accepted |
| `missing_required_fields` | invalid | not evaluated |
| `no_explicit_decision` | invalid | not evaluated |
| `options_without_reasons` | invalid | not evaluated |
| `structurally_valid_but_not_accepted` | valid | pending review or rejected |
| `contradictory_status` | invalid | not evaluated |

Output:

- expected classification matched;
- expected classification missed;
- false valid;
- false invalid;
- acceptance/status confusion;
- indeterminate.

### operational_measurement

Collect:

- run status;
- duration when available;
- artifact count;
- trace event count;
- final artifact size;
- command success or failure;
- provider/model label externally;
- observed cost and token diagnostics only when available outside the durable
  core.

Operational measurements do not imply semantic quality.

### heuristic_evaluation

Optional for the pilot:

- constraint coverage indicator;
- explicit status preservation;
- explanation of pending conditions;
- evidence of invented approval;
- repeated phrasing or brittle formatting.

Every heuristic must be labeled as heuristic and excluded from structural pass
or fail.

### llm_judge_evaluation

Out of scope for the manual pilot.

May be considered in a later experiment only after the structural and oracle
layers produce stable evidence.

### human_evaluation

Required for:

- extraction of a candidate `decision_record` from final synthesis when the
  output is not already structured;
- confirmation that a structural failure code matches the fixture intent;
- review of any observation or knowledge candidate.

Human review should not silently override structural results. If a human
reviewer disagrees with a structural classification, record the conflict as
evidence.

## Evidence Dossier

The evidence dossier is the central output of this experiment. It should sit
between raw runs and observations.

Minimum dossier shape:

```yaml
experiment_id: decision-record-repeated-fixture-study
status: draft
fixture_set:
  source: docs/research/decision-record-fixtures.md
contract:
  source: docs/research/decision-record-contract.md
runs:
  total: 0
  completed: 0
  failed: 0
resources: []
measurements:
  structural_valid_count: 0
  structural_invalid_count: 0
  extraction_failure_count: 0
  oracle_match_count: 0
  oracle_miss_count: 0
  status_confusion_count: 0
variance:
  by_fixture: []
  by_resource: []
human_review:
  required: true
  reviewed_cases: []
observations: []
limitations: []
```

The dossier should link to run and trace files without committing raw provider
outputs into the repository.

Evidence can support several outcomes:

- the hypothesis is supported within a narrow scope;
- the hypothesis is weakened;
- the fixture set is inadequate;
- the local contract is inadequate;
- the protocol under test is a poor instrument;
- the evaluation plan needs revision;
- a resource shows a scoped capability or failure pattern.

## Interpretation Rules

Allowed conclusions:

- In this experiment, configuration X produced structurally valid records for
  fixture family Y in N of M repetitions.
- Configuration X confused structural validity with acceptance in N cases.
- Fixture Y produced high variance and needs refinement.
- The current protocol does or does not provide a clean enough instrument for
  this question.
- The local contract was sufficient or insufficient for the pilot.
- The roadmap concept `evidence` did or did not add useful separation between
  measurements and observations.

Forbidden conclusions:

- Configuration X is generally better than configuration Y.
- Provider X is better than provider Y.
- A model is globally good or bad.
- The result measures general intelligence.
- Structural validity proves decision quality.
- Passing this experiment means Delibra should add a production validator.
- A single run proves a capability.
- The batch runner should be implemented before manual friction is observed.

Observation template:

```text
Under experiment conditions C, evidence dossier E supports observation O with
limitations L.
```

Knowledge candidate template:

```text
Across evidence dossiers E1..En, capability claim K appears to hold under
conditions C, with counterexamples X and replication needs R.
```

No knowledge candidate should be created from the manual pilot alone unless it
is explicitly labeled as weak and replication-required.

## Threats To Validity

- The fixture definitions are not yet concrete input texts.
- `decision_review@0.1.0` does not formally produce a `decision_record`.
- Manual extraction may introduce reviewer bias.
- Small repetition counts may hide variance.
- Remote model versions may change without notice.
- Provider/model metadata is intentionally external to durable core records.
- A resource may fail because of prompt shape rather than capability.
- Structural checks may reward shallow formatting compliance.
- Human review may overinterpret plausible prose.
- The pilot may validate the local contract but not the broader roadmap.

## Open Questions

- Should concrete fixture texts live in this document, a separate research file,
  or outside the repository with only hashes committed?
- Should the first complete study modify the protocol to produce a
  `decision_record`, or keep the existing preset unchanged for comparability?
- Is manual extraction acceptable for the pilot, or does it contaminate the
  evidence too much?
- What is the minimum useful repetition count?
- Which resource configurations should be compared first?
- How should provider/model metadata be captured externally without weakening
  the core boundary?
- What failure codes are stable enough to reuse?
- When does repeated manual execution justify a small batch helper?
- Does the `Evidence` concept remain useful once real results are collected?
- Which concepts from the roadmap become unnecessary in this first experiment?

## Next Experiment

Run the smallest manual pilot:

1. Choose one fixture from the six representative fixtures.
2. Write one concrete input text for that fixture.
3. Run `decision_review@0.1.0` three times with one real resource
   configuration.
4. Store raw run and trace outputs outside the repository.
5. Extract candidate `decision_record` content for each repetition.
6. Apply the local structural contract manually or with a scratch script outside
   production code.
7. Fill an evidence dossier.
8. Write a short critical review:
   - what the evidence supports;
   - what remains indeterminate;
   - which roadmap concepts were useful;
   - which concepts felt unnecessary;
   - whether the next step should be fixture refinement, protocol refinement,
     or evaluator refinement.

Do not implement a batch runner, validator, schema, Observatory store, routing
policy, or production abstraction before this pilot has been reviewed.
