# Field Note -- Code Review on Delibra With OpenAI

## Date

2026-07-08

## Protocol

`code_review@0.1.0`

## Provider

`openai`

## Model

`gpt-5.5`

## Input Source

Git diff: `HEAD~1..HEAD`

The selected diff contained 197 lines.

## Output Location

Raw outputs were written outside the repository:

`/tmp/delibra-code-review.eVAFtZ`

Generated files included `input.patch`, `run.json`, `trace.json`, `inspect.txt`, and `final_synthesis.txt`.

## What Worked

- The full real-provider scenario completed successfully.
- Delibra produced 7 artifacts.
- Delibra produced 29 trace events.
- `inspect` summarized the durable run and trace.
- `final_synthesis.txt` made the final review readable without manually opening `run.json`.
- The durable core model did not need to change.

## What Was Confusing

- The first OpenAI attempts were hard to interpret because the script was silent during provider calls.
- Initial failures did not clearly distinguish timeout, missing model, no-text provider response, and incomplete provider output.
- Before `final_synthesis.txt`, the scenario produced valid durable outputs but did not make the human review easy to read.

## Cost / Time

Observed from the provider usage dashboard:

- About `$1.41`
- 20 requests
- About 57k tokens

Observed provider input character sizes during the successful run:

- 7777
- 2742
- 2730
- 2727
- 29606
- 29604
- 44829

The final synthesis call had the largest input context.

## Provider-Side Observations

OpenAI platform logs exposed the request shape received by the provider for the final synthesis call:

- response id: `resp_083579250ac1e477006a4eab1ecdb081928dc36f5368437716`
- role: `synthesizer`
- step: `final`
- input tokens shown by OpenAI: about 10,427
- output tokens shown by OpenAI: about 1,562
- resolved artifact ids included: `artifact_0001` through `artifact_0006`

The final prompt included the framing artifact, three review artifacts, and two critique artifacts. This confirms that the high final-call context came from passing the prior derivation artifacts into synthesis.

The provider log is useful for debugging runtime behavior, but it is not Delibra durable provenance. It must not be copied into `run.json`, `trace.json`, artifacts, or field notes except as summarized observations.

## Frictions Observed

- Initial timeout and lack of visible progress made the run feel blocked.
- The scenario needed a heartbeat/progress indicator.
- The scenario needed to extract `final_synthesis.txt`.
- Provider output needed runtime-only diagnostics for no-text responses.
- `OPENAI_TIMEOUT_SECONDS` and `OPENAI_MAX_OUTPUT_TOKENS` needed to be configurable.
- Context grew substantially in critique and final synthesis steps.
- The provider log made context growth measurable: the final synthesis received all six prior artifacts and accounted for about 10k input tokens.
- The scenario script needed hardening:
  - owner-only output permissions;
  - safer Git diff flags;
  - clearer empty-diff and invalid-range errors;
  - README warnings about provider cost and source-code exposure.

## Decision

- fix now: harden the real scenario script.
- fix now: add runtime-only OpenAI diagnostics and configurable timeout/output limits.
- document: explain scenario status, requirements, diff behavior, generated outputs, and provider cost/sensitivity.
- wait: stop OpenAI runs temporarily.
- wait: collect 5-10 field notes before adding major features such as planning, budgeting, cache, or context optimization.
- concept tension: provider-side logs are useful for observing execution cost and context shape, but they must remain outside durable core provenance.

## Follow-Up

- Run more field notes across code review, design review, and decision review.
- Track repeated context-growth friction before designing cost or planning features.
- Compare future field notes by step-level context size when provider logs are available.
- Do not treat this note as a roadmap item by itself.
