# ADR-0003 - Efficient Execution

## Status

Accepted

## Context

Delibra preserves derivations as durable artifacts and traces.

Real provider execution made cost visible, but provider token accounting is not the core issue. Token usage, model pricing, and provider usage metadata are provider-specific execution details.

The deeper architectural concern is redundant reasoning. A runtime can waste work even when the durable derivation model is correct.

## Decision

Delibra should minimize redundant execution while preserving derivation semantics.

Every token must justify its existence.

The runtime may optimize how derivation steps execute, but it must not change what a protocol derives.

## Accepted

- Provider-independent execution planning.
- Reusing already-derived artifacts when reuse preserves derivation semantics.
- Avoiding redundant context where the protocol does not require it.
- Prompt or request deduplication inside runtime boundaries.
- Context compaction or summarization as an execution strategy when it preserves the declared derivation.
- Provider-independent budgeting and preflight estimation.
- Provider-specific cost and token observations as runtime diagnostics only.

## Rejected

- Changing a protocol's derivation semantics to save tokens.
- Provider-specific optimization concepts entering the durable core.
- Token usage, cost, model metadata, or provider usage objects in `Artifact`, `Run`, `Trace`, `Protocol`, `StepDefinition`, or `Produces`.
- Modifying durable artifacts to reduce execution cost.
- Treating provider token accounting as the architecture model for efficiency.
- Adding cache, replay, memory, tools, branching, or persistence formats under this ADR.

## Consequences

Efficient execution is a runtime quality, not a core entity.

Future cost-related features should first prove that they preserve derivation semantics and provider boundaries.

Observed provider cost may inform runtime diagnostics, but durable provenance remains provider-agnostic.

If an optimization changes which artifacts are derived, when they are derived, or which inputs they represent, it is not an optimization; it is a protocol or core-model change and requires separate governance.
