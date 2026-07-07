from __future__ import annotations

import unittest
from types import MappingProxyType

from delibra.core import Produces, Protocol, Role, StepDefinition, StepKind


ROLE_JSON = {
    "id": "framer",
    "name": "Framer",
    "instruction": "Restate scope and missing context.",
}

PRODUCES_JSON = {
    "output": "framing",
    "kind": "framing",
}

STEP_DEFINITION_JSON = {
    "id": "frame",
    "kind": "prompt",
    "role": "framer",
    "roles": None,
    "instruction": "Frame the input.",
    "inputs": ["user_input"],
    "produces": PRODUCES_JSON,
}

FANOUT_STEP_DEFINITION_JSON = {
    "id": "role_reviews",
    "kind": "fanout",
    "role": None,
    "roles": ["maintainer", "tester", "security"],
    "instruction": "Review the framed input.",
    "inputs": ["framing"],
    "produces": {
        "output": "reviews",
        "kind": "review",
    },
}

PROTOCOL_JSON = {
    "id": "code_review",
    "version": "0.1.0",
    "description": "Structured code review protocol.",
    "roles": {
        "framer": ROLE_JSON,
    },
    "steps": [
        STEP_DEFINITION_JSON,
    ],
}


class StaticProtocolModelTests(unittest.TestCase):
    def test_role_serializes_to_canonical_json(self) -> None:
        role = Role(
            id="framer",
            name="Framer",
            instruction="Restate scope and missing context.",
        )

        self.assertEqual(role.to_json(), ROLE_JSON)

    def test_role_deserializes_from_canonical_json(self) -> None:
        role = Role.from_json(ROLE_JSON)

        self.assertEqual(role.to_json(), ROLE_JSON)

    def test_role_constructor_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be non-empty"):
            Role(id="", name="Framer", instruction="Restate scope.")
        with self.assertRaisesRegex(TypeError, "name must be a string"):
            Role(id="framer", name=None, instruction="Restate scope.")
        with self.assertRaisesRegex(TypeError, "instruction must be a string"):
            Role(id="framer", name="Framer", instruction=None)

    def test_produces_serializes_to_canonical_json(self) -> None:
        produces = Produces(output="framing", kind="framing")

        self.assertEqual(produces.to_json(), PRODUCES_JSON)

    def test_produces_deserializes_from_canonical_json(self) -> None:
        produces = Produces.from_json(PRODUCES_JSON)

        self.assertEqual(produces.to_json(), PRODUCES_JSON)

    def test_produces_constructor_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "output must be non-empty"):
            Produces(output="", kind="framing")
        with self.assertRaisesRegex(TypeError, "kind must be a string"):
            Produces(output="framing", kind=None)

    def test_step_definition_serializes_to_canonical_json(self) -> None:
        step = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=None,
            instruction="Frame the input.",
            inputs=("user_input",),
            produces=Produces(output="framing", kind="framing"),
        )

        self.assertEqual(step.to_json(), STEP_DEFINITION_JSON)

    def test_step_definition_deserializes_from_canonical_json(self) -> None:
        step = StepDefinition.from_json(STEP_DEFINITION_JSON)

        self.assertEqual(step.kind, StepKind.PROMPT)
        self.assertEqual(step.to_json(), STEP_DEFINITION_JSON)

    def test_step_definition_constructor_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be non-empty"):
            StepDefinition(
                id="",
                kind=StepKind.PROMPT,
                role="framer",
                roles=None,
                instruction="Frame.",
                inputs=("user_input",),
                produces=Produces(output="framing", kind="framing"),
            )
        with self.assertRaisesRegex(TypeError, "role must be a string"):
            StepDefinition(
                id="frame",
                kind=StepKind.PROMPT,
                role=42,
                roles=None,
                instruction="Frame.",
                inputs=("user_input",),
                produces=Produces(output="framing", kind="framing"),
            )
        with self.assertRaisesRegex(TypeError, "instruction must be a string"):
            StepDefinition(
                id="frame",
                kind=StepKind.PROMPT,
                role="framer",
                roles=None,
                instruction=None,
                inputs=("user_input",),
                produces=Produces(output="framing", kind="framing"),
            )
        with self.assertRaisesRegex(TypeError, "produces must be a Produces"):
            StepDefinition(
                id="frame",
                kind=StepKind.PROMPT,
                role="framer",
                roles=None,
                instruction="Frame.",
                inputs=("user_input",),
                produces={"output": "framing", "kind": "framing"},
            )

    def test_step_definition_constructor_rejects_string_as_sequence(self) -> None:
        with self.assertRaisesRegex(TypeError, "inputs must be a list or tuple"):
            StepDefinition(
                id="frame",
                kind=StepKind.PROMPT,
                role="framer",
                roles=None,
                instruction="Frame.",
                inputs="user_input",
                produces=Produces(output="framing", kind="framing"),
            )
        with self.assertRaisesRegex(TypeError, "roles must be a list or tuple"):
            StepDefinition(
                id="reviews",
                kind=StepKind.FANOUT,
                role=None,
                roles="tester",
                instruction="Review.",
                inputs=("framing",),
                produces=Produces(output="reviews", kind="review"),
            )

    def test_step_definition_models_inputs_as_output_references(self) -> None:
        step = StepDefinition.from_json(FANOUT_STEP_DEFINITION_JSON)

        self.assertEqual(step.id, "role_reviews")
        self.assertEqual(step.inputs, ("framing",))
        self.assertEqual(step.produces.output, "reviews")
        self.assertNotEqual(step.id, step.produces.output)
        self.assertEqual(step.to_json(), FANOUT_STEP_DEFINITION_JSON)

    def test_protocol_serializes_to_canonical_json(self) -> None:
        protocol = Protocol(
            id="code_review",
            version="0.1.0",
            description="Structured code review protocol.",
            roles={
                "framer": Role(
                    id="framer",
                    name="Framer",
                    instruction="Restate scope and missing context.",
                )
            },
            steps=(
                StepDefinition(
                    id="frame",
                    kind=StepKind.PROMPT,
                    role="framer",
                    roles=None,
                    instruction="Frame the input.",
                    inputs=("user_input",),
                    produces=Produces(output="framing", kind="framing"),
                ),
            ),
        )

        self.assertEqual(protocol.to_json(), PROTOCOL_JSON)

    def test_protocol_deserializes_from_canonical_json(self) -> None:
        protocol = Protocol.from_json(PROTOCOL_JSON)

        self.assertIsInstance(protocol.roles, MappingProxyType)
        self.assertEqual(protocol.to_json(), PROTOCOL_JSON)

    def test_protocol_constructor_rejects_invalid_values(self) -> None:
        step = StepDefinition.from_json(STEP_DEFINITION_JSON)
        role = Role.from_json(ROLE_JSON)

        with self.assertRaisesRegex(ValueError, "id must be non-empty"):
            Protocol(
                id="",
                version="0.1.0",
                description="Structured code review protocol.",
                roles={"framer": role},
                steps=(step,),
            )
        with self.assertRaisesRegex(ValueError, "version must be non-empty"):
            Protocol(
                id="code_review",
                version="",
                description="Structured code review protocol.",
                roles={"framer": role},
                steps=(step,),
            )
        with self.assertRaisesRegex(TypeError, "description must be a string"):
            Protocol(
                id="code_review",
                version="0.1.0",
                description=None,
                roles={"framer": role},
                steps=(step,),
            )
        with self.assertRaisesRegex(TypeError, "roles must be a mapping"):
            Protocol(
                id="code_review",
                version="0.1.0",
                description="Structured code review protocol.",
                roles=[role],
                steps=(step,),
            )
        with self.assertRaisesRegex(TypeError, "steps must be a list or tuple"):
            Protocol(
                id="code_review",
                version="0.1.0",
                description="Structured code review protocol.",
                roles={"framer": role},
                steps="frame",
            )

    def test_step_kind_parses_valid_values(self) -> None:
        self.assertEqual(StepKind.parse("prompt"), StepKind.PROMPT)
        self.assertEqual(StepKind.parse("fanout"), StepKind.FANOUT)
        self.assertEqual(StepKind.parse("criticize"), StepKind.CRITICIZE)
        self.assertEqual(StepKind.parse("synthesize"), StepKind.SYNTHESIZE)

    def test_step_kind_rejects_invalid_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown step kind"):
            StepKind.parse("branch")

    def test_produces_kind_is_structural_not_domain_enum(self) -> None:
        produces = Produces.from_json(
            {
                "output": "legal_reviews",
                "kind": "review",
            }
        )

        self.assertEqual(produces.kind, "review")

    def test_unknown_fields_are_rejected(self) -> None:
        step_json = {
            **STEP_DEFINITION_JSON,
            "depends_on": ["frame"],
        }

        with self.assertRaisesRegex(ValueError, "unknown fields"):
            StepDefinition.from_json(step_json)


if __name__ == "__main__":
    unittest.main()
