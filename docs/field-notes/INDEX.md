# Field Notes Index

This index summarizes observed usage evidence. It is not a roadmap.

Use it to see repeated frictions across field notes. Do not treat a pattern as a feature request until the evidence is strong enough and the architecture governance allows it.

See also [Observed Frictions](FRICTIONS.md) for the factual friction register.

## Notes

| Note | Type | Provider | Main friction | Decision |
|---|---|---|---|---|
| 0001 | code_review | OpenAI | cost/context growth, final output access, provider diagnostics | harden, document, wait |
| 0002 | design_review | mock | manual run/inspect workflow, final synthesis access | wait |
| 0003 | design_review | mock | manual run/inspect workflow, final synthesis access | wait |
| 0004 | decision_review | mock | final recommendation access, semantic value requires real provider | wait |
| 0005 | decision_review | mock | semantic value requires real provider, final synthesis access, possible file input friction | wait |
| 0006 | decision_review | Ollama/qwen3:4b | unsupported claims amplified across artifacts | wait |
| 0007 | comparative_qualification | Ollama/qwen3:4b and OpenAI/gpt-5.5 | same protocol/input produced different epistemic behavior | wait |

## Observed Patterns

Confidence levels:

- Low: 1 observation
- Medium: 2-4 observations
- High: 5+ observations

| Pattern | Mentions | First seen | Last seen | Confidence |
|---|---:|---|---|---|
| Final synthesis access | 5 | 0001 | 0005 | High |
| Manual run/inspect workflow | 2 | 0002 | 0003 | Medium |
| Cost / context growth | 1 | 0001 | 0001 | Low |
| Provider diagnostics | 1 | 0001 | 0001 | Low |
| Semantic value requires real provider | 2 | 0004 | 0005 | Medium |
| Possible file input friction | 1 | 0005 | 0005 | Low |
| Unsupported claims amplified across artifacts | 1 | 0006 | 0006 | Low |
| Same protocol/input can show different epistemic behavior across model/provider configurations | 1 | 0007 | 0007 | Low |

## Current Reading

The durable model and presets are not under pressure from these notes.

The repeated friction is user-facing access to the final result after a run. This may eventually justify a small renderer or extraction workflow, but the evidence is still observational and should remain outside the roadmap until more field notes exist.
