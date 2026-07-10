# Observation 0002 - Treasure Hunt Selection

## Hypothesis

Adding a selection/compression step before final synthesis reduces final-step
context pressure while preserving the strongest ideas and critiques.

## Mechanical validation

- Protocol validates.
- Runtime completes.
- Trace and analysis are produced.
- Existing runtime primitives only: prompt, fanout, criticize, synthesize.
- No runtime feature was added.
- The selection step is `kind: prompt`, because v0.1 keeps `synthesize` as the
  final step only.

## Real-provider comparison

Baseline:
- protocol: treasure_hunt_design@0.1.0
- provider: OpenAI
- model: gpt-4.1-mini
- artifacts: 11
- final artifact: artifact_0011
- final output chars: 3064
- final OpenAI input tokens observed externally: 11,201

Selection variant:
- protocol: treasure_hunt_design_selection@0.1.0
- provider: OpenAI
- model: gpt-4.1-mini
- artifacts: 12
- selection artifact: artifact_0011
- final artifact: artifact_0012
- final output chars: 3478
- final OpenAI input tokens: not captured in durable run/trace data

## Context pressure

`analyze-run` reports deterministic upper-bound context estimates over persisted
artifacts:

- 0001 largest pre-call context upper bound: 39,518 chars before artifact_0011
- 0002 largest pre-call context upper bound: 42,180 chars before artifact_0012

This upper-bound metric does not yet account for the final step's declared
resolved inputs. The trace is more useful for this experiment:

- 0001 final declared inputs: user_input, game_dna, design_views, design_critiques
- 0001 final resolved artifacts: 10
- 0001 final resolved artifact JSON chars: 39,195
- 0002 final declared inputs: game_dna, selected_design_material
- 0002 final resolved artifacts: 2
- 0002 final resolved artifact JSON chars: 6,165

Result: the protocol change strongly reduces the material intentionally fed to
the final step, even though the current `analyze-run` upper-bound metric does
not show that reduction.

Measurement note:
- This observation introduced [M001](../../docs/measurement-notes.md): whenever
  trace data exposes the variable under test directly, prefer it over whole-run
  proxy metrics. Proxy metrics should be explicitly labeled as proxies.

## Selection artifact

The selection artifact preserves the important critique categories:

- dead-end risk from weak cross-room links
- opaque Latin, cipher, and heraldry assumptions
- linear dependency blocking risk
- need for explicit observation/manipulation cues
- plausible physical interactions only
- difficulty balancing for motivated adults
- foreshadowing the narrative twist
- cooperation encouraged but not mandatory

It also identifies novelty opportunities:

- castle architecture as a meta-puzzle
- light and shadow effects
- mixed visual, tactile, and logical puzzle types
- layered in-world documents and marginalia
- progression from recognition to integration
- narrative breadcrumbs that reward replay

## Final artifact

The final synthesis is structured and concrete at the beginning: game DNA,
narrative vision, and an 8-step spatial map are present. The output appears more
directly guided by the selected material than the baseline.

However, the final artifact is truncated before completing all required
sections. It reaches the step map and stops in the final row. Required sections
such as detailed main puzzles, progressive hints, expected solutions, blocking
risks, false leads, solvability verification, memorable emergent property, and
limitations are not present in the persisted final artifact.

## Observations

- Context pressure before the final step is reduced in the resolved-input sense.
- Useful critiques are preserved in the selection artifact.
- Novelty opportunities are preserved in the selection artifact.
- The final output starts more concretely but does not complete the requested
  structure.
- Information may not be lost during selection; the larger issue is output
  budget or final instruction pressure.

## Conclusion

Partially supported.

The experiment supports the architectural hypothesis that protocol design can
reduce final-step context pressure without changing the runtime. It also shows
that a selection artifact can preserve critique and novelty constraints.

It does not yet prove improved final output quality, because the final synthesis
is incomplete. The next experiment should keep the selection pattern but either
reduce final required sections, tighten the final output format, or run with a
larger output budget before treating the protocol as better than the baseline.
