from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from delibra.policy_loader import PolicyLoadError, load_policy_yaml
from delibra.runtime.policy import (
    Budget,
    ExecutionMode,
    ExecutionPolicy,
    PolicyDecisionAction,
    PolicyState,
    StepPolicy,
    decide_before_call,
    default_execution_policy,
    default_policy_state,
    estimate_approx_units,
)


class ExecutionPolicyTests(unittest.TestCase):
    def test_default_execution_policy_is_unbounded_standard_policy(self) -> None:
        policy = default_execution_policy()

        self.assertEqual(policy.id, "default")
        self.assertEqual(policy.mode, ExecutionMode.STANDARD)
        self.assertEqual(policy.unit, "approx_token")
        self.assertIsNone(policy.run_budget)
        self.assertIsNone(policy.default_step_budget)
        self.assertEqual(policy.steps, {})
        self.assertEqual(policy.routes, {})

    def test_constructs_policy_with_opaque_routes(self) -> None:
        policy = ExecutionPolicy(
            id="cheap-review",
            mode=ExecutionMode.CHEAP,
            run_budget=Budget(max_estimated_units=3000),
            default_step_budget=Budget(max_output_units=300),
            routes={
                "cheap-default": {
                    "provider": "openai",
                    "model": "gpt-5-mini",
                },
            },
            steps={
                "frame": StepPolicy(route_id="cheap-default"),
            },
        )

        self.assertIsInstance(policy.routes["cheap-default"], MappingProxyType)
        self.assertEqual(
            policy.to_json()["routes"],
            {
                "cheap-default": {
                    "provider": "openai",
                    "model": "gpt-5-mini",
                },
            },
        )

    def test_policy_rejects_non_v1_unit(self) -> None:
        with self.assertRaisesRegex(ValueError, "unit must be approx_token"):
            ExecutionPolicy(id="policy", unit="usd")

    def test_budget_rejects_zero_or_negative_values(self) -> None:
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must be positive"):
                    Budget(max_estimated_units=value)
                with self.assertRaisesRegex(ValueError, "must be positive"):
                    Budget(max_output_units=value)

    def test_policy_rejects_unknown_step_route(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown route"):
            ExecutionPolicy(
                id="policy",
                steps={"frame": StepPolicy(route_id="missing")},
                routes={},
            )

    def test_estimate_approx_units_is_deterministic_and_rough(self) -> None:
        self.assertEqual(estimate_approx_units(0), 0)
        self.assertEqual(estimate_approx_units(1), 1)
        self.assertEqual(estimate_approx_units(4), 1)
        self.assertEqual(estimate_approx_units(5), 2)

    def test_decision_allows_call_without_budget(self) -> None:
        result = decide_before_call(
            default_execution_policy(),
            default_policy_state(),
            step_id="frame",
            role_id="framer",
            input_chars=16,
        )

        self.assertEqual(result.decision.action, PolicyDecisionAction.ALLOW_CALL)
        self.assertEqual(result.decision.reason, "within budget")
        self.assertEqual(result.decision.estimated_input_units, 4)
        self.assertEqual(result.decision.reserved_output_units, 0)
        self.assertEqual(result.decision.estimated_total_units, 4)
        self.assertIsNone(result.decision.run_budget_remaining)
        self.assertIsNone(result.decision.step_budget_remaining)
        self.assertIsNone(result.decision.route_id)
        self.assertEqual(result.state.consumed_run_units, 4)
        self.assertEqual(result.state.consumed_step_units["frame"], 4)

    def test_decision_allows_call_with_sufficient_budget(self) -> None:
        policy = ExecutionPolicy(
            id="budgeted",
            run_budget=Budget(max_estimated_units=20),
            default_step_budget=Budget(
                max_estimated_units=12,
                max_output_units=3,
            ),
        )

        result = decide_before_call(
            policy,
            PolicyState(consumed_run_units=5, consumed_step_units={"frame": 2}),
            step_id="frame",
            input_chars=16,
        )

        self.assertEqual(result.decision.action, PolicyDecisionAction.ALLOW_CALL)
        self.assertEqual(result.decision.estimated_input_units, 4)
        self.assertEqual(result.decision.reserved_output_units, 3)
        self.assertEqual(result.decision.estimated_total_units, 7)
        self.assertEqual(result.decision.run_budget_remaining, 8)
        self.assertEqual(result.decision.step_budget_remaining, 3)
        self.assertEqual(result.state.consumed_run_units, 12)
        self.assertEqual(result.state.consumed_step_units["frame"], 9)

    def test_decision_cancels_run_when_run_budget_is_exceeded(self) -> None:
        policy = ExecutionPolicy(
            id="budgeted",
            run_budget=Budget(max_estimated_units=10),
            default_step_budget=Budget(max_output_units=3),
        )
        state = PolicyState(consumed_run_units=5)

        result = decide_before_call(
            policy,
            state,
            step_id="frame",
            input_chars=12,
        )

        self.assertEqual(result.decision.action, PolicyDecisionAction.CANCEL_RUN)
        self.assertEqual(result.decision.reason, "run budget exceeded")
        self.assertEqual(result.decision.estimated_total_units, 6)
        self.assertEqual(result.decision.run_budget_remaining, 0)
        self.assertIs(result.state, state)

    def test_decision_cancels_run_when_step_budget_is_exceeded(self) -> None:
        policy = ExecutionPolicy(
            id="budgeted",
            run_budget=Budget(max_estimated_units=100),
            default_step_budget=Budget(
                max_estimated_units=10,
                max_output_units=3,
            ),
        )
        state = PolicyState(consumed_run_units=5, consumed_step_units={"frame": 5})

        result = decide_before_call(
            policy,
            state,
            step_id="frame",
            input_chars=12,
        )

        self.assertEqual(result.decision.action, PolicyDecisionAction.CANCEL_RUN)
        self.assertEqual(result.decision.reason, "step budget exceeded")
        self.assertEqual(result.decision.run_budget_remaining, 89)
        self.assertEqual(result.decision.step_budget_remaining, 0)
        self.assertIs(result.state, state)

    def test_step_budget_overrides_default_step_budget(self) -> None:
        policy = ExecutionPolicy(
            id="budgeted",
            default_step_budget=Budget(
                max_estimated_units=5,
                max_output_units=1,
            ),
            steps={
                "final": StepPolicy(
                    budget=Budget(
                        max_estimated_units=20,
                        max_output_units=4,
                    ),
                ),
            },
        )

        result = decide_before_call(
            policy,
            default_policy_state(),
            step_id="final",
            input_chars=16,
        )

        self.assertEqual(result.decision.action, PolicyDecisionAction.ALLOW_CALL)
        self.assertEqual(result.decision.reserved_output_units, 4)
        self.assertEqual(result.decision.estimated_total_units, 8)
        self.assertEqual(result.decision.step_budget_remaining, 12)

    def test_step_route_id_is_used_in_decision(self) -> None:
        policy = ExecutionPolicy(
            id="routed",
            routes={"cheap-default": {"opaque": "route"}},
            steps={"frame": StepPolicy(route_id="cheap-default")},
        )

        result = decide_before_call(
            policy,
            default_policy_state(),
            step_id="frame",
            input_chars=4,
        )

        self.assertEqual(result.decision.route_id, "cheap-default")
        self.assertNotIn("provider", result.decision.to_json())
        self.assertNotIn("model", result.decision.to_json())

    def test_decision_estimation_is_stable(self) -> None:
        policy = ExecutionPolicy(
            id="budgeted",
            run_budget=Budget(max_estimated_units=100),
            default_step_budget=Budget(max_output_units=2),
        )
        first = decide_before_call(
            policy,
            default_policy_state(),
            step_id="frame",
            input_chars=17,
        ).decision
        second = decide_before_call(
            policy,
            default_policy_state(),
            step_id="frame",
            input_chars=17,
        ).decision

        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.estimated_input_units, 5)
        self.assertEqual(first.estimated_total_units, 7)

    def test_loads_policy_yaml(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: cheap-review\n"
                "mode: cheap\n"
                "unit: approx_token\n"
                "budget:\n"
                "  max_estimated_units: 3000\n"
                "  max_output_units: 800\n"
                "default_step_budget:\n"
                "  max_output_units: 300\n"
                "steps:\n"
                "  final:\n"
                "    max_estimated_units: 1200\n"
                "    max_output_units: 500\n"
                "    route_id: standard-synthesis\n"
                "routes:\n"
                "  cheap-default:\n"
                "    provider: openai\n"
                "    model: gpt-5-mini\n"
                "  standard-synthesis:\n"
                "    provider: openai\n"
                "    model: gpt-5\n"
            )
            handle.flush()

            policy = load_policy_yaml(handle.name)

        self.assertEqual(policy.id, "cheap-review")
        self.assertEqual(policy.mode, ExecutionMode.CHEAP)
        self.assertEqual(policy.run_budget, Budget(3000, 800))
        self.assertEqual(policy.default_step_budget, Budget(None, 300))
        self.assertEqual(policy.steps["final"].budget, Budget(1200, 500))
        self.assertEqual(policy.steps["final"].route_id, "standard-synthesis")
        self.assertEqual(
            policy.to_json()["routes"]["standard-synthesis"],
            {"provider": "openai", "model": "gpt-5"},
        )

    def test_load_policy_yaml_rejects_invalid_unit(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write("id: policy\nmode: standard\nunit: tokens\n")
            handle.flush()

            with self.assertRaisesRegex(PolicyLoadError, "approx_token"):
                load_policy_yaml(handle.name)

    def test_load_policy_yaml_rejects_unknown_mode(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write("id: policy\nmode: turbo\n")
            handle.flush()

            with self.assertRaisesRegex(PolicyLoadError, "unknown execution mode"):
                load_policy_yaml(handle.name)

    def test_load_policy_yaml_rejects_unknown_top_level_field(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write("id: policy\nmode: standard\nmagic: true\n")
            handle.flush()

            with self.assertRaisesRegex(PolicyLoadError, "unknown fields"):
                load_policy_yaml(handle.name)

    def test_load_policy_yaml_rejects_unknown_route_reference(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: policy\n"
                "mode: standard\n"
                "steps:\n"
                "  frame:\n"
                "    route_id: missing\n"
            )
            handle.flush()

            with self.assertRaisesRegex(PolicyLoadError, "unknown route"):
                load_policy_yaml(handle.name)

    def test_load_policy_yaml_rejects_missing_file(self) -> None:
        missing = Path("missing-policy.yaml")

        with self.assertRaisesRegex(PolicyLoadError, "policy file not found"):
            load_policy_yaml(missing)


if __name__ == "__main__":
    unittest.main()
