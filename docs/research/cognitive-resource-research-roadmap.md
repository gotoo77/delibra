# Cognitive Resource Research Roadmap

## Status

Research program roadmap. Not an accepted architecture decision, protocol
specification, implementation plan, product commitment, or approval to create a
new Delibra subsystem.

This document preserves a research direction for Delibra:

> How can a system select and combine cognitive resources for a task while
> balancing quality, cost, latency, stability, and resource use?

The roadmap is deliberately non-normative. It should make research questions
falsifiable and guide experiments without moving provider metadata, model
rankings, experiment objects, schedulers, or evaluation schemas into the durable
core.

## Existing Grounding

This roadmap is grounded in existing repository material:

- [ADR-0001](../adr/0001-core-identity.md) defines Delibra as an
  artifact-first derivation runtime with durable provenance and keeps the core
  small.
- [ADR-0002](../adr/0002-runtime-provider-boundary.md) keeps provider names,
  model names, token usage, cost, and raw provider responses out of durable
  core records.
- [ADR-0003](../adr/0003-efficient-execution.md) frames efficient execution as
  a runtime quality that must preserve derivation semantics.
- [Architecture Principles](../architecture-principles.md) require new ideas to
  grow from observed usage and keep trace as observability, not domain state.
- [Measurement Notes](../measurement-notes.md) distinguish direct measures from
  proxies.
- [Delibra Observatory Design Review](../design-reviews/delibra-observatory.md)
  explores review-required observation and comparison of completed runs without
  accepting an Observatory subsystem.
- [Field notes](../field-notes/README.md) already serve as the human-readable
  surface for observed usage evidence.
- The existing CLI includes `inspect`, `analyze-run`, and `compare-runs` helper
  surfaces for completed run and trace files.
- Existing research notes on `decision_record` define representative fixtures
  and a local structural contract without creating a production validator.

What exists today:

- durable `Run`, `Artifact`, and `Trace` records;
- protocols and presets;
- provider integrations behind runtime boundaries;
- execution policy and runtime diagnostics;
- mechanical run inspection and analysis;
- a review-required comparison helper;
- field notes, observations, design reviews, ADRs, and non-normative research
  notes.

What is only evoked or candidate:

- durable experiment definitions;
- repeated run batches;
- evaluation result dossiers;
- cognitive routing or automatic escalation;
- resource/task capability maps;
- an Observatory persistence layer;
- candidate knowledge records derived from repeated experiments.

What would be new:

- an explicit experiment vocabulary for repeated model/protocol/input studies;
- evaluation contracts separating structure, oracle checks, operations,
  heuristics, LLM judges, and human review;
- a systematic route from runs to measurements, evidence, observations,
  candidate knowledge, and replication;
- adaptive routing research based on evidence rather than model preference;
- a resource vocabulary that can include LLMs, deterministic tools, retrieval,
  solvers, and humans without making any one resource type the architecture.

Potential tensions:

- Provider/model metadata is necessary for experimental comparison, but current
  ADRs reject it from durable core records.
- Cost and token information is useful for efficiency research, but it remains
  runtime diagnostic data unless a later decision changes the durable model.
- Observatory may help organize evidence, but the accepted architecture does
  not yet include an Observatory subsystem or store.
- Evaluation outputs may look authoritative even when they are generated,
  heuristic, or based on one run.

## Why This Research Matters

Most public comparison work around LLM systems still centers on models: which
model scores higher, which provider is stronger, which benchmark moved. That is
useful, but it is not the whole engineering problem Delibra exposes.

Delibra is already centered on artifacts, transformations, roles, protocols,
and provenance. From that perspective, the more interesting question is not
only which model performed best, but what actually produced the performance:

- the model;
- the protocol;
- task decomposition;
- role specialization;
- resource combination;
- verification;
- execution order;
- context allocation;
- constraints;
- escalation policy;
- human review.

The research direction is therefore a move from a science of isolated models
toward a science of reasoning systems. The unit of study becomes the allocation
strategy under explicit constraints, not only the raw model call.

Candidate system view:

```text
task
x protocol
x resources
x evaluation
-> observed behavior
```

In that view, Delibra is not the object being optimized for its own sake. It is
an experimental instrument for making artifact derivation systems observable,
comparable, and criticizable.

Central claim:

> The objective is not to discover the best cognitive resource, but to discover
> the most appropriate allocation strategy for a given problem under explicit
> constraints.

This matters because a system may achieve better real-world performance by
choosing, sequencing, checking, or combining modest resources than by always
calling the strongest available model. The claim is not that smaller resources
are generally superior. The claim is that resource allocation itself is a
research object.

## Vision

Users should express tasks, goals, constraints, quality expectations, and
possibly budget, latency, or criticality. A future system could then select,
combine, verify, or escalate cognitive resources according to evidence.

This does not assume that small models are generally better than large models.
The research question is narrower and more useful:

- when is a small model sufficient;
- when is it especially suitable;
- when does it fail predictably;
- when can several specialized passes outperform a single direct call;
- when is escalation to a stronger model necessary;
- how can the system detect an insufficient result;
- how should quality, cost, latency, stability, confidentiality, availability,
  and resource use be traded off?

The guiding principle is:

> Seek systemic intelligence gains before brute-force model power gains.

Efficiency is not only an operational metric. It is a design pressure:

> Do not use a more expensive cognitive resource than necessary to satisfy the
> task's explicit requirements.

## Operating Principles

- Do not rank models globally.
- Describe scoped behavior under declared conditions.
- Study allocation strategies, not only individual model performance.
- Treat cognitive resources broadly: LLMs, deterministic tools, retrieval,
  solvers, specialized programs, and humans may all be resources under explicit
  contracts.
- Do not use a more expensive cognitive resource than needed when a cheaper
  resource satisfies the declared quality, latency, and risk constraints.
- Treat one run as evidence, not knowledge.
- Preserve the distinction between data, measurement, interpretation, and
  decision.
- Prefer directly observable variables over proxies when trace data allows it.
- Treat LLM judges as imperfect instruments, not oracles.
- Keep human review targeted at informative cases instead of requiring humans to
  read everything.
- Keep provider-specific details outside the durable Delibra core unless a
  future ADR explicitly changes that boundary.
- Add production abstractions only after repeated experiments create real
  architectural pressure.

## Vocabulary

These terms are operational vocabulary for Delibra research, not universal
philosophical claims.

`data`
: Raw run output, trace event, artifact payload, fixture result, or elementary
  measurement.

`measurement`
: A reproducible extraction or calculation over data, such as duration, artifact
  count, schema validity, missing fields, or repeated output count.

`information`
: Data or measurements contextualized enough to compare, for example with
  protocol version, fixture identity, provider/model configuration, repetition
  index, and controlled variables.

`evidence`
: A reviewed or reviewable dossier of measurements, evaluation results,
  repetitions, variance, provenance, and human or automated checks that can
  support or weaken an observation. Evidence may aggregate many runs; it should
  not be reduced to one run unless the observation is explicitly single-run.

`observation`
: A situated interpretation anchored to evidence. Example: "configuration B
  preserved the architecture/product/support split in this pair of runs."

`knowledge candidate`
: A scoped regularity that appears to hold under declared conditions but still
  needs replication, counterexamples, and limits of validity.

`more robust knowledge`
: A knowledge candidate that has survived repetitions, controlled variations,
  or independent replications.

`replication`
: Repeating an experiment or a controlled variant to test whether an observation
  persists.

`qualification`
: A scoped judgment that a run, configuration, protocol, or output met a
  defined bar. Qualification is not global model quality.

Candidate progression:

```text
run
-> measurement
-> evidence
-> observation
-> knowledge candidate
-> replication
-> more robust knowledge
```

## Research Axes

### A. Experimental Reproducibility

Goal: define what makes two runs comparable.

Questions:

- Which variables are controlled: protocol id/version, input fixture, provider,
  model label, runtime version, language, policy, temperature-like settings,
  repetition index, and timestamp?
- Which variables are free or unstable: remote model revisions, provider-side
  serving changes, latent nondeterminism, rate limits, and hidden safety policy?
- What is exact replication, controlled variation, and a new experiment?
- How should remote models be identified when the exact backend version is not
  exposed?

Minimum direction: persist enough external experiment metadata to compare runs
without adding provider/model fields to `Run`, `Artifact`, `Trace`, or
`Protocol`.

### B. Run Batches

Goal: express and execute experimental matrices.

Conceptual shape:

```text
resources
x protocol variants
x fixtures
x repetitions
x controlled parameters
```

This roadmap does not authorize a batch runner. The first need is a contract for
what a batch would mean and how each run would be linked to an experiment.

### C. Task Taxonomy

Goal: classify tasks, not models.

Candidate families:

- extraction;
- classification;
- transformation;
- structural validation;
- factual verification;
- contradiction detection;
- critique;
- option generation;
- synthesis;
- decision;
- planning;
- design;
- constrained creativity;
- constraint preservation;
- code production;
- code repair;
- evaluation;
- triage.

A useful taxonomy must be operational, testable, extensible,
model-independent, fine enough to distinguish behavior, and small enough to
remain usable.

### D. Capability Matching And Failure Taxonomy

Goal: describe required capabilities, resource capabilities, and mismatches in
context.

Candidate matching flow:

```text
task
-> required capabilities
-> candidate resource capabilities
-> matching decision
-> observed behavior
```

The scheduler research should not route directly from task to resource name.
It should first ask what capabilities the task requires, then which resources
can provide those capabilities under the declared constraints.

Candidate required capabilities:

- reliable extraction;
- structural validation;
- deterministic verification;
- deep critique;
- logical reasoning;
- contradiction detection;
- constraint preservation;
- broad synthesis;
- domain expertise;
- uncertainty calibration;
- human accountability.

Candidate dimensions:

- format adherence;
- constraint fidelity;
- context recall;
- critique depth;
- precision;
- false positive rate;
- false negative rate;
- stability;
- variance;
- prompt sensitivity;
- order sensitivity;
- invention propensity;
- uncertainty signaling;
- self-limit detection;
- usable justification;
- synthesis without erasing disagreement.

Preferred statement shape:

```text
Under conditions C, on task family T, configuration X showed behavior B,
supported by evidence E, with limits L.
```

Avoid:

```text
Model X is good.
Model Y is bad.
```

### E. Resource Taxonomy

Goal: describe available cognitive resources without reducing them to LLM model
names.

Candidate resource families:

- general-purpose LLM;
- small local LLM;
- specialized LLM or fine-tuned model;
- deterministic function;
- parser or schema validator;
- compiler;
- software test suite;
- SAT, SMT, or constraint solver;
- search engine;
- retrieval system;
- vector database;
- OCR engine;
- calculator or symbolic engine;
- static analyzer;
- simulator;
- human reviewer;
- human domain expert.

A useful resource taxonomy should describe what a resource can do, what it
costs, how deterministic it is, what inputs it accepts, what evidence it
produces, what failure modes it has, and how it can be composed with other
resources.

This is aligned with Delibra's current identity: Delibra derives artifacts
through declared transformations. LLMs are important resources, but they should
not become the only imaginable source of cognitive work.

### F. Mechanical Metrics

Goal: measure what is directly observable.

Examples:

- duration;
- errors;
- completion rate;
- JSON validity;
- schema or local contract conformance;
- field presence;
- length;
- tokens when available outside the core;
- estimated cost when available outside the core;
- number of calls;
- number of steps;
- variance across repetitions.

Mechanical metrics are often reliable but do not prove semantic quality.

### G. Oracle-Based Metrics

Goal: evaluate properties where expected answers or rules are known.

Examples:

- software tests;
- injected contradictions to detect;
- mandatory constraints to preserve;
- inconsistent statuses to reject;
- known bugs to identify;
- fixture facts to retain;
- calculable solutions;
- explicit structural rules.

This is the strongest starting ground because it can produce repeatable
evidence without pretending to solve open-ended judgment.

### H. Heuristics

Goal: collect useful signals without treating them as truth.

Examples:

- constraint coverage;
- presence of reasons;
- repetition;
- option diversity;
- argument-to-conclusion traceability;
- internal contradiction;
- apparent novelty;
- information loss between steps;
- excessive convergence;
- excessive divergence.

Every heuristic should declare what it measures, what it does not prove, likely
false positives, and likely false negatives.

### I. LLM Judges

Goal: use models as evaluation instruments only when their limits are explicit.

Required caveats:

- bias toward longer answers;
- style bias;
- position or order bias;
- self-preference;
- instability;
- correlation between non-independent judges;
- need for precise rubrics;
- possible need for multiple judges;
- disagreement measurement;
- comparison with sampled human evaluation.

An LLM judge produces evidence for review, not an oracle verdict.

### J. Targeted Human Evaluation

Goal: reduce human reading load, not eliminate human judgment.

Cases worth surfacing:

- strong evaluator disagreement;
- regression;
- atypical result;
- high variance;
- unexpected violation;
- weak model beating a baseline;
- possible emergence;
- unclassified failure;
- conflict between metrics.

Principle:

> Humans should read the most informative cases, not every case.

### K. Resource x Protocol Interaction

Goal: avoid attributing protocol effects to resource capability.

The object of study is the complete system configuration, not one dimension in
isolation:

```text
task x protocol x resources x evaluation -> observed behavior
```

Factors to separate:

- resource;
- protocol;
- input;
- parameters;
- order;
- role;
- accumulated context;
- interactions between those factors.

### L. Escalation And Adaptive Routing

Goal: study a future cognitive scheduler without implementing it now.

Candidate loop:

```text
analyze task
-> choose low-cost suitable resource
-> execute
-> evaluate result
-> accept, verify, recombine, or escalate
```

Questions:

- How can difficulty be estimated before execution?
- How can confident failure be detected?
- Which signal triggers escalation?
- Is verification by a smaller model enough?
- When is a deterministic tool better than an LLM call?
- When should a human be treated as the right resource rather than as a final
  fallback?
- When are multiple small models more efficient than one large model?
- When is escalation cheaper than starting with the large model?
- How can evaluation cascades be kept cheaper than the original task?
- How should goals express quality, cost, latency, and criticality constraints?

### M. Efficiency

Goal: avoid reducing evaluation to best absolute score.

Dimensions:

- quality;
- cost;
- latency;
- token use;
- energy when measurable;
- stability;
- explainability;
- confidentiality;
- local availability;
- robustness;
- escalation capacity.

Candidate methods:

- minimum thresholds;
- constraints;
- Pareto fronts;
- multi-objective comparison;
- policy profiles;
- minimum cost at acceptable quality;
- best quality under budget;
- best latency under quality threshold.

No universal scalar quality formula is proposed.

### N. Emergence And Systemic Intelligence

Goal: test whether organized combinations produce useful output beyond simple
concatenation or averaging.

Distinctions:

- textual novelty;
- conceptual novelty;
- recombination;
- mutual correction;
- contradiction resolution;
- creation of an option absent from inputs;
- useful improvement;
- new hallucination.

Novelty is not automatically improvement.

### O. From Observations To Knowledge

Goal: formalize progression:

```text
run
-> measurement
-> evidence
-> observation
-> knowledge candidate
-> replication
-> more robust knowledge
```

Candidate requirements:

- provenance;
- context;
- limits of validity;
- evidence dossier;
- supporting evidence;
- counterexamples;
- status;
- date;
- resource and protocol configuration;
- confidence level;
- replication need;
- revision history.

Knowledge Vault may be relevant after human review and repeated evidence, but
this roadmap does not couple Delibra to Knowledge Vault.

## Candidate Concept Map

These are reasoning objects, not production classes. The candidate concept map
is intentionally a reasoning vocabulary, not a proposed software object model.
No one-to-one mapping between these concepts and implementation classes should
be assumed.

### ResearchQuestion

Responsibility: state what the experiment program is trying to discover.

Minimum data: question, scope, motivation, non-goals, status.

Relation to Delibra: may cite protocols, presets, runs, and field notes.

Durability: durable research note.

Provenance: author/reviewer, date, linked evidence.

Overlap risk: may become a roadmap item or product promise.

Open questions: where research questions should live and how many are useful.

### Hypothesis

Responsibility: make a falsifiable claim under scoped conditions.

Minimum data: claim, expected observation, falsification condition, scope,
evidence needed.

Relation to Delibra: may concern a protocol, task family, model configuration,
or evaluation family.

Durability: durable until confirmed, revised, or refuted.

Provenance: originating observation, date, reviewer.

Overlap risk: may be confused with accepted architecture.

Open questions: what status vocabulary is enough.

### ExperimentDefinition

Responsibility: define a comparable set of runs and evaluations.

Minimum data: id, question, hypotheses, fixtures, protocol variants,
configurations, repetitions, controlled variables, free variables, evaluation
plan, stopping criteria.

Relation to Delibra: references protocols, presets, inputs, run outputs, and
external provider/model metadata.

Durability: candidate durable research object outside the core.

Provenance: definition author, version, review status.

Overlap risk: may overlap with Observatory Experiment or a future batch
manifest.

Open questions: whether it belongs in `docs/research`, run output directories,
field notes, or Observatory.

### ExperimentCase

Responsibility: define one fixture/configuration/repetition cell.

Minimum data: fixture id, protocol id/version, provider/model configuration,
parameter set, repetition index, expected oracle facts if any.

Relation to Delibra: produces one or more ordinary Delibra runs.

Durability: durable as part of an experiment definition or manifest.

Provenance: links to fixture source and experiment version.

Overlap risk: may duplicate CLI run arguments.

Open questions: whether cases should be generated or written explicitly.

### ExperimentRun

Responsibility: link an actual completed run to an experiment case.

Minimum data: run file, trace file, case id, status, execution timestamp,
external configuration metadata, failure mode if any.

Relation to Delibra: references ordinary persisted `run.json` and `trace.json`;
does not mutate them.

Durability: candidate sidecar or report entry.

Provenance: run output paths or digests, command context where available.

Overlap risk: may look like a replacement for `Run`.

Open questions: how much provider metadata can be durable externally without
polluting the core.

### EvaluationDefinition

Responsibility: define how outputs will be evaluated.

Minimum data: family, target artifact or run scope, procedure, rubric or rule,
expected oracle values, limitations.

Relation to Delibra: may inspect artifacts and traces after completion.

Durability: durable if repeatable.

Provenance: author, version, fixture source, reviewer.

Overlap risk: may become a generic validation architecture too early.

Open questions: whether evaluation definitions are documentation, sidecars, or
future Observatory records.

### EvaluationResult

Responsibility: record evaluation output for one experiment run or artifact.

Minimum data: target, measurements, pass/fail/warning details where applicable,
heuristic scores, judge outputs, human review flags, limitations.

Relation to Delibra: references run and artifact ids.

Durability: candidate experiment artifact, not core artifact by default.

Provenance: evaluation definition version, evaluator identity, timestamp.

Overlap risk: may be confused with semantic truth or accepted qualification.

Open questions: whether it should be a Delibra artifact, sidecar, Markdown
section, or Observatory object.

### Evidence

Responsibility: aggregate the proof material that supports, weakens, or
falsifies an observation.

Minimum data: referenced experiment definitions, run set, measurement summary,
evaluation results, variance, repetitions, reviewer status, limitations, and
counterexamples.

Relation to Delibra: cites runs, traces, artifacts, evaluation results, and
field notes without requiring observations to point directly to raw runs.

Durability: durable evidence dossier when it is reviewable and repeatable;
otherwise a draft section in an experiment report.

Provenance: source runs, evaluation definitions, evaluator identities,
timestamps, reviewer state, and versioned fixtures.

Overlap risk: may look more authoritative than its evidence quality permits.

Open questions: whether evidence is a standalone record, an experiment report
section, an Observatory object, or only a documentary convention.

### Observation

Responsibility: state an interpreted finding anchored to evidence.

Minimum data: statement, evidence references, scope, confidence, status,
limitations.

Relation to Delibra: cites an evidence dossier that may itself reference run
ids, artifact ids, trace events, and evaluation results.

Durability: durable as field note, research note, or future Observatory output.

Provenance: source evidence, reviewer, date.

Overlap risk: may be promoted too quickly into knowledge.

Open questions: contract difference between observation, qualification, and
knowledge candidate.

### KnowledgeCandidate

Responsibility: preserve a scoped regularity that may guide later routing or
design.

Minimum data: claim, scope, evidence, counterexamples, confidence, replication
status, limits of validity.

Relation to Delibra: may influence future presets, policies, or routing
experiments.

Durability: durable but review-required.

Provenance: supporting observations and replications.

Overlap risk: false authority from weak evidence.

Open questions: where candidates live and how they are retired or revised.

### Replication

Responsibility: test whether a prior observation persists.

Minimum data: target observation, repeated or varied conditions, results,
comparison, interpretation.

Relation to Delibra: references new runs and prior evidence.

Durability: durable research record.

Provenance: experiment versions, run references, evaluator versions.

Overlap risk: may be treated as exact reproducibility despite uncontrolled
provider changes.

Open questions: how many repetitions are sufficient for each task family.

### ExperimentReport

Responsibility: synthesize the experiment evidence for human review.

Minimum data: question, design, results, anomalies, observations, limitations,
candidate knowledge, open questions, next action.

Relation to Delibra: may be a field note, research note, or future Observatory
draft.

Durability: durable review surface.

Provenance: linked definitions, runs, evaluation results, reviewer.

Overlap risk: may hide raw variance behind a polished narrative.

Open questions: when reports should become field notes versus research notes.

## Evaluation Families

No single universal score is proposed. An evaluation should produce a
multidimensional dossier.

### structural_evaluation

Objectivity: high when the contract is explicit.

Automation: high.

Cost: low after the contract exists.

Limits: proves structure, not semantic acceptance or usefulness.

Evidence produced: schema validity, required fields, deterministic consistency
rules, structural warnings.

Escalation role: can reject or retry malformed output before expensive semantic
review.

### task_oracle_evaluation

Objectivity: high to medium, depending on oracle quality.

Automation: medium to high.

Cost: low to medium.

Limits: only covers known expected facts, injected defects, and closed
criteria.

Evidence produced: constraints preserved, known errors detected, false
positives, false negatives, fixture-specific correctness.

Escalation role: strong signal for escalation when expected facts are missed or
contradictions are accepted.

### operational_measurement

Objectivity: high for captured values, lower for estimates.

Automation: high.

Cost: low.

Limits: duration, tokens, cost, and counts do not imply quality.

Evidence produced: latency, errors, completion, call count, step count, token or
cost diagnostics when available outside the core.

Escalation role: constrains policies by budget, latency, and failure rate.

### heuristic_evaluation

Objectivity: low to medium.

Automation: medium.

Cost: low to medium.

Limits: can be gamed and may correlate weakly with actual quality.

Evidence produced: traceability indicators, repetition indicators, coverage
proxies, divergence or convergence signals.

Escalation role: useful as a triage signal, not as the only escalation trigger.

### llm_judge_evaluation

Objectivity: low to medium, depending on rubric and calibration.

Automation: medium to high.

Cost: medium to high.

Limits: judge bias, instability, non-independence, verbosity preference, style
preference, and self-preference.

Evidence produced: rubric scores, rationales, disagreement, comparative
judgments.

Escalation role: can flag cases for review or escalation when disagreement is
high, but should not be treated as an oracle.

### human_evaluation

Objectivity: variable; improved by rubrics and independent review.

Automation: low.

Cost: high.

Limits: fatigue, bias, expertise differences, low throughput.

Evidence produced: reviewed judgments, qualitative explanations, corrections to
automated evaluations, sampled calibration data.

Escalation role: final arbiter for high-criticality cases and calibration source
for judge and heuristic evaluation.

Illustrative dossier:

```yaml
structural:
  schema_valid: true
  required_fields_present: true
  explicit_decision: true
task_oracle:
  constraints_preserved: 8
  constraints_total: 10
  known_errors_detected: 3
  known_errors_total: 4
  false_positives: 1
operational:
  duration_ms: 14230
  input_tokens: 4200
  output_tokens: 1800
  estimated_cost: 0.012
heuristics:
  traceability_score: 0.72
  repetition_indicator: 0.18
semantic_judges:
  relevance:
    median: 4
    disagreement: 1
  actionability:
    median: 3
    disagreement: 2
human_review:
  required: true
  reason: high_judge_disagreement
```

This format is illustrative, not a proposed production schema.

## First Experimental Slice

Title:

> Define the minimal experiment and evaluation contracts for a repeated
> `decision_record` fixture study.

Why this slice:

- `decision_record` already has non-normative research notes, representative
  fixtures, and a local structural contract.
- The domain separates structural validity from acceptance.
- It can test small and large models on a scoped task without ranking them
  globally.
- It supports mechanical metrics, structural checks, oracle-like fixture
  expectations, repetition, and human review of ambiguous cases.

Scope:

- fixed fixture set derived from the existing representative fixtures;
- one protocol or protocol variant selected explicitly for the study;
- several provider/model configurations recorded outside durable core records;
- repeated runs per fixture/configuration;
- structural evaluation of the produced `decision_record`;
- fixture oracle checks for required constraints and contradictory status;
- operational measurements such as completion, duration, error, artifact count,
  and cost/token diagnostics where available externally;
- interpretation limited to the experiment conditions.

Candidate deliverables:

1. Experiment definition.
2. Versioned fixtures.
3. Controlled and free variable declaration.
4. Mechanical metrics list.
5. Structural oracle.
6. Evaluation dossier format.
7. Repetition protocol.
8. Comparability criteria.
9. Interpretation rules.
10. Success and failure criteria.

Allowed conclusion shape:

```text
Under this experiment's conditions, configuration X produced structurally
conformant decision records in N percent of repetitions, with observed cost,
latency, variance, and constraint-fidelity characteristics.
```

Disallowed conclusion shapes:

- model X is generally intelligent;
- provider Y is better;
- small models are superior;
- structural validity proves decision quality;
- one run establishes a capability.

## Milestones

### Milestone 0 - Vocabulary And Experimental Contracts

Define experiment, repetition, observation, knowledge candidate, measurement,
evaluation, interpretation, and decision. Decide minimum metadata.

Do not proceed until a reader can tell what is being compared and what is not.

### Milestone 1 - First Oracle-Based Experiment

Use closed fixtures, several model configurations, repetitions, mechanical
metrics, and reproducible structural evaluation.

Do not proceed until the experiment can be repeated from its definition.

### Milestone 2 - Minimal Batch Runner

Only after the contract is stable, consider matrix execution, run-experiment
association, automatic collection, error recovery, and raw reports.

Do not proceed if manual execution is still sufficient or the matrix is not
well defined.

### Milestone 3 - Comparison And Triage

Aggregate results, variance, anomalies, regressions, and runs worth human
inspection.

Do not proceed until raw results can be reviewed without hiding individual
failures.

### Milestone 4 - Constraint Fidelity

Use injected constraints, omissions, contradictions, false positives, and load
sensitivity.

Do not proceed until structural validation and acceptance remain separate.

### Milestone 5 - Heuristic Evaluations

Test traceability, repetition, coverage, information loss, and disagreement.

Do not proceed unless each heuristic declares its failure modes.

### Milestone 6 - Calibrated LLM Judges

Introduce rubrics, multiple judges, order randomization, disagreement, and a
sampled human control set.

Do not proceed unless judge outputs are treated as review evidence, not oracle
truth.

### Milestone 7 - Static Routing

Define manual recommendations by task family and observed configuration
behavior.

Do not proceed unless recommendations cite experiment evidence and limits.

### Milestone 8 - Conditional Escalation

Try low-cost first pass, verification, confidence threshold, and escalation.

Do not proceed unless escalation cost is measured against direct large-model
execution.

### Milestone 9 - Adaptive Routing

Study automatic choice, multi-objective optimization, and retrospective analysis
of routing decisions.

Do not proceed until static routing and escalation have produced stable
evidence.

### Milestone 10 - Emergence Study

Compare complementary protocols against simple baselines for useful novelty,
mutual correction, and marginal cost of deliberation.

Do not proceed until simpler quality and cost measures are reliable.

### Milestone 11 - Durable Capitalization

Record knowledge candidates, replications, status, and possible links to
Observatory or Knowledge Vault.

Do not proceed until the project has evidence worth preserving beyond a single
local experiment.

## Anti-Goals

- Build a universal LLM leaderboard.
- Evaluate every available model.
- Create an autonomous routing system immediately.
- Add all candidate concepts to Delibra core.
- Create a single magic quality score.
- Treat LLM judges as objective.
- Automate away all human evaluation.
- Generalize from one run.
- Conclude that a model is intrinsically good or bad.
- Prove ideologically that small models are superior.
- Create a new subsystem before experimental pressure justifies it.
- Confuse operational metrics with quality.
- Confuse novelty with useful emergence.
- Confuse structural conformance with semantic acceptance.
- Confuse observation with established knowledge.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Combinatorial explosion of experiment matrices. | Start with closed fixtures, few configurations, and explicit stopping criteria. |
| Batch cost. | Run small pilots, measure cost, and cap repetitions before expanding. |
| Remote model instability. | Record timestamps, exposed model labels, provider metadata externally, and avoid exact-version claims when unavailable. |
| Fixture bias. | Add fixtures from real observed failures and later replicate on independent domains. |
| Overfitting to a local benchmark. | Treat results as local until replicated with new fixtures and protocols. |
| Prompt/evaluator contamination. | Keep production prompts, evaluation rubrics, and oracle answers separated. |
| Self-evaluation by related models. | Record judge identity and use human samples or independent judges where possible. |
| Easy but meaningless metrics. | Label what each metric can and cannot prove. |
| False objectivity. | Require limitations, review status, and evidence references. |
| Data volume without interpretation. | Add triage and report formats before scaling batches. |
| Documentation drift. | Keep one roadmap and promote only repeated findings. |
| Premature abstractions. | Require repeated independent experiments before shared production code. |
| Observatory complexity absorbing the project. | Keep Observatory as design review or helper until persistence pressure is proven. |
| Non-reproducible results. | Separate exact replication from controlled variation and record uncontrolled variables. |
| Overgeneralized conclusions. | Use scoped conclusion templates. |
| Confusion between research and product. | Keep status labels explicit and avoid product promises. |
| Energy or financial cost of evaluations. | Track evaluation overhead and compare it with direct execution. |
| Scheduler more expensive than direct call. | Measure routing overhead as part of any escalation experiment. |
| Escalation too frequent. | Tune thresholds against direct baselines and false escalation rates. |
| Excessive trust in model self-reports. | Prefer external checks, source pointers, and human review. |
| Opportunistic selection of favorable results. | Declare fixtures, repetitions, and success criteria before running. |

## Open Questions

1. Is an experiment a durable Delibra object or an external research concept?
2. Does Observatory only observe completed runs, or could it eventually
   orchestrate experiments?
3. Where should experiment definitions be stored?
4. Which provider/model metadata can be durable without polluting the core?
5. How should unstable remote model versions be represented?
6. Is an evaluation a normal Delibra artifact or a distinct object?
7. How can evaluators avoid influencing the production they evaluate?
8. How should independence between several judges be qualified?
9. How can LLM evaluation be calibrated with limited human review?
10. How should limits of validity be expressed for an observation?
11. What repetition level is sufficient?
12. How should non-deterministic model runs be compared?
13. What is the contract difference between observation, qualification, and
    knowledge candidate?
14. How should contradictory results across experiments be handled?
15. How can energy consumption be measured when a provider does not expose it?
16. How should quality, cost, and latency be balanced without arbitrary scalar
    collapse?
17. How can confident failure by a small model be detected?
18. When does additional verification become counterproductive?
19. How can emergent synthesis be evaluated without rewarding verbosity or mere
    novelty?
20. Which criteria should trigger escalation to a stronger resource?
21. How can model weakness be distinguished from protocol weakness?
22. How can a task taxonomy avoid becoming too abstract or too large?
23. How should recommendations evolve when models change quickly?
24. Should results qualify a model, an exact version, a family, or only an
    experimental configuration?
25. What role should local models, confidentiality, and offline availability
    play in efficiency?

## Progression Criteria

A research slice can progress when:

- the question and hypothesis are explicit;
- controlled and free variables are declared;
- fixtures or inputs are versioned or otherwise identifiable;
- evaluation families are separated;
- mechanical measures are not presented as semantic quality;
- human review requirements are explicit;
- limitations are written before conclusions;
- raw variance remains inspectable;
- conclusions stay within the experiment scope;
- the next implementation step removes proven friction rather than anticipated
  complexity.

## Proposed Next Slice

Define the minimal experiment and evaluation contracts for a repeated
`decision_record` fixture study.

Immediate work should be contractual:

- write a small experiment definition;
- choose or refine the existing representative fixtures;
- define controlled variables and repetition rules;
- define structural and task-oracle evaluation expectations;
- define the evaluation dossier shape as a draft;
- define interpretation rules and allowed conclusion language;
- run a tiny manual pilot before designing a batch runner.

This next slice should not implement adaptive routing, create an Observatory
store, modify providers, add a runtime module, alter the core domain, or turn
candidate objects into classes.
