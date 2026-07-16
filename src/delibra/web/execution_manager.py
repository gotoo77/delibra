from __future__ import annotations

import asyncio
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from delibra.app.run import RunProtocolApplicationRequest, run_protocol_application
from delibra.runtime import EngineExecutionError, EngineProgressEvent


ExecutionStatus = str
MAX_PROGRESS_EVENTS = 1000


@dataclass(frozen=True)
class WebProgressEvent:
    sequence: int
    elapsed_seconds: float
    event: EngineProgressEvent


@dataclass
class WebExecution:
    id: str
    request: RunProtocolApplicationRequest
    status: ExecutionStatus = "queued"
    created_at_monotonic: float = field(default_factory=time.monotonic)
    started_at_monotonic: float | None = None
    completed_at_monotonic: float | None = None
    progress: list[WebProgressEvent] = field(default_factory=list)
    next_progress_sequence: int = 1
    error: str | None = None
    run_path: Path | None = None
    trace_path: Path | None = None
    artifact_count: int | None = None
    show_progress: bool = True

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at_monotonic or time.monotonic()
        start = self.started_at_monotonic or self.created_at_monotonic
        return end - start


class ExecutionLimitError(RuntimeError):
    pass


class ExecutionManager:
    def __init__(self, *, max_active: int = 1) -> None:
        self.max_active = max_active
        self._executions: dict[str, WebExecution] = {}
        self._lock = threading.Lock()

    def start(
        self,
        request: RunProtocolApplicationRequest,
        *,
        show_progress: bool = True,
    ) -> WebExecution:
        with self._lock:
            active = sum(
                1
                for execution in self._executions.values()
                if execution.status in {"queued", "running"}
            )
            if active >= self.max_active:
                raise ExecutionLimitError("another run is already active")

            execution = WebExecution(
                id=uuid4().hex,
                request=request,
                show_progress=show_progress,
            )
            self._executions[execution.id] = execution

        asyncio.create_task(asyncio.to_thread(self._run, execution.id))
        return execution

    def get(self, execution_id: str) -> WebExecution | None:
        with self._lock:
            return self._executions.get(execution_id)

    def snapshot(self, execution_id: str) -> WebExecution | None:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                return None
            return WebExecution(
                id=execution.id,
                request=execution.request,
                status=execution.status,
                created_at_monotonic=execution.created_at_monotonic,
                started_at_monotonic=execution.started_at_monotonic,
                completed_at_monotonic=execution.completed_at_monotonic,
                progress=list(execution.progress),
                next_progress_sequence=execution.next_progress_sequence,
                error=execution.error,
                run_path=execution.run_path,
                trace_path=execution.trace_path,
                artifact_count=execution.artifact_count,
                show_progress=execution.show_progress,
            )

    def events_after(self, execution_id: str, sequence: int) -> list[WebProgressEvent]:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                return []
            return [event for event in execution.progress if event.sequence > sequence]

    def _run(self, execution_id: str) -> None:
        with self._lock:
            execution = self._executions[execution_id]
            execution.status = "running"
            execution.started_at_monotonic = time.monotonic()

        def progress(event: EngineProgressEvent) -> None:
            self._append_progress(execution_id, event)

        request = RunProtocolApplicationRequest(
            protocol=execution.request.protocol,
            input_ref=execution.request.input_ref,
            provider=execution.request.provider,
            output_paths=execution.request.output_paths,
            policy=execution.request.policy,
            language=execution.request.language,
            progress=progress if execution.show_progress else None,
        )
        try:
            result = run_protocol_application(request)
        except EngineExecutionError as exc:
            with self._lock:
                execution = self._executions[execution_id]
                execution.status = "failed"
                execution.error = _safe_error_message(exc)
                execution.completed_at_monotonic = time.monotonic()
                execution.run_path = request.output_paths.run_path
                execution.trace_path = request.output_paths.trace_path
                execution.artifact_count = len(exc.result.run.artifacts)
            return
        except Exception as exc:
            with self._lock:
                execution = self._executions[execution_id]
                execution.status = "failed"
                execution.error = _safe_error_message(exc)
                execution.completed_at_monotonic = time.monotonic()
            return

        with self._lock:
            execution = self._executions[execution_id]
            execution.status = "completed"
            execution.completed_at_monotonic = time.monotonic()
            execution.run_path = result.run_path
            execution.trace_path = result.trace_path
            execution.artifact_count = len(result.result.run.artifacts)

    def _append_progress(self, execution_id: str, event: EngineProgressEvent) -> None:
        with self._lock:
            execution = self._executions[execution_id]
            start = execution.started_at_monotonic or execution.created_at_monotonic
            execution.progress.append(
                WebProgressEvent(
                    sequence=execution.next_progress_sequence,
                    elapsed_seconds=time.monotonic() - start,
                    event=event,
                )
            )
            execution.next_progress_sequence += 1
            if len(execution.progress) > MAX_PROGRESS_EVENTS:
                del execution.progress[: len(execution.progress) - MAX_PROGRESS_EVENTS]


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    if message == "":
        message = exc.__class__.__name__
    message = _redact_environment_secrets(message)
    return message[:1000]


def _redact_environment_secrets(message: str) -> str:
    redacted = message
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    for name, value in os.environ.items():
        if len(value) < 8:
            continue
        if any(marker in name.upper() for marker in secret_markers):
            redacted = redacted.replace(value, "[redacted]")
    return redacted
