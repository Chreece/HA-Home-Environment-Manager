"""Cautioned airing speech and the real General/native timeout controls.

Uses the existing HA transport fixture while executing production forms,
settings writes, native-number properties and all spoken language templates.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import importlib
import importlib.util
import json
from pathlib import Path
from string import Formatter
from types import SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
fixture_spec = importlib.util.spec_from_file_location(
    "hem_window_text_settings_fixture",
    ROOT / ".github/tests/test_061b5_language_settings.py",
)
fixture = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixture)

const = fixture.const
logic = importlib.import_module(fixture.PKG + ".logic")
messages = importlib.import_module(fixture.PKG + ".messages")
text = importlib.import_module(fixture.PKG + ".window_open_text")
names = importlib.import_module(fixture.PKG + ".settings_name_catalog")
status_catalog = importlib.import_module(fixture.PKG + ".controller_status_catalog")
KEY = const.CONF_WINDOW_OPEN_TIMEOUT_MINUTES
NATIVE_KEY = "global_setting_" + KEY

fixture.production("device_controls.py", {"_finite"}, fixture.ns)
fixture.ns.update(NumberEntity=fixture.Entity, NumberMode=N(BOX="box"))
fixture.production("number.py", {"ConfigNumber"}, fixture.ns)
ConfigNumber = fixture.ns["ConfigNumber"]


def rec(**changes):
    original = logic.Recommendation(
        "open", "bathroom", "Badezimmer · μπάνιο",
        (logic.Window("binary_sensor.bathroom", "Badfenster", False),),
        (logic.Reason("climate_window_dry", "Dehumidifier", "2.5 g/kg"),),
    )
    return replace(original, **changes)


def fields(template):
    return {field for _, field, _, _ in Formatter().parse(template) if field is not None}


class WindowSpeechTests(unittest.TestCase):
    def test_all_languages_have_complete_cautions_and_valid_placeholders(self):
        supported = set(fixture.languages.SUPPORTED_LANGUAGE_TAGS)
        self.assertEqual(set(text.WINDOW_OPEN_TEXT), supported)
        self.assertEqual(len(supported), 38)
        placeholders = {
            "conditional_open": {"area", "windows", "reasons", "cautions"},
            "wait": {"minutes"}, "heat_loss": {"value"},
            "outside_more_moisture": {"value"}, "outside_pollen": {"value"},
            "aqi_scale_unconfigured": {"name"}, "unverified": set(),
        }
        for language, entry in text.WINDOW_OPEN_TEXT.items():
            with self.subTest(language=language):
                for key, expected in placeholders.items():
                    self.assertEqual(fields(entry[key]), expected, key)
                self.assertEqual(len(entry["weather"]), 4)
                for template in entry["weather"]:
                    self.assertEqual(fields(template), {"value"})
                for code in ("weather_heat_loss", "outside_conditions_not_verified",
                             "outside_more_moisture", "aqi_scale_unconfigured", "outside_pollen"):
                    self.assertNotEqual(messages.explain(logic.Reason(code, "Source", "17"), language),
                                        code.replace("_", " "))

    def test_every_caution_survives_beyond_the_short_indoor_reason_list(self):
        warnings = (
            logic.Reason("weather_cold", value="3.9 °C"),
            logic.Reason("weather_wind", value="48 km/h"),
            logic.Reason("outside_pm25", "PM2.5", "44 µg/m³"),
            logic.Reason("weather_heat_loss", value="17.1 °C"),
            logic.Reason("outside_more_moisture", value="1.3 g/kg"),
            logic.Reason("outside_conditions_not_verified"),
            logic.Reason("active_warning", "Storm warning · Τελευταία"),
        )
        notice = rec(cautions=warnings, wait_seconds=300)
        for language in fixture.languages.SUPPORTED_LANGUAGE_TAGS:
            with self.subTest(language=language):
                title, body = messages.announcement(notice, language)
                self.assertTrue(title)
                self.assertIn(notice.area_name, body)
                self.assertNotIn("Badfenster", body)
                self.assertIn("2.5 g/kg", body)
                for warning in warnings:
                    self.assertIn(messages.explain(warning, language), body)
                expected = text.WINDOW_OPEN_TEXT[language]["conditional_open"].format(
                    area=notice.area_name, windows=text.ROOM_WINDOW_NAMES[language],
                    reasons=messages.explain(notice.reasons[0], language),
                    cautions="; ".join(messages.explain(warning, language) for warning in warnings),
                )
                self.assertTrue(body.startswith(expected))
                self.assertTrue(body.endswith(text.WINDOW_OPEN_TEXT[language]["wait"].format(minutes="5")))
        english = messages.announcement(notice, "en")[1]
        self.assertNotIn("Outdoor conditions are suitable", english)
        self.assertIn("Devices already running continue", english)

    def test_wait_suffix_only_describes_a_valid_opening_wait(self):
        plain = rec()
        base = messages.announcement(plain, "en")[1]
        for invalid in (None, True, "300", 0, -1, float("nan"), float("inf"), 1801):
            with self.subTest(value=invalid):
                self.assertEqual(messages.announcement(replace(plain, wait_seconds=invalid), "en")[1], base)
        self.assertIn("up to 1 minute for", messages.announcement(replace(plain, wait_seconds=60), "en")[1])
        for remaining in (1, 16.123456, 59.9):
            result = messages.announcement(replace(plain, wait_seconds=remaining), "en")[1]
            self.assertIn("up to 1 minute for", result)
            self.assertNotIn(str(remaining / 60), result)
        closed = rec(action="close", reasons=(logic.Reason("weather_wind", value="42 km/h"),),
                     wait_seconds=300)
        self.assertNotIn("automatic device starts", messages.announcement(closed, "en")[1])

    def test_opportunities_do_not_claim_that_a_device_is_already_running(self):
        phrases = {
            "en": ("equipment is operating",),
            "de": ("die Kühlung läuft", "die Heizung läuft", "die Entfeuchtung läuft"),
            "el": ("λειτουργεί ψύξη", "λειτουργεί θέρμανση", "λειτουργεί αφύγρανση"),
        }
        for language, prohibited in phrases.items():
            for effect in ("cool", "heat", "dry"):
                description = messages.explain(logic.Reason("climate_window_" + effect, value="2"), language)
                self.assertIn("2", description)
                for phrase in prohibited:
                    self.assertNotIn(phrase, description)


class WindowSettingTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_setting_defaults_and_zero_or_thirty_round_trip(self):
        flow = fixture.GeneralFlow(language="el", keep={"room": "unchanged"})
        before = deepcopy(flow._values)
        form = await flow.async_step_setup_general()
        marker = next(field for field in form["data_schema"] if field == KEY)
        self.assertEqual(marker.default, 5)
        config = form["data_schema"][marker].config
        self.assertEqual((config["min"], config["max"], config["step"]), (0, 30, 1))
        self.assertEqual(flow._values, before)
        for minutes in (0, 1, 5, 30):
            result = await flow.async_step_setup_general({KEY: minutes})
            self.assertEqual(result["saved"][KEY], minutes)
            self.assertIs(type(result["saved"][KEY]), int)
            self.assertEqual(result["saved"]["language"], "el")
            self.assertEqual(result["saved"]["keep"], {"room": "unchanged"})

    async def test_invalid_general_and_native_timeout_do_not_save(self):
        manager = fixture.Manager(**{KEY: 5})
        for bad in (-1, 31, 2.5, True, None, "invalid", float("nan"), float("inf")):
            with self.subTest(value=bad):
                flow = fixture.GeneralFlow(**{KEY: 5})
                before = deepcopy(flow._values)
                form = await flow.async_step_setup_general({KEY: bad})
                self.assertEqual(form["errors"][KEY], "invalid_room_source")
                self.assertEqual(flow._values, before)
                self.assertEqual(flow.saved, 0)
                with self.assertRaises(ValueError):
                    await fixture.ns["update_device_setting"](manager, "global_setting", KEY, bad)
        self.assertEqual(manager.saved, [])
        with self.assertRaises(ValueError):
            await fixture.ns["update_device_setting"](manager, "global_setting", KEY, 7, area="other")

    async def test_native_number_saves_same_setting_and_retains_other_options(self):
        manager = fixture.Manager(language="de", announcement_repeat_minutes=17)
        number = ConfigNumber(manager, manager.entry.entry_id, None, "global_setting",
                              KEY, (0, 30, 1, "min"))
        self.assertEqual(number.native_value, 5)
        self.assertEqual(number._attr_unique_id, "existing_entry_home_global_setting_" + KEY)
        for minutes in (0, 4, 30):
            await number.async_set_native_value(minutes)
            self.assertEqual(number.native_value, minutes)
            self.assertEqual(manager.settings[KEY], minutes)
            self.assertEqual(manager.settings["announcement_repeat_minutes"], 17)
            self.assertEqual(manager.settings["language"], "de")
            self.assertEqual(manager.settings["keep"], {"room": "unchanged"})
        for bad in (None, True, -5, 31, 0.5, float("nan"), "bad"):
            manager.entry.options[KEY] = bad
            self.assertEqual(number.native_value, 5)

    def test_every_catalog_matches_the_native_setting_and_waiting_statuses(self):
        manager = fixture.Manager()
        number = ConfigNumber(manager, manager.entry.entry_id, None, "global_setting",
                              KEY, (0, 30, 1, "min"))
        for language in fixture.languages.SUPPORTED_LANGUAGE_TAGS:
            with self.subTest(language=language):
                manager.hass.config.language = language
                catalog = json.loads((ROOT / "translations" / f"{language}.json").read_text())
                self.assertEqual(number.name, catalog["entity"]["number"][NATIVE_KEY]["name"])
                help_text = number.extra_state_attributes["configuration_help"]
                for flow in ("config", "options"):
                    general = catalog[flow]["step"]["setup_general"]
                    self.assertEqual(help_text, general["data_description"][KEY])
                    self.assertEqual(general["data"][KEY], text.WINDOW_OPEN_TEXT[language]["label"])
                states = catalog["entity"]["sensor"]["equipment_control_status"]["state"]
                for code, field in (("window_open_wait", "waiting"), ("window_request_pending", "pending")):
                    self.assertEqual(states[code], text.WINDOW_OPEN_TEXT[language][field])
                    self.assertIn(code, status_catalog.CONTROLLER_STATUS_CODES)
                    self.assertIn(code, status_catalog.EQUIPMENT_SENSOR_STATUSES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
