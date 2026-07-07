from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from delibra.core import Protocol
from delibra.core.json import JsonMutableObject


class ProtocolLoadError(Exception):
    """Raised when a protocol file cannot be loaded as canonical Protocol data."""


def load_protocol_yaml(path: str | Path) -> Protocol:
    protocol_path = Path(path)
    try:
        raw = protocol_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ProtocolLoadError(f"protocol file not found: {protocol_path}") from exc
    except OSError as exc:
        raise ProtocolLoadError(f"could not read protocol file: {protocol_path}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ProtocolLoadError(f"invalid protocol YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ProtocolLoadError("protocol YAML must be a mapping")

    try:
        normalized = _normalize_protocol_yaml(data)
    except (TypeError, ValueError) as exc:
        raise ProtocolLoadError(f"invalid protocol YAML shape: {exc}") from exc

    try:
        return Protocol.from_json(normalized)
    except (TypeError, ValueError) as exc:
        raise ProtocolLoadError(f"invalid canonical protocol shape: {exc}") from exc


def _normalize_protocol_yaml(data: dict[str, Any]) -> JsonMutableObject:
    protocol = dict(data)
    roles = protocol.get("roles")
    if not isinstance(roles, dict):
        raise TypeError("roles must be a mapping")
    protocol["roles"] = {
        _require_string("role id", role_id): _normalize_role_yaml(role_id, role)
        for role_id, role in roles.items()
    }
    return protocol


def _normalize_role_yaml(role_id: str, role: Any) -> JsonMutableObject:
    if not isinstance(role, dict):
        raise TypeError(f"roles.{role_id} must be a mapping")
    normalized = dict(role)
    normalized["id"] = role_id
    return normalized


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
