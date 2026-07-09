from __future__ import annotations

import json
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


def _nested_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys.update(_nested_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_nested_keys(item))
    return keys


def _without_timestamps(value):
    if isinstance(value, dict):
        return {
            key: _without_timestamps(item)
            for key, item in value.items()
            if key not in {"started_at", "completed_at", "created_at", "timestamp"}
        }
    if isinstance(value, list):
        return [_without_timestamps(item) for item in value]
    return value


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
        self.assertIn("--policy", result.stdout)
        self.assertIn("path to an execution policy YAML file", result.stdout)
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

    def test_run_default_and_explicit_mock_provider_produce_same_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            default_run_output = tmp_path / "default-run.json"
            default_trace_output = tmp_path / "default-trace.json"
            explicit_run_output = tmp_path / "explicit-run.json"
            explicit_trace_output = tmp_path / "explicit-trace.json"

            default_result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--input-text",
                "Review this change.",
                "--run-output",
                str(default_run_output),
                "--trace-output",
                str(default_trace_output),
            )
            explicit_result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--provider",
                "mock",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(explicit_run_output),
                "--trace-output",
                str(explicit_trace_output),
            )

            self.assertEqual(default_result.returncode, 0)
            self.assertEqual(explicit_result.returncode, 0)
            self.assertEqual(default_result.stderr, "")
            self.assertEqual(explicit_result.stderr, "")
            default_run = json.loads(default_run_output.read_text(encoding="utf-8"))
            explicit_run = json.loads(explicit_run_output.read_text(encoding="utf-8"))
            default_trace = json.loads(default_trace_output.read_text(encoding="utf-8"))
            explicit_trace = json.loads(explicit_trace_output.read_text(encoding="utf-8"))

            self.assertEqual(
                _without_timestamps(default_run),
                _without_timestamps(explicit_run),
            )
            self.assertEqual(
                _without_timestamps(default_trace),
                _without_timestamps(explicit_trace),
            )

    def test_run_accepts_valid_policy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_output = tmp_path / "run.json"
            trace_output = tmp_path / "trace.json"
            policy_path = tmp_path / "policy.yaml"
            policy_path.write_text(
                "id: cheap-review\n"
                "mode: cheap\n"
                "budget:\n"
                "  max_estimated_units: 10000\n"
                "default_step_budget:\n"
                "  max_output_units: 300\n"
                "routes:\n"
                "  cheap-default:\n"
                "    provider: openai\n"
                "    model: gpt-5-mini\n"
                "steps:\n"
                "  frame:\n"
                "    route_id: cheap-default\n",
                encoding="utf-8",
            )

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--provider",
                "mock",
                "--policy",
                str(policy_path),
                "--input-text",
                "Review this change.",
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
            policy_applied = next(
                event for event in trace_json["events"] if event["type"] == "PolicyApplied"
            )
            self.assertEqual(policy_applied["type"], "PolicyApplied")
            self.assertEqual(
                policy_applied["payload"],
                {
                    "policy_id": "cheap-review",
                    "mode": "cheap",
                    "unit": "approx_token",
                },
            )
            decision_events = [
                event
                for event in trace_json["events"]
                if event["type"] == "PolicyDecision"
            ]
            self.assertGreater(len(decision_events), 0)
            self.assertEqual(decision_events[0]["payload"]["route_id"], "cheap-default")
            self.assertTrue(
                {"provider", "model", "tokens", "cost"}.isdisjoint(
                    _nested_keys(trace_json)
                )
            )

    def test_run_policy_budget_can_cancel_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_output = tmp_path / "run.json"
            trace_output = tmp_path / "trace.json"
            policy_path = tmp_path / "policy.yaml"
            policy_path.write_text(
                "id: too-cheap\n"
                "mode: standard\n"
                "budget:\n"
                "  max_estimated_units: 1\n",
                encoding="utf-8",
            )

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--provider",
                "mock",
                "--policy",
                str(policy_path),
                "--input-text",
                "Review this change.",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            run_json = json.loads(run_output.read_text(encoding="utf-8"))
            trace_json = json.loads(trace_output.read_text(encoding="utf-8"))
            self.assertEqual(run_json["status"], "cancelled")
            self.assertEqual(run_json["artifacts"], [])
            self.assertIn(
                "PolicyDecision",
                [event["type"] for event in trace_json["events"]],
            )
            self.assertIn(
                "BudgetExceeded",
                [event["type"] for event in trace_json["events"]],
            )
            self.assertTrue(
                {"provider", "model", "tokens", "cost"}.isdisjoint(
                    _nested_keys(trace_json)
                )
            )

    def test_run_invalid_policy_fails_before_writing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_output = tmp_path / "run.json"
            trace_output = tmp_path / "trace.json"
            policy_path = tmp_path / "policy.yaml"
            policy_path.write_text(
                "id: invalid\n"
                "mode: standard\n"
                "unit: tokens\n",
                encoding="utf-8",
            )

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--provider",
                "mock",
                "--policy",
                str(policy_path),
                "--input-text",
                "Review this change.",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid policy YAML shape", result.stderr)
            self.assertIn("approx_token", result.stderr)
            self.assertFalse(run_output.exists())
            self.assertFalse(trace_output.exists())
            self.assertNotIn("Traceback", result.stderr)

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
