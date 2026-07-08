from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from delibra.core.json import JsonMutableObject
from delibra.runtime.builders import IdSequence
from delibra.runtime.llm import LLMRequest, LLMResponse, Message


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OPENAI_TIMEOUT_SECONDS_ENV = "OPENAI_TIMEOUT_SECONDS"
OPENAI_MAX_OUTPUT_TOKENS_ENV = "OPENAI_MAX_OUTPUT_TOKENS"
DELIBRA_DEBUG_PROVIDER_ENV = "DELIBRA_DEBUG_PROVIDER"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 120.0
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 800


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str = DEFAULT_OPENAI_BASE_URL
    timeout_seconds: float = DEFAULT_OPENAI_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
    debug_provider: bool = False


@dataclass(frozen=True)
class OpenAIConfigError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class OpenAIProviderError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


OpenAITransport = Callable[[OpenAIConfig, JsonMutableObject], JsonMutableObject]


@dataclass
class OpenAIClient:
    config: OpenAIConfig
    response_message_ids: IdSequence
    transport: OpenAITransport | None = None

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = _post_response

    @classmethod
    def from_env(
        cls,
        *,
        response_message_ids: IdSequence,
        env: Mapping[str, str] | None = None,
        transport: OpenAITransport | None = None,
    ) -> "OpenAIClient":
        env = os.environ if env is None else env
        api_key = env.get(OPENAI_API_KEY_ENV, "")
        model = env.get(OPENAI_MODEL_ENV, "")
        base_url = env.get(OPENAI_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL)
        timeout_seconds = _timeout_from_env(env)
        max_output_tokens = _max_output_tokens_from_env(env)
        debug_provider = _debug_provider_from_env(env)
        if api_key == "":
            raise OpenAIConfigError(f"{OPENAI_API_KEY_ENV} is required for OpenAI provider")
        if model == "":
            raise OpenAIConfigError(f"{OPENAI_MODEL_ENV} is required for OpenAI provider")
        return cls(
            config=OpenAIConfig(
                api_key=api_key,
                model=model,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                max_output_tokens=max_output_tokens,
                debug_provider=debug_provider,
            ),
            response_message_ids=response_message_ids,
            transport=_post_response if transport is None else transport,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        input_text = _render_input(request)
        payload = {
            "model": self.config.model,
            "input": input_text,
            "max_output_tokens": self.config.max_output_tokens,
        }
        _debug_provider_request(self.config, input_text)
        response = self.transport(
            self.config,
            payload,
        )
        content = _extract_text(response, self.config)
        return LLMResponse(
            message=Message(
                id=self.response_message_ids.next(),
                role="assistant",
                content=content,
            ),
            payload={"content": content},
            metadata={},
        )


def _render_input(request: LLMRequest) -> str:
    return "\n\n".join(
        (
            request.message.content,
            "Resolved inputs:",
            json.dumps(request.inputs, indent=2, sort_keys=True),
        )
    )


def _timeout_from_env(env: Mapping[str, str]) -> float:
    raw_value = env.get(OPENAI_TIMEOUT_SECONDS_ENV, "")
    if raw_value == "":
        return DEFAULT_OPENAI_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(raw_value)
    except ValueError as exc:
        raise OpenAIConfigError(
            f"{OPENAI_TIMEOUT_SECONDS_ENV} must be a positive number"
        ) from exc
    if timeout_seconds <= 0:
        raise OpenAIConfigError(f"{OPENAI_TIMEOUT_SECONDS_ENV} must be a positive number")
    return timeout_seconds


def _max_output_tokens_from_env(env: Mapping[str, str]) -> int:
    raw_value = env.get(OPENAI_MAX_OUTPUT_TOKENS_ENV, "")
    if raw_value == "":
        return DEFAULT_OPENAI_MAX_OUTPUT_TOKENS
    try:
        max_output_tokens = int(raw_value)
    except ValueError as exc:
        raise OpenAIConfigError(
            f"{OPENAI_MAX_OUTPUT_TOKENS_ENV} must be a positive integer"
        ) from exc
    if max_output_tokens <= 0:
        raise OpenAIConfigError(
            f"{OPENAI_MAX_OUTPUT_TOKENS_ENV} must be a positive integer"
        )
    return max_output_tokens


def _debug_provider_from_env(env: Mapping[str, str]) -> bool:
    return env.get(DELIBRA_DEBUG_PROVIDER_ENV, "") == "1"


def _debug_provider_request(config: OpenAIConfig, input_text: str) -> None:
    if not config.debug_provider:
        return
    print(
        "delibra.openai:"
        f" model={config.model}"
        f" timeout_seconds={config.timeout_seconds:g}"
        f" max_output_tokens={config.max_output_tokens}"
        f" input_chars={len(input_text)}",
        file=sys.stderr,
        flush=True,
    )


def _post_response(config: OpenAIConfig, payload: JsonMutableObject) -> JsonMutableObject:
    url = config.base_url.rstrip("/") + "/responses"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OpenAIProviderError(f"OpenAI request failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OpenAIProviderError(f"OpenAI request failed: {exc.reason}") from exc
    except OSError as exc:
        raise OpenAIProviderError(f"OpenAI request failed: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OpenAIProviderError("OpenAI response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OpenAIProviderError("OpenAI response must be a JSON object")
    return parsed


def _extract_text(response: JsonMutableObject, config: OpenAIConfig | None = None) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text != "":
        return output_text

    output = response.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            text = _content_text(content)
            if text is not None:
                parts.append(text)
                continue
            if not isinstance(content, list):
                continue
            for content_item in content:
                text = _content_text(content_item)
                if text is not None:
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    diagnostics = _response_diagnostics(response)
    if config is not None and config.debug_provider:
        print(f"delibra.openai: no text output; {diagnostics}", file=sys.stderr, flush=True)
    raise OpenAIProviderError(f"OpenAI response did not contain text output ({diagnostics})")


def _content_text(content_item: Any) -> str | None:
    if isinstance(content_item, str) and content_item != "":
        return content_item
    if not isinstance(content_item, dict):
        return None
    text = content_item.get("text")
    if isinstance(text, str):
        return text
    output_text = content_item.get("output_text")
    if isinstance(output_text, str):
        return output_text
    return None


def _response_diagnostics(response: JsonMutableObject) -> str:
    parts: list[str] = []
    status = response.get("status")
    if isinstance(status, str):
        parts.append(f"status={status}")

    error = response.get("error")
    if isinstance(error, dict):
        error_type = error.get("type")
        error_code = error.get("code")
        if isinstance(error_type, str):
            parts.append(f"error_type={error_type}")
        if isinstance(error_code, str):
            parts.append(f"error_code={error_code}")
    elif isinstance(error, str):
        parts.append("error=present")

    incomplete_details = response.get("incomplete_details")
    if isinstance(incomplete_details, dict):
        reason = incomplete_details.get("reason")
        if isinstance(reason, str):
            parts.append(f"incomplete_reason={reason}")
    elif isinstance(incomplete_details, str):
        parts.append(f"incomplete_details={incomplete_details}")

    output = response.get("output")
    if isinstance(output, list):
        output_types: list[str] = []
        content_types: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                output_types.append(type(item).__name__)
                continue
            item_type = item.get("type")
            output_types.append(item_type if isinstance(item_type, str) else "unknown")
            content = item.get("content")
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict):
                        content_type = content_item.get("type")
                        content_types.append(
                            content_type if isinstance(content_type, str) else "unknown"
                        )
                    else:
                        content_types.append(type(content_item).__name__)
            elif content is not None:
                content_types.append(type(content).__name__)
        parts.append(f"output_types={','.join(output_types) if output_types else 'none'}")
        if content_types:
            parts.append(f"content_types={','.join(content_types)}")
    else:
        parts.append("output=missing")

    return "; ".join(parts) if parts else "no diagnostics"
