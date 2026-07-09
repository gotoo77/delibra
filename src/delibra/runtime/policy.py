from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from delibra.core.json import JsonFrozenObject, JsonMutableObject


DEFAULT_POLICY_ID = "default"
DEFAULT_POLICY_UNIT = "approx_token"


class ExecutionMode(str, Enum):
    CHEAP = "cheap"
    STANDARD = "standard"
    DEEP = "deep"

    @classmethod
    def parse(cls, value: str) -> "ExecutionMode":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown execution mode: {value}") from exc


class BudgetExceededAction(str, Enum):
    CANCEL_RUN = "cancel_run"

    @classmethod
    def parse(cls, value: str) -> "BudgetExceededAction":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unknown budget exceeded action: {value}") from exc


class PolicyDecisionAction(str, Enum):
    ALLOW_CALL = "allow_call"
    CANCEL_RUN = "cancel_run"


@dataclass(frozen=True)
class Budget:
    max_estimated_units: int | None = None
    max_output_units: int | None = None

    def __post_init__(self) -> None:
        _require_optional_positive_int(
            "max_estimated_units",
            self.max_estimated_units,
        )
        _require_optional_positive_int("max_output_units", self.max_output_units)

    def to_json(self) -> JsonMutableObject:
        return {
            "max_estimated_units": self.max_estimated_units,
            "max_output_units": self.max_output_units,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "Budget":
        _require_fields(
            "Budget",
            data,
            {"max_estimated_units", "max_output_units"},
        )
        return cls(
            max_estimated_units=_require_optional_int(
                "max_estimated_units",
                data["max_estimated_units"],
            ),
            max_output_units=_require_optional_int(
                "max_output_units",
                data["max_output_units"],
            ),
        )


@dataclass(frozen=True)
class StepPolicy:
    budget: Budget | None = None
    route_id: str | None = None

    def __post_init__(self) -> None:
        if self.budget is not None and not isinstance(self.budget, Budget):
            raise TypeError("budget must be a Budget")
        if self.route_id is not None:
            _require_non_empty_string("route_id", self.route_id)

    def to_json(self) -> JsonMutableObject:
        return {
            "budget": None if self.budget is None else self.budget.to_json(),
            "route_id": self.route_id,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "StepPolicy":
        _require_fields("StepPolicy", data, {"budget", "route_id"})
        budget = data["budget"]
        if budget is not None:
            budget = Budget.from_json(_require_object("budget", budget))
        route_id = data["route_id"]
        if route_id is not None:
            route_id = _require_non_empty_string("route_id", route_id)
        return cls(budget=budget, route_id=route_id)


@dataclass(frozen=True)
class ExecutionPolicy:
    id: str = DEFAULT_POLICY_ID
    mode: ExecutionMode = ExecutionMode.STANDARD
    unit: str = DEFAULT_POLICY_UNIT
    run_budget: Budget | None = None
    default_step_budget: Budget | None = None
    steps: Mapping[str, StepPolicy] = MappingProxyType({})
    routes: Mapping[str, JsonFrozenObject] = MappingProxyType({})
    on_budget_exceeded: BudgetExceededAction = BudgetExceededAction.CANCEL_RUN

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _require_non_empty_string("id", self.id))
        object.__setattr__(self, "mode", _coerce_execution_mode(self.mode))
        if self.unit != DEFAULT_POLICY_UNIT:
            raise ValueError(f"unit must be {DEFAULT_POLICY_UNIT} for v1")
        if self.run_budget is not None and not isinstance(self.run_budget, Budget):
            raise TypeError("run_budget must be a Budget")
        if self.default_step_budget is not None and not isinstance(
            self.default_step_budget,
            Budget,
        ):
            raise TypeError("default_step_budget must be a Budget")
        object.__setattr__(
            self,
            "on_budget_exceeded",
            _coerce_budget_exceeded_action(self.on_budget_exceeded),
        )
        steps = _coerce_steps(self.steps)
        routes = _coerce_routes(self.routes)
        _require_known_step_routes(steps, routes)
        object.__setattr__(self, "steps", MappingProxyType(steps))
        object.__setattr__(self, "routes", MappingProxyType(routes))

    def to_json(self) -> JsonMutableObject:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "unit": self.unit,
            "run_budget": None if self.run_budget is None else self.run_budget.to_json(),
            "default_step_budget": None
            if self.default_step_budget is None
            else self.default_step_budget.to_json(),
            "steps": {
                step_id: step_policy.to_json()
                for step_id, step_policy in self.steps.items()
            },
            "routes": {
                route_id: _thaw_json_object(route)
                for route_id, route in self.routes.items()
            },
            "on_budget_exceeded": self.on_budget_exceeded.value,
        }

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "ExecutionPolicy":
        _require_fields(
            "ExecutionPolicy",
            data,
            {
                "id",
                "mode",
                "unit",
                "run_budget",
                "default_step_budget",
                "steps",
                "routes",
                "on_budget_exceeded",
            },
        )
        run_budget = data["run_budget"]
        if run_budget is not None:
            run_budget = Budget.from_json(_require_object("run_budget", run_budget))
        default_step_budget = data["default_step_budget"]
        if default_step_budget is not None:
            default_step_budget = Budget.from_json(
                _require_object("default_step_budget", default_step_budget)
            )
        steps = {
            _require_non_empty_string("step id", step_id): StepPolicy.from_json(
                _require_object(f"steps.{step_id}", step_policy)
            )
            for step_id, step_policy in _require_object("steps", data["steps"]).items()
        }
        routes = {
            _require_non_empty_string("route id", route_id): _require_object(
                f"routes.{route_id}",
                route,
            )
            for route_id, route in _require_object("routes", data["routes"]).items()
        }
        return cls(
            id=_require_non_empty_string("id", data["id"]),
            mode=ExecutionMode.parse(_require_string("mode", data["mode"])),
            unit=_require_string("unit", data["unit"]),
            run_budget=run_budget,
            default_step_budget=default_step_budget,
            steps=steps,
            routes=routes,
            on_budget_exceeded=BudgetExceededAction.parse(
                _require_string("on_budget_exceeded", data["on_budget_exceeded"])
            ),
        )


@dataclass(frozen=True)
class PolicyState:
    consumed_run_units: int = 0
    consumed_step_units: Mapping[str, int] = MappingProxyType({})

    def __post_init__(self) -> None:
        _require_non_negative_int("consumed_run_units", self.consumed_run_units)
        consumed_step_units = dict(self.consumed_step_units)
        for step_id, consumed_units in consumed_step_units.items():
            _require_non_empty_string("step id", step_id)
            _require_non_negative_int("consumed step units", consumed_units)
        object.__setattr__(
            self,
            "consumed_step_units",
            MappingProxyType(consumed_step_units),
        )

    def with_reserved_units(self, step_id: str, units: int) -> "PolicyState":
        _require_non_empty_string("step_id", step_id)
        _require_non_negative_int("units", units)
        consumed_step_units = dict(self.consumed_step_units)
        consumed_step_units[step_id] = consumed_step_units.get(step_id, 0) + units
        return PolicyState(
            consumed_run_units=self.consumed_run_units + units,
            consumed_step_units=consumed_step_units,
        )


@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyDecisionAction
    reason: str
    policy_id: str
    mode: ExecutionMode
    unit: str
    step_id: str
    role_id: str | None
    estimated_input_units: int
    reserved_output_units: int
    estimated_total_units: int
    run_budget_remaining: int | None
    step_budget_remaining: int | None
    route_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _coerce_policy_decision_action(self.action))
        object.__setattr__(self, "mode", _coerce_execution_mode(self.mode))
        _require_non_empty_string("policy_id", self.policy_id)
        _require_string("unit", self.unit)
        _require_non_empty_string("step_id", self.step_id)
        if self.role_id is not None:
            _require_non_empty_string("role_id", self.role_id)
        _require_non_negative_int("estimated_input_units", self.estimated_input_units)
        _require_non_negative_int("reserved_output_units", self.reserved_output_units)
        _require_non_negative_int("estimated_total_units", self.estimated_total_units)
        if self.run_budget_remaining is not None:
            _require_non_negative_int(
                "run_budget_remaining",
                self.run_budget_remaining,
            )
        if self.step_budget_remaining is not None:
            _require_non_negative_int(
                "step_budget_remaining",
                self.step_budget_remaining,
            )
        if self.route_id is not None:
            _require_non_empty_string("route_id", self.route_id)
        _require_non_empty_string("reason", self.reason)

    def to_json(self) -> JsonMutableObject:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "mode": self.mode.value,
            "unit": self.unit,
            "step_id": self.step_id,
            "role_id": self.role_id,
            "estimated_input_units": self.estimated_input_units,
            "reserved_output_units": self.reserved_output_units,
            "estimated_total_units": self.estimated_total_units,
            "run_budget_remaining": self.run_budget_remaining,
            "step_budget_remaining": self.step_budget_remaining,
            "route_id": self.route_id,
        }


@dataclass(frozen=True)
class PolicyDecisionResult:
    decision: PolicyDecision
    state: PolicyState


def default_execution_policy() -> ExecutionPolicy:
    return ExecutionPolicy()


def default_policy_state() -> PolicyState:
    return PolicyState()


def estimate_approx_units(chars: int) -> int:
    if not isinstance(chars, int):
        raise TypeError("chars must be an integer")
    if chars < 0:
        raise ValueError("chars must be non-negative")
    return math.ceil(chars / 4)


def decide_before_call(
    policy: ExecutionPolicy,
    state: PolicyState,
    *,
    step_id: str,
    role_id: str | None = None,
    input_chars: int,
) -> PolicyDecisionResult:
    if not isinstance(policy, ExecutionPolicy):
        raise TypeError("policy must be an ExecutionPolicy")
    if not isinstance(state, PolicyState):
        raise TypeError("state must be a PolicyState")
    step_id = _require_non_empty_string("step_id", step_id)
    if role_id is not None:
        role_id = _require_non_empty_string("role_id", role_id)
    estimated_input_units = estimate_approx_units(input_chars)
    step_policy = policy.steps.get(step_id)
    step_budget = _effective_step_budget(policy, step_policy)
    reserved_output_units = _reserved_output_units(step_budget)
    estimated_total_units = estimated_input_units + reserved_output_units
    route_id = None if step_policy is None else step_policy.route_id

    run_budget_remaining = _remaining_after(
        policy.run_budget.max_estimated_units if policy.run_budget is not None else None,
        state.consumed_run_units,
        estimated_total_units,
    )
    step_budget_remaining = _remaining_after(
        step_budget.max_estimated_units if step_budget is not None else None,
        state.consumed_step_units.get(step_id, 0),
        estimated_total_units,
    )

    if run_budget_remaining is not None and run_budget_remaining < 0:
        decision = _policy_decision(
            policy,
            step_id=step_id,
            role_id=role_id,
            action=PolicyDecisionAction.CANCEL_RUN,
            reason="run budget exceeded",
            estimated_input_units=estimated_input_units,
            reserved_output_units=reserved_output_units,
            estimated_total_units=estimated_total_units,
            run_budget_remaining=0,
            step_budget_remaining=_clamp_remaining(step_budget_remaining),
            route_id=route_id,
        )
        return PolicyDecisionResult(decision=decision, state=state)

    if step_budget_remaining is not None and step_budget_remaining < 0:
        decision = _policy_decision(
            policy,
            step_id=step_id,
            role_id=role_id,
            action=PolicyDecisionAction.CANCEL_RUN,
            reason="step budget exceeded",
            estimated_input_units=estimated_input_units,
            reserved_output_units=reserved_output_units,
            estimated_total_units=estimated_total_units,
            run_budget_remaining=_clamp_remaining(run_budget_remaining),
            step_budget_remaining=0,
            route_id=route_id,
        )
        return PolicyDecisionResult(decision=decision, state=state)

    next_state = state.with_reserved_units(step_id, estimated_total_units)
    decision = _policy_decision(
        policy,
        step_id=step_id,
        role_id=role_id,
        action=PolicyDecisionAction.ALLOW_CALL,
        reason="within budget",
        estimated_input_units=estimated_input_units,
        reserved_output_units=reserved_output_units,
        estimated_total_units=estimated_total_units,
        run_budget_remaining=run_budget_remaining,
        step_budget_remaining=step_budget_remaining,
        route_id=route_id,
    )
    return PolicyDecisionResult(decision=decision, state=next_state)


def _policy_decision(
    policy: ExecutionPolicy,
    *,
    step_id: str,
    role_id: str | None,
    action: PolicyDecisionAction,
    reason: str,
    estimated_input_units: int,
    reserved_output_units: int,
    estimated_total_units: int,
    run_budget_remaining: int | None,
    step_budget_remaining: int | None,
    route_id: str | None,
) -> PolicyDecision:
    return PolicyDecision(
        action=action,
        reason=reason,
        policy_id=policy.id,
        mode=policy.mode,
        unit=policy.unit,
        step_id=step_id,
        role_id=role_id,
        estimated_input_units=estimated_input_units,
        reserved_output_units=reserved_output_units,
        estimated_total_units=estimated_total_units,
        run_budget_remaining=run_budget_remaining,
        step_budget_remaining=step_budget_remaining,
        route_id=route_id,
    )


def _effective_step_budget(
    policy: ExecutionPolicy,
    step_policy: StepPolicy | None,
) -> Budget | None:
    if step_policy is not None and step_policy.budget is not None:
        return step_policy.budget
    return policy.default_step_budget


def _reserved_output_units(step_budget: Budget | None) -> int:
    if step_budget is None or step_budget.max_output_units is None:
        return 0
    return step_budget.max_output_units


def _remaining_after(
    limit: int | None,
    consumed_units: int,
    new_units: int,
) -> int | None:
    if limit is None:
        return None
    return limit - consumed_units - new_units


def _clamp_remaining(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, value)


def _coerce_execution_mode(value: ExecutionMode | str) -> ExecutionMode:
    if isinstance(value, ExecutionMode):
        return value
    return ExecutionMode.parse(value)


def _coerce_policy_decision_action(
    value: PolicyDecisionAction | str,
) -> PolicyDecisionAction:
    if isinstance(value, PolicyDecisionAction):
        return value
    return PolicyDecisionAction(value)


def _coerce_budget_exceeded_action(
    value: BudgetExceededAction | str,
) -> BudgetExceededAction:
    if isinstance(value, BudgetExceededAction):
        return value
    return BudgetExceededAction.parse(value)


def _coerce_steps(value: Mapping[str, StepPolicy]) -> dict[str, StepPolicy]:
    if not isinstance(value, Mapping):
        raise TypeError("steps must be a mapping")
    steps = dict(value)
    for step_id, step_policy in steps.items():
        _require_non_empty_string("step id", step_id)
        if not isinstance(step_policy, StepPolicy):
            raise TypeError("steps values must be StepPolicy")
    return steps


def _coerce_routes(value: Mapping[str, JsonMutableObject | JsonFrozenObject]) -> dict[str, JsonFrozenObject]:
    if not isinstance(value, Mapping):
        raise TypeError("routes must be a mapping")
    routes: dict[str, JsonFrozenObject] = {}
    for route_id, route in value.items():
        _require_non_empty_string("route id", route_id)
        routes[route_id] = _freeze_json_object(_require_object("route", route))
    return routes


def _require_known_step_routes(
    steps: Mapping[str, StepPolicy],
    routes: Mapping[str, JsonFrozenObject],
) -> None:
    for step_id, step_policy in steps.items():
        if step_policy.route_id is not None and step_policy.route_id not in routes:
            raise ValueError(
                f"steps.{step_id}.route_id references unknown route: {step_policy.route_id}"
            )


def _freeze_json_object(value: JsonMutableObject | JsonFrozenObject) -> JsonFrozenObject:
    return MappingProxyType(
        {
            _require_string("JSON object key", key): _freeze_json_value(item)
            for key, item in value.items()
        }
    )


def _freeze_json_value(value: Any):
    if isinstance(value, Mapping):
        return _freeze_json_object(value)
    if isinstance(value, list) or isinstance(value, tuple):
        return tuple(_freeze_json_value(item) for item in value)
    if isinstance(value, str) or isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        raise TypeError("JSON-compatible values cannot include non-finite floats")
    raise TypeError("value must be JSON-compatible")


def _thaw_json_object(value: JsonFrozenObject) -> JsonMutableObject:
    return {
        key: _thaw_json_value(item)
        for key, item in value.items()
    }


def _thaw_json_value(value: Any):
    if isinstance(value, Mapping):
        return _thaw_json_object(value)
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _require_fields(name: str, data: JsonMutableObject, expected: set[str]) -> None:
    _require_object(name, data)
    actual = set(data)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{name} unknown fields: {', '.join(sorted(unknown))}")


def _require_object(name: str, value: Any) -> JsonMutableObject:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object")
    return dict(value)


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_non_empty_string(name: str, value: Any) -> str:
    value = _require_string(name, value)
    if value == "":
        raise ValueError(f"{name} must be non-empty")
    return value


def _require_optional_int(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_non_negative_int(name: str, value: Any) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_optional_positive_int(name: str, value: int | None) -> None:
    if value is None:
        return
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
