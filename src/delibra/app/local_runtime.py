from __future__ import annotations

import os
import socket
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from delibra.app.local_diagnostics import (
    KNOWN_LOCAL_PROVIDER_PROBES,
    LocalDiagnostics,
    LocalProviderProbe,
    LocalProviderStatus,
    diagnose_local_providers,
)
from delibra.runtime.builders import IdSequence
from delibra.runtime.llm import LLMRequest, Message
from delibra.runtime.ollama import (
    DEFAULT_OLLAMA_BASE_URL,
    OLLAMA_BASE_URL_ENV,
    OLLAMA_MAX_OUTPUT_TOKENS_ENV,
    OLLAMA_MODEL_ENV,
    OLLAMA_TIMEOUT_SECONDS_ENV,
    OllamaClient,
    OllamaConfigError,
    OllamaProviderError,
    OllamaTransport,
)


LocalRuntimeOperation = Literal["diagnose", "check_inference"]
LocalActiveProviderId = Literal["ollama"]
InferenceStatus = Literal[
    "not_attempted",
    "server_unreachable",
    "no_models",
    "model_missing",
    "timeout",
    "provider_error",
    "invalid_response",
    "succeeded",
]

DEFAULT_LOCAL_INFERENCE_TIMEOUT_SECONDS = 10.0
MINIMAL_INFERENCE_MAX_OUTPUT_TOKENS = 8
MINIMAL_INFERENCE_PROMPT = "Reply with OK."


@dataclass(frozen=True)
class LocalRuntimeIntent:
    operation: LocalRuntimeOperation = "diagnose"
    provider_id: LocalActiveProviderId = "ollama"
    model: str | None = None
    timeout_seconds: float = DEFAULT_LOCAL_INFERENCE_TIMEOUT_SECONDS


@dataclass(frozen=True)
class LocalInferenceCheck:
    provider_id: str
    attempted: bool
    status: InferenceStatus
    model: str | None = None
    error: str | None = None
    recovery_hint: str | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True)
class LocalRuntimeAssessment:
    diagnostics: LocalDiagnostics
    inference_checks: tuple[LocalInferenceCheck, ...] = ()


def assess_local_runtime(
    intent: LocalRuntimeIntent,
    *,
    probes: Sequence[LocalProviderProbe] = KNOWN_LOCAL_PROVIDER_PROBES,
    env: Mapping[str, str] | None = None,
    diagnostics: LocalDiagnostics | None = None,
    ollama_transport: OllamaTransport | None = None,
    monotonic: Callable[[], float] | None = None,
) -> LocalRuntimeAssessment:
    env = os.environ if env is None else env
    diagnostics = (
        diagnose_local_providers(probes=_probes_for_intent(probes, intent, env))
        if diagnostics is None
        else diagnostics
    )
    if intent.operation == "diagnose":
        return LocalRuntimeAssessment(diagnostics=diagnostics)

    selected_model = _selected_model(intent, env)
    ollama_status = _first_status(diagnostics.statuses, provider_id="ollama")
    check = _check_ollama_inference(
        ollama_status,
        selected_model=selected_model,
        timeout_seconds=intent.timeout_seconds,
        env=env,
        transport=ollama_transport,
        monotonic=time.monotonic if monotonic is None else monotonic,
    )
    return LocalRuntimeAssessment(
        diagnostics=diagnostics,
        inference_checks=(check,),
    )


def _selected_model(intent: LocalRuntimeIntent, env: Mapping[str, str]) -> str | None:
    if intent.model is not None and intent.model != "":
        return intent.model
    model = env.get(OLLAMA_MODEL_ENV, "")
    if model != "":
        return model
    return None


def _probes_for_intent(
    probes: Sequence[LocalProviderProbe],
    intent: LocalRuntimeIntent,
    env: Mapping[str, str],
) -> Sequence[LocalProviderProbe]:
    if intent.operation != "check_inference":
        return probes
    base_url = env.get(OLLAMA_BASE_URL_ENV, "")
    if base_url == "":
        return probes
    return tuple(
        LocalProviderProbe(
            provider_id=probe.provider_id,
            label=probe.label,
            kind=probe.kind,
            base_urls=(base_url,),
        )
        if probe.provider_id == "ollama"
        else probe
        for probe in probes
    )


def _first_status(
    statuses: Sequence[LocalProviderStatus],
    *,
    provider_id: str,
) -> LocalProviderStatus | None:
    for status in statuses:
        if status.provider_id == provider_id:
            return status
    return None


def _check_ollama_inference(
    status: LocalProviderStatus | None,
    *,
    selected_model: str | None,
    timeout_seconds: float,
    env: Mapping[str, str],
    transport: OllamaTransport | None,
    monotonic: Callable[[], float],
) -> LocalInferenceCheck:
    if status is None or not status.reachable:
        return LocalInferenceCheck(
            provider_id="ollama",
            attempted=False,
            status="server_unreachable",
            model=selected_model,
            error=None if status is None else status.error,
            recovery_hint=(
                "Start Ollama, verify it is listening at "
                f"{DEFAULT_OLLAMA_BASE_URL}, then rerun `delibra doctor local`."
            )
            if status is None
            else status.recovery_hint,
        )
    if not status.models:
        return LocalInferenceCheck(
            provider_id="ollama",
            attempted=False,
            status="no_models",
            model=selected_model,
            recovery_hint=(
                "Ollama is reachable but reports no models. Download a model with "
                "Ollama tooling, then rerun the check."
            ),
        )
    if selected_model is None:
        return LocalInferenceCheck(
            provider_id="ollama",
            attempted=False,
            status="not_attempted",
            recovery_hint=(
                "Choose a model explicitly with `--model`, or set OLLAMA_MODEL, "
                "then rerun with `--check-inference`."
            ),
        )
    if selected_model not in status.models:
        return LocalInferenceCheck(
            provider_id="ollama",
            attempted=False,
            status="model_missing",
            model=selected_model,
            error=f"model is not listed by Ollama: {selected_model}",
            recovery_hint=(
                "Choose one of the visible models, or download the requested model "
                "with Ollama tooling before rerunning the check."
            ),
        )

    base_url = env.get(OLLAMA_BASE_URL_ENV, status.base_url)
    start = monotonic()
    try:
        client = OllamaClient.from_env(
            response_message_ids=IdSequence("msg_response"),
            env={
                OLLAMA_MODEL_ENV: selected_model,
                OLLAMA_BASE_URL_ENV: base_url,
                OLLAMA_TIMEOUT_SECONDS_ENV: str(timeout_seconds),
                OLLAMA_MAX_OUTPUT_TOKENS_ENV: str(MINIMAL_INFERENCE_MAX_OUTPUT_TOKENS),
            },
            transport=transport,
        )
        client.generate(_minimal_request())
    except (TimeoutError, socket.timeout) as exc:
        return _failed_inference_check(
            "timeout",
            selected_model,
            str(exc),
            start,
            monotonic,
        )
    except OllamaProviderError as exc:
        status_code = _classify_ollama_provider_error(str(exc))
        return _failed_inference_check(
            status_code,
            selected_model,
            str(exc),
            start,
            monotonic,
        )
    except OllamaConfigError as exc:
        return _failed_inference_check(
            "provider_error",
            selected_model,
            str(exc),
            start,
            monotonic,
        )

    return LocalInferenceCheck(
        provider_id="ollama",
        attempted=True,
        status="succeeded",
        model=selected_model,
        duration_seconds=monotonic() - start,
    )


def _minimal_request() -> LLMRequest:
    return LLMRequest(
        message=Message(
            id="msg_probe_0001",
            role="user",
            content=MINIMAL_INFERENCE_PROMPT,
        ),
        step_id="local_inference_check",
        role_id="local_probe",
        inputs={},
    )


def _classify_ollama_provider_error(message: str) -> InferenceStatus:
    lowered = message.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if "did not contain non-empty response text" in lowered:
        return "invalid_response"
    if "response was not valid json" in lowered or "response must be a json object" in lowered:
        return "invalid_response"
    return "provider_error"


def _failed_inference_check(
    status: InferenceStatus,
    model: str,
    error: str,
    start: float,
    monotonic: Callable[[], float],
) -> LocalInferenceCheck:
    return LocalInferenceCheck(
        provider_id="ollama",
        attempted=True,
        status=status,
        model=model,
        error=error,
        recovery_hint=_inference_recovery_hint(status),
        duration_seconds=monotonic() - start,
    )


def _inference_recovery_hint(status: InferenceStatus) -> str:
    if status == "timeout":
        return (
            "The model did not answer before the check timeout. Verify that Ollama "
            "is still responsive, check machine load, try a smaller model if needed, "
            "or rerun with a longer inference timeout."
        )
    if status == "invalid_response":
        return (
            "Verify that the local endpoint behaves like Ollama /api/generate and "
            "returns a non-empty response field."
        )
    return (
        "Review the provider error, verify that the model can run in Ollama, then "
        "rerun the inference check."
    )
