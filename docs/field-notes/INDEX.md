# Field Notes Index

This index summarizes observed usage evidence. It is not a roadmap.

Use it to see repeated frictions across field notes. Do not treat a pattern as a feature request until the evidence is strong enough and the architecture governance allows it.

## Notes

| Note | Type | Provider | Main friction | Decision |
|---|---|---|---|---|
| 0001 | code_review | OpenAI | cost/context growth, final output access, provider diagnostics | harden, document, wait |
| 0002 | design_review | mock | manual run/inspect workflow, final synthesis access | wait |
| 0003 | design_review | mock | manual run/inspect workflow, final synthesis access | wait |
| 0004 | decision_review | mock | final recommendation access, semantic value requires real provider | wait |

## Observed Patterns

Confidence levels:

- Low: 1 observation
- Medium: 2-4 observations
- High: 5+ observations

| Pattern | Mentions | First seen | Last seen | Confidence |
|---|---:|---|---|---|
| Final synthesis access | 4 | 0001 | 0004 | Medium |
| Manual run/inspect workflow | 2 | 0002 | 0003 | Medium |
| Cost / context growth | 1 | 0001 | 0001 | Low |
| Provider diagnostics | 1 | 0001 | 0001 | Low |
| Semantic value requires real provider | 1 | 0004 | 0004 | Low |

## Current Reading

The durable model and presets are not under pressure from these notes.

The repeated friction is user-facing access to the final result after a run. This may eventually justify a small renderer or extraction workflow, but the evidence is still observational and should remain outside the roadmap until more field notes exist.
