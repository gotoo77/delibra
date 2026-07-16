from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from delibra.app.local_diagnostics import LocalDiagnostics, LocalProviderStatus
from delibra.app.local_runtime import LocalInferenceCheck, LocalRuntimeAssessment
from delibra.cli import main


class CliDoctorTests(unittest.TestCase):
    def test_doctor_local_renders_unreachable_status_without_traceback(self) -> None:
        diagnostics = LocalDiagnostics(
            statuses=(
                LocalProviderStatus(
                    provider_id="ollama",
                    label="Ollama",
                    kind="ollama",
                    base_url="http://localhost:11434",
                    reachable=False,
                    models=(),
                    error="connection refused",
                    recovery_hint="Start Ollama, then rerun `delibra doctor local`.",
                ),
            )
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch(
            "delibra.cli.assess_local_runtime",
            return_value=LocalRuntimeAssessment(diagnostics=diagnostics),
        ):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["doctor", "local"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Local provider diagnostics", stdout.getvalue())
        self.assertIn("Ollama (http://localhost:11434): not reachable", stdout.getvalue())
        self.assertIn("recovery: Start Ollama", stdout.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_doctor_local_renders_models_without_choosing_one(self) -> None:
        diagnostics = LocalDiagnostics(
            statuses=(
                LocalProviderStatus(
                    provider_id="openai-compatible",
                    label="OpenAI-compatible local endpoint",
                    kind="openai-compatible",
                    base_url="http://localhost:1234/v1",
                    reachable=True,
                    models=("local-a", "local-b"),
                    error=None,
                    recovery_hint=None,
                ),
            )
        )

        stdout = io.StringIO()
        with mock.patch(
            "delibra.cli.assess_local_runtime",
            return_value=LocalRuntimeAssessment(diagnostics=diagnostics),
        ):
            with contextlib.redirect_stdout(stdout):
                code = main(["doctor", "local"])

        self.assertEqual(code, 0)
        self.assertIn("models: local-a, local-b", stdout.getvalue())
        self.assertIn("Choose a provider and model explicitly", stdout.getvalue())
        self.assertIn("did not install anything", stdout.getvalue())
        self.assertNotIn("selected model", stdout.getvalue().lower())

    def test_doctor_local_does_not_create_files(self) -> None:
        diagnostics = LocalDiagnostics(statuses=())

        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            before = set(Path(tmp).iterdir())
            stdout = io.StringIO()
            try:
                os.chdir(tmp)
                with mock.patch(
                    "delibra.cli.assess_local_runtime",
                    return_value=LocalRuntimeAssessment(diagnostics=diagnostics),
                ):
                    with contextlib.redirect_stdout(stdout):
                        code = main(["doctor", "local"])
            finally:
                os.chdir(previous_cwd)
            after = set(Path(tmp).iterdir())

        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        self.assertIn("no local provider probes configured", stdout.getvalue())

    def test_doctor_local_help_is_available(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stdout(stdout):
                main(["doctor", "local", "--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("Diagnose local LLM providers", stdout.getvalue())
        self.assertIn("--check-inference", stdout.getvalue())
        self.assertIn("--model", stdout.getvalue())

    def test_doctor_local_check_inference_renders_success(self) -> None:
        assessment = LocalRuntimeAssessment(
            diagnostics=LocalDiagnostics(
                statuses=(
                    LocalProviderStatus(
                        provider_id="ollama",
                        label="Ollama",
                        kind="ollama",
                        base_url="http://localhost:11434",
                        reachable=True,
                        models=("llama3.2",),
                        error=None,
                        recovery_hint=None,
                    ),
                )
            ),
            inference_checks=(
                LocalInferenceCheck(
                    provider_id="ollama",
                    attempted=True,
                    status="succeeded",
                    model="llama3.2",
                    duration_seconds=0.25,
                    error=None,
                    recovery_hint=None,
                ),
            ),
        )

        stdout = io.StringIO()
        with mock.patch("delibra.cli.assess_local_runtime", return_value=assessment):
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "doctor",
                        "local",
                        "--check-inference",
                        "--provider",
                        "ollama",
                        "--model",
                        "llama3.2",
                    ]
                )

        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("Inference check", output)
        self.assertIn("- ollama: succeeded", output)
        self.assertIn("model: llama3.2", output)
        self.assertIn("attempted: yes", output)

    def test_doctor_local_check_inference_renders_timeout_without_traceback(self) -> None:
        assessment = LocalRuntimeAssessment(
            diagnostics=LocalDiagnostics(statuses=()),
            inference_checks=(
                LocalInferenceCheck(
                    provider_id="ollama",
                    attempted=True,
                    status="timeout",
                    model="llama3.2",
                    error="timed out",
                    recovery_hint="Try a smaller model.",
                    duration_seconds=10.0,
                ),
            ),
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("delibra.cli.assess_local_runtime", return_value=assessment):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["doctor", "local", "--check-inference", "--model", "llama3.2"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("- ollama: timeout", stdout.getvalue())
        self.assertIn("cause: timed out", stdout.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue())

    def test_doctor_local_check_inference_does_not_create_files(self) -> None:
        assessment = LocalRuntimeAssessment(
            diagnostics=LocalDiagnostics(statuses=()),
            inference_checks=(
                LocalInferenceCheck(
                    provider_id="ollama",
                    attempted=False,
                    status="server_unreachable",
                    model="llama3.2",
                    error="connection refused",
                    recovery_hint="Start Ollama.",
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            before = set(Path(tmp).iterdir())
            stdout = io.StringIO()
            try:
                os.chdir(tmp)
                with mock.patch("delibra.cli.assess_local_runtime", return_value=assessment):
                    with contextlib.redirect_stdout(stdout):
                        code = main(
                            ["doctor", "local", "--check-inference", "--model", "llama3.2"]
                        )
            finally:
                os.chdir(previous_cwd)
            after = set(Path(tmp).iterdir())

        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        self.assertIn("Ollama server is not reachable", stdout.getvalue())
        self.assertIn("Skipped.", stdout.getvalue())
        self.assertIn("No inference was attempted.", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
