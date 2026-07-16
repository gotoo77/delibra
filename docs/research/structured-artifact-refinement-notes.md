# Structured Artifact Refinement Notes

## Status

Research notes. Non-normative.

This document is a working notebook for hypotheses that emerged from reviewing
`treasure_hunt_design_selection@0.2.0`. It is not an architecture principle,
ADR, protocol specification, core concept, or implementation plan.

The purpose is to preserve useful research threads without giving them official
status prematurely.

## Starting Point

The 0.2.0 treasure hunt selection protocol produced many traceable artifacts but
did not produce an operationally complete treasure hunt. The final output
remained generic, and the weakness was visible before final synthesis.

The candidate interpretation is:

> The protocol validated artifacts as documents, but did not force models to
> construct and transform a sufficiently concrete business object.

## Candidate Pattern

Working shape:

```text
structured object
  -> situated usage or projection
  -> localized diagnosis
  -> traceable transformation
  -> revised object
  -> situated audit
```

For a single playable puzzle, this could become:

```text
constraint_contract
  -> puzzle_v1
  -> player_simulation
  -> logic_repair
  -> organizer_simulation
  -> installability_repair
  -> adequacy_audit
  -> playable_puzzle_view
```

Important constraint:

> A critique step is useful only if its findings become inputs to an
> identifiable transformation of the object.

Candidate repair contract:

```json
{
  "revised_puzzle": {},
  "blocking_point_resolutions": [
    {
      "blocking_point_id": "bp_1",
      "status": "resolved",
      "changed_fields": ["observable_world", "deduction_rule"],
      "explanation": "..."
    }
  ],
  "unresolved_blocking_points": []
}
```

## Candidate Puzzle Object

Possible fields for a laboratory puzzle object:

```json
{
  "id": "puzzle_1",
  "location": "...",
  "setup": "...",
  "observable_world": [
    {
      "element": "...",
      "exact_content": "...",
      "presentation": "..."
    }
  ],
  "player_actions": ["..."],
  "information_revealed": "...",
  "deduction_rule": {
    "inputs": ["..."],
    "operations": ["..."],
    "uniqueness_argument": "..."
  },
  "expected_reasoning": ["..."],
  "answer": "...",
  "feedback": "...",
  "hint_ladder": ["...", "...", "..."],
  "failure_cases": ["..."],
  "dependencies": ["..."],
  "estimated_difficulty": "..."
}
```

This schema is not proposed as a durable Delibra model. It is only a possible
protocol payload for testing whether structured artifact refinement improves
operability.

## Observation Vocabulary

Candidate vocabulary for experiment notes:

- question;
- scope;
- observation;
- claim;
- evidence;
- assessment;
- interpretation;
- open questions.

This is a vocabulary, not a mandatory template. Different documents may use
different subsets. A simple field note may only need context, observation,
evidence, and open questions. A design review may contain multiple scoped
claims, each with separate evidence.

Do not promote this vocabulary into a formal model until it has proved useful
across independent experiments.

## Applicability Hypothesis

The candidate pattern may be most useful when an artifact has:

- a notion of adequacy that can be tested or simulated;
- an intended use or stakeholder projection;
- defects that can be localized;
- a plausible transformation from defect to revised object;
- an audit that can inspect the relation between diagnosis and transformation.

Likely adapted objects:

- playable puzzle;
- feature specification;
- patch or code review output;
- runbook;
- complex decision candidate.

Objects to test as boundaries:

- incident report;
- root cause analysis;
- strategy option;
- creative brief;
- literary scene;
- forecast or estimate.

Possible failure conditions:

- the object has no clear adequacy criterion;
- the usage cannot be simulated credibly;
- findings are mostly subjective;
- the transformation only rephrases the object;
- the audit reveals no information beyond direct human reading;
- the protocol cost exceeds the additional observations it produces.

## Cost Dimensions To Observe

Do not introduce a formal cost model yet. For experiments, record simple facts:

- number of steps;
- number of artifacts;
- duration;
- largest context pressure if available;
- human inspection burden;
- amount of new actionable information;
- whether the final audit changed the interpretation of the run.

## Candidate Experiment Sequence

1. `playable_puzzle_refinement@0.1.0`

   Test one structured puzzle, not a full treasure hunt.

2. A non-puzzle object from a different class.

   Candidate: `decision_readiness_refinement@0.1.0` or
   `feature_spec_readiness@0.1.0`.

3. A boundary object.

   Candidate: incident report, creative brief, or forecast. The goal is to find
   where the pattern becomes artificial or too costly.

## Open Questions

- Does structured artifact refinement improve operability, or only make failure
  easier to see?
- Can smaller local models perform the repair contracts reliably?
- Does a stronger model make the document-style protocol acceptable, or does the
  structured-object protocol remain useful?
- Which object types naturally support diagnosis-to-transformation linkage?
- When does the protocol cost outweigh its additional observations?
- How many independent contexts are enough before this candidate pattern
  deserves a formal name?

## Puzzle Design Prompt-Only Result

`puzzle_design@0.1.0` through `puzzle_design@0.1.3` tested a smaller artifact
grain: one puzzle instead of a complete treasure hunt.

The smaller grain improved observability but did not by itself make the output
operational. Ollama runs repeatedly converted the request for one playable
puzzle into a castle-wide hunt, multi-step game concept, or prose summary.
Repeated prompt hardening improved the brief and constraint extraction, but did
not reliably force:

- a literal exact answer;
- a physically buildable validation method;
- a single fixed-location puzzle;
- rejection of invented doors, hidden mechanisms, informants, or scattered
  relics;
- `NON_JOUABLE` when the repaired artifact failed the stated quality bar.

The most important negative result came from `puzzle_design@0.1.3`: adding a
separate LLM quality-gate step still produced a false `PASS`. The validation
artifact accepted a puzzle while its own text contained disqualifying evidence,
including a secret door, a "series of puzzles", and a non-exact goal-state
answer.

Interpretation:

> Prompt-only validation can make failure more visible, but it should not be
> trusted as a hard quality gate for operational artifacts.

Candidate next experiment:

Use a structured or deterministic validation layer outside the LLM response.
For example, require machine-checkable fields for `answer`, `validation_method`,
`scope`, `materials`, and `forbidden_mechanisms`, then reject outputs that
contain known disqualifying patterns or missing fields before final synthesis.

Experiment note: the Ollama model used in these runs is not recoverable from
`run.json` or `trace.json`; the CLI resolves it from `OLLAMA_MODEL`, and Delibra
keeps provider/model metadata outside durable artifacts by design.

## Domain-Specific Validation Boundary

The current `puzzle_spec` work is an experimental pilot for validating
domain-specific structured artifacts. It is not a proposal to make Delibra a
puzzle-design system, and it is not an accepted runtime architecture decision.

The puzzle is the instrument of the experiment, not the abstraction.

Context:

- real provider outputs violated explicit puzzle-design constraints while still
  producing plausible prose;
- `validate_puzzle_spec` now rejects those failures deterministically;
- `delibra validate-puzzle-spec` exposes that boundary as a public, scriptable
  CLI without invoking an LLM or changing runtime core.

Experimental pipeline under investigation:

```text
provider output
  -> strict structured extraction
  -> contract-specific validation
  -> stable validation report
  -> promotion or explicit stop
```

Ownership boundary:

- Delibra core may transport artifacts, payloads, artifact identity,
  provenance, declared output kinds, and perhaps generic validation outcomes if
  future evidence justifies them.
- Delibra core must not contain puzzle-specific semantics or rules.
- The application or domain layer owns contracts such as `puzzle_spec`,
  extraction policy for those contracts, validators, domain error codes, and
  promotion criteria derived from domain validation.

Rules such as `ANSWER_NOT_EXPLICIT` and
`VALIDATION_METHOD_NOT_BUILDABLE` are application-owned. They should not move
into the runtime core merely because the puzzle experiment needs them.

Questions this experiment may inform:

- How is a provider payload converted into a strict structured document?
- How are extraction failures distinguished from contract violations?
- Should rejected candidates remain durable artifacts?
- How is validation provenance represented?
- What prevents an invalid candidate from being promoted?
- Is a generic validation result contract eventually justified?

Non-goals for the next tranche:

- generic artifact validation;
- a runtime validator registry;
- a new `StepKind`;
- tolerant extraction from prose;
- automatic repair loops;
- promotion after extraction failure;
- treating all artifact quality as deterministically measurable.

Next experimental tranche:

Use `puzzle_spec` as a pilot for validating domain-specific structured artifacts
extracted from provider payloads.

Expected outcomes:

- strict JSON plus valid `puzzle_spec` produces an accepted candidate;
- strict JSON plus invalid `puzzle_spec` produces a stable invalid validation
  report;
- invalid JSON content produces a distinct extraction error report.

## Puzzle Spec Payload Extraction Result

The first local extraction tranche added `extract_puzzle_spec(payload)` and
`evaluate_puzzle_spec_payload(payload)` in the application layer.

The accepted input shape is intentionally minimal:

```json
{
  "content": "{\"scope\":\"single_fixed_spot\", ...}"
}
```

The implementation distinguishes three local outcomes:

- `extraction_error`: `payload.content` could not be converted into a strict
  JSON document;
- `invalid`: strict JSON was extracted, but `validate_puzzle_spec` rejected the
  document;
- `accepted`: strict JSON was extracted and accepted as an `accepted_puzzle_spec`.

Observed as puzzle-specific:

- the required `puzzle_spec` fields;
- the domain error codes such as `ANSWER_NOT_EXPLICIT`;
- the disqualifying puzzle-design phrases and validation-method patterns.

Observed as potentially domain-independent:

- extraction failure and contract violation are different outcomes;
- validation should not run after extraction failure;
- the accepted document can remain a local application result rather than a
  durable runtime artifact;
- stable status labels make the result easier to test and eventually render.

Still ambiguous:

- whether invalid candidates should become durable artifacts;
- whether validation provenance needs validator id, validator version, or both;
- whether a future promotion step belongs in the application layer, protocol
  layer, or runtime;
- whether other domains need warnings or partial acceptance in addition to
  valid/invalid.

Deliberately not generalized:

- no generic artifact validator interface;
- no runtime validator registry;
- no new `StepKind`;
- no durable `accepted_artifact` or `rejected_artifact` model;
- no tolerant extraction from prose;
- no repair or retry loop.
