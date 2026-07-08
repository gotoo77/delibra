from __future__ import annotations

import json
import os
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
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str = DEFAULT_OPENAI_BASE_URL


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
        if api_key == "":
            raise OpenAIConfigError(f"{OPENAI_API_KEY_ENV} is required for OpenAI provider")
        if model == "":
            raise OpenAIConfigError(f"{OPENAI_MODEL_ENV} is required for OpenAI provider")
        return cls(
            config=OpenAIConfig(api_key=api_key, model=model, base_url=base_url),
            response_message_ids=response_message_ids,
            transport=_post_response if transport is None else transport,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = self.transport(
            self.config,
            {
                "model": self.config.model,
                "input": _render_input(request),
            },
        )
        content = _extract_text(response)
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
        with urllib.request.urlopen(request, timeout=60) as response:
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


def _extract_text(response: JsonMutableObject) -> str:
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
            if not isinstance(content, list):
                continue
            for content_item in content:
                text = _content_text(content_item)
                if text is not None:
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    raise OpenAIProviderError("OpenAI response did not contain text output")


def _content_text(content_item: Any) -> str | None:
    if not isinstance(content_item, dict):
        return None
    text = content_item.get("text")
    if isinstance(text, str):
        return text
    return None
