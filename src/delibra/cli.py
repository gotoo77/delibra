from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml


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
        help="run a protocol",
        description="Run a protocol.",
    )
    run.set_defaults(handler=_not_implemented("run"))

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

    print(json.dumps(protocol.to_json(), indent=2))
    return 0


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler
