"""B17: all HEM locale contracts and card/device settings separation.

No HA runtime, third-party dependencies, physical hardware or service writes.
The browser B13/B7 suites separately validate real DOM and service operations.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "custom_components" / "environment_manager"
CARD = (SRC / "frontend" / "air-quality-advisor-card.js").read_text(encoding="utf-8")
WINDOW = runpy.run_path(str(SRC / "window_option_catalog.py"))["WINDOW_OPTION_LABELS"]
TRANSLATIONS = SRC / "translations"
STRINGS = json.loads((SRC / "strings.json").read_text(encoding="utf-8"))
EN = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))


class DeviceMenuLocalizationTests(unittest.TestCase):
    def test_all_38_translated_window_purpose_labels_match_backend_and_card(self):
        paths = sorted(TRANSLATIONS.glob("*.json"))
        self.assertEqual(len(paths), 38)
        self.assertEqual(set(WINDOW), {path.stem for path in paths})
        for path in paths:
            with self.subTest(language=path.stem):
                document = json.loads(path.read_text(encoding="utf-8"))
                native = document["entity"]["switch"]["equipment_announce_before_start"]["name"]
                expected = WINDOW[path.stem][0]
                self.assertTrue(native.endswith(expected), (path.stem, native, expected))
                self.assertIn(expected, CARD, f"Card lacks {path.stem} prompt")
                self.assertTrue(expected and "Ask to open windows" not in expected)
        self.assertTrue(
            STRINGS["entity"]["switch"]["equipment_announce_before_start"]["name"]
            .endswith(WINDOW["en"][0])
        )
        self.assertEqual(
            WINDOW["el"][0],
            "Προτροπή ανοίγματος παραθύρων για αποφυγή χρήσης αυτής της συσκευής",
        )

    def test_every_translated_select_retains_all_canonical_option_keys(self):
        english = EN["entity"]["select"]
        missing = []
        for path in sorted(TRANSLATIONS.glob("*.json")):
            translated = json.loads(path.read_text(encoding="utf-8"))["entity"]["select"]
            for entity, reference in english.items():
                if entity not in translated:
                    missing.append((path.stem, entity, "<missing select>"))
                    continue
                for option in reference.get("state", {}):
                    if not translated[entity].get("state", {}).get(option):
                        missing.append((path.stem, entity, option))
        self.assertFalse(missing, f"Missing localized select options: {missing[:40]} ({len(missing)} total)")

    def test_compact_card_and_categorized_device_dialog_contract(self):
        self.assertIn("const modeControls=this._operatingModeControls7(entry,room.area_id,true);", CARD)
        self.assertIn("const details=!methodsOnly && panel.parameters.length?", CARD)
        self.assertIn('<div class="hem-device-category-anchor129"', CARD)
        self.assertIn('data-hem-full-list127', CARD)
        self.assertIn('this._hemFullOptionLabel129(field,option)', CARD)
        self.assertIn("data-hem-full-category127", CARD)
        self.assertIn('option=input.value;', CARD)
        self.assertIn("HEM_FULL_GROUP_LOCALES129", CARD)
        for path in TRANSLATIONS.glob("*.json"):
            language = path.stem.lower()
            if language not in ("en", "el", "de"):
                self.assertIn('"' + language + '":', CARD)
        # The exact real app still resolves configuration metadata by setting
        # key, so mode-specific PID gains are not misclassified as Modes.
        self.assertIn('const name=String(meta.setting_key||field.kind||"").toLowerCase();', CARD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
