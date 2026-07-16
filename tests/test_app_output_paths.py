from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from delibra.app.output_paths import (
    RunOutputPathError,
    prepare_run_output_paths,
    resolve_run_output_paths,
)


class RunOutputPathTests(unittest.TestCase):
    def test_historical_outputs_resolve_without_output_dir(self) -> None:
        paths = resolve_run_output_paths(
            run_output="custom.run.json",
            trace_output="custom.trace.json",
            output_dir=None,
        )

        self.assertEqual(paths.run_path, Path("custom.run.json"))
        self.assertEqual(paths.trace_path, Path("custom.trace.json"))
        self.assertIsNone(paths.output_dir)

    def test_outputs_are_required_without_output_dir(self) -> None:
        with self.assertRaisesRegex(RunOutputPathError, "--run-output and --trace-output"):
            resolve_run_output_paths(
                run_output=None,
                trace_output="trace.json",
                output_dir=None,
            )

    def test_output_dir_uses_default_names(self) -> None:
        paths = resolve_run_output_paths(
            run_output=None,
            trace_output=None,
            output_dir="experiments/demo",
        )

        self.assertEqual(paths.run_path, Path("experiments/demo/run.json"))
        self.assertEqual(paths.trace_path, Path("experiments/demo/trace.json"))
        self.assertEqual(paths.output_dir, Path("experiments/demo"))

    def test_output_dir_resolves_relative_custom_names(self) -> None:
        paths = resolve_run_output_paths(
            run_output="mistral.run.json",
            trace_output="mistral.trace.json",
            output_dir="experiments/demo",
        )

        self.assertEqual(paths.run_path, Path("experiments/demo/mistral.run.json"))
        self.assertEqual(paths.trace_path, Path("experiments/demo/mistral.trace.json"))

    def test_output_dir_resolves_relative_subdirectories(self) -> None:
        paths = resolve_run_output_paths(
            run_output="data/custom.run.json",
            trace_output="data/custom.trace.json",
            output_dir="experiments/demo",
        )

        self.assertEqual(paths.run_path, Path("experiments/demo/data/custom.run.json"))
        self.assertEqual(paths.trace_path, Path("experiments/demo/data/custom.trace.json"))

    def test_output_dir_normalizes_dot_components(self) -> None:
        paths = resolve_run_output_paths(
            run_output="./data/./custom.run.json",
            trace_output="./trace.json",
            output_dir="./experiments/./demo",
        )

        self.assertEqual(
            paths.run_path.resolve(strict=False),
            Path("experiments/demo/data/custom.run.json").resolve(strict=False),
        )
        self.assertEqual(
            paths.trace_path.resolve(strict=False),
            Path("experiments/demo/trace.json").resolve(strict=False),
        )

    def test_output_dir_rejects_absolute_run_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RunOutputPathError, "must be relative"):
                resolve_run_output_paths(
                    run_output=str(Path(tmp) / "run.json"),
                    trace_output="trace.json",
                    output_dir="experiments/demo",
                )

    def test_output_dir_rejects_paths_escaping_directory(self) -> None:
        with self.assertRaisesRegex(RunOutputPathError, "must stay within"):
            resolve_run_output_paths(
                run_output="data/../../../outside.run.json",
                trace_output="trace.json",
                output_dir="experiments/demo",
            )

    def test_absolute_output_dir_allows_relative_outputs_inside_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "experiments" / "demo"

            paths = resolve_run_output_paths(
                run_output="data/custom.run.json",
                trace_output="trace.json",
                output_dir=str(output_dir),
            )

            self.assertEqual(paths.run_path, output_dir / "data" / "custom.run.json")
            self.assertEqual(paths.trace_path, output_dir / "trace.json")

    def test_existing_symlink_escape_under_output_dir_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "experiments"
            outside_dir = tmp_path / "outside"
            output_dir.mkdir()
            outside_dir.mkdir()
            link = output_dir / "link"
            try:
                link.symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            with self.assertRaisesRegex(RunOutputPathError, "must stay within"):
                resolve_run_output_paths(
                    run_output="link/run.json",
                    trace_output="trace.json",
                    output_dir=str(output_dir),
                )

    def test_output_dir_may_itself_be_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            real_dir = tmp_path / "real-output"
            real_dir.mkdir()
            output_dir = tmp_path / "output-link"
            try:
                output_dir.symlink_to(real_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            paths = resolve_run_output_paths(
                run_output=None,
                trace_output=None,
                output_dir=str(output_dir),
            )

            self.assertEqual(paths.run_path, output_dir / "run.json")
            self.assertEqual(paths.trace_path, output_dir / "trace.json")

    def test_rejects_identical_outputs(self) -> None:
        with self.assertRaisesRegex(RunOutputPathError, "must be different"):
            resolve_run_output_paths(
                run_output="result.json",
                trace_output="result.json",
                output_dir="experiments/demo",
            )

    def test_rejects_identical_outputs_after_normalization(self) -> None:
        with self.assertRaisesRegex(RunOutputPathError, "must be different"):
            resolve_run_output_paths(
                run_output="./data/../result.json",
                trace_output="result.json",
                output_dir="experiments/demo",
            )

    def test_prepare_creates_output_dir_and_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments" / "demo"
            paths = resolve_run_output_paths(
                run_output="data/custom.run.json",
                trace_output="trace/custom.trace.json",
                output_dir=str(root),
            )

            prepare_run_output_paths(paths)

            self.assertTrue(root.is_dir())
            self.assertTrue((root / "data").is_dir())
            self.assertTrue((root / "trace").is_dir())

    def test_prepare_rejects_existing_file_as_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            output_dir.write_text("not a directory", encoding="utf-8")
            paths = resolve_run_output_paths(
                run_output=None,
                trace_output=None,
                output_dir=str(output_dir),
            )

            with self.assertRaisesRegex(RunOutputPathError, "not a directory"):
                prepare_run_output_paths(paths)


if __name__ == "__main__":
    unittest.main()
