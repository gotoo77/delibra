from __future__ import annotations

from copy import deepcopy
import unittest

from delibra.app.puzzle_spec import validate_puzzle_spec


VALID_SPEC = {
    "scope": "single_fixed_spot",
    "answer": "AUBEPINE",
    "validation_method": "Compare the assembled letter cards with the printed answer slot labelled REPONSE.",
    "player_separation_allowed": False,
    "materials": ["letter cards", "answer slot card", "hint envelope"],
    "forbidden_mechanisms": ["lock"],
}


class PuzzleSpecValidatorTests(unittest.TestCase):
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
