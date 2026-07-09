from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from delibra.app.local_diagnostics import LocalDiagnostics, LocalProviderStatus
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
        with mock.patch("delibra.cli.diagnose_local_providers", return_value=diagnostics):
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
        with mock.patch("delibra.cli.diagnose_local_providers", return_value=diagnostics):
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
                    "delibra.cli.diagnose_local_providers",
                    return_value=diagnostics,
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


if __name__ == "__main__":
    unittest.main()
