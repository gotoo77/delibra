from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Sequence

from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml
from delibra.protocol_validator import ProtocolValidationError, validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    IdSequence,
    MockLLMClient,
    MockLLMError,
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
    run.add_argument("--input-text", required=True, help="text input for the run")
    run.add_argument("--run-output", required=True, help="path to write run JSON")
    run.add_argument("--trace-output", required=True, help="path to write trace JSON")
    run.set_defaults(handler=_run)

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
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=ids,
            clock=deterministic_clock(),
        )
    except EngineExecutionError as exc:
        _write_run_outputs(args, exc.result)
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1
    except (ProtocolValidationError, UnsupportedStepKindError, MockLLMError, ValueError) as exc:
        print(f"delibra run: {exc}", file=sys.stderr)
        return 1

    _write_run_outputs(args, result)
    return 0


def _write_run_outputs(args: argparse.Namespace, result) -> None:
    Path(args.run_output).write_text(json.dumps(result.run.to_json(), indent=2), encoding="utf-8")
    Path(args.trace_output).write_text(
        json.dumps(result.trace.to_json(), indent=2),
        encoding="utf-8",
    )


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler
