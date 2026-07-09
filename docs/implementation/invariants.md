# Delibra Implementation Invariants

Every implementation change must preserve this checklist.

See also [Architecture Principles](../architecture-principles.md) for the
project-level guardrails behind this implementation checklist.

- Delibra never reasons; models reason.
- Artifacts are immutable.
- Steps create artifacts; they never mutate artifacts.
- Message is not durable core.
- Providers do not enter core.
- Core does not interpret payload.
- Inputs resolve via produces.output, not step.id.
- kind is structural, not domain-specific.
- No primitive beyond prompt/fanout/criticize/synthesize.
- Trace is an event stream, not an ad hoc log.
- Runtime behavior is deterministic given fixed protocol, input, model outputs, ids, and clock.
- Non-determinism is isolated at provider/model boundaries.
- When a CLI command or option is added, renamed, removed, or behaviorally
  changed, the same patch must check and update:
  - CLI help and usage text;
  - associated CLI tests;
  - `README.md` when the option is user-facing;
  - `docs/README.md` or the relevant documentation when the option touches
    runtime behavior;
  - a minimal usage example when it helps prevent hidden or ambiguous behavior.

Model outputs may vary.
Runtime derivation must not.
