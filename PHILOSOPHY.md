# The Zen of Delibra

Models reason.
Delibra orchestrates.

Delibra is not an agent framework.
Delibra is an artifact-first derivation runtime with durable provenance.

Execution is an implementation detail.
Derivation is the domain model.

Artifacts are durable.
Messages are transient.

Delibra never reasons.
Delibra preserves reasoning.

Artifact-first.
Prompting is an implementation detail.

Protocols describe derivations.
They do not encode execution logic.

Protocols describe knowledge derivation.
They do not describe execution.

Steps are derivation functions.
Runs are records of derivation.
Trace is the event stream of derivation.

Prefer explicit artifact flow.
Avoid implicit execution.

Prefer simple primitives.
Avoid generic workflow features.

Small before powerful.

The core should continuously get smaller as the ecosystem grows.

The core must remain boring.

A protocol should explain itself.

The runtime manipulates artifacts.
It does not interpret them.

If a feature makes Delibra look like a workflow engine,
it probably does not belong in the core.

If a feature makes the runtime smarter,
it probably belongs in the model instead.

If a concept can remain a preset,
do not promote it into the core.

The core grows only when multiple protocols demand the same abstraction.

If a result matters,
make it an artifact.

If a step fails,
preserve what was already derived.

When in doubt,
preserve the artifact.

When still in doubt,
keep the core boring.

When in doubt,
do less.
