# Treasure Hunt Selection 0.2.0 Protocol Review

## Status

This document is an engineering review, not an accepted architecture decision.

It records what the `treasure_hunt_design_selection@0.2.0` experiment appears
to show about Delibra protocol design. It should not be read as approval to add
runtime primitives, core entities, artifact mutation semantics, or a new
Observatory model.

## Scope

Evidence reviewed:

- protocol: `presets/treasure_hunt_design_selection-0.2.0.yaml`
- run: `experiments/local/mistral2/run.json`
- trace: `experiments/local/mistral2/trace.json`
- comparison notes: `observations/0001-treasure-hunt-baseline/notes.md`
- comparison notes: `observations/0002-treasure-hunt-selection/notes.md`

The 0.2.0 run completed on 2026-07-16 with:

- status: `completed`
- artifacts: 20
- trace events: 102
- duration: approximately 349 seconds

The persisted run does not store provider/model metadata. The directory name
and surrounding experiment context suggest a local Mistral/Ollama run, but this
review treats the run artifact and trace as the durable evidence.

## Question

What did `treasure_hunt_design_selection@0.2.0` demonstrate about protocol
design in Delibra?

## Observations

The protocol became substantially more rigorous than the baseline. It added
constraint extraction, design selection, audits, validated design material, a
draft, final review, and final synthesis while still using the existing runtime
primitives: `prompt`, `fanout`, `criticize`, and `synthesize`.

The runtime executed the protocol successfully. The run and trace preserve the
derivation chain across 20 artifacts and 102 trace events.

The final artifact was not operationally useful as a treasure hunt design. It
summarized eight generic puzzle prompts such as looking for a statue that tells
the castle's story, finding figures in a grand hall, or connecting the dots in
the final enigma. It did not provide concrete puzzle mechanics that an organizer
could run without inventing most of the game.

The weakness appears before final synthesis. The `select_design_material`
artifact already contains broad scene labels, generic hints, and high-level
puzzle descriptions. Later audit and review artifacts largely repeat or certify
that material instead of failing it for missing playable mechanisms.

The `prepare_validated_material` artifact wraps prior selection and audit
artifacts rather than producing a repaired, field-level validated puzzle object.
The `draft_final` artifact explicitly says details are omitted due to space
constraints while still listing the same generic puzzle material.

The final review reports `PASS`, no violations, and no unsupported additions,
despite the design remaining under-specified from an organizer's perspective.

## Claims

### Claim 1: 0.2.0 validated traceability more than artifact adequacy.

Evidence:

- the run completed with 20 artifacts and 102 trace events;
- the derivation chain is inspectable across selection, audit, validation,
  draft, review, and final synthesis;
- the final artifact remains too generic to operate as a playable game.

Assessment:

The evidence is direct for this run. It does not prove that the same protocol
would fail with every provider/model configuration.

### Claim 2: the main artifact-quality failure began before final synthesis.

Evidence:

- `artifact_0012` (`select_design_material`) already contains generic puzzle
  descriptions and hint slogans;
- `artifact_0015` (`validated_design_material`) mainly packages prior
  artifacts instead of repairing weak material;
- `artifact_0016` (`final_draft`) states that details are omitted due to space
  constraints and repeats the generic puzzle structure;
- `artifact_0020` (`final_synthesis`) compresses the same weak material.

Assessment:

This is strongly supported for the inspected run. The final synthesis degraded
the presentation, but it inherited an already insufficient object.

### Claim 3: the protocol formed a confirmation pipeline around insufficiently
concrete material.

Evidence:

- selection chose broad puzzle descriptions;
- constraint and provenance audits did not fail the missing mechanics;
- validation preserved the selected material;
- final review reported `PASS`;
- final synthesis returned a compliant-looking but non-operational design.

Assessment:

This claim is supported for this run. It is a protocol-behavior observation, not
a global claim about all review or audit stages.

### Claim 4: this experiment does not prove that the runtime needs new
primitives.

Evidence:

- every step executed using the existing primitives;
- the observed failure can be explained by protocol contracts that do not force
  concrete artifact transformation;
- the runtime already transports opaque JSON artifacts, so a protocol can test
  structured puzzle objects without runtime changes.

Assessment:

The evidence supports protocol-first experimentation. Runtime changes may still
be justified later, but this run does not create that pressure by itself.

## Experimental Interpretation

The protocol describes many review and validation activities, but it does not
define a sufficiently concrete business object for those activities to improve.
In practice, a puzzle is treated as text with a title, location, hint, and
solution-like phrase. The protocol never forces fields such as observable world,
player action, deduction rule, feedback, failure cases, or dependencies to be
complete and testable.

The observations suggest the following protocol hypothesis:

> In this experiment, the protocol did not make the puzzle object explicit
> enough for missing mechanics to become observable failures.

The next experiment should therefore focus on artifact adequacy, not on adding
more reviewers.

## Candidate Next Experiment

Create a small laboratory protocol before attempting another full treasure hunt
variant:

```text
playable_puzzle_refinement@0.1.0
```

Experimental question:

> Can a protocol based on one structured puzzle object, usage simulations, and
> mandatory repairs increase puzzle operability without runtime changes?

Candidate flow:

```text
extract_constraints
  -> draft_puzzle_object
  -> simulate_player_attempt
  -> repair_logic_from_attempt
  -> simulate_organizer_installation
  -> repair_installability
  -> adequacy_audit
  -> render_playable_puzzle
```

The final render should be intentionally non-creative. It should format the
accepted object and should not add mechanisms, repair gaps, or hide remaining
insufficiencies.

## Limits

This review is based on one 0.2.0 run and earlier 0.1.0 comparison notes. It
does not establish a general law about Mistral, Ollama, puzzle design, or
multi-step protocols.

The review also does not prove that structured artifacts will solve the problem.
It only identifies a narrower, cheaper, and more falsifiable next experiment
than changing the runtime.

## Open Questions

This review leaves several questions intentionally unresolved.

- Would the same protocol behave differently with a stronger model?
- Would structured puzzle objects improve operability?
- Would usage simulations produce more actionable repairs?
- Does this protocol shape generalize beyond puzzle design?
