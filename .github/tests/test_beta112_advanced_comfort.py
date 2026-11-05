"""Ordinary room controls and explicit ISO 7730 opt-in using production code.

Only HA registry/entity transport is simulated. The actual migration, entity
constructors, setting writer, switch/select actions and comfort gates run.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, replace
import importlib
import math
from pathlib import Path
import sys
from types import MappingProxyType, ModuleType, SimpleNamespace as N
from typing import Any
import unittest

ROOT = Path(__file__).resolve().parents[2]
PKG = "hem_beta112_comfort"


def module(name, **attrs):
    value = ModuleType(name)
    value.__dict__.update(attrs)
    sys.modules[name] = value
    return value


module(PKG, __path__=[str(ROOT)])
module("homeassistant", __path__=[])
module("homeassistant.helpers", __path__=[])
registry_module = module(
    "homeassistant.helpers.entity_registry",
    RegistryEntryDisabler=N(INTEGRATION="integration", USER="user"),
    async_get=lambda hass: hass.registry,
)
advanced = importlib.import_module(PKG + ".advanced_comfort")
const = importlib.import_module(PKG + ".const")
copy_config = importlib.import_module(PKG + ".config_data").mutable_copy
science = importlib.import_module(PKG + ".environment_science")
comfort = importlib.import_module(PKG + ".comfort_targets")


def production_nodes(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in names:
                selected.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names
            for target in node.targets
        ):
            selected.append(node)
    exec(compile(ast.Module(body=selected, type_ignores=[]), filename, "exec"), namespace)


control_names = {
    "GLOBAL_ENV_NUMBERS", "GLOBAL_OCCUPANCY_NUMBERS", "AREA_ENV_NUMBERS",
    "CLIMATE_OPERATING_NUMBERS", "AREA_ENV_FLAGS", "GLOBAL_ENV_FLAGS",
    "CLIMATE_OPERATING_FLAGS", "CLIMATE_POLICY_OPTIONS", "DEVICE_POLICY_OPTIONS",
    "_finite", "climate_settings", "update_device_setting",
}
control_ns = {
    **vars(const), "__package__": PKG, "__name__": PKG + ".device_controls",
    "Any": Any, "asyncio": asyncio, "math": math, "deepcopy": copy_config,
    "HomeAssistantError": ValueError,
}
production_nodes("device_controls.py", control_names, control_ns)


class Entity:
    _attr_entity_registry_enabled_default = True

    def async_write_ha_state(self):
        self.writes = getattr(self, "writes", 0) + 1


entity_ns = {
    "SettingsMetadata": importlib.import_module(PKG + ".settings_help").SettingsMetadata,
    **vars(const), **{name: control_ns[name] for name in control_names},
    "__package__": PKG, "__name__": PKG + ".entity_fixture",
    "callback": lambda fn: fn, "EntityCategory": N(CONFIG="config"),
    "NumberMode": N(BOX="box"), "NumberEntity": Entity,
    "SwitchEntity": Entity, "SelectEntity": Entity,
}
production_nodes("number.py", {"ConfigNumber"}, entity_ns)
production_nodes("switch.py", {"HomeSettingSwitch"}, entity_ns)
production_nodes("select.py", {"ConfigSelect", "AreaScienceSource"}, entity_ns)
ConfigNumber = entity_ns["ConfigNumber"]
HomeSettingSwitch = entity_ns["HomeSettingSwitch"]
ConfigSelect = entity_ns["ConfigSelect"]
AreaScienceSource = entity_ns["AreaScienceSource"]


@dataclass(frozen=True)
class RegistryEntry:
    entity_id: str
    unique_id: str
    config_entry_id: str = "hem-entry"
    platform: str = "environment_manager"
    disabled_by: str | None = None
    name: str | None = "Custom name"


class Registry:
    def __init__(self):
        self.entries = {}
        self.updates = []

    def async_get_entity_id(self, domain, platform, unique_id):
        return next((eid for eid, item in self.entries.items()
                     if eid.partition(".")[0] == domain
                     and item.platform == platform and item.unique_id == unique_id), None)

    def async_get(self, entity_id):
        return self.entries.get(entity_id)

    def async_update_entity(self, entity_id, **changes):
        self.updates.append((entity_id, changes))
        self.entries[entity_id] = replace(self.entries[entity_id], **changes)

    def add_room(self, area):
        identifiers = []
        for domain, suffix in (
            ("number", "area_environment_air_speed_m_s"),
            ("number", "area_environment_met"),
            ("number", "area_environment_clo"),
            ("select", "area_science_radiant_temperature_entity"),
            ("select", "area_science_air_speed_entity"),
            ("switch", "area_environment_enable_pmv"),
        ):
            eid = f"{domain}.renamed_{area}_{len(identifiers)}"
            self.entries[eid] = RegistryEntry(eid, f"hem-entry_area_{area}_{suffix}")
            identifiers.append(eid)
        return identifiers


class Manager:
    _active = False

    def __init__(self, data=None):
        self.entry = N(
            entry_id="hem-entry", options=MappingProxyType({}),
            data=MappingProxyType(data or {"areas": ["room"], "environment_rooms": {"room": {}}}),
        )
        self.saved = []
        self.hass = N(
            registry=Registry(),
            config_entries=N(async_update_entry=self.save),
        )  # No service interface: configuration cannot send physical commands.

    @property
    def settings(self):
        return {**self.entry.data, **self.entry.options}

    def save(self, entry, **changes):
        self.saved.append(copy_config(changes))
        for name, value in changes.items():
            setattr(entry, name, MappingProxyType(value))


class AdvancedComfortTests(unittest.IsolatedAsyncioTestCase):
    def test_ordinary_defaults_and_explicit_legacy_pmv_controls(self):
        manager = Manager({
            "areas": ["ordinary", "calculation", "target"],
            "environment_rooms": {"calculation": {"enable_pmv": True, "met": 1.2}},
            "climate_rooms": {"target": {"target_source": "pmv"}},
        })
        for area, expected in (("ordinary", False), ("calculation", True), ("target", True)):
            with self.subTest(area=area):
                controls = [ConfigNumber(manager, "hem-entry", area, "area_environment", key,
                                         control_ns["AREA_ENV_NUMBERS"][key][:4])
                            for key in ("air_speed_m_s", "met", "clo")]
                controls.extend(AreaScienceSource(manager, "hem-entry", area, key)
                                for key in ("radiant_temperature_entity", "air_speed_entity"))
                controls.append(HomeSettingSwitch(manager, "hem-entry", "enable_pmv",
                                                  kind="area_environment", area=area))
                self.assertEqual([item._attr_entity_registry_enabled_default for item in controls],
                                 [expected] * 6)
                self.assertEqual(controls[1].native_value, 1.2 if area == "calculation" else None)
        normal = ConfigNumber(manager, "hem-entry", "ordinary", "area_environment",
                              "room_volume_m3", (1, 30000, 1, "m³"))
        self.assertTrue(normal._attr_entity_registry_enabled_default)

    def test_upgrade_disables_only_inactive_owned_iso_entities_and_preserves_data(self):
        manager = Manager({
            "areas": ["room", "pmv", "target"],
            "environment_rooms": {"room": {"met": 1.2, "clo": .7, "air_speed_m_s": .1},
                                  "pmv": {"enable_pmv": True}},
            "climate_rooms": {"target": {"target_source": "pmv"}},
            "equipment_controllers": {"heater": {"control_mode": "pid"}},
        })
        original = copy_config(manager.entry.data)
        registry = manager.hass.registry
        basic = registry.add_room("room")
        active = registry.add_room("pmv") + registry.add_room("target")
        registry.entries[basic[2]] = replace(registry.entries[basic[2]], disabled_by="user")
        registry.entries[basic[4]] = replace(registry.entries[basic[4]], config_entry_id="other-entry")
        registry.entries["number.room_volume"] = RegistryEntry(
            "number.room_volume", "hem-entry_area_room_area_environment_room_volume_m3",
        )
        before = dict(registry.entries)
        advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        self.assertEqual(set(eid for eid, _ in registry.updates), {basic[0], basic[1], basic[3], basic[5]})
        for eid in active + [basic[2], basic[4], "number.room_volume"]:
            self.assertEqual(registry.entries[eid], before[eid])
        for eid, changes in registry.updates:
            self.assertEqual(changes, {"disabled_by": "integration"})
            self.assertEqual(registry.entries[eid], replace(before[eid], disabled_by="integration"))
        self.assertEqual(copy_config(manager.entry.data),
                         {**original, advanced.MIGRATION_KEY: advanced.MIGRATION_VERSION})
        self.assertEqual(dict(manager.entry.options), {})

    def test_once_only_migration_keeps_later_user_enable_and_disable_choices(self):
        manager = Manager()
        registry = manager.hass.registry
        controls = registry.add_room("room")
        advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        registry.async_update_entity(controls[1], disabled_by=None)
        registry.async_update_entity(controls[2], disabled_by="user")
        registry.updates.clear()
        manager.saved.clear()
        for _ in range(3):
            advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        self.assertEqual(registry.updates, [])
        self.assertEqual(manager.saved, [])
        self.assertIsNone(registry.entries[controls[1]].disabled_by)
        self.assertEqual(registry.entries[controls[2]].disabled_by, "user")

    async def test_explicit_switch_on_exposes_inputs_without_inventing_missing_values(self):
        manager = Manager()
        registry = manager.hass.registry
        controls = registry.add_room("room")
        advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        registry.async_update_entity(controls[2], disabled_by="user")
        # The user enables the optional ISO switch in HA, then turns it on.
        registry.async_update_entity(controls[5], disabled_by=None)
        switch = HomeSettingSwitch(manager, "hem-entry", "enable_pmv",
                                   kind="area_environment", area="room")
        switch.hass = manager.hass
        await switch.async_turn_on()
        self.assertTrue(switch.is_on)
        self.assertEqual(manager.settings["environment_rooms"]["room"], {"enable_pmv": True})
        self.assertEqual(switch.extra_state_attributes["input_validation"], "pending_inputs")
        self.assertEqual(set(switch.extra_state_attributes["missing_configured_inputs"]),
                         {"radiant_temperature_entity", "met", "clo", "air_speed"})
        for i, eid in enumerate(controls):
            self.assertEqual(registry.entries[eid].disabled_by, "user" if i == 2 else None)
        self.assertEqual(science.pmv_iso7730(21, None, 50, None, None, None)["status"],
                         "missing_or_outside_iso7730_inputs")
        self.assertEqual(comfort.solve_pmv_air_temperature(None, 50, None, None, None)["status"],
                         "insufficient_physical_inputs")
        registry.updates.clear()
        await switch.async_turn_off()
        advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        self.assertEqual(registry.updates, [])
        self.assertFalse(switch.is_on)

    async def test_explicit_pmv_target_selection_exposes_optional_switch_and_inputs(self):
        manager = Manager({"areas": ["room"], "environment_rooms": {"room": {}},
                           "climate_rooms": {"room": {"enabled": True, "target_source": "temperature"}}})
        registry = manager.hass.registry
        controls = registry.add_room("room")
        advanced.async_migrate_advanced_comfort(manager.hass, manager.entry)
        registry.async_update_entity(controls[2], disabled_by="user")
        selection = ConfigSelect(manager, "hem-entry", "room", "climate_policy",
                                 ("temperature", "auto_comfort", "pmv"), setting_key="target_source")
        selection.hass = manager.hass
        await selection.async_select_option("pmv")
        self.assertEqual(selection.current_option, "pmv")
        self.assertEqual(manager.settings["environment_rooms"]["room"], {})
        for i, eid in enumerate(controls):
            self.assertEqual(registry.entries[eid].disabled_by, "user" if i == 2 else None)

    async def test_ordinary_legacy_wizard_skips_iso_form_but_explicit_pmv_keeps_validation(self):
        tree = ast.parse((ROOT / "config_flow.py").read_text())
        function = next(node for node in ast.walk(tree)
                        if isinstance(node, ast.AsyncFunctionDef)
                        and node.name == "async_step_environment_room_comfort")
        namespace = {"__package__": PKG, "Any": Any, "ConfigFlowResult": dict,
                     "CONF_ENVIRONMENT_ROOMS": "environment_rooms", "math": math,
                     "_marker": lambda key, value=None: key, "_optional_sensor": lambda: "sensor",
                     "probatio": N(Schema=lambda fields: fields)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "config_flow.py", "exec"), namespace)

        class Flow:
            async_step_environment_room_comfort = namespace["async_step_environment_room_comfort"]

            def __init__(self, enabled=False):
                self._values = {"environment_rooms": MappingProxyType({"other": {"met": 1.4}})}
                self._environment_room_data = {"room_volume_m3": 45, **({"enable_pmv": True} if enabled else {})}
                self._environment_area = "room"

            def _environment_area_name(self):
                return "Room"

            def async_show_form(self, **kw):
                return {"type": "form", **kw}

            async def _finish(self):
                return {"type": "save", "data": copy_config(self._values)}

        plain = await Flow().async_step_environment_room_comfort()
        self.assertEqual(plain["type"], "save")
        self.assertEqual(plain["data"]["environment_rooms"],
                         {"other": {"met": 1.4}, "room": {"room_volume_m3": 45}})
        advanced_flow = Flow(enabled=True)
        initial = await advanced_flow.async_step_environment_room_comfort()
        self.assertEqual(initial["type"], "form")
        self.assertEqual(set(initial["data_schema"]), {"radiant_temperature_entity", "air_speed_entity"})
        missing = await advanced_flow.async_step_environment_room_comfort({})
        self.assertEqual(missing["errors"], {"base": "pmv_requires_explicit_inputs"})

    def test_everyday_automatic_comfort_does_not_need_specialist_inputs(self):
        result = comfort.automatic_comfort_band(21, 25, 50)
        self.assertEqual(result["status"], "humidity_aware_estimate")
        self.assertEqual((result["heat_c"], result["cool_c"]), (21, 25))
        missing = comfort.automatic_comfort_band(21, 25, None)
        self.assertEqual(missing["status"], "fixed_targets_missing_humidity")
        self.assertEqual((missing["heat_c"], missing["cool_c"]), (21, 25))


if __name__ == "__main__":
    unittest.main(verbosity=2)
