from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from delibra.app.analysis import analyze_run
from delibra.app.inspection import inspect_run
from delibra.app.storage import load_run_json, load_trace_json
from delibra.cli import _render_inspection, _render_run_analysis
from tests.test_inspect import create_run_and_trace, run_cli


class AppInspectionAnalysisTests(unittest.TestCase):
    def test_inspect_run_returns_structured_summary_without_rendering_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)
            inspection = inspect_run(
                load_run_json(run_path),
                load_trace_json(trace_path),
            )

            self.assertEqual(inspection.run_id, "run_0001")
            self.assertEqual(inspection.status, "completed")
            self.assertEqual(inspection.protocol_id, "code_review")
            self.assertEqual(inspection.protocol_version, "0.1.0")
            self.assertEqual(inspection.requested_language, "auto")
            self.assertEqual(inspection.resolved_language, "en")
            self.assertEqual(inspection.artifact_count, 7)
            self.assertGreater(inspection.trace_event_count or 0, 0)
            self.assertIn(
                ("reviews", "review", "role_reviews", "maintainer"),
                [
                    (
                        artifact.output,
                        artifact.kind,
                        artifact.producer_step_id,
                        artifact.producer_role_id,
                    )
                    for artifact in inspection.artifacts
                ],
            )

    def test_analyze_run_returns_structured_metrics_without_rendering_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)
            analysis = analyze_run(
                load_run_json(run_path),
                load_trace_json(trace_path),
            )

            self.assertEqual(analysis.run_id, "run_0001")
            self.assertEqual(analysis.status, "completed")
            self.assertEqual(analysis.protocol_id, "code_review")
            self.assertEqual(analysis.protocol_version, "0.1.0")
            self.assertEqual(analysis.artifact_count, 7)
            self.assertEqual(len(analysis.artifact_metrics), 7)
            self.assertGreater(analysis.total_payload_chars, 0)
            self.assertGreater(analysis.total_artifact_json_chars, 0)
            self.assertGreater(analysis.average_payload_chars, 0)
            self.assertIsNotNone(analysis.largest_artifact)
            self.assertIn(
                ("role_reviews", 3),
                [
                    (step.step_id, step.role_count)
                    for step in analysis.fanout_like_steps
                ],
            )
            self.assertIn(
                ("critique_reviews", 2),
                [
                    (step.step_id, step.role_count)
                    for step in analysis.critique_like_steps
                ],
            )
            self.assertEqual(
                analysis.estimated_tokens_upper_bound,
                round(analysis.cumulative_artifact_context_chars_upper_bound / 4),
            )
            self.assertEqual(
                analysis.limitations,
                (
                    "Exact provider input sizes, token usage, latency, and cost are not persisted in run.json or trace.json.",
                    "Context metrics above are deterministic upper-bound estimates from persisted input and artifacts, not provider billing data.",
                ),
            )

    def test_empty_trace_is_optional_for_structured_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, _ = create_run_and_trace(tmp)
            run = load_run_json(Path(run_path))

            inspection = inspect_run(run)
            analysis = analyze_run(run)

            self.assertIsNone(inspection.trace_event_count)
            self.assertIsNone(analysis.trace_event_count)

    def test_inspect_run_reports_legacy_missing_language_as_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, _ = create_run_and_trace(tmp)
            run = load_run_json(Path(run_path))
            legacy_json = run.to_json()
            legacy_json.pop("language")
            legacy = type(run).from_json(legacy_json)

            inspection = inspect_run(legacy)

            self.assertIsNone(inspection.requested_language)
            self.assertIsNone(inspection.resolved_language)
            self.assertIn("language: not recorded", _render_inspection(inspection))

    def test_cli_inspect_output_matches_structured_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            result = run_cli("inspect", "--run", str(run_path), "--trace", str(trace_path))
            expected = _render_inspection(
                inspect_run(load_run_json(run_path), load_trace_json(trace_path))
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertEqual(result.stdout, expected + "\n")

    def test_cli_analyze_output_matches_structured_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = create_run_and_trace(tmp)

            result = run_cli(
                "analyze-run",
                "--run",
                str(run_path),
                "--trace",
                str(trace_path),
            )
            expected = _render_run_analysis(
                analyze_run(load_run_json(run_path), load_trace_json(trace_path))
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertEqual(result.stdout, expected + "\n")


if __name__ == "__main__":
    unittest.main()
