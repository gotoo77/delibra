from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from delibra.core import Run, Trace


@dataclass(frozen=True)
class ArtifactMetric:
    artifact_id: str
    output: str
    kind: str
    step_id: str
    role_id: str
    payload_chars: int
    total_chars: int


@dataclass(frozen=True)
class StepProduction:
    step_id: str
    artifact_count: int
    role_count: int
    kind_labels: tuple[str, ...]
    role_ids: tuple[str, ...]


@dataclass(frozen=True)
class StepRoleCount:
    step_id: str
    role_count: int


@dataclass(frozen=True)
class RepeatedOutput:
    output: str
    artifact_count: int


@dataclass(frozen=True)
class ContextEstimate:
    before_artifact_id: str
    chars: int


@dataclass(frozen=True)
class RunAnalysis:
    run_id: str
    status: str
    protocol_id: str
    protocol_version: str
    artifact_count: int
    trace_event_count: int | None
    duration_seconds: float | None
    artifact_metrics: tuple[ArtifactMetric, ...]
    total_payload_chars: int
    total_artifact_json_chars: int
    average_payload_chars: int
    largest_artifact: ArtifactMetric | None
    step_productions: tuple[StepProduction, ...]
    fanout_like_steps: tuple[StepRoleCount, ...]
    critique_like_steps: tuple[StepRoleCount, ...]
    input_chars: int
    context_estimates: tuple[ContextEstimate, ...]
    cumulative_artifact_context_chars_upper_bound: int
    largest_pre_call_context: ContextEstimate | None
    estimated_tokens_upper_bound: int
    repeated_outputs: tuple[RepeatedOutput, ...]
    potential_bottlenecks: tuple[str, ...]
    limitations: tuple[str, ...]


LIMITATIONS = (
    "Exact provider input sizes, token usage, latency, and cost are not persisted in run.json or trace.json.",
    "Context metrics above are deterministic upper-bound estimates from persisted input and artifacts, not provider billing data.",
)


def analyze_run(run: Run, trace: Trace | None = None) -> RunAnalysis:
    metrics = tuple(_artifact_metrics(run))
    total_payload_chars = sum(metric.payload_chars for metric in metrics)
    total_artifact_chars = sum(metric.total_chars for metric in metrics)
    largest = max(metrics, key=lambda metric: metric.payload_chars, default=None)
    average_payload_chars = (
        0 if len(metrics) == 0 else round(total_payload_chars / len(metrics))
    )
    context_estimates = tuple(_context_pressure_estimates(run, metrics))
    largest_context = max(
        context_estimates,
        key=lambda item: item.chars,
        default=None,
    )
    step_groups = _group_artifacts_by_step(metrics)
    repeated_outputs = tuple(
        RepeatedOutput(output=output, artifact_count=count)
        for output, count in _repeated_outputs(metrics)
    )
    cumulative_context_chars = sum(item.chars for item in context_estimates)

    return RunAnalysis(
        run_id=run.id,
        status=run.status.value,
        protocol_id=str(run.protocol["id"]),
        protocol_version=str(run.protocol["version"]),
        artifact_count=len(metrics),
        trace_event_count=None if trace is None else len(trace.events),
        duration_seconds=_duration_seconds(run.started_at, run.completed_at),
        artifact_metrics=metrics,
        total_payload_chars=total_payload_chars,
        total_artifact_json_chars=total_artifact_chars,
        average_payload_chars=average_payload_chars,
        largest_artifact=largest,
        step_productions=tuple(_step_productions(step_groups)),
        fanout_like_steps=tuple(
            StepRoleCount(step_id=step_id, role_count=len(group))
            for step_id, group in step_groups
            if len(group) > 1
        ),
        critique_like_steps=tuple(
            StepRoleCount(step_id=step_id, role_count=len(group))
            for step_id, group in step_groups
            if any(
                metric.kind == "critique" or "critique" in metric.output
                for metric in group
            )
        ),
        input_chars=_json_chars(run.input),
        context_estimates=context_estimates,
        cumulative_artifact_context_chars_upper_bound=cumulative_context_chars,
        largest_pre_call_context=largest_context,
        estimated_tokens_upper_bound=_rough_token_count(cumulative_context_chars),
        repeated_outputs=repeated_outputs,
        potential_bottlenecks=tuple(_potential_bottlenecks(metrics, largest_context)),
        limitations=LIMITATIONS,
    )


def _artifact_metrics(run: Run) -> list[ArtifactMetric]:
    return [
        ArtifactMetric(
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
    metrics: tuple[ArtifactMetric, ...],
) -> list[tuple[str, list[ArtifactMetric]]]:
    groups: list[tuple[str, list[ArtifactMetric]]] = []
    by_step: dict[str, list[ArtifactMetric]] = {}
    for metric in metrics:
        if metric.step_id not in by_step:
            by_step[metric.step_id] = []
            groups.append((metric.step_id, by_step[metric.step_id]))
        by_step[metric.step_id].append(metric)
    return groups


def _step_productions(
    step_groups: list[tuple[str, list[ArtifactMetric]]],
) -> list[StepProduction]:
    productions: list[StepProduction] = []
    for step_id, group in step_groups:
        role_ids = tuple(sorted({metric.role_id for metric in group}))
        kind_labels = tuple(sorted({metric.kind for metric in group}))
        productions.append(
            StepProduction(
                step_id=step_id,
                artifact_count=len(group),
                role_count=len(role_ids),
                kind_labels=kind_labels,
                role_ids=role_ids,
            )
        )
    return productions


def _repeated_outputs(metrics: tuple[ArtifactMetric, ...]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for metric in metrics:
        counts[metric.output] = counts.get(metric.output, 0) + 1
    return sorted((output, count) for output, count in counts.items() if count > 1)


def _context_pressure_estimates(
    run: Run,
    metrics: tuple[ArtifactMetric, ...],
) -> list[ContextEstimate]:
    input_chars = _json_chars(run.input)
    estimates: list[ContextEstimate] = []
    prior_artifact_chars = 0
    for metric in metrics:
        estimates.append(
            ContextEstimate(
                before_artifact_id=metric.artifact_id,
                chars=input_chars + prior_artifact_chars,
            )
        )
        prior_artifact_chars += metric.total_chars
    return estimates


def _potential_bottlenecks(
    metrics: tuple[ArtifactMetric, ...],
    largest_context: ContextEstimate | None,
) -> list[str]:
    bottlenecks: list[str] = []
    largest_artifact = max(metrics, key=lambda metric: metric.payload_chars, default=None)
    if largest_artifact is not None and largest_artifact.payload_chars > 8000:
        bottlenecks.append(
            "large artifact payload may dominate later synthesis: "
            f"{largest_artifact.artifact_id} payload_chars={largest_artifact.payload_chars}"
        )
    if largest_context is not None and largest_context.chars > 30000:
        bottlenecks.append(
            "large accumulated context estimate before a later call: "
            f"{largest_context.chars} chars"
        )
    for step_id, group in _group_artifacts_by_step(metrics):
        if len(group) >= 4:
            bottlenecks.append(
                f"multi-role step creates broad context fan-in pressure: {step_id} roles={len(group)}"
            )
    return bottlenecks


def _json_chars(value: Any) -> int:
    return len(json.dumps(_plain_json(value), ensure_ascii=False, sort_keys=True))


def _plain_json(value: Any) -> Any:
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
