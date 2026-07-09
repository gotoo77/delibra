from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, replace
from typing import Protocol as TypingProtocol

from delibra.core import (
    Artifact,
    Protocol,
    Run,
    RunStatus,
    StepDefinition,
    StepKind,
    Trace,
    TraceEvent,
    TraceEventType,
)
from delibra.core.json import JsonMutableObject


TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}

ALLOWED_TRANSITIONS = {
    RunStatus.CREATED: {RunStatus.VALIDATED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.VALIDATED: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.RUNNING: {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}


class Clock(TypingProtocol):
    def now(self) -> str:
        ...


@dataclass
class IdSequence:
    prefix: str
    start: int = 1
    width: int = 4

    def __post_init__(self) -> None:
        self._next = self.start

    def next(self) -> str:
        value = f"{self.prefix}_{self._next:0{self.width}d}"
        self._next += 1
        return value


@dataclass(frozen=True)
class FixedClock:
    timestamps: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "_index", 0)

    def now(self) -> str:
        index = self._index
        if index >= len(self.timestamps):
            raise RuntimeError("fixed clock exhausted")
        object.__setattr__(self, "_index", index + 1)
        return self.timestamps[index]


@dataclass(frozen=True)
class SystemClock:
    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_run(
    protocol: Protocol,
    input_ref: JsonMutableObject,
    *,
    run_ids: IdSequence,
    trace_ids: IdSequence,
    clock: Clock,
) -> Run:
    return Run(
        id=run_ids.next(),
        protocol={
            "id": protocol.id,
            "version": protocol.version,
        },
        status=RunStatus.CREATED,
        input=input_ref,
        artifacts=(),
        trace_id=trace_ids.next(),
        started_at=clock.now(),
        completed_at=None,
    )


def create_trace(run: Run) -> Trace:
    return Trace(
        id=run.trace_id,
        run_id=run.id,
        events=(),
    )


def transition_run(run: Run, status: RunStatus, *, clock: Clock) -> Run:
    status = RunStatus.parse(status.value if isinstance(status, RunStatus) else status)
    if status not in ALLOWED_TRANSITIONS[run.status]:
        raise ValueError(f"invalid run transition: {run.status.value} -> {status.value}")
    completed_at = clock.now() if status in TERMINAL_STATUSES else run.completed_at
    return replace(run, status=status, completed_at=completed_at)


def create_artifact(
    step: StepDefinition,
    *,
    producer_role_id: str,
    payload: JsonMutableObject,
    metadata: JsonMutableObject,
    artifact_ids: IdSequence,
    clock: Clock,
    output: str | None = None,
    kind: str | None = None,
) -> Artifact:
    output = step.produces.output if output is None else output
    kind = step.produces.kind if kind is None else kind
    if output != step.produces.output:
        raise ValueError(
            f"artifact output {output} does not match step output {step.produces.output}"
        )
    if kind != step.produces.kind:
        raise ValueError(f"artifact kind {kind} does not match step kind {step.produces.kind}")
    _require_producer_role_matches_step(step, producer_role_id)
    return Artifact(
        id=artifact_ids.next(),
        kind=kind,
        output=output,
        producer_step_id=step.id,
        producer_role_id=producer_role_id,
        payload=payload,
        metadata=metadata,
        created_at=clock.now(),
    )


def _require_producer_role_matches_step(
    step: StepDefinition, producer_role_id: str
) -> None:
    if step.kind in (StepKind.PROMPT, StepKind.SYNTHESIZE):
        if producer_role_id != step.role:
            raise ValueError(
                f"producer_role_id {producer_role_id} does not match step role {step.role}"
            )
        return
    if step.kind in (StepKind.FANOUT, StepKind.CRITICIZE):
        if step.roles is None or producer_role_id not in step.roles:
            raise ValueError(
                f"producer_role_id {producer_role_id} is not in step roles"
            )
        return
    raise ValueError(f"unsupported step kind: {step.kind}")


def append_artifact(run: Run, artifact: Artifact) -> Run:
    return replace(run, artifacts=(*run.artifacts, artifact))


def create_trace_event(
    *,
    run_id: str,
    event_type: TraceEventType,
    event_ids: IdSequence,
    clock: Clock,
    step_id: str | None,
    payload: JsonMutableObject,
) -> TraceEvent:
    return TraceEvent(
        id=event_ids.next(),
        type=event_type,
        timestamp=clock.now(),
        run_id=run_id,
        step_id=step_id,
        payload=payload,
    )


def append_trace_event(trace: Trace, event: TraceEvent) -> Trace:
    return replace(trace, events=(*trace.events, event))
