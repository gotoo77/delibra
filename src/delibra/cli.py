from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Sequence

from delibra.core import Run, Trace
from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml
from delibra.protocol_validator import ProtocolValidationError, validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    IdSequence,
    MockLLMClient,
    MockLLMError,
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
        help="run a protocol with the mock LLM",
        description="Run a protocol with the mock LLM.",
    )
    run.add_argument("--protocol", required=True, help="path to a protocol YAML file")
    run.add_argument(
        "--provider",
        choices=("mock", "openai"),
        default="mock",
        help="LLM provider to use; defaults to mock",
    )
    run.add_argument("--input-text", required=True, help="text input for the run")
    run.add_argument("--run-output", required=True, help="path to write run JSON")
    run.add_argument("--trace-output", required=True, help="path to write trace JSON")
    run.set_defaults(handler=_run)

    inspect = subparsers.add_parser(
        "inspect",
        help="inspect canonical run and trace JSON",
        description="Inspect canonical run and trace JSON.",
    )
    inspect.add_argument("--run", required=True, help="path to canonical run JSON")
    inspect.add_argument("--trace", help="path to canonical trace JSON")
    inspect.set_defaults(handler=_inspect)

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
        )
    except EngineExecutionError as exc:
        _write_run_outputs(args, exc.result)
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1
    except (
        ProtocolValidationError,
        UnsupportedStepKindError,
        MockLLMError,
        OpenAIConfigError,
        OpenAIProviderError,
        ValueError,
    ) as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1

    _write_run_outputs(args, result)
    return 0


def _build_llm_client(provider: str):
    if provider == "mock":
        return MockLLMClient(IdSequence("msg_response"))
    if provider == "openai":
        return OpenAIClient.from_env(response_message_ids=IdSequence("msg_response"))
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


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler
