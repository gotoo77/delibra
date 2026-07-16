from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from delibra.app.inputs import input_from_file, input_from_json, input_from_text
from delibra.app.presets import PresetError, list_presets, load_preset, resolve_preset_path


ROOT = Path(__file__).resolve().parents[1]


class AppInputsPresetsTests(unittest.TestCase):
    def test_input_from_text_uses_text_shape(self) -> None:
        self.assertEqual(
            input_from_text("Review this change."),
            {"kind": "text", "content": "Review this change."},
        )

    def test_input_from_file_reads_utf8_text_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text("Décision à revoir", encoding="utf-8")

            self.assertEqual(
                input_from_file(path),
                {"kind": "text", "content": "Décision à revoir"},
            )

    def test_input_from_json_preserves_object_shape(self) -> None:
        raw = json.dumps(
            {
                "kind": "custom",
                "items": [1, {"nested": True}],
                "metadata": {"source": "test"},
            }
        )

        self.assertEqual(
            input_from_json(raw),
            {
                "kind": "custom",
                "items": [1, {"nested": True}],
                "metadata": {"source": "test"},
            },
        )

    def test_input_from_json_rejects_non_object(self) -> None:
        with self.assertRaisesRegex(TypeError, "input JSON must be a JSON object"):
            input_from_json("[1, 2, 3]")

    def test_list_presets_includes_local_yaml_protocols(self) -> None:
        names = {preset.name for preset in list_presets(ROOT / "presets")}

        self.assertIn("code_review", names)
        self.assertIn("puzzle_design", names)
        self.assertIn("treasure_hunt_design_selection", names)

    def test_resolve_preset_rejects_path_traversal(self) -> None:
        with self.assertRaisesRegex(PresetError, "invalid preset name"):
            resolve_preset_path("../tests/fixtures/rfc_protocol", ROOT / "presets")

    def test_resolve_preset_fails_clearly_for_unknown_name(self) -> None:
        with self.assertRaisesRegex(PresetError, "preset not found: missing"):
            resolve_preset_path("missing", ROOT / "presets")

    def test_versioned_filename_preset_can_be_loaded_by_stem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            preset_dir = Path(tmp)
            (preset_dir / "example-0.2.0.yaml").write_text(
                """id: example
version: 0.2.0
description: Versioned filename preset.

roles:
  framer:
    name: Framer
    instruction: Frame the input.
  synthesizer:
    name: Synthesizer
    instruction: Synthesize the result.

steps:
  - id: frame
    kind: prompt
    role: framer
    roles: null
    instruction: Frame the submitted input.
    inputs:
      - user_input
    produces:
      output: framing
      kind: framing
  - id: final
    kind: synthesize
    role: synthesizer
    roles: null
    instruction: Synthesize the final answer.
    inputs:
      - framing
    produces:
      output: final_synthesis
      kind: synthesis
""",
                encoding="utf-8",
            )

            protocol = load_preset("example-0.2.0", preset_dir)

        self.assertEqual(protocol.id, "example")
        self.assertEqual(protocol.version, "0.2.0")


if __name__ == "__main__":
    unittest.main()
