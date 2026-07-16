from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunOutputPaths:
    run_path: Path
    trace_path: Path
    output_dir: Path | None

    @property
    def uses_output_dir(self) -> bool:
        return self.output_dir is not None


class RunOutputPathError(ValueError):
    pass


def resolve_run_output_paths(
    *,
    run_output: str | None,
    trace_output: str | None,
    output_dir: str | None,
) -> RunOutputPaths:
    if output_dir is None:
        if run_output is None or trace_output is None:
            raise RunOutputPathError(
                "--run-output and --trace-output are required unless --output-dir is provided"
            )
        run_path = Path(run_output)
        trace_path = Path(trace_output)
    else:
        root = Path(output_dir)
        run_path = _resolve_below_output_dir(
            root,
            "run-output",
            Path("run.json") if run_output is None else Path(run_output),
        )
        trace_path = _resolve_below_output_dir(
            root,
            "trace-output",
            Path("trace.json") if trace_output is None else Path(trace_output),
        )

    if _same_path(run_path, trace_path):
        raise RunOutputPathError("run and trace output paths must be different")

    return RunOutputPaths(
        run_path=run_path,
        trace_path=trace_path,
        output_dir=None if output_dir is None else Path(output_dir),
    )


def prepare_run_output_paths(paths: RunOutputPaths) -> None:
    if paths.output_dir is None:
        return

    try:
        paths.output_dir.mkdir(parents=True, exist_ok=True)
        paths.run_path.parent.mkdir(parents=True, exist_ok=True)
        paths.trace_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError as exc:
        raise RunOutputPathError(
            f"output directory path is not a directory: {exc.filename}"
        ) from exc
    except OSError as exc:
        raise OSError(f"could not create output directory: {exc}") from exc


def _resolve_below_output_dir(root: Path, option_name: str, path: Path) -> Path:
    if path.is_absolute():
        raise RunOutputPathError(
            f"--{option_name} must be relative when --output-dir is provided"
        )

    resolved_root = root.resolve(strict=False)
    resolved_path = (root / path).resolve(strict=False)
    if not resolved_path.is_relative_to(resolved_root):
        raise RunOutputPathError(
            f"--{option_name} must stay within --output-dir"
        )
    return root / path


def _same_path(first: Path, second: Path) -> bool:
    return first.resolve(strict=False) == second.resolve(strict=False)
