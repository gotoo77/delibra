# Field Note -- puzzle_design prompt-only quality gate failure

## Date

2026-07-17

## Protocol

- `puzzle_design@0.1.0` through `puzzle_design@0.1.3`

## Provider

- Ollama

## Model

- Unknown from persisted artifacts.
- The CLI `run --provider ollama` resolves the model from `OLLAMA_MODEL`.
- Delibra intentionally does not persist provider/model metadata in `run.json`
  or `trace.json`.

## Input Source

- `experiments/treasure/puzzle_design_chateau_inclusif_input.txt`

## Output Location

- `experiments/treasure/puzzle_design_chateau_inclusif_ollama_001/`
- `experiments/treasure/puzzle_design_chateau_inclusif_ollama_002/`
- `experiments/treasure/puzzle_design_chateau_inclusif_ollama_003/`
- `experiments/treasure/puzzle_design_chateau_inclusif_ollama_004/`

## What Worked

- Moving from a full treasure hunt preset to a one-puzzle preset improved the
  artifact shape: the run produced a brief, multiple drafts, critiques, a
  repaired puzzle, and a final synthesis.
- Later versions improved constraint extraction. In particular, the brief
  stopped inventing a door as the initial objective and captured "no actual or
  symbolic locks" as an exclusion.
- Accessibility constraints were usually preserved as inclusion constraints
  rather than making dyslexia a special ability.

## What Was Confusing

- The model repeatedly converted "one playable puzzle" into a larger game or
  hunt concept.
- The repaired puzzle frequently became a prose summary rather than a
  field-by-field puzzle specification.
- "Exact answer" was often a goal state rather than a literal answer, for
  example escaping the castle, opening a door, finding relics, or finding an
  order without naming the order.
- Validation often depended on invented physical mechanisms such as a secret
  door opening.
- Critique and validation roles sometimes summarized or accepted outputs that
  visibly violated their own stated quality criteria.

## Cost / Time

- One recorded Ollama run of `puzzle_design@0.1.0` took 133.489 seconds and
  produced 11 artifacts.
- The same run had `total_payload_chars: 28296`,
  `total_artifact_json_chars: 30783`, and an estimated upper-bound context of
  42571 tokens.
- Later runs added protocol iterations and, in `0.1.3`, a twelfth artifact for
  `puzzle_validation`.

## Provider-Side Observations

- The observed failures may be model-dependent, but the exact model is not
  recoverable from the durable run files.
- Because `OLLAMA_MODEL` is external runtime configuration, future comparable
  runs should include the model name in the output directory, manifest, or a
  separate experiment note.

## Frictions Observed

- Prompt-only quality gates are not reliable enough to enforce hard acceptance
  criteria.
- A validator role can produce `PASS` while quoting evidence that should have
  forced `FAIL`.
- Provider/model provenance is intentionally absent from durable artifacts,
  which preserves core boundaries but makes later experimental interpretation
  harder unless the operator records the model externally.

## Decision

Choose one or more:

- fix now
- document
- preset issue
- runtime issue
- concept tension
- wait

Decision:

- document
- preset issue
- concept tension
- wait

## Follow-Up

- Stop strengthening this preset only by adding more prompt instructions.
- Test a deterministic or structured quality gate outside the LLM response,
  especially for fields such as exact answer, single-puzzle scope, validation
  mechanism, forbidden objects, and unsupported multi-room progression.
- Consider a small experiment manifest or output naming convention that records
  provider and model without changing Delibra's durable core model.
