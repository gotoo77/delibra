from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PuzzleSpecValidationError:
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class PuzzleSpecValidationResult:
    valid: bool
    errors: tuple[PuzzleSpecValidationError, ...]


@dataclass(frozen=True)
class PuzzleSpecExtractionError:
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class PuzzleSpecExtractionResult:
    extracted: bool
    document: object | None = None
    error: PuzzleSpecExtractionError | None = None


@dataclass(frozen=True)
class PuzzleSpecPayloadEvaluation:
    status: str
    extraction_error: PuzzleSpecExtractionError | None = None
    puzzle_spec_validation_report: PuzzleSpecValidationResult | None = None
    accepted_puzzle_spec: dict[str, Any] | None = None


_ANSWER_GOAL_PATTERNS = (
    "ouvrir",
    "open",
    "unlock",
    "s echapper",
    "escape",
    "trouver",
    "find",
    "discover",
    "decouvrir",
    "bonne combinaison",
    "correct combination",
    "solution correcte",
    "correct solution",
    "right order",
    "ordre correct",
    "find the order",
    "trouver l ordre",
    "door opens",
    "porte ouverte",
    "relics in hand",
    "reliques en main",
)

_UNBUILDABLE_VALIDATION_PATTERNS = (
    "secret door",
    "porte secrete",
    "porte principale",
    "main door",
    "opens automatically",
    "s ouvre automatiquement",
    "automatic",
    "automatique",
    "hidden mechanism",
    "mecanisme cache",
    "hidden electronics",
    "electronique cachee",
    "sensor",
    "capteur",
    "unlock",
    "deverrou",
)

_SCOPE_DISQUALIFYING_PATTERNS = (
    "series of puzzles",
    "serie d enigmes",
    "plusieurs enigmes",
    "throughout the castle",
    "dans tout le chateau",
    "castle wide",
    "recherche dans le chateau",
    "scattered",
    "dispers",
    "hidden informant",
    "informateur secret",
    "relics hidden",
    "reliques cachees",
    "several reliquaries",
    "plusieurs reliquaires",
    "multi room",
    "plusieurs salles",
    "progression through",
)


def extract_puzzle_spec(payload: object) -> PuzzleSpecExtractionResult:
    if not isinstance(payload, dict):
        return PuzzleSpecExtractionResult(
            extracted=False,
            error=PuzzleSpecExtractionError(
                code="EXTRACTION_PAYLOAD_NOT_OBJECT",
                field="$",
                message="Payload must be a JSON object containing a content field.",
            ),
        )
    if "content" not in payload:
        return PuzzleSpecExtractionResult(
            extracted=False,
            error=PuzzleSpecExtractionError(
                code="EXTRACTION_CONTENT_MISSING",
                field="content",
                message="Payload must contain a content field.",
            ),
        )
    content = payload["content"]
    if not isinstance(content, str):
        return PuzzleSpecExtractionResult(
            extracted=False,
            error=PuzzleSpecExtractionError(
                code="EXTRACTION_CONTENT_NOT_STRING",
                field="content",
                message="Payload content must be a string containing strict JSON.",
            ),
        )
    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        return PuzzleSpecExtractionResult(
            extracted=False,
            error=PuzzleSpecExtractionError(
                code="EXTRACTION_INVALID_JSON",
                field="content",
                message=f"Payload content is not valid JSON: {exc.msg}.",
            ),
        )
    return PuzzleSpecExtractionResult(extracted=True, document=document)


def evaluate_puzzle_spec_payload(payload: object) -> PuzzleSpecPayloadEvaluation:
    extraction = extract_puzzle_spec(payload)
    if not extraction.extracted:
        return PuzzleSpecPayloadEvaluation(
            status="extraction_error",
            extraction_error=extraction.error,
        )

    validation = validate_puzzle_spec(extraction.document)
    if not validation.valid:
        return PuzzleSpecPayloadEvaluation(
            status="invalid",
            puzzle_spec_validation_report=validation,
        )

    assert isinstance(extraction.document, dict)
    return PuzzleSpecPayloadEvaluation(
        status="accepted",
        puzzle_spec_validation_report=validation,
        accepted_puzzle_spec=extraction.document,
    )


def validate_puzzle_spec(spec: object) -> PuzzleSpecValidationResult:
    errors: list[PuzzleSpecValidationError] = []
    if not isinstance(spec, dict):
        return PuzzleSpecValidationResult(
            valid=False,
            errors=(
                PuzzleSpecValidationError(
                    code="PUZZLE_SPEC_NOT_OBJECT",
                    field="$",
                    message="Puzzle spec must be a JSON object.",
                ),
            ),
        )

    scope = spec.get("scope")
    if scope != "single_fixed_spot":
        errors.append(
            PuzzleSpecValidationError(
                code="SCOPE_NOT_SINGLE_FIXED_SPOT",
                field="scope",
                message='Puzzle scope must be exactly "single_fixed_spot".',
            )
        )

    answer = spec.get("answer")
    if not _non_empty_string(answer):
        errors.append(
            PuzzleSpecValidationError(
                code="ANSWER_MISSING",
                field="answer",
                message="The answer must be a non-empty string.",
            )
        )
    elif _contains_any(answer, _ANSWER_GOAL_PATTERNS):
        errors.append(
            PuzzleSpecValidationError(
                code="ANSWER_NOT_EXPLICIT",
                field="answer",
                message="The answer must identify the exact expected solution, not a goal state.",
            )
        )

    validation_method = spec.get("validation_method")
    if not _non_empty_string(validation_method):
        errors.append(
            PuzzleSpecValidationError(
                code="VALIDATION_METHOD_MISSING",
                field="validation_method",
                message="The validation method must be a non-empty string.",
            )
        )
    elif _contains_any(validation_method, _UNBUILDABLE_VALIDATION_PATTERNS):
        errors.append(
            PuzzleSpecValidationError(
                code="VALIDATION_METHOD_NOT_BUILDABLE",
                field="validation_method",
                message="The validation method must be physically buildable from listed materials.",
            )
        )

    if spec.get("player_separation_allowed") is not False:
        errors.append(
            PuzzleSpecValidationError(
                code="PLAYER_SEPARATION_ALLOWED",
                field="player_separation_allowed",
                message="Players must not be allowed or required to separate.",
            )
        )

    materials = spec.get("materials")
    if not _non_empty_string_list(materials):
        errors.append(
            PuzzleSpecValidationError(
                code="MATERIALS_EMPTY",
                field="materials",
                message="Materials must be a non-empty list of strings.",
            )
        )

    forbidden = spec.get("forbidden_mechanisms")
    if not _contains_mechanism(forbidden, ("lock", "cadenas")):
        errors.append(
            PuzzleSpecValidationError(
                code="FORBIDDEN_MECHANISM_MISSING",
                field="forbidden_mechanisms",
                message='The forbidden mechanism "lock" must be declared.',
            )
        )

    combined_text = _stringify_text(spec)
    if _contains_any(combined_text, _SCOPE_DISQUALIFYING_PATTERNS):
        errors.append(
            PuzzleSpecValidationError(
                code="DISQUALIFYING_SCOPE_PATTERN",
                field="$",
                message="Puzzle spec contains language suggesting a hunt, sequence, or multi-location game.",
            )
        )
    if _contains_any(combined_text, _UNBUILDABLE_VALIDATION_PATTERNS):
        errors.append(
            PuzzleSpecValidationError(
                code="DISQUALIFYING_VALIDATION_PATTERN",
                field="$",
                message="Puzzle spec contains language suggesting an unsupported validation mechanism.",
            )
        )

    return PuzzleSpecValidationResult(valid=not errors, errors=tuple(errors))


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _non_empty_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(item, str) and item.strip() != "" for item in value)
    )


def _contains_mechanism(value: object, mechanisms: tuple[str, ...]) -> bool:
    if not isinstance(value, list):
        return False
    normalized = [_normalize(item) for item in value if isinstance(item, str)]
    return any(
        mechanism in item
        for item in normalized
        for mechanism in mechanisms
    )


def _contains_any(value: object, patterns: tuple[str, ...]) -> bool:
    text = _normalize(value) if isinstance(value, str) else _normalize(_stringify_text(value))
    return any(pattern in text for pattern in patterns)


def _stringify_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_stringify_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_stringify_text(item) for item in value)
    return ""


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(ascii_text.lower().replace("'", " ").split())
