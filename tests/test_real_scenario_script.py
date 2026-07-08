from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_real_code_review.sh"


class RealScenarioScriptTests(unittest.TestCase):
    def test_script_exists_and_is_executable(self) -> None:
        self.assertTrue(SCRIPT.exists())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_script_runs_with_mock_provider_against_current_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            output = Path(tmp) / "output"
            repo.mkdir()

            subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            (repo / "example.txt").write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "add", "example.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (repo / "example.txt").write_text("first\nsecond\n", encoding="utf-8")
            subprocess.run(["git", "add", "example.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "Update"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            env = os.environ.copy()
            env["PROVIDER"] = "mock"
            env["DELIBRA_OUTPUT_DIR"] = str(output)
            env["DELIBRA_GIT_ROOT"] = str(repo)
            env["DELIBRA_BIN"] = f"{sys.executable} -m delibra"
            env["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [str(SCRIPT)],
                cwd=ROOT,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Delibra real code review scenario complete.", result.stdout)
            self.assertTrue((output / "input.patch").exists())
            self.assertTrue((output / "run.json").exists())
            self.assertTrue((output / "trace.json").exists())
            self.assertTrue((output / "inspect.txt").exists())

    def test_openai_provider_requires_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PROVIDER"] = "openai"
            env["DELIBRA_OUTPUT_DIR"] = str(Path(tmp) / "output")
            env.pop("OPENAI_API_KEY", None)
            env.pop("OPENAI_MODEL", None)

            result = subprocess.run(
                [str(SCRIPT)],
                cwd=ROOT,
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OPENAI_API_KEY is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
