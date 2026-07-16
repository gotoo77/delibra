from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from delibra.core import Protocol, Run, Trace
from delibra.core.json import JsonMutableObject
from delibra.runtime.policy import ExecutionPolicy


ProviderId = Literal["mock", "openai", "ollama"]


@dataclass(frozen=True)
class ProviderConfig:
    id: ProviderId = "mock"
    model: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class RunOutputTarget:
    run_path: Path
    trace_path: Path


@dataclass(frozen=True)
class ValidateProtocolRequest:
    protocol: Protocol | None = None
    protocol_path: Path | None = None


@dataclass(frozen=True)
class ValidationResult:
    protocol: Protocol


@dataclass(frozen=True)
class RunProtocolRequest:
    protocol: Protocol | None = None
    protocol_path: Path | None = None
    input_ref: JsonMutableObject | None = None
    provider: ProviderConfig = ProviderConfig()
    policy: ExecutionPolicy | None = None
    policy_path: Path | None = None
    output: RunOutputTarget | None = None


@dataclass(frozen=True)
class RunProtocolResult:
    run: Run
    trace: Trace
    run_path: Path | None = None
    trace_path: Path | None = None
