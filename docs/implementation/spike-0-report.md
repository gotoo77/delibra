# Spike 0 Report: In-Memory Artifact Derivation Prototype

## Scope

Spike 0 implemented a disposable in-memory prototype in `spikes/spike_0_artifact_derivation.py`.

It intentionally avoided:

- CLI;
- YAML;
- provider calls;
- full serialization;
- rendering;
- architecture finalization.

The prototype demonstrates:

- an in-memory `Protocol` with `StepDefinition` values;
- `StepDefinition.inputs` consuming `produces.output` values;
- an ephemeral `ExecutionContext` with `output_index`;
- immutable `Artifact` creation;
- trace as an event stream;
- `Artifact -> StepDefinition -> Artifact` derivation.

## Does the artifact-first model feel pleasant in code?

Yes.

The model maps cleanly to a small execution loop:

1. resolve input output names through `ExecutionContext`;
2. derive one or more artifacts from a `StepDefinition`;
3. append artifacts to the output index;
4. append trace events;
5. keep the durable `Run` as a final record.

The most useful shape is:

```text
StepDefinition
  consumes output names
  produces one output name

ExecutionContext
  output_index: output name -> artifact ids

Run
  immutable record of artifacts and trace events
```

This kept the prototype focused on artifact derivation rather than prompt orchestration.

## Did inputs resolving via produces.output work cleanly?

Yes.

The distinction between `step.id` and `produces.output` was valuable immediately.

In the prototype:

```text
frame_operation -> produces output "framing"
review_operation -> consumes "framing" and produces "reviews"
final_operation -> consumes "framing" and "reviews"
```

The `ExecutionContext.output_index` stayed simple:

```text
framing -> artifact_0001
reviews -> artifact_0002, artifact_0003
final_synthesis -> artifact_0004
```

This confirms that `produces.output` should remain the data-flow identity. `step.id` should remain only the operation identity.

## Did Run risk becoming a mutable bag?

Less than expected.

The spike avoided that by making `ExecutionContext` the mutable operational object and `Run` the final durable record.

The clean split was:

- `ExecutionContext`: mutable output index, working artifact list, working trace event list;
- `Run`: immutable record produced after execution.

This suggests the implementation should resist updating `Run` directly during step execution. The engine can maintain operational state in `ExecutionContext`, then create or update durable run records at explicit boundaries.

## What frictions appeared?

1. `StepCompleted` needs care for multi-role steps.

   In the prototype, `StepCompleted` uses all artifact ids currently indexed under the step output. This is fine because `produces.output` is unique in v0.1, but the implementation should still capture produced ids locally during a step to avoid accidental coupling to the full output index.

2. Python `frozen=True` is not enough for deep artifact immutability.

   The prototype used `MappingProxyType` for payloads. In the real implementation, immutability should be enforced by value ownership and API shape, not assumed from a shallow immutable container.

3. Trace events can become noisy quickly.

   Even three steps produced ten events. This is acceptable, but the event schema should stay minimal and factual.

4. The prototype did not exercise failures.

   The happy path was enough for Spike 0, but Lot 5 and Lot 9 should explicitly test failed runs with partial artifacts.

5. The derivation function must not interpret payload.

   The prototype generated payload content mechanically. The implementation should keep this boundary clear: the engine creates artifacts from model output, but the core does not reason over artifact payload.

## Should we proceed to Lot 1 unchanged, amend backlog, or revisit the core model?

Proceed to Lot 1 unchanged.

The core model does not need revision from this spike.

The backlog remains valid, with one implementation note:

> When implementing step execution, collect `produced_artifact_ids` locally during the step, then append them to trace events. Do not derive `StepCompleted` only by re-reading the full output index.

This is an implementation detail, not a core model change.

## Smoke Test

Command run:

```bash
python3 spikes/spike_0_artifact_derivation.py
```

Output:

```text
spike-0 ok: 4 artifacts, 10 trace events
```
