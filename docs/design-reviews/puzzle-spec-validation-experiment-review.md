# Puzzle Spec Validation Experiment Review

## Status

This document is an engineering review, not an accepted architecture decision.

It records what the `puzzle_spec` validation experiment appears to demonstrate
about artifact quality in Delibra. It should not be read as approval to add a
generic validation runtime, validator registry, new `StepKind`, or durable
candidate/accepted/rejected artifact lifecycle.

## Scope

Evidence reviewed:

- `presets/puzzle_design.yaml`
- `docs/field-notes/0009-puzzle-design-quality-gate-ollama.md`
- `docs/research/structured-artifact-refinement-notes.md`
- `src/delibra/app/puzzle_spec.py`
- `tests/test_app_puzzle_spec.py`
- `src/delibra/cli.py`
- `tests/test_cli.py`

Relevant commits:

- `3cbb652` Reject invalid puzzle specifications deterministically
- `e51c362` Add CLI validation for puzzle spec JSON
- `400b758` Document domain-specific validation boundary
- `1e6ff6d` Evaluate puzzle spec provider payloads

## Question

What did the `puzzle_spec` experiment actually demonstrate, what did it
disprove, and what remains open?

## Summary

The experiment demonstrated that, in at least one domain, deterministic
application-level validation can objectively improve artifact quality by
rejecting outputs that previously looked plausible but were outside contract.

It did not demonstrate that Delibra needs a generic artifact validation
architecture. The puzzle is the experimental instrument, not the abstraction.

The deeper observation is that a structured provider output may need to pass
through local states before it is safe to render or promote:

```text
provider output
  -> candidate document
  -> extraction
  -> validation
  -> validated or rejected local result
```

This is an observation from one domain, not yet a core lifecycle.

## What Was Demonstrated

### 1. Some artifact-quality failures are objectively rejectable.

The observed Ollama outputs for `puzzle_design` failed deterministic criteria:

- answer expressed as a goal state rather than an exact solution;
- validation by unsupported doors or hidden mechanisms;
- castle-wide search or multi-puzzle language where one fixed-location puzzle
  was required;
- missing declared forbidden mechanisms;
- player-separation or scope drift.

These failures can be detected without asking an LLM to judge itself.

### 2. A local application validator can improve quality without core changes.

`validate_puzzle_spec` lives in `delibra.app`, not in core or runtime. It returns
stable error codes and all detectable violations. The CLI boundary makes the
contract scriptable:

```text
0: valid document
1: readable document rejected by domain validation
2: input or parsing failure
```

This improved quality control without adding a runtime primitive.

### 3. Extraction failure and contract violation are distinct.

`extract_puzzle_spec(payload)` treats `payload.content` as strict JSON. It
separates:

- `EXTRACTION_PAYLOAD_NOT_OBJECT`
- `EXTRACTION_CONTENT_MISSING`
- `EXTRACTION_CONTENT_NOT_STRING`
- `EXTRACTION_INVALID_JSON`

from domain validation errors such as `ANSWER_NOT_EXPLICIT`.

Validation does not run after extraction failure. That separation is likely
important beyond puzzles, but it has only been observed in this one domain so
far.

### 4. The experiment produced testable regression fixtures.

The previously manual judgments about `ollama_002`, `ollama_003`, and
`ollama_004` now correspond to tested invalid cases. A valid fixture protects
against a validator that rejects everything.

## What Was Disproved

### 1. Prompt-only quality gates are insufficient for hard acceptance criteria.

`puzzle_design@0.1.3` added an LLM quality-gate step. The model still produced
a false `PASS` while its own text contained disqualifying evidence, including a
secret door, a series of puzzles, and a non-exact answer.

### 2. More protocol roles do not automatically improve artifact adequacy.

The earlier treasure-hunt and puzzle-design runs improved traceability and
surface structure, but they did not reliably produce operational artifacts.
Review and validation roles often summarized, certified, or transformed weak
material instead of rejecting it.

### 3. Smaller artifact grain is helpful but not sufficient.

Moving from "design a whole game" to "design one puzzle" made failures easier
to observe. It did not by itself force exact answers, buildable validation, or
explicit rejection.

## Still Open

- Whether invalid candidates should become durable artifacts.
- Whether validation provenance needs validator id, validator version, input
  artifact id, or all of them.
- Whether "validated" and "accepted" are separate states.
- Whether promotion belongs in application code, protocol conventions, runtime,
  or a later product layer.
- Whether other domains need warnings, partial acceptance, or multiple
  validators.
- Whether strict JSON extraction is enough, or whether some domains need a
  different structured-output boundary.
- Whether the same extraction/validation/report/promotion pattern appears in a
  second, sufficiently different domain.

## Validated vs Accepted

The current local result uses `accepted_puzzle_spec` for a document that passed
extraction and validation. That name is acceptable for this local tranche, but
it may hide a future distinction.

Validation describes a fact about contract conformance. Acceptance may describe
a decision to promote, publish, persist, or use the document. A future domain
could plausibly produce:

```text
validated document
  -> human review
  -> accepted or rejected
```

or:

```text
validated document
  -> budget or policy check
  -> accepted or rejected
```

This experiment suggests the distinction should be watched. It does not yet
justify a generic lifecycle model.

## Architecture Reading

The experiment supports this methodological rule:

> Do not generalize from one case. Do not ignore a form repeated across several
> independent cases.

For now:

- `puzzle_spec` remains application-owned;
- puzzle semantics remain outside runtime core;
- extraction and validation are local functions;
- the CLI is a public boundary for the experiment, not a core model change.

If a second domain naturally produces the same shape, the architectural pressure
will be stronger. If it produces a different shape, the puzzle experiment will
have usefully bounded the abstraction.

## Candidate Counter-Test

The next domain should be different enough to challenge the hypothesis.

`decision_record` is a strong candidate because it may have deterministic
requirements such as explicit decision, options considered, reasons,
consequences, uncertainty, and status, but it does not have a puzzle-like exact
answer.

The counter-test should ask whether the same broad shape appears naturally:

```text
provider output
  -> strict extraction
  -> contract validation
  -> stable report
  -> block or promote
```

It should also record divergences, such as partial acceptance, warnings,
multiple validators, non-provider inputs, or human approval after validation.

## Non-Goals

This review does not recommend:

- a generic artifact validator;
- a runtime validator registry;
- a new `StepKind`;
- durable candidate/validated/accepted/rejected artifact states;
- automatic repair loops;
- tolerant prose parsing;
- moving puzzle-specific codes into core.

## Conclusion

The `puzzle_spec` experiment is the first evidence that Delibra can improve
artifact quality through executable, deterministic rejection rather than only
through richer prompting or more review roles.

That is a real quality improvement. It is not yet a runtime architecture.
