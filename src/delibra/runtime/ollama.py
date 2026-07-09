from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from delibra.core.json import JsonMutableObject
from delibra.runtime.builders import IdSequence
from delibra.runtime.llm import LLMRequest, LLMResponse, Message


OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"
OLLAMA_TIMEOUT_SECONDS_ENV = "OLLAMA_TIMEOUT_SECONDS"
OLLAMA_MAX_OUTPUT_TOKENS_ENV = "OLLAMA_MAX_OUTPUT_TOKENS"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class OllamaConfig:
    model: str
    base_url: str = DEFAULT_OLLAMA_BASE_URL
    timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class OllamaConfigError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class OllamaProviderError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


OllamaTransport = Callable[[OllamaConfig, JsonMutableObject], JsonMutableObject]


@dataclass
class OllamaClient:
    config: OllamaConfig
    response_message_ids: IdSequence
    transport: OllamaTransport | None = None

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = _post_generate

    @classmethod
    def from_env(
        cls,
        *,
        response_message_ids: IdSequence,
        env: Mapping[str, str] | None = None,
        transport: OllamaTransport | None = None,
    ) -> "OllamaClient":
        env = os.environ if env is None else env
        model = env.get(OLLAMA_MODEL_ENV, "")
        base_url = env.get(OLLAMA_BASE_URL_ENV, DEFAULT_OLLAMA_BASE_URL)
        timeout_seconds = _timeout_from_env(env)
        max_output_tokens = _max_output_tokens_from_env(env)
        if model == "":
            raise OllamaConfigError(f"{OLLAMA_MODEL_ENV} is required for Ollama provider")
        return cls(
            config=OllamaConfig(
                model=model,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
            ),
            response_message_ids=response_message_ids,
            transport=_post_generate if transport is None else transport,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload: JsonMutableObject = {
            "model": self.config.model,
            "prompt": _render_prompt(request),
            "stream": False,
        }
        if self.config.max_output_tokens is not None:
            payload["options"] = {"num_predict": self.config.max_output_tokens}
        response = self.transport(self.config, payload)
        content = _extract_response_text(response)
        return LLMResponse(
            message=Message(
                id=self.response_message_ids.next(),
                role="assistant",
                content=content,
            ),
            payload={"content": content},
            metadata={},
        )


def _render_prompt(request: LLMRequest) -> str:
    return "\n\n".join(
        (
            request.message.content,
            "Resolved inputs:",
            json.dumps(request.inputs, indent=2, sort_keys=True),
        )
    )


def _timeout_from_env(env: Mapping[str, str]) -> float:
    raw_value = env.get(OLLAMA_TIMEOUT_SECONDS_ENV, "")
    if raw_value == "":
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(raw_value)
    except ValueError as exc:
        raise OllamaConfigError(
            f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be a positive number"
        ) from exc
    if timeout_seconds <= 0:
        raise OllamaConfigError(f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be a positive number")
    return timeout_seconds


def _max_output_tokens_from_env(env: Mapping[str, str]) -> int | None:
    raw_value = env.get(OLLAMA_MAX_OUTPUT_TOKENS_ENV, "")
    if raw_value == "":
        return None
    try:
        max_output_tokens = int(raw_value)
    except ValueError as exc:
        raise OllamaConfigError(
            f"{OLLAMA_MAX_OUTPUT_TOKENS_ENV} must be a positive integer"
        ) from exc
    if max_output_tokens <= 0:
        raise OllamaConfigError(
            f"{OLLAMA_MAX_OUTPUT_TOKENS_ENV} must be a positive integer"
        )
    return max_output_tokens


def _post_generate(config: OllamaConfig, payload: JsonMutableObject) -> JsonMutableObject:
    url = config.base_url.rstrip("/") + "/api/generate"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaProviderError(
            f"Ollama request failed: HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OllamaProviderError(
            f"Ollama request failed: {exc.reason}. Is Ollama running at {config.base_url}?"
        ) from exc
    except OSError as exc:
        raise OllamaProviderError(
            f"Ollama request failed: {exc}. Is Ollama running at {config.base_url}?"
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaProviderError("Ollama response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OllamaProviderError("Ollama response must be a JSON object")
    return parsed


def _extract_response_text(response: JsonMutableObject) -> str:
    error = response.get("error")
    if isinstance(error, str) and error != "":
        raise OllamaProviderError(f"Ollama returned error: {error}")
    text = response.get("response")
    if isinstance(text, str) and text != "":
        return text
    raise OllamaProviderError("Ollama response did not contain non-empty response text")
