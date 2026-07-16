from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from delibra.app.inputs import input_from_text
from delibra.app.models import ProviderConfig
from delibra.app.output_paths import resolve_run_output_paths
from delibra.app.run import RunProtocolApplicationRequest, run_protocol_application
from delibra.app.storage import load_run_json, load_trace_json
from delibra.protocol_loader import load_protocol_yaml


ROOT = Path(__file__).resolve().parents[1]


class AppRunServiceTests(unittest.TestCase):
    def test_run_service_executes_protocol_and_writes_canonical_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "run"
            result = run_protocol_application(
                RunProtocolApplicationRequest(
                    protocol=load_protocol_yaml(
                        ROOT / "tests" / "fixtures" / "prompt_synthesize_protocol.yaml"
                    ),
                    input_ref=input_from_text("Review this change."),
                    provider=ProviderConfig("mock"),
                    output_paths=resolve_run_output_paths(
                        run_output=None,
                        trace_output=None,
                        output_dir=str(output_dir),
                    ),
                )
            )

            run = load_run_json(result.run_path)
            trace = load_trace_json(result.trace_path)
            self.assertEqual(run.status.value, "completed")
            self.assertEqual(trace.run_id, run.id)
            self.assertEqual(result.result.run.id, run.id)


if __name__ == "__main__":
    unittest.main()
