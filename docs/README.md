# Delibra Docs

- [Delibra Core Model v0.1](core-model-v0.1.md)
- [Architecture Principles](architecture-principles.md)
- [ADR-0001 - Delibra Core Identity](adr/0001-core-identity.md)
- [ADR-0002 - Runtime Provider Boundary](adr/0002-runtime-provider-boundary.md)
- [ADR-0003 - Efficient Execution](adr/0003-efficient-execution.md)
- [Concept Notes](concepts/README.md)
- [AI Systems Engineering](implementation/ai-systems-engineering.md)

## Presets

- [Code Review](../presets/code_review.yaml)
- [Design Review](../presets/design_review.yaml)
- [Decision Review](../presets/decision_review.yaml)
- [Treasure Hunt Design](../presets/treasure_hunt_design.yaml) (experimental)

### Treasure Hunt Design

`treasure_hunt_design` is an experimental preset for designing a game de piste,
treasure hunt, or multi-domain puzzle sequence from structured constraints. It
first derives a `game_dna`, then fans out design perspectives, critiques them
through saboteur/playtester/coherence roles, and synthesizes a testable design.

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

Limitations: this preset only uses the current runtime primitives (`prompt`,
`fanout`, `criticize`, `synthesize`). It does not add specialized puzzle
validation, external fact checking, stateful play simulation, or a custom game
generator. Those are future design questions, not requirements for this first
usable pass.
