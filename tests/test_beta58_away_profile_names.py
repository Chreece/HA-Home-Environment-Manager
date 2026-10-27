"""Beta58: Away is absence, never a native appliance OFF command.

Regression tests validate all distributed HA locale catalogs and the original
room-profile configuration keys. No HA installation is required.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEYS = (
    "area_climate_profile_away_heat",
    "area_climate_profile_away_cool",
    "area_climate_profile_away_humidity",
)


class AwayProfileNames(unittest.TestCase):
    def test_away_number_names_exist_in_all_38_languages(self):
        files = sorted((ROOT / "translations").glob("*.json"))
        self.assertEqual(len(files), 38)
        for path in [ROOT / "strings.json", *files]:
            with self.subTest(locale=path.stem):
                catalog = json.loads(path.read_text(encoding="utf-8"))
                numbers = catalog["entity"]["number"]
                for key in KEYS:
                    self.assertIn(key, numbers)
                    title = numbers[key]["name"]
                    self.assertIn(" · ", title)
                    self.assertNotIn(" · Home · Off", title)
                    self.assertNotIn(" · Σπίτι · Απενεργοποίηση", title)
                    self.assertNotEqual(title, numbers[key.replace("away", "home")]["name"])
                    self.assertTrue(title.strip())

    def test_greek_away_labels_match_the_mode_selection(self):
        catalog = json.loads((ROOT / "translations/el.json").read_text())
        numbers = catalog["entity"]["number"]
        self.assertEqual(catalog["entity"]["select"]["area_manual_profile"]["state"]["away"],
                         "Απών")
        self.assertEqual(numbers["area_climate_profile_away_heat"]["name"],
                         "Θέρμανση · Απών")
        self.assertEqual(numbers["area_climate_profile_away_cool"]["name"],
                         "Ψύξη · Απών")
        self.assertEqual(numbers["area_climate_profile_away_humidity"]["name"],
                         "Υγρασία · Απών · στόχος (%)")
        self.assertEqual(numbers["area_climate_profile_home_heat"]["name"],
                         "Θέρμανση · Σπίτι")

    def test_english_away_does_not_imply_turning_device_off(self):
        for path in (ROOT / "strings.json", ROOT / "translations/en.json"):
            names=json.loads(path.read_text())["entity"]["number"]
            self.assertEqual(names["area_climate_profile_away_heat"]["name"],"Heating · Away")
            self.assertEqual(names["area_climate_profile_away_cool"]["name"],"Cooling · Away")
            self.assertEqual(names["area_climate_profile_away_humidity"]["name"],
                             "Humidity · Away · target (%)")

    def test_no_profile_key_numeric_target_or_entity_id_changed(self):
        source = (ROOT / "device_controls.py").read_text(encoding="utf-8")
        self.assertIn('"away": {"heat": 16.0, "cool": 30.0, "humidity": 50.0}',source)
        self.assertIn('ROOM_PROFILES = ("comfort", "home", "away", "sleep", "eco")',source)
        entity = (ROOT / "number.py").read_text(encoding="utf-8")
        self.assertIn('f"area_{kind}_{key}"',entity)
        self.assertIn('f"{entry_id}_area_{area_id}_{kind}_"',entity)

    def test_full_translation_json_and_flat_python_files_parse(self):
        for path in [ROOT/"strings.json",*(ROOT/"translations").glob("*.json")]:
            with self.subTest(file=path.name):
                json.loads(path.read_text(encoding="utf-8"))
        for path in ROOT.glob("*.py"):
            with self.subTest(file=path.name):
                ast.parse(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
