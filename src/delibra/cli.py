from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from delibra import __version__
from delibra.core import Run, Trace
from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml
from delibra.protocol_validator import ProtocolValidationError, validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    EngineProgressEvent,
    IdSequence,
    MockLLMClient,
    MockLLMError,
    OllamaClient,
    OllamaConfigError,
    OllamaProviderError,
    OpenAIClient,
    OpenAIConfigError,
    OpenAIProviderError,
    UnsupportedStepKindError,
    default_engine_ids,
    deterministic_clock,
    execute_protocol,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="delibra",
        description="Artifact-first deliberation orchestration.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"delibra {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    validate = subparsers.add_parser(
        "validate",
        help="parse a protocol definition",
        description="Parse a protocol definition.",
    )
    validate.add_argument(
        "--protocol",
        required=True,
        help="path to a protocol YAML file",
    )
    validate.set_defaults(handler=_validate)

    run = subparsers.add_parser(
        "run",
        help="run a protocol with the selected provider",
        description="Run a protocol with the selected provider.",
    )
    run.add_argument("--protocol", required=True, help="path to a protocol YAML file")
    run.add_argument(
        "--provider",
        choices=("mock", "openai", "ollama"),
        default="mock",
        help="provider: mock, openai, ollama; default mock",
    )
    run.add_argument("--input-text", required=True, help="text input for the run")
    run.add_argument("--run-output", required=True, help="path to write run JSON")
    run.add_argument("--trace-output", required=True, help="path to write trace JSON")
    run.add_argument(
        "--progress",
        action="store_true",
        help="print run progress to stderr",
    )
    run.set_defaults(handler=_run)

    inspect = subparsers.add_parser(
        "inspect",
        help="inspect canonical run and trace JSON",
        description="Inspect canonical run and trace JSON.",
    )
    inspect.add_argument("--run", required=True, help="path to canonical run JSON")
    inspect.add_argument("--trace", help="path to canonical trace JSON")
    inspect.set_defaults(handler=_inspect)

    analyze_run = subparsers.add_parser(
        "analyze-run",
        help="analyze canonical run and trace metrics",
        description="Analyze canonical run and trace metrics.",
    )
    analyze_run.add_argument("--run", required=True, help="path to canonical run JSON")
    analyze_run.add_argument("--trace", help="path to canonical trace JSON")
    analyze_run.set_defaults(handler=_analyze_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return handler(args)


def _validate(args: argparse.Namespace) -> int:
    try:
        protocol = load_protocol_yaml(args.protocol)
    except ProtocolLoadError as exc:
        print(f"delibra validate: {exc}", file=sys.stderr)
        return 1
    try:
        validate_protocol(protocol)
    except ProtocolValidationError as exc:
        print(f"delibra validate: invalid protocol: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(protocol.to_json(), indent=2))
    return 0


def _run(args: argparse.Namespace) -> int:
    try:
        protocol = load_protocol_yaml(args.protocol)
    except ProtocolLoadError as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1

    try:
        ids = default_engine_ids()
        result = execute_protocol(
            protocol,
            {"kind": "text", "content": args.input_text},
            llm=_build_llm_client(args.provider),
            ids=ids,
            clock=deterministic_clock(),
            progress=_build_progress_printer(args.provider) if args.progress else None,
        )
    except EngineExecutionError as exc:
        _write_run_outputs(args, exc.result)
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1
    except (
        ProtocolValidationError,
        UnsupportedStepKindError,
        MockLLMError,
        OllamaConfigError,
        OllamaProviderError,
        OpenAIConfigError,
        OpenAIProviderError,
        ValueError,
    ) as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1

    _write_run_outputs(args, result)
    return 0


def _build_progress_printer(provider: str):
    def print_progress(event: EngineProgressEvent) -> None:
        print(_render_progress_event(event, provider), file=sys.stderr)

    return print_progress


def _render_progress_event(event: EngineProgressEvent, provider: str) -> str:
    prefix = "delibra run:"
    if event.type == "run_started":
        return (
            f"{prefix} started run={event.run_id} "
            f"protocol={event.protocol_id}@{event.protocol_version} "
            f"provider={provider}"
        )
    if event.type == "step_started":
        return f"{prefix} step started step={event.step_id} kind={event.step_kind}"
    if event.type == "role_started":
        return (
            f"{prefix} role started step={event.step_id} "
            f"role={event.role_id}"
        )
    if event.type == "role_completed":
        return (
            f"{prefix} role completed step={event.step_id} "
            f"role={event.role_id} artifact={event.artifact_id}"
        )
    if event.type == "step_completed":
        return (
            f"{prefix} step completed step={event.step_id} "
            f"artifacts={event.artifact_count}"
        )
    if event.type == "run_completed":
        return f"{prefix} completed artifacts={event.artifact_count}"
    if event.type == "run_failed":
        return (
            f"{prefix} failed step={event.step_id} "
            f"artifacts={event.artifact_count}"
        )
    return f"{prefix} {event.type}"


def _build_llm_client(provider: str):
    if provider == "mock":
        return MockLLMClient(IdSequence("msg_response"))
    if provider == "openai":
        return OpenAIClient.from_env(response_message_ids=IdSequence("msg_response"))
    if provider == "ollama":
        return OllamaClient.from_env(response_message_ids=IdSequence("msg_response"))
    raise ValueError(f"unsupported provider: {provider}")


def _write_run_outputs(args: argparse.Namespace, result) -> None:
    Path(args.run_output).write_text(json.dumps(result.run.to_json(), indent=2), encoding="utf-8")
    Path(args.trace_output).write_text(
        json.dumps(result.trace.to_json(), indent=2),
        encoding="utf-8",
    )


def _inspect(args: argparse.Namespace) -> int:
    try:
        run = _load_run_json(args.run)
        trace = None if args.trace is None else _load_trace_json(args.trace)
        if trace is not None and trace.run_id != run.id:
            raise ValueError("trace run_id does not match run id")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"delibra inspect: {exc}", file=sys.stderr)
        return 1

    print(_render_inspection(run, trace))
    return 0


def _analyze_run(args: argparse.Namespace) -> int:
    try:
        run = _load_run_json(args.run)
        trace = None if args.trace is None else _load_trace_json(args.trace)
        if trace is not None and trace.run_id != run.id:
            raise ValueError("trace run_id does not match run id")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"delibra analyze-run: {exc}", file=sys.stderr)
        return 1

    print(_render_run_analysis(run, trace))
    return 0


def _load_run_json(path: str) -> Run:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"run file not found: {path}") from exc
    return Run.from_json(_load_json_object(raw, "run JSON"))


def _load_trace_json(path: str) -> Trace:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"trace file not found: {path}") from exc
    return Trace.from_json(_load_json_object(raw, "trace JSON"))


def _load_json_object(raw: str, name: str):
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError(f"{name} must be a JSON object")
    return data


def _render_inspection(run: Run, trace: Trace | None) -> str:
    protocol = run.protocol
    lines = [
        f"run: {run.id}",
        f"status: {run.status.value}",
        f"protocol: {protocol['id']}@{protocol['version']}",
        f"artifacts: {len(run.artifacts)}",
        "artifact_summary:",
    ]
    for artifact in run.artifacts:
        lines.append(
            "  "
            f"- output={artifact.output} "
            f"kind={artifact.kind} "
            f"producer_step_id={artifact.producer_step_id} "
            f"producer_role_id={artifact.producer_role_id}"
        )
    if trace is not None:
        lines.append(f"trace_events: {len(trace.events)}")
    return "\n".join(lines)


@dataclass(frozen=True)
class _ArtifactMetric:
    artifact_id: str
    output: str
    kind: str
    step_id: str
    role_id: str
    payload_chars: int
    total_chars: int


def _render_run_analysis(run: Run, trace: Trace | None) -> str:
    metrics = _artifact_metrics(run)
    total_payload_chars = sum(metric.payload_chars for metric in metrics)
    total_artifact_chars = sum(metric.total_chars for metric in metrics)
    largest = max(metrics, key=lambda metric: metric.payload_chars, default=None)
    average_payload_chars = (
        0 if len(metrics) == 0 else round(total_payload_chars / len(metrics))
    )
    context_estimates = _context_pressure_estimates(run, metrics)
    largest_context = max(
        context_estimates,
        key=lambda item: item[1],
        default=(None, 0),
    )
    step_groups = _group_artifacts_by_step(metrics)
    repeated_outputs = _repeated_outputs(metrics)
    duration_seconds = _duration_seconds(run.started_at, run.completed_at)

    lines = [
        "Protocol metrics",
        "----------------",
        f"run: {run.id}",
        f"status: {run.status.value}",
        f"protocol: {run.protocol['id']}@{run.protocol['version']}",
        f"artifacts: {len(metrics)}",
    ]
    if trace is not None:
        lines.append(f"trace_events: {len(trace.events)}")
    if duration_seconds is not None:
        lines.append(f"duration_seconds: {duration_seconds:g}")

    lines.extend(
        [
            "",
            "Artifact sizes",
            "--------------",
            f"total_payload_chars: {total_payload_chars}",
            f"total_artifact_json_chars: {total_artifact_chars}",
            f"average_payload_chars: {average_payload_chars}",
        ]
    )
    if largest is not None:
        lines.append(
            "largest_artifact: "
            f"{largest.artifact_id} "
            f"output={largest.output} "
            f"step={largest.step_id} "
            f"role={largest.role_id} "
            f"payload_chars={largest.payload_chars}"
        )

    lines.extend(["", "Step production", "---------------"])
    for step_id, group in step_groups:
        role_ids = sorted({metric.role_id for metric in group})
        kind_labels = sorted({metric.kind for metric in group})
        lines.append(
            f"- {step_id}: artifacts={len(group)} "
            f"roles={len(role_ids)} "
            f"kinds={','.join(kind_labels)} "
            f"role_ids={','.join(role_ids)}"
        )

    lines.extend(["", "Fanout-like steps", "-----------------"])
    fanout_like = [(step_id, group) for step_id, group in step_groups if len(group) > 1]
    if not fanout_like:
        lines.append("- none observed")
    for step_id, group in fanout_like:
        lines.append(f"- {step_id}: {len(group)} roles")

    lines.extend(["", "Critique-like steps", "-------------------"])
    critique_like = [
        (step_id, group)
        for step_id, group in step_groups
        if any(metric.kind == "critique" or "critique" in metric.output for metric in group)
    ]
    if not critique_like:
        lines.append("- none observed")
    for step_id, group in critique_like:
        lines.append(f"- {step_id}: {len(group)} roles")

    lines.extend(
        [
            "",
            "Context pressure estimates",
            "--------------------------",
            f"input_chars: {_json_chars(run.input)}",
            f"cumulative_artifact_context_chars_upper_bound: {sum(chars for _, chars in context_estimates)}",
        ]
    )
    if largest_context[0] is not None:
        lines.append(
            "largest_pre_call_context_upper_bound: "
            f"before_artifact={largest_context[0]} chars={largest_context[1]}"
        )
    lines.append("estimated_tokens_upper_bound: " f"{_rough_token_count(sum(chars for _, chars in context_estimates))}")

    lines.extend(["", "Repeated information signals", "----------------------------"])
    if not repeated_outputs:
        lines.append("- no repeated artifact outputs")
    for output, count in repeated_outputs:
        lines.append(f"- output={output} artifacts={count}")

    lines.extend(["", "Potential bottlenecks", "---------------------"])
    bottlenecks = _potential_bottlenecks(metrics, largest_context)
    if not bottlenecks:
        lines.append("- none obvious from persisted run data")
    else:
        lines.extend(f"- {item}" for item in bottlenecks)

    lines.extend(
        [
            "",
            "Limitations",
            "-----------",
            "- Exact provider input sizes, token usage, latency, and cost are not persisted in run.json or trace.json.",
            "- Context metrics above are deterministic upper-bound estimates from persisted input and artifacts, not provider billing data.",
        ]
    )
    return "\n".join(lines)


def _artifact_metrics(run: Run) -> list[_ArtifactMetric]:
    return [
        _ArtifactMetric(
            artifact_id=artifact.id,
            output=artifact.output,
            kind=artifact.kind,
            step_id=artifact.producer_step_id,
            role_id=artifact.producer_role_id,
            payload_chars=_json_chars(artifact.to_json()["payload"]),
            total_chars=_json_chars(artifact.to_json()),
        )
        for artifact in run.artifacts
    ]


def _group_artifacts_by_step(
    metrics: list[_ArtifactMetric],
) -> list[tuple[str, list[_ArtifactMetric]]]:
    groups: list[tuple[str, list[_ArtifactMetric]]] = []
    by_step: dict[str, list[_ArtifactMetric]] = {}
    for metric in metrics:
        if metric.step_id not in by_step:
            by_step[metric.step_id] = []
            groups.append((metric.step_id, by_step[metric.step_id]))
        by_step[metric.step_id].append(metric)
    return groups


def _repeated_outputs(metrics: list[_ArtifactMetric]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for metric in metrics:
        counts[metric.output] = counts.get(metric.output, 0) + 1
    return sorted((output, count) for output, count in counts.items() if count > 1)


def _context_pressure_estimates(
    run: Run,
    metrics: list[_ArtifactMetric],
) -> list[tuple[str, int]]:
    input_chars = _json_chars(run.input)
    estimates: list[tuple[str, int]] = []
    prior_artifact_chars = 0
    for metric in metrics:
        estimates.append((metric.artifact_id, input_chars + prior_artifact_chars))
        prior_artifact_chars += metric.total_chars
    return estimates


def _potential_bottlenecks(
    metrics: list[_ArtifactMetric],
    largest_context: tuple[str | None, int],
) -> list[str]:
    bottlenecks: list[str] = []
    largest_artifact = max(metrics, key=lambda metric: metric.payload_chars, default=None)
    if largest_artifact is not None and largest_artifact.payload_chars > 8000:
        bottlenecks.append(
            "large artifact payload may dominate later synthesis: "
            f"{largest_artifact.artifact_id} payload_chars={largest_artifact.payload_chars}"
        )
    if largest_context[1] > 30000:
        bottlenecks.append(
            "large accumulated context estimate before a later call: "
            f"{largest_context[1]} chars"
        )
    for step_id, group in _group_artifacts_by_step(metrics):
        if len(group) >= 4:
            bottlenecks.append(
                f"multi-role step creates broad context fan-in pressure: {step_id} roles={len(group)}"
            )
    return bottlenecks


def _json_chars(value) -> int:
    return len(json.dumps(_plain_json(value), ensure_ascii=False, sort_keys=True))


def _plain_json(value):
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    return value


def _rough_token_count(chars: int) -> int:
    return round(chars / 4)


def _duration_seconds(started_at: str, completed_at: str | None) -> float | None:
    if completed_at is None:
        return None
    try:
        started = _parse_timestamp(started_at)
        completed = _parse_timestamp(completed_at)
    except ValueError:
        return None
    return (completed - started).total_seconds()


def _parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler
