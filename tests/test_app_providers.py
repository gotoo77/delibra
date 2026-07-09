from __future__ import annotations

import os
import unittest
from unittest import mock

from delibra.app.models import ProviderConfig
from delibra.app.providers import build_llm_client
from delibra.runtime import (
    MockLLMClient,
    OllamaConfigError,
    OpenAIConfigError,
)


class AppProviderTests(unittest.TestCase):
    def test_builds_mock_client_from_provider_id(self) -> None:
        client = build_llm_client("mock")

        self.assertIsInstance(client, MockLLMClient)

    def test_builds_mock_client_from_provider_config(self) -> None:
        client = build_llm_client(ProviderConfig("mock"))

        self.assertIsInstance(client, MockLLMClient)

    def test_openai_missing_config_error_stays_provider_specific(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(OpenAIConfigError, "OPENAI_API_KEY"):
                build_llm_client("openai")

    def test_ollama_missing_config_error_stays_provider_specific(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(OllamaConfigError, "OLLAMA_MODEL"):
                build_llm_client("ollama")

    def test_unsupported_provider_fails_cleanly(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported provider: other"):
            build_llm_client("other")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
