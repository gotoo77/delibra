from __future__ import annotations

import unittest

from delibra.core import TraceEventType
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    FixedClock,
    IdSequence,
    MockLLMClient,
    MockLLMError,
    append_artifact,
    append_trace_event,
    create_artifact,
    create_llm_request,
    create_run,
    create_trace,
    create_trace_event,
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


class RuntimeLLMTests(unittest.TestCase):
    def test_mock_returns_deterministic_response_for_step_and_role(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"artifact_ids": []},
        )
        client = MockLLMClient(response_message_ids=IdSequence("msg", start=2))

        response = client.generate(request)

        self.assertEqual(request.message.id, "msg_0001")
        self.assertEqual(response.message.id, "msg_0002")
        self.assertEqual(
            response.payload,
            {"content": "mock response for step frame role framer"},
        )
        self.assertEqual(response.metadata, {})

    def test_mock_provider_error_can_be_simulated(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={},
        )
        client = MockLLMClient(
            response_message_ids=IdSequence("msg", start=2),
            fail_for=(("frame", "framer"),),
        )

        with self.assertRaises(MockLLMError) as raised:
            client.generate(request)

        self.assertEqual(raised.exception.step_id, "frame")
        self.assertEqual(raised.exception.role_id, "framer")

    def test_message_trace_events_reference_message_ids(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={},
        )
        response = MockLLMClient(
            response_message_ids=IdSequence("msg", start=2)
        ).generate(request)
        run = create_run(
            protocol,
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        trace = create_trace(run)
        event_ids = IdSequence("evt")
        clock = make_clock()

        sent = create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.MESSAGE_SENT,
            event_ids=event_ids,
            clock=clock,
            step_id=step.id,
            payload={"message_id": request.message.id},
        )
        received = create_trace_event(
            run_id=run.id,
            event_type=TraceEventType.MESSAGE_RECEIVED,
            event_ids=event_ids,
            clock=clock,
            step_id=step.id,
            payload={"message_id": response.message.id},
        )
        trace = append_trace_event(append_trace_event(trace, sent), received)

        self.assertEqual(
            [event.type for event in trace.events],
            [TraceEventType.MESSAGE_SENT, TraceEventType.MESSAGE_RECEIVED],
        )
        self.assertEqual(trace.events[0].payload["message_id"], "msg_0001")
        self.assertEqual(trace.events[1].payload["message_id"], "msg_0002")

    def test_message_is_not_in_core_run_or_artifact_json(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={},
        )
        response = MockLLMClient(
            response_message_ids=IdSequence("msg", start=2)
        ).generate(request)
        run = create_run(
            protocol,
            {"kind": "text", "content": "input"},
            run_ids=IdSequence("run"),
            trace_ids=IdSequence("trace"),
            clock=make_clock(),
        )
        artifact = create_artifact(
            step,
            producer_role_id=role.id,
            payload=response.payload,
            metadata=response.metadata,
            artifact_ids=IdSequence("artifact"),
            clock=make_clock(),
        )
        run = append_artifact(run, artifact)
        run_json = run.to_json()

        self.assertNotIn("message", run_json)
        self.assertNotIn("messages", run_json)
        self.assertNotIn("message_id", run_json)
        self.assertNotIn("message", run_json["artifacts"][0])
        self.assertNotIn("messages", run_json["artifacts"][0])
        self.assertNotIn("message_id", run_json["artifacts"][0])


if __name__ == "__main__":
    unittest.main()
