from __future__ import annotations

import json
from pathlib import Path

from delibra.app.storage import load_json_object
from delibra.core.json import JsonMutableObject


def input_from_text(text: str) -> JsonMutableObject:
    return {"kind": "text", "content": text}


def input_from_file(path: str | Path) -> JsonMutableObject:
    input_path = Path(path)
    try:
        return input_from_text(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"input file not found: {input_path}") from exc
    except OSError as exc:
        raise OSError(f"could not read input file: {input_path}") from exc


def input_from_json(raw: str) -> JsonMutableObject:
    try:
        return load_json_object(raw, "input JSON")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid input JSON: {exc}") from exc
