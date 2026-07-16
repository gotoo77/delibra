from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from delibra.app.output_paths import (
    RunOutputPathError,
    RunOutputPaths,
    resolve_run_output_paths,
)
from delibra.app.storage import load_run_json, load_trace_json
from delibra.core import Run, Trace


MAX_DISCOVERY_DIRECTORIES = 2000


class WebPathError(ValueError):
    pass


@dataclass(frozen=True)
class PayloadFieldView:
    label: str
    text: str
    multiline: bool


@dataclass(frozen=True)
class PersistedRun:
    key: str
    label: str
    directory: Path
    run_path: Path
    trace_path: Path
    run: Run | None
    trace: Trace | None
    diagnostic: str | None = None

    @property
    def valid(self) -> bool:
        return self.run is not None and self.trace is not None and self.diagnostic is None

    @property
    def run_label(self) -> str:
        return f"{self.label.rstrip('/')}/run.json" if self.label != "." else "run.json"

    @property
    def trace_label(self) -> str:
        return f"{self.label.rstrip('/')}/trace.json" if self.label != "." else "trace.json"


def prepare_experiments_root(path: str | Path) -> Path:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise WebPathError(f"experiments root is not a directory: {root}")
    return root


def resolve_web_output_paths(root: Path, relative_output_dir: str) -> RunOutputPaths:
    if len(relative_output_dir) > 240:
        raise WebPathError("output directory is too long")
    raw = relative_output_dir.strip()
    if raw == "":
        raise WebPathError("output directory is required")

    relative = Path(raw)
    if relative.is_absolute():
        raise WebPathError("output directory must be relative to experiments root")

    resolved_root = root.resolve(strict=False)
    candidate = root / relative
    resolved_candidate = candidate.resolve(strict=False)
    if not resolved_candidate.is_relative_to(resolved_root):
        raise WebPathError("output directory must stay within experiments root")

    paths = resolve_run_output_paths(
        run_output=None,
        trace_output=None,
        output_dir=str(candidate),
    )
    if paths.run_path.exists() or paths.trace_path.exists():
        raise WebPathError("output directory already contains run.json or trace.json")
    return paths


def discover_runs(root: Path, *, max_directories: int = MAX_DISCOVERY_DIRECTORIES) -> tuple[PersistedRun, ...]:
    resolved_root = root.resolve(strict=False)
    discovered: list[PersistedRun] = []
    visited = 0

    for directory in _walk_directories(root):
        visited += 1
        if visited > max_directories:
            discovered.append(
                PersistedRun(
                    key=".",
                    label=".",
                    directory=root,
                    run_path=root / "run.json",
                    trace_path=root / "trace.json",
                    run=None,
                    trace=None,
                    diagnostic=(
                        f"Discovery stopped after {max_directories} directories; "
                        "narrow the experiments root."
                    ),
                )
            )
            break

        resolved_directory = directory.resolve(strict=False)
        if not resolved_directory.is_relative_to(resolved_root):
            continue
        run_path = directory / "run.json"
        trace_path = directory / "trace.json"
        if not run_path.exists() and not trace_path.exists():
            continue
        discovered.append(_load_persisted_run(root, directory, run_path, trace_path))

    return tuple(sorted(discovered, key=lambda item: item.label))


def persisted_run_by_key(root: Path, key: str) -> PersistedRun:
    if len(key) > 300:
        raise WebPathError("run key is too long")
    relative = Path(key)
    if relative.is_absolute():
        raise WebPathError("run key must be relative")
    directory = root / relative
    resolved_root = root.resolve(strict=False)
    if not directory.resolve(strict=False).is_relative_to(resolved_root):
        raise WebPathError("run key must stay within experiments root")
    item = _load_persisted_run(root, directory, directory / "run.json", directory / "trace.json")
    if not item.valid:
        raise WebPathError(item.diagnostic or "run is not readable")
    return item


def artifact_payload_text(value: object) -> str:
    return json.dumps(_plain_json(value), indent=2, sort_keys=True, ensure_ascii=False)


def payload_primary_text(value: object) -> str | None:
    data = _plain_json(value)
    if isinstance(data, Mapping):
        for key in ("content", "text", "summary", "final", "answer"):
            item = data.get(key)
            if isinstance(item, str) and item != "":
                return item
    if isinstance(data, str) and data != "":
        return data
    return None


def payload_fields(value: object) -> tuple[PayloadFieldView, ...]:
    data = _plain_json(value)
    if not isinstance(data, Mapping):
        if data in ({}, [], None, ""):
            return ()
        text = _field_text(data)
        return (PayloadFieldView(label="value", text=text, multiline=_is_multiline(text)),)

    fields: list[PayloadFieldView] = []
    for key, item in data.items():
        if key in {"content", "text", "summary", "final", "answer"} and isinstance(item, str):
            continue
        if item in ({}, [], None, ""):
            continue
        text = _field_text(item)
        fields.append(
            PayloadFieldView(label=str(key), text=text, multiline=_is_multiline(text))
        )
    return tuple(fields)


def _plain_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain_json(item) for item in value]
    return value


def _field_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _is_multiline(value: str) -> bool:
    return "\n" in value or len(value) > 120


def _walk_directories(root: Path):
    yield root
    for directory in root.rglob("*"):
        if directory.is_dir():
            yield directory


def _load_persisted_run(root: Path, directory: Path, run_path: Path, trace_path: Path) -> PersistedRun:
    label = _relative_label(root, directory)
    key = label
    if not run_path.exists() or not trace_path.exists():
        return PersistedRun(
            key=key,
            label=label,
            directory=directory,
            run_path=run_path,
            trace_path=trace_path,
            run=None,
            trace=None,
            diagnostic="directory must contain both run.json and trace.json",
        )

    try:
        run = load_run_json(run_path)
        trace = load_trace_json(trace_path)
        if trace.run_id != run.id:
            raise ValueError("trace run_id does not match run id")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return PersistedRun(
            key=key,
            label=label,
            directory=directory,
            run_path=run_path,
            trace_path=trace_path,
            run=None,
            trace=None,
            diagnostic=str(exc),
        )

    return PersistedRun(
        key=key,
        label=label,
        directory=directory,
        run_path=run_path,
        trace_path=trace_path,
        run=run,
        trace=trace,
    )


def _relative_label(root: Path, directory: Path) -> str:
    try:
        label = directory.relative_to(root).as_posix()
    except ValueError:
        label = directory.name
    return "." if label == "" else label
