from __future__ import annotations

from copy import deepcopy
import json
import unittest

from delibra.app.puzzle_spec import (
    evaluate_puzzle_spec_payload,
    extract_puzzle_spec,
    validate_puzzle_spec,
)


VALID_SPEC = {
    "scope": "single_fixed_spot",
    "answer": "AUBEPINE",
    "validation_method": "Compare the assembled letter cards with the printed answer slot labelled REPONSE.",
    "player_separation_allowed": False,
    "materials": ["letter cards", "answer slot card", "hint envelope"],
    "forbidden_mechanisms": ["lock"],
}


class PuzzleSpecValidatorTests(unittest.TestCase):
    def test_extract_puzzle_spec_reads_strict_json_from_payload_content(self) -> None:
        result = extract_puzzle_spec({"content": json.dumps(VALID_SPEC)})

        self.assertTrue(result.extracted)
        self.assertEqual(result.document, VALID_SPEC)
        self.assertIsNone(result.error)

    def test_extract_puzzle_spec_rejects_non_object_payload(self) -> None:
        result = extract_puzzle_spec("not a payload")

        self.assertFalse(result.extracted)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, "EXTRACTION_PAYLOAD_NOT_OBJECT")
        self.assertEqual(result.error.field, "$")

    def test_extract_puzzle_spec_rejects_missing_content(self) -> None:
        result = extract_puzzle_spec({"text": json.dumps(VALID_SPEC)})

        self.assertFalse(result.extracted)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, "EXTRACTION_CONTENT_MISSING")
        self.assertEqual(result.error.field, "content")

    def test_extract_puzzle_spec_rejects_non_string_content(self) -> None:
        result = extract_puzzle_spec({"content": VALID_SPEC})

        self.assertFalse(result.extracted)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, "EXTRACTION_CONTENT_NOT_STRING")
        self.assertEqual(result.error.field, "content")

    def test_extract_puzzle_spec_rejects_invalid_json_content(self) -> None:
        result = extract_puzzle_spec({"content": "{"})

        self.assertFalse(result.extracted)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, "EXTRACTION_INVALID_JSON")
        self.assertEqual(result.error.field, "content")

    def test_evaluate_puzzle_spec_payload_reports_extraction_error(self) -> None:
        result = evaluate_puzzle_spec_payload({"content": "{"})

        self.assertEqual(result.status, "extraction_error")
        self.assertIsNotNone(result.extraction_error)
        assert result.extraction_error is not None
        self.assertEqual(result.extraction_error.code, "EXTRACTION_INVALID_JSON")
        self.assertIsNone(result.puzzle_spec_validation_report)
        self.assertIsNone(result.accepted_puzzle_spec)

    def test_evaluate_puzzle_spec_payload_reports_invalid_spec(self) -> None:
        result = evaluate_puzzle_spec_payload(
            {
                "content": json.dumps(
                    {
                        "scope": "single_fixed_spot",
                        "answer": "Find the order of the relics.",
                        "validation_method": "Compare the relic cards with the printed answer slot.",
                        "player_separation_allowed": False,
                        "materials": ["relic cards"],
                        "forbidden_mechanisms": ["lock"],
                    }
                )
            }
        )

        self.assertEqual(result.status, "invalid")
        self.assertIsNone(result.extraction_error)
        self.assertIsNotNone(result.puzzle_spec_validation_report)
        assert result.puzzle_spec_validation_report is not None
        self.assertFalse(result.puzzle_spec_validation_report.valid)
        self.assertEqual(
            [error.code for error in result.puzzle_spec_validation_report.errors],
            ["ANSWER_NOT_EXPLICIT"],
        )
        self.assertIsNone(result.accepted_puzzle_spec)

    def test_evaluate_puzzle_spec_payload_accepts_valid_spec(self) -> None:
        result = evaluate_puzzle_spec_payload({"content": json.dumps(VALID_SPEC)})

        self.assertEqual(result.status, "accepted")
        self.assertIsNone(result.extraction_error)
        self.assertIsNotNone(result.puzzle_spec_validation_report)
        assert result.puzzle_spec_validation_report is not None
        self.assertTrue(result.puzzle_spec_validation_report.valid)
        self.assertEqual(result.accepted_puzzle_spec, VALID_SPEC)

    def test_accepts_minimal_valid_puzzle_spec(self) -> None:
        result = validate_puzzle_spec(VALID_SPEC)

        self.assertTrue(result.valid)
        self.assertEqual(result.errors, ())

    def test_rejects_non_object_spec(self) -> None:
        result = validate_puzzle_spec("prose summary")

        self.assertFalse(result.valid)
        self.assertEqual([error.code for error in result.errors], ["PUZZLE_SPEC_NOT_OBJECT"])

    def test_validate_puzzle_spec_does_not_mutate_input(self) -> None:
        spec = {
            "scope": "castle_wide_hunt",
            "answer": "Find the order of the relics.",
            "validation_method": "The secret door opens.",
            "player_separation_allowed": True,
            "materials": [],
            "forbidden_mechanisms": [],
            "nested": {"description": ["Relics are scattered throughout the castle."]},
        }
        original = deepcopy(spec)

        validate_puzzle_spec(spec)

        self.assertEqual(spec, original)

    def test_validation_errors_have_stable_order(self) -> None:
        result = validate_puzzle_spec(
            {
                "scope": "castle_wide_hunt",
                "answer": "Find the order of the relics.",
                "validation_method": "The secret door opens.",
                "player_separation_allowed": True,
                "materials": [],
                "forbidden_mechanisms": [],
                "description": "Relics are scattered throughout the castle.",
            }
        )

        self.assertEqual(
            [error.code for error in result.errors],
            [
                "SCOPE_NOT_SINGLE_FIXED_SPOT",
                "ANSWER_NOT_EXPLICIT",
                "VALIDATION_METHOD_NOT_BUILDABLE",
                "PLAYER_SEPARATION_ALLOWED",
                "MATERIALS_EMPTY",
                "FORBIDDEN_MECHANISM_MISSING",
                "DISQUALIFYING_SCOPE_PATTERN",
                "DISQUALIFYING_VALIDATION_PATTERN",
            ],
        )

    def test_returns_all_detectable_violations(self) -> None:
        result = validate_puzzle_spec(
            {
                "scope": "castle_wide_hunt",
                "answer": "Find the order of the relics and escape the castle.",
                "validation_method": "The secret door opens automatically.",
                "player_separation_allowed": True,
                "materials": [],
                "forbidden_mechanisms": [],
                "notes": "The relics are scattered throughout the castle.",
            }
        )

        self.assertFalse(result.valid)
        self.assertEqual(
            {error.code for error in result.errors},
            {
                "SCOPE_NOT_SINGLE_FIXED_SPOT",
                "ANSWER_NOT_EXPLICIT",
                "VALIDATION_METHOD_NOT_BUILDABLE",
                "PLAYER_SEPARATION_ALLOWED",
                "MATERIALS_EMPTY",
                "FORBIDDEN_MECHANISM_MISSING",
                "DISQUALIFYING_SCOPE_PATTERN",
                "DISQUALIFYING_VALIDATION_PATTERN",
            },
        )

    def test_rejects_ollama_002_style_reliquary_order_answer(self) -> None:
        result = validate_puzzle_spec(
            {
                "scope": "single_fixed_spot",
                "answer": "Trouver l'ordre des reliquaires qui permet de découvrir une solution finale.",
                "validation_method": "Certains reliquaires doivent être placés dans un certain ordre.",
                "player_separation_allowed": False,
                "materials": ["reliquaires en carton"],
                "forbidden_mechanisms": ["cadenas"],
                "description": "Les reliquaires sont dispersés à travers le château.",
            }
        )

        self.assertFalse(result.valid)
        self.assertIn("ANSWER_NOT_EXPLICIT", {error.code for error in result.errors})
        self.assertIn("DISQUALIFYING_SCOPE_PATTERN", {error.code for error in result.errors})

    def test_rejects_ollama_003_style_relics_and_main_door_answer(self) -> None:
        result = validate_puzzle_spec(
            {
                "scope": "single_fixed_spot",
                "answer": "The relics in hand and the main door of the castle opened.",
                "validation_method": "The main door opens when the six relics are assembled before it.",
                "player_separation_allowed": False,
                "materials": ["book of hours", "map", "relic cards"],
                "forbidden_mechanisms": ["lock"],
                "description": "The group must gather six relics hidden throughout the castle.",
            }
        )

        self.assertFalse(result.valid)
        self.assertIn("ANSWER_NOT_EXPLICIT", {error.code for error in result.errors})
        self.assertIn("VALIDATION_METHOD_NOT_BUILDABLE", {error.code for error in result.errors})
        self.assertIn("DISQUALIFYING_SCOPE_PATTERN", {error.code for error in result.errors})

    def test_rejects_ollama_004_style_false_pass(self) -> None:
        result = validate_puzzle_spec(
            {
                "scope": "single_fixed_spot",
                "answer": "Escape the castle by unlocking the secret door with the correct key word.",
                "validation_method": "Players can open the secret door when they input the correct key word.",
                "player_separation_allowed": False,
                "materials": ["castle map", "six candles", "six unique tokens", "clue sheet"],
                "forbidden_mechanisms": ["lock"],
                "why_single_puzzle": "Six players collaborate to solve a series of puzzles.",
            }
        )

        self.assertFalse(result.valid)
        self.assertIn("ANSWER_NOT_EXPLICIT", {error.code for error in result.errors})
        self.assertIn("VALIDATION_METHOD_NOT_BUILDABLE", {error.code for error in result.errors})
        self.assertIn("DISQUALIFYING_SCOPE_PATTERN", {error.code for error in result.errors})


if __name__ == "__main__":
    unittest.main()
