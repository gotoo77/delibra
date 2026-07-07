from __future__ import annotations

import unittest
from types import MappingProxyType

from dataclasses import replace

from delibra.core import Produces, RunStatus, StepDefinition, StepKind
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    ExecutionContext,
    FixedClock,
    IdSequence,
    InvalidRunStateError,
    MissingOutputError,
    append_artifact,
    create_artifact,
    create_run,
)


FIXTURE = "tests/fixtures/rfc_protocol.yaml"


def load_valid_protocol():
    protocol = load_protocol_yaml(FIXTURE)
    validate_protocol(protocol)
    return protocol


def make_clock() -> FixedClock:
    return FixedClock(
        (
            "2026-07-07T10:00:00Z",
            "2026-07-07T10:00:01Z",
            "2026-07-07T10:00:02Z",
            "2026-07-07T10:00:03Z",
            "2026-07-07T10:00:04Z",
        )
    )


def make_run():
    return create_run(
        load_valid_protocol(),
        {"kind": "text", "content": "input"},
        run_ids=IdSequence("run"),
        trace_ids=IdSequence("trace"),
        clock=make_clock(),
    )


def make_running_run():
    return replace(make_run(), status=RunStatus.RUNNING)


class ExecutionContextTests(unittest.TestCase):
    def test_from_run_accepts_running_run(self) -> None:
        context = ExecutionContext.from_run(make_running_run())

        self.assertEqual(context.run_id, "run_0001")

    def test_from_run_rejects_created_run(self) -> None:
        with self.assertRaises(InvalidRunStateError) as raised:
            ExecutionContext.from_run(make_run())

        self.assertEqual(raised.exception.status, RunStatus.CREATED)

    def test_from_run_rejects_validated_run(self) -> None:
        with self.assertRaises(InvalidRunStateError) as raised:
            ExecutionContext.from_run(replace(make_run(), status=RunStatus.VALIDATED))

        self.assertEqual(raised.exception.status, RunStatus.VALIDATED)

    def test_from_run_rejects_completed_run(self) -> None:
        with self.assertRaises(InvalidRunStateError) as raised:
            ExecutionContext.from_run(replace(make_run(), status=RunStatus.COMPLETED))

        self.assertEqual(raised.exception.status, RunStatus.COMPLETED)

    def test_from_run_rejects_failed_run(self) -> None:
        with self.assertRaises(InvalidRunStateError) as raised:
            ExecutionContext.from_run(replace(make_run(), status=RunStatus.FAILED))

        self.assertEqual(raised.exception.status, RunStatus.FAILED)

    def test_from_run_rejects_cancelled_run(self) -> None:
        with self.assertRaises(InvalidRunStateError) as raised:
            ExecutionContext.from_run(replace(make_run(), status=RunStatus.CANCELLED))

        self.assertEqual(raised.exception.status, RunStatus.CANCELLED)

    def test_empty_context_resolves_user_input(self) -> None:
        run = make_running_run()
        context = ExecutionContext.from_run(run)

        self.assertEqual(context.run_id, "run_0001")
        self.assertEqual(context.resolve_input("user_input"), run.input)
        self.assertEqual(context.output_index, {})

    def test_context_does_not_expose_canonical_serialization(self) -> None:
        context = ExecutionContext.from_run(make_running_run())

        self.assertFalse(hasattr(context, "to_json"))

    def test_index_one_artifact_under_framing(self) -> None:
        protocol = load_valid_protocol()
        run = make_running_run()
        artifact = create_artifact(
            protocol.steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )

        context = ExecutionContext.from_run(append_artifact(run, artifact))

        self.assertIsInstance(context.output_index, MappingProxyType)
        self.assertEqual(context.output_index["framing"], ("artifact_0001",))
        self.assertEqual(context.resolve_input("framing"), ("artifact_0001",))

    def test_resolve_multiple_artifacts_under_same_output(self) -> None:
        protocol = load_valid_protocol()
        review_step = protocol.steps[1]
        run = make_running_run()
        artifact_ids = IdSequence("artifact")
        clock = make_clock()

        first = create_artifact(
            review_step,
            producer_role_id="maintainer",
            payload={"content": "maintainer review"},
            metadata={},
            artifact_ids=artifact_ids,
            clock=clock,
        )
        second = create_artifact(
            review_step,
            producer_role_id="tester",
            payload={"content": "tester review"},
            metadata={},
            artifact_ids=artifact_ids,
            clock=clock,
        )
        run = append_artifact(append_artifact(run, first), second)

        context = ExecutionContext.from_run(run)

        self.assertEqual(
            context.output_index["reviews"],
            ("artifact_0001", "artifact_0002"),
        )
        self.assertEqual(
            context.resolve_input("reviews"),
            ("artifact_0001", "artifact_0002"),
        )

    def test_missing_output_fails_with_structured_error(self) -> None:
        context = ExecutionContext.from_run(make_running_run())

        with self.assertRaises(MissingOutputError) as raised:
            context.resolve_input("framing")

        self.assertEqual(raised.exception.output, "framing")
        self.assertEqual(str(raised.exception), "missing output: framing")

    def test_resolve_step_inputs_uses_produces_output_not_step_id(self) -> None:
        protocol = load_valid_protocol()
        run = make_running_run()
        framing_artifact = create_artifact(
            protocol.steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )
        context = ExecutionContext.from_run(append_artifact(run, framing_artifact))
        step = StepDefinition(
            id="not_the_output_name",
            kind=StepKind.FANOUT,
            role=None,
            roles=("maintainer",),
            instruction="Review.",
            inputs=("framing",),
            produces=Produces(output="reviews", kind="review"),
        )

        resolved = context.resolve_step_inputs(step)

        self.assertIsNone(resolved.user_input)
        self.assertEqual(resolved.artifact_ids, ("artifact_0001",))

    def test_resolve_step_inputs_can_include_user_input_and_artifacts(self) -> None:
        protocol = load_valid_protocol()
        run = make_running_run()
        artifact = create_artifact(
            protocol.steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )
        context = ExecutionContext.from_run(append_artifact(run, artifact))
        step = StepDefinition(
            id="synthesize_with_input",
            kind=StepKind.SYNTHESIZE,
            role="synthesizer",
            roles=None,
            instruction="Synthesize.",
            inputs=("user_input", "framing"),
            produces=Produces(output="final", kind="synthesis"),
        )

        resolved = context.resolve_step_inputs(step)

        self.assertEqual(resolved.user_input, run.input)
        self.assertEqual(resolved.artifact_ids, ("artifact_0001",))

    def test_context_can_be_extended_without_mutating_previous_context(self) -> None:
        protocol = load_valid_protocol()
        context = ExecutionContext.from_run(make_running_run())
        artifact = create_artifact(
            protocol.steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )

        updated = context.with_artifact(artifact)

        self.assertNotIn("framing", context.output_index)
        self.assertEqual(updated.output_index["framing"], ("artifact_0001",))


if __name__ == "__main__":
    unittest.main()
