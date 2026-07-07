from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from delibra.core import Artifact, Run, RunStatus, StepDefinition
from delibra.core.json import JsonFrozenObject


@dataclass(frozen=True)
class MissingOutputError(Exception):
    output: str

    def __str__(self) -> str:
        return f"missing output: {self.output}"


@dataclass(frozen=True)
class InvalidRunStateError(Exception):
    status: RunStatus

    def __str__(self) -> str:
        return f"execution context requires running run, got: {self.status.value}"


@dataclass(frozen=True)
class ResolvedInputs:
    user_input: JsonFrozenObject | None
    artifact_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionContext:
    run_id: str
    input_ref: JsonFrozenObject
    output_index: MappingProxyType[str, tuple[str, ...]]

    @classmethod
    def from_run(cls, run: Run) -> "ExecutionContext":
        if run.status is not RunStatus.RUNNING:
            raise InvalidRunStateError(run.status)
        output_index: dict[str, list[str]] = {}
        for artifact in run.artifacts:
            output_index.setdefault(artifact.output, []).append(artifact.id)
        return cls(
            run_id=run.id,
            input_ref=run.input,
            output_index=MappingProxyType(
                {
                    output: tuple(artifact_ids)
                    for output, artifact_ids in output_index.items()
                }
            ),
        )

    def resolve_input(self, input_id: str) -> JsonFrozenObject | tuple[str, ...]:
        if input_id == "user_input":
            return self.input_ref
        try:
            return self.output_index[input_id]
        except KeyError as exc:
            raise MissingOutputError(input_id) from exc

    def resolve_step_inputs(self, step: StepDefinition) -> ResolvedInputs:
        user_input: JsonFrozenObject | None = None
        artifact_ids: list[str] = []
        for input_id in step.inputs:
            resolved = self.resolve_input(input_id)
            if input_id == "user_input":
                user_input = resolved
            else:
                artifact_ids.extend(resolved)
        return ResolvedInputs(
            user_input=user_input,
            artifact_ids=tuple(artifact_ids),
        )

    def with_artifact(self, artifact: Artifact) -> "ExecutionContext":
        current = self.output_index.get(artifact.output, ())
        updated = dict(self.output_index)
        updated[artifact.output] = (*current, artifact.id)
        return ExecutionContext(
            run_id=self.run_id,
            input_ref=self.input_ref,
            output_index=MappingProxyType(updated),
        )
