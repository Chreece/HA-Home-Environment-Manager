"""Backend language coverage and real lookups without a Home Assistant process.

Run with --runtime-only while authoring translation batches. The default run is
a complete coverage gate: missing locales, placeholder damage and prose copied
from English fail even when a helper could silently fall back.
"""
from __future__ import annotations

import ast
import builtins
from hashlib import sha256
import importlib
import json
from pathlib import Path
import string
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
if not SOURCE.is_dir():
    SOURCE = ROOT
PACKAGE = "hem_b8_language_tests"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package
RUNTIME_ONLY = "--runtime-only" in sys.argv
if RUNTIME_ONLY:
    sys.argv.remove("--runtime-only")

def load(name):
    return importlib.import_module(PACKAGE + "." + name)

languages = load("languages")
text = load("backend_text")
equipment = load("equipment_help")
settings = load("settings_help")
names = load("settings_name_catalog")
mode = load("operating_mode_catalog")
commands = load("equipment_resume")
options = load("setting_option_explanations")
notices = load("off_state_profiles")
watchdog = load("off_state_watchdog")
doors = load("equipment_door_policy")
messages = load("messages")
device_names = load("equipment_name_catalog")
pid_names = load("room_pid_name_catalog")

def placeholders(value):
    return sorted({(key, spec, conversion) for _, key, spec, conversion in string.Formatter().parse(value)
                   if key is not None})

class BackendLanguageTests(unittest.TestCase):
    def test_generated_catalog_size_stays_close_to_source(self):
        # Long source paragraphs must not become Python indentation: that can
        # multiply package size and the work needed at Home Assistant startup.
        catalog_size = (SOURCE / "backend_text_catalog.py").stat().st_size
        source_size = (ROOT / ".github/localization/backend_help.json").stat().st_size
        self.assertLessEqual(catalog_size, 2 * source_size + 65_536)

    def test_existing_values_keep_placeholders_and_numeric_formats(self):
        for english, variants in text.TEXT.items():
            for locale, value in variants.items():
                self.assertTrue(value.strip(), (english, locale))
                self.assertEqual(placeholders(value), placeholders(english), (english, locale))

    @unittest.skipIf(RUNTIME_ONLY, "Translation authoring: full coverage is checked by the default run")
    def test_every_bundled_message_has_every_supported_locale(self):
        supported = set(languages.SUPPORTED_LANGUAGE_TAGS)
        failures = []
        for english, variants in text.TEXT.items():
            missing = supported - variants.keys()
            if missing:
                failures.append((english[:100], sorted(missing)))
            self.assertEqual(variants.get("en"), english)
            for locale, value in variants.items():
                self.assertTrue(value.strip(), (english, locale))
                self.assertEqual(placeholders(value), placeholders(english), (english, locale))
                if locale != "en" and len(english.split()) >= 8:
                    self.assertNotEqual(value, english, (english, locale))
        self.assertFalse(failures, json.dumps(failures, ensure_ascii=False, indent=2))

    def test_all_real_help_sources_are_registered(self):
        expected = {value[0] for value in equipment.HELP.values()}
        expected.update(value["en"] for value in settings.SETTING_HELP.values())
        expected.update(values[0] for group in options.OPTION_TEXT.values() for values in group.values())
        self.assertFalse(expected - text.TEXT.keys())

    def test_mode_target_help_uses_localized_units_and_separate_profile_values(self):
        tree = ast.parse((SOURCE / "equipment_mode_entities.py").read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ("target_field", "scoped_help")]
        profiles = next(ast.literal_eval(node.value) for node in tree.body
                        if isinstance(node, ast.Assign) and any(
                            isinstance(target, ast.Name) and target.id == "TARGET_PROFILES"
                            for target in node.targets))
        scope = {"TARGET_PROFILES": profiles, "mode_locale": mode.mode_locale,
                 "translated_text": text.translated_text}
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     str(SOURCE / "equipment_mode_entities.py"), "exec"), scope)
        composed = json.loads((ROOT / ".github/localization/backend_composed_help.json").read_text())
        english = {key: scope["scoped_help"](key, "en", equipment.equipment_configuration_help(key, "en"))
                   for key in ("target_home_heat", "target_home_humidity")}
        self.assertIn("profiles keep separate values", english["target_home_humidity"])
        self.assertIn("Automatic/PID dehumidification", english["target_home_humidity"])
        self.assertIn("surface relative humidity", english["target_home_humidity"])
        self.assertIn("room relative humidity", english["target_home_humidity"])
        self.assertIn("after conversion", english["target_home_humidity"])
        self.assertNotIn("mold", english["target_home_heat"].lower())
        for key, source in english.items():
            self.assertEqual(set(composed[source]), set(languages.SUPPORTED_LANGUAGE_TAGS))
            for locale in languages.SUPPORTED_LANGUAGE_TAGS:
                with self.subTest(key=key, locale=locale):
                    actual = scope["scoped_help"](key, locale, equipment.equipment_configuration_help(key, locale))
                    self.assertEqual(actual, composed[source][locale])
                    self.assertNotIn(equipment.equipment_configuration_help("future_setting", locale), actual)
                    if locale != "en":
                        for clause in source.splitlines():
                            self.assertNotIn(clause, actual)

    def test_reviewed_help_replaces_legacy_generic_form_prose(self):
        rejected = json.loads((ROOT / ".github/localization/backend_rejected_generic_help.json").read_text())
        for key, variants in settings.SETTING_HELP.items():
            english = variants["en"]
            if english not in rejected:
                continue
            for locale, legacy in rejected[english].items():
                actual = settings.configuration_help(key, locale)
                self.assertNotEqual(actual, legacy, (key, locale))
                self.assertEqual(actual, text.TEXT[english][locale], (key, locale))
        # Existing generic form text must not override a corrected exact source.
        source = next(iter(rejected))
        legacy = rejected[source]["fr"]
        self.assertEqual(text.translated_variants({"en": source, "fr": legacy})["fr"],
                         text.TEXT[source]["fr"])

    @unittest.skipIf(RUNTIME_ONLY, "Translation authoring: full coverage is checked by the default run")
    def test_real_help_lookups_do_not_fall_back_to_english(self):
        # A complete data file is insufficient if a production helper still
        # selects only its original three language slots.
        failures = []
        for locale in languages.SUPPORTED_LANGUAGE_TAGS:
            if locale == "en":
                continue
            for key in (*equipment.HELP, "future_setting"):
                if equipment.equipment_configuration_help(key, locale) == equipment.equipment_configuration_help(key, "en"):
                    failures.append(("equipment", key, locale))
            for key in settings.SETTING_HELP:
                if settings.configuration_help(key, locale) == settings.configuration_help(key, "en"):
                    failures.append(("settings", key, locale))
            for key in options.OPTION_TEXT:
                choices = options.option_help_locales(key, locale)
                self.assertEqual(set(choices[locale]), set(choices["en"]))
                for option, english in choices["en"].items():
                    if choices[locale][option] == english:
                        failures.append(("option", key, option, locale))
            for supported_modes in ((), ("heat", "cool", "dry", "humidify")):
                translated = equipment.equipment_configuration_help("native_full_output", locale, modes=supported_modes)
                english = equipment.equipment_configuration_help("native_full_output", "en", modes=supported_modes)
                self.assertNotEqual(translated, english, ("native_full_output", supported_modes, locale))
                self.assertNotIn("{mode}", translated)
        self.assertFalse(failures, json.dumps(failures, ensure_ascii=False, indent=2))

    def test_window_titles_use_window_open_close_semantics(self):
        for locale, pack in languages.EXTRA_LOCALES.items():
            ui = pack["ui"]
            self.assertEqual(messages.TEXT[locale]["title_open"], f"{ui[7]} - {ui[13]} {ui[11]}")
            self.assertEqual(messages.TEXT[locale]["title_close"], f"{ui[7]} - {ui[14]} {ui[11]}")
            self.assertNotIn(ui[15], messages.TEXT[locale]["title_close"])

    def test_aliases_keep_script_region_and_norwegian_meaning(self):
        for alias, canonical in (("zh-TW", "zh-Hant"), ("zh-CN", "zh-Hans"),
                                 ("zh_Hant_HK", "zh-Hant"), ("pt_BR", "pt-BR"),
                                 ("no", "nb"), ("fr-CA", "fr")):
            self.assertEqual(names.setting_locale(alias), canonical)
            self.assertEqual(mode.mode_locale(alias), canonical)
            self.assertEqual(device_names.localized_equipment_name("pid_review_approve", alias),
                             device_names.localized_equipment_name("pid_review_approve", canonical))
            self.assertEqual(pid_names.localized_room_pid_name("area_pid_gain_source", alias),
                             pid_names.localized_room_pid_name("area_pid_gain_source", canonical))

    def test_setting_names_do_not_expose_placeholders_or_english_prefixes(self):
        for locale in languages.SUPPORTED_LANGUAGE_TAGS:
            self.assertNotIn("PID_OFFSET_C", names.localized_setting_name("area_pid_offset_c", locale))
            self.assertNotIn("NO VENT", names.localized_setting_name("home_global_environment_pollen_avoid_ventilation", locale))
            self.assertNotIn("UNOCCUPIED_DELAY", names.localized_setting_name("area_climate_operating_unoccupied_delay_minutes", locale))
            self.assertNotIn("CLIMATE_MANUAL_PROFILE", names.localized_setting_name("area_manual_profile", locale))
            if locale != "en":
                self.assertNotIn("Target speed", names.localized_setting_name("area_device_target_fan_speed_percent", locale))
                self.assertNotIn("Vacancy delay", names.localized_setting_name("area_climate_operating_unoccupied_delay_minutes", locale))
                self.assertNotIn("Override", names.localized_setting_name("area_manual_profile", locale))
            if locale not in ("en", "el", "de"):
                self.assertNotEqual(names.localized_setting_name("global_threshold_mode_max_age_mode", locale),
                                    names.localized_setting_name("global_threshold_mode_max_age_mode", "en"))
                self.assertNotIn("PID · Gains ·", pid_names.localized_room_pid_name("area_pid_gain_source", locale))

    def test_runtime_command_feedback_localizes_labels_without_changing_values(self):
        current = SimpleNamespace(state="heat", attributes={"temperature":22, "temperature_unit":"°C"})
        expected = {"attributes":{"temperature":23}}
        for locale in ("el", "de", "fr", "ar", "ja", "zh-Hant"):
            desired, observed = commands._command_feedback(expected, current, language=locale)
            self.assertIn("23", desired)
            self.assertIn("22", observed)
            self.assertIn("°C", desired)
            self.assertNotIn("Temperature setpoint", desired)
        self.assertEqual(current.state, "heat")
        self.assertEqual(current.attributes["temperature"], 22)
        self.assertEqual(expected, {"attributes":{"temperature":23}})

    def test_option_language_payload_is_bounded_and_keeps_english(self):
        all_values = options.option_help_locales("equipment_control_mode")
        self.assertEqual(set(all_values), set(languages.SUPPORTED_LANGUAGE_TAGS))
        selected = options.option_help_locales("equipment_control_mode", "ja")
        self.assertEqual(set(selected), {"en", "el", "de", "ja"})
        self.assertEqual(selected["en"], all_values["en"])
        self.assertEqual(set(selected["ja"]), set(selected["en"]))

    def test_door_option_translation_keeps_native_select_values(self):
        # Execute unchanged production classes against the HA state boundary.
        tree = ast.parse((SOURCE / "door_entities.py").read_text())
        body = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "WORDS" for target in node.targets
            ):
                body.append(node)
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Subscript):
                    if isinstance(call.func.value.value, ast.Name) and call.func.value.value.id == "WORDS":
                        body.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name == "words":
                body.append(node)
            elif isinstance(node, ast.ClassDef) and node.name in ("DoorEntity", "DoorSelect"):
                body.append(node)
        scope = {"__name__": PACKAGE + ".door_probe", "__package__": PACKAGE,
                 "EntityCategory": SimpleNamespace(CONFIG="config"), "SelectEntity": object,
                 "callback": lambda fn: fn, "sha256": sha256, "DOMAIN": "environment_manager",
                 "complete_catalog": text.complete_catalog, "resolve_language": languages.resolve_language,
                 "presentation_languages": text.presentation_languages}
        exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE / "door_entities.py"), "exec"), scope)
        manager = SimpleNamespace(entry=SimpleNamespace(entry_id="entry"),
            hass=SimpleNamespace(config=SimpleNamespace(language="fr"),
                                 states={"binary_sensor.door":SimpleNamespace(name="Hall door")}))
        entity = scope["DoorSelect"](manager, "room", "binary_sensor.door", "kind")
        values = set(entity.options)
        attributes = entity.extra_state_attributes
        self.assertEqual(values, {"Intérieure", "Extérieure", "Porte coupe-feu ou de sécurité"})
        self.assertEqual(set(attributes["option_labels_locales"]["en"]), values)
        self.assertEqual(set(attributes["option_labels_locales"]["en"].values()),
                         {"Interior", "Exterior", "Fire/safety door"})
        self.assertEqual(set(attributes["option_help_locales"]["en"]), values)

    def test_lookup_performs_no_file_or_network_work(self):
        # All imported catalogs above are already loaded, like integration setup.
        with patch.object(builtins, "open", side_effect=AssertionError("runtime file read")), \
             patch.object(Path, "read_text", side_effect=AssertionError("runtime file read")):
            for locale in ("en", "fr", "ja", "ar"):
                self.assertTrue(equipment.equipment_configuration_help("control_mode", locale))
                self.assertTrue(settings.configuration_help("global_threshold_mode_max_age_mode", locale))
                self.assertTrue(doors.words(locale)["coord_help"])
                title, body = notices.notice("heat", locale, "suspected", name="Unit", room="Room",
                                             first=20, current=23, target=21)
                self.assertIn("Unit", body)
                self.assertTrue(title)

if __name__ == "__main__":
    unittest.main()
