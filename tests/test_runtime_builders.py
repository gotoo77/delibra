from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from delibra.core import Produces, RunStatus, StepDefinition, StepKind, TraceEventType
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    FixedClock,
    IdSequence,
    SystemClock,
    append_artifact,
    append_trace_event,
    create_artifact,
    create_run,
    create_trace,
    create_trace_event,
    transition_run,
)
from delibra.runtime.smoke import run_lot5_smoke


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rfc_protocol.yaml"


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
            "2026-07-07T10:00:05Z",
        )
    )


def run_python_module(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", *args],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class RuntimeBuilderTests(unittest.TestCase):
    def test_fixed_clock_raises_when_exhausted(self) -> None:
        clock = FixedClock(("2026-07-07T10:00:00Z",))

        self.assertEqual(clock.now(), "2026-07-07T10:00:00Z")
        with self.assertRaisesRegex(RuntimeError, "fixed clock exhausted"):
            clock.now()

    def test_system_clock_returns_utc_iso_timestamp(self) -> None:
        timestamp = SystemClock().now()

        self.assertTrue(timestamp.endswith("Z"))
        self.assertIn("T", timestamp)

    def test_create_run_in_created_status(self) -> None:
        run = create_run(
            load_valid_protocol(),
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )

        self.assertEqual(run.id, "run_0001")
        self.assertEqual(run.trace_id, "trace_0001")
        self.assertEqual(run.status, RunStatus.CREATED)
        self.assertEqual(run.started_at, "2026-07-07T10:00:00Z")
        self.assertEqual(run.artifacts, ())

    def test_run_lifecycle_transitions_are_enforced(self) -> None:
        run = create_run(
            load_valid_protocol(),
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        clock = make_clock()

        validated = transition_run(run, RunStatus.VALIDATED, clock=clock)
        running = transition_run(validated, RunStatus.RUNNING, clock=clock)
        completed = transition_run(running, RunStatus.COMPLETED, clock=clock)

        self.assertEqual(validated.status, RunStatus.VALIDATED)
        self.assertEqual(running.status, RunStatus.RUNNING)
        self.assertEqual(completed.status, RunStatus.COMPLETED)
        self.assertEqual(completed.completed_at, "2026-07-07T10:00:00Z")

    def test_terminal_run_cannot_return_to_running(self) -> None:
        run = create_run(
            load_valid_protocol(),
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        clock = make_clock()
        failed = transition_run(
            transition_run(run, RunStatus.VALIDATED, clock=clock),
            RunStatus.FAILED,
            clock=clock,
        )

        with self.assertRaisesRegex(ValueError, "invalid run transition"):
            transition_run(failed, RunStatus.RUNNING, clock=clock)

    def test_create_artifact_matching_step_produces(self) -> None:
        step = load_valid_protocol().steps[0]

        artifact = create_artifact(
            step,
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )

        self.assertEqual(artifact.id, "artifact_0001")
        self.assertEqual(artifact.kind, step.produces.kind)
        self.assertEqual(artifact.output, step.produces.output)
        self.assertEqual(artifact.producer_step_id, step.id)
        self.assertEqual(artifact.producer_role_id, "framer")

    def test_create_artifact_rejects_wrong_kind_or_output(self) -> None:
        step = load_valid_protocol().steps[0]

        with self.assertRaisesRegex(ValueError, "does not match step output"):
            create_artifact(
                step,
                producer_role_id="framer",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
                output="reviews",
            )
        with self.assertRaisesRegex(ValueError, "does not match step kind"):
            create_artifact(
                step,
                producer_role_id="framer",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
                kind="review",
            )

    def test_prompt_artifact_with_wrong_role_fails(self) -> None:
        step = load_valid_protocol().steps[0]

        with self.assertRaisesRegex(ValueError, "does not match step role"):
            create_artifact(
                step,
                producer_role_id="tester",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
            )

    def test_synthesize_artifact_with_wrong_role_fails(self) -> None:
        step = load_valid_protocol().steps[2]

        with self.assertRaisesRegex(ValueError, "does not match step role"):
            create_artifact(
                step,
                producer_role_id="tester",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
            )

    def test_fanout_artifact_with_role_outside_step_roles_fails(self) -> None:
        step = load_valid_protocol().steps[1]

        with self.assertRaisesRegex(ValueError, "not in step roles"):
            create_artifact(
                step,
                producer_role_id="synthesizer",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
            )

    def test_criticize_artifact_with_role_outside_step_roles_fails(self) -> None:
        step = StepDefinition(
            id="critiques",
            kind=StepKind.CRITICIZE,
            role=None,
            roles=("maintainer", "tester"),
            instruction="Criticize.",
            inputs=("reviews",),
            produces=Produces(output="critiques", kind="critique"),
        )

        with self.assertRaisesRegex(ValueError, "not in step roles"):
            create_artifact(
                step,
                producer_role_id="security",
                payload={},
                metadata={},
                artifact_ids=IdSequence("artifact"),
                clock=make_clock(),
            )

    def test_valid_fanout_and_criticize_roles_pass(self) -> None:
        fanout = load_valid_protocol().steps[1]
        criticize = StepDefinition(
            id="critiques",
            kind=StepKind.CRITICIZE,
            role=None,
            roles=("maintainer", "tester"),
            instruction="Criticize.",
            inputs=("reviews",),
            produces=Produces(output="critiques", kind="critique"),
        )

        fanout_artifact = create_artifact(
            fanout,
            producer_role_id="tester",
            payload={},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )
        criticize_artifact = create_artifact(
            criticize,
            producer_role_id="maintainer",
            payload={},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )

        self.assertEqual(fanout_artifact.producer_role_id, "tester")
        self.assertEqual(criticize_artifact.producer_role_id, "maintainer")

    def test_append_trace_events_preserves_order_and_is_immutable(self) -> None:
        run = create_run(
            load_valid_protocol(),
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        trace = create_trace(run)
        event_ids = IdSequence("evt")
        clock = make_clock()

        first = create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.RUN_CREATED,
            event_ids=event_ids,
            clock=clock,
            step_id=None,
            payload={"run_id": run.id},
        )
        second = create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.RUN_VALIDATED,
            event_ids=event_ids,
            clock=clock,
            step_id=None,
            payload={"run_id": run.id},
        )
        updated = append_trace_event(append_trace_event(trace, first), second)

        self.assertEqual(trace.events, ())
        self.assertEqual([event.id for event in updated.events], ["evt_0001", "evt_0002"])
        self.assertEqual(
            [event.type for event in updated.events],
            [TraceEventType.RUN_CREATED, TraceEventType.RUN_VALIDATED],
        )

    def test_failed_runs_retain_partial_artifacts(self) -> None:
        protocol = load_valid_protocol()
        run = create_run(
            protocol,
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        artifact = create_artifact(
            protocol.steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )
        run_with_artifact = append_artifact(run, artifact)
        failed = transition_run(run_with_artifact, RunStatus.FAILED, clock=make_clock())

        self.assertEqual(failed.status, RunStatus.FAILED)
        self.assertEqual([item.id for item in failed.artifacts], ["artifact_0001"])

    def test_artifact_payload_is_immutable_after_append(self) -> None:
        artifact = create_artifact(
            load_valid_protocol().steps[0],
            producer_role_id="framer",
            payload={"content": "framed"},
            metadata={},
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )

        with self.assertRaises(TypeError):
            artifact.payload["content"] = "changed"

    def test_deterministic_ids_and_clock_produce_same_json(self) -> None:
        first = run_lot5_smoke(str(FIXTURE))
        second = run_lot5_smoke(str(FIXTURE))

        self.assertEqual(first, second)

    def test_lot5_smoke_path_serializes_run_and_trace(self) -> None:
        result = run_lot5_smoke(str(FIXTURE))

        self.assertEqual(result["run"]["id"], "run_0001")
        self.assertEqual(result["trace"]["id"], "trace_0001")
        self.assertEqual(result["run"]["artifacts"][0]["id"], "artifact_0001")
        self.assertEqual(
            [event["type"] for event in result["trace"]["events"]],
            ["RunCreated", "ArtifactCreated"],
        )

    def test_lot5_smoke_module_runs(self) -> None:
        result = run_python_module("delibra.runtime.smoke", str(FIXTURE))

        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["run"]["id"], "run_0001")
        self.assertEqual(output["trace"]["events"][1]["type"], "ArtifactCreated")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
