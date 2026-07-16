from __future__ import annotations

import unittest

from delibra.runtime import (
    RequestedLanguage,
    ResolvedLanguage,
    RunLanguage,
    detect_language,
    detect_language_result,
    language_instruction,
)


class RuntimeLanguageTests(unittest.TestCase):
    def test_explicit_french_resolves_to_french(self) -> None:
        language = RunLanguage.resolve(
            RequestedLanguage.FR,
            {"kind": "text", "content": "Review this change."},
        )

        self.assertEqual(language.to_json(), {"requested": "fr", "resolved": "fr"})

    def test_explicit_english_resolves_to_english(self) -> None:
        language = RunLanguage.resolve(
            RequestedLanguage.EN,
            {"kind": "text", "content": "Merci de relire cette decision."},
        )

        self.assertEqual(language.to_json(), {"requested": "en", "resolved": "en"})

    def test_auto_detects_french_input(self) -> None:
        examples = (
            "Bonjour, peux-tu analyser cette architecture ?",
            "Peux tu vérifier ce code et proposer une correction",
            "Analyse les risques de cette proposition",
            "Je voudrais comprendre comment fonctionne ce protocole",
        )

        for text in examples:
            with self.subTest(text=text):
                result = detect_language_result(text)
                self.assertEqual(result.resolved, ResolvedLanguage.FR)
                self.assertFalse(result.fallback)

    def test_auto_detects_english_input(self) -> None:
        examples = (
            "Hello, can you review this design?",
            "Can you analyze the risks of this proposal?",
            "I would like to understand how this protocol works",
        )

        for text in examples:
            with self.subTest(text=text):
                result = detect_language_result(text)
                self.assertEqual(result.resolved, ResolvedLanguage.EN)
                self.assertFalse(result.fallback)

    def test_auto_falls_back_to_english_for_short_ambiguous_code_or_technical_input(self) -> None:
        examples = (
            "Bonjour world",
            "fn main() { println!(\"hello\"); }",
            "OK",
            "architecture protocol runtime",
        )

        for text in examples:
            with self.subTest(text=text):
                result = detect_language_result(text)
                self.assertEqual(result.resolved, ResolvedLanguage.EN)
                self.assertTrue(result.fallback)

    def test_auto_resolution_is_deterministic(self) -> None:
        text = "Peux tu vérifier ce code et proposer une correction"

        self.assertEqual(
            [detect_language(text) for _ in range(5)],
            [ResolvedLanguage.FR] * 5,
        )

    def test_run_language_auto_keeps_requested_and_detected_resolved_values(self) -> None:
        language = RunLanguage.resolve(
            "auto",
            {"kind": "text", "content": "Bonjour, peux-tu analyser cette architecture ?"},
        )

        self.assertEqual(language.requested, RequestedLanguage.AUTO)
        self.assertEqual(language.resolved, ResolvedLanguage.FR)

    def test_language_instruction_uses_resolved_language_only(self) -> None:
        self.assertEqual(
            language_instruction(ResolvedLanguage.FR),
            "Produce all generated artifact content in French.",
        )
        self.assertEqual(
            language_instruction(ResolvedLanguage.EN),
            "Produce all generated artifact content in English.",
        )

    def test_invalid_requested_language_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported language: de"):
            RunLanguage.resolve("de", {"kind": "text", "content": "Hallo"})


if __name__ == "__main__":
    unittest.main()
