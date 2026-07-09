from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from delibra.core.json import JsonMutableObject
from delibra.runtime.policy import Budget, ExecutionPolicy


class PolicyLoadError(Exception):
    """Raised when an execution policy file cannot be loaded."""


def load_policy_yaml(path: str | Path) -> ExecutionPolicy:
    policy_path = Path(path)
    try:
        raw = policy_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"policy file not found: {policy_path}") from exc
    except OSError as exc:
        raise PolicyLoadError(f"could not read policy file: {policy_path}") from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"invalid policy YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise PolicyLoadError("policy YAML must be a mapping")

    try:
        normalized = _normalize_policy_yaml(data)
        return ExecutionPolicy.from_json(normalized)
    except (TypeError, ValueError) as exc:
        raise PolicyLoadError(f"invalid policy YAML shape: {exc}") from exc


def _normalize_policy_yaml(data: dict[str, Any]) -> JsonMutableObject:
    policy = dict(data)
    unknown = set(policy) - {
        "id",
        "mode",
        "unit",
        "budget",
        "default_step_budget",
        "steps",
        "routes",
        "on_budget_exceeded",
    }
    if unknown:
        raise ValueError(f"policy unknown fields: {', '.join(sorted(unknown))}")

    policy.setdefault("unit", "approx_token")
    policy.setdefault("budget", None)
    policy.setdefault("default_step_budget", None)
    policy.setdefault("steps", {})
    policy.setdefault("routes", {})
    policy.setdefault("on_budget_exceeded", "cancel_run")

    return {
        "id": policy.get("id"),
        "mode": policy.get("mode", "standard"),
        "unit": policy["unit"],
        "run_budget": _normalize_budget(policy["budget"]),
        "default_step_budget": _normalize_budget(policy["default_step_budget"]),
        "steps": {
            _require_string("step id", step_id): _normalize_step_policy(
                step_id,
                step_policy,
            )
            for step_id, step_policy in _require_mapping(
                "steps",
                policy["steps"],
            ).items()
        },
        "routes": {
            _require_string("route id", route_id): _require_mapping(
                f"routes.{route_id}",
                route,
            )
            for route_id, route in _require_mapping("routes", policy["routes"]).items()
        },
        "on_budget_exceeded": policy["on_budget_exceeded"],
    }


def _normalize_step_policy(step_id: str, data: Any) -> JsonMutableObject:
    data = _require_mapping(f"steps.{step_id}", data)
    unknown = set(data) - {"max_estimated_units", "max_output_units", "route_id", "budget"}
    if unknown:
        raise ValueError(
            f"steps.{step_id} unknown fields: {', '.join(sorted(unknown))}"
        )
    budget = data.get("budget")
    if budget is None:
        budget = {
            "max_estimated_units": data.get("max_estimated_units"),
            "max_output_units": data.get("max_output_units"),
        }
    return {
        "budget": _normalize_budget(budget),
        "route_id": data.get("route_id"),
    }


def _normalize_budget(data: Any) -> JsonMutableObject | None:
    if data is None:
        return None
    data = _require_mapping("budget", data)
    unknown = set(data) - {"max_estimated_units", "max_output_units"}
    if unknown:
        raise ValueError(f"budget unknown fields: {', '.join(sorted(unknown))}")
    return Budget(
        max_estimated_units=data.get("max_estimated_units"),
        max_output_units=data.get("max_output_units"),
    ).to_json()


def _require_mapping(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a mapping")
    return value


def _require_string(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
