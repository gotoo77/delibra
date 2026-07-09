from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from delibra.core import Produces, Protocol, Role, StepDefinition, StepKind
from delibra.protocol_validator import ProtocolValidationError, validate_protocol


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rfc_protocol.yaml"


def make_protocol(*steps: StepDefinition) -> Protocol:
    return Protocol(
        id="code_review",
        version="0.1.0",
        description="Structured code review protocol.",
        roles={
            "framer": Role("framer", "Framer", "Frame input."),
            "maintainer": Role("maintainer", "Maintainer", "Review maintenance."),
            "tester": Role("tester", "Tester", "Review tests."),
            "security": Role("security", "Security", "Review security."),
            "synthesizer": Role("synthesizer", "Synthesizer", "Synthesize."),
        },
        steps=steps or valid_steps(),
    )


def valid_steps() -> tuple[StepDefinition, ...]:
    return (
        StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=None,
            instruction="Frame the input.",
            inputs=("user_input",),
            produces=Produces(output="framing", kind="framing"),
        ),
        StepDefinition(
            id="reviews",
            kind=StepKind.FANOUT,
            role=None,
            roles=("maintainer", "tester", "security"),
            instruction="Review the framing.",
            inputs=("framing",),
            produces=Produces(output="reviews", kind="review"),
        ),
        StepDefinition(
            id="final",
            kind=StepKind.SYNTHESIZE,
            role="synthesizer",
            roles=None,
            instruction="Synthesize the reviews.",
            inputs=("framing", "reviews"),
            produces=Produces(output="final_synthesis", kind="synthesis"),
        ),
    )


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    return subprocess.run(
        [sys.executable, "-m", "delibra", *args],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class ProtocolValidatorTests(unittest.TestCase):
    def test_valid_protocol_passes(self) -> None:
        validate_protocol(make_protocol())

    def test_protocol_id_and_version_must_be_non_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "id must be non-empty"):
            Protocol(
                id="",
                version="0.1.0",
                description="Structured code review protocol.",
                roles={"framer": Role("framer", "Framer", "Frame input.")},
                steps=valid_steps(),
            )
        with self.assertRaisesRegex(ValueError, "version must be non-empty"):
            Protocol(
                id="code_review",
                version="",
                description="Structured code review protocol.",
                roles={"framer": Role("framer", "Framer", "Frame input.")},
                steps=valid_steps(),
            )

    def test_roles_and_steps_must_be_non_empty(self) -> None:
        with self.assertRaisesRegex(ProtocolValidationError, "roles must be non-empty"):
            validate_protocol(
                Protocol(
                    id="code_review",
                    version="0.1.0",
                    description="Structured code review protocol.",
                    roles={},
                    steps=valid_steps(),
                )
            )
        with self.assertRaisesRegex(ProtocolValidationError, "steps must be non-empty"):
            validate_protocol(
                Protocol(
                    id="code_review",
                    version="0.1.0",
                    description="Structured code review protocol.",
                    roles={"framer": Role("framer", "Framer", "Frame input.")},
                    steps=(),
                )
            )

    def test_role_map_key_must_match_role_id(self) -> None:
        protocol = Protocol(
            id="code_review",
            version="0.1.0",
            description="Structured code review protocol.",
            roles={"framer": Role("other", "Framer", "Frame input.")},
            steps=valid_steps(),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "must match role id"):
            validate_protocol(protocol)

    def test_duplicate_step_ids_fail(self) -> None:
        first, _, final = valid_steps()
        duplicate = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=None,
            instruction="Frame again.",
            inputs=("user_input",),
            produces=Produces(output="framing_again", kind="framing"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "duplicate step id"):
            validate_protocol(make_protocol(first, duplicate, final))

    def test_duplicate_produces_output_values_fail(self) -> None:
        first, _, final = valid_steps()
        duplicate = StepDefinition(
            id="reviews",
            kind=StepKind.FANOUT,
            role=None,
            roles=("maintainer",),
            instruction="Review.",
            inputs=("framing",),
            produces=Produces(output="framing", kind="review"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "duplicate produces.output"):
            validate_protocol(make_protocol(first, duplicate, final))

    def test_user_input_reserved_output_fails_validation(self) -> None:
        step = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=None,
            instruction="Frame.",
            inputs=("user_input",),
            produces=Produces(output="user_input", kind="framing"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "reserved input id"):
            validate_protocol(make_protocol(step))

    def test_unknown_input_output_fails(self) -> None:
        step = StepDefinition(
            id="reviews",
            kind=StepKind.FANOUT,
            role=None,
            roles=("maintainer",),
            instruction="Review.",
            inputs=("missing_output",),
            produces=Produces(output="reviews", kind="review"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "unavailable output"):
            validate_protocol(make_protocol(step))

    def test_future_input_output_fails(self) -> None:
        first, reviews, final = valid_steps()
        bad_first = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=None,
            instruction="Frame the input.",
            inputs=("reviews",),
            produces=Produces(output="framing", kind="framing"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "unavailable output"):
            validate_protocol(make_protocol(bad_first, reviews, final))

    def test_missing_role_reference_fails(self) -> None:
        step = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="missing",
            roles=None,
            instruction="Frame.",
            inputs=("user_input",),
            produces=Produces(output="framing", kind="framing"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "unknown role"):
            validate_protocol(make_protocol(step))

    def test_instruction_and_produces_fields_must_be_present(self) -> None:
        with self.assertRaisesRegex(ProtocolValidationError, "instruction is required"):
            validate_protocol(
                make_protocol(
                    StepDefinition(
                        id="frame",
                        kind=StepKind.PROMPT,
                        role="framer",
                        roles=None,
                        instruction="",
                        inputs=("user_input",),
                        produces=Produces(output="framing", kind="framing"),
                    )
                )
            )
        with self.assertRaisesRegex(ValueError, "output must be non-empty"):
            Produces(output="", kind="framing")
        with self.assertRaisesRegex(ProtocolValidationError, "produces.kind"):
            validate_protocol(
                make_protocol(
                    StepDefinition(
                        id="frame",
                        kind=StepKind.PROMPT,
                        role="framer",
                        roles=None,
                        instruction="Frame.",
                        inputs=("user_input",),
                        produces=Produces(output="framing", kind=""),
                    )
                )
            )

    def test_prompt_with_roles_fails(self) -> None:
        step = StepDefinition(
            id="frame",
            kind=StepKind.PROMPT,
            role="framer",
            roles=("maintainer",),
            instruction="Frame.",
            inputs=("user_input",),
            produces=Produces(output="framing", kind="framing"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "forbids roles"):
            validate_protocol(make_protocol(step))

    def test_fanout_without_roles_fails(self) -> None:
        first, _, final = valid_steps()
        step = StepDefinition(
            id="reviews",
            kind=StepKind.FANOUT,
            role=None,
            roles=(),
            instruction="Review.",
            inputs=("framing",),
            produces=Produces(output="reviews", kind="review"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "requires non-empty roles"):
            validate_protocol(make_protocol(first, step, final))

    def test_fanout_with_role_fails(self) -> None:
        first, _, final = valid_steps()
        step = StepDefinition(
            id="reviews",
            kind=StepKind.FANOUT,
            role="maintainer",
            roles=("tester",),
            instruction="Review.",
            inputs=("framing",),
            produces=Produces(output="reviews", kind="review"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "forbids role"):
            validate_protocol(make_protocol(first, step, final))

    def test_criticize_with_role_fails(self) -> None:
        first, _, final = valid_steps()
        step = StepDefinition(
            id="critiques",
            kind=StepKind.CRITICIZE,
            role="maintainer",
            roles=("tester",),
            instruction="Criticize.",
            inputs=("framing",),
            produces=Produces(output="critiques", kind="critique"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "forbids role"):
            validate_protocol(make_protocol(first, step, final))

    def test_criticize_without_roles_fails(self) -> None:
        first, _, final = valid_steps()
        step = StepDefinition(
            id="critiques",
            kind=StepKind.CRITICIZE,
            role=None,
            roles=(),
            instruction="Criticize.",
            inputs=("framing",),
            produces=Produces(output="critiques", kind="critique"),
        )

        with self.assertRaisesRegex(ProtocolValidationError, "requires non-empty roles"):
            validate_protocol(make_protocol(first, step, final))

    def test_synthesize_not_last_fails(self) -> None:
        first, reviews, final = valid_steps()

        with self.assertRaisesRegex(ProtocolValidationError, "synthesize step must be final"):
            validate_protocol(make_protocol(first, final, reviews))

    def test_unknown_primitive_fails_during_parse(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: code_review\n"
                "version: 0.1.0\n"
                "description: Structured code review protocol.\n"
                "roles:\n"
                "  framer:\n"
                "    name: Framer\n"
                "    instruction: Frame.\n"
                "steps:\n"
                "  - id: frame\n"
                "    kind: branch\n"
                "    role: framer\n"
                "    roles: null\n"
                "    instruction: Frame.\n"
                "    inputs: [user_input]\n"
                "    produces:\n"
                "      output: framing\n"
                "      kind: framing\n"
            )
            handle.flush()

            result = run_cli("validate", "--protocol", handle.name)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown step kind", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_validate_runs_parsing_and_validation(self) -> None:
        result = run_cli("validate", "--protocol", str(FIXTURE))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["id"], "code_review")
        self.assertEqual(result.stderr, "")

    def test_cli_validate_reports_validation_errors_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml") as handle:
            handle.write(
                "id: code_review\n"
                "version: 0.1.0\n"
                "description: Structured code review protocol.\n"
                "roles:\n"
                "  framer:\n"
                "    name: Framer\n"
                "    instruction: Frame.\n"
                "steps: []\n"
            )
            handle.flush()

            result = run_cli("validate", "--protocol", handle.name)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid protocol", result.stderr)
        self.assertIn("steps must be non-empty", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
