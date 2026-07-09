from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from delibra.core.json import JsonMutableObject


USER_INPUT_RESERVED_ID = "user_input"


class StepKind(str, Enum):
    PROMPT = "prompt"
    FANOUT = "fanout"
    CRITICIZE = "criticize"
    SYNTHESIZE = "synthesize"

    @classmethod
    def parse(cls, value: str) -> "StepKind":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown step kind: {value}") from exc


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    instruction: str

    def __post_init__(self) -> None:
        _require_non_empty_string("id", self.id)
        _require_string("name", self.name)
        _require_string("instruction", self.instruction)

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "name": self.name,
            "instruction": self.instruction,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Role":
        _require_fields("Role", data, {"id", "name", "instruction"})
        return cls(
            id=_require_string("id", data["id"]),
            name=_require_string("name", data["name"]),
            instruction=_require_string("instruction", data["instruction"]),
        )


@dataclass(frozen=True)
class Produces:
    output: str
    kind: str

    def __post_init__(self) -> None:
        _require_non_empty_string("output", self.output)
        _require_string("kind", self.kind)

    def to_json(self) -> JsonMutableObject:
        return {
            "output": self.output,
            "kind": self.kind,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Produces":
        _require_fields("Produces", data, {"output", "kind"})
        return cls(
            output=_require_string("output", data["output"]),
            kind=_require_string("kind", data["kind"]),
        )


@dataclass(frozen=True)
class StepDefinition:
    id: str
    kind: StepKind
    role: str | None
    roles: tuple[str, ...] | None
    instruction: str
    inputs: tuple[str, ...]
    produces: Produces

    def __post_init__(self) -> None:
        _require_non_empty_string("id", self.id)
        object.__setattr__(self, "kind", _coerce_step_kind(self.kind))
        if self.role is not None:
            _require_string("role", self.role)
        _require_string("instruction", self.instruction)
        if not isinstance(self.produces, Produces):
            raise TypeError("produces must be a Produces")
        object.__setattr__(self, "roles", _coerce_optional_string_tuple("roles", self.roles))
        object.__setattr__(self, "inputs", _coerce_string_tuple("inputs", self.inputs))

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "role": self.role,
            "roles": None if self.roles is None else list(self.roles),
            "instruction": self.instruction,
            "inputs": list(self.inputs),
            "produces": self.produces.to_json(),
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "StepDefinition":
        _require_fields(
            "StepDefinition",
            data,
            {"id", "kind", "role", "roles", "instruction", "inputs", "produces"},
        )
        role = data["role"]
        if role is not None:
            role = _require_string("role", role)
        return cls(
            id=_require_string("id", data["id"]),
            kind=StepKind.parse(_require_string("kind", data["kind"])),
            role=role,
            roles=_require_optional_string_list("roles", data["roles"]),
            instruction=_require_string("instruction", data["instruction"]),
            inputs=_require_string_list("inputs", data["inputs"]),
            produces=Produces.from_json(_require_object("produces", data["produces"])),
        )


@dataclass(frozen=True)
class Protocol:
    id: str
    version: str
    description: str
    roles: Mapping[str, Role]
    steps: tuple[StepDefinition, ...]

    def __post_init__(self) -> None:
        _require_non_empty_string("id", self.id)
        _require_non_empty_string("version", self.version)
        _require_string("description", self.description)
        if not isinstance(self.roles, Mapping):
            raise TypeError("roles must be a mapping")
        roles = dict(self.roles)
        for role_id, role in roles.items():
            _require_non_empty_string("role id", role_id)
            if not isinstance(role, Role):
                raise TypeError("roles values must be Role")
        steps = _coerce_step_tuple("steps", self.steps)
        object.__setattr__(self, "roles", MappingProxyType(roles))
        object.__setattr__(self, "steps", steps)

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "roles": {
                role_id: role.to_json()
                for role_id, role in self.roles.items()
            },
            "steps": [step.to_json() for step in self.steps],
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Protocol":
        _require_fields(
            "Protocol",
            data,
            {"id", "version", "description", "roles", "steps"},
        )
        roles = _require_object("roles", data["roles"])
        steps = data["steps"]
        if not isinstance(steps, list):
            raise TypeError("steps must be a JSON array")
        return cls(
            id=_require_string("id", data["id"]),
            version=_require_string("version", data["version"]),
            description=_require_string("description", data["description"]),
            roles={
                _require_string("role id", role_id): Role.from_json(
                    _require_object(f"roles.{role_id}", role)
                )
                for role_id, role in roles.items()
            },
            steps=tuple(
                StepDefinition.from_json(_require_object("step", step))
                for step in steps
            ),
        )


def _coerce_step_kind(value: StepKind | str) -> StepKind:
    if isinstance(value, StepKind):
        return value
    return StepKind.parse(value)


def _coerce_string_tuple(name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be a list or tuple of strings")
    return tuple(_require_string(name, item) for item in value)


def _coerce_optional_string_tuple(
    name: str, value: Any
) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _coerce_string_tuple(name, value)


def _coerce_step_tuple(name: str, value: Any) -> tuple[StepDefinition, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be a list or tuple of StepDefinition")
    steps = tuple(value)
    for step in steps:
        if not isinstance(step, StepDefinition):
            raise TypeError(f"{name} values must be StepDefinition")
    return steps


def _require_fields(name: str, data: JsonMutableObject, expected: set[str]) -> None:
    _require_object(name, data)
    actual = set(data)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{name} unknown fields: {', '.join(sorted(unknown))}")


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_non_empty_string(name: str, value: Any) -> str:
    value = _require_string(name, value)
    if value == "":
        raise ValueError(f"{name} must be non-empty")
    return value


def _require_object(name: str, value: Any) -> JsonMutableObject:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON object")
    return value


def _require_string_list(name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    return tuple(_require_string(name, item) for item in value)


def _require_optional_string_list(name: str, value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _require_string_list(name, value)
