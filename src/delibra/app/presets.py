from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from delibra.core import Protocol
from delibra.protocol_loader import load_protocol_yaml


_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PRESET_DIR = _ROOT / "presets"
_PRESET_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


class PresetError(ValueError):
    pass


@dataclass(frozen=True)
class PresetInfo:
    name: str
    protocol_id: str
    version: str
    description: str
    path: Path


def list_presets(preset_dir: str | Path = DEFAULT_PRESET_DIR) -> tuple[PresetInfo, ...]:
    root = Path(preset_dir)
    presets: list[PresetInfo] = []
    for path in sorted(root.glob("*.yaml")):
        protocol = load_protocol_yaml(path)
        presets.append(
            PresetInfo(
                name=path.stem,
                protocol_id=protocol.id,
                version=protocol.version,
                description=protocol.description,
                path=path,
            )
        )
    return tuple(presets)


def resolve_preset_path(
    name: str,
    preset_dir: str | Path = DEFAULT_PRESET_DIR,
) -> Path:
    if not _PRESET_NAME_RE.fullmatch(name):
        raise PresetError(f"invalid preset name: {name}")

    root = Path(preset_dir).resolve()
    path = (root / f"{name}.yaml").resolve()
    if path.parent != root:
        raise PresetError(f"invalid preset name: {name}")
    if not path.exists():
        raise PresetError(f"preset not found: {name}")
    return path


def load_preset(name: str, preset_dir: str | Path = DEFAULT_PRESET_DIR) -> Protocol:
    return load_protocol_yaml(resolve_preset_path(name, preset_dir))
