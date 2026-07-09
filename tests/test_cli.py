from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, env_overrides: dict[str, str | None] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    if env_overrides is not None:
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value

    return subprocess.run(
        [sys.executable, "-m", "delibra", *args],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class CliSmokeTests(unittest.TestCase):
    def test_help_runs_successfully(self) -> None:
        result = run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra", result.stdout)
        self.assertIn("run a protocol with the selected provider", result.stdout)
        self.assertNotIn("run a protocol with the mock LLM", result.stdout)

    def test_version_runs_successfully(self) -> None:
        result = run_cli("--version")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertRegex(result.stdout.strip(), r"^delibra \d+\.\d+\.\d+$")

    def test_validate_help_runs_successfully(self) -> None:
        result = run_cli("validate", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra validate", result.stdout)
        self.assertIn("--protocol", result.stdout)
        self.assertIn("parse a protocol definition", result.stdout.lower())

    def test_run_help_runs_successfully(self) -> None:
        result = run_cli("run", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra run", result.stdout)
        self.assertIn("Run a protocol with the selected provider.", result.stdout)
        self.assertIn("--provider", result.stdout)
        self.assertIn("{mock,openai,ollama}", result.stdout)
        self.assertIn("provider: mock, openai, ollama; default mock", result.stdout)
        self.assertIn("--progress", result.stdout)
        self.assertNotIn("mock LLM", result.stdout)
        self.assertIn("--run-output", result.stdout)
        self.assertIn("--trace-output", result.stdout)

    def test_inspect_help_runs_successfully(self) -> None:
        result = run_cli("inspect", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra inspect", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertIn("--trace", result.stdout)

    def test_analyze_run_help_runs_successfully(self) -> None:
        result = run_cli("analyze-run", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra analyze-run", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertIn("--trace", result.stdout)

    def test_validate_requires_protocol_path(self) -> None:
        result = run_cli("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--protocol", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_requires_arguments(self) -> None:
        result = run_cli("run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--protocol", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_defaults_to_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--input-text",
                "Review this change.",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertTrue(run_output.exists())
            self.assertTrue(trace_output.exists())

    def test_run_accepts_explicit_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--provider",
                "mock",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_run_progress_writes_status_to_stderr_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "rfc_protocol.yaml"),
                "--provider",
                "mock",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
                "--progress",
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("delibra run: started", result.stderr)
            self.assertIn("provider=mock", result.stderr)
            self.assertIn("delibra run: step started step=reviews kind=fanout", result.stderr)
            self.assertIn("delibra run: role started step=reviews role=maintainer", result.stderr)
            self.assertIn("delibra run: completed artifacts=5", result.stderr)
            self.assertTrue(run_output.exists())
            self.assertTrue(trace_output.exists())

    def test_openai_provider_missing_config_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--provider",
                "openai",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
                env_overrides={
                    "OPENAI_API_KEY": None,
                    "OPENAI_MODEL": None,
                },
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OPENAI_API_KEY", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_ollama_provider_missing_config_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--provider",
                "ollama",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
                env_overrides={"OLLAMA_MODEL": None},
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OLLAMA_MODEL", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
