"""Outdoor discovery is a choice, not proof that every AQI source is outside.

Execute production discovery, both source-selection entrypoints, and the
source-specific scale form against read-only HA registries. Saved selections
and the runtime's independent outdoor-evidence requirement remain intact.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_074b7_outdoor_sources"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(SOURCE)])
module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object)
helpers = module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: datetime.now(timezone.utc)))
for name in ("area_registry", "entity_registry", "device_registry"):
    setattr(helpers, name, module("homeassistant.helpers." + name,
        async_get=lambda hass, name=name: getattr(hass, name)))
module(PACKAGE + ".languages", SUPPORTED_LANGUAGE_TAGS=("en", "el", "de"),
       normalize_announcement_language=lambda value: value if value in ("auto", "en", "el", "de") else None)
module(PACKAGE + ".ai_rewrite", DEFAULT_AGENT="none")
module(PACKAGE + ".hub_delivery", hub_installed=lambda hass: False)

constants = importlib.import_module(PACKAGE + ".const")
discovery = importlib.import_module(PACKAGE + ".discovery")
logic = importlib.import_module(PACKAGE + ".logic")


class ForbiddenTransport:
    def __getattr__(self, name):
        raise AssertionError(f"Selecting a source must not invoke {name}")


class States:
    def __init__(self, rows):
        self.rows = {row.entity_id: row for row in rows}

    def get(self, entity_id):
        return self.rows.get(entity_id)

    def async_all(self, domain):
        return [row for key, row in self.rows.items() if key.startswith(domain + ".")]


class Selectors:
    NumberSelectorMode = N(BOX="box")

    def NumberSelectorConfig(self, **values):
        return values

    def NumberSelector(self, config):
        return ("number", config)

    def BooleanSelector(self):
        return ("boolean",)


defaults = {}


def field(name, value, **kwargs):
    defaults[name] = deepcopy(value)
    return name


scope = {"__name__": PACKAGE + ".source_forms", "__package__": PACKAGE,
         "Any": Any, "ConfigFlowResult": dict, "math": math, "deepcopy": deepcopy,
         "selector": Selectors(), "probatio": N(Schema=lambda values: values),
         "field": field, "_marker": field, "_field": field,
         "select": lambda values, **kwargs: ("select", values),
         "_select": lambda values, **kwargs: ("select", values),
         "_number": lambda low, high: ("number", low, high),
         "_multi": lambda values: values,
         "outdoor_choices": discovery.outdoor_choices}
scope.update({name: getattr(constants, name) for name in dir(constants) if name.isupper()})
for filename, method_name in (("room_setup.py", "async_step_setup_general"),
                              ("config_flow.py", "async_step_outdoor"),
                              ("compact_options.py", "async_step_outside_aqi")):
    tree = ast.parse((SOURCE / filename).read_text())
    method = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE / filename), "exec"), scope)


class Form:
    def __init__(self, hass, saved=None):
        self.hass = hass
        self._values = {"areas": ["living"], "weather_entities": ["weather.home"],
                        "environment_global": {}, "occupancy_global": {}}
        if saved is not None:
            self._values["outdoor_sensors"] = deepcopy(saved)
        self._setup_order = []
        self._setup_index = 0
        self.saved = 0
        self.advanced = []

    def _general_options(self):
        options = {key: [] for key in ("weather_warnings", "notify_entities", "media_players",
            "pollen_entities", "general_home_trackers", "away_windows_target_people")}
        options.update({
            "weather_entities": [{"value": "weather.home"}],
            "outdoor_sensors": discovery.outdoor_choices(self.hass, ["living"]),
            "tts_engine": [{"value": "none"}], "ai_conversation_agent": [{"value": "none"}],
            "away_windows_delivery_channels": [{"value": "mobile_notification"}],
        })
        for key in ("general_occupied_rooms_entity", "general_sleep_rooms_entity",
                    "general_wake_alarm_entity", "general_wake_lead_minutes_entity"):
            options[key] = [{"value": "none"}]
        return options

    def _room_attribute_options(self, hass, entity_id):
        return [{"value": "__state__"}]

    def async_show_form(self, **kwargs):
        return kwargs

    async def _finish(self):
        self.saved += 1
        return {"saved": deepcopy(self._values)}

    async def _advance(self, step):
        self.advanced.append(step)
        return {"next": step}


class OutdoorSelectionTests(unittest.TestCase):
    def setUp(self):
        self.ids = ["sensor.aqi_co2", "sensor.aqi_humidity", "sensor.aqi_pm25",
                    "sensor.aqi_temperature", "sensor.aqi_tvoc", "sensor.home_air_quality_index",
                    "sensor.piraeus_air_quality_index"]
        names = ["AQI Co2", "AQI Humidity", "AQI PM 2.5", "AQI Temperature", "AQI TVOC",
                 "Home AQI Index", "Piraeus-1, Greece - Air quality index"]
        values = (1, 2, 1, 2, 1, 1, 85)
        rows = [N(entity_id=entity, name=name, state=str(value), attributes={"device_class": "aqi"})
                for entity, name, value in zip(self.ids, names, values)]
        registration = N(area_id=None, device_id=None, original_device_class="aqi")
        self.hass = N(states=States(rows),
            entity_registry=N(async_get=lambda entity: registration),
            device_registry=N(async_get=lambda entity: None), area_registry=N(),
            services=ForbiddenTransport(), config_entries=ForbiddenTransport())

    def general(self, form, user_input=None):
        defaults.clear()
        return asyncio.run(scope["async_step_setup_general"](form, user_input))

    def legacy(self, form, user_input=None):
        defaults.clear()
        return asyncio.run(scope["async_step_outdoor"](form, user_input))

    def scale(self, form, user_input=None):
        defaults.clear()
        return asyncio.run(scope["async_step_outside_aqi"](form, user_input))

    def test_new_general_setup_requires_explicit_outdoor_choice(self):
        form = Form(self.hass)
        before = deepcopy(form._values)
        result = self.general(form)
        self.assertEqual(result["errors"], {})
        self.assertEqual(defaults["outdoor_sensors"], [])
        self.assertEqual({item["value"] for item in result["data_schema"]["outdoor_sensors"][1]},
                         set(self.ids))
        self.assertEqual(form._values, before)
        self.assertEqual(form.saved, 0)
        # Numeric categories and suggestive source names do not become
        # concentrations or prove that these sensors measure outdoor air.
        for row in self.hass.states.rows.values():
            self.assertEqual(discovery.supported_metric(self.hass, row, outdoor=True), "aqi")
        output = self.general(form, {"general_away_cooldown_minutes": 15})
        self.assertEqual(output["saved"]["outdoor_sensors"], [])

    def test_saved_empty_and_nonempty_selections_survive_unrelated_edits(self):
        for selected in ([], self.ids[:6], self.ids):
            with self.subTest(selected=selected):
                form = Form(self.hass, selected)
                before = deepcopy(form._values)
                self.general(form)
                self.assertEqual(defaults["outdoor_sensors"], selected)
                self.assertEqual(form._values, before)
                result = self.general(form, {"general_away_cooldown_minutes": 20})
                self.assertEqual(result["saved"]["outdoor_sensors"], selected)

    def test_explicit_general_selection_and_clearing_are_valid(self):
        form = Form(self.hass)
        result = self.general(form, {"outdoor_sensors": [self.ids[-1]]})
        self.assertEqual(result["saved"]["outdoor_sensors"], [self.ids[-1]])
        result = self.general(form, {"outdoor_sensors": []})
        self.assertEqual(result["saved"]["outdoor_sensors"], [])
        invalid = self.general(form, {"outdoor_sensors": ["sensor.foreign"]})
        self.assertEqual(invalid["errors"]["outdoor_sensors"], "invalid_room_source")

    def test_legacy_selection_can_be_empty_even_without_candidates(self):
        for have_candidates in (True, False):
            with self.subTest(have_candidates=have_candidates):
                if not have_candidates:
                    self.hass.states = States([])
                form = Form(self.hass)
                self.assertEqual(self.legacy(form)["errors"], {})
                self.assertEqual(defaults["outdoor_sensors"], [])
                self.assertEqual(self.legacy(form, {"outdoor_sensors": []}), {"next": "weather"})
                self.assertEqual(form._values["outdoor_sensors"], [])

    def test_legacy_selection_keeps_known_sources_and_rejects_invalid_inputs(self):
        form = Form(self.hass, self.ids)
        before = deepcopy(form._values)
        self.legacy(form)
        self.assertEqual(defaults["outdoor_sensors"], self.ids)
        self.assertEqual(form._values, before)
        missing = self.legacy(form, {})
        self.assertEqual(missing["errors"]["base"], "invalid_outdoor")
        self.assertEqual(form._values, before)
        self.assertEqual(self.legacy(form, {"outdoor_sensors": [self.ids[-1]]}), {"next": "weather"})
        for selected in (None, self.ids[-1], {}, ["sensor.foreign"], [None], [1]):
            with self.subTest(selected=selected):
                invalid = self.legacy(Form(self.hass), {"outdoor_sensors": selected})
                self.assertEqual(invalid["errors"]["base"], "invalid_outdoor")

    def test_empty_choice_keeps_runtime_evidence_requirement(self):
        plan = logic.evaluate((), (logic.Weather("weather.home", "partlycloudy", 20, 60, 5),),
                              (), (), constants.DEFAULT_THRESHOLDS)
        self.assertIn("no_outdoor_data", {reason.code for reason in plan.outside_reasons})
        self.assertFalse(plan.outdoor_safe)

    def test_legacy_scale_form_offers_its_automatic_default(self):
        form = Form(self.hass, [self.ids[-1]])
        before = deepcopy(form._values)
        shown = self.scale(form)
        self.assertEqual(shown["errors"], {})
        self.assertEqual(defaults["outside_aqi_scale"], "auto")
        self.assertEqual(shown["data_schema"]["outside_aqi_scale"][1],
                         ["auto", "not_configured", "us_epa", "eea_category", "custom"])
        self.assertEqual(form._values, before)
        self.assertEqual(form.saved, 0)
        saved = self.scale(form, {"outside_aqi_scale": "auto"})
        self.assertEqual(saved["saved"]["environment_global"]["aqi_scales"], {})

    def test_legacy_scale_choice_preserves_manual_values_and_other_sources(self):
        for selection in ("not_configured", "us_epa", "eea_category", "custom"):
            with self.subTest(selection=selection):
                form = Form(self.hass, self.ids)
                details = {"scale": selection}
                if selection == "custom":
                    details["custom_limit"] = 2.5
                existing = {self.ids[0]: details, self.ids[-1]: {"scale": "us_epa"}}
                form._values["environment_global"] = {"aqi_scales": deepcopy(existing)}
                self.scale(form)
                self.assertEqual(defaults["outside_aqi_scale"], selection)
                self.assertEqual(defaults["outside_aqi_limit"], details.get("custom_limit", 100))
                self.assertEqual(form._values["environment_global"]["aqi_scales"], existing)
                unchanged = self.scale(form, {"outside_aqi_scale": selection})
                self.assertEqual(unchanged["saved"]["environment_global"]["aqi_scales"], existing)
                automatic = self.scale(form, {"outside_aqi_scale": "auto"})
                self.assertEqual(automatic["saved"]["environment_global"]["aqi_scales"],
                                 {self.ids[-1]: {"scale": "us_epa"}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
