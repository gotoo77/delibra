from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.core import (
    Produces,
    Protocol,
    Role,
    RunStatus,
    StepDefinition,
    StepKind,
    TraceEventType,
)
from delibra.protocol_loader import load_protocol_yaml
from delibra.runtime import (
    Budget,
    EngineExecutionError,
    ExecutionMode,
    ExecutionPolicy,
    IdSequence,
    MockLLMClient,
    StepPolicy,
    default_engine_ids,
    deterministic_clock,
    execute_protocol,
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
    return execute_protocol(
        protocol,
        {"kind": "text", "content": "Why protect oceans?"},
        llm=MockLLMClient(IdSequence("msg_response")),
        ids=default_engine_ids(),
        clock=deterministic_clock(),
    )


def execute_full_fixture():
    protocol = load_protocol_yaml(FULL_FIXTURE)
    return execute_protocol(
        protocol,
        {"kind": "text", "content": "Why protect oceans?"},
        llm=MockLLMClient(IdSequence("msg_response")),
        ids=default_engine_ids(),
        clock=deterministic_clock(),
    )


def make_criticize_protocol() -> Protocol:
    roles = {
        "framer": Role("framer", "Framer", "Frame input."),
        "maintainer": Role("maintainer", "Maintainer", "Review maintenance."),
        "tester": Role("tester", "Tester", "Review tests."),
        "critic": Role("critic", "Critic", "Criticize reviews."),
        "synthesizer": Role("synthesizer", "Synthesizer", "Synthesize."),
    }
    return Protocol(
        id="criticize_review",
        version="0.1.0",
        description="Review then criticize protocol.",
        roles=roles,
        steps=(
            StepDefinition(
                id="frame",
                kind=StepKind.PROMPT,
                role="framer",
                roles=None,
                instruction="Frame the input.",
                inputs=("user_input",),
                produces=Produces(output="framing", kind="framing"),
            ),
            StepDefinition(
                id="reviews",
                kind=StepKind.FANOUT,
                role=None,
                roles=("maintainer", "tester"),
                instruction="Review the framing.",
                inputs=("framing",),
                produces=Produces(output="reviews", kind="review"),
            ),
            StepDefinition(
                id="critiques",
                kind=StepKind.CRITICIZE,
                role=None,
                roles=("critic", "tester"),
                instruction="Criticize the reviews.",
                inputs=("reviews",),
                produces=Produces(output="critiques", kind="critique"),
            ),
            StepDefinition(
                id="final",
                kind=StepKind.SYNTHESIZE,
                role="synthesizer",
                roles=None,
                instruction="Synthesize the critiques.",
                inputs=("framing", "reviews", "critiques"),
                produces=Produces(output="final_synthesis", kind="synthesis"),
            ),
        ),
    )


class RecordingLLMClient:
    def __init__(self) -> None:
        self._mock = MockLLMClient(IdSequence("msg_response"))
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return self._mock.generate(request)


class RuntimeEngineTests(unittest.TestCase):
    def test_execute_prompt_then_synthesize_with_mock_provider(self) -> None:
        result = execute_fixture()

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(result.run.language, {"requested": "auto", "resolved": "en"})
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
                (None, "RunCreated"),
                (None, "PolicyApplied"),
                ("frame", "StepStarted"),
                ("frame", "PolicyDecision"),
                ("frame", "MessageSent"),
                ("frame", "MessageReceived"),
                ("frame", "ArtifactCreated"),
                ("frame", "StepCompleted"),
                ("final", "StepStarted"),
                ("final", "PolicyDecision"),
                ("final", "MessageSent"),
                ("final", "MessageReceived"),
                ("final", "ArtifactCreated"),
                ("final", "StepCompleted"),
            ],
        )

    def test_run_created_is_first_trace_event(self) -> None:
        result = execute_fixture()

        first = result.trace.events[0]

        self.assertEqual(first.type, TraceEventType.RUN_CREATED)
        self.assertIsNone(first.step_id)
        self.assertEqual(first.payload, {})

    def test_step_started_records_declared_and_resolved_inputs(self) -> None:
        result = execute_fixture()
        started = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.STEP_STARTED
        ]

        self.assertEqual(
            [event.payload for event in started],
            [
                {
                    "step_id": "frame",
                    "inputs": ("user_input",),
                    "resolved_artifact_ids": (),
                },
                {
                    "step_id": "final",
                    "inputs": ("framing",),
                    "resolved_artifact_ids": ("artifact_0001",),
                },
            ],
        )

    def test_execute_protocol_accepts_policy_none_and_records_default_policy(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=None,
        )

        policy_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.POLICY_APPLIED
        ]
        self.assertEqual(len(policy_events), 1)
        self.assertEqual(
            policy_events[0].payload,
            {
                "policy_id": "default",
                "mode": "standard",
                "unit": "approx_token",
            },
        )

    def test_execute_protocol_accepts_explicit_policy_and_records_neutral_payload(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)
        policy = ExecutionPolicy(
            id="cheap-review",
            mode=ExecutionMode.CHEAP,
            run_budget=Budget(max_estimated_units=3000),
            routes={"cheap-default": {"provider": "openai", "model": "gpt-5-mini"}},
            steps={"frame": StepPolicy(route_id="cheap-default")},
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=policy,
        )

        policy_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.POLICY_APPLIED
        ]
        self.assertEqual(len(policy_events), 1)
        self.assertEqual(
            policy_events[0].payload,
            {
                "policy_id": "cheap-review",
                "mode": "cheap",
                "unit": "approx_token",
            },
        )
        self.assertTrue(
            {"provider", "model", "tokens", "cost"}.isdisjoint(
                set(policy_events[0].payload)
            )
        )

    def test_policy_decision_event_is_emitted_before_each_llm_call(self) -> None:
        result = execute_full_fixture()
        decision_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.POLICY_DECISION
        ]
        message_sent_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.MESSAGE_SENT
        ]

        self.assertEqual(len(decision_events), len(message_sent_events))
        self.assertEqual(len(decision_events), 5)
        for decision_event, message_event in zip(decision_events, message_sent_events):
            self.assertEqual(decision_event.step_id, message_event.step_id)
            self.assertLess(
                result.trace.events.index(decision_event),
                result.trace.events.index(message_event),
            )

    def test_policy_decision_payload_is_neutral(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)
        policy = ExecutionPolicy(
            id="cheap-review",
            mode=ExecutionMode.CHEAP,
            default_step_budget=Budget(max_output_units=300),
            routes={"cheap-default": {"provider": "openai", "model": "gpt-5-mini"}},
            steps={"frame": StepPolicy(route_id="cheap-default")},
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=policy,
        )

        decision = next(
            event
            for event in result.trace.events
            if event.type is TraceEventType.POLICY_DECISION
            and event.step_id == "frame"
        )
        self.assertEqual(
            set(decision.payload),
            {
                "step_id",
                "role_id",
                "action",
                "reason",
                "estimated_input_units",
                "reserved_output_units",
                "estimated_total_units",
                "run_budget_remaining",
                "step_budget_remaining",
                "route_id",
                "unit",
            },
        )
        self.assertEqual(decision.payload["action"], "allow_call")
        self.assertEqual(decision.payload["route_id"], "cheap-default")
        self.assertEqual(decision.payload["unit"], "approx_token")
        self.assertTrue(
            {"provider", "model", "tokens", "cost"}.isdisjoint(set(decision.payload))
        )

    def test_sufficient_budget_preserves_runtime_behavior(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)
        llm = RecordingLLMClient()
        policy = ExecutionPolicy(
            id="budgeted",
            run_budget=Budget(max_estimated_units=10_000),
            default_step_budget=Budget(max_estimated_units=5_000),
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=llm,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=policy,
        )

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.run.artifacts), 2)
        self.assertEqual(len(llm.requests), 2)
        self.assertFalse(
            any(event.type is TraceEventType.BUDGET_EXCEEDED for event in result.trace.events)
        )

    def test_run_budget_exceeded_cancels_before_llm_call(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)
        llm = RecordingLLMClient()
        policy = ExecutionPolicy(
            id="too-cheap",
            run_budget=Budget(max_estimated_units=1),
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=llm,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=policy,
        )

        self.assertEqual(result.run.status, RunStatus.CANCELLED)
        self.assertEqual(len(llm.requests), 0)
        self.assertEqual(len(result.run.artifacts), 0)
        decision_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.POLICY_DECISION
        ]
        budget_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.BUDGET_EXCEEDED
        ]
        self.assertEqual(len(decision_events), 1)
        self.assertEqual(len(budget_events), 1)
        self.assertEqual(decision_events[0].payload["action"], "cancel_run")
        self.assertEqual(decision_events[0].payload["reason"], "run budget exceeded")
        self.assertLess(
            result.trace.events.index(decision_events[0]),
            result.trace.events.index(budget_events[0]),
        )
        self.assertEqual(
            budget_events[0].payload,
            {
                "step_id": "frame",
                "role_id": "framer",
                "reason": "run budget exceeded",
                "estimated_total_units": decision_events[0].payload[
                    "estimated_total_units"
                ],
                "run_budget_remaining": 0,
                "step_budget_remaining": 0,
                "unit": "approx_token",
            },
        )
        self.assertTrue(
            {"provider", "model", "tokens", "cost"}.isdisjoint(
                set(budget_events[0].payload)
            )
        )

    def test_step_budget_exceeded_cancels_before_step_llm_call(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)
        llm = RecordingLLMClient()
        policy = ExecutionPolicy(
            id="final-too-cheap",
            steps={
                "final": StepPolicy(
                    budget=Budget(max_estimated_units=1),
                ),
            },
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Why protect oceans?"},
            llm=llm,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            policy=policy,
        )

        self.assertEqual(result.run.status, RunStatus.CANCELLED)
        self.assertEqual(len(llm.requests), 1)
        self.assertEqual([request.step_id for request in llm.requests], ["frame"])
        self.assertEqual(len(result.run.artifacts), 1)
        self.assertEqual(result.run.artifacts[0].producer_step_id, "frame")
        budget_events = [
            event
            for event in result.trace.events
            if event.type is TraceEventType.BUDGET_EXCEEDED
        ]
        self.assertEqual(len(budget_events), 1)
        self.assertEqual(budget_events[0].payload["step_id"], "final")
        self.assertEqual(budget_events[0].payload["role_id"], "synthesizer")
        self.assertEqual(budget_events[0].payload["reason"], "step budget exceeded")
        self.assertEqual(budget_events[0].payload["step_budget_remaining"], 0)

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

    def test_fanout_creates_multiple_artifacts_under_one_output(self) -> None:
        result = execute_full_fixture()

        reviews = [
            artifact
            for artifact in result.run.artifacts
            if artifact.output == "reviews"
        ]

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.run.artifacts), 5)
        self.assertEqual(len(reviews), 3)
        self.assertEqual(
            [artifact.producer_role_id for artifact in reviews],
            ["maintainer", "tester", "security"],
        )
        self.assertEqual({artifact.kind for artifact in reviews}, {"review"})

    def test_fanout_step_completed_references_all_produced_artifacts(self) -> None:
        result = execute_full_fixture()
        reviews_completed = [
            event
            for event in result.trace.events
            if event.step_id == "reviews"
            and event.type is TraceEventType.STEP_COMPLETED
        ]

        self.assertEqual(len(reviews_completed), 1)
        self.assertEqual(
            reviews_completed[0].payload,
            {"artifact_ids": ("artifact_0002", "artifact_0003", "artifact_0004")},
        )

    def test_fanout_uses_existing_durable_artifact_shape(self) -> None:
        result = execute_full_fixture()
        review_json = result.run.artifacts[1].to_json()

        self.assertEqual(
            set(review_json),
            {
                "id",
                "kind",
                "output",
                "producer_step_id",
                "producer_role_id",
                "payload",
                "metadata",
                "created_at",
            },
        )
        self.assertEqual(review_json["output"], "reviews")

    def test_criticize_consumes_prior_outputs_and_creates_critique_artifacts(self) -> None:
        protocol = make_criticize_protocol()
        llm = RecordingLLMClient()

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "input"},
            llm=llm,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
        )
        critiques = [
            artifact
            for artifact in result.run.artifacts
            if artifact.output == "critiques"
        ]
        criticize_requests = [
            request
            for request in llm.requests
            if request.step_id == "critiques"
        ]

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(len(critiques), 2)
        self.assertEqual([artifact.kind for artifact in critiques], ["critique", "critique"])
        self.assertEqual(
            [artifact.producer_role_id for artifact in critiques],
            ["critic", "tester"],
        )
        self.assertEqual(len(criticize_requests), 2)
        self.assertEqual(
            [request.inputs["artifact_ids"] for request in criticize_requests],
            [["artifact_0002", "artifact_0003"], ["artifact_0002", "artifact_0003"]],
        )

    def test_language_is_persisted_as_requested_and_resolved_values(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        french_result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Merci de relire cette decision importante."},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            language="auto",
        )
        english_result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Hello, can you review this design?"},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            language="auto",
        )

        self.assertEqual(french_result.run.to_json()["language"], {"requested": "auto", "resolved": "fr"})
        self.assertEqual(english_result.run.to_json()["language"], {"requested": "auto", "resolved": "en"})

    def test_language_instruction_is_injected_for_all_llm_step_kinds(self) -> None:
        protocol = make_criticize_protocol()
        original_protocol_json = protocol.to_json()
        llm = RecordingLLMClient()
        instruction = "Produce all generated artifact content in French."

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Merci de relire cette decision importante."},
            llm=llm,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            language="fr",
        )

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(
            [(request.step_id, request.role_id) for request in llm.requests],
            [
                ("frame", "framer"),
                ("reviews", "maintainer"),
                ("reviews", "tester"),
                ("critiques", "critic"),
                ("critiques", "tester"),
                ("final", "synthesizer"),
            ],
        )
        for request in llm.requests:
            role = protocol.roles[request.role_id]
            step = next(step for step in protocol.steps if step.id == request.step_id)
            self.assertEqual(request.message.content.count(instruction), 1)
            self.assertLess(
                request.message.content.index(instruction),
                request.message.content.index(role.instruction),
            )
            self.assertLess(
                request.message.content.index(instruction),
                request.message.content.index(step.instruction),
            )
        self.assertEqual(
            {request.message.content.splitlines()[2] for request in llm.requests},
            {instruction},
        )
        self.assertNotIn(instruction, json.dumps(result.trace.to_json()))
        self.assertEqual(protocol.to_json(), original_protocol_json)

    def test_language_instruction_does_not_modify_structural_artifact_fields(self) -> None:
        protocol = make_criticize_protocol()

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Review this decision."},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            language="fr",
        )

        self.assertEqual(
            [
                (artifact.output, artifact.kind, artifact.producer_step_id, artifact.producer_role_id)
                for artifact in result.run.artifacts
            ],
            [
                ("framing", "framing", "frame", "framer"),
                ("reviews", "review", "reviews", "maintainer"),
                ("reviews", "review", "reviews", "tester"),
                ("critiques", "critique", "critiques", "critic"),
                ("critiques", "critique", "critiques", "tester"),
                ("final_synthesis", "synthesis", "final", "synthesizer"),
            ],
        )

    def test_failed_execution_preserves_partial_run_and_trace(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        with self.assertRaises(EngineExecutionError) as raised:
            execute_protocol(
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

    def test_progress_callback_reports_run_steps_roles_and_artifact_counts(self) -> None:
        protocol = make_criticize_protocol()
        events = []

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "input"},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
            progress=events.append,
        )

        self.assertEqual(result.run.status, RunStatus.COMPLETED)
        self.assertEqual(events[0].type, "run_started")
        self.assertEqual(events[0].artifact_count, 0)
        self.assertEqual(events[-1].type, "run_completed")
        self.assertEqual(events[-1].artifact_count, 6)
        self.assertIn(
            ("role_started", "reviews", "maintainer"),
            [(event.type, event.step_id, event.role_id) for event in events],
        )
        self.assertIn(
            ("role_started", "critiques", "critic"),
            [(event.type, event.step_id, event.role_id) for event in events],
        )
        self.assertIn(
            ("step_completed", "reviews", 2),
            [(event.type, event.step_id, event.artifact_count) for event in events],
        )

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
            self.assertEqual(trace_json["events"][0]["type"], "RunCreated")
            self.assertEqual(
                trace_json["events"][1]["payload"],
                {
                    "policy_id": "default",
                    "mode": "standard",
                    "unit": "approx_token",
                },
            )
            self.assertEqual(trace_json["events"][2]["type"], "StepStarted")


if __name__ == "__main__":
    unittest.main()
