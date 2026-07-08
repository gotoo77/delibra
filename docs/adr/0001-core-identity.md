# ADR-0001 - Delibra Core Identity

## Status

Accepted

## Decision

Delibra is an artifact-first derivation runtime with durable provenance.

Delibra treats artifacts as the durable boundary of reasoning. Runs and traces exist to preserve how artifacts were derived. Messages, prompts, provider responses, and execution mechanics are engine concerns, not core domain concepts.

Execution is an implementation detail. Derivation is the domain model.

Protocols describe knowledge derivation, not execution.

The core should continuously get smaller as the ecosystem grows.

## Rejected Identities

Delibra is not:

- an agent framework;
- a workflow engine;
- a debate engine;
- a provider abstraction layer.

These may appear as presets, execution strategies, renderers, integrations, or product layers, but they must not define the core model.

## Governance Rule

A feature may enter the core only if:

- at least three unrelated protocols require it;
- it cannot reasonably live in the engine;
- it cannot reasonably live in a provider;
- it cannot reasonably live in a preset;
- it cannot reasonably live in a renderer or product layer;
- removing it would make the core less coherent.

Usefulness is not enough. A core feature must increase the coherence of the model.

Concept notes may document tensions before they become core candidates. A concept note is not approval to implement the concept in the core. Concept notes document tensions, not ideas.

## Next Architecture Gates

1. Fanout/Criticize

   Prove multi-role derivation can produce multiple artifacts without changing Artifact, Run, Trace, or Protocol.

2. Real Presets

   Prove code_review, design_review, and one additional serious protocol require no new primitives or domain entities.

3. Real Provider

   Prove an actual provider can be integrated without leaking provider-specific concerns into the durable core.

4. Persistence/Replay

   Prove Delibra's long-term value comes from artifacts and traces, not transient messages.
