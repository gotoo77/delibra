# Decision Record Validation Framing

## Status

Experimental framing. Not an architecture decision, protocol specification, or
template for future experiments.

This document frames a possible second structured-artifact validation
experiment. It should be read as a counter-test to the `puzzle_spec` experiment,
not as a proposal for a generic validation architecture.

## Question

Which responsibilities emerge when refining a `decision_record` extracted from
provider output, and how do they compare with the observations from
`puzzle_spec`?

The goal is not to force the same pipeline to reappear. The goal is to observe
what the domain actually requires, then compare those observations with the
previous experiment.

## Why This Domain

`decision_record` differs from `puzzle_spec` in ways that make it a useful
counter-test:

- it has no puzzle-like exact answer;
- validation likely mixes deterministic structure and qualitative coherence;
- passing validation may not imply acceptance;
- the artifact represents a reasoned decision, not a puzzle solution;
- promotion may require policy or human judgment rather than contract
  conformance alone.

These differences make the domain suitable for testing whether the
responsibilities observed in `puzzle_spec` were domain-specific or part of a
broader pattern.

## Expected Differences

Unlike `puzzle_spec`, this experiment is expected to differ in several ways.
These differences are desirable because they increase the experiment's ability
to falsify conclusions drawn from the previous domain.

Possible differences include:

- validation may produce warnings rather than binary outcomes;
- structural validity may not imply acceptance;
- acceptance may require policy or human judgment;
- qualitative assessment may remain outside deterministic validation;
- missing information may be more important than forbidden content;
- several independent checks may be needed before a decision can be considered
  ready.

## Hypothesis

A `decision_record` can be validated locally for structural contract
violations, but the experiment may show that validation and acceptance must
remain separate.

This hypothesis should be treated as falsifiable. If the domain does not fit
extraction, validation, report, and promotion responsibilities naturally, that
is useful evidence rather than a failed implementation.

## Local Contract

The local contract is deliberately application-owned and still open.

Candidate fields may include:

- decision;
- status;
- options_considered;
- reasons;
- consequences;
- uncertainties;
- evidence_refs;
- owner_or_reviewer;

The contract should start small. It should not attempt to encode all decision
quality.

## Success Criteria

- A valid `decision_record` can be identified as structurally valid.
- An invalid `decision_record` can be rejected or warned with stable codes.
- Extraction errors are distinguished from contract violations.
- The experiment records what appears domain-specific versus potentially
  domain-independent.
- The result can be compared directly with the `puzzle_spec` review.

## Non-Goals

- no generic validator abstraction;
- no runtime validator registry;
- no new `StepKind`;
- no claim that decision quality is fully deterministic;
- no automatic promotion to accepted decision;
- no official experiment template;
- no new documentary category;
- no claim that `decision_record` should enter Delibra core.

## What Would Invalidate The Hypothesis

- The domain does not fit extraction, validation, and report responsibilities at
  all.
- Validation mostly becomes subjective prose review.
- Warnings or partial states dominate binary valid/invalid outcomes.
- Acceptance clearly requires a separate human or policy step.
- The useful checks are too domain-specific to suggest any shared lifecycle.

## Evidence Expected

This experiment should not conclude that a generic validation architecture is
needed.

Instead, it should produce evidence that can later be compared with other
independent experiments.

Particular attention should be paid to:

- recurring responsibilities;
- recurring lifecycle transitions;
- recurring provenance requirements;
- recurring failure categories;
- genuinely domain-specific behavior;
- places where `decision_record` diverges from `puzzle_spec`.

## Architectural Pressure

Architectural pressure exists when multiple independent experiments repeatedly
require the same responsibility, and keeping separate implementations becomes
more costly than introducing a shared abstraction.

This experiment should look for that pressure without assuming it exists.

## Method Note

The emerging experimental method is also not yet an official Delibra principle.

If several independent experiments naturally produce the same sequence of
framing, local implementation, observation, review, and decision, that may
eventually justify documenting a general method. Until then, the method should
remain observed practice rather than declared process.
