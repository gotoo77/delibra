# ADR-0002 - Runtime Provider Boundary

## Status

Accepted

## Context

Gate 3 added the first real provider integration without changing the durable core model.

The OpenAI provider lives behind the runtime `LLMClient` boundary. Its request shape, authentication, model name, response shape, and failure modes are execution concerns.

## Decision

Provider details may affect execution.

Provider details must not define derivation.

Providers may produce model output for a derivation step, but the durable result remains an artifact created by Delibra according to the protocol.

## Accepted

- Providers live in runtime and CLI code.
- Provider selection is explicit at execution time.
- Mock remains the default provider for tests.
- Provider output is normalized into the existing runtime response shape.
- Provider failures become runtime execution failures and trace failure events.
- Engine-only request data may include resolved artifacts so providers can generate useful output.

## Rejected

- Provider-specific fields in `Artifact`, `Run`, `Trace`, `Protocol`, `StepDefinition`, or `Produces`.
- Token usage, cost tracking, model metadata, or provider ids in durable core records.
- Raw provider responses as durable artifacts.
- Provider response schemas defining artifact payload schemas.
- Streaming, retries, tools, memory, persistence, replay, or branching as part of the provider boundary.

## Consequences

Durable provenance records what Delibra derived, not provider implementation details.

Provider integrations can change without changing the derivation model.

Future persistence and replay work must preserve this boundary: persisted runs and traces must remain provider-agnostic unless a later ADR explicitly changes the durable model.
