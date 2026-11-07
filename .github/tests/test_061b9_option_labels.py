"""Current device option names, actual-mode suffixes and explanatory help.

Loads the production catalogs without Home Assistant. The caller supplies
already-qualified modes; these display helpers must not invent capability.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
NAMES = runpy.run_path(str(ROOT / "equipment_name_catalog.py"))
HELP = runpy.run_path(str(ROOT / "equipment_help.py"))
MODES = runpy.run_path(str(ROOT / "operating_mode_catalog.py"))
name = NAMES["localized_equipment_name"]
label = NAMES["native_full_output_label"]
help_text = HELP["equipment_configuration_help"]
mode_label = MODES["operating_mode_label"]
KEYS = ("announce_device_errors", "sleep_when_everyone_asleep", "native_full_output")
QUICK = (*KEYS, "pause_on_window_open", "announce_before_start",
         "quiet_sleep", "quiet_occupied", "sensor_verified")


def short(key, language):
    full = name(key, language)
    return (full.partition(" · ")[2] or full).rstrip(" ·")


class OptionLabelTests(unittest.TestCase):
    def test_exact_requested_titles_and_all38_explicit_translations(self):
        self.assertEqual(short("announce_device_errors", "en"), "Announce device errors")
        self.assertEqual(short("sleep_when_everyone_asleep", "en"), "Keep device off when all asleep")
        self.assertEqual(label((), "en"), "Maximum target by mode")
        self.assertEqual(label((), "el"), "Μέγιστος στόχος ανά λειτουργία")
        self.assertEqual(short("announce_device_errors", "el"), "Ανακοίνωση σφαλμάτων συσκευής")
        paths = sorted((ROOT / "translations").glob("*.json"))
        self.assertEqual(len(paths), 38)
        self.assertEqual(set(path.stem for path in paths), set(NAMES["EQUIPMENT_TRANSLATED_NAMES"]))
        for path in [ROOT / "strings.json", *paths]:
            locale = "en" if path.name == "strings.json" else path.stem
            data = json.loads(path.read_text())
            with self.subTest(locale=locale):
                for key in KEYS:
                    translated = data["entity"]["switch"]["equipment_" + key]["name"]
                    self.assertEqual(translated, NAMES["EQUIPMENT_TRANSLATED_NAMES"][locale][key])
                    self.assertEqual(translated.replace("{channel}", "").strip(), name(key, locale))
                    self.assertTrue(short(key, locale))
                    if locale != "en":
                        self.assertNotEqual(short(key, locale), short(key, "en"), key)
                self.assertEqual(short("native_full_output", locale), label((), locale))

    def test_mode_suffix_uses_only_supplied_modes_and_each_locale(self):
        order = ("heat", "cool", "dry", "humidify")
        for locale in NAMES["EQUIPMENT_TRANSLATED_NAMES"]:
            with self.subTest(locale=locale):
                expected = ", ".join(mode_label(mode, locale) for mode in order)
                mixed = ("humidify", "dry", "fan_only", "cool", "heat", "dry", "off", "auto", "invented")
                self.assertEqual(label(mixed, locale), f"{label((), locale)} ({expected})")
                for mode in order:
                    self.assertEqual(label((mode, mode), locale), f"{label((), locale)} ({mode_label(mode, locale)})")
                self.assertEqual(label(("auto", "fan_only", "off", "invented"), locale), label((), locale))

    def test_language_variants_share_the_correct_catalog(self):
        for variant, canonical in (("el-GR", "el"), ("de_DE", "de"), ("pt_br", "pt-BR"),
                                   ("zh_hant", "zh-Hant"), ("en-US", "en"), ("unknown", "en")):
            self.assertEqual(label(("dry",), variant), label(("dry",), canonical))

    def test_dynamic_help_explains_only_this_devices_supported_endpoints(self):
        for locale in ("en", "el", "de"):
            for selected in (("heat",), ("cool",), ("dry",), ("humidify",), ("heat", "cool")):
                with self.subTest(locale=locale, modes=selected):
                    paragraphs = help_text("native_full_output", locale, modes=selected).split("\n\n")
                    for mode in ("heat", "cool", "dry", "humidify"):
                        descriptions = [part for part in paragraphs if part.startswith(mode_label(mode, locale) + ":")]
                        self.assertEqual(len(descriptions), int(mode in selected))
                    self.assertGreater(len(paragraphs), 4)
        endpoints = {
            "heat": "highest temperature", "cool": "lowest temperature",
            "dry": "lowest relative-humidity target", "humidify": "highest relative-humidity target",
        }
        for mode, expected in endpoints.items():
            self.assertIn(expected, help_text("native_full_output", modes=(mode,)))
        self.assertIn("no verified operating mode", help_text("native_full_output", modes=("fan_only",)))

    def test_each_quick_control_explains_on_off_and_its_scope(self):
        for key in QUICK:
            for locale, on, off in (("en", "On", "Off"), ("el", "Ενεργό", "Ανενεργό"),
                                    ("de", "Eingeschaltet", "Ausgeschaltet")):
                with self.subTest(key=key, locale=locale):
                    text = help_text(key, locale)
                    paragraphs = text.split("\n\n")
                    self.assertTrue(any(part.startswith(on) for part in paragraphs))
                    self.assertTrue(any(part.startswith(off) for part in paragraphs))
                    self.assertGreaterEqual(len(paragraphs), 3)
                    self.assertGreater(len(text), 300)
        self.assertIn("Other devices keep their own", help_text("announce_device_errors"))
        self.assertIn("one minute", help_text("pause_on_window_open"))
        self.assertIn("CO₂", help_text("announce_before_start"))
        self.assertIn("covered cause", help_text("announce_before_start"))
        self.assertIn("speed ceiling", help_text("quiet_sleep"))
        self.assertIn("does not raise a lower stage", help_text("quiet_occupied"))
        self.assertIn("room's PM2.5 source may still", help_text("sensor_verified"))

    def test_pid_attempts_and_actual_feedback_are_distinct_from_power_authority(self):
        text = help_text("native_full_output", modes=("dry",))
        for expected in ("three total dispatch attempts", "including the first", "one minute for feedback",
                         "third remains unconfirmed", "guarded ON/OFF control", "cycles and restarts",
                         "offline checks do not spend attempts", "actually reported targets",
                         "real device feedback", "Automatic retains its existing retry policy"):
            self.assertIn(expected, text)
        self.assertIn("leave the device's native target unchanged", text)

    def test_household_sleep_is_an_off_rule_with_verified_conditions(self):
        text = help_text("sleep_when_everyone_asleep")
        for expected in ("Automatic or PID", "keep this device off", "at least one room is occupied",
                         "every occupied room", "minimum ON time", "actual OFF feedback",
                         "Home or Comfort preset", "empty home", "confirmed Away", "unknown",
                         "wake-alarm lead", "remove only this device's extra household sleep hold"):
            self.assertIn(expected, text)
        self.assertNotIn("also apply this device's sleep behavior, Sleep targets", text)

    def test_native_operating_duration_names_use_minutes_in_all38_languages(self):
        timing_keys = ("min_on_seconds", "min_off_seconds", "max_on_seconds")
        minute_units = {
            "min", "λεπτά", "Min.", "perc", "мин", "хв", "dk", "دقيقة", "דקות",
            "دقیقه", "मिनट", "মিনিট", "நிமிடம்", "منٹ", "menit", "分", "분",
            "นาที", "phút", "分钟", "分鐘",
        }
        self.assertEqual(name("min_on_seconds", "en"), "Operation · Minimum device ON time (min)")
        self.assertEqual(name("min_off_seconds", "en"), "Operation · Minimum device OFF time (min)")
        self.assertEqual(name("max_on_seconds", "en"), "Power · Maximum ON time (min)")
        for path in [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]:
            locale = "en" if path.name == "strings.json" else path.stem
            entries = json.loads(path.read_text())["entity"]["number"]
            for key in timing_keys:
                with self.subTest(locale=locale, key=key):
                    translated = entries["equipment_" + key]["name"]
                    self.assertEqual(translated, NAMES["EQUIPMENT_TRANSLATED_NAMES"][locale][key])
                    unit = translated.rsplit(" (", 1)[-1].removesuffix(")")
                    self.assertIn(unit, minute_units)
                    if locale == "el":
                        self.assertEqual(unit, "λεπτά")
                    if locale == "de":
                        self.assertEqual(unit, "Min.")
        for key in ("sample_seconds", "cycle_seconds", "power_switch_cooldown_seconds"):
            self.assertTrue(name(key, "en").endswith(("(s)", "(seconds)")), key)

    def test_minute_help_preserves_fractional_minima_and_physical_safeguards(self):
        for key in ("min_on_seconds", "min_off_seconds", "max_on_seconds"):
            for locale, minutes, seconds in (("en", "minutes", "seconds"),
                                             ("el", "λεπτά", "δευτερόλεπτα"),
                                             ("de", "Minuten", "Sekunden")):
                with self.subTest(key=key, locale=locale):
                    text = help_text(key, locale)
                    self.assertIn(minutes, text)
                    self.assertNotIn(seconds, text)
        for key in ("min_on_seconds", "min_off_seconds"):
            text = help_text(key)
            self.assertIn("Fractional minutes are allowed", text)
            self.assertIn("0.5 for half a minute", text)
            self.assertIn("waits for command confirmation", text)
            self.assertIn("does not change the external power-switch timing", text)
        self.assertIn("Set 0 to disable", help_text("min_on_seconds"))
        self.assertIn("current cycle completes first", help_text("min_on_seconds"))
        self.assertIn("0 disables", help_text("min_off_seconds"))
        self.assertIn("observed OFF time", help_text("min_off_seconds"))
        self.assertIn("must exceed the minimum ON time", help_text("max_on_seconds"))
        self.assertIn("defrost protection", help_text("max_on_seconds"))

    def test_retired_timing_option_has_no_current_name_help_or_translation(self):
        self.assertNotIn("timed_setpoint_sequence", HELP["HELP"])
        self.assertNotIn("_TIMED_SETPOINT_LABELS", NAMES)
        for names in NAMES["EQUIPMENT_TRANSLATED_NAMES"].values():
            self.assertNotIn("timed_setpoint_sequence", names)
        for path in [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]:
            data = json.loads(path.read_text())
            for entries in data.get("entity", {}).values():
                self.assertNotIn("equipment_timed_setpoint_sequence", entries, str(path))
        for key in QUICK:
            for locale in ("en", "el", "de"):
                self.assertNotIn("30", help_text(key, locale))


if __name__ == "__main__":
    unittest.main(verbosity=2)
