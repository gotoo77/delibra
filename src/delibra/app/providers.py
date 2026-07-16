from __future__ import annotations

import os

from delibra.app.models import ProviderConfig, ProviderId
from delibra.runtime import (
    IdSequence,
    LLMClient,
    MockLLMClient,
    OllamaClient,
    OpenAIClient,
)
from delibra.runtime.ollama import OLLAMA_BASE_URL_ENV, OLLAMA_MODEL_ENV
from delibra.runtime.openai import OPENAI_BASE_URL_ENV, OPENAI_MODEL_ENV


def build_llm_client(provider: ProviderId | ProviderConfig) -> LLMClient:
    config = provider if isinstance(provider, ProviderConfig) else ProviderConfig(provider)
    provider_id = config.id
    if provider_id == "mock":
        return MockLLMClient(IdSequence("msg_response"))
    if provider_id == "openai":
        return OpenAIClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env=_provider_env(
                model_env=OPENAI_MODEL_ENV,
                base_url_env=OPENAI_BASE_URL_ENV,
                config=config,
            ),
        )
    if provider_id == "ollama":
        return OllamaClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env=_provider_env(
                model_env=OLLAMA_MODEL_ENV,
                base_url_env=OLLAMA_BASE_URL_ENV,
                config=config,
            ),
        )
    raise ValueError(f"unsupported provider: {provider_id}")


def _provider_env(
    *,
    model_env: str,
    base_url_env: str,
    config: ProviderConfig,
) -> dict[str, str]:
    env = dict(os.environ)
    if config.model is not None:
        env[model_env] = config.model
    if config.base_url is not None:
        env[base_url_env] = config.base_url
    return env
