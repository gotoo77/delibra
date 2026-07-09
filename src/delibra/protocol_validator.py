from __future__ import annotations

from dataclasses import dataclass

from delibra.core import Protocol, StepDefinition, StepKind, USER_INPUT_RESERVED_ID


@dataclass(frozen=True)
class ProtocolValidationError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def validate_protocol(protocol: Protocol) -> None:
    _validate_non_empty_protocol_fields(protocol)
    _validate_unique_role_ids(protocol)
    _validate_steps(protocol)


def _validate_non_empty_protocol_fields(protocol: Protocol) -> None:
    if protocol.id == "":
        raise ProtocolValidationError("protocol id is required")
    if protocol.version == "":
        raise ProtocolValidationError("protocol version is required")
    if not protocol.roles:
        raise ProtocolValidationError("protocol roles must be non-empty")
    if not protocol.steps:
        raise ProtocolValidationError("protocol steps must be non-empty")


def _validate_unique_role_ids(protocol: Protocol) -> None:
    for role_id, role in protocol.roles.items():
        if role.id != role_id:
            raise ProtocolValidationError(
                f"role map key '{role_id}' must match role id '{role.id}'"
            )


def _validate_steps(protocol: Protocol) -> None:
    role_ids = set(protocol.roles)
    step_ids: set[str] = set()
    output_ids: set[str] = set()
    available_inputs = {USER_INPUT_RESERVED_ID}

    for index, step in enumerate(protocol.steps):
        if step.id in step_ids:
            raise ProtocolValidationError(f"duplicate step id: {step.id}")
        step_ids.add(step.id)

        if step.produces.output in output_ids:
            raise ProtocolValidationError(
                f"duplicate produces.output: {step.produces.output}"
            )
        output_ids.add(step.produces.output)

        _validate_step_shape(step, index, len(protocol.steps), role_ids)
        _validate_step_inputs(step, available_inputs)

        available_inputs.add(step.produces.output)


def _validate_step_shape(
    step: StepDefinition, index: int, step_count: int, role_ids: set[str]
) -> None:
    if step.instruction == "":
        raise ProtocolValidationError(f"step {step.id} instruction is required")
    if step.produces.output == "":
        raise ProtocolValidationError(f"step {step.id} produces.output is required")
    if step.produces.output == USER_INPUT_RESERVED_ID:
        raise ProtocolValidationError(
            f"step {step.id} produces.output uses reserved input id: "
            f"{USER_INPUT_RESERVED_ID}"
        )
    if step.produces.kind == "":
        raise ProtocolValidationError(f"step {step.id} produces.kind is required")

    if step.kind in (StepKind.PROMPT, StepKind.SYNTHESIZE):
        _require_single_role(step, role_ids)
    elif step.kind in (StepKind.FANOUT, StepKind.CRITICIZE):
        _require_many_roles(step, role_ids)
    else:
        raise ProtocolValidationError(f"unsupported step kind: {step.kind}")

    if step.kind is StepKind.SYNTHESIZE and index != step_count - 1:
        raise ProtocolValidationError("synthesize step must be final")


def _require_single_role(step: StepDefinition, role_ids: set[str]) -> None:
    if step.role is None:
        raise ProtocolValidationError(f"{step.kind.value} step {step.id} requires role")
    if step.roles is not None:
        raise ProtocolValidationError(f"{step.kind.value} step {step.id} forbids roles")
    _require_role_exists(step.role, role_ids, step.id)


def _require_many_roles(step: StepDefinition, role_ids: set[str]) -> None:
    if step.role is not None:
        raise ProtocolValidationError(f"{step.kind.value} step {step.id} forbids role")
    if not step.roles:
        raise ProtocolValidationError(
            f"{step.kind.value} step {step.id} requires non-empty roles"
        )
    for role_id in step.roles:
        _require_role_exists(role_id, role_ids, step.id)


def _require_role_exists(role_id: str, role_ids: set[str], step_id: str) -> None:
    if role_id not in role_ids:
        raise ProtocolValidationError(
            f"step {step_id} references unknown role: {role_id}"
        )


def _validate_step_inputs(step: StepDefinition, available_inputs: set[str]) -> None:
    for input_id in step.inputs:
        if input_id not in available_inputs:
            raise ProtocolValidationError(
                f"step {step.id} input references unavailable output: {input_id}"
            )
