from __future__ import annotations

import io
import urllib.error
import unittest
from pathlib import Path
from unittest import mock

from delibra.app.local_diagnostics import LocalDiagnostics, LocalProviderStatus
from delibra.app.presets import PresetInfo
from delibra.app.run_config import describe_preset, describe_provider_options, list_openai_models


class AppRunConfigTests(unittest.TestCase):
    def test_provider_options_use_passive_diagnostics_and_do_not_expose_secrets(self) -> None:
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

        options = describe_provider_options(
            diagnostics,
            env={
                "OPENAI_API_KEY": "secret-value",
                "OPENAI_MODEL": "gpt-test",
            },
            openai_model_transport=lambda _base_url, _api_key, _timeout: (
                "gpt-5",
                "gpt-5-mini",
            ),
        )

        by_id = {option.id: option for option in options}
        self.assertEqual(by_id["mock"].status, "ready")
        self.assertEqual(by_id["openai"].status, "configured")
        self.assertIn("API credentials", by_id["openai"].detail)
        self.assertNotIn("secret-value", by_id["openai"].detail)
        self.assertEqual(by_id["openai"].models, ("gpt-5", "gpt-5-mini"))
        self.assertTrue(by_id["openai"].model_required)
        self.assertEqual(by_id["ollama"].status, "reachable")
        self.assertEqual(by_id["ollama"].models, ("mistral:latest", "qwen3:4b"))

    def test_openai_model_discovery_closes_http_error_response(self) -> None:
        body = io.BytesIO(b'{"error":"unauthorized"}')
        error = urllib.error.HTTPError(
            url="https://api.openai.test/models",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=body,
        )

        with mock.patch("urllib.request.urlopen", side_effect=error):
            models = list_openai_models("https://api.openai.test", "bad-key", 0.1)

        self.assertEqual(models, ())
        self.assertTrue(body.closed)

    def test_preset_detail_summarizes_protocol_structure(self) -> None:
        detail = describe_preset(
            PresetInfo(
                name="code_review",
                protocol_id="code_review",
                version="0.1.0",
                description="",
                path=Path("presets/code_review.yaml"),
            )
        )

        steps = {step.id: step for step in detail.steps}
        self.assertEqual(detail.protocol_id, "code_review")
        self.assertEqual(detail.source_path, "presets/code_review.yaml")
        self.assertIn("id: code_review", detail.source_yaml)
        self.assertIn("Structured code review protocol.", detail.source_yaml)
        self.assertIn("security", detail.roles)
        self.assertEqual(steps["role_reviews"].kind, "fanout")
        self.assertEqual(steps["role_reviews"].roles, ("maintainer", "tester", "security"))
        self.assertEqual(steps["final"].output, "final_synthesis")


if __name__ == "__main__":
    unittest.main()
