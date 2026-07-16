from __future__ import annotations

import socket
import unittest
from unittest import mock

from delibra.app.local_diagnostics import (
    LocalDiagnostics,
    LocalProviderProbe,
    LocalProviderStatus,
)
from delibra.app.local_runtime import (
    LocalRuntimeIntent,
    assess_local_runtime,
)


def ollama_status(
    *,
    reachable: bool = True,
    models: tuple[str, ...] = ("llama3.2",),
    error: str | None = None,
) -> LocalProviderStatus:
    return LocalProviderStatus(
        provider_id="ollama",
        label="Ollama",
        kind="ollama",
        base_url="http://localhost:11434",
        reachable=reachable,
        models=models,
        error=error,
        recovery_hint="Start Ollama." if not reachable else None,
    )


class AppLocalRuntimeTests(unittest.TestCase):
    def test_diagnose_intent_does_not_attempt_inference(self) -> None:
        diagnostics = LocalDiagnostics(statuses=(ollama_status(),))

        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="diagnose"),
            diagnostics=diagnostics,
            ollama_transport=lambda _config, _payload: (_ for _ in ()).throw(
                AssertionError("inference should not be attempted")
            ),
        )

        self.assertEqual(assessment.diagnostics, diagnostics)
        self.assertEqual(assessment.inference_checks, ())

    def test_check_inference_without_model_does_not_select_automatically(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(),)),
            env={},
            ollama_transport=lambda _config, _payload: (_ for _ in ()).throw(
                AssertionError("inference should not be attempted")
            ),
        )

        check = assessment.inference_checks[0]
        self.assertFalse(check.attempted)
        self.assertEqual(check.status, "not_attempted")
        self.assertIsNone(check.model)

    def test_check_inference_uses_ollama_model_from_env(self) -> None:
        seen_payloads = []

        def transport(_config, payload):
            seen_payloads.append(payload)
            return {"response": "OK"}

        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(),)),
            env={"OLLAMA_MODEL": "llama3.2"},
            ollama_transport=transport,
            monotonic=_clock(1.0, 1.25),
        )

        check = assessment.inference_checks[0]
        self.assertTrue(check.attempted)
        self.assertEqual(check.status, "succeeded")
        self.assertEqual(check.model, "llama3.2")
        self.assertEqual(check.duration_seconds, 0.25)
        self.assertEqual(seen_payloads[0]["model"], "llama3.2")
        self.assertEqual(seen_payloads[0]["options"], {"num_predict": 256})

    def test_explicit_model_overrides_ollama_model_env(self) -> None:
        seen_payloads = []

        def transport(_config, payload):
            seen_payloads.append(payload)
            return {"response": "OK"}

        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="qwen2.5"),
            diagnostics=LocalDiagnostics(
                statuses=(ollama_status(models=("llama3.2", "qwen2.5")),)
            ),
            env={"OLLAMA_MODEL": "llama3.2"},
            ollama_transport=transport,
        )

        check = assessment.inference_checks[0]
        self.assertEqual(check.status, "succeeded")
        self.assertEqual(check.model, "qwen2.5")
        self.assertEqual(seen_payloads[0]["model"], "qwen2.5")

    def test_check_inference_uses_ollama_base_url_for_probe(self) -> None:
        seen_probe_urls: list[tuple[str, ...]] = []

        def diagnose(*, probes):
            seen_probe_urls.extend(probe.base_urls for probe in probes)
            return LocalDiagnostics(statuses=())

        with mock.patch("delibra.app.local_runtime.diagnose_local_providers", diagnose):
            assess_local_runtime(
                LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
                probes=(
                    LocalProviderProbe(
                        provider_id="ollama",
                        label="Ollama",
                        kind="ollama",
                        base_urls=("http://localhost:11434",),
                    ),
                ),
                env={"OLLAMA_BASE_URL": "http://ollama.test:11434"},
            )

        self.assertEqual(seen_probe_urls, [("http://ollama.test:11434",)])

    def test_server_unreachable_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
            diagnostics=LocalDiagnostics(
                statuses=(ollama_status(reachable=False, models=(), error="refused"),)
            ),
            ollama_transport=lambda _config, _payload: (_ for _ in ()).throw(
                AssertionError("inference should not be attempted")
            ),
        )

        check = assessment.inference_checks[0]
        self.assertFalse(check.attempted)
        self.assertEqual(check.status, "server_unreachable")
        self.assertEqual(check.error, "refused")

    def test_no_models_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(models=()),)),
        )

        check = assessment.inference_checks[0]
        self.assertFalse(check.attempted)
        self.assertEqual(check.status, "no_models")

    def test_model_missing_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="missing"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(models=("llama3.2",)),)),
        )

        check = assessment.inference_checks[0]
        self.assertFalse(check.attempted)
        self.assertEqual(check.status, "model_missing")
        self.assertIn("missing", check.error or "")

    def test_timeout_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(),)),
            ollama_transport=lambda _config, _payload: (_ for _ in ()).throw(
                socket.timeout("timed out")
            ),
            monotonic=_clock(2.0, 12.0),
        )

        check = assessment.inference_checks[0]
        self.assertTrue(check.attempted)
        self.assertEqual(check.status, "timeout")
        self.assertEqual(check.duration_seconds, 10.0)

    def test_invalid_or_empty_response_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(),)),
            ollama_transport=lambda _config, _payload: {"response": ""},
        )

        check = assessment.inference_checks[0]
        self.assertTrue(check.attempted)
        self.assertEqual(check.status, "invalid_response")

    def test_reasoning_model_can_exhaust_tiny_output_limit_before_response(self) -> None:
        def qwen3_like_transport(_config, payload):
            num_predict = payload.get("options", {}).get("num_predict")
            if isinstance(num_predict, int) and num_predict <= 192:
                return {
                    "response": "",
                    "thinking": "Okay, the user wants me to reply",
                    "done": True,
                    "done_reason": "length",
                    "eval_count": num_predict,
                }
            return {"response": "OK", "thinking": "reasoning", "done": True}

        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="qwen3:4b"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(models=("qwen3:4b",)),)),
            ollama_transport=qwen3_like_transport,
        )

        check = assessment.inference_checks[0]
        self.assertTrue(check.attempted)
        self.assertEqual(check.status, "succeeded")

    def test_provider_error_is_distinct(self) -> None:
        assessment = assess_local_runtime(
            LocalRuntimeIntent(operation="check_inference", model="llama3.2"),
            diagnostics=LocalDiagnostics(statuses=(ollama_status(),)),
            ollama_transport=lambda _config, _payload: {"error": "model crashed"},
        )

        check = assessment.inference_checks[0]
        self.assertTrue(check.attempted)
        self.assertEqual(check.status, "provider_error")
        self.assertIn("model crashed", check.error or "")


def _clock(*values: float):
    items = iter(values)

    def monotonic() -> float:
        return next(items)

    return monotonic


if __name__ == "__main__":
    unittest.main()
