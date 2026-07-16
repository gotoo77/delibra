from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from delibra.app.storage import load_json_object, load_run_json, load_trace_json
from delibra.core import Artifact, Run, Trace, TraceEventType


@dataclass(frozen=True)
class RunTraceFiles:
    run_path: Path
    trace_path: Path


@dataclass(frozen=True)
class ProtocolPosition:
    step_id: str
    role_id: str
    output: str
    artifact_kind: str
    ordinal: int

    @property
    def key(self) -> str:
        return (
            f"{self.step_id} / {self.role_id} / {self.output} / "
            f"{self.artifact_kind} / {self.ordinal}"
        )


@dataclass(frozen=True)
class ObservedArtifact:
    artifact_id: str
    position: ProtocolPosition
    production_order: int
    payload_chars: int
    artifact_json_chars: int
    created_at: str
    trace_event_id: str | None
    trace_timestamp: str | None


@dataclass(frozen=True)
class ObservedRun:
    label: str
    run_path: Path
    trace_path: Path
    run_id: str
    trace_id: str
    status: str
    protocol_id: str
    protocol_version: str
    input_digest: str
    input_display: str
    started_at: str
    completed_at: str | None
    trace_event_count: int
    artifacts: tuple[ObservedArtifact, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class AlignedPosition:
    position: ProtocolPosition
    artifacts_by_label: tuple[tuple[str, ObservedArtifact | None], ...]


@dataclass(frozen=True)
class ManifestRunMetadata:
    label: str | None
    run_file: str | None
    trace_file: str | None
    execution_environment: Mapping[str, Any] | None
    parameters: Mapping[str, Any] | None


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str | None
    protocol_id: str | None
    protocol_version: str | None
    input_digest: str | None
    input_text: str | None
    controlled_dimensions: tuple[str, ...]
    changed_dimensions: tuple[str, ...]
    runs: tuple[ManifestRunMetadata, ...]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class ComparabilityAssessment:
    classification: str
    controlled_dimensions: tuple[str, ...]
    changed_dimensions: tuple[str, ...]
    reservations: tuple[str, ...]
    incompatibilities: tuple[str, ...]
    manifest_inconsistencies: tuple[str, ...]


@dataclass(frozen=True)
class MechanicalComparison:
    runs: tuple[ObservedRun, ...]
    aligned_positions: tuple[AlignedPosition, ...]
    assessment: ComparabilityAssessment
    manifest: ExperimentManifest | None


class ObservatoryError(ValueError):
    pass


def compare_run_files(
    pairs: Sequence[RunTraceFiles],
    *,
    manifest: ExperimentManifest | None = None,
) -> MechanicalComparison:
    if len(pairs) < 2:
        raise ObservatoryError("at least two run/trace pairs are required")

    runs: list[ObservedRun] = []
    for index, pair in enumerate(pairs, start=1):
        run = load_run_json(pair.run_path)
        trace = load_trace_json(pair.trace_path)
        manifest_run = _manifest_run_for_pair(manifest, pair, index)
        label = (
            manifest_run.label
            if manifest_run is not None and manifest_run.label is not None
            else f"run_{index}"
        )
        runs.append(_observe_run(label, pair, run, trace))

    _validate_run_labels(tuple(runs))
    aligned = _align_positions(tuple(runs))
    assessment = _assess_comparability(tuple(runs), aligned, manifest, pairs)
    return MechanicalComparison(
        runs=tuple(runs),
        aligned_positions=aligned,
        assessment=assessment,
        manifest=manifest,
    )


def load_experiment_manifest(path: str | Path) -> ExperimentManifest:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"manifest file not found: {path}") from exc
    data = load_json_object(raw, "experiment manifest")

    protocol = _optional_mapping(data.get("protocol"), "protocol")
    input_data = _optional_mapping(data.get("input"), "input")
    runs = data.get("runs", ())
    if not isinstance(runs, list):
        raise TypeError("experiment manifest runs must be a JSON array")

    return ExperimentManifest(
        experiment_id=_optional_string(data.get("experiment_id"), "experiment_id"),
        protocol_id=(
            None
            if protocol is None
            else _optional_string(protocol.get("id"), "protocol.id")
        ),
        protocol_version=(
            None
            if protocol is None
            else _optional_string(protocol.get("version"), "protocol.version")
        ),
        input_digest=(
            None
            if input_data is None
            else _optional_string(input_data.get("digest"), "input.digest")
        ),
        input_text=(
            None
            if input_data is None
            else _optional_string(input_data.get("text"), "input.text")
        ),
        controlled_dimensions=_string_tuple(
            data.get("controlled_dimensions", ()),
            "controlled_dimensions",
        ),
        changed_dimensions=_string_tuple(
            data.get("changed_dimensions", ()),
            "changed_dimensions",
        ),
        runs=tuple(_manifest_run(item) for item in runs),
        raw=data,
    )


def render_comparison_markdown(comparison: MechanicalComparison) -> str:
    lines = [
        "# Delibra Run Comparison",
        "",
        "## Status",
        "",
        "review_required: true",
        "",
        "This draft is mechanical DelObs output. It aligns persisted Delibra runs and leaves observation, interpretation, qualification, confidence, and knowledge promotion to human review.",
        "",
        "## Naming And Authority",
        "",
        "- Internal Delibra identifiers such as `run_0001` and `artifact_0007` are opaque, stable within their scope, and independent of provider, model, preset, input, or experiment parameters.",
        "- File names are navigation labels only. They may be descriptive, but they are not a source of truth because files can be renamed.",
        "- `run.json` and `trace.json` content is authoritative for run id, trace id, protocol, input digest, status, artifacts, trace events, step ids, role ids, outputs, artifact kinds, timestamps, and payload sizes.",
        "- The optional experiment manifest is authoritative only for external comparison dimensions such as experiment label, human variant labels, declared controlled or changed dimensions, and known execution-environment metadata.",
        "- Manifest values that duplicate persisted run or trace facts are checked and reported when inconsistent; they do not override persisted run or trace content.",
        "- Protocol positions use artifact kind, not step kind. Step kind (`prompt`, `fanout`, `criticize`, `synthesize`) is not persisted in `run.json` or `trace.json`, so DelObs does not reconstruct it in this tranche.",
        "- Input text is not copied into this draft by default. The table reports deterministic input identity by digest and size to avoid casual duplication of source content.",
        "",
        "## Compared Runs",
        "",
        "| Label | Run id | Run file | Trace file | Protocol | Status | Input | Artifacts | Trace events |",
        "|---|---|---|---|---|---|---|---:|---:|",
    ]

    for observed in comparison.runs:
        lines.append(
            "| "
            f"{_md(observed.label)} | "
            f"`{_md(observed.run_id)}` | "
            f"`{_md(str(observed.run_path))}` | "
            f"`{_md(str(observed.trace_path))}` | "
            f"`{_md(observed.protocol_id)}@{_md(observed.protocol_version)}` | "
            f"`{_md(observed.status)}` | "
            f"{_md(observed.input_display)} | "
            f"{len(observed.artifacts)} | "
            f"{observed.trace_event_count} |"
        )

    lines.extend(
        [
            "",
            "## Mechanical Comparability",
            "",
            f"Classification: `{comparison.assessment.classification}`",
            "",
            "### Controlled Dimensions",
            "",
        ]
    )
    lines.extend(_bullet_list(comparison.assessment.controlled_dimensions))
    lines.extend(["", "### Changed Dimensions", ""])
    lines.extend(_bullet_list(comparison.assessment.changed_dimensions))
    lines.extend(["", "### Reservations", ""])
    lines.extend(_bullet_list(comparison.assessment.reservations))
    lines.extend(["", "### Incompatibilities", ""])
    lines.extend(_bullet_list(comparison.assessment.incompatibilities))
    lines.extend(["", "### Manifest Inconsistencies", ""])
    lines.extend(_bullet_list(comparison.assessment.manifest_inconsistencies))

    if comparison.manifest is not None:
        lines.extend(_render_manifest_section(comparison))

    lines.extend(
        [
            "",
            "## Protocol Positions",
            "",
            "| Position | " + " | ".join(_md(run.label) for run in comparison.runs) + " |",
            "|---|" + "---|" * len(comparison.runs),
        ]
    )
    for aligned in comparison.aligned_positions:
        cells = []
        for _, artifact in aligned.artifacts_by_label:
            if artifact is None:
                cells.append("missing")
            else:
                cells.append(
                    f"`{_md(artifact.artifact_id)}` "
                    f"order={artifact.production_order} "
                    f"payload_chars={artifact.payload_chars}"
                )
        lines.append(f"| `{_md(aligned.position.key)}` | " + " | ".join(cells) + " |")

    lines.extend(["", "## Artifact Provenance", ""])
    for aligned in comparison.aligned_positions:
        lines.extend(["", f"### `{aligned.position.key}`", ""])
        for label, artifact in aligned.artifacts_by_label:
            if artifact is None:
                lines.append(f"- {label}: missing")
            else:
                run = _run_by_label(comparison.runs, label)
                lines.append(
                    f"- {label}: artifact `{artifact.artifact_id}` from run "
                    f"`{run.run_id}`, step `{artifact.position.step_id}`, role "
                    f"`{artifact.position.role_id}`, output "
                    f"`{artifact.position.output}`, artifact_kind "
                    f"`{artifact.position.artifact_kind}`, "
                    f"production_order `{artifact.production_order}`, "
                    f"payload_chars `{artifact.payload_chars}`, "
                    f"created_at `{artifact.created_at}`, trace_event "
                    f"`{artifact.trace_event_id or 'unavailable'}` at "
                    f"`{artifact.trace_timestamp or 'unavailable'}`."
                )

    lines.extend(
        [
            "",
            "## Source Artifact Content",
            "",
            "Source payloads are not copied into this draft. This avoids uncontrolled duplication and keeps persisted `run.json` files as the source for artifact content. The provenance section above provides stable pointers for reviewer lookup.",
            "",
            "## Human Observations",
            "",
            "review_required: true",
            "",
            "### Candidate Observation",
            "",
            "- Description:",
            "- First occurrence:",
            "- Propagation:",
            "- Correction or reinforcement:",
            "- Confidence:",
            "- Limitations:",
            "- Supporting artifacts:",
            "",
            "## Human Qualifications",
            "",
            "review_required: true",
            "",
            "### Candidate Qualification",
            "",
            "- Name:",
            "- Definition:",
            "- Scope:",
            "- Evidence:",
            "- Counter-evidence:",
            "- Confidence:",
            "- Reviewer:",
            "- Review date:",
        ]
    )
    return "\n".join(lines) + "\n"


def _observe_run(label: str, pair: RunTraceFiles, run: Run, trace: Trace) -> ObservedRun:
    issues = list(_validate_pair(run, trace))
    trace_artifacts = _artifact_trace_index(trace)
    positions: list[ObservedArtifact] = []
    base_counts: dict[tuple[str, str, str, str], int] = {}

    for fallback_index, artifact in enumerate(run.artifacts, start=1):
        base = (
            artifact.producer_step_id,
            artifact.producer_role_id,
            artifact.output,
            artifact.kind,
        )
        base_counts[base] = base_counts.get(base, 0) + 1
        ordinal = base_counts[base]
        trace_data = trace_artifacts.get(artifact.id)
        production_order = (
            trace_data[0] if trace_data is not None else fallback_index
        )
        positions.append(
            ObservedArtifact(
                artifact_id=artifact.id,
                position=ProtocolPosition(
                    step_id=artifact.producer_step_id,
                    role_id=artifact.producer_role_id,
                    output=artifact.output,
                    artifact_kind=artifact.kind,
                    ordinal=ordinal,
                ),
                production_order=production_order,
                payload_chars=_json_chars(artifact.to_json()["payload"]),
                artifact_json_chars=_json_chars(artifact.to_json()),
                created_at=artifact.created_at,
                trace_event_id=None if trace_data is None else trace_data[1],
                trace_timestamp=None if trace_data is None else trace_data[2],
            )
        )
        if trace_data is None:
            issues.append(f"artifact {artifact.id} has no ArtifactCreated trace event")

    duplicated = [base for base, count in base_counts.items() if count > 1]
    for step_id, role_id, output, kind in duplicated:
        issues.append(
            "multiple artifacts share base protocol position "
            f"{step_id}/{role_id}/{output}/{kind}; ordinal alignment is used"
        )

    protocol_id = str(run.protocol["id"])
    protocol_version = str(run.protocol["version"])
    return ObservedRun(
        label=label,
        run_path=pair.run_path,
        trace_path=pair.trace_path,
        run_id=run.id,
        trace_id=trace.id,
        status=run.status.value,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        input_digest=_input_digest(run.input),
        input_display=_input_display(run.input),
        started_at=run.started_at,
        completed_at=run.completed_at,
        trace_event_count=len(trace.events),
        artifacts=tuple(sorted(positions, key=lambda item: item.production_order)),
        issues=tuple(issues),
    )


def _validate_run_labels(runs: tuple[ObservedRun, ...]) -> None:
    seen: set[str] = set()
    for observed in runs:
        if observed.label.strip() == "":
            raise ObservatoryError("run labels must be non-empty")
        if observed.label in seen:
            raise ObservatoryError(f"duplicate run label: {observed.label}")
        seen.add(observed.label)


def _validate_pair(run: Run, trace: Trace) -> tuple[str, ...]:
    issues: list[str] = []
    if trace.run_id != run.id:
        issues.append(
            f"trace run_id {trace.run_id} does not match run id {run.id}"
        )
    if run.trace_id != trace.id:
        issues.append(
            f"run trace_id {run.trace_id} does not match trace id {trace.id}"
        )
    artifacts_by_id = {artifact.id: artifact for artifact in run.artifacts}
    for event in trace.events:
        if event.type != TraceEventType.ARTIFACT_CREATED:
            continue
        artifact_id = event.payload.get("artifact_id")
        if not isinstance(artifact_id, str):
            issues.append(f"ArtifactCreated event {event.id} lacks artifact_id")
            continue
        artifact = artifacts_by_id.get(artifact_id)
        if artifact is None:
            issues.append(
                f"ArtifactCreated event {event.id} references unknown artifact {artifact_id}"
            )
            continue
        _check_event_payload(issues, event.id, artifact, event.payload)
    return tuple(issues)


def _check_event_payload(
    issues: list[str],
    event_id: str,
    artifact: Artifact,
    payload: Mapping[str, Any],
) -> None:
    checks = {
        "output": artifact.output,
        "kind": artifact.kind,
        "producer_role_id": artifact.producer_role_id,
    }
    for field, expected in checks.items():
        actual = payload.get(field)
        if actual != expected:
            issues.append(
                f"ArtifactCreated event {event_id} {field}={actual!r} "
                f"does not match artifact {artifact.id} {field}={expected!r}"
            )


def _artifact_trace_index(trace: Trace) -> dict[str, tuple[int, str, str]]:
    index: dict[str, tuple[int, str, str]] = {}
    order = 0
    for event in trace.events:
        if event.type != TraceEventType.ARTIFACT_CREATED:
            continue
        artifact_id = event.payload.get("artifact_id")
        if not isinstance(artifact_id, str):
            continue
        order += 1
        index.setdefault(artifact_id, (order, event.id, event.timestamp))
    return index


def _align_positions(runs: tuple[ObservedRun, ...]) -> tuple[AlignedPosition, ...]:
    first_seen: dict[ProtocolPosition, tuple[int, int]] = {}
    for run_index, observed in enumerate(runs):
        for artifact in observed.artifacts:
            first_seen.setdefault(
                artifact.position,
                (run_index, artifact.production_order),
            )

    positions = sorted(
        first_seen,
        key=lambda position: (
            first_seen[position],
            position.step_id,
            position.role_id,
            position.output,
            position.artifact_kind,
            position.ordinal,
        ),
    )
    aligned: list[AlignedPosition] = []
    for position in positions:
        cells = []
        for observed in runs:
            artifact = next(
                (
                    item
                    for item in observed.artifacts
                    if item.position == position
                ),
                None,
            )
            cells.append((observed.label, artifact))
        aligned.append(AlignedPosition(position=position, artifacts_by_label=tuple(cells)))
    return tuple(aligned)


def _assess_comparability(
    runs: tuple[ObservedRun, ...],
    aligned: tuple[AlignedPosition, ...],
    manifest: ExperimentManifest | None,
    pairs: Sequence[RunTraceFiles],
) -> ComparabilityAssessment:
    incompatibilities: list[str] = []
    reservations: list[str] = []

    for observed in runs:
        if observed.issues:
            for issue in observed.issues:
                qualified = f"{observed.label}: {issue}"
                if issue.startswith("multiple artifacts share base protocol position"):
                    reservations.append(qualified)
                else:
                    incompatibilities.append(qualified)
        if observed.status != "completed":
            reservations.append(
                f"{observed.label}: run status is {observed.status}, not completed"
            )
        if observed.input_display == "empty object; digest=" + observed.input_digest:
            reservations.append(f"{observed.label}: input is empty JSON object")

    protocol_ids = {run.protocol_id for run in runs}
    versions = {run.protocol_version for run in runs}
    input_digests = {run.input_digest for run in runs}
    if len(protocol_ids) > 1:
        incompatibilities.append(
            "protocol ids differ: " + ", ".join(sorted(protocol_ids))
        )
    if len(versions) > 1:
        incompatibilities.append(
            "protocol versions differ: " + ", ".join(sorted(versions))
        )
    if len(input_digests) > 1:
        incompatibilities.append(
            "inputs differ by deterministic digest: "
            + ", ".join(sorted(input_digests))
        )

    for aligned_position in aligned:
        missing = [
            label
            for label, artifact in aligned_position.artifacts_by_label
            if artifact is None
        ]
        if missing:
            reservations.append(
                f"position {aligned_position.position.key} missing in "
                + ", ".join(missing)
            )

    structures = {
        tuple(artifact.position for artifact in observed.artifacts)
        for observed in runs
    }
    if len(structures) > 1:
        reservations.append("protocol position structure differs across runs")

    manifest_inconsistencies = (
        ()
        if manifest is None
        else _manifest_inconsistencies(manifest, runs, pairs)
    )

    if incompatibilities:
        classification = "not_comparable"
    elif reservations or manifest_inconsistencies:
        classification = "comparable_with_reservations"
    else:
        classification = "comparable"

    return ComparabilityAssessment(
        classification=classification,
        controlled_dimensions=_controlled_dimensions(manifest),
        changed_dimensions=_changed_dimensions(manifest, runs),
        reservations=tuple(dict.fromkeys(reservations)),
        incompatibilities=tuple(dict.fromkeys(incompatibilities)),
        manifest_inconsistencies=tuple(dict.fromkeys(manifest_inconsistencies)),
    )


def _manifest_inconsistencies(
    manifest: ExperimentManifest,
    runs: tuple[ObservedRun, ...],
    pairs: Sequence[RunTraceFiles],
) -> tuple[str, ...]:
    issues: list[str] = []
    protocol_ids = {run.protocol_id for run in runs}
    versions = {run.protocol_version for run in runs}
    digests = {run.input_digest for run in runs}
    if manifest.protocol_id is not None and manifest.protocol_id not in protocol_ids:
        issues.append(
            f"manifest protocol.id {manifest.protocol_id} is not present in loaded runs"
        )
    if manifest.protocol_version is not None and manifest.protocol_version not in versions:
        issues.append(
            "manifest protocol.version "
            f"{manifest.protocol_version} is not present in loaded runs"
        )
    if manifest.input_digest is not None and manifest.input_digest not in digests:
        issues.append(
            f"manifest input.digest {manifest.input_digest} is not present in loaded runs"
        )
    if manifest.input_text is not None:
        expected_digest = _input_digest({"kind": "text", "content": manifest.input_text})
        if expected_digest not in digests:
            issues.append("manifest input.text digest does not match loaded run input")

    for index, pair in enumerate(pairs, start=1):
        manifest_run = _manifest_run_for_pair(manifest, pair, index)
        if manifest_run is None:
            issues.append(
                f"manifest has no run entry for pair {index}: {pair.run_path}"
            )
            continue
        if manifest_run.run_file is not None and not _path_matches(
            manifest_run.run_file,
            pair.run_path,
        ):
            issues.append(
                f"manifest run_file {manifest_run.run_file} does not match loaded path {pair.run_path}"
            )
        if manifest_run.trace_file is not None and not _path_matches(
            manifest_run.trace_file,
            pair.trace_path,
        ):
            issues.append(
                f"manifest trace_file {manifest_run.trace_file} does not match loaded path {pair.trace_path}"
            )
    return tuple(issues)


def _controlled_dimensions(manifest: ExperimentManifest | None) -> tuple[str, ...]:
    if manifest is not None and manifest.controlled_dimensions:
        return manifest.controlled_dimensions
    return ("protocol", "protocol_version", "input")


def _changed_dimensions(
    manifest: ExperimentManifest | None,
    runs: tuple[ObservedRun, ...],
) -> tuple[str, ...]:
    if manifest is not None and manifest.changed_dimensions:
        return manifest.changed_dimensions
    if len({run.protocol_id for run in runs}) > 1:
        return ("protocol",)
    if len({run.protocol_version for run in runs}) > 1:
        return ("protocol_version",)
    if len({run.input_digest for run in runs}) > 1:
        return ("input",)
    return ("not_declared",)


def _manifest_run_for_pair(
    manifest: ExperimentManifest | None,
    pair: RunTraceFiles,
    index: int,
) -> ManifestRunMetadata | None:
    if manifest is None:
        return None
    for item in manifest.runs:
        if item.run_file is not None and _path_matches(item.run_file, pair.run_path):
            return item
        if item.trace_file is not None and _path_matches(item.trace_file, pair.trace_path):
            return item
    if index <= len(manifest.runs):
        return manifest.runs[index - 1]
    return None


def _manifest_run(data: Any) -> ManifestRunMetadata:
    if not isinstance(data, Mapping):
        raise TypeError("experiment manifest run entries must be JSON objects")
    environment = _optional_mapping(
        data.get("execution_environment"),
        "runs.execution_environment",
    )
    parameters = _optional_mapping(data.get("parameters"), "runs.parameters")
    return ManifestRunMetadata(
        label=_optional_string(data.get("label"), "runs.label"),
        run_file=_optional_string(data.get("run_file"), "runs.run_file"),
        trace_file=_optional_string(data.get("trace_file"), "runs.trace_file"),
        execution_environment=environment,
        parameters=parameters,
    )


def _render_manifest_section(comparison: MechanicalComparison) -> list[str]:
    manifest = comparison.manifest
    if manifest is None:
        return []
    lines = ["", "## Experiment Manifest", ""]
    if manifest.experiment_id is not None:
        lines.append(f"- experiment_id: `{_md(manifest.experiment_id)}`")
    if manifest.protocol_id is not None or manifest.protocol_version is not None:
        lines.append(
            f"- declared_protocol: `{_md(manifest.protocol_id or 'unspecified')}@{_md(manifest.protocol_version or 'unspecified')}`"
        )
    if manifest.input_digest is not None:
        lines.append(f"- declared_input_digest: `{_md(manifest.input_digest)}`")
    if manifest.input_text is not None:
        lines.append(
            "- declared_input_text_digest: "
            f"`{_input_digest({'kind': 'text', 'content': manifest.input_text})}`"
        )
    if not lines or lines[-1] == "":
        lines.append("- no experiment-level manifest fields declared")
    lines.extend(["", "| Label | Run file | Trace file | Execution environment | Parameters |", "|---|---|---|---|---|"])
    for item in manifest.runs:
        lines.append(
            "| "
            f"{_md(item.label or 'unlabeled')} | "
            f"`{_md(item.run_file or 'unspecified')}` | "
            f"`{_md(item.trace_file or 'unspecified')}` | "
            f"{_md(_json_inline(item.execution_environment or {}))} | "
            f"{_md(_json_inline(item.parameters or {}))} |"
        )
    return lines


def _input_digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _input_display(value: Mapping[str, Any]) -> str:
    digest = _input_digest(value)
    if value.get("kind") == "text" and isinstance(value.get("content"), str):
        text = value["content"]
        return f"text chars={len(text)}; digest={digest}"
    if len(value) == 0:
        return f"empty object; digest={digest}"
    return f"json chars={_json_chars(value)}; digest={digest}"


def _json_chars(value: Any) -> int:
    return len(_canonical_json(value))


def _canonical_json(value: Any) -> str:
    return json.dumps(_plain_json(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    return value


def _optional_mapping(value: Any, name: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise TypeError(f"{name} must be a JSON array")
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"{name} entries must be strings")
    return tuple(value)


def _path_matches(manifest_path: str, actual_path: Path) -> bool:
    return manifest_path == str(actual_path) or Path(manifest_path).name == actual_path.name


def _run_by_label(runs: tuple[ObservedRun, ...], label: str) -> ObservedRun:
    for run in runs:
        if run.label == label:
            return run
    raise AssertionError(f"unknown run label: {label}")


def _json_inline(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _bullet_list(items: tuple[str, ...]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
