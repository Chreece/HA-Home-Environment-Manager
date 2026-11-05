"""Pressure retirement keeps real pollutant evidence and useful room lux.

Exercise production inventory, discovery, source persistence, outdoor capture
and configuration methods against read-only HA registries. No HA entities or
physical services are created, changed or called.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "beta115_sensor_scope"
ROOM = "living"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


module(PKG, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.core", HomeAssistant=object, State=object)
helpers = module("homeassistant.helpers", __path__=[])
module("homeassistant.util", dt=N(utcnow=lambda: datetime.now(timezone.utc)))
for name in ("area_registry", "entity_registry", "device_registry"):
    setattr(helpers, name, module(
        "homeassistant.helpers." + name,
        async_get=lambda hass, name=name: getattr(hass, name),
    ))

constants = importlib.import_module(PKG + ".const")
discovery = importlib.import_module(PKG + ".discovery")
sources = importlib.import_module(PKG + ".room_sources")
# Reconciliation is unrelated to retiring input fields. Preserve the actual
# updated device draft and fail if a test ever enrolls physical equipment.
def reconcile(previous, current):
    assert current.get("selected_devices") == []
    return deepcopy(current)


module(PKG + ".compact_options", _reconcile_device_selection=reconcile)


class States:
    def __init__(self):
        self.data = {}

    def get(self, entity):
        return self.data.get(entity)

    def async_all(self, domain=None):
        return [value for value in self.data.values()
                if domain is None or value.domain == domain]


class Fixture:
    def __init__(self):
        self.states = States()
        self.entries = {}
        self.hass = N(
            states=self.states,
            entity_registry=N(entities=self.entries, async_get=self.entries.get),
            device_registry=N(async_get=lambda entity: None),
            area_registry=N(async_get_area=lambda area: N(id=area, name=area)),
        )
        self.add("sensor.room_pressure", "1015", "atmospheric_pressure", "hPa")
        self.add("sensor.unit_pressure", "101500", "", "Pa")
        self.add("sensor.gauge_pressure", "1", "pressure", "bar")
        self.add("sensor.offline_pressure", "unavailable", "pressure", "kPa")
        self.add("sensor.removed_pressure", None, "atmospheric_pressure", "hPa")
        self.add("sensor.light", "1400", "illuminance", "lx")
        self.add("sensor.room_co2", "800", "co2", "ppm")
        self.add("sensor.missing_co2", None, "co2", "ppm")
        self.add("sensor.temperature", "21", "temperature", "°C")
        self.add("sensor.humidity", "48", "humidity", "%")
        self.add("sensor.noise", "40", "sound_pressure", "dB(A)")
        self.add("sensor.outdoor", "unavailable", "co2", "ppm", area="outside")
        self.add("sensor.outside_pressure", "1012", "atmospheric_pressure", "hPa", area="outside")

    def add(self, entity, value, kind, unit, *, area=ROOM):
        self.entries[entity] = N(
            entity_id=entity, area_id=area, device_id=None, platform="test",
            device_class=None, original_device_class=kind,
            original_unit_of_measurement=unit, name=None, original_name=entity,
        )
        if value is not None:
            now = datetime.now(timezone.utc)
            self.states.data[entity] = N(
                entity_id=entity, domain=entity.split(".")[0], name=entity,
                state=value, attributes={"device_class": kind, "unit_of_measurement": unit},
                last_updated=now, last_reported=now, last_changed=now,
            )


class SensorScopeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.hass = self.fixture.hass

    def test_positive_pressure_metadata_and_missing_pollutants(self):
        for entity in ("sensor.room_pressure", "sensor.unit_pressure",
                       "sensor.gauge_pressure", "sensor.offline_pressure",
                       "sensor.removed_pressure"):
            with self.subTest(entity=entity):
                self.assertTrue(discovery.is_pressure_sensor(self.hass, entity))
        for entity in ("sensor.room_co2", "sensor.missing_co2", "sensor.not_registered",
                       "sensor.light", "sensor.noise", "binary_sensor.pressure_warning"):
            self.assertFalse(discovery.is_pressure_sensor(self.hass, entity))
        # Real live reclassification wins over old registry pressure metadata.
        state = self.fixture.states.data["sensor.room_pressure"]
        state.attributes = {"device_class": "co2", "unit_of_measurement": "ppm"}
        self.assertFalse(discovery.is_pressure_sensor(self.hass, state.entity_id))
        self.assertEqual(discovery.supported_metric(self.hass, state, outdoor=True), "co2")

    def test_pressure_never_becomes_a_pollutant_from_its_entity_name(self):
        self.fixture.add("sensor.barometer_co2", "1012", "pressure", "ppm")
        state = self.fixture.states.get("sensor.barometer_co2")
        for outdoor in (False, True):
            self.assertIsNone(discovery.supported_metric(self.hass, state, outdoor=outdoor))

    def test_room_and_outdoor_choices_retain_lux_and_real_pollutants(self):
        self.assertEqual(sources.GROUPS, (
            "windows", "air_quality", "temperature", "humidity", "climate_devices", "shades"))
        previous = {"pressure": ["sensor.removed_pressure"],
                    "air_quality": ["sensor.offline_pressure", "sensor.removed_pressure", "sensor.missing_co2"]}
        offered = sources.choices(self.hass, ROOM, previous)
        self.assertNotIn("pressure", offered)
        all_ids = {item["value"] for group in offered.values() for item in group}
        self.assertFalse(any(discovery.is_pressure_sensor(self.hass, entity) for entity in all_ids))
        self.assertTrue({"sensor.light", "sensor.room_co2", "sensor.missing_co2", "sensor.noise"} <= all_ids)
        outdoor = discovery.outdoor_choices(self.hass, [ROOM])
        self.assertEqual([item["value"] for item in outdoor], ["sensor.outdoor"])

    def test_pressure_only_room_keeps_explicit_empty_inputs(self):
        saved = {"pressure": ["sensor.room_pressure"], "shades": []}
        config = {"room_sources": {ROOM: saved}}
        before = deepcopy(config)
        defaults = sources.defaults(self.hass, config, ROOM)
        self.assertTrue(all(value == [] for value in defaults.values()))
        self.assertEqual(config, before)
        # An absent legacy cover group may discover cover inventory. It must
        # still never rediscover unselected air/temperature/humidity sources.
        del saved["shades"]
        defaults = sources.defaults(self.hass, config, ROOM)
        for group in ("windows", "air_quality", "temperature", "humidity", "climate_devices"):
            self.assertEqual(defaults[group], [])

    def test_active_source_edit_preserves_inert_legacy_keys_and_other_rooms(self):
        current = {group: [] for group in sources.GROUPS}
        current.update(pressure=["sensor.room_pressure"], future_metadata={"keep": True})
        other = {"temperature": ["sensor.other"], "pressure": ["sensor.other_pressure"]}
        config = {"room_sources": {ROOM: deepcopy(current), "other": deepcopy(other)},
                  "outside_configuration": {"unchanged": [1, 2]}}
        values = {group: [] for group in sources.GROUPS}
        values["air_quality"] = ["sensor.light"]
        sources.store_selection(self.hass, config, ROOM, values)
        self.assertEqual(config["room_sources"][ROOM]["pressure"], current["pressure"])
        self.assertEqual(config["room_sources"][ROOM]["future_metadata"], {"keep": True})
        self.assertEqual(config["room_sources"]["other"], other)
        self.assertEqual(config["outside_configuration"], {"unchanged": [1, 2]})
        self.assertEqual(config["room_sources"][ROOM]["temperature"], [])
        self.assertEqual(config["room_sources"][ROOM]["air_quality"], ["sensor.light"])
        self.assertEqual(config["climate_rooms"][ROOM]["selected_devices"], [])
        self.assertNotIn("enabled", config["climate_rooms"][ROOM])
        self.assertEqual(set(self.fixture.entries), set(Fixture().entries))

    def test_room_capture_and_overview_omit_retired_pressure(self):
        selected = {group: [] for group in sources.GROUPS}
        selected.update(pressure=["sensor.room_pressure"], air_quality=[
            "sensor.light", "sensor.room_pressure", "sensor.removed_pressure", "sensor.missing_co2"])
        settings = {"room_sources": {ROOM: selected}}
        rooms = discovery.rooms(self.hass, [ROOM], 90, source_selections=settings["room_sources"])
        readings = {reading.entity_id: reading for reading in rooms[0].readings}
        self.assertEqual(set(readings), {"sensor.light", "sensor.missing_co2"})
        self.assertEqual(readings["sensor.light"].value, 1400)
        self.assertIsNone(readings["sensor.missing_co2"].value)
        manager = N(hass=self.hass, settings=settings, thresholds={})
        overview = sources.source_overview(manager, ROOM)
        self.assertNotIn("pressure", overview)
        self.assertNotIn("pressure_summary", overview)
        self.assertEqual({item["entity_id"] for item in overview["air_quality"]},
                         {"sensor.light", "sensor.missing_co2"})
        self.assertIsNone(sources.numeric(self.hass, "sensor.room_pressure", ROOM, "pressure", 90))

    def test_actual_manager_outdoor_selection_filters_only_known_pressure(self):
        tree = ast.parse((ROOT / "manager.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "AirQualityManager")
        capture = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                       and node.name == "_capture")
        stop = next(index for index, node in enumerate(capture.body)
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == "monitored_areas"
                        for target in node.targets))
        settings = {constants.CONF_OUTDOOR: ["sensor.outside_pressure", "sensor.removed_pressure",
                    "sensor.outdoor", "sensor.missing_co2", "sensor.not_registered"]}
        before = deepcopy(settings)
        scope = {"__package__": PKG, "CONF_OUTDOOR": constants.CONF_OUTDOOR,
                 "self": N(hass=self.hass, settings=settings, thresholds={"max_age_minutes": 90})}
        exec(compile(ast.Module(capture.body[:stop], type_ignores=[]), "manager.py", "exec"), scope)
        self.assertEqual(scope["selected_outdoor"],
                         {"sensor.outdoor", "sensor.missing_co2", "sensor.not_registered"})
        self.assertEqual(settings, before)

    def test_general_form_removes_only_pressure_from_draft_and_saved_outdoor_list(self):
        prior = runpy.run_path(str(ROOT / ".github/tests/test_beta79_general_form.py"))
        # Keep all unrelated form helpers, but exercise the real source
        # classifier against this test's physical metadata and registry.
        sys.modules["beta79_general.discovery"].is_pressure_sensor = discovery.is_pressure_sensor
        ui = prior["UI"]()
        ui.hass = self.hass
        ui._values[constants.CONF_OUTDOOR] = ["sensor.outside_pressure", "sensor.outdoor"]
        before = deepcopy(ui._values)
        form = asyncio.run(prior["real"](ui))
        self.assertFalse(form["errors"])
        self.assertEqual(prior["keys"][constants.CONF_OUTDOOR], ["sensor.outdoor"])
        self.assertEqual(ui._values, before)
        self.assertEqual(ui.saved, 0)
        result = asyncio.run(prior["real"](ui, {"global_threshold_indoor_humidity": 62.0}))
        self.assertEqual(result["saved"][constants.CONF_OUTDOOR], ["sensor.outdoor"])
        self.assertEqual(result["saved"]["weather_entities"], before["weather_entities"])
        self.assertEqual(ui.saved, 1)

    def test_legacy_outdoor_form_has_no_pressure_default_or_open_side_effect(self):
        tree = ast.parse((ROOT / "config_flow.py").read_text())
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == "async_step_outdoor")
        defaults = {}
        def marker(name, value, **kwargs):
            defaults[name] = deepcopy(value)
            return name
        scope = {"__package__": PKG, "Any": Any, "ConfigFlowResult": dict,
                 "CONF_OUTDOOR": constants.CONF_OUTDOOR, "CONF_AREAS": constants.CONF_AREAS,
                 "outdoor_choices": discovery.outdoor_choices, "_marker": marker,
                 "_multi": lambda values: values, "probatio": N(Schema=lambda fields: fields)}
        exec(compile(ast.Module([method], type_ignores=[]), "config_flow.py", "exec"), scope)
        config = {constants.CONF_AREAS: [ROOM],
                  constants.CONF_OUTDOOR: ["sensor.outside_pressure", "sensor.outdoor"]}
        before = deepcopy(config)
        ui = N(hass=self.hass, _values=config, async_show_form=lambda **kwargs: kwargs)
        form = asyncio.run(scope["async_step_outdoor"](ui))
        self.assertEqual(form["step_id"], "outdoor")
        self.assertEqual(defaults[constants.CONF_OUTDOOR], ["sensor.outdoor"])
        self.assertEqual(config, before)

    def test_every_catalog_explains_lux_and_has_only_active_sensor_groups(self):
        paths = [ROOT / "strings.json", *sorted((ROOT / "translations").glob("*.json"))]
        self.assertEqual(len(paths), 39)
        helpers = json.loads((ROOT / "full_config_help_science.json").read_text())[
            "environment_room_exposure.illuminance_entity"]
        for path in paths:
            locale = "en" if path.name == "strings.json" else path.stem
            data = json.loads(path.read_text())
            for flow in ("config", "options"):
                steps = data[flow]["step"]
                for name in ("setup_room_sources", "room_settings", "edit_room"):
                    with self.subTest(locale=locale, flow=flow, form=name):
                        step = steps[name]
                        self.assertNotIn("pressure", step["data"])
                        self.assertNotIn("pressure", step["data_description"])
                        self.assertIn("lux", step["data_description"]["air_quality"].casefold())
                        self.assertTrue(set(sources.GROUPS) <= set(step["data"]))
                exposure = steps["environment_room_exposure"]
                self.assertIn("lux", exposure["data"]["illuminance_entity"].casefold())
                self.assertEqual(exposure["data_description"]["illuminance_entity"], helpers[locale])
        english = json.loads((ROOT / "strings.json").read_text())["options"]["step"]
        room_help = english["edit_room"]["data_description"]["air_quality"]
        self.assertIn("new automatic closing", room_help)
        self.assertIn("minimum brightness", room_help)
        self.assertIn("Selecting sensors here does not enable movement", room_help)
        self.assertIn("configured separately", helpers["en"])


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if not result.result.wasSuccessful():
        raise SystemExit(1)
    print("BETA115_PRESSURE_RETIRED_LUX_EXPLAINED_LEGACY_SOURCES_PRESERVED=PASS")
