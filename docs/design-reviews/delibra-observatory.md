# Delibra Observatory Design Review

## Status

This document is a design review, not an accepted architecture decision.

It records a target direction, evidence, candidate concepts, risks, and open
questions for a possible future Delibra Observatory module. It is structured and
non-normative. Normative decisions must be accepted separately through ADRs,
architecture documentation, or implementation work.

No Observatory module exists yet. This review should not be read as approval to
create a new subsystem, directory, data model, CLI surface, or persistence
format.

## Evidence So Far

This review is grounded in two field notes, not in a broad experimental corpus.

- [Field Note 0006](../field-notes/0006-local-ollama-decision-review-qualification.md)
  records a single-run experimental qualification of `decision_review@0.1.0`
  with `ollama` / `qwen3:4b`.
- [Field Note 0007](../field-notes/0007-comparative-decision-review-model-qualification.md)
  records a comparative qualification across two provider/model configurations
  using the same protocol and same input.

Those notes show that completed Delibra runs can be inspected not only for their
domain output, but also for protocol behavior: grounding, provenance,
epistemic-status preservation, role behavior, and comparative differences across
configurations.

They do not establish general laws about providers, models, or protocols.

## Module Identity

Delibra Observatory is a possible future module for recording, comparing, and
qualifying observed behavior from completed Delibra runs.

Its subject is not the user's original decision or domain task. Its subject is:

> How did a Delibra protocol behave in a completed run, and what evidence
> supports that assessment?

The module would help turn completed runs into inspectable experimental
evidence while preserving the difference between:

- a run artifact;
- an observation about that artifact;
- a qualification judgment;
- a comparison across runs;
- durable knowledge that may or may not later deserve promotion.

## Problem Statement

Delibra currently produces durable run artifacts and traces. Users can inspect
and analyze runs, and they can manually write field notes. This works for a
small number of experiments, but it becomes fragile as soon as the project asks
questions such as:

- Did this protocol preserve uncertainty?
- Did a role invent evidence?
- Did the critique step challenge or launder prior claims?
- Did the same prompt behave differently across provider/model configurations?
- Which claims in the final synthesis came from user input, earlier artifacts,
  generated assumptions, or nowhere observable?
- Are repeated observations strong enough to justify a design change, ADR,
  field-note pattern, or Knowledge Vault candidate?

The Observatory problem is therefore not "store more reports". The problem is
to make protocol behavior observable, comparable, and qualified without turning
generated judgments into false authority.

## Boundaries

### Runtime

The runtime executes protocols and writes run, trace, and artifact data. It
should remain boring and deterministic in its responsibilities.

Observatory should not alter protocol execution, provider calls, artifact
creation, scheduling, retries, budgets, or trace semantics. It should consume
completed runs after the fact.

### `analyze-run`

`analyze-run` summarizes mechanical run metadata such as duration, artifacts,
trace events, and policy information.

Observatory would sit above that level. It may reuse runtime metadata, but its
focus is behavioral qualification: provenance, epistemic drift, role behavior,
claim transformation, and cross-run comparison.

`analyze-run` answers "what happened mechanically?" Observatory would ask "what
does the observed behavior imply about protocol qualification?"

### Field Notes

Field notes are human-readable records of observed usage evidence. They remain
the current documentation surface for experimental qualification.

Observatory should not replace field notes immediately. In the smallest viable
form, it may help produce evidence that a human later records as a field note.
Field Note 0006 and Field Note 0007 are evidence that the field-note structure
can absorb early Observatory-style work.

### Knowledge Vault

Knowledge Vault is for durable knowledge that has survived review and is useful
beyond one local project context.

Observatory output should not be promoted automatically into Knowledge Vault.
It should produce evidence and candidate patterns. Promotion requires human
review and convergence across independent experiments.

## Non-Goals

- Do not judge whether a model is globally good or bad.
- Do not rank providers.
- Do not infer causality from one or two runs.
- Do not decide business strategy from generated artifacts.
- Do not replace human review.
- Do not turn a field note into an automatic truth source.
- Do not mutate run artifacts or traces.
- Do not create a general analytics warehouse.
- Do not introduce a new protocol execution engine.
- Do not require changes to presets before the observed failure mode is better
  understood.

## Candidate Domain Objects

### Experiment

An Experiment is a bounded observation context around one or more completed
runs.

Candidate fields:

- experiment id;
- protocol id and version;
- input identity or digest;
- provider/model/runtime configuration;
- run and trace references;
- execution status;
- declared qualification question;
- evidence sources;
- reviewer or capture metadata.

Example from 0006: one run of `decision_review@0.1.0` with `qwen3:4b` asking
whether the output remained grounded.

Example from 0007: two runs with identical protocol/input and different
provider/model configurations.

### Observation

An Observation is a factual statement anchored to evidence.

Candidate fields:

- observation id;
- source run;
- source artifact or trace event;
- step and role;
- excerpt or structured pointer;
- observed phenomenon;
- confidence in extraction;
- reviewer status.

Observations should be as close to the artifacts as possible. For example:
`artifact_0004` introduced "Confidence: 92%" is an observation; "the model is
unreliable" is not.

### Qualification

A Qualification is a scoped judgment about whether a run or configuration met a
defined behavioral bar.

Candidate fields:

- qualification target;
- qualification question;
- result, such as pass, fail, mixed, or indeterminate;
- scope;
- supporting observations;
- limitations;
- reviewer status.

Example from 0006: runtime execution passed, but grounding and cross-artifact
epistemic-status preservation failed for that configuration.

### Comparison

A Comparison is a relation across experiments or runs.

Candidate fields:

- compared experiments or runs;
- controlled dimensions;
- changed dimensions;
- phenomena compared;
- statuses such as disappeared, weakened, remained, newly appeared;
- limitations and uncontrolled variables.

Example from 0007: same protocol/input, different provider/model; authority
fabrication disappeared in the second inspected run, while scenario elaboration
remained.

## Minimal Workflow

1. Execute one or more Delibra runs normally.
2. Preserve run and trace files.
3. Select a qualification question, such as "did the synthesis preserve claim
   provenance?"
4. Extract observations from artifacts and trace metadata.
5. Classify observations by source, step, role, and phenomenon.
6. Produce a scoped qualification or comparison.
7. Human reviewer checks excerpts and conclusions.
8. Save the result as a field note or future Observatory artifact.
9. Optionally identify candidate patterns for later review.
10. Promote only repeated, reviewed, durable findings into Knowledge Vault.

## Manual vs Derivable

### Derivable

- run status;
- protocol id and version;
- artifact count;
- trace event count;
- step and role producing each artifact;
- artifact text;
- timestamps and durations where available;
- identical or different input text;
- exact phrase occurrence and first appearance;
- basic cross-artifact claim propagation.

### Manual or Review-Required

- whether a claim is unsupported;
- whether a transformation is epistemic drift or harmless paraphrase;
- whether a comparison is meaningful;
- whether a qualification should pass, fail, or remain indeterminate;
- whether a repeated pattern deserves architectural action;
- whether evidence is strong enough for Knowledge Vault promotion.

The boundary matters: Delibra can help extract and organize evidence, but it
should not grant authority to its own generated judgments without review.

## Persistence Options

### Option A -- Field Notes Only

Continue using Markdown field notes. Observatory remains a practice, not a
module.

Pros:

- no new architecture;
- easy to review;
- compatible with current conventions.

Cons:

- hard to query;
- comparisons become manual;
- repeated phenomena are difficult to aggregate.

### Option B -- Structured Sidecar Files

Store structured experiment, observation, qualification, and comparison data as
JSON or YAML sidecars next to field notes or run outputs.

Pros:

- machine-readable;
- diffable;
- incremental path from current practice.

Cons:

- creates a new persistence surface;
- requires schema governance;
- may tempt premature automation.

### Option C -- Dedicated Observatory Store

Create a dedicated persistence layer for experiments and comparisons.

Pros:

- queryable corpus;
- better for many runs;
- supports dashboards or longitudinal studies.

Cons:

- too early based on only 0006 and 0007;
- high risk of overbuilding;
- could blur the boundary between evidence and authority.

Current recommendation: stay with Option A until more comparative notes exist.
Design Option B only when repeated manual extraction becomes a proven friction.

## Provenance Requirements

Any Observatory output must preserve:

- run file reference;
- trace file reference;
- protocol id and version;
- input identity or digest;
- provider/model/runtime configuration;
- artifact id;
- step and role;
- exact or closely paraphrased source formulation;
- reviewer status;
- distinction between observed fact, interpretation, hypothesis, and
  qualification judgment.

For comparisons, it must also preserve:

- controlled dimensions;
- changed dimensions;
- uncontrolled variables;
- compared phenomena;
- whether a phenomenon disappeared, weakened, remained, or newly appeared.

## Risks

### Self-Evaluation

Delibra may use LLM-generated artifacts to evaluate LLM-generated artifacts.
Without guardrails, this can create a closed loop where generated claims become
generated evidence.

Mitigation: require source pointers, excerpts, and human review for
qualification judgments.

### False Authority

A structured Observatory report may look authoritative even when based on one
run or weak evidence.

Mitigation: include scope, evidence level, and review status in every output.

### Taxonomy Creep

The project may invent new document types before repeated evidence justifies
them.

Mitigation: keep 0006 and 0007 as field notes for now. Revisit taxonomy only
after multiple comparative qualifications create real pressure.

### Model Ranking

Comparative runs can be misread as model leaderboards.

Mitigation: compare behaviors under scoped configurations. Do not rank models
or infer global provider quality.

### Causality Errors

If provider, model, settings, runtime behavior, and prompt handling all differ,
the comparison cannot identify cause.

Mitigation: record controlled and uncontrolled variables explicitly.

## Smallest Viable Implementation Tranche

Do not implement this yet. If implementation becomes justified, the smallest
viable tranche should be deliberately narrow:

1. Read two completed `run.json` / `trace.json` pairs.
2. Verify same protocol id/version and same input content or digest.
3. Produce a mechanical comparison skeleton:
   - run status;
   - artifact count;
   - trace event count;
   - step/role artifact map;
   - controlled and changed dimensions.
4. Optionally search for reviewer-provided claim strings across artifacts.
5. Emit a Markdown draft with empty review-required sections for observations,
   hypotheses, and qualification verdict.

This tranche should not attempt automatic semantic judgment. It should reduce
manual friction while keeping qualification human-reviewed.

## Open Questions

- Is Observatory a CLI command, application service, library module, or
  documentation workflow first?
- Should Observatory outputs be persisted next to runs, field notes, or in a
  dedicated store?
- What is the minimum schema for Experiment, Observation, Qualification, and
  Comparison?
- Should artifact excerpts be copied into Observatory outputs or referenced by
  pointer only?
- How should reviewers mark confidence, status, and review completion?
- Should claim extraction be manual, rule-based, LLM-assisted, or hybrid?
- What threshold justifies promotion from field notes to Knowledge Vault?
- What threshold justifies an ADR for Observatory persistence?
- How should Observatory avoid becoming a model-ranking system?
- How should it handle sensitive or private run contents?

## Candidate ADRs

No ADR should be created yet. Candidate future decisions include:

- Observatory persistence boundary: Markdown-only, sidecar files, or dedicated
  store.
- Observatory command surface: whether it belongs under `delibra analyze`,
  `delibra observe`, or another namespace.
- Review status model for generated observations and qualifications.
- Durable boundary between field notes, Observatory records, and Knowledge
  Vault captures.

## Current Recommendation

Keep the current repository structure:

- 0006 remains a single-run experimental qualification field note.
- 0007 remains a comparative qualification field note.
- This document remains a design review.
- No Observatory subsystem directory is created yet.
- No code is implemented yet.

The next evidence threshold should be practical friction: if another comparative
qualification requires repeated manual extraction of the same metadata and
claim-provenance structure, then a small mechanical comparison helper may be
worth designing.
