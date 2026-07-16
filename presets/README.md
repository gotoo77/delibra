# Presets

Presets are reusable Delibra recipes.

They are YAML protocols that encode a structured deliberation pattern for a
class of inputs. They are versionable, reviewable, and shareable. They are not
provider configurations, execution policies, or examples that can drift without
care.

## Convention

- File name: stable `snake_case`, matching the protocol `id`.
- Protocol `version`: required and updated when recipe behavior changes.
- `description`: short statement of the recipe purpose.
- Runtime primitives: only `prompt`, `fanout`, `criticize`, and `synthesize`.
- Provider details: none.
- Execution policy: separate from the preset.
- Tests: every preset should validate and execute with the mock provider.

Experimental presets should be called out in documentation until repeated use
shows the recipe is stable enough to treat as ordinary.

## Current Experimental Presets

- `puzzle_design.yaml`: micro-protocol for designing one concrete, playable,
  testable puzzle before composing larger treasure hunt structures.
- `treasure_hunt_design.yaml`: baseline structured treasure hunt design protocol.
- `treasure_hunt_design_selection.yaml`: variant that adds one selection and
  compression step before final synthesis to test whether preserving only the
  strongest ideas and critiques improves the final output under context
  pressure.
