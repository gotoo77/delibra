from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from delibra.web.paths import (
    WebPathError,
    discover_runs,
    persisted_run_by_key,
    prepare_experiments_root,
    resolve_web_output_paths,
)
from tests.test_inspect import create_run_and_trace


class WebPathTests(unittest.TestCase):
    def test_prepare_experiments_root_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"

            prepared = prepare_experiments_root(root)

            self.assertEqual(prepared, root)
            self.assertTrue(root.is_dir())

    def test_resolves_relative_output_paths_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            root.mkdir()

            paths = resolve_web_output_paths(root, "local/model-a")

            self.assertEqual(paths.run_path, root / "local" / "model-a" / "run.json")
            self.assertEqual(paths.trace_path, root / "local" / "model-a" / "trace.json")

    def test_rejects_absolute_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            root.mkdir()

            with self.assertRaisesRegex(WebPathError, "relative"):
                resolve_web_output_paths(root, str(Path(tmp) / "outside"))

    def test_rejects_escaping_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            root.mkdir()

            with self.assertRaisesRegex(WebPathError, "stay within"):
                resolve_web_output_paths(root, "../outside")

    def test_rejects_internal_symlink_that_escapes_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "experiments"
            outside = tmp_path / "outside"
            root.mkdir()
            outside.mkdir()
            link = root / "link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            with self.assertRaisesRegex(WebPathError, "stay within"):
                resolve_web_output_paths(root, "link/run")

    def test_rejects_existing_run_outputs_to_limit_accidental_resubmission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            output = root / "demo"
            output.mkdir(parents=True)
            (output / "run.json").write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(WebPathError, "already contains"):
                resolve_web_output_paths(root, "demo")

    def test_discovers_valid_run_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            directory = root / "demo"
            directory.mkdir(parents=True)
            run_path, trace_path = create_run_and_trace(directory)

            runs = discover_runs(root)

            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0].label, "demo")
            self.assertEqual(runs[0].run_path, Path(run_path))
            self.assertEqual(runs[0].trace_path, Path(trace_path))
            self.assertTrue(runs[0].valid)

    def test_discovery_reports_invalid_pairs_without_modifying_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            bad = root / "bad"
            bad.mkdir(parents=True)
            run_path = bad / "run.json"
            trace_path = bad / "trace.json"
            run_path.write_text("{", encoding="utf-8")
            trace_path.write_text("{}", encoding="utf-8")

            runs = discover_runs(root)

            self.assertEqual(len(runs), 1)
            self.assertFalse(runs[0].valid)
            self.assertIsNotNone(runs[0].diagnostic)
            self.assertEqual(run_path.read_text(encoding="utf-8"), "{")
            self.assertEqual(json.loads(trace_path.read_text(encoding="utf-8")), {})

    def test_discovery_reports_mismatched_run_trace_as_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            directory = root / "bad"
            directory.mkdir(parents=True)
            run_path, trace_path = create_run_and_trace(directory)
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["run_id"] = "other_run"
            for event in trace["events"]:
                event["run_id"] = "other_run"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")

            runs = discover_runs(root)

            self.assertEqual(len(runs), 1)
            self.assertFalse(runs[0].valid)
            self.assertIn("trace run_id does not match", runs[0].diagnostic or "")

    def test_persisted_run_key_is_confined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            root.mkdir()

            with self.assertRaisesRegex(WebPathError, "stay within"):
                persisted_run_by_key(root, "../outside")


if __name__ == "__main__":
    unittest.main()
