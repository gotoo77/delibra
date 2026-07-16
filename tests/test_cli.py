from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.cli import ProgressRenderer
from delibra.runtime import EngineProgressEvent


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


def progress_event(
    event_type: str,
    *,
    step_id: str | None = None,
    step_kind: str | None = None,
    role_id: str | None = None,
    artifact_id: str | None = None,
    artifact_count: int | None = None,
) -> EngineProgressEvent:
    return EngineProgressEvent(
        type=event_type,
        run_id="run_0001",
        protocol_id="protocol",
        protocol_version="0.1.0",
        step_id=step_id,
        step_kind=step_kind,
        role_id=role_id,
        artifact_id=artifact_id,
        artifact_count=artifact_count,
    )


def monotonic_clock(*values: float):
    items = iter(values)

    def now() -> float:
        return next(items)

    return now


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

    def test_validate_puzzle_spec_help_runs_successfully(self) -> None:
        result = run_cli("validate-puzzle-spec", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra validate-puzzle-spec", result.stdout)
        self.assertIn("--input-json", result.stdout)
        self.assertIn("--json", result.stdout)
        self.assertIn("puzzle_spec JSON document", result.stdout)

    def test_run_help_runs_successfully(self) -> None:
        result = run_cli("run", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra run", result.stdout)
        self.assertIn("Run a protocol with the selected provider.", result.stdout)
        self.assertIn("--protocol", result.stdout)
        self.assertIn("--preset", result.stdout)
        self.assertIn("name of a local preset", result.stdout)
        self.assertIn("--input-text", result.stdout)
        self.assertIn("--input-file", result.stdout)
        self.assertIn("--input-json", result.stdout)
        self.assertIn("inline JSON object input; arrays are allowed inside", result.stdout)
        self.assertIn("the object", result.stdout)
        self.assertIn("--provider", result.stdout)
        self.assertIn("{mock,openai,ollama}", result.stdout)
        self.assertIn("provider: mock, openai, ollama; default mock", result.stdout)
        self.assertIn("--language", result.stdout)
        self.assertIn("{auto,fr,en}", result.stdout)
        self.assertIn("language for generated artifact content", result.stdout)
        self.assertIn("--progress", result.stdout)
        self.assertIn("--policy", result.stdout)
        self.assertIn("path to an execution policy YAML file", result.stdout)
        self.assertNotIn("mock LLM", result.stdout)
        self.assertIn("--run-output", result.stdout)
        self.assertIn("--trace-output", result.stdout)
        self.assertIn("--output-dir", result.stdout)
        self.assertIn("Defaults are", result.stdout)
        self.assertIn("run.json and trace.json", result.stdout)

    def test_inspect_help_runs_successfully(self) -> None:
        result = run_cli("inspect", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra inspect", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertIn("--trace", result.stdout)
        self.assertIn("--artifact", result.stdout)

    def test_presets_list_help_runs_successfully(self) -> None:
        result = run_cli("presets", "list", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra presets list", result.stdout)
        self.assertIn("list available local presets", result.stdout.lower())

    def test_analyze_run_help_runs_successfully(self) -> None:
        result = run_cli("analyze-run", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra analyze-run", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertIn("--trace", result.stdout)

    def test_compare_runs_help_runs_successfully(self) -> None:
        result = run_cli("compare-runs", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: delibra compare-runs", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertIn("--trace", result.stdout)
        self.assertIn("--manifest", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertIn("Markdown draft", result.stdout)

    def test_web_help_runs_successfully(self) -> None:
        result = run_cli("web", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("usage: delibra web", result.stdout)
        self.assertIn("--host", result.stdout)
        self.assertIn("default 127.0.0.1", result.stdout)
        self.assertIn("--port", result.stdout)
        self.assertIn("default 8000", result.stdout)
        self.assertIn("--experiments-root", result.stdout)

    def test_validate_requires_protocol_path(self) -> None:
        result = run_cli("validate")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--protocol", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_validate_puzzle_spec_accepts_valid_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid-puzzle.json"
            path.write_text(
                json.dumps(
                    {
                        "scope": "single_fixed_spot",
                        "answer": "AUBEPINE",
                        "validation_method": "Compare the assembled cards with the printed answer slot.",
                        "player_separation_allowed": False,
                        "materials": ["letter cards", "answer slot card"],
                        "forbidden_mechanisms": ["lock"],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli("validate-puzzle-spec", "--input-json", str(path))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("valid: true", result.stdout)
        self.assertIn("errors: 0", result.stdout)

    def test_validate_puzzle_spec_rejects_invalid_document_with_error_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid-puzzle.json"
            path.write_text(
                json.dumps(
                    {
                        "scope": "castle_wide_hunt",
                        "answer": "Find the order of the relics and escape the castle.",
                        "validation_method": "The secret door opens automatically.",
                        "player_separation_allowed": True,
                        "materials": [],
                        "forbidden_mechanisms": [],
                        "description": "Relics are scattered throughout the castle.",
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli("validate-puzzle-spec", "--input-json", str(path))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertIn("valid: false", result.stdout)
        self.assertIn("ANSWER_NOT_EXPLICIT [answer]", result.stdout)
        self.assertIn("VALIDATION_METHOD_NOT_BUILDABLE [validation_method]", result.stdout)
        self.assertIn("DISQUALIFYING_SCOPE_PATTERN [$]", result.stdout)
        self.assertIn("FORBIDDEN_MECHANISM_MISSING [forbidden_mechanisms]", result.stdout)

    def test_validate_puzzle_spec_can_render_json_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid-puzzle.json"
            path.write_text(
                json.dumps(
                    {
                        "scope": "single_fixed_spot",
                        "answer": "",
                        "validation_method": "",
                        "player_separation_allowed": False,
                        "materials": ["cards"],
                        "forbidden_mechanisms": ["lock"],
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli("validate-puzzle-spec", "--input-json", str(path), "--json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload,
            {
                "valid": False,
                "errors": [
                    {
                        "code": "ANSWER_MISSING",
                        "field": "answer",
                        "message": "The answer must be a non-empty string.",
                    },
                    {
                        "code": "VALIDATION_METHOD_MISSING",
                        "field": "validation_method",
                        "message": "The validation method must be a non-empty string.",
                    },
                ],
            },
        )

    def test_validate_puzzle_spec_invalid_json_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{", encoding="utf-8")

            result = run_cli("validate-puzzle-spec", "--input-json", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid JSON", result.stderr)
        self.assertIn("broken.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_validate_puzzle_spec_missing_file_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"

            result = run_cli("validate-puzzle-spec", "--input-json", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("validate-puzzle-spec", result.stderr)
        self.assertIn("missing.json", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_requires_arguments(self) -> None:
        result = run_cli("run")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--protocol", result.stderr)
        self.assertIn("--preset", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_rejects_multiple_protocol_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--preset",
                "code_review",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not allowed with argument", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_rejects_multiple_input_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.txt"
            input_path.write_text("Review this change.", encoding="utf-8")
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--input-text",
                "Review this change.",
                "--input-file",
                str(input_path),
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not allowed with argument", result.stderr)
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

    def test_run_accepts_language_option_and_persists_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--language",
                "fr",
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            run_json = json.loads(run_output.read_text(encoding="utf-8"))
            self.assertEqual(run_json["language"], {"requested": "fr", "resolved": "fr"})

    def test_run_rejects_invalid_language_option(self) -> None:
        result = run_cli(
            "run",
            "--protocol",
            str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
            "--input-text",
            "Review this change.",
            "--language",
            "de",
            "--run-output",
            "run.json",
            "--trace-output",
            "trace.json",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice: 'de'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_requires_outputs_without_output_dir(self) -> None:
        result = run_cli(
            "run",
            "--protocol",
            str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
            "--input-text",
            "Review this change.",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--run-output and --trace-output are required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_output_dir_writes_default_files_and_prints_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments" / "local" / "mistral"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--provider",
                "mock",
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertTrue((output_dir / "run.json").exists())
            self.assertTrue((output_dir / "trace.json").exists())
            self.assertIn(f"run_output: {output_dir / 'run.json'}", result.stdout)
            self.assertIn(f"trace_output: {output_dir / 'trace.json'}", result.stdout)

    def test_run_output_dir_accepts_relative_custom_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments" / "custom"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
                "--run-output",
                "data/mistral.run.json",
                "--trace-output",
                "data/mistral.trace.json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / "data" / "mistral.run.json").exists())
            self.assertTrue((output_dir / "data" / "mistral.trace.json").exists())

    def test_run_output_dir_rejects_absolute_custom_output_before_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "presets" / "code_review.yaml"),
                "--provider",
                "openai",
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
                "--run-output",
                str(Path(tmp) / "outside.run.json"),
                "--trace-output",
                "trace.json",
                env_overrides={
                    "OPENAI_API_KEY": None,
                    "OPENAI_MODEL": None,
                },
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--run-output must be relative", result.stderr)
            self.assertNotIn("OPENAI_API_KEY", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_output_dir_rejects_escaping_relative_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
                "--run-output",
                "../outside.run.json",
                "--trace-output",
                "trace.json",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--run-output must stay within --output-dir", result.stderr)
            self.assertFalse(output_dir.exists())
            self.assertNotIn("Traceback", result.stderr)

    def test_run_output_dir_rejects_identical_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(Path(tmp) / "experiments"),
                "--run-output",
                "result.json",
                "--trace-output",
                "result.json",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run and trace output paths must be different", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_output_dir_rejects_existing_file_as_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            output_dir.write_text("not a directory", encoding="utf-8")

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output directory path is not a directory", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_output_dir_preserves_existing_overwrite_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments"
            output_dir.mkdir()
            run_output = output_dir / "run.json"
            trace_output = output_dir / "trace.json"
            run_output.write_text("old run", encoding="utf-8")
            trace_output.write_text("old trace", encoding="utf-8")

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-text",
                "Review this change.",
                "--output-dir",
                str(output_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(run_output.read_text(encoding="utf-8"), "old run")
            self.assertNotEqual(trace_output.read_text(encoding="utf-8"), "old trace")
            self.assertEqual(json.loads(run_output.read_text(encoding="utf-8"))["id"], "run_0001")

    def test_run_accepts_input_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.txt"
            input_path.write_text("Review this file input.", encoding="utf-8")
            run_output = tmp_path / "run.json"
            trace_output = tmp_path / "trace.json"

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-file",
                str(input_path),
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            run_json = json.loads(run_output.read_text(encoding="utf-8"))
            self.assertEqual(
                run_json["input"],
                {"kind": "text", "content": "Review this file input."},
            )

    def test_run_missing_input_file_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-file",
                str(Path(tmp) / "missing.txt"),
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("input file not found", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_accepts_input_json_without_coercion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_output = tmp_path / "run.json"
            trace_output = tmp_path / "trace.json"
            raw_input = json.dumps(
                {
                    "kind": "structured",
                    "decision": {"title": "Ship v1", "risk": 3},
                    "tags": ["cli", "json"],
                }
            )

            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-json",
                raw_input,
                "--run-output",
                str(run_output),
                "--trace-output",
                str(trace_output),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            run_json = json.loads(run_output.read_text(encoding="utf-8"))
            self.assertEqual(
                run_json["input"],
                {
                    "kind": "structured",
                    "decision": {"title": "Ship v1", "risk": 3},
                    "tags": ["cli", "json"],
                },
            )

    def test_run_malformed_input_json_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-json",
                "{",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid input JSON", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_non_object_input_json_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--protocol",
                str(ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"),
                "--input-json",
                "[1, 2, 3]",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("input JSON must be a JSON object", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_accepts_preset_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_output = Path(tmp) / "run.json"
            trace_output = Path(tmp) / "trace.json"

            result = run_cli(
                "run",
                "--preset",
                "code_review",
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
            self.assertEqual(run_json["protocol"]["id"], "code_review")

    def test_run_rejects_unsafe_preset_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--preset",
                "../tests/fixtures/rfc_protocol",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid preset name", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_run_unknown_preset_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                "run",
                "--preset",
                "missing",
                "--input-text",
                "Review this change.",
                "--run-output",
                str(Path(tmp) / "run.json"),
                "--trace-output",
                str(Path(tmp) / "trace.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("preset not found: missing", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_presets_list_reports_known_presets(self) -> None:
        result = run_cli("presets", "list")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("Available presets", result.stdout)
        self.assertIn("code_review: code_review@0.1.0", result.stdout)
        self.assertIn(
            "treasure_hunt_design_selection: treasure_hunt_design_selection@0.1.0",
            result.stdout,
        )

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
            self.assertIn("[+", result.stderr)
            self.assertIn("delibra run: started", result.stderr)
            self.assertIn("provider=mock", result.stderr)
            self.assertIn("delibra run: step started step=reviews kind=fanout", result.stderr)
            self.assertIn("delibra run: role started step=reviews role=maintainer", result.stderr)
            self.assertIn("duration=", result.stderr)
            self.assertIn("delibra run: completed artifacts=5", result.stderr)
            self.assertTrue(run_output.exists())
            self.assertTrue(trace_output.exists())

    def test_progress_renderer_reports_elapsed_and_step_duration(self) -> None:
        renderer = ProgressRenderer(
            "mock",
            monotonic_clock=monotonic_clock(100.0, 100.2, 104.8, 104.9),
        )

        self.assertEqual(
            renderer.render(progress_event("run_started")),
            "[+0.00s] delibra run: started run=run_0001 protocol=protocol@0.1.0 provider=mock",
        )
        self.assertEqual(
            renderer.render(
                progress_event("step_started", step_id="frame", step_kind="prompt")
            ),
            "[+0.20s] delibra run: step started step=frame kind=prompt",
        )
        self.assertEqual(
            renderer.render(
                progress_event("step_completed", step_id="frame", artifact_count=1)
            ),
            "[+4.80s] delibra run: step completed step=frame artifacts=1 duration=4.60s",
        )
        self.assertEqual(
            renderer.render(progress_event("run_completed", artifact_count=1)),
            "[+4.90s] delibra run: completed artifacts=1 duration=4.90s",
        )

    def test_progress_renderer_keeps_independent_step_start_times(self) -> None:
        renderer = ProgressRenderer(
            "mock",
            monotonic_clock=monotonic_clock(0.0, 1.0, 2.0, 5.0, 8.0),
        )

        renderer.render(progress_event("run_started"))
        renderer.render(progress_event("step_started", step_id="a", step_kind="prompt"))
        renderer.render(
            progress_event("role_started", step_id="a", role_id="framer")
        )
        renderer.render(
            progress_event("step_started", step_id="b", step_kind="synthesize")
        )
        rendered = renderer.render(
            progress_event("step_completed", step_id="a", artifact_count=1)
        )

        self.assertEqual(
            rendered,
            "[+8.00s] delibra run: step completed step=a artifacts=1 duration=7.00s",
        )

    def test_progress_renderer_omits_duration_when_step_start_is_unknown(self) -> None:
        renderer = ProgressRenderer(
            "mock",
            monotonic_clock=monotonic_clock(10.0, 14.0),
        )

        renderer.render(progress_event("run_started"))
        rendered = renderer.render(
            progress_event("step_completed", step_id="frame", artifact_count=1)
        )

        self.assertEqual(
            rendered,
            "[+4.00s] delibra run: step completed step=frame artifacts=1",
        )

    def test_progress_renderer_omits_duration_when_run_start_is_unknown(self) -> None:
        renderer = ProgressRenderer("mock", monotonic_clock=monotonic_clock(14.0))

        rendered = renderer.render(progress_event("run_completed", artifact_count=1))

        self.assertEqual(
            rendered,
            "[+0.00s] delibra run: completed artifacts=1",
        )

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
