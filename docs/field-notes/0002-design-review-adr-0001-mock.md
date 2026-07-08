# Field Note -- Design Review on ADR-0001 With Mock

## Date

2026-07-08

## Protocol

`design_review@0.1.0`

## Provider

`mock`

## Model

N/A

## Input Source

`docs/adr/0001-core-identity.md`

Input size observed locally: about 2,010 bytes.

## Output Location

Raw outputs were written outside the repository:

`~/dev/delibra-runs/0002-design-review-adr-0001-mock`

Generated files included `input.txt`, `run.json`, `trace.json`, `run.stdout`, and `inspect.txt`.

## What Worked

- The `design_review` preset executed successfully with the mock provider.
- The run produced 7 artifacts.
- The trace contained 29 events.
- `inspect` made the artifact structure readable without opening `run.json`.
- The run was cost-free and safe for workflow validation.

## What Was Confusing

- Running a non-code-review field note required manually assembling the `delibra run` and `delibra inspect` commands.
- Unlike `scripts/run_real_code_review.sh`, there is no scenario helper that extracts `final_synthesis.txt`.
- Mock output validates the protocol mechanics but is not useful for judging ADR quality.

## Cost / Time

- Provider cost: none.
- Execution time: local/mock, effectively immediate.

## Provider-Side Observations

None. The mock provider was used.

## Frictions Observed

- Field-note runs currently require repeated manual command wiring.
- There is no common helper for arbitrary preset + file input.
- Inspect output is useful, but final synthesis extraction is only available in the code review scenario script.
- The note can record mechanics and workflow ergonomics, but not semantic review quality.

## Decision

- wait: do not add a generic scenario runner yet.
- document: record that arbitrary field-note runs are still manual.
- runtime issue: none observed.
- preset issue: none observed from mock execution alone.

## Follow-Up

- Repeat with one semantic provider run only after more mock notes justify the cost.
- Watch whether final artifact extraction becomes repeated friction across field notes.
