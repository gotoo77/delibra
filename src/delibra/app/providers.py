from __future__ import annotations

from delibra.app.models import ProviderConfig, ProviderId
from delibra.runtime import (
    IdSequence,
    LLMClient,
    MockLLMClient,
    OllamaClient,
    OpenAIClient,
)


def build_llm_client(provider: ProviderId | ProviderConfig) -> LLMClient:
    provider_id = provider.id if isinstance(provider, ProviderConfig) else provider
    if provider_id == "mock":
        return MockLLMClient(IdSequence("msg_response"))
    if provider_id == "openai":
        return OpenAIClient.from_env(response_message_ids=IdSequence("msg_response"))
    if provider_id == "ollama":
        return OllamaClient.from_env(response_message_ids=IdSequence("msg_response"))
    raise ValueError(f"unsupported provider: {provider_id}")
