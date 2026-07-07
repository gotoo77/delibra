# AI Systems Engineering

This document records the development discipline used to build Delibra with AI assistance.

It is not a product feature.
It is the method used to protect architecture while implementation grows.

## Positioning

Delibra should not be developed as an agent framework.

The central abstraction is not the agent, the prompt, or the execution graph.
The central abstraction is the artifact.

Delibra is artifact-first, not agent-first.

Delibra is a deterministic runtime for artifact derivation.

Model outputs may vary.
Runtime derivation must not.

## Design Principle

The runtime should remain deliberately simple.

It should:

- resolve inputs;
- create engine-only messages;
- call a model boundary;
- create artifacts;
- append trace events;
- advance run state.

It should not reason, plan, interpret payloads, invent workflow behavior, or make domain decisions.

Intelligence belongs in models.
Durable derivation belongs in Delibra.

## Development Loop

Development should proceed one architectural layer at a time.

The preferred loop is:

```text
RFC
-> Concept Validation
-> Decision
-> Implementation
-> Compliance Review
-> Fix
-> Commit
```

For backlog lots, the practical loop is:

```text
Lot
-> Tests
-> Architecture Review
-> Fix
-> Demo or Smoke Path
-> Commit
```

Do not implement multiple lots at once.

Each lot should leave the codebase in a state where the next layer can be built without revisiting hidden architectural debt.

## Levels Of Confidence

Not every decision deserves the same level of confidence before code is written.

Use the smallest level that responsibly reduces the current risk.

| Level | State | Required |
| --- | --- | --- |
| L0 | Idea | Discussion |
| L1 | Architecture | RFC |
| L2 | Uncertain abstraction | Concept Validation |
| L3 | Accepted design | Implementation |
| L4 | Conformance | Review |
| L5 | Stable | Commit |

The goal is not to slow development down.
The goal is to avoid giving unstable ideas the authority of stable code.

## Architectural Checkpoints

Before entering a major architectural phase, stop.

Read:

- the philosophy;
- the core RFC;
- the implementation invariants;
- the recent commit history;
- the current source structure.

Ask:

- does the implementation still resemble the philosophy?
- are durable and ephemeral boundaries still clean?
- did provider, engine, or message concepts leak into core?
- can the next phase start without revisiting previous lots?
- what should be frozen exactly as-is before continuing?

Only then continue.

## Compliance Reviews

Reviews should not primarily ask whether the code is elegant.

They should ask whether the implementation still conforms to:

- `PHILOSOPHY.md`;
- `docs/core-model-v0.1.md`;
- `docs/implementation/invariants.md`;
- the current backlog lot.

The review should look for:

- architectural drift;
- hidden mutability;
- accidental coupling;
- provider leakage;
- engine leakage into durable core;
- `Message` leakage into durable core;
- payload interpretation;
- premature workflow-engine behavior;
- missing invariants.

The goal is to freeze each layer before building the next one.

## Concept Validation

A concept validation is a disposable experiment used to reduce architectural risk.

It should answer a design question before the concept enters production code.

Concept validations should be numbered when they create durable architectural knowledge.

Examples:

- `CV-000 Artifact-first derivation` - accepted;
- `CV-001 Parallel fanout` - pending;
- `CV-002 Persistence backend` - rejected.

The status matters because the experiment becomes part of the design memory.

Examples:

- Does artifact-first execution remain simple when steps derive artifacts from prior outputs?
- Can fanout be expressed without changing the durable core?
- Can provider integration remain outside the core model?
- Can persistence be added without making `Run` operational state?
- Can concurrency stay outside the protocol model?

The code produced by a concept validation is disposable.
The decision it enables is durable.

## Negative Spikes

A negative spike asks whether a proposed feature can be avoided.

This is especially important for features that would make Delibra look like a generic workflow engine.

Examples:

- Can `if` be avoided?
- Can `parallel` remain an execution strategy instead of a core primitive?
- Can a repeated pattern be expressed as a preset instead of a new protocol construct?
- Can memory remain outside the core?

If a concept can remain a preset, do not promote it into the core.

Before adding a new core concept, first prove that it cannot remain a preset.

The core grows only when multiple protocols demand the same abstraction.

## Runtime Boundary Discipline

The runtime may coordinate derivation, but it must not become the source of meaning.

During engine work, preserve these boundaries:

- `Run` is a durable record, not an execution context.
- `ExecutionContext` is ephemeral, not canonical output.
- `Message` is engine-only.
- Providers stay behind model boundaries.
- Trace is a typed event stream, not an ad hoc log.
- Artifacts are immutable and append-only.
- Payloads remain opaque JSON.
- Inputs resolve through `produces.output`, not `step.id`.

Given fixed protocol, input, model outputs, ids, and clock, runtime behavior should be reproducible.

## When To Add A Spike

Do not add spikes on a schedule.

Add one when a decision can damage the architecture if made too early.

Good candidates include:

- first real provider integration;
- first fanout execution;
- persistence format;
- concurrency;
- streaming;
- any proposal to add workflow concepts to the core.

The purpose of a spike is not to explore indefinitely.
The purpose is to avoid a bad architectural decision.
