from __future__ import annotations

import os
import json
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from delibra.app.local_diagnostics import LocalDiagnostics
from delibra.app.models import ProviderId
from delibra.app.presets import PresetInfo, load_preset
from delibra.core import Protocol, StepDefinition
from delibra.runtime.openai import (
    DEFAULT_OPENAI_BASE_URL,
    OPENAI_API_KEY_ENV,
    OPENAI_BASE_URL_ENV,
    OPENAI_MODEL_ENV,
)


SUPPORTED_PROVIDER_IDS: tuple[ProviderId, ...] = ("mock", "openai", "ollama")
OPENAI_MODEL_DISCOVERY_TIMEOUT_SECONDS = 2.0
OpenAIModelTransport = Callable[[str, str, float], tuple[str, ...]]


@dataclass(frozen=True)
class ProviderOption:
    id: ProviderId
    label: str
    status: str
    detail: str
    models: tuple[str, ...] = ()
    model_required: bool = False
    model_placeholder: str = ""
    model_help: str = ""


@dataclass(frozen=True)
class ProtocolStepSummary:
    id: str
    kind: str
    roles: tuple[str, ...]
    inputs: tuple[str, ...]
    output: str
    output_kind: str
    instruction_preview: str


@dataclass(frozen=True)
class PresetDetail:
    name: str
    protocol_id: str
    version: str
    description: str
    roles: tuple[str, ...]
    steps: tuple[ProtocolStepSummary, ...]


def describe_provider_options(
    diagnostics: LocalDiagnostics,
    *,
    env: Mapping[str, str] | None = None,
    openai_model_transport: OpenAIModelTransport | None = None,
) -> tuple[ProviderOption, ...]:
    env = os.environ if env is None else env
    openai_model_transport = (
        list_openai_models if openai_model_transport is None else openai_model_transport
    )
    ollama_status = next(
        (status for status in diagnostics.statuses if status.provider_id == "ollama"),
        None,
    )

    options: list[ProviderOption] = [
        ProviderOption(
            id="mock",
            label="Mock",
            status="ready",
            detail="Built-in deterministic provider; no external service required.",
        )
    ]

    api_key_present = env.get(OPENAI_API_KEY_ENV, "") != ""
    fallback_model_present = env.get(OPENAI_MODEL_ENV, "") != ""
    openai_models = _openai_models(env, openai_model_transport) if api_key_present else ()
    options.append(
        ProviderOption(
            id="openai",
            label="OpenAI",
            status="configured" if api_key_present else "not configured",
            detail=_openai_detail(api_key_present, fallback_model_present, openai_models),
            models=openai_models,
            model_required=True,
            model_placeholder="OpenAI model id",
            model_help=_model_help("OpenAI", openai_models),
        )
    )

    if ollama_status is None:
        options.append(
            ProviderOption(
                id="ollama",
                label="Ollama",
                status="unknown",
                detail="No Ollama diagnostic result is available.",
                model_required=True,
                model_placeholder="mistral:latest or qwen3:4b",
                model_help="No Ollama model was detected by the local provider diagnostic.",
            )
        )
    elif ollama_status.reachable and ollama_status.models:
        options.append(
            ProviderOption(
                id="ollama",
                label="Ollama",
                status="reachable",
                detail=f"Reachable at {ollama_status.base_url}; {len(ollama_status.models)} visible model(s).",
                models=ollama_status.models,
                model_required=True,
                model_placeholder="mistral:latest or qwen3:4b",
                model_help=_model_help("Ollama", ollama_status.models),
            )
        )
    elif ollama_status.reachable:
        options.append(
            ProviderOption(
                id="ollama",
                label="Ollama",
                status="reachable, no models",
                detail=ollama_status.recovery_hint
                or f"Reachable at {ollama_status.base_url}, but no models were reported.",
                model_required=True,
                model_placeholder="mistral:latest or qwen3:4b",
                model_help="No Ollama model was detected by the local provider diagnostic.",
            )
        )
    else:
        options.append(
            ProviderOption(
                id="ollama",
                label="Ollama",
                status="unreachable",
                detail=ollama_status.recovery_hint
                or f"Ollama was not reachable at {ollama_status.base_url}.",
                model_required=True,
                model_placeholder="mistral:latest or qwen3:4b",
                model_help="No Ollama model was detected by the local provider diagnostic.",
            )
        )

    return tuple(options)


def list_openai_models(base_url: str, api_key: str, timeout_seconds: float) -> tuple[str, ...]:
    url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError):
        return ()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return ()
    if not isinstance(parsed, dict):
        return ()
    data = parsed.get("data")
    if not isinstance(data, list):
        return ()
    return tuple(
        model_id
        for model_id in (_object_string(item, "id") for item in data)
        if model_id is not None
    )


def describe_presets(presets: Sequence[PresetInfo]) -> tuple[PresetDetail, ...]:
    return tuple(describe_preset(preset) for preset in presets)


def describe_preset(preset: PresetInfo) -> PresetDetail:
    protocol = load_preset(preset.name)
    return _preset_detail(preset, protocol)


def _preset_detail(preset: PresetInfo, protocol: Protocol) -> PresetDetail:
    return PresetDetail(
        name=preset.name,
        protocol_id=protocol.id,
        version=protocol.version,
        description=protocol.description,
        roles=tuple(sorted(protocol.roles)),
        steps=tuple(_step_summary(step) for step in protocol.steps),
    )


def _step_summary(step: StepDefinition) -> ProtocolStepSummary:
    if step.role is not None:
        roles = (step.role,)
    elif step.roles is not None:
        roles = step.roles
    else:
        roles = ()
    return ProtocolStepSummary(
        id=step.id,
        kind=step.kind.value,
        roles=roles,
        inputs=step.inputs,
        output=step.produces.output,
        output_kind=step.produces.kind,
        instruction_preview=_preview(step.instruction),
    )


def _preview(text: str, *, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _openai_models(
    env: Mapping[str, str],
    transport: OpenAIModelTransport,
) -> tuple[str, ...]:
    api_key = env.get(OPENAI_API_KEY_ENV, "")
    if api_key == "":
        return ()
    return transport(
        env.get(OPENAI_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL),
        api_key,
        OPENAI_MODEL_DISCOVERY_TIMEOUT_SECONDS,
    )


def _model_help(provider_label: str, models: tuple[str, ...]) -> str:
    if models:
        return f"{provider_label} models detected: {', '.join(models)}"
    return f"No {provider_label} model was detected."


def _object_string(value: Any, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    item = value.get(key)
    if not isinstance(item, str) or item == "":
        return None
    return item


def _openai_detail(
    api_key_present: bool,
    fallback_model_present: bool,
    models: tuple[str, ...],
) -> str:
    if api_key_present and fallback_model_present:
        model_note = " Visible models were discovered." if models else ""
        return (
            "API credentials and a default model are available to the Delibra process."
            + model_note
        )
    if api_key_present:
        model_note = " Visible models were discovered." if models else ""
        return "API credentials are available; choose a model for this run." + model_note
    if fallback_model_present:
        return "A default model is available, but API credentials are not available."
    return "API credentials are not available to the Delibra process."
