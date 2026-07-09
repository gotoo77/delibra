# Field Note -- Decision Review on Input File Priority With Mock

## Date

2026-07-09

## Protocol

`decision_review@0.1.0`

## Provider

`mock`

## Model

N/A

## Input Source

Manual decision prompt:

> Should Delibra prioritize adding a file-based input option (`delibra run --input-file`) now, or continue collecting field notes with the current `--input-text` interface and avoid new CLI mechanics for the moment?

The input included known context about command wiring friction, process argument
limits for large diffs, recent execution-policy work, and the requirement that
new CLI options update help, docs, examples, and tests.

## Output Location

Raw outputs were written outside the repository:

`~/dev/delibra-runs/0005-decision-review-input-file-mock`

Generated files included `input.txt`, `policy.yaml`, `run.json`, `trace.json`,
`run.stdout`, `run.stderr`, `inspect.txt`, and `analyze.txt`.

## What Worked

- The `decision_review` preset executed successfully with the mock provider.
- The run produced 7 artifacts: framing, 3 role reviews, 2 critiques, and final synthesis.
- The trace contained 37 events.
- Execution policy observability worked during the run: 7 `PolicyDecision` events, no `BudgetExceeded` events.
- The recipe shape is appropriate for this kind of product decision: framing, strategic review, risk review, operational review, critique, and synthesis are the right pressure points.

## What Was Confusing

- Mock artifacts cannot evaluate the actual decision. They only prove that the recipe shape executes.
- The intermediate artifacts are structurally inspectable, but not semantically useful with mock content.
- The final synthesis still requires manual extraction from `run.json` if the user wants a standalone recommendation.

## Cost / Time

- Provider cost: none.
- Execution time: local/mock, effectively immediate.
- Policy estimates: 7 allowed calls, 4083 total estimated units, largest pre-call estimate on `final/synthesizer` with 797 estimated units.
- No budget pressure was observed under the permissive policy used for the field note.

## Provider-Side Observations

None. The mock provider was used.

## Frictions Observed

- This run reinforces that `decision_review` needs a semantic provider to test its real value.
- A simple prompt would likely be faster for a human to read, but would not produce durable intermediate artifacts for framing, role-specific pressure, critique, and synthesis.
- The field-note workflow still requires manual command assembly and manual reading/extraction of the final artifact.
- The `--input-text` limitation remains plausible but is not proven by this run because the input was small.

## Decision

- wait: do not add `--input-file` from this mock run alone.
- wait: run `decision_review` with a semantic provider before treating this recipe as validated for real decisions.
- document: record that `decision_review` has the right structural shape for product decisions.
- runtime issue: final synthesis access remains a repeated workflow friction, but still needs a small, separately justified design.

## Follow-Up

- Re-run this decision with a semantic provider when available.
- Compare the semantic run against a single-prompt baseline.
- If more field notes hit shell argument limits or awkward file input, reconsider `--input-file` with the CLI documentation/test rule already in place.
