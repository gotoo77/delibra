from __future__ import annotations

from dataclasses import dataclass

from delibra.core import Artifact, Run, Trace


@dataclass(frozen=True)
class ArtifactInspection:
    artifact_id: str
    output: str
    kind: str
    producer_step_id: str
    producer_role_id: str


@dataclass(frozen=True)
class ArtifactDetail:
    artifact_id: str
    output: str
    kind: str
    producer_step_id: str
    producer_role_id: str
    payload: object
    metadata: object


@dataclass(frozen=True)
class RunInspection:
    run_id: str
    status: str
    protocol_id: str
    protocol_version: str
    requested_language: str | None
    resolved_language: str | None
    artifact_count: int
    artifacts: tuple[ArtifactInspection, ...]
    trace_event_count: int | None


def inspect_run(run: Run, trace: Trace | None = None) -> RunInspection:
    return RunInspection(
        run_id=run.id,
        status=run.status.value,
        protocol_id=str(run.protocol["id"]),
        protocol_version=str(run.protocol["version"]),
        requested_language=None if run.language is None else str(run.language["requested"]),
        resolved_language=None if run.language is None else str(run.language["resolved"]),
        artifact_count=len(run.artifacts),
        artifacts=tuple(
            ArtifactInspection(
                artifact_id=artifact.id,
                output=artifact.output,
                kind=artifact.kind,
                producer_step_id=artifact.producer_step_id,
                producer_role_id=artifact.producer_role_id,
            )
            for artifact in run.artifacts
        ),
        trace_event_count=None if trace is None else len(trace.events),
    )


def inspect_artifact(run: Run, artifact_id: str) -> ArtifactDetail:
    artifact = _find_artifact(run, artifact_id)
    return ArtifactDetail(
        artifact_id=artifact.id,
        output=artifact.output,
        kind=artifact.kind,
        producer_step_id=artifact.producer_step_id,
        producer_role_id=artifact.producer_role_id,
        payload=artifact.to_json()["payload"],
        metadata=artifact.to_json()["metadata"],
    )


def _find_artifact(run: Run, artifact_id: str) -> Artifact:
    for artifact in run.artifacts:
        if artifact.id == artifact_id:
            return artifact
    raise ValueError(f"artifact not found: {artifact_id}")
