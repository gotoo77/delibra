# Delibra Docs

- [Delibra Core Model v0.1](core-model-v0.1.md)
- [Architecture Principles](architecture-principles.md)
- [Preset Repository](preset-repository.md)
- [ADR-0001 - Delibra Core Identity](adr/0001-core-identity.md)
- [ADR-0002 - Runtime Provider Boundary](adr/0002-runtime-provider-boundary.md)
- [ADR-0003 - Efficient Execution](adr/0003-efficient-execution.md)
- [Concept Notes](concepts/README.md)
- [AI Systems Engineering](implementation/ai-systems-engineering.md)
- [Measurement Notes](measurement-notes.md)

## Presets

Presets are reusable Delibra recipes: versioned YAML protocols that encode
structured deliberation patterns. See [Preset Repository](preset-repository.md)
and [presets/README.md](../presets/README.md) for the current convention.

- [Code Review](../presets/code_review.yaml)
- [Design Review](../presets/design_review.yaml)
- [Decision Review](../presets/decision_review.yaml)
- [Treasure Hunt Design](../presets/treasure_hunt_design.yaml) (experimental)
- [Treasure Hunt Design Selection](../presets/treasure_hunt_design_selection.yaml) (experimental)

### Treasure Hunt Design

`treasure_hunt_design` is an experimental preset for designing a game de piste,
treasure hunt, or multi-domain puzzle sequence from structured constraints. It
first derives a `game_dna`, then fans out design perspectives, critiques them
through saboteur/playtester/coherence roles, and synthesizes a testable design.

`treasure_hunt_design_selection` is a comparison variant. It keeps the same
runtime primitives, adds one selection/compression step before final synthesis,
and uses that compact artifact to reduce final-step context pressure.

Minimal input example: [treasure_hunt_design_input.md](../examples/treasure_hunt_design_input.md).
More ambitious comparison input: [treasure_hunt_design_input_gotoo.md](../examples/treasure_hunt_design_input_gotoo.md).

Example mock run:

```bash
delibra run \
  --protocol presets/treasure_hunt_design.yaml \
  --provider mock \
  --input-text "$(cat examples/treasure_hunt_design_input.md)" \
  --run-output run.json \
  --trace-output trace.json
```

Example run with an execution policy:

```bash
cat > policy.yaml <<'YAML'
id: cheap-treasure-hunt
mode: cheap
budget:
  max_estimated_units: 4000
default_step_budget:
  max_output_units: 300
YAML

delibra run \
  --protocol presets/treasure_hunt_design.yaml \
  --provider mock \
  --policy policy.yaml \
  --input-text "$(cat examples/treasure_hunt_design_input.md)" \
  --run-output run.json \
  --trace-output trace.json
```

Limitations: this preset only uses the current runtime primitives (`prompt`,
`fanout`, `criticize`, `synthesize`). It does not add specialized puzzle
validation, external fact checking, stateful play simulation, or a custom game
generator. Those are future design questions, not requirements for this first
usable pass.

In v0.1, multi-role `fanout` and `criticize` steps are executed sequentially by
the runtime.
