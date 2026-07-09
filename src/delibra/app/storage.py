from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol as TypingProtocol

from delibra.core import Run, Trace
from delibra.core.json import JsonMutableObject


class RunTraceResult(TypingProtocol):
    run: Run
    trace: Trace


def write_run_outputs(
    result: RunTraceResult,
    *,
    run_path: str | Path,
    trace_path: str | Path,
) -> None:
    Path(run_path).write_text(
        json.dumps(result.run.to_json(), indent=2),
        encoding="utf-8",
    )
    Path(trace_path).write_text(
        json.dumps(result.trace.to_json(), indent=2),
        encoding="utf-8",
    )


def load_run_json(path: str | Path) -> Run:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"run file not found: {path}") from exc
    return Run.from_json(load_json_object(raw, "run JSON"))


def load_trace_json(path: str | Path) -> Trace:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"trace file not found: {path}") from exc
    return Trace.from_json(load_json_object(raw, "trace JSON"))


def load_json_object(raw: str, name: str) -> JsonMutableObject:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be a JSON object")
    return data
