from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.core import Artifact, Run, Trace, TraceEvent
from delibra.protocol_loader import load_protocol_yaml
from delibra.protocol_validator import validate_protocol


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "delibra" / "core"
PRESETS = ROOT / "presets"
CONCEPTS = ROOT / "docs" / "concepts"
ALLOWED_PRIMITIVES = {"prompt", "fanout", "criticize", "synthesize"}
FORBIDDEN_DURABLE_FIELDS = {
    "provider",
    "provider_id",
    "model",
    "usage",
    "tokens",
    "cost",
}


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


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports


def nested_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys.update(nested_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(nested_keys(item))
    return keys


def make_run_outputs(tmp: str) -> tuple[Path, Path]:
    run_path = Path(tmp) / "run.json"
    trace_path = Path(tmp) / "trace.json"
    result = run_cli(
        "run",
        "--protocol",
        str(PRESETS / "code_review.yaml"),
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


class ArchitectureInvariantTests(unittest.TestCase):
    def test_core_does_not_import_runtime_or_provider_modules(self) -> None:
        for path in CORE.glob("*.py"):
            with self.subTest(path=path):
                imports = imported_modules(path)

                self.assertFalse(
                    any(name == "delibra.runtime" or name.startswith("delibra.runtime.") for name in imports),
                    imports,
                )
                self.assertNotIn("delibra.runtime.openai", imports)
                self.assertFalse(
                    any("provider" in name.lower() for name in imports),
                    imports,
                )

    def test_runtime_provider_modules_are_not_imported_by_core(self) -> None:
        core_source = "\n".join(path.read_text(encoding="utf-8") for path in CORE.glob("*.py"))

        self.assertNotIn("OpenAI", core_source)
        self.assertNotIn("Provider", core_source)
        self.assertNotIn("delibra.runtime.openai", core_source)

    def test_durable_models_reject_unknown_fields(self) -> None:
        artifact_json = {
            "id": "artifact_0001",
            "kind": "review",
            "output": "reviews",
            "producer_step_id": "role_reviews",
            "producer_role_id": "maintainer",
            "payload": {},
            "metadata": {},
            "created_at": "2026-07-07T10:00:00Z",
        }
        event_json = {
            "id": "evt_0001",
            "type": "ArtifactCreated",
            "timestamp": "2026-07-07T10:00:01Z",
            "run_id": "run_0001",
            "step_id": "role_reviews",
            "payload": {},
        }
        trace_json = {
            "id": "trace_0001",
            "run_id": "run_0001",
            "events": [event_json],
        }
        run_json = {
            "id": "run_0001",
            "protocol": {"id": "code_review", "version": "0.1.0"},
            "status": "completed",
            "input": {"kind": "text", "content": "input"},
            "artifacts": [artifact_json],
            "trace_id": "trace_0001",
            "started_at": "2026-07-07T10:00:00Z",
            "completed_at": "2026-07-07T10:00:02Z",
        }

        with self.assertRaisesRegex(ValueError, "Artifact unknown fields"):
            Artifact.from_json({**artifact_json, "provider": "openai"})
        with self.assertRaisesRegex(ValueError, "TraceEvent unknown fields"):
            TraceEvent.from_json({**event_json, "message": {}})
        with self.assertRaisesRegex(ValueError, "Trace unknown fields"):
            Trace.from_json({**trace_json, "provider": "openai"})
        with self.assertRaisesRegex(ValueError, "Run unknown fields"):
            Run.from_json({**run_json, "model": "provider-model"})

    def test_integration_outputs_are_provider_free_and_message_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path, trace_path = make_run_outputs(tmp)
            run_json = json.loads(run_path.read_text(encoding="utf-8"))
            trace_json = json.loads(trace_path.read_text(encoding="utf-8"))

            self.assertTrue(FORBIDDEN_DURABLE_FIELDS.isdisjoint(nested_keys(run_json)))
            self.assertTrue(FORBIDDEN_DURABLE_FIELDS.isdisjoint(nested_keys(trace_json)))
            self.assertNotIn("message", nested_keys(run_json))
            self.assertNotIn("messages", nested_keys(run_json))
            for artifact in run_json["artifacts"]:
                self.assertNotIn("message", artifact)
                self.assertNotIn("messages", artifact)
                self.assertNotIn("message_id", artifact)
            for event in trace_json["events"]:
                self.assertNotIn("message", event)
                self.assertNotIn("messages", event)
                self.assertNotIn("message", event["payload"])
                self.assertNotIn("messages", event["payload"])

    def test_presets_use_only_v0_1_primitives(self) -> None:
        for path in sorted(PRESETS.glob("*.yaml")):
            with self.subTest(path=path):
                protocol = load_protocol_yaml(path)
                validate_protocol(protocol)

                self.assertTrue(
                    {step.kind.value for step in protocol.steps}.issubset(ALLOWED_PRIMITIVES)
                )

    def test_concept_notes_are_not_accepted_core_documentation(self) -> None:
        concept_index = (CONCEPTS / "README.md").read_text(encoding="utf-8")
        claim_model = (CONCEPTS / "claim-model.md").read_text(encoding="utf-8")

        self.assertIn("Concept notes document tensions, not ideas.", concept_index)
        self.assertIn("A concept note is not approval", (ROOT / "docs" / "adr" / "0001-core-identity.md").read_text(encoding="utf-8"))
        self.assertIn("Hypothesis", claim_model)
        self.assertIn("Rejected for v0.1", claim_model)
        self.assertNotIn("## Status\n\nCore", claim_model)


if __name__ == "__main__":
    unittest.main()
