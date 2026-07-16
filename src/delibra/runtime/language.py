from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from delibra.core.json import JsonMutableObject


SUPPORTED_REQUESTED_LANGUAGE_VALUES = ("auto", "fr", "en")
SUPPORTED_RESOLVED_LANGUAGE_VALUES = ("fr", "en")


class RequestedLanguage(str, Enum):
    AUTO = "auto"
    FR = "fr"
    EN = "en"

    @classmethod
    def parse(cls, value: str) -> "RequestedLanguage":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unsupported language: {value}") from exc


class ResolvedLanguage(str, Enum):
    FR = "fr"
    EN = "en"

    @classmethod
    def parse(cls, value: str) -> "ResolvedLanguage":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unsupported resolved language: {value}") from exc


@dataclass(frozen=True)
class RunLanguage:
    requested: RequestedLanguage
    resolved: ResolvedLanguage

    @classmethod
    def resolve(
        cls,
        requested: RequestedLanguage | str = RequestedLanguage.AUTO,
        input_ref: JsonMutableObject | None = None,
    ) -> "RunLanguage":
        requested = _coerce_requested_language(requested)
        if requested is RequestedLanguage.FR:
            return cls(requested=requested, resolved=ResolvedLanguage.FR)
        if requested is RequestedLanguage.EN:
            return cls(requested=requested, resolved=ResolvedLanguage.EN)
        return cls(
            requested=requested,
            resolved=detect_language_from_input(input_ref or {}),
        )

    @classmethod
    def from_json(cls, data: JsonMutableObject) -> "RunLanguage":
        return cls(
            requested=RequestedLanguage.parse(_require_string(data, "requested")),
            resolved=ResolvedLanguage.parse(_require_string(data, "resolved")),
        )

    def to_json(self) -> JsonMutableObject:
        return {
            "requested": self.requested.value,
            "resolved": self.resolved.value,
        }


@dataclass(frozen=True)
class LanguageDetection:
    resolved: ResolvedLanguage
    fallback: bool


def detect_language_from_input(input_ref: JsonMutableObject) -> ResolvedLanguage:
    text = _input_text(input_ref)
    return detect_language(text)


def detect_language(text: str) -> ResolvedLanguage:
    return detect_language_result(text).resolved


def detect_language_result(text: str) -> LanguageDetection:
    normalized = text.lower()
    if len(normalized.strip()) < 12:
        return LanguageDetection(resolved=ResolvedLanguage.EN, fallback=True)

    words = re.findall(r"[a-zàâçéèêëîïôûùüÿñæœ']+", normalized)
    if len(words) < 3:
        return LanguageDetection(resolved=ResolvedLanguage.EN, fallback=True)

    code_markers = sum(
        normalized.count(marker)
        for marker in ("{", "}", ";", "=>", "def ", "class ", "function ", "fn ")
    )
    if code_markers >= max(3, len(words) // 2):
        return LanguageDetection(resolved=ResolvedLanguage.EN, fallback=True)

    fr_score = _language_score(words, normalized, _FR_MARKERS, _FR_PATTERNS)
    en_score = _language_score(words, normalized, _EN_MARKERS, _EN_PATTERNS)
    if fr_score >= 3 and fr_score >= en_score + 2:
        return LanguageDetection(resolved=ResolvedLanguage.FR, fallback=False)
    if en_score >= 3 and en_score >= fr_score + 2:
        return LanguageDetection(resolved=ResolvedLanguage.EN, fallback=False)
    if _has_french_diacritic(normalized) and fr_score >= 2 and fr_score > en_score:
        return LanguageDetection(resolved=ResolvedLanguage.FR, fallback=False)
    return LanguageDetection(resolved=ResolvedLanguage.EN, fallback=True)


def language_instruction(language: ResolvedLanguage | str) -> str:
    language = _coerce_resolved_language(language)
    label = "French" if language is ResolvedLanguage.FR else "English"
    return f"Produce all generated artifact content in {label}."


def _input_text(input_ref: JsonMutableObject) -> str:
    content = input_ref.get("content")
    if isinstance(content, str):
        return content
    text = input_ref.get("text")
    if isinstance(text, str):
        return text
    return _collect_strings(input_ref)


def _collect_strings(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_collect_strings(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_collect_strings(item) for item in value)
    return ""


def _language_score(
    words: list[str],
    text: str,
    markers: set[str],
    patterns: tuple[str, ...],
) -> int:
    score = sum(1 for word in words if word in markers)
    score += sum(1 for pattern in patterns if pattern in text)
    return score


def _has_french_diacritic(text: str) -> bool:
    return any(character in text for character in "àâçéèêëîïôûùüÿæœ")


def _coerce_requested_language(value: RequestedLanguage | str) -> RequestedLanguage:
    if isinstance(value, RequestedLanguage):
        return value
    return RequestedLanguage.parse(value)


def _coerce_resolved_language(value: ResolvedLanguage | str) -> ResolvedLanguage:
    if isinstance(value, ResolvedLanguage):
        return value
    return ResolvedLanguage.parse(value)


def _require_string(data: JsonMutableObject, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise TypeError(f"language.{key} must be a string")
    return value


_FR_MARKERS = {
    "a",
    "afin",
    "analyse",
    "analyser",
    "avec",
    "bonjour",
    "ce",
    "cette",
    "ces",
    "code",
    "comment",
    "comprendre",
    "correction",
    "dans",
    "de",
    "decision",
    "décision",
    "des",
    "du",
    "elle",
    "en",
    "est",
    "et",
    "etre",
    "faire",
    "faut",
    "fonctionne",
    "il",
    "je",
    "la",
    "le",
    "les",
    "leur",
    "mais",
    "merci",
    "nous",
    "ou",
    "par",
    "pas",
    "peux",
    "pour",
    "proposer",
    "proposition",
    "protocole",
    "relire",
    "que",
    "qui",
    "risques",
    "sur",
    "tu",
    "une",
    "verifier",
    "vérifier",
    "vous",
    "voudrais",
}

_EN_MARKERS = {
    "a",
    "about",
    "analyze",
    "and",
    "are",
    "as",
    "be",
    "but",
    "by",
    "can",
    "design",
    "for",
    "from",
    "hello",
    "how",
    "i",
    "in",
    "is",
    "it",
    "like",
    "of",
    "on",
    "or",
    "proposal",
    "protocol",
    "review",
    "risks",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "understand",
    "we",
    "what",
    "works",
    "would",
    "with",
    "you",
}

_FR_PATTERNS = (
    "peux tu",
    "peux-tu",
    "est-ce",
    "qu'",
    "l'",
    "d'",
)

_EN_PATTERNS = (
    "can you",
    "would like",
    "how this",
)
