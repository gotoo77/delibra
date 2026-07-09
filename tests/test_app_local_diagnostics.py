from __future__ import annotations

import unittest

from delibra.app.local_diagnostics import (
    LocalProviderProbe,
    diagnose_local_providers,
    http_get_json,
)


class AppLocalDiagnosticsTests(unittest.TestCase):
    def test_ollama_probe_lists_models_from_api_tags(self) -> None:
        diagnostics = diagnose_local_providers(
            probes=(
                LocalProviderProbe(
                    provider_id="ollama",
                    label="Ollama",
                    kind="ollama",
                    base_urls=("http://local-ollama",),
                ),
            ),
            transport=lambda url, _timeout: {
                "models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]
            },
        )

        status = diagnostics.statuses[0]
        self.assertEqual(status.provider_id, "ollama")
        self.assertEqual(status.base_url, "http://local-ollama")
        self.assertTrue(status.reachable)
        self.assertEqual(status.models, ("llama3.1:8b", "qwen2.5:7b"))
        self.assertIsNone(status.error)
        self.assertIsNone(status.recovery_hint)

    def test_openai_compatible_probe_lists_models_from_v1_models(self) -> None:
        seen_urls: list[str] = []

        def transport(url: str, _timeout: float):
            seen_urls.append(url)
            return {"data": [{"id": "local-model-a"}, {"id": "local-model-b"}]}

        diagnostics = diagnose_local_providers(
            probes=(
                LocalProviderProbe(
                    provider_id="openai-compatible",
                    label="OpenAI-compatible local endpoint",
                    kind="openai-compatible",
                    base_urls=("http://localhost:1234/v1",),
                ),
            ),
            transport=transport,
        )

        status = diagnostics.statuses[0]
        self.assertEqual(seen_urls, ["http://localhost:1234/v1/models"])
        self.assertTrue(status.reachable)
        self.assertEqual(status.models, ("local-model-a", "local-model-b"))

    def test_unreachable_probe_returns_recovery_hint_without_raising(self) -> None:
        diagnostics = diagnose_local_providers(
            probes=(
                LocalProviderProbe(
                    provider_id="ollama",
                    label="Ollama",
                    kind="ollama",
                    base_urls=("http://localhost:11434",),
                ),
            ),
            transport=lambda _url, _timeout: (_ for _ in ()).throw(
                ConnectionError("connection refused")
            ),
        )

        status = diagnostics.statuses[0]
        self.assertFalse(status.reachable)
        self.assertEqual(status.models, ())
        self.assertEqual(status.error, "connection refused")
        self.assertIn("Start Ollama", status.recovery_hint or "")

    def test_reachable_provider_without_models_returns_recovery_hint(self) -> None:
        diagnostics = diagnose_local_providers(
            probes=(
                LocalProviderProbe(
                    provider_id="ollama",
                    label="Ollama",
                    kind="ollama",
                    base_urls=("http://localhost:11434",),
                ),
            ),
            transport=lambda _url, _timeout: {"models": []},
        )

        status = diagnostics.statuses[0]
        self.assertTrue(status.reachable)
        self.assertEqual(status.models, ())
        self.assertIsNone(status.error)
        self.assertIn("no models", status.recovery_hint or "")

    def test_incompatible_response_returns_diagnostic_not_exception(self) -> None:
        diagnostics = diagnose_local_providers(
            probes=(
                LocalProviderProbe(
                    provider_id="openai-compatible",
                    label="OpenAI-compatible local endpoint",
                    kind="openai-compatible",
                    base_urls=("http://localhost:1234/v1",),
                ),
            ),
            transport=lambda _url, _timeout: {"models": []},
        )

        status = diagnostics.statuses[0]
        self.assertFalse(status.reachable)
        self.assertIn("missing data array", status.error or "")
        self.assertIn("expected model listing API", status.recovery_hint or "")

    def test_http_get_json_rejects_non_json_object(self) -> None:
        with self.assertRaises(ConnectionError):
            http_get_json("http://127.0.0.1:1/v1/models", 0.001)


if __name__ == "__main__":
    unittest.main()
