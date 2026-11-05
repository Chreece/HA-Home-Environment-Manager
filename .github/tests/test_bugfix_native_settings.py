"""Native room preferences exist without granting a legacy room controller.

Runs the production select/number/switch/time platform setup, entity actions,
settings writer and authorization context. Only Home Assistant transport and
entity base classes are simulated. A newly selected native appliance has no
legacy climate_rooms.enabled flag, including while its native state is offline.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import time
import importlib
from pathlib import Path
import sys
from types import MappingProxyType, ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_bugfix_native_settings"
AREA = "living_room"
SOURCE = "climate.room_heater"


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


class Entity:
    _attr_entity_registry_enabled_default = True

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def name(self):
        return getattr(self, "_attr_name", None)

    @property
    def extra_state_attributes(self):
        return {}

    def async_write_ha_state(self):
        self.writes = getattr(self, "writes", 0) + 1


module(PKG, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.core", callback=lambda func: func)
module("homeassistant.const", EVENT_STATE_CHANGED="state_changed")
module("homeassistant.exceptions", HomeAssistantError=ValueError)
module("homeassistant.components", __path__=[])
for platform, name in (("select", "SelectEntity"), ("number", "NumberEntity"),
                       ("switch", "SwitchEntity"), ("time", "TimeEntity")):
    module("homeassistant.components." + platform,
           **{name: Entity, "NumberMode": N(BOX="box")})
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.entity", EntityCategory=N(CONFIG="config"))
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
module("homeassistant.helpers.dispatcher",
       async_dispatcher_connect=lambda *args: lambda: None)
module("homeassistant.helpers.event",
       async_track_state_change_event=lambda *args: lambda: None)
# No covers are selected in these fixtures; importing unrelated shade drivers
# is unnecessary for exercising the real configuration-platform setup.
module(PKG + ".shade_cooling", SHADE_NUMBERS={})

controls = importlib.import_module(PKG + ".device_controls")
model = importlib.import_module(PKG + ".equipment_model")
activation = importlib.import_module(PKG + ".device_activation")
copy_config = importlib.import_module(PKG + ".config_data").mutable_copy
platforms = {name: importlib.import_module(PKG + "." + name)
             for name in ("select", "number", "switch", "time")}


class Registry:
    def __init__(self):
        self.entities = {
            SOURCE: N(entity_id=SOURCE, id="source-registry-id", unique_id="native-heater",
                      device_id="physical-heater", area_id=AREA, platform="native"),
        }

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

    def async_get_entity_id(self, domain, platform, unique_id):
        return None

    def async_remove(self, entity_id):
        raise AssertionError("This setup has no obsolete registry entities")


class Fixture:
    _active = False

    def __init__(self, *, native=True, online=True, room=None, options=None):
        # This is the persisted shape from room_sources.store_selection():
        # inventory and per-device defaults, with no legacy enabled grant.
        selected = [SOURCE] if native else []
        saved = {
            "selected_devices": selected,
            "device_settings": {SOURCE: {"auto_control": False,
                                         "selection_generation": 1}} if native else {},
            "profiles": {"comfort": {"heat_c": 20, "cool_c": 26, "humidity": 58}},
            **deepcopy(room or {}),
        }
        self.entry = N(entry_id="entry", options=MappingProxyType(options or {}),
                       data=MappingProxyType({
                           "areas": [AREA],
                           "climate_rooms": {AREA: saved, "other": {"keep": "room"}},
                           "environment_rooms": {AREA: {}},
                           "room_sources": {AREA: {
                               "windows": [], "temperature": [], "humidity": [],
                               "air_quality": [], "climate_devices": selected,
                               "shades": [],
                           }},
                           "unrelated": {"keep": True},
                       }))
        self.entry.runtime_data = self
        self.unloads = []
        self.entry.async_on_unload = self.unloads.append
        self.spec = model.ManagedDevice("controller", AREA, "Room heater",
                                       "physical-heater", (SOURCE,))
        self._device_hierarchy = {"controllers": (
            {self.spec.identifier: {"spec": self.spec}} if native else {}
        )}
        state = N(state="off", attributes={
            "hvac_modes": ["off", "heat"], "supported_features": 1,
            "min_temp": 5, "max_temp": 35, "temperature_unit": "°C",
        })
        self.saved = []
        self.hass = N(
            states={SOURCE: state} if online else {},
            registry=Registry(), config=N(language="en", time_zone="UTC"),
            config_entries=N(async_update_entry=self.save),
            bus=N(async_listen=lambda *args: lambda: None),
        )  # No services interface: preference editing must never command hardware.
        self.equipment = N(records={}, statuses={})
        self.added = {}

    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}

    @property
    def room(self):
        return self.settings["climate_rooms"][AREA]

    def save(self, entry, *, options):
        self.saved.append(copy_config(options))
        entry.options = MappingProxyType(options)

    async def setup(self):
        for name, platform in platforms.items():
            entities = []
            await platform.async_setup_entry(
                self.hass, self.entry, lambda batch, **kwargs: entities.extend(batch),
            )
            self.added[name] = {entity.unique_id: entity for entity in entities}
            for entity in entities:
                entity.hass = self.hass

    def get(self, platform, suffix):
        return self.added[platform][f"entry_area_{AREA}_{suffix}"]


class NativeRoomSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_native_room_exposes_preferences_without_legacy_enable(self):
        for online in (True, False):
            for legacy_flag in ({}, {"enabled": False, "allow_actuation": False}):
                with self.subTest(online=online, legacy_flag=legacy_flag):
                    fixture = Fixture(online=online, room=legacy_flag)
                    original = copy_config(fixture.settings)
                    await fixture.setup()
                    self.assertEqual(fixture.get("select", "climate_policy_target_source").current_option,
                                     "temperature")
                    self.assertEqual(fixture.get("number", "climate_operating_comfort_adjustment_max_c").native_value,
                                     1.5)
                    self.assertFalse(fixture.get("switch", "climate_operating_sleep_active").is_on)
                    self.assertFalse(fixture.get("switch", "climate_operating_sleep_schedule_enabled").is_on)
                    self.assertEqual(fixture.get("time", "climate_sleep_start").native_value, time(22))
                    self.assertEqual(fixture.get("time", "climate_sleep_end").native_value, time(7))
                    self.assertNotIn(f"entry_area_{AREA}_manual_profile", fixture.added["select"])
                    self.assertEqual(copy_config(fixture.settings), original)
                    self.assertFalse(fixture.saved)
                    self.assertFalse(activation.authorized(fixture, fixture.spec))

    async def test_entity_actions_persist_without_arming_or_losing_other_settings(self):
        fixture = Fixture(online=False, room={"enabled": False, "allow_actuation": False})
        await fixture.setup()
        before_authority = activation.authority_context(fixture, fixture.spec)
        await asyncio.gather(
            fixture.get("select", "climate_policy_target_source").async_select_option("auto_comfort"),
            fixture.get("number", "climate_operating_comfort_adjustment_max_c").async_set_native_value(.4),
            fixture.get("switch", "climate_operating_sleep_active").async_turn_on(),
            fixture.get("time", "climate_sleep_start").async_set_value(time(23, 30)),
            fixture.get("time", "climate_sleep_end").async_set_value(time(6, 45)),
        )
        await fixture.get("switch", "climate_operating_sleep_schedule_enabled").async_turn_on()
        self.assertEqual(fixture.room["target_source"], "auto_comfort")
        self.assertEqual(fixture.room["comfort_adjustment_max_c"], .4)
        self.assertTrue(fixture.room["sleep_active"])
        self.assertTrue(fixture.room["sleep_schedule_enabled"])
        self.assertEqual((fixture.room["sleep_start"], fixture.room["sleep_end"]), ("23:30", "06:45"))
        self.assertEqual(fixture.room["profiles"]["comfort"]["humidity"], 58)
        self.assertEqual(fixture.settings["climate_rooms"]["other"], {"keep": "room"})
        self.assertEqual(fixture.settings["unrelated"], {"keep": True})
        self.assertIs(fixture.room["enabled"], False)
        self.assertIs(fixture.room["allow_actuation"], False)
        self.assertFalse(fixture.room["device_settings"][SOURCE]["auto_control"])
        self.assertEqual(activation.authority_context(fixture, fixture.spec), before_authority)
        self.assertFalse(activation.authorized(fixture, fixture.spec))
        self.assertNotIn(model.SETTINGS, fixture.entry.options)
        # A fresh manager/platform setup sees the saved settings while native
        # hardware remains unavailable; no transient planning copy is persisted.
        restored = Fixture(online=False, options=copy_config(fixture.entry.options))
        await restored.setup()
        self.assertEqual(restored.get("select", "climate_policy_target_source").current_option,
                         "auto_comfort")
        self.assertEqual(restored.get("time", "climate_sleep_start").native_value, time(23, 30))
        self.assertTrue(restored.get("switch", "climate_operating_sleep_active").is_on)
        self.assertFalse(restored.room["enabled"])

    async def test_monitoring_only_and_uncommissioned_relays_still_reject_preferences(self):
        for room in ({}, {"selected_devices": ["switch.uncommissioned"], "controller": "pwm"}):
            with self.subTest(room=room):
                fixture = Fixture(native=False, room=room)
                await fixture.setup()
                self.assertNotIn(f"entry_area_{AREA}_climate_policy_target_source", fixture.added["select"])
                self.assertNotIn(f"entry_area_{AREA}_climate_sleep_start", fixture.added["time"])
                for kind, key, value in (
                    ("climate_policy", "target_source", "auto_comfort"),
                    ("climate_operating", "sleep_active", True),
                    ("climate_schedule", "sleep_start", "23:00"),
                ):
                    with self.assertRaises(ValueError):
                        await controls.update_device_setting(fixture, kind, key, value, area=AREA)
                self.assertFalse(fixture.saved)

    async def test_native_preference_access_does_not_enable_legacy_controls(self):
        fixture = Fixture(room={"enabled": False, "controller": "pwm", "allow_actuation": False})
        await fixture.setup()
        self.assertFalse(any(getattr(entity, "_kind", None) == "direct_tuning"
                             for entity in fixture.added["number"].values()))
        self.assertNotIn(f"entry_area_{AREA}_climate_policy_away_policy", fixture.added["select"])
        for kind, key, value in (
            ("direct_tuning", "kp", 12),
            ("climate_policy", "away_policy", "all_home"),
            ("device_policy", "presence_requirement", "always"),
            ("device_target", "fan_speed_percent", 50),
        ):
            with self.assertRaises(ValueError):
                await controls.update_device_setting(fixture, kind, key, value,
                                                     area=AREA, entity_id=SOURCE)
        self.assertFalse(fixture.saved)

    async def test_enabled_legacy_room_keeps_original_policy_and_schedule_controls(self):
        fixture = Fixture(room={"enabled": True, "allow_actuation": False})
        await fixture.setup()
        self.assertIn(f"entry_area_{AREA}_manual_profile", fixture.added["select"])
        await fixture.get("select", "climate_policy_away_policy").async_select_option("all_home")
        await fixture.get("time", "climate_sleep_end").async_set_value(time(8))
        self.assertEqual(fixture.room["away_policy"], "all_home")
        self.assertEqual(fixture.room["sleep_end"], "08:00")
        self.assertFalse(fixture.room["allow_actuation"])

    async def test_invalid_sleep_schedule_cannot_be_enabled_but_can_be_repaired(self):
        clock = importlib.import_module(PKG + ".climate_schedule")
        for native in (True, False):
            for end in ("22:00", "invalid"):
                with self.subTest(native=native, end=end):
                    fixture = Fixture(native=native, room={
                        "enabled": not native, "allow_actuation": False,
                        "sleep_schedule_enabled": False,
                        "sleep_start": "22:00", "sleep_end": end,
                    })
                    await fixture.setup()
                    switch = fixture.get("switch", "climate_operating_sleep_schedule_enabled")
                    before = copy_config(fixture.settings)
                    with self.assertRaisesRegex(ValueError, "Invalid sleep interval"):
                        await switch.async_turn_on()
                    self.assertFalse(switch.is_on)
                    self.assertFalse(getattr(switch, "writes", 0))
                    self.assertFalse(fixture.saved)
                    self.assertEqual(copy_config(fixture.settings), before)

                    # A disabled schedule can be edited in either order, even
                    # when the other saved endpoint still needs repair.
                    await fixture.get("time", "climate_sleep_start").async_set_value(time(23))
                    await fixture.get("time", "climate_sleep_end").async_set_value(time(7))
                    await switch.async_turn_on()
                    self.assertTrue(switch.is_on)
                    self.assertEqual(clock.scheduled_sleep(fixture.room, 1704067200, "UTC"),
                                     (True, "local_overnight_interval"))
                    before = copy_config(fixture.settings)
                    writes = len(fixture.saved)
                    with self.assertRaisesRegex(ValueError, "Invalid sleep interval"):
                        await fixture.get("time", "climate_sleep_start").async_set_value(time(7))
                    self.assertEqual(copy_config(fixture.settings), before)
                    self.assertEqual(len(fixture.saved), writes)

                    await switch.async_turn_off()
                    await fixture.get("time", "climate_sleep_end").async_set_value(time(23))
                    self.assertFalse(switch.is_on)
                    self.assertEqual((fixture.room["sleep_start"], fixture.room["sleep_end"]),
                                     ("23:00", "23:00"))
                    self.assertIs(fixture.room["enabled"], not native)
                    self.assertFalse(fixture.room["allow_actuation"])

    async def test_previously_enabled_invalid_sleep_schedule_can_be_turned_off(self):
        for native in (True, False):
            with self.subTest(native=native):
                fixture = Fixture(native=native, room={
                    "enabled": not native, "allow_actuation": False,
                    "sleep_schedule_enabled": True,
                    "sleep_start": "22:00", "sleep_end": "22:00",
                })
                await fixture.setup()
                switch = fixture.get("switch", "climate_operating_sleep_schedule_enabled")
                self.assertTrue(switch.is_on)
                await switch.async_turn_off()
                self.assertFalse(switch.is_on)
                self.assertEqual((fixture.room["sleep_start"], fixture.room["sleep_end"]),
                                 ("22:00", "22:00"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
