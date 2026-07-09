from __future__ import annotations

import contextlib
import io
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
    OllamaClient,
    OllamaConfigError,
    OllamaProviderError,
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

    def test_openai_from_env_accepts_timeout_configuration(self) -> None:
        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg"),
            env={
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_TIMEOUT_SECONDS": "180",
            },
            transport=lambda _config, _payload: {"output_text": "ok"},
        )

        self.assertEqual(client.config.timeout_seconds, 180.0)

    def test_openai_from_env_accepts_max_output_tokens_configuration(self) -> None:
        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg"),
            env={
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_MAX_OUTPUT_TOKENS": "1200",
            },
            transport=lambda _config, _payload: {"output_text": "ok"},
        )

        self.assertEqual(client.config.max_output_tokens, 1200)

    def test_openai_from_env_rejects_invalid_timeout_configuration(self) -> None:
        with self.assertRaisesRegex(OpenAIConfigError, "OPENAI_TIMEOUT_SECONDS"):
            OpenAIClient.from_env(
                response_message_ids=IdSequence("msg"),
                env={
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "test-model",
                    "OPENAI_TIMEOUT_SECONDS": "0",
                },
            )

    def test_openai_from_env_rejects_invalid_max_output_tokens_configuration(self) -> None:
        with self.assertRaisesRegex(OpenAIConfigError, "OPENAI_MAX_OUTPUT_TOKENS"):
            OpenAIClient.from_env(
                response_message_ids=IdSequence("msg"),
                env={
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MODEL": "test-model",
                    "OPENAI_MAX_OUTPUT_TOKENS": "0",
                },
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
        self.assertEqual(calls[0][1]["max_output_tokens"], 800)
        self.assertIn("Resolved inputs:", calls[0][1]["input"])
        self.assertEqual(response.message.id, "msg_response_0001")
        self.assertEqual(response.payload, {"content": "normalized content"})
        self.assertEqual(response.metadata, {})

    def test_openai_client_extracts_responses_api_message_output_text(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"user_input": {"content": "input"}, "artifact_ids": [], "artifacts": []},
        )

        def transport(_config, _payload):
            return {
                "status": "completed",
                "output": [
                    {"type": "reasoning", "content": [], "summary": []},
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "message content",
                            }
                        ],
                    },
                ],
            }

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
            transport=transport,
        )

        response = client.generate(request)

        self.assertEqual(response.payload, {"content": "message content"})

    def test_openai_no_text_response_error_includes_shape_diagnostics(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"user_input": {"content": "input"}, "artifact_ids": [], "artifacts": []},
        )

        def transport(_config, _payload):
            return {
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [
                    {"type": "reasoning", "content": [], "summary": []},
                ],
            }

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "DELIBRA_DEBUG_PROVIDER": "1",
            },
            transport=transport,
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(OpenAIProviderError) as raised:
                client.generate(request)

        message = str(raised.exception)
        self.assertIn("status=incomplete", message)
        self.assertIn("incomplete_reason=max_output_tokens", message)
        self.assertIn("output_types=reasoning", message)
        self.assertIn("no text output", stderr.getvalue())

    def test_openai_debug_provider_logs_runtime_diagnostics_only(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"user_input": {"content": "input"}, "artifact_ids": [], "artifacts": []},
        )

        client = OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "test-model",
                "OPENAI_TIMEOUT_SECONDS": "45",
                "OPENAI_MAX_OUTPUT_TOKENS": "123",
                "DELIBRA_DEBUG_PROVIDER": "1",
            },
            transport=lambda _config, _payload: {"output_text": "normalized content"},
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            client.generate(request)

        debug_output = stderr.getvalue()
        self.assertIn("delibra.openai:", debug_output)
        self.assertIn("model=test-model", debug_output)
        self.assertIn("timeout_seconds=45", debug_output)
        self.assertIn("max_output_tokens=123", debug_output)
        self.assertIn("input_chars=", debug_output)
        self.assertNotIn("test-key", debug_output)

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
                TraceEventType.RUN_CREATED,
                TraceEventType.POLICY_APPLIED,
                TraceEventType.STEP_STARTED,
                TraceEventType.POLICY_DECISION,
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

    def test_ollama_from_env_requires_model(self) -> None:
        with self.assertRaisesRegex(OllamaConfigError, "OLLAMA_MODEL"):
            OllamaClient.from_env(response_message_ids=IdSequence("msg"), env={})

    def test_ollama_from_env_accepts_base_url_timeout_and_output_limit(self) -> None:
        client = OllamaClient.from_env(
            response_message_ids=IdSequence("msg"),
            env={
                "OLLAMA_MODEL": "llama3.2",
                "OLLAMA_BASE_URL": "http://ollama.test:11434",
                "OLLAMA_TIMEOUT_SECONDS": "90",
                "OLLAMA_MAX_OUTPUT_TOKENS": "512",
            },
            transport=lambda _config, _payload: {"response": "ok"},
        )

        self.assertEqual(client.config.model, "llama3.2")
        self.assertEqual(client.config.base_url, "http://ollama.test:11434")
        self.assertEqual(client.config.timeout_seconds, 90.0)
        self.assertEqual(client.config.max_output_tokens, 512)

    def test_ollama_from_env_rejects_invalid_timeout_and_output_limit(self) -> None:
        with self.assertRaisesRegex(OllamaConfigError, "OLLAMA_TIMEOUT_SECONDS"):
            OllamaClient.from_env(
                response_message_ids=IdSequence("msg"),
                env={"OLLAMA_MODEL": "llama3.2", "OLLAMA_TIMEOUT_SECONDS": "0"},
            )
        with self.assertRaisesRegex(OllamaConfigError, "OLLAMA_MAX_OUTPUT_TOKENS"):
            OllamaClient.from_env(
                response_message_ids=IdSequence("msg"),
                env={"OLLAMA_MODEL": "llama3.2", "OLLAMA_MAX_OUTPUT_TOKENS": "0"},
            )

    def test_ollama_client_normalizes_generate_response(self) -> None:
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
            return {"model": "llama3.2", "response": "local content", "done": True}

        client = OllamaClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OLLAMA_MODEL": "llama3.2", "OLLAMA_MAX_OUTPUT_TOKENS": "256"},
            transport=transport,
        )

        response = client.generate(request)

        self.assertEqual(calls[0][0].model, "llama3.2")
        self.assertEqual(calls[0][1]["model"], "llama3.2")
        self.assertEqual(calls[0][1]["stream"], False)
        self.assertEqual(calls[0][1]["options"], {"num_predict": 256})
        self.assertIn("Resolved inputs:", calls[0][1]["prompt"])
        self.assertEqual(response.message.id, "msg_response_0001")
        self.assertEqual(response.payload, {"content": "local content"})
        self.assertEqual(response.metadata, {})

    def test_ollama_error_response_is_clear(self) -> None:
        protocol = load_valid_protocol()
        step = protocol.steps[0]
        role = protocol.roles["framer"]
        request = create_llm_request(
            step,
            role,
            message_ids=IdSequence("msg"),
            inputs={"user_input": {"content": "input"}, "artifact_ids": [], "artifacts": []},
        )
        client = OllamaClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OLLAMA_MODEL": "missing-model"},
            transport=lambda _config, _payload: {"error": "model not found"},
        )

        with self.assertRaisesRegex(OllamaProviderError, "model not found"):
            client.generate(request)

    def test_ollama_provider_metadata_does_not_enter_run_or_artifact_json(self) -> None:
        protocol = load_valid_protocol()
        client = OllamaClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={"OLLAMA_MODEL": "llama3.2"},
            transport=lambda _config, _payload: {
                "model": "llama3.2",
                "response": "local content",
                "done": True,
                "eval_count": 5,
            },
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
        for artifact in run_json["artifacts"]:
            self.assertEqual(artifact["payload"], {"content": "local content"})
            self.assertEqual(artifact["metadata"], {})
            self.assertNotIn("provider", artifact)
            self.assertNotIn("model", artifact)
        self.assertNotIn("provider", trace_json)
        self.assertNotIn("model", trace_json)


if __name__ == "__main__":
    unittest.main()
