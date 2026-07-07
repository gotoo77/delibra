# Delibra Implementation Invariants

Every implementation change must preserve this checklist.

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
