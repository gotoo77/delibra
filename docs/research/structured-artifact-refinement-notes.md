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
