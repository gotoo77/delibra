from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.core import Run, Trace


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "presets" / "code_review.yaml"


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


def create_run_and_trace(tmp: str) -> tuple[Path, Path]:
    run_path = Path(tmp) / "run.json"
    trace_path = Path(tmp) / "trace.json"
    result = run_cli(
        "run",
        "--protocol",
        str(PRESET),
        "--provider",
        "mock",
        "--input-text",
        "Review this change.",
        "--run-output",
        str(run_path),
        "--trace-output",
        str(trace_path),
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return run_path, trace_path


class InspectTests(unittest.TestCase):
    def test_run_and_trace_reload_from_canonical_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            run = Run.from_json(json.loads(run_path.read_text(encoding="utf-8")))
            trace = Trace.from_json(json.loads(trace_path.read_text(encoding="utf-8")))

            self.assertEqual(run.id, "run_0001")
            self.assertEqual(trace.run_id, run.id)
            self.assertEqual(len(run.artifacts), 7)
            self.assertGreater(len(trace.events), 0)

    def test_artifacts_are_inspectable_from_reloaded_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, _ = create_run_and_trace(tmp)

            run = Run.from_json(json.loads(run_path.read_text(encoding="utf-8")))
            artifact_summary = [
                (
                    artifact.output,
                    artifact.kind,
                    artifact.producer_step_id,
                    artifact.producer_role_id,
                )
                for artifact in run.artifacts
            ]

            self.assertIn(("framing", "framing", "frame", "framer"), artifact_summary)
            self.assertIn(("reviews", "review", "role_reviews", "maintainer"), artifact_summary)
            self.assertIn(("critiques", "critique", "critique_reviews", "critic"), artifact_summary)
            self.assertIn(("final_synthesis", "synthesis", "final", "synthesizer"), artifact_summary)

    def test_canonical_json_does_not_require_provider_or_message_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            run_json = json.loads(run_path.read_text(encoding="utf-8"))
            trace_json = json.loads(trace_path.read_text(encoding="utf-8"))

            self.assertNotIn("provider", run_json)
            self.assertNotIn("message", run_json)
            self.assertNotIn("messages", run_json)
            for artifact in run_json["artifacts"]:
                self.assertNotIn("provider", artifact)
                self.assertNotIn("message", artifact)
                self.assertNotIn("messages", artifact)
                self.assertNotIn("message_id", artifact)
            for event in trace_json["events"]:
                self.assertNotIn("provider", event)
                self.assertNotIn("model", event)
                self.assertNotIn("usage", event)

    def test_cli_inspect_with_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, _ = create_run_and_trace(tmp)

            result = run_cli("inspect", "--run", str(run_path))

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn("run: run_0001", result.stdout)
            self.assertIn("protocol: code_review@0.1.0", result.stdout)
            self.assertIn("artifacts: 7", result.stdout)
            self.assertIn("output=reviews kind=review", result.stdout)
            self.assertNotIn("trace_events:", result.stdout)

    def test_cli_inspect_with_run_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            result = run_cli(
                "inspect",
                "--run",
                str(run_path),
                "--trace",
                str(trace_path),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn("trace_events:", result.stdout)

    def test_cli_inspect_invalid_json_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp) / "run.json"
            run_path.write_text("{", encoding="utf-8")

            result = run_cli("inspect", "--run", str(run_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("delibra inspect:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_inspect_missing_run_file_message_is_unchanged(self) -> None:
        result = run_cli("inspect", "--run", "missing-run.json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "delibra inspect: run file not found: missing-run.json",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_inspect_wrong_durable_shape_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp) / "run.json"
            run_path.write_text(json.dumps({"id": "not-a-run"}), encoding="utf-8")

            result = run_cli("inspect", "--run", str(run_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Run missing fields", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_inspect_rejects_trace_for_different_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)
            trace_json = json.loads(trace_path.read_text(encoding="utf-8"))
            trace_json["run_id"] = "other_run"
            for event in trace_json["events"]:
                event["run_id"] = "other_run"
            trace_path.write_text(json.dumps(trace_json), encoding="utf-8")

            result = run_cli(
                "inspect",
                "--run",
                str(run_path),
                "--trace",
                str(trace_path),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("trace run_id does not match run id", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_analyze_missing_trace_file_message_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, _ = create_run_and_trace(tmp)

            result = run_cli(
                "analyze-run",
                "--run",
                str(run_path),
                "--trace",
                "missing-trace.json",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "delibra analyze-run: trace file not found: missing-trace.json",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_analyze_run_reports_observable_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            result = run_cli(
                "analyze-run",
                "--run",
                str(run_path),
                "--trace",
                str(trace_path),
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn("Protocol metrics", result.stdout)
            self.assertIn("protocol: code_review@0.1.0", result.stdout)
            self.assertIn("artifacts: 7", result.stdout)
            self.assertIn("trace_events:", result.stdout)
            self.assertIn("Artifact sizes", result.stdout)
            self.assertIn("Fanout-like steps", result.stdout)
            self.assertIn("- role_reviews: 3 roles", result.stdout)
            self.assertIn("Critique-like steps", result.stdout)
            self.assertIn("- critique_reviews: 2 roles", result.stdout)
            self.assertIn("Context pressure estimates", result.stdout)
            self.assertIn("Limitations", result.stdout)


if __name__ == "__main__":
    unittest.main()
