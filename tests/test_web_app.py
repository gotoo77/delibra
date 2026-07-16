from __future__ import annotations

import json
import re
import tempfile
import time
import unittest
import asyncio
from importlib.resources import files
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from delibra.web.app import DEFAULT_HOST, create_app
from delibra.web.execution_manager import ExecutionLimitError, ExecutionManager
from delibra.web.paths import resolve_web_output_paths
from delibra.app.inputs import input_from_text
from delibra.app.local_diagnostics import LocalDiagnostics, LocalProviderStatus
from delibra.app.local_runtime import LocalRuntimeAssessment
from delibra.app.models import ProviderConfig
from delibra.app.presets import load_preset
from delibra.app.run import RunProtocolApplicationRequest
from tests.test_inspect import create_run_and_trace


CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


class WebAppTests(unittest.TestCase):
    def test_package_data_is_loadable_independent_of_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                self.assertTrue(files("delibra.web").joinpath("templates/base.html").is_file())
                self.assertTrue(files("delibra.web").joinpath("static/style.css").is_file())
            finally:
                os.chdir(old_cwd)

    def test_default_host_is_localhost(self) -> None:
        self.assertEqual(DEFAULT_HOST, "127.0.0.1")

    def test_new_run_page_renders_provider_diagnostics_and_protocol_preview(self) -> None:
        diagnostics = LocalDiagnostics(
            statuses=(
                LocalProviderStatus(
                    provider_id="ollama",
                    label="Ollama",
                    kind="ollama",
                    base_url="http://localhost:11434",
                    reachable=True,
                    models=("mistral:latest", "qwen3:4b"),
                    error=None,
                    recovery_hint=None,
                ),
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            with mock.patch(
                "delibra.web.app.assess_local_runtime",
                return_value=LocalRuntimeAssessment(diagnostics=diagnostics),
            ):
                with mock.patch(
                    "delibra.app.run_config.list_openai_models",
                    return_value=("gpt-5", "gpt-5-mini"),
                ):
                    with mock.patch.dict(
                        "os.environ",
                        {"OPENAI_API_KEY": "secret-value-12345"},
                        clear=True,
                    ):
                        response = client.get("/runs/new")

        self.assertEqual(response.status_code, 200)
        self.assertIn("OpenAI - configured", response.text)
        self.assertNotIn("secret-value-12345", response.text)
        self.assertIn("OpenAI models detected: gpt-5, gpt-5-mini", response.text)
        self.assertIn('<option value="gpt-5"></option>', response.text)
        self.assertIn("Ollama models detected: mistral:latest, qwen3:4b", response.text)
        self.assertIn('<option value="qwen3:4b"></option>', response.text)
        self.assertIn('data-model-list="models-openai"', response.text)
        self.assertIn('data-model-list="models-ollama"', response.text)
        self.assertIn('data-provider-select', response.text)
        self.assertIn('data-model-required="false"', response.text)
        self.assertIn('data-model-required="true"', response.text)
        self.assertIn('data-model-field', response.text)
        self.assertIn("Preset details", response.text)
        self.assertNotIn("Protocol preview", response.text)
        self.assertIn("role_reviews", response.text)
        self.assertIn("final_synthesis", response.text)
        self.assertIn("new_run.js", response.text)

    def test_creates_mock_run_from_post_and_discovers_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            client = TestClient(create_app(experiments_root=root))

            response = self._post_run(
                client,
                {
                    "preset": "code_review",
                    "provider": "mock",
                    "input_text": "Review this change.",
                    "output_dir": "web/mock",
                    "show_progress": "on",
                },
            )

            self.assertEqual(response.status_code, 303)
            execution_url = response.headers["location"]
            self._wait_for_execution(client.app.state.manager, execution_url)
            self.assertTrue((root / "web" / "mock" / "run.json").exists())
            self.assertTrue((root / "web" / "mock" / "trace.json").exists())

            restarted = TestClient(create_app(experiments_root=root))
            runs = restarted.get("/runs")
            self.assertEqual(runs.status_code, 200)
            self.assertIn("web/mock", runs.text)
            detail = restarted.get("/runs/web/mock")
            self.assertEqual(detail.status_code, 200)
            self.assertIn("code_review@0.1.0", detail.text)
            self.assertIn("Raw payload JSON", detail.text)

    def test_payload_content_is_rendered_as_readable_text_before_raw_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            directory = root / "readable"
            directory.mkdir(parents=True)
            run_path, _ = create_run_and_trace(directory)
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["artifacts"][0]["payload"] = {
                "content": "Readable first line\nReadable second line",
                "confidence": 0.82,
                "notes": {"source": "test"},
            }
            run_path.write_text(json.dumps(run), encoding="utf-8")

            client = TestClient(create_app(experiments_root=root))
            response = client.get("/runs/readable")

            self.assertEqual(response.status_code, 200)
            artifact_index = response.text.index("artifact_0001")
            readable_index = response.text.index("Readable first line", artifact_index)
            raw_index = response.text.index("Raw payload JSON", artifact_index)
            self.assertLess(readable_index, raw_index)
            self.assertIn("<dt>confidence</dt>", response.text)
            self.assertIn("0.82", response.text)
            self.assertIn("<dt>notes</dt>", response.text)

    def test_invalid_csrf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            client.get("/runs/new")
            response = client.post(
                "/runs",
                data={
                    "csrf_token": "bad",
                    "preset": "code_review",
                    "provider": "mock",
                    "input_text": "Review this change.",
                    "output_dir": "csrf",
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("invalid CSRF token", response.text)

    def test_invalid_origin_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            token = self._csrf_token(client)
            response = client.post(
                "/runs",
                headers={"Origin": "https://example.invalid"},
                data={
                    "csrf_token": token,
                    "preset": "code_review",
                    "provider": "mock",
                    "input_text": "Review this change.",
                    "output_dir": "origin",
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("request origin is not allowed", response.text)

    def test_input_too_large_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            token = self._csrf_token(client)
            response = client.post(
                "/runs",
                data={
                    "csrf_token": token,
                    "preset": "code_review",
                    "provider": "mock",
                    "input_text": "x" * 130_000,
                    "output_dir": "large",
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("form submission is too large", response.text)

    def test_path_validation_happens_before_provider_construction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            token = self._csrf_token(client)
            response = client.post(
                "/runs",
                data={
                    "csrf_token": token,
                    "preset": "code_review",
                    "provider": "openai",
                    "model": "gpt-test",
                    "input_text": "Review this change.",
                    "output_dir": "../outside",
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn("stay within experiments root", response.text)
            self.assertNotIn("OPENAI_API_KEY", response.text)

    def test_provider_failure_is_recorded_without_traceback_or_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            client = TestClient(create_app(experiments_root=root))
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "secret-value-12345"}, clear=True):
                with mock.patch(
                    "delibra.web.execution_manager.run_protocol_application",
                    side_effect=RuntimeError("provider failed with secret-value-12345"),
                ):
                    response = self._post_run(
                        client,
                        {
                            "preset": "code_review",
                            "provider": "openai",
                            "model": "gpt-test",
                            "input_text": "Review this change.",
                            "output_dir": "provider/fail",
                        },
                    )

                    self.assertEqual(response.status_code, 303)
                    execution = self._wait_for_execution(
                        client.app.state.manager,
                        response.headers["location"],
                    )

            self.assertEqual(execution.status, "failed")
            self.assertNotIn("Traceback", execution.error or "")
            self.assertNotIn("secret-value-12345", execution.error or "")
            self.assertIn("[redacted]", execution.error or "")

    def test_provider_errors_from_real_builder_are_deferred_to_background_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            client = TestClient(create_app(experiments_root=root))
            with mock.patch.dict("os.environ", {}, clear=True):
                response = self._post_run(
                    client,
                    {
                        "preset": "code_review",
                        "provider": "openai",
                        "model": "gpt-test",
                        "input_text": "Review this change.",
                        "output_dir": "provider/fail",
                    },
                )

                self.assertEqual(response.status_code, 303)
                execution = self._wait_for_execution(
                    client.app.state.manager,
                    response.headers["location"],
                )

            self.assertEqual(execution.status, "failed")
            self.assertIn("OPENAI_API_KEY", execution.error or "")

    def test_execution_manager_rejects_second_active_run_and_releases_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            manager = ExecutionManager(max_active=1)

            def slow_failure(_request):
                time.sleep(0.2)
                raise RuntimeError("boom")

            with mock.patch("delibra.web.execution_manager.run_protocol_application", slow_failure):
                asyncio.run(self._exercise_execution_limit(manager, root))

    async def _exercise_execution_limit(self, manager: ExecutionManager, root: Path) -> None:
        first = manager.start(self._run_request(root, "active/one"))
        with self.assertRaises(ExecutionLimitError):
            manager.start(self._run_request(root, "active/two"))

        deadline = time.time() + 5
        while time.time() < deadline:
            execution = manager.snapshot(first.id)
            if execution is not None and execution.status == "failed":
                break
            await asyncio.sleep(0.05)
        else:
            raise AssertionError("first execution did not fail")

        third = manager.start(self._run_request(root, "active/three"))
        self.assertIsNotNone(third.id)

    def test_show_progress_false_still_allows_status_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(create_app(experiments_root=Path(tmp) / "experiments"))
            response = self._post_run(
                client,
                {
                    "preset": "code_review",
                    "provider": "mock",
                    "input_text": "Review this change.",
                    "output_dir": "no-progress",
                },
            )

            execution = self._wait_for_execution(client.app.state.manager, response.headers["location"])
            self.assertEqual(execution.status, "completed")
            self.assertFalse(execution.show_progress)
            self.assertEqual(execution.progress, [])

    def test_payload_xss_is_escaped_as_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiments"
            directory = root / "xss"
            directory.mkdir(parents=True)
            run_path, _ = create_run_and_trace(directory)
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["artifacts"][0]["payload"] = {
                "content": (
                    "<script>alert(1)</script>\n"
                    "<img src=x onerror=alert(1)>\n"
                    "{{ expression }}\n"
                    "**bold <script>alert(2)</script>**\n"
                    "javascript:alert(3)"
                )
            }
            run_path.write_text(json.dumps(run), encoding="utf-8")

            client = TestClient(create_app(experiments_root=root))
            response = client.get("/runs/xss")

            self.assertEqual(response.status_code, 200)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;", response.text)
            self.assertIn("{{ expression }}", response.text)
            self.assertIn("javascript:alert(3)", response.text)
            self.assertNotIn("<script>alert(1)</script>", response.text)
            self.assertNotIn("<img src=x onerror=alert(1)>", response.text)
            self.assertIn("Raw payload JSON", response.text)

    def _csrf_token(self, client: TestClient) -> str:
        response = client.get("/runs/new")
        self.assertEqual(response.status_code, 200)
        match = CSRF_RE.search(response.text)
        self.assertIsNotNone(match)
        return match.group(1)

    def _post_run(self, client: TestClient, data: dict[str, str]) -> object:
        token = self._csrf_token(client)
        return client.post(
            "/runs",
            data={"csrf_token": token, **data},
            follow_redirects=False,
        )

    def _wait_for_execution(self, manager, location: str):
        execution_id = location.rstrip("/").split("/")[-1]
        deadline = time.time() + 5
        while time.time() < deadline:
            execution = manager.snapshot(execution_id)
            if execution is not None and execution.status in {"completed", "failed"}:
                return execution
            time.sleep(0.05)
        raise AssertionError("execution did not finish")

    def _run_request(self, root: Path, output_dir: str) -> RunProtocolApplicationRequest:
        return RunProtocolApplicationRequest(
            protocol=load_preset("code_review"),
            input_ref=input_from_text("Review this change."),
            provider=ProviderConfig("mock"),
            output_paths=resolve_web_output_paths(root, output_dir),
        )


if __name__ == "__main__":
    unittest.main()
