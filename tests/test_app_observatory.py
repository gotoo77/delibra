from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from delibra.app.observatory import (
    RunTraceFiles,
    compare_run_files,
    load_experiment_manifest,
    render_comparison_markdown,
)
from tests.test_inspect import run_cli


def artifact_json(
    artifact_id: str,
    *,
    step_id: str,
    role_id: str,
    output: str,
    kind: str,
    content: str,
) -> dict:
    return {
        "id": artifact_id,
        "kind": kind,
        "output": output,
        "producer_step_id": step_id,
        "producer_role_id": role_id,
        "payload": {"content": content},
        "metadata": {},
        "created_at": "2026-07-16T10:00:00Z",
    }


def run_json(
    run_id: str,
    trace_id: str,
    *,
    protocol_id: str = "decision_review",
    protocol_version: str = "0.1.0",
    status: str = "completed",
    input_value: dict | None = None,
    artifacts: list[dict] | None = None,
) -> dict:
    if input_value is None:
        input_value = {
            "kind": "text",
            "content": "Should Delibra support local LLMs by default?",
        }
    if artifacts is None:
        artifacts = base_artifacts("artifact")
    return {
        "id": run_id,
        "protocol": {"id": protocol_id, "version": protocol_version},
        "status": status,
        "input": input_value,
        "artifacts": artifacts,
        "trace_id": trace_id,
        "started_at": "2026-07-16T10:00:00Z",
        "completed_at": "2026-07-16T10:00:03Z" if status == "completed" else None,
    }


def trace_json(trace_id: str, run_id: str, artifacts: list[dict]) -> dict:
    events = [
        {
            "id": "evt_0001",
            "type": "RunCreated",
            "timestamp": "2026-07-16T10:00:00Z",
            "run_id": run_id,
            "step_id": None,
            "payload": {},
        }
    ]
    for index, artifact in enumerate(artifacts, start=2):
        events.append(
            {
                "id": f"evt_{index:04d}",
                "type": "ArtifactCreated",
                "timestamp": f"2026-07-16T10:00:{index:02d}Z",
                "run_id": run_id,
                "step_id": artifact["producer_step_id"],
                "payload": {
                    "artifact_id": artifact["id"],
                    "output": artifact["output"],
                    "kind": artifact["kind"],
                    "producer_role_id": artifact["producer_role_id"],
                },
            }
        )
    return {"id": trace_id, "run_id": run_id, "events": events}


def base_artifacts(prefix: str) -> list[dict]:
    return [
        artifact_json(
            f"{prefix}_0001",
            step_id="frame",
            role_id="framer",
            output="framing",
            kind="framing",
            content="frame",
        ),
        artifact_json(
            f"{prefix}_0002",
            step_id="role_reviews",
            role_id="strategist",
            output="reviews",
            kind="review",
            content="strategy",
        ),
        artifact_json(
            f"{prefix}_0003",
            step_id="final",
            role_id="synthesizer",
            output="final_synthesis",
            kind="synthesis",
            content="final",
        ),
    ]


def write_pair(tmp: Path, name: str, run: dict, trace: dict) -> RunTraceFiles:
    run_path = tmp / f"{name}.run.json"
    trace_path = tmp / f"{name}.trace.json"
    run_path.write_text(json.dumps(run), encoding="utf-8")
    trace_path.write_text(json.dumps(trace), encoding="utf-8")
    return RunTraceFiles(run_path=run_path, trace_path=trace_path)


class ObservatoryComparisonTests(unittest.TestCase):
    def test_two_runs_are_strictly_comparable_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            first_artifacts = base_artifacts("a")
            second_artifacts = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=first_artifacts),
                trace_json("trace_0001", "run_0001", first_artifacts),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=second_artifacts),
                trace_json("trace_0002", "run_0002", second_artifacts),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(comparison.assessment.classification, "comparable")
            self.assertEqual(len(comparison.aligned_positions), 3)
            self.assertEqual(comparison.runs[0].label, "run_1")
            self.assertEqual(
                comparison.aligned_positions[0].position.artifact_kind,
                "framing",
            )
            self.assertEqual(
                comparison.aligned_positions[0].position.key,
                "frame / framer / framing / framing / 1",
            )

    def test_three_runs_keep_stable_order_and_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            pairs = []
            for index in range(1, 4):
                artifacts = base_artifacts(f"r{index}")
                pairs.append(
                    write_pair(
                        tmp,
                        f"run{index}",
                        run_json(f"run_{index:04d}", f"trace_{index:04d}", artifacts=artifacts),
                        trace_json(f"trace_{index:04d}", f"run_{index:04d}", artifacts),
                    )
                )

            comparison = compare_run_files(tuple(pairs))

            self.assertEqual(comparison.assessment.classification, "comparable")
            self.assertEqual([run.label for run in comparison.runs], ["run_1", "run_2", "run_3"])
            self.assertEqual(
                [position.position.key for position in comparison.aligned_positions],
                [
                    "frame / framer / framing / framing / 1",
                    "role_reviews / strategist / reviews / review / 1",
                    "final / synthesizer / final_synthesis / synthesis / 1",
                ],
            )

    def test_protocol_version_and_input_differences_are_not_comparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            first_artifacts = base_artifacts("a")
            second_artifacts = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=first_artifacts),
                trace_json("trace_0001", "run_0001", first_artifacts),
            )
            second = write_pair(
                tmp,
                "second",
                run_json(
                    "run_0002",
                    "trace_0002",
                    protocol_version="0.2.0",
                    input_value={"kind": "text", "content": "Different"},
                    artifacts=second_artifacts,
                ),
                trace_json("trace_0002", "run_0002", second_artifacts),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(comparison.assessment.classification, "not_comparable")
            self.assertTrue(
                any("protocol versions differ" in item for item in comparison.assessment.incompatibilities)
            )
            self.assertTrue(
                any("inputs differ" in item for item in comparison.assessment.incompatibilities)
            )

    def test_protocol_id_difference_is_not_comparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", protocol_id="design_review", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(comparison.assessment.classification, "not_comparable")
            self.assertTrue(
                any("protocol ids differ" in item for item in comparison.assessment.incompatibilities)
            )

    def test_trace_mismatch_is_not_comparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_expected", artifacts=artifacts_b),
                trace_json("trace_actual", "run_0002", artifacts_b),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(comparison.assessment.classification, "not_comparable")
            self.assertTrue(
                any("trace_id" in item for item in comparison.assessment.incompatibilities)
            )

    def test_missing_role_and_extra_artifact_are_reservations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            first_artifacts = base_artifacts("a")
            second_artifacts = [
                first_artifacts[0] | {"id": "b_0001"},
                artifact_json(
                    "b_0004",
                    step_id="bonus",
                    role_id="auditor",
                    output="audit",
                    kind="review",
                    content="extra",
                ),
                first_artifacts[2] | {"id": "b_0003"},
            ]
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=first_artifacts),
                trace_json("trace_0001", "run_0001", first_artifacts),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=second_artifacts),
                trace_json("trace_0002", "run_0002", second_artifacts),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(
                comparison.assessment.classification,
                "comparable_with_reservations",
            )
            self.assertTrue(
                any("missing" in item for item in comparison.assessment.reservations)
            )
            self.assertTrue(
                any("structure differs" in item for item in comparison.assessment.reservations)
            )

    def test_duplicate_base_position_uses_ordinal_and_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            first_artifacts = base_artifacts("a") + [
                artifact_json(
                    "a_0004",
                    step_id="role_reviews",
                    role_id="strategist",
                    output="reviews",
                    kind="review",
                    content="strategy second",
                )
            ]
            second_artifacts = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=first_artifacts),
                trace_json("trace_0001", "run_0001", first_artifacts),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=second_artifacts),
                trace_json("trace_0002", "run_0002", second_artifacts),
            )

            comparison = compare_run_files((first, second))

            self.assertTrue(
                any("ordinal alignment is used" in item for item in comparison.assessment.incompatibilities + comparison.assessment.reservations)
            )
            self.assertIn(
                "role_reviews / strategist / reviews / review / 2",
                [position.position.key for position in comparison.aligned_positions],
            )

    def test_empty_input_and_failed_run_are_reservations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", input_value={}, artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json(
                    "run_0002",
                    "trace_0002",
                    status="failed",
                    input_value={},
                    artifacts=artifacts_b,
                ),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )

            comparison = compare_run_files((first, second))

            self.assertEqual(
                comparison.assessment.classification,
                "comparable_with_reservations",
            )
            self.assertTrue(any("input is empty" in item for item in comparison.assessment.reservations))
            self.assertTrue(any("not completed" in item for item in comparison.assessment.reservations))

    def test_manifest_labels_external_dimensions_and_inconsistencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )
            manifest_path = tmp / "experiment.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "experiment_id": "local-llm-default",
                        "protocol": {"id": "wrong", "version": "0.1.0"},
                        "input": {
                            "text": "Should Delibra support local LLMs by default?"
                        },
                        "controlled_dimensions": ["protocol", "protocol_version", "input"],
                        "changed_dimensions": ["model"],
                        "runs": [
                            {
                                "label": "qwen",
                                "run_file": first.run_path.name,
                                "trace_file": first.trace_path.name,
                                "execution_environment": {
                                    "provider": "ollama",
                                    "model": "qwen3:4b",
                                },
                            },
                            {
                                "label": "mistral",
                                "run_file": second.run_path.name,
                                "trace_file": second.trace_path.name,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            manifest = load_experiment_manifest(manifest_path)

            comparison = compare_run_files((first, second), manifest=manifest)

            self.assertEqual([run.label for run in comparison.runs], ["qwen", "mistral"])
            self.assertEqual(comparison.assessment.changed_dimensions, ("model",))
            self.assertTrue(
                any("manifest protocol.id wrong" in item for item in comparison.assessment.manifest_inconsistencies)
            )

    def test_manifest_duplicate_labels_fail_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )
            manifest_path = tmp / "experiment.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "runs": [
                            {"label": "same", "run_file": first.run_path.name},
                            {"label": "same", "run_file": second.run_path.name},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            manifest = load_experiment_manifest(manifest_path)

            with self.assertRaisesRegex(ValueError, "duplicate run label: same"):
                compare_run_files((first, second), manifest=manifest)

    def test_manifest_empty_label_fails_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )
            manifest_path = tmp / "experiment.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "runs": [
                            {"label": "", "run_file": first.run_path.name},
                            {"label": "second", "run_file": second.run_path.name},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            manifest = load_experiment_manifest(manifest_path)

            with self.assertRaisesRegex(ValueError, "run labels must be non-empty"):
                compare_run_files((first, second), manifest=manifest)

    def test_markdown_is_deterministic_review_required_and_non_semantic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )
            comparison = compare_run_files((first, second))

            first_render = render_comparison_markdown(comparison)
            second_render = render_comparison_markdown(comparison)

            self.assertEqual(first_render, second_render)
            self.assertIn("review_required: true", first_render)
            self.assertIn("artifact_kind", first_render)
            self.assertIn("Step kind", first_render)
            self.assertIn("text chars=45; digest=sha256:", first_render)
            self.assertNotIn("Should Delibra support local LLMs by default?", first_render)
            self.assertIn("Human Observations", first_render)
            self.assertIn("Human Qualifications", first_render)
            self.assertNotIn("hallucination", first_render.lower())
            self.assertNotIn("model ranking", first_render.lower())

    def test_cli_compare_runs_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            artifacts_a = base_artifacts("a")
            artifacts_b = base_artifacts("b")
            first = write_pair(
                tmp,
                "first",
                run_json("run_0001", "trace_0001", artifacts=artifacts_a),
                trace_json("trace_0001", "run_0001", artifacts_a),
            )
            second = write_pair(
                tmp,
                "second",
                run_json("run_0002", "trace_0002", artifacts=artifacts_b),
                trace_json("trace_0002", "run_0002", artifacts_b),
            )
            output = tmp / "comparison.md"

            result = run_cli(
                "compare-runs",
                "--run",
                str(first.run_path),
                "--trace",
                str(first.trace_path),
                "--run",
                str(second.run_path),
                "--trace",
                str(second.trace_path),
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("classification: comparable", result.stdout)
            self.assertIn("# Delibra Run Comparison", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
