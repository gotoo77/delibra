from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from delibra.core.json import JsonMutableObject


ProbeKind = Literal["ollama", "openai-compatible"]
HttpGetJson = Callable[[str, float], JsonMutableObject]

DEFAULT_LOCAL_DIAGNOSTIC_TIMEOUT_SECONDS = 1.0


@dataclass(frozen=True)
class LocalProviderProbe:
    provider_id: str
    label: str
    kind: ProbeKind
    base_urls: tuple[str, ...]


@dataclass(frozen=True)
class LocalProviderStatus:
    provider_id: str
    label: str
    kind: ProbeKind
    base_url: str
    reachable: bool
    models: tuple[str, ...]
    error: str | None
    recovery_hint: str | None


@dataclass(frozen=True)
class LocalDiagnostics:
    statuses: tuple[LocalProviderStatus, ...]

    @property
    def reachable_statuses(self) -> tuple[LocalProviderStatus, ...]:
        return tuple(status for status in self.statuses if status.reachable)


KNOWN_LOCAL_PROVIDER_PROBES = (
    LocalProviderProbe(
        provider_id="ollama",
        label="Ollama",
        kind="ollama",
        base_urls=("http://localhost:11434",),
    ),
    LocalProviderProbe(
        provider_id="openai-compatible",
        label="OpenAI-compatible local endpoint",
        kind="openai-compatible",
        base_urls=(
            "http://localhost:1234/v1",
            "http://localhost:8080/v1",
        ),
    ),
)


def diagnose_local_providers(
    *,
    probes: Sequence[LocalProviderProbe] = KNOWN_LOCAL_PROVIDER_PROBES,
    transport: HttpGetJson | None = None,
    timeout_seconds: float = DEFAULT_LOCAL_DIAGNOSTIC_TIMEOUT_SECONDS,
) -> LocalDiagnostics:
    transport = http_get_json if transport is None else transport
    statuses: list[LocalProviderStatus] = []
    for probe in probes:
        for base_url in probe.base_urls:
            statuses.append(
                _probe_base_url(
                    probe,
                    base_url=base_url,
                    transport=transport,
                    timeout_seconds=timeout_seconds,
                )
            )
    return LocalDiagnostics(statuses=tuple(statuses))


def http_get_json(url: str, timeout_seconds: float) -> JsonMutableObject:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ConnectionError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc
    except (OSError, TimeoutError, socket.timeout) as exc:
        raise ConnectionError(str(exc)) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("response was not valid JSON") from exc
    if not isinstance(data, dict):
        raise TypeError("response JSON must be an object")
    return data


def _probe_base_url(
    probe: LocalProviderProbe,
    *,
    base_url: str,
    transport: HttpGetJson,
    timeout_seconds: float,
) -> LocalProviderStatus:
    url = _models_url(probe, base_url)
    try:
        data = transport(url, timeout_seconds)
        models = _extract_models(probe, data)
    except (ConnectionError, OSError, TimeoutError) as exc:
        return _unreachable_status(
            probe,
            base_url,
            error=str(exc),
            recovery_hint=_connection_recovery_hint(probe, base_url),
        )
    except (TypeError, ValueError) as exc:
        return _unreachable_status(
            probe,
            base_url,
            error=str(exc),
            recovery_hint=(
                "Verify that the local server exposes the expected model listing "
                "API for this provider type."
            ),
        )

    if not models:
        return LocalProviderStatus(
            provider_id=probe.provider_id,
            label=probe.label,
            kind=probe.kind,
            base_url=base_url,
            reachable=True,
            models=(),
            error=None,
            recovery_hint=(
                "The endpoint is reachable, but no models were reported. "
                "Install or load a model with your local provider tooling, then "
                "rerun `delibra doctor local`."
            ),
        )

    return LocalProviderStatus(
        provider_id=probe.provider_id,
        label=probe.label,
        kind=probe.kind,
        base_url=base_url,
        reachable=True,
        models=models,
        error=None,
        recovery_hint=None,
    )


def _models_url(probe: LocalProviderProbe, base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if probe.kind == "ollama":
        return base_url + "/api/tags"
    if probe.kind == "openai-compatible":
        return base_url + "/models"
    raise ValueError(f"unsupported local provider probe kind: {probe.kind}")


def _extract_models(
    probe: LocalProviderProbe,
    data: JsonMutableObject,
) -> tuple[str, ...]:
    if probe.kind == "ollama":
        return _extract_ollama_models(data)
    if probe.kind == "openai-compatible":
        return _extract_openai_compatible_models(data)
    raise ValueError(f"unsupported local provider probe kind: {probe.kind}")


def _extract_ollama_models(data: JsonMutableObject) -> tuple[str, ...]:
    models = data.get("models")
    if not isinstance(models, list):
        raise TypeError("Ollama /api/tags response missing models array")
    return tuple(
        name
        for name in (_object_string(model, "name") for model in models)
        if name is not None
    )


def _extract_openai_compatible_models(data: JsonMutableObject) -> tuple[str, ...]:
    models = data.get("data")
    if not isinstance(models, list):
        raise TypeError("OpenAI-compatible /models response missing data array")
    return tuple(
        model_id
        for model_id in (_object_string(model, "id") for model in models)
        if model_id is not None
    )


def _object_string(value: Any, key: str) -> str | None:
    if not isinstance(value, dict):
        return None
    item = value.get(key)
    if not isinstance(item, str) or item == "":
        return None
    return item


def _unreachable_status(
    probe: LocalProviderProbe,
    base_url: str,
    *,
    error: str,
    recovery_hint: str,
) -> LocalProviderStatus:
    return LocalProviderStatus(
        provider_id=probe.provider_id,
        label=probe.label,
        kind=probe.kind,
        base_url=base_url,
        reachable=False,
        models=(),
        error=error,
        recovery_hint=recovery_hint,
    )


def _connection_recovery_hint(probe: LocalProviderProbe, base_url: str) -> str:
    if probe.kind == "ollama":
        return (
            f"Start Ollama, verify it is listening at {base_url}, or configure "
            "OLLAMA_BASE_URL before running Delibra."
        )
    return (
        f"Start a local OpenAI-compatible server at {base_url}, or rerun the "
        "diagnostic against the base URL your local server actually uses."
    )
