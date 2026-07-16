from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from delibra.app.local_diagnostics import LocalDiagnostics
from delibra.app.models import ProviderId
from delibra.app.presets import PresetInfo, load_preset
from delibra.core import Protocol, StepDefinition
from delibra.runtime.openai import OPENAI_API_KEY_ENV, OPENAI_MODEL_ENV


SUPPORTED_PROVIDER_IDS: tuple[ProviderId, ...] = ("mock", "openai", "ollama")


@dataclass(frozen=True)
class ProviderOption:
    id: ProviderId
    label: str
    status: str
    detail: str
    models: tuple[str, ...] = ()
    model_required: bool = False


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
) -> tuple[ProviderOption, ...]:
    env = os.environ if env is None else env
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
    options.append(
        ProviderOption(
            id="openai",
            label="OpenAI",
            status="configured" if api_key_present else "not configured",
            detail=_openai_detail(api_key_present, fallback_model_present),
            model_required=not fallback_model_present,
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
            )
        )

    return tuple(options)


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


def _openai_detail(api_key_present: bool, fallback_model_present: bool) -> str:
    if api_key_present and fallback_model_present:
        return "API credentials and a default model are available to the Delibra process."
    if api_key_present:
        return "API credentials are available; choose a model for this run."
    if fallback_model_present:
        return "A default model is available, but API credentials are not available."
    return "API credentials are not available to the Delibra process."
