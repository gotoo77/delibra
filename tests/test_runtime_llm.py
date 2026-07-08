from __future__ import annotations

import unittest

from delibra.core import TraceEventType
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    EngineExecutionError,
    FixedClock,
    IdSequence,
    MockLLMClient,
    MockLLMError,
    OpenAIClient,
    OpenAIConfigError,
    OpenAIProviderError,
    append_artifact,
    append_trace_event,
    create_artifact,
    create_llm_request,
    create_run,
    create_trace,
    create_trace_event,
    default_engine_ids,
    deterministic_clock,
    execute_protocol,
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

    def test_openai_from_env_requires_api_key_and_model(self) -> None:
        with self.assertRaisesRegex(OpenAIConfigError, "OPENAI_API_KEY"):
            OpenAIClient.from_env(response_message_ids=IdSequence("msg"), env={})

        with self.assertRaisesRegex(OpenAIConfigError, "OPENAI_MODEL"):
            OpenAIClient.from_env(
                response_message_ids=IdSequence("msg"),
                env={"OPENAI_API_KEY": "test-key"},
            )

    def test_openai_client_normalizes_text_response(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"user_input": {"content": "input"}, "artifact_ids": [], "artifacts": []},
        )
        calls = []

        def transport(config, payload):
            calls.append((config, payload))
            return {
                "id": "resp_provider_id",
                "model": "provider-model",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "output_text": "normalized content",
            }

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
            transport=transport,
        )

        response = client.generate(request)

        self.assertEqual(calls[0][0].model, "test-model")
        self.assertEqual(calls[0][1]["model"], "test-model")
        self.assertIn("Resolved inputs:", calls[0][1]["input"])
        self.assertEqual(response.message.id, "msg_response_0001")
        self.assertEqual(response.payload, {"content": "normalized content"})
        self.assertEqual(response.metadata, {})

    def test_openai_provider_error_becomes_runtime_failure_with_trace(self) -> None:
        protocol = load_valid_protocol()

        def transport(_config, _payload):
            raise OpenAIProviderError("provider exploded")

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
            transport=transport,
        )

        with self.assertRaises(EngineExecutionError) as raised:
            execute_protocol(
                protocol,
                {"kind": "text", "content": "input"},
                llm=client,
                ids=default_engine_ids(),
                clock=deterministic_clock(),
            )

        result = raised.exception.result
        self.assertEqual(str(raised.exception), "provider exploded")
        self.assertEqual(result.run.status.value, "failed")
        self.assertEqual(
            [event.type for event in result.trace.events],
            [
                TraceEventType.STEP_STARTED,
                TraceEventType.MESSAGE_SENT,
                TraceEventType.STEP_FAILED,
                TraceEventType.RUN_FAILED,
            ],
        )

    def test_openai_provider_metadata_does_not_enter_run_or_artifact_json(self) -> None:
        protocol = load_valid_protocol()

        def transport(_config, _payload):
            return {
                "id": "resp_provider_id",
                "model": "provider-model",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "output_text": "provider content",
            }

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
            transport=transport,
        )

        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "input"},
            llm=client,
            ids=default_engine_ids(),
            clock=deterministic_clock(),
        )
        run_json = result.run.to_json()
        trace_json = result.trace.to_json()

        self.assertNotIn("provider", run_json)
        self.assertNotIn("model", run_json)
        self.assertNotIn("usage", run_json)
        for artifact in run_json["artifacts"]:
            self.assertEqual(artifact["payload"], {"content": "provider content"})
            self.assertEqual(artifact["metadata"], {})
            self.assertNotIn("provider", artifact)
            self.assertNotIn("model", artifact)
            self.assertNotIn("usage", artifact)
        self.assertNotIn("provider", trace_json)
        self.assertNotIn("model", trace_json)
        self.assertNotIn("usage", trace_json)
        for event in trace_json["events"]:
            self.assertNotIn("provider", event)
            self.assertNotIn("model", event)
            self.assertNotIn("usage", event)
            self.assertNotIn("provider", event["payload"])
            self.assertNotIn("model", event["payload"])
            self.assertNotIn("usage", event["payload"])


if __name__ == "__main__":
    unittest.main()
