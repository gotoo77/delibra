# Field Note -- Abstraction Promotion Observation

## Date

2026-07-16

## Type

methodological_observation

## Scope

This note covers a discussion following the
`treasure_hunt_design_selection@0.2.0` experiment and related Delibra
architecture reviews. It is not a protocol result, ADR, or accepted principle.

## Context

The 0.2.0 treasure hunt selection protocol produced a traceable but weak final
artifact. The subsequent review considered several possible abstractions:

- a runtime primitive for mutation or refinement;
- a structured artifact refinement pattern;
- an `observation_record` artifact;
- a `Claim` / `Evidence` model;
- a stricter template for future field notes and reviews.

Each candidate was deliberately kept outside the core architecture while a
cheaper protocol-level experiment remains available.

## Observation

Across this discussion and prior Delibra design work, candidate abstractions
were repeatedly left at the experimental or documentary level when the evidence
was still local:

- `Claim`, `Evidence`, `Critique`, and `Decision` remain rejected for v0.1 core
  in `docs/concepts/claim-model.md`;
- mutation-style behavior is being considered as protocol structure before any
  runtime primitive;
- observation vocabulary is being treated as a writing aid rather than a new
  artifact type or mandatory template;
- the next proposed test is a small laboratory protocol, not a new core model.

## Claim

Architectural abstractions in Delibra appear to be safer when they are promoted
only after they have proved useful, stable, and difficult to replace across
multiple independent contexts.

## Evidence

- ADR-0001 already requires core growth to be justified by multiple unrelated
  protocols and by failure to fit cleanly outside the core.
- The claim model remains a concept note with explicit `wait` status.
- The 0.2.0 failure can be investigated through a structured protocol without
  runtime changes.
- The observation vocabulary discussed after the run can live in reviews and
  field notes before becoming a formal model.

## Assessment

The evidence is methodological and local to Delibra. It is strong enough to
guide caution in upcoming experiments, but not strong enough to promote a new
architecture principle.

This should be treated as a candidate discipline:

> Experimental abstractions are encouraged. Architectural abstractions should be
> promoted only after they survive multiple independent contexts.

## Interpretation

Delibra may benefit from making abstraction promotion itself evidence-driven.
The immediate consequence is negative: do not add new runtime primitives,
official observation records, or a claim model solely because they seem useful
after one experiment.

## Open Questions

- Does this discipline remain useful outside treasure-hunt protocols?
- Which future experiments count as independent contexts?
- When does a repeated documentary convention deserve a named concept?
- How much evidence is enough for a concept note, an ADR, or a core model
  change?

## Decision

wait

## Follow-Up

- Run a small `playable_puzzle_refinement@0.1.0` experiment before changing the
  runtime.
- Apply the same observation discipline to at least one non-puzzle context
  before promoting a general refinement pattern.

