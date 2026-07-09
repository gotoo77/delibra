# Delibra Architecture Principles

This document records the principles Delibra gives up only reluctantly. It is
not a feature roadmap. It is a guardrail for deciding where future ideas belong.

## Principles

1. Delibra never reasons; models reason.

   Delibra derives, stores, and traces artifacts. It does not claim semantic
   authority over model output.

2. Artifacts are the business output.

   Messages, prompts, provider responses, request payloads, and execution
   mechanics are not the durable product of a run.

3. Trace is observability, not domain state.

   Trace explains how artifacts were derived. It must not become an ad hoc
   place for business concepts.

4. The runtime stays boring.

   The runtime executes declared protocols and explicit configuration. It must
   not silently decide to compress, summarize, change provider, change model,
   retry, cache, or alter generation settings.

5. Decisions belong in the right layer.

   If an idea requires judgment, ask where it belongs: preset, provider, renderer,
   product layer, execution policy, optimizer/client, or core. Do not put it in
   the runtime merely because the runtime is nearby.

6. The DSL stays minimal.

   New primitives are suspect. Delibra should first prove that `prompt`,
   `fanout`, `criticize`, and `synthesize` are insufficient across unrelated
   protocols.

7. Providers must not contaminate the durable model.

   Provider names, models, tokens, costs, raw responses, and API details are
   execution concerns. They may be observable, but they must not redefine
   `Run`, `Artifact`, `Trace`, or `Protocol` as business objects.

8. Derivation must remain deterministic around model output.

   Given the same protocol, input, model outputs, ids, and clock, Delibra's
   runtime derivation should be deterministic. Model outputs may vary; runtime
   derivation must not.

9. Core growth requires proof.

   Usefulness is not enough. A core concept must make the model more coherent,
   be required by multiple unrelated protocols, and fail to fit cleanly in
   presets, providers, renderers, product layers, or explicit execution policy.

10. Optimizations must be observable and reversible.

    Delibra may apply explicit optimization policies in the future, but raw
    intent must remain recoverable and transformations must never silently change
    the semantics of a run.
