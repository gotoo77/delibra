from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.protocol_loader import ProtocolLoadError, load_protocol_yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rfc_protocol.yaml"

EXPECTED_PROTOCOL_JSON = {
    "id": "code_review",
    "version": "0.1.0",
    "description": "Structured code review protocol.",
    "roles": {
        "framer": {
            "id": "framer",
            "name": "Framer",
            "instruction": "Restate scope and missing context.",
        },
    },
    "steps": [
        {
            "id": "frame",
            "kind": "prompt",
            "role": "framer",
            "roles": None,
            "instruction": "Frame the input.",
            "inputs": ["user_input"],
            "produces": {
                "output": "framing",
                "kind": "framing",
            },
        },
    ],
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


class ProtocolLoaderTests(unittest.TestCase):
    def test_loads_valid_protocol_yaml(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        self.assertEqual(protocol.to_json(), EXPECTED_PROTOCOL_JSON)

    def test_normalizes_role_map_entries_with_explicit_ids(self) -> None:
        protocol = load_protocol_yaml(FIXTURE)

        self.assertEqual(protocol.roles["framer"].id, "framer")
        self.assertEqual(protocol.to_json()["roles"]["framer"]["id"], "framer")

    def test_invalid_yaml_fails_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write("id: [\n")
            handle.flush()

            with self.assertRaisesRegex(ProtocolLoadError, "invalid protocol YAML"):
                load_protocol_yaml(handle.name)

    def test_missing_file_fails_cleanly(self) -> None:
        with self.assertRaisesRegex(ProtocolLoadError, "protocol file not found"):
            load_protocol_yaml(ROOT / "tests" / "fixtures" / "missing.yaml")

    def test_unknown_top_level_shape_fails_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: code_review\n"
                "version: 0.1.0\n"
                "description: Structured code review protocol.\n"
                "roles: {}\n"
                "steps: []\n"
                "workflow: {}\n"
            )
            handle.flush()

            with self.assertRaisesRegex(
                ProtocolLoadError, "invalid canonical protocol shape"
            ):
                load_protocol_yaml(handle.name)

    def test_invalid_yaml_role_shape_fails_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: code_review\n"
                "version: 0.1.0\n"
                "description: Structured code review protocol.\n"
                "roles: []\n"
                "steps: []\n"
            )
            handle.flush()

            with self.assertRaisesRegex(ProtocolLoadError, "invalid protocol YAML shape"):
                load_protocol_yaml(handle.name)

    def test_cli_validate_protocol_outputs_canonical_json(self) -> None:
        result = run_cli("validate", "--protocol", str(FIXTURE))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), EXPECTED_PROTOCOL_JSON)
        self.assertEqual(result.stderr, "")

    def test_cli_validate_missing_file_fails_cleanly(self) -> None:
        result = run_cli(
            "validate",
            "--protocol",
            str(ROOT / "tests" / "fixtures" / "missing.yaml"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protocol file not found", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_validate_invalid_yaml_fails_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write("id: [\n")
            handle.flush()

            result = run_cli("validate", "--protocol", handle.name)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid protocol YAML", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
