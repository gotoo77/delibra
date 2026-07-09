from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from delibra.app.storage import (
    load_json_object,
    load_run_json,
    load_trace_json,
    write_run_outputs,
)
from delibra.protocol_loader import load_protocol_yaml
from delibra.runtime import (
    IdSequence,
    MockLLMClient,
    default_engine_ids,
    deterministic_clock,
    execute_protocol,
)


ROOT = Path(__file__).resolve().parents[1]


class AppStorageTests(unittest.TestCase):
    def test_write_and_reload_run_outputs_round_trip_canonical_json(self) -> None:
        protocol = load_protocol_yaml(
            ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"
        )
        result = execute_protocol(
            protocol,
            {"kind": "text", "content": "Review this change."},
            llm=MockLLMClient(IdSequence("msg_response")),
            ids=default_engine_ids(),
            clock=deterministic_clock(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp) / "run.json"
            trace_path = Path(tmp) / "trace.json"

            write_run_outputs(result, run_path=run_path, trace_path=trace_path)

            self.assertEqual(load_run_json(run_path), result.run)
            self.assertEqual(load_trace_json(trace_path), result.trace)
            self.assertEqual(
                json.loads(run_path.read_text(encoding="utf-8")),
                result.run.to_json(),
            )
            self.assertEqual(
                json.loads(trace_path.read_text(encoding="utf-8")),
                result.trace.to_json(),
            )

    def test_load_run_json_missing_file_preserves_cli_error_text(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "run file not found: missing.json",
        ):
            load_run_json("missing.json")

    def test_load_trace_json_missing_file_preserves_cli_error_text(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "trace file not found: missing.json",
        ):
            load_trace_json("missing.json")

    def test_load_json_object_rejects_non_object_json(self) -> None:
        with self.assertRaisesRegex(TypeError, "run JSON must be a JSON object"):
            load_json_object("[]", "run JSON")


if __name__ == "__main__":
    unittest.main()
