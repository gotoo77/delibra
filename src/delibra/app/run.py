from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from delibra.app.models import ProviderConfig
from delibra.app.output_paths import (
    RunOutputPaths,
    prepare_run_output_paths,
)
from delibra.app.providers import build_llm_client
from delibra.app.storage import write_run_outputs
from delibra.core import Protocol
from delibra.core.json import JsonMutableObject
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    EngineProgressEvent,
    EngineResult,
    ProgressCallback,
    SystemClock,
    default_engine_ids,
    execute_protocol,
)
from delibra.runtime.language import RequestedLanguage
from delibra.runtime.policy import ExecutionPolicy


@dataclass(frozen=True)
class RunProtocolApplicationRequest:
    protocol: Protocol
    input_ref: JsonMutableObject
    provider: ProviderConfig
    output_paths: RunOutputPaths
    policy: ExecutionPolicy | None = None
    language: RequestedLanguage | str = RequestedLanguage.AUTO
    progress: ProgressCallback | None = None


@dataclass(frozen=True)
class RunProtocolApplicationResult:
    result: EngineResult
    run_path: Path
    trace_path: Path


def run_protocol_application(
    request: RunProtocolApplicationRequest,
) -> RunProtocolApplicationResult:
    validate_protocol(request.protocol)
    prepare_run_output_paths(request.output_paths)
    result = _execute(request)
    write_run_outputs(
        result,
        run_path=request.output_paths.run_path,
        trace_path=request.output_paths.trace_path,
    )
    return RunProtocolApplicationResult(
        result=result,
        run_path=request.output_paths.run_path,
        trace_path=request.output_paths.trace_path,
    )


def _execute(request: RunProtocolApplicationRequest) -> EngineResult:
    try:
        return execute_protocol(
            request.protocol,
            request.input_ref,
            llm=build_llm_client(request.provider),
            ids=default_engine_ids(),
            clock=SystemClock(),
            policy=request.policy,
            language=request.language,
            progress=request.progress,
        )
    except EngineExecutionError as exc:
        write_run_outputs(
            exc.result,
            run_path=request.output_paths.run_path,
            trace_path=request.output_paths.trace_path,
        )
        raise


__all__ = [
    "EngineProgressEvent",
    "RunProtocolApplicationRequest",
    "RunProtocolApplicationResult",
    "run_protocol_application",
]
