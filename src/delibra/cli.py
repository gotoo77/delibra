from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from delibra import __version__
from delibra.app.analysis import RunAnalysis, analyze_run
from delibra.app.inputs import input_from_file, input_from_json, input_from_text
from delibra.app.inspection import (
    ArtifactDetail,
    RunInspection,
    inspect_artifact,
    inspect_run,
)
from delibra.app.local_diagnostics import (
    LocalDiagnostics,
)
from delibra.app.local_runtime import (
    LocalInferenceCheck,
    LocalRuntimeAssessment,
    LocalRuntimeIntent,
    assess_local_runtime,
)
from delibra.app.observatory import (
    ObservatoryError,
    RunTraceFiles,
    compare_run_files,
    load_experiment_manifest,
    render_comparison_markdown,
)
from delibra.app.providers import build_llm_client
from delibra.app.presets import PresetError, PresetInfo, list_presets, load_preset
from delibra.app.storage import load_run_json, load_trace_json, write_run_outputs
from delibra.policy_loader import PolicyLoadError, load_policy_yaml
from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml
from delibra.protocol_validator import ProtocolValidationError, validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    EngineProgressEvent,
    MockLLMError,
    OllamaConfigError,
    OllamaProviderError,
    OpenAIConfigError,
    OpenAIProviderError,
    SystemClock,
    UnsupportedStepKindError,
    default_engine_ids,
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
        description=(
            "Run a protocol with the selected provider. In v0.1, multi-role "
            "fanout and criticize steps execute sequentially."
        ),
    )
    protocol_source = run.add_mutually_exclusive_group(required=True)
    protocol_source.add_argument("--protocol", help="path to a protocol YAML file")
    protocol_source.add_argument("--preset", help="name of a local preset")
    run.add_argument(
        "--provider",
        choices=("mock", "openai", "ollama"),
        default="mock",
        help="provider: mock, openai, ollama; default mock",
    )
    input_source = run.add_mutually_exclusive_group(required=True)
    input_source.add_argument("--input-text", help="text input for the run")
    input_source.add_argument("--input-file", help="path to a UTF-8 text input file")
    input_source.add_argument(
        "--input-json",
        help="inline JSON object input; arrays are allowed inside the object",
    )
    run.add_argument(
        "--policy",
        help="path to an execution policy YAML file",
    )
    run.add_argument("--run-output", required=True, help="path to write run JSON")
    run.add_argument("--trace-output", required=True, help="path to write trace JSON")
    run.add_argument(
        "--progress",
        action="store_true",
        help="print elapsed run progress and step durations to stderr",
    )
    run.set_defaults(handler=_run)

    inspect = subparsers.add_parser(
        "inspect",
        help="inspect canonical run and trace JSON",
        description="Inspect canonical run and trace JSON.",
    )
    inspect.add_argument("--run", required=True, help="path to canonical run JSON")
    inspect.add_argument("--trace", help="path to canonical trace JSON")
    inspect.add_argument("--artifact", help="artifact id to render with payload")
    inspect.set_defaults(handler=_inspect)

    analyze_run = subparsers.add_parser(
        "analyze-run",
        help="analyze canonical run and trace metrics",
        description="Analyze canonical run and trace metrics.",
    )
    analyze_run.add_argument("--run", required=True, help="path to canonical run JSON")
    analyze_run.add_argument("--trace", help="path to canonical trace JSON")
    analyze_run.set_defaults(handler=_analyze_run)

    compare_runs = subparsers.add_parser(
        "compare-runs",
        help="compare completed run/trace pairs mechanically",
        description=(
            "Compare two or more completed run.json/trace.json pairs and write "
            "a review-required Markdown draft. File names are labels only; "
            "persisted run and trace content remains authoritative."
        ),
    )
    compare_runs.add_argument(
        "--run",
        action="append",
        required=True,
        help="path to a canonical run JSON file; repeat once per run",
    )
    compare_runs.add_argument(
        "--trace",
        action="append",
        required=True,
        help="path to a canonical trace JSON file; repeat once per run",
    )
    compare_runs.add_argument(
        "--manifest",
        help="optional experimental manifest JSON for labels and external dimensions",
    )
    compare_runs.add_argument(
        "--output",
        required=True,
        help="path to write the review-required Markdown comparison draft",
    )
    compare_runs.set_defaults(handler=_compare_runs)

    doctor = subparsers.add_parser(
        "doctor",
        help="diagnose local Delibra environment",
        description="Diagnose local Delibra environment.",
    )
    doctor_subparsers = doctor.add_subparsers(dest="doctor_command", metavar="COMMAND")
    doctor_local = doctor_subparsers.add_parser(
        "local",
        help="diagnose local LLM providers",
        description="Diagnose local LLM providers without installing or writing files.",
    )
    doctor_local.add_argument(
        "--check-inference",
        action="store_true",
        help="run an explicit minimal local inference check; no install or download",
    )
    doctor_local.add_argument(
        "--provider",
        choices=("ollama",),
        help="local provider to check actively; default ollama when checking inference",
    )
    doctor_local.add_argument(
        "--model",
        help="explicit installed model to use for --check-inference",
    )
    doctor_local.set_defaults(handler=_doctor_local)

    presets = subparsers.add_parser(
        "presets",
        help="inspect available local presets",
        description="Inspect available local presets.",
    )
    presets_subparsers = presets.add_subparsers(dest="presets_command", metavar="COMMAND")
    presets_list = presets_subparsers.add_parser(
        "list",
        help="list available local presets",
        description="List available local presets from the local presets directory.",
    )
    presets_list.set_defaults(handler=_presets_list)

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
        protocol = _load_protocol_source(args)
        input_ref = _load_run_input(args)
    except (ProtocolLoadError, PresetError, OSError, TypeError, ValueError) as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1
    try:
        policy = None if args.policy is None else load_policy_yaml(args.policy)
    except PolicyLoadError as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1

    try:
        ids = default_engine_ids()
        result = execute_protocol(
            protocol,
            input_ref,
            llm=build_llm_client(args.provider),
            ids=ids,
            clock=SystemClock(),
            policy=policy,
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


def _load_protocol_source(args: argparse.Namespace):
    if args.protocol is not None:
        return load_protocol_yaml(args.protocol)
    return load_preset(args.preset)


def _load_run_input(args: argparse.Namespace):
    if args.input_text is not None:
        return input_from_text(args.input_text)
    if args.input_file is not None:
        return input_from_file(args.input_file)
    return input_from_json(args.input_json)


def _build_progress_printer(provider: str):
    renderer = ProgressRenderer(provider)

    def print_progress(event: EngineProgressEvent) -> None:
        print(renderer.render(event), file=sys.stderr)

    return print_progress


class ProgressRenderer:
    def __init__(
        self,
        provider: str,
        *,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # CLI progress measures local elapsed durations. It deliberately does not
        # reuse durable UTC clocks used for run and trace timestamps.
        self.provider = provider
        self.monotonic_clock = monotonic_clock
        self.run_started_at: float | None = None
        self.step_started_at_by_step_id: dict[str, float] = {}

    def render(self, event: EngineProgressEvent) -> str:
        now = self.monotonic_clock()
        if event.type == "run_started" and self.run_started_at is None:
            self.run_started_at = now
        elapsed = 0.0 if self.run_started_at is None else now - self.run_started_at
        message = _render_progress_event(event, self.provider)
        duration = self._duration_suffix(event, now)
        return f"[+{elapsed:.2f}s] {message}{duration}"

    def _duration_suffix(self, event: EngineProgressEvent, now: float) -> str:
        if event.type == "step_started" and event.step_id is not None:
            self.step_started_at_by_step_id[event.step_id] = now
            return ""
        if event.type == "step_completed" and event.step_id is not None:
            started_at = self.step_started_at_by_step_id.pop(event.step_id, None)
            if started_at is not None:
                return f" duration={now - started_at:.2f}s"
            return ""
        if event.type in {"run_completed", "run_failed"} and self.run_started_at is not None:
            return f" duration={now - self.run_started_at:.2f}s"
        return ""


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


def _write_run_outputs(args: argparse.Namespace, result) -> None:
    write_run_outputs(result, run_path=args.run_output, trace_path=args.trace_output)


def _inspect(args: argparse.Namespace) -> int:
    try:
        run = load_run_json(args.run)
        trace = None if args.trace is None else load_trace_json(args.trace)
        if trace is not None and trace.run_id != run.id:
            raise ValueError("trace run_id does not match run id")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"delibra inspect: {exc}", file=sys.stderr)
        return 1

    if args.artifact is not None:
        try:
            print(_render_artifact_detail(inspect_artifact(run, args.artifact)))
        except ValueError as exc:
            print(f"delibra inspect: {exc}", file=sys.stderr)
            return 1
        return 0

    print(_render_inspection(inspect_run(run, trace)))
    return 0


def _analyze_run(args: argparse.Namespace) -> int:
    try:
        run = load_run_json(args.run)
        trace = None if args.trace is None else load_trace_json(args.trace)
        if trace is not None and trace.run_id != run.id:
            raise ValueError("trace run_id does not match run id")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"delibra analyze-run: {exc}", file=sys.stderr)
        return 1

    print(_render_run_analysis(analyze_run(run, trace)))
    return 0


def _compare_runs(args: argparse.Namespace) -> int:
    if len(args.run) != len(args.trace):
        print(
            "delibra compare-runs: --run and --trace must be provided the same number of times",
            file=sys.stderr,
        )
        return 1
    if len(args.run) < 2:
        print("delibra compare-runs: at least two run/trace pairs are required", file=sys.stderr)
        return 1

    try:
        manifest = (
            None
            if args.manifest is None
            else load_experiment_manifest(args.manifest)
        )
        comparison = compare_run_files(
            tuple(
                RunTraceFiles(run_path=Path(run), trace_path=Path(trace))
                for run, trace in zip(args.run, args.trace, strict=True)
            ),
            manifest=manifest,
        )
        Path(args.output).write_text(
            render_comparison_markdown(comparison),
            encoding="utf-8",
        )
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        ObservatoryError,
    ) as exc:
        print(f"delibra compare-runs: {exc}", file=sys.stderr)
        return 1

    print(f"comparison: {args.output}")
    print(f"classification: {comparison.assessment.classification}")
    return 0


def _doctor_local(args: argparse.Namespace) -> int:
    if args.check_inference:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(
                operation="check_inference",
                provider_id="ollama" if args.provider is None else args.provider,
                model=args.model,
            )
        )
        print(_render_local_runtime_assessment(assessment))
        return 0

    assessment = assess_local_runtime(LocalRuntimeIntent())
    print(_render_local_diagnostics(assessment.diagnostics))
    return 0


def _presets_list(_args: argparse.Namespace) -> int:
    try:
        presets = list_presets()
    except (OSError, ProtocolLoadError, TypeError, ValueError) as exc:
        print(f"delibra presets list: {exc}", file=sys.stderr)
        return 1

    print(_render_presets_list(presets))
    return 0


def _render_inspection(inspection: RunInspection) -> str:
    lines = [
        f"run: {inspection.run_id}",
        f"status: {inspection.status}",
        f"protocol: {inspection.protocol_id}@{inspection.protocol_version}",
        f"artifacts: {inspection.artifact_count}",
        "artifact_summary:",
    ]
    for artifact in inspection.artifacts:
        lines.append(
            "  "
            f"- id={artifact.artifact_id} "
            f"output={artifact.output} "
            f"kind={artifact.kind} "
            f"producer_step_id={artifact.producer_step_id} "
            f"producer_role_id={artifact.producer_role_id}"
        )
    if inspection.trace_event_count is not None:
        lines.append(f"trace_events: {inspection.trace_event_count}")
    return "\n".join(lines)


def _render_artifact_detail(artifact: ArtifactDetail) -> str:
    lines = [
        f"artifact: {artifact.artifact_id}",
        f"output: {artifact.output}",
        f"kind: {artifact.kind}",
        f"producer_step_id: {artifact.producer_step_id}",
        f"producer_role_id: {artifact.producer_role_id}",
        "payload:",
        json.dumps(artifact.payload, indent=2, sort_keys=True),
        "metadata:",
        json.dumps(artifact.metadata, indent=2, sort_keys=True),
    ]
    return "\n".join(lines)


def _render_presets_list(presets: tuple[PresetInfo, ...]) -> str:
    lines = ["Available presets", "-----------------"]
    if not presets:
        lines.append("- none found")
        return "\n".join(lines)
    for preset in presets:
        lines.append(
            f"- {preset.name}: {preset.protocol_id}@{preset.version} "
            f"- {preset.description}"
        )
    return "\n".join(lines)


def _render_run_analysis(analysis: RunAnalysis) -> str:
    lines = [
        "Protocol metrics",
        "----------------",
        f"run: {analysis.run_id}",
        f"status: {analysis.status}",
        f"protocol: {analysis.protocol_id}@{analysis.protocol_version}",
        f"artifacts: {analysis.artifact_count}",
    ]
    if analysis.trace_event_count is not None:
        lines.append(f"trace_events: {analysis.trace_event_count}")
    if analysis.duration_seconds is not None:
        lines.append(f"duration_seconds: {analysis.duration_seconds:g}")

    lines.extend(
        [
            "",
            "Artifact sizes",
            "--------------",
            f"total_payload_chars: {analysis.total_payload_chars}",
            f"total_artifact_json_chars: {analysis.total_artifact_json_chars}",
            f"average_payload_chars: {analysis.average_payload_chars}",
        ]
    )
    if analysis.largest_artifact is not None:
        largest = analysis.largest_artifact
        lines.append(
            "largest_artifact: "
            f"{largest.artifact_id} "
            f"output={largest.output} "
            f"step={largest.step_id} "
            f"role={largest.role_id} "
            f"payload_chars={largest.payload_chars}"
        )

    lines.extend(["", "Step production", "---------------"])
    for step in analysis.step_productions:
        lines.append(
            f"- {step.step_id}: artifacts={step.artifact_count} "
            f"roles={step.role_count} "
            f"kinds={','.join(step.kind_labels)} "
            f"role_ids={','.join(step.role_ids)}"
        )

    lines.extend(["", "Fanout-like steps", "-----------------"])
    if not analysis.fanout_like_steps:
        lines.append("- none observed")
    for step in analysis.fanout_like_steps:
        lines.append(f"- {step.step_id}: {step.role_count} roles")

    lines.extend(["", "Critique-like steps", "-------------------"])
    if not analysis.critique_like_steps:
        lines.append("- none observed")
    for step in analysis.critique_like_steps:
        lines.append(f"- {step.step_id}: {step.role_count} roles")

    lines.extend(
        [
            "",
            "Context pressure estimates",
            "--------------------------",
            f"input_chars: {analysis.input_chars}",
            "cumulative_artifact_context_chars_upper_bound: "
            f"{analysis.cumulative_artifact_context_chars_upper_bound}",
        ]
    )
    if analysis.largest_pre_call_context is not None:
        lines.append(
            "largest_pre_call_context_upper_bound: "
            f"before_artifact={analysis.largest_pre_call_context.before_artifact_id} "
            f"chars={analysis.largest_pre_call_context.chars}"
        )
    lines.append(
        "estimated_tokens_upper_bound: "
        f"{analysis.estimated_tokens_upper_bound}"
    )

    lines.extend(["", "Repeated information signals", "----------------------------"])
    if not analysis.repeated_outputs:
        lines.append("- no repeated artifact outputs")
    for repeated in analysis.repeated_outputs:
        lines.append(
            f"- output={repeated.output} artifacts={repeated.artifact_count}"
        )

    lines.extend(["", "Potential bottlenecks", "---------------------"])
    if not analysis.potential_bottlenecks:
        lines.append("- none obvious from persisted run data")
    else:
        lines.extend(f"- {item}" for item in analysis.potential_bottlenecks)

    lines.extend(["", "Limitations", "-----------"])
    lines.extend(f"- {item}" for item in analysis.limitations)
    return "\n".join(lines)


def _render_local_diagnostics(diagnostics: LocalDiagnostics) -> str:
    lines = [
        "Local provider diagnostics",
        "--------------------------",
    ]
    if not diagnostics.statuses:
        lines.append("- no local provider probes configured")
        return "\n".join(lines)

    found_any = False
    for status in diagnostics.statuses:
        marker = "ok" if status.reachable else "not reachable"
        lines.append(f"- {status.label} ({status.base_url}): {marker}")
        if status.models:
            found_any = True
            lines.append(f"  models: {', '.join(status.models)}")
        elif status.reachable:
            found_any = True
            lines.append("  models: none reported")
        if status.error is not None:
            lines.append(f"  error: {status.error}")
        if status.recovery_hint is not None:
            lines.append(f"  recovery: {status.recovery_hint}")

    lines.extend(["", "Next steps"])
    if found_any:
        lines.append(
            "- Choose a provider and model explicitly before running Delibra."
        )
        lines.append("- Delibra did not install anything or choose a model for you.")
    else:
        lines.append(
            "- Start a local provider such as Ollama or an OpenAI-compatible local "
            "server, then rerun `delibra doctor local`."
        )
        lines.append("- Delibra did not install anything or write any files.")
    return "\n".join(lines)


def _render_local_runtime_assessment(assessment: LocalRuntimeAssessment) -> str:
    lines = [_render_local_diagnostics(assessment.diagnostics)]
    if assessment.inference_checks:
        lines.extend(["", "Inference check", "---------------"])
        for check in assessment.inference_checks:
            lines.extend(_render_inference_check(check))
    return "\n".join(lines)


def _render_inference_check(check: LocalInferenceCheck) -> list[str]:
    if not check.attempted:
        return _render_skipped_inference_check(check)
    lines = [f"- {check.provider_id}: {_inference_status_label(check.status)}"]
    if check.model is not None:
        lines.append(f"  model: {check.model}")
    lines.append(f"  attempted: {'yes' if check.attempted else 'no'}")
    if check.duration_seconds is not None:
        lines.append(f"  duration_seconds: {check.duration_seconds:g}")
    if check.error is not None:
        lines.append(f"  cause: {check.error}")
    if check.recovery_hint is not None:
        lines.append(f"  recovery: {check.recovery_hint}")
    return lines


def _render_skipped_inference_check(check: LocalInferenceCheck) -> list[str]:
    lines = [
        "Skipped.",
        f"Reason: {_skipped_inference_reason(check)}",
        "No inference was attempted.",
    ]
    if check.model is not None:
        lines.insert(1, f"Model: {check.model}")
    if check.error is not None:
        lines.append(f"Cause: {check.error}")
    if check.recovery_hint is not None:
        lines.append(f"Next step: {check.recovery_hint}")
    return lines


def _skipped_inference_reason(check: LocalInferenceCheck) -> str:
    if check.status == "server_unreachable":
        return "Ollama server is not reachable."
    if check.status == "no_models":
        return "Ollama is reachable but reported no visible models."
    if check.status == "model_missing":
        return "The requested model is not visible to Ollama."
    if check.status == "not_attempted":
        return "No explicit model was provided."
    return _inference_status_label(check.status)


def _inference_status_label(status: str) -> str:
    return {
        "not_attempted": "not attempted",
        "server_unreachable": "server unreachable",
        "no_models": "no models visible",
        "model_missing": "model missing",
        "timeout": "timeout",
        "provider_error": "provider error",
        "invalid_response": "invalid or empty response",
        "succeeded": "succeeded",
    }.get(status, status)


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler
