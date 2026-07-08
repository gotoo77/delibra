from __future__ import annotations

import unittest
from pathlib import Path

from delibra.core import RunStatus, StepKind
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol
from delibra.runtime import (
    IdSequence,
    MockLLMClient,
    default_engine_ids,
    deterministic_clock,
    execute_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
PRESET_PATHS = (
    ROOT / "presets" / "code_review.yaml",
    ROOT / "presets" / "design_review.yaml",
    ROOT / "presets" / "decision_review.yaml",
)


def execute_preset(path: Path):
    protocol = load_protocol_yaml(path)
    return execute_protocol(
        protocol,
        {"kind": "text", "content": f"input for {protocol.id}"},
        llm=MockLLMClient(IdSequence("msg_response")),
        ids=default_engine_ids(),
        clock=deterministic_clock(),
    )


class PresetTests(unittest.TestCase):
    def test_all_presets_validate(self) -> None:
        for path in PRESET_PATHS:
            with self.subTest(path=path):
                validate_protocol(load_protocol_yaml(path))

    def test_all_presets_execute_with_mock_provider(self) -> None:
        for path in PRESET_PATHS:
            with self.subTest(path=path):
                result = execute_preset(path)

                self.assertEqual(result.run.status, RunStatus.COMPLETED)
                self.assertEqual(result.run.artifacts[-1].output, "final_synthesis")
                self.assertEqual(result.run.artifacts[-1].kind, "synthesis")

    def test_presets_have_final_synthesize_step(self) -> None:
        for path in PRESET_PATHS:
            with self.subTest(path=path):
                protocol = load_protocol_yaml(path)

                self.assertEqual(protocol.steps[-1].kind, StepKind.SYNTHESIZE)
                self.assertEqual(protocol.steps[-1].produces.output, "final_synthesis")

    def test_fanout_produces_multiple_artifacts_under_declared_output(self) -> None:
        for path in PRESET_PATHS:
            with self.subTest(path=path):
                protocol = load_protocol_yaml(path)
                result = execute_preset(path)
                fanout_steps = [
                    step for step in protocol.steps if step.kind is StepKind.FANOUT
                ]

                self.assertGreaterEqual(len(fanout_steps), 1)
                for step in fanout_steps:
                    artifacts = [
                        artifact
                        for artifact in result.run.artifacts
                        if artifact.producer_step_id == step.id
                    ]
                    self.assertEqual(len(artifacts), len(step.roles or ()))
                    self.assertGreater(len(artifacts), 1)
                    self.assertEqual(
                        {artifact.output for artifact in artifacts},
                        {step.produces.output},
                    )

    def test_criticize_steps_produce_critique_artifacts(self) -> None:
        for path in PRESET_PATHS:
            with self.subTest(path=path):
                protocol = load_protocol_yaml(path)
                result = execute_preset(path)
                criticize_steps = [
                    step for step in protocol.steps if step.kind is StepKind.CRITICIZE
                ]

                self.assertGreaterEqual(len(criticize_steps), 1)
                for step in criticize_steps:
                    artifacts = [
                        artifact
                        for artifact in result.run.artifacts
                        if artifact.producer_step_id == step.id
                    ]
                    self.assertEqual(len(artifacts), len(step.roles or ()))
                    self.assertEqual({artifact.kind for artifact in artifacts}, {"critique"})

    def test_run_json_remains_canonical(self) -> None:
        expected_run_fields = {
            "id",
            "protocol",
            "status",
            "input",
            "artifacts",
            "trace_id",
            "started_at",
            "completed_at",
        }
        expected_artifact_fields = {
            "id",
            "kind",
            "output",
            "producer_step_id",
            "producer_role_id",
            "payload",
            "metadata",
            "created_at",
        }

        for path in PRESET_PATHS:
            with self.subTest(path=path):
                run_json = execute_preset(path).run.to_json()

                self.assertEqual(set(run_json), expected_run_fields)
                self.assertEqual(run_json["status"], "completed")
                self.assertGreaterEqual(len(run_json["artifacts"]), 1)
                for artifact in run_json["artifacts"]:
                    self.assertEqual(set(artifact), expected_artifact_fields)
                    self.assertNotIn("message", artifact)
                    self.assertNotIn("messages", artifact)


if __name__ == "__main__":
    unittest.main()
