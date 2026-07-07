from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from delibra.core.json import (
    JsonFrozenObject,
    JsonFrozenValue,
    JsonMutableObject,
    JsonMutableValue,
)


class RunStatus(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def parse(cls, value: str) -> "RunStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown run status: {value}") from exc


class TraceEventType(str, Enum):
    RUN_CREATED = "RunCreated"
    RUN_VALIDATED = "RunValidated"
    RUN_STARTED = "RunStarted"
    STEP_STARTED = "StepStarted"
    MESSAGE_SENT = "MessageSent"
    MESSAGE_RECEIVED = "MessageReceived"
    ARTIFACT_CREATED = "ArtifactCreated"
    STEP_COMPLETED = "StepCompleted"
    STEP_FAILED = "StepFailed"
    RUN_COMPLETED = "RunCompleted"
    RUN_FAILED = "RunFailed"
    RUN_CANCELLED = "RunCancelled"

    @classmethod
    def parse(cls, value: str) -> "TraceEventType":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown trace event type: {value}") from exc


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str
    output: str
    producer_step_id: str
    producer_role_id: str
    payload: JsonMutableObject | JsonFrozenObject
    metadata: JsonMutableObject | JsonFrozenObject
    created_at: str

    def __post_init__(self) -> None:
        _require_json_object("payload", self.payload)
        _require_json_object("metadata", self.metadata)
        object.__setattr__(self, "payload", _freeze_json_object(self.payload))
        object.__setattr__(self, "metadata", _freeze_json_object(self.metadata))

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "kind": self.kind,
            "output": self.output,
            "producer_step_id": self.producer_step_id,
            "producer_role_id": self.producer_role_id,
            "payload": _thaw_json_object(self.payload),
            "metadata": _thaw_json_object(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Artifact":
        _require_fields(
            "Artifact",
            data,
            {
                "id",
                "kind",
                "output",
                "producer_step_id",
                "producer_role_id",
                "payload",
                "metadata",
                "created_at",
            },
        )
        return cls(
            id=_require_string("id", data["id"]),
            kind=_require_string("kind", data["kind"]),
            output=_require_string("output", data["output"]),
            producer_step_id=_require_string(
                "producer_step_id", data["producer_step_id"]
            ),
            producer_role_id=_require_string(
                "producer_role_id", data["producer_role_id"]
            ),
            payload=_require_json_object("payload", data["payload"]),
            metadata=_require_json_object("metadata", data["metadata"]),
            created_at=_require_string("created_at", data["created_at"]),
        )


@dataclass(frozen=True)
class TraceEvent:
    id: str
    type: TraceEventType
    timestamp: str
    run_id: str
    step_id: str | None
    payload: JsonMutableObject | JsonFrozenObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", _coerce_trace_event_type(self.type))
        _require_json_object("payload", self.payload)
        object.__setattr__(self, "payload", _freeze_json_object(self.payload))

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "payload": _thaw_json_object(self.payload),
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "TraceEvent":
        _require_fields(
            "TraceEvent",
            data,
            {"id", "type", "timestamp", "run_id", "step_id", "payload"},
        )
        step_id = data["step_id"]
        if step_id is not None:
            step_id = _require_string("step_id", step_id)
        return cls(
            id=_require_string("id", data["id"]),
            type=TraceEventType.parse(_require_string("type", data["type"])),
            timestamp=_require_string("timestamp", data["timestamp"]),
            run_id=_require_string("run_id", data["run_id"]),
            step_id=step_id,
            payload=_require_json_object("payload", data["payload"]),
        )


@dataclass(frozen=True)
class Trace:
    id: str
    run_id: str
    events: tuple[TraceEvent, ...]

    def __post_init__(self) -> None:
        events = tuple(self.events)
        _require_unique_values("Trace.events.id", (event.id for event in events))
        for event in events:
            if event.run_id != self.run_id:
                raise ValueError("Trace events must match trace run_id")
        object.__setattr__(self, "events", events)

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "events": [event.to_json() for event in self.events],
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Trace":
        _require_fields("Trace", data, {"id", "run_id", "events"})
        events = data["events"]
        if not isinstance(events, list):
            raise TypeError("events must be a JSON array")
        return cls(
            id=_require_string("id", data["id"]),
            run_id=_require_string("run_id", data["run_id"]),
            events=tuple(TraceEvent.from_json(event) for event in events),
        )


@dataclass(frozen=True)
class Run:
    id: str
    protocol: JsonMutableObject | JsonFrozenObject
    status: RunStatus
    input: JsonMutableObject | JsonFrozenObject
    artifacts: tuple[Artifact, ...]
    trace_id: str
    started_at: str
    completed_at: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _coerce_run_status(self.status))
        _require_protocol_ref(self.protocol)
        _require_json_object("input", self.input)
        object.__setattr__(self, "protocol", _freeze_json_object(self.protocol))
        object.__setattr__(self, "input", _freeze_json_object(self.input))
        artifacts = tuple(self.artifacts)
        _require_unique_values("Run.artifacts.id", (artifact.id for artifact in artifacts))
        object.__setattr__(self, "artifacts", artifacts)

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "protocol": _thaw_json_object(self.protocol),
            "status": self.status.value,
            "input": _thaw_json_object(self.input),
            "artifacts": [artifact.to_json() for artifact in self.artifacts],
            "trace_id": self.trace_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Run":
        _require_fields(
            "Run",
            data,
            {
                "id",
                "protocol",
                "status",
                "input",
                "artifacts",
                "trace_id",
                "started_at",
                "completed_at",
            },
        )
        artifacts = data["artifacts"]
        if not isinstance(artifacts, list):
            raise TypeError("artifacts must be a JSON array")
        completed_at = data["completed_at"]
        if completed_at is not None:
            completed_at = _require_string("completed_at", completed_at)
        return cls(
            id=_require_string("id", data["id"]),
            protocol=_require_json_object("protocol", data["protocol"]),
            status=RunStatus.parse(_require_string("status", data["status"])),
            input=_require_json_object("input", data["input"]),
            artifacts=tuple(Artifact.from_json(artifact) for artifact in artifacts),
            trace_id=_require_string("trace_id", data["trace_id"]),
            started_at=_require_string("started_at", data["started_at"]),
            completed_at=completed_at,
        )


def _coerce_run_status(value: RunStatus | str) -> RunStatus:
    if isinstance(value, RunStatus):
        return value
    return RunStatus.parse(value)


def _coerce_trace_event_type(value: TraceEventType | str) -> TraceEventType:
    if isinstance(value, TraceEventType):
        return value
    return TraceEventType.parse(value)


def _require_fields(name: str, data: JsonMutableObject, expected: set[str]) -> None:
    _require_json_object(name, data)
    actual = set(data)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{name} unknown fields: {', '.join(sorted(unknown))}")


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_protocol_ref(value: Any) -> JsonMutableObject | JsonFrozenObject:
    data = _require_json_object("protocol", value)
    _require_fields("protocol", data, {"id", "version"})
    _require_string("protocol.id", data["id"])
    _require_string("protocol.version", data["version"])
    return data


def _require_json_object(name: str, value: Any) -> JsonMutableObject | JsonFrozenObject:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{name} keys must be strings")
        _require_json_value(f"{name}.{key}", item)
    return value


def _require_json_value(name: str, value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError(f"{name} must be JSON-compatible")
        return
    if isinstance(value, Mapping):
        _require_json_object(name, value)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_json_value(f"{name}[{index}]", item)
        return
    raise TypeError(f"{name} must be JSON-compatible")


def _require_unique_values(name: str, values: Any) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{name} values must be unique")
        seen.add(value)


def _freeze_json_object(value: JsonMutableObject | JsonFrozenObject) -> JsonFrozenObject:
    return MappingProxyType({key: _freeze_json_value(item) for key, item in value.items()})


def _freeze_json_value(value: JsonMutableValue | JsonFrozenValue) -> JsonFrozenValue:
    if isinstance(value, Mapping):
        return _freeze_json_object(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_object(value: JsonFrozenObject) -> JsonMutableObject:
    return {key: _thaw_json_value(item) for key, item in value.items()}


def _thaw_json_value(value: JsonFrozenValue) -> JsonMutableValue:
    if isinstance(value, Mapping):
        return _thaw_json_object(value)
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value
