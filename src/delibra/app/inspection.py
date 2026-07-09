from __future__ import annotations

from dataclasses import dataclass

from delibra.core import Run, Trace


@dataclass(frozen=True)
class ArtifactInspection:
    output: str
    kind: str
    producer_step_id: str
    producer_role_id: str


@dataclass(frozen=True)
class RunInspection:
    run_id: str
    status: str
    protocol_id: str
    protocol_version: str
    artifact_count: int
    artifacts: tuple[ArtifactInspection, ...]
    trace_event_count: int | None


def inspect_run(run: Run, trace: Trace | None = None) -> RunInspection:
    return RunInspection(
        run_id=run.id,
        status=run.status.value,
        protocol_id=str(run.protocol["id"]),
        protocol_version=str(run.protocol["version"]),
        artifact_count=len(run.artifacts),
        artifacts=tuple(
            ArtifactInspection(
                output=artifact.output,
                kind=artifact.kind,
                producer_step_id=artifact.producer_step_id,
                producer_role_id=artifact.producer_role_id,
            )
            for artifact in run.artifacts
        ),
        trace_event_count=None if trace is None else len(trace.events),
    )
