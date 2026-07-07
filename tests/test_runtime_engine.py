from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.core import RunStatus, TraceEventType
from delibra.protocol_loader import load_protocol_yaml
from delibra.runtime import (
    EngineExecutionError,
    IdSequence,
    MockLLMClient,
    UnsupportedStepKindError,
    default_engine_ids,
    deterministic_clock,
    execute_prompt_synthesize_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"
FULL_FIXTURE = ROOT / "tests" / "fixtures" / "rfc_protocol.yaml"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "delibra", *args],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def execute_fixture():
    protocol = load_protocol_yaml(FIXTURE)
    return execute_prompt_synthesize_protocol(
        protocol,
        {"kind": "text", "content": "Why protect oceans?"},
        llm=MockLLMClient(IdSequence("msg_response")),
        ids=default_engine_ids(),
        clock=deterministic_clock(),
    )


class RuntimeEngineTests(unittest.TestCase):
    def test_execute_prompt_then_synthesize_with_mock_provider(self) -> None:
        result = execute_fixture()

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.run.artifacts), 2)
        self.assertEqual(result.run.artifacts[0].producer_step_id, "frame")
        self.assertEqual(result.run.artifacts[0].output, "framing")
        self.assertEqual(result.run.artifacts[0].kind, "framing")
        self.assertEqual(result.run.artifacts[1].producer_step_id, "final")
        self.assertEqual(result.run.artifacts[1].output, "final_synthesis")
        self.assertEqual(result.run.artifacts[1].kind, "synthesis")

    def test_trace_event_order_for_each_step(self) -> None:
        result = execute_fixture()

        self.assertEqual(
            [(event.step_id, event.type.value) for event in result.trace.events],
            [
                ("frame", "StepStarted"),
                ("frame", "MessageSent"),
                ("frame", "MessageReceived"),
                ("frame", "ArtifactCreated"),
                ("frame", "StepCompleted"),
                ("final", "StepStarted"),
                ("final", "MessageSent"),
                ("final", "MessageReceived"),
                ("final", "ArtifactCreated"),
                ("final", "StepCompleted"),
            ],
        )

    def test_message_trace_events_reference_message_ids_only(self) -> None:
        result = execute_fixture()
        message_events = [
            event.to_json()
            for event in result.trace.events
            if event.type.value in ("MessageSent", "MessageReceived")
        ]

        self.assertEqual(
            [event["payload"] for event in message_events],
            [
                {"message_id": "msg_0001"},
                {"message_id": "msg_response_0001"},
                {"message_id": "msg_0002"},
                {"message_id": "msg_response_0002"},
            ],
        )

    def test_synthesize_resolves_prior_artifact_output(self) -> None:
        result = execute_fixture()
        final_artifact = result.run.artifacts[1]

        self.assertEqual(final_artifact.payload["content"], "mock response for step final role synthesizer")
        self.assertEqual(final_artifact.metadata, {})

    def test_mock_metadata_does_not_enter_durable_artifacts(self) -> None:
        result = execute_fixture()

        self.assertEqual([artifact.metadata for artifact in result.run.artifacts], [{}, {}])

    def test_run_and_artifact_json_do_not_embed_messages(self) -> None:
        result = execute_fixture()
        run_json = result.run.to_json()

        self.assertNotIn("message", run_json)
        self.assertNotIn("messages", run_json)
        for artifact in run_json["artifacts"]:
            self.assertNotIn("message", artifact)
            self.assertNotIn("messages", artifact)
            self.assertNotIn("message_id", artifact)

    def test_fanout_is_not_supported_in_lot8(self) -> None:
        protocol = load_protocol_yaml(FULL_FIXTURE)

        with self.assertRaises(UnsupportedStepKindError):
            execute_prompt_synthesize_protocol(
                protocol,
                {"kind": "text", "content": "input"},
                llm=MockLLMClient(IdSequence("msg_response")),
                ids=default_engine_ids(),
                clock=deterministic_clock(),
            )

    def test_failed_execution_preserves_partial_run_and_trace(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        with self.assertRaises(EngineExecutionError) as raised:
            execute_prompt_synthesize_protocol(
                protocol,
                {"kind": "text", "content": "input"},
                llm=MockLLMClient(
                    IdSequence("msg_response"),
                    fail_for=(("final", "synthesizer"),),
                ),
                ids=default_engine_ids(),
                clock=deterministic_clock(),
            )

        result = raised.exception.result
        self.assertEqual(result.run.status, RunStatus.FAILED)
        self.assertEqual(len(result.run.artifacts), 1)
        self.assertEqual(result.run.artifacts[0].producer_step_id, "frame")
        self.assertEqual(
            [event.type for event in result.trace.events[-3:]],
            [
                TraceEventType.MESSAGE_SENT,
                TraceEventType.STEP_FAILED,
                TraceEventType.RUN_FAILED,
            ],
        )
        self.assertEqual(result.trace.events[-2].payload, {"step_id": "final"})
        self.assertEqual(result.trace.events[-1].payload, {"step_id": "final"})

    def test_cli_run_writes_run_and_trace_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(FIXTURE),
                "--input-text",
                "Why protect oceans?",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            run_json = json.loads(run_output.read_text(encoding="utf-8"))
            trace_json = json.loads(trace_output.read_text(encoding="utf-8"))
            self.assertEqual(run_json["status"], "completed")
            self.assertEqual(len(run_json["artifacts"]), 2)
            self.assertEqual(trace_json["events"][0]["type"], "StepStarted")


if __name__ == "__main__":
    unittest.main()
