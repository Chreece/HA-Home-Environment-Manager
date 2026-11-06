"""Room RH defaults agree at display, physical planning and both save paths.

Uses production profile selection, target limits, Number values and settings
writers. Only HA state/options transport is simulated; no device services are
available. Existing saved values must survive a change to the defaults and an
unrelated temperature edit, including values saved by legacy versions.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_beta116_humidity"
AREA = "room"
ENTITY = "climate.humidity"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


class NumberEntity:
    pass


module(PKG, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.core", callback=lambda func: func)
module("homeassistant.exceptions", HomeAssistantError=ValueError)
module("homeassistant.components", __path__=[])
module("homeassistant.components.number", NumberEntity=NumberEntity, NumberMode=N(BOX="box"))
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.entity", EntityCategory=N(CONFIG="config"))
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module("homeassistant.helpers.dispatcher", async_dispatcher_connect=lambda *args: lambda: None)
# Registry transport for the real occupancy policy reached by live plan_for.
# This RH-only fixture installs one climate endpoint and no presence sources.
module(PKG + ".discovery",
       entity_area=lambda hass, entity: AREA if entity == ENTITY else None,
       _device_class=lambda hass, state: state.attributes.get("device_class", ""))
# Unrelated cover-control entities are not instantiated by this regression.
module(PKG + ".shade_cooling", SHADE_NUMBERS={})
model = importlib.import_module(PKG + ".equipment_model")
controls = importlib.import_module(PKG + ".device_controls")
numbers = importlib.import_module(PKG + ".number")
strategy = importlib.import_module(PKG + ".climate_strategy")


def method(filename, cls, name, **values):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls)
    found = next(node for node in owner.body if isinstance(node, ast.AsyncFunctionDef) and node.name == name)
    namespace = dict(__name__=PKG + ".fixture", __package__=PKG,
                     asyncio=asyncio, deepcopy=deepcopy, **values)
    source = ast.Module(body=[ast.parse("from __future__ import annotations").body[0], found],
                        type_ignores=[])
    exec(compile(source, str(ROOT / filename), "exec"), namespace)
    return namespace[name]


set_targets = method("equipment_runtime.py", "EquipmentRuntime", "async_set_targets",
                     model=model, HomeAssistantError=ValueError, finite=model.finite)
device_form = method(
    "compact_options.py", "CompactOptionsMixin", "async_step_device_settings",
    DEFAULT_PROFILE_TARGETS=strategy.DEFAULT_PROFILE_TARGETS,
    CONF_EXCLUDED_INDOOR="excluded_indoor_entities",
    entity_area=lambda hass, entity: AREA,
    _device_type=lambda entity: entity.split(".", 1)[0],
)


class Fixture:
    def __init__(self, room=None, *, config=None, maximum=80):
        self.spec = model.ManagedDevice("controller", AREA, "Humidity", "physical", (ENTITY,))
        room = {"selected_devices": [ENTITY], "occupancy_sensors": [], **deepcopy(room or {})}
        self.entry = N(entry_id="entry", data={"areas": [AREA], "climate_rooms": {AREA: room},
                                              "unrelated": {"keep": True}}, options={})
        if config:
            self.entry.data[model.SETTINGS] = {self.spec.identifier: deepcopy(config)}
        self._device_hierarchy = {"controllers": {self.spec.identifier: {"spec": self.spec}}}
        self.plan = N(environment={AREA: {"climate_plan": {
            "away": "home", "occupancy": "occupied", "sleeping": False,
        }}})
        self.state = N(state="off", attributes={
            "hvac_modes": ["off", "dry"], "supported_features": 4,
            "min_humidity": 20, "max_humidity": maximum,
        })
        self.saved = []
        self.hass = N(states={ENTITY: self.state}, config=N(language="en"),
                      config_entries=N(async_update_entry=self.save))
        # No services property: editing targets must never actuate hardware.
        self.runtime = N(manager=self, hass=self.hass)

    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}

    @property
    def room(self):
        return self.settings["climate_rooms"][AREA]

    def save(self, entry, *, options):
        self.saved.append(deepcopy(options))
        entry.options = options

    def display(self, profile):
        key = profile + "_humidity"
        return numbers.ConfigNumber(self, "entry", AREA, "climate_profile", key,
                                    controls.PROFILE_NUMBERS[key]).native_value

    def target(self, profile=None, *, plan=None, manual=None):
        config = {"control_mode": "automatic", "preset": profile or "none"}
        if manual is not None:
            config.update(control_mode="manual", preset="none",
                          profile_targets={"manual": {"humidity": manual}})
        result = model.targets(self, self.spec, model.capabilities(self, self.spec), config,
                               plan or {"away": "home", "occupancy": "occupied", "sleeping": False})
        return result["humidity"]


class HumidityDefaultTests(unittest.IsolatedAsyncioTestCase):
    def test_unconfigured_profiles_display_and_plan_same_defaults(self):
        fixture = Fixture()
        before = deepcopy(fixture.settings)
        for name, expected in (("comfort", 65.), ("home", 65.), ("away", 65.),
                               ("sleep", 65.), ("eco", 70.)):
            with self.subTest(profile=name):
                self.assertEqual(fixture.display(name), expected)
                self.assertEqual(fixture.target(name), expected)
        self.assertEqual(fixture.settings, before, "Reading defaults must not persist configuration")
        self.assertFalse(fixture.saved)

    def test_automatic_presence_and_sleep_select_new_targets(self):
        fixture = Fixture()
        for plan, expected_profile in (
            ({"away": "home", "occupancy": "occupied"}, "comfort"),
            ({"away": "home", "occupancy": "unoccupied"}, "home"),
            ({"away": "away", "occupancy": "occupied"}, "away"),
            ({"away": "home", "occupancy": "occupied", "sleeping": True}, "sleep"),
        ):
            with self.subTest(profile=expected_profile):
                self.assertEqual(model.profile_name({"preset": "none", "control_mode": "pid"}, plan),
                                 expected_profile)
                self.assertEqual(fixture.target(plan=plan), 65.)

    def test_explicit_previous_defaults_and_custom_targets_survive(self):
        for profile in ("comfort", "home", "away", "sleep", "eco"):
            for saved in (50., 57., 72.):
                with self.subTest(profile=profile, saved=saved):
                    fixture = Fixture({"profiles": {profile: {"humidity": saved}}})
                    self.assertEqual(fixture.display(profile), saved)
                    self.assertEqual(fixture.target(profile), saved)
                    self.assertEqual(fixture.room["profiles"][profile]["humidity"], saved)

    def test_missing_humidity_in_temperature_profile_uses_only_that_profile_default(self):
        for profile, expected in (("comfort", 65.), ("home", 65.), ("away", 65.),
                                  ("sleep", 65.), ("eco", 70.)):
            fixture = Fixture({"profiles": {profile: {"heat_c": 20., "cool_c": 26.}}})
            self.assertEqual(fixture.display(profile), expected)
            self.assertEqual(fixture.target(profile), expected)

    def test_legacy_room_target_keeps_precedence_when_profile_not_saved(self):
        fixture = Fixture({"humidity_target": 54., "sleep_humidity_target": 61.})
        for profile in ("comfort", "home", "away", "eco"):
            self.assertEqual(fixture.display(profile), 54.)
            self.assertEqual(fixture.target(profile), 54.)
        self.assertEqual(fixture.display("sleep"), 61.)
        self.assertEqual(fixture.target("sleep"), 61.)

    def test_manual_targets_and_native_limits_remain_authoritative(self):
        fixture = Fixture()
        self.assertEqual(fixture.target(manual=58.), 58.)
        narrower = Fixture(maximum=60)
        self.assertEqual(narrower.target("home"), 60.)
        self.assertEqual(narrower.target("eco"), 60.)
        self.assertEqual(fixture.target(manual=50.), 50.)

    async def test_number_temperature_save_keeps_new_humidity_default(self):
        for profile, expected in (("comfort", 65.), ("home", 65.), ("away", 65.),
                                  ("sleep", 65.), ("eco", 70.)):
            fixture = Fixture()
            await controls.update_device_setting(fixture, "climate_profile", profile + "_heat", 19., area=AREA)
            self.assertEqual(fixture.room["profiles"][profile]["humidity"], expected)
            self.assertEqual(fixture.display(profile), fixture.target(profile))
            self.assertEqual(fixture.settings["unrelated"], {"keep": True})

    async def test_both_temperature_save_paths_preserve_saved_humidity(self):
        for writer in ("number", "climate"):
            for legacy in (False, True):
                for profile in ("comfort", "sleep", "eco"):
                    with self.subTest(writer=writer, legacy=legacy, profile=profile):
                        room = ({"humidity_target": 53., "sleep_humidity_target": 53.} if legacy else
                                {"profiles": {profile: {"heat_c": 20., "cool_c": 26., "humidity": 53.}}})
                        fixture = Fixture(room, config={"control_mode": "automatic", "preset": profile})
                        if writer == "number":
                            await controls.update_device_setting(fixture, "climate_profile", profile + "_heat", 19., area=AREA)
                        else:
                            await set_targets(fixture.runtime, fixture.spec, {"heat": 19.})
                        self.assertEqual(fixture.room["profiles"][profile]["humidity"], 53.)
                        self.assertEqual(fixture.display(profile), fixture.target(profile))

    async def test_climate_temperature_save_keeps_new_humidity_default(self):
        for profile, expected in (("comfort", 65.), ("home", 65.), ("away", 65.),
                                  ("sleep", 65.), ("eco", 70.)):
            fixture = Fixture(config={"control_mode": "automatic", "preset": profile})
            await set_targets(fixture.runtime, fixture.spec, {"heat": 19.})
            self.assertEqual(fixture.room["profiles"][profile]["humidity"], expected)
            self.assertEqual(fixture.display(profile), fixture.target(profile))

    async def test_legacy_device_form_uses_65_without_rewriting_saved_values(self):
        class Flow:
            def __init__(self, previous):
                self._device_entity, self._climate_area = ENTITY, AREA
                self._climate_draft = {"selected_devices": [ENTITY], "device_settings": {ENTITY: previous}}
                self._values = {}
                self.hass = N(states={ENTITY: N(state="off", attributes={"hvac_modes": ["off", "dry"]})})

            async def _save_devices(self):
                return deepcopy(self._climate_draft)

        for previous in ({}, {"humidity_target": 50., "sleep_humidity_target": 57.}):
            flow = Flow(deepcopy(previous))
            result = await device_form(flow, {})
            saved = result["device_settings"][ENTITY]
            self.assertEqual(saved["humidity_target"], previous.get("humidity_target", 65.))
            self.assertEqual(saved["sleep_humidity_target"], previous.get("sleep_humidity_target", 65.))
            self.assertFalse(saved["auto_control"])
            self.assertNotIn("allow_actuation", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
