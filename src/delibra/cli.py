from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="delibra",
        description="Artifact-first deliberation orchestration.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    validate = subparsers.add_parser(
        "validate",
        help="validate a protocol definition",
        description="Validate a protocol definition.",
    )
    validate.set_defaults(handler=_not_implemented("validate"))

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


def _not_implemented(command: str):
    def handler(_args: argparse.Namespace) -> int:
        print(f"delibra {command}: not implemented yet", file=sys.stderr)
        return 1

    return handler

