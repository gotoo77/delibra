from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Produces:
    output: str
    kind: str


@dataclass(frozen=True)
class StepDefinition:
    id: str
    kind: str
    role: str | None
    roles: tuple[str, ...]
    instruction: str
    inputs: tuple[str, ...]
    produces: Produces


@dataclass(frozen=True)
class Protocol:
    id: str
    version: str
    steps: tuple[StepDefinition, ...]


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str
    output: str
    producer_step_id: str
    producer_role_id: str
    payload: Mapping[str, str]


@dataclass(frozen=True)
class TraceEvent:
    type: str
    step_id: str | None
    payload: Mapping[str, object]


@dataclass(frozen=True)
class Run:
    id: str
    protocol_id: str
    artifacts: tuple[Artifact, ...]
    trace: tuple[TraceEvent, ...]


class ExecutionContext:
    def __init__(self, run_id: str, user_input: str) -> None:
        self.run_id = run_id
        self.user_input = user_input
        self.output_index: dict[str, list[str]] = {}
        self._artifacts: list[Artifact] = []
        self._trace: list[TraceEvent] = []

    def resolve(self, inputs: tuple[str, ...]) -> list[str]:
        resolved: list[str] = []
        for input_name in inputs:
            if input_name == "user_input":
                continue
            resolved.extend(self.output_index[input_name])
        return resolved

    def append_artifact(self, artifact: Artifact) -> None:
        self._artifacts.append(artifact)
        self.output_index.setdefault(artifact.output, []).append(artifact.id)
        self._trace.append(
            TraceEvent(
                type="ArtifactCreated",
                step_id=artifact.producer_step_id,
                payload=MappingProxyType(
                    {
                        "artifact_id": artifact.id,
                        "output": artifact.output,
                        "kind": artifact.kind,
                    }
                ),
            )
        )

    def append_event(self, event_type: str, step_id: str | None, payload: Mapping[str, object]) -> None:
        self._trace.append(
            TraceEvent(
                type=event_type,
                step_id=step_id,
                payload=MappingProxyType(dict(payload)),
            )
        )

    def finish(self, protocol: Protocol) -> Run:
        return Run(
            id=self.run_id,
            protocol_id=protocol.id,
            artifacts=tuple(self._artifacts),
            trace=tuple(self._trace),
        )


def derive(step: StepDefinition, context: ExecutionContext) -> None:
    input_artifact_ids = context.resolve(step.inputs)
    context.append_event(
        "StepStarted",
        step.id,
        {"inputs": step.inputs, "resolved_artifact_ids": tuple(input_artifact_ids)},
    )

    role_ids = step.roles if step.roles else (step.role,)
    for role_id in role_ids:
        assert role_id is not None
        artifact = Artifact(
            id=f"artifact_{len(context._artifacts) + 1:04d}",
            kind=step.produces.kind,
            output=step.produces.output,
            producer_step_id=step.id,
            producer_role_id=role_id,
            payload=MappingProxyType(
                {
                    "content": (
                        f"{role_id} derived {step.produces.kind} "
                        f"from {','.join(input_artifact_ids) or 'user_input'}"
                    )
                }
            ),
        )
        context.append_artifact(artifact)

    produced_ids = context.output_index[step.produces.output]
    context.append_event(
        "StepCompleted",
        step.id,
        {"produced_artifact_ids": tuple(produced_ids)},
    )


def build_protocol() -> Protocol:
    return Protocol(
        id="spike_0",
        version="0.1.0",
        steps=(
            StepDefinition(
                id="frame_operation",
                kind="prompt",
                role="framer",
                roles=(),
                instruction="Frame the input.",
                inputs=("user_input",),
                produces=Produces(output="framing", kind="framing"),
            ),
            StepDefinition(
                id="review_operation",
                kind="fanout",
                role=None,
                roles=("maintainer", "tester"),
                instruction="Review the framing.",
                inputs=("framing",),
                produces=Produces(output="reviews", kind="review"),
            ),
            StepDefinition(
                id="final_operation",
                kind="synthesize",
                role="synthesizer",
                roles=(),
                instruction="Synthesize the reviews.",
                inputs=("framing", "reviews"),
                produces=Produces(output="final_synthesis", kind="synthesis"),
            ),
        ),
    )


def smoke() -> Run:
    protocol = build_protocol()
    context = ExecutionContext(run_id="run_spike_0", user_input="demo input")

    for step in protocol.steps:
        derive(step, context)

    run = context.finish(protocol)

    assert context.output_index == {
        "framing": ["artifact_0001"],
        "reviews": ["artifact_0002", "artifact_0003"],
        "final_synthesis": ["artifact_0004"],
    }
    assert [artifact.output for artifact in run.artifacts] == [
        "framing",
        "reviews",
        "reviews",
        "final_synthesis",
    ]
    assert run.artifacts[1].producer_step_id == "review_operation"
    assert run.artifacts[1].producer_role_id == "maintainer"
    assert run.trace[0].type == "StepStarted"
    assert run.trace[-1].type == "StepCompleted"

    try:
        run.artifacts[0].payload["content"] = "mutated"
        raise AssertionError("artifact payload should be immutable")
    except TypeError:
        pass

    return run


if __name__ == "__main__":
    result = smoke()
    print(
        f"spike-0 ok: {len(result.artifacts)} artifacts, "
        f"{len(result.trace)} trace events"
    )
