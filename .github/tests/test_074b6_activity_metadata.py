"""Activity role metadata shares planning evidence without issuing commands.

The production role resolver, effective-device projection, controller
inventory and climate attribute getter run against read-only HA transports.
No Home Assistant instance, physical device or network is needed.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_074b6_activity_metadata"


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    sys.modules[name] = result
    return result


module(PACKAGE, __path__=[str(SOURCE)])
module(PACKAGE + ".const", DOMAIN="environment_manager")
module(PACKAGE + ".device_hierarchy",
       configured_sources=lambda settings, area: settings["allowed"].get(area, ()))
module(PACKAGE + ".room_sources",
       selected=lambda settings, area, kind: settings["air"].get(area, ()))
module(PACKAGE + ".discovery",
       supported_metric=lambda hass, state, **kwargs: state.attributes.get("metric"))
module(PACKAGE + ".arrival_preparation", automatic_eligible=lambda cfg: False)
module(PACKAGE + ".operating_mode_catalog", operating_mode_ui_labels=lambda locale: {})
model = module(PACKAGE + ".equipment_model",
               settings=lambda manager, spec: manager.cfg,
               device_config=lambda manager, spec, entity: manager.device.get(entity, {}),
               room_config=lambda manager, spec: manager.room,
               capabilities=lambda manager, spec: manager.cap,
               specs=lambda manager: (manager.spec,),
               operating_modes=lambda manager, spec: ("fan_only",),
               plan_for=lambda manager, spec: {},
               profile_name=lambda cfg, plan: "home",
               permission=lambda *args: (False, False))
module("homeassistant", __path__=[])
module("homeassistant.helpers", __path__=[])
module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry)
activation = importlib.import_module(PACKAGE + ".device_activation")
inventory = importlib.import_module(PACKAGE + ".controller_inventory")


class ReadOnlyTransport:
    def __getattr__(self, name):
        raise AssertionError(f"Activity metadata attempted an external action: {name}")


class AttributeBase:
    @property
    def extra_state_attributes(self):
        return {"source_entity_ids": list(self._spec.source_entities)}


# Run the unmodified production getter with its real super() relationship.
# Unrelated climate-platform service methods do not participate in this read.
climate_tree = ast.parse((SOURCE / "climate.py").read_text())
climate_class = next(node for node in climate_tree.body
                     if isinstance(node, ast.ClassDef) and node.name == "ManagedClimate")
getters = [node for node in climate_class.body if isinstance(node, ast.FunctionDef)
           and node.name in ("extra_state_attributes", "_overview_targets")]
attribute_class = ast.ClassDef(name="ManagedClimate", bases=[ast.Name(id="AttributeBase", ctx=ast.Load())],
                              keywords=[], body=getters, decorator_list=[])
scope = {"__name__": PACKAGE + ".climate", "__package__": PACKAGE,
         "AttributeBase": AttributeBase, "model": model}
exec(compile(ast.fix_missing_locations(ast.Module(body=[attribute_class], type_ignores=[])),
             str(SOURCE / "climate.py"), "exec"), scope)


class ActivityMetadataTests(unittest.TestCase):
    def setUp(self):
        self.spec = N(identifier="purifier", area_id="room", name="Air unit",
                      source_device_id="native_device", source_entities=("fan.native",))
        self.states = {
            "fan.native": N(state="on", attributes={"percentage": 50}),
            "sensor.co2": N(state="800", attributes={"metric": "co2"}),
            "sensor.pm25": N(state="8", attributes={"metric": "pm25"}),
            "switch.supply": N(state="off", attributes={}),
        }
        registry = N(
            async_get_entity_id=lambda domain, platform, uid: "climate.hem_air",
            async_get=lambda entity: N(platform="environment_manager", config_entry_id="entry",
                                      unique_id="purifier_climate", disabled_by=None),
        )
        self.manager = N(
            spec=self.spec, cfg={"fan_purpose": "auto", "control_mode": "existing",
                                 "preset": "none", "requested_mode": "fan_only"},
            room={}, device={}, cap=N(primary="fan.native", modes=("off", "fan_only"), humidity=False,
                                      temperature=False, temperature_range=False),
            entry=N(entry_id="entry"),
            settings={"allowed": {"room": ["fan.native"]}, "air": {"room": []}},
            hass=N(states=self.states, registry=registry, services=ReadOnlyTransport(),
                   config_entries=ReadOnlyTransport()),
            equipment=N(records={}, statuses={}, active_control_mode=lambda spec: "fan_only",
                        measurements=lambda spec, cap: {"pm25": 8}),
        )

    def role(self):
        return activation.resolved_fan_purpose(self.manager, self.spec, "fan.native")

    def row(self):
        rows = inventory.controller_inventory(self.manager)
        self.assertEqual(len(rows), 1)
        return rows[0]

    def climate_attributes(self):
        view = scope["ManagedClimate"]()
        view._manager, view._spec = self.manager, self.spec
        view._caps = self.manager.cap
        view.controller_settings = self.manager.cfg
        view.preset_mode = "none"
        view._physical_hvac_mode = "fan_only"
        view._state = self.states.get("fan.native")
        return view.extra_state_attributes

    def test_active_targets_use_controller_mode_and_measurement_basis(self):
        view = scope["ManagedClimate"]()
        view._manager, view._spec = self.manager, self.spec
        cfg = {"control_mode": "automatic"}
        plan = {"air_actions": {"thresholds": {"co2_operational_ppm": 900, "pm25_short_term_action_ug_m3": 20}}}
        fan = self.manager.cap
        self.assertEqual(view._overview_targets(fan, cfg, plan, {}, "filtration"), {"pm25": 20})
        self.assertEqual(view._overview_targets(fan, cfg, plan, {}, "extraction"), {"co2": 900})
        self.assertEqual(view._overview_targets(fan, cfg, {}, {}, "filtration"), {})
        self.assertEqual(view._overview_targets(fan, {"control_mode": "off"}, plan, {}, "extraction"), {})
        reversible = N(temperature=True, temperature_range=True, modes=("off", "heat_cool"), humidity=False)
        with patch.object(model, "targets", return_value={"heat": 20, "cool": 24}, create=True):
            self.assertEqual(view._overview_targets(reversible, cfg, {}, {}, None), {"heat": 20, "cool": 24})
        dryer = N(temperature=False, temperature_range=False, humidity=True)
        basis = {"target_basis": "mold_surface_rh", "control_target": 60, "effective_humidity_target": 45}
        self.assertEqual(view._overview_targets(dryer, cfg, {}, basis, None), {"mold": 60})
        basis["target_basis"] = "room_relative_humidity"
        self.assertEqual(view._overview_targets(dryer, cfg, {}, basis, None), {"humidity": 45})

    def test_resolved_auto_roles_match_physical_planning(self):
        cases = (
            ({"purifier_fan_entity": "fan.native"}, ["co2", "pm25"], "filtration"),
            ({"extraction_fan_entity": "fan.native"}, ["co2", "pm25"], "extraction"),
            ({}, ["pm25"], "filtration"),
            ({}, ["co2"], "extraction"),
            ({}, ["co2", "pm25"], None),
            ({}, [], None),
            ({"purifier_fan_entity": "fan.other"}, ["co2", "pm25"], None),
        )
        for room, metrics, expected in cases:
            with self.subTest(room=room, metrics=metrics):
                self.manager.room = room
                self.manager.settings["air"]["room"] = ["sensor." + metric for metric in metrics]
                before = deepcopy((self.manager.cfg, self.manager.room, self.manager.device,
                                   self.manager.settings, self.manager.equipment.records, self.states))
                self.assertEqual(self.role(), expected)
                effective = activation.effective_device(self.manager, self.spec, "fan.native")
                self.assertEqual(effective.get("fan_purpose"), expected)
                self.assertEqual(self.row()["resolved_fan_purpose"], expected)
                self.assertEqual(self.climate_attributes()["resolved_fan_purpose"], expected)
                self.assertEqual(before, (self.manager.cfg, self.manager.room, self.manager.device,
                                         self.manager.settings, self.manager.equipment.records, self.states))

    def test_explicit_controller_and_device_precedence_remains_unchanged(self):
        self.manager.room = {"extraction_fan_entity": "fan.native"}
        self.manager.device["fan.native"] = {"fan_purpose": "filtration", "preserve": 7}
        self.assertEqual(self.role(), "filtration")
        self.manager.cfg["fan_purpose"] = "extraction"
        self.assertEqual(self.role(), "extraction")
        effective = activation.effective_device(self.manager, self.spec, "fan.native")
        self.assertEqual(effective["fan_purpose"], "extraction")
        self.assertEqual(effective["preserve"], 7)
        self.manager.cfg["fan_purpose"] = "auto"
        self.assertEqual(self.role(), "filtration")

        # Unrecognized persisted metadata is not reported as a known role;
        # the existing planning projection still preserves unrelated data.
        self.manager.room = {}
        self.manager.device["fan.native"]["fan_purpose"] = "legacy_unknown"
        self.assertIsNone(self.role())
        self.assertEqual(activation.effective_device(self.manager, self.spec, "fan.native")[
            "fan_purpose"], "legacy_unknown")

    def test_offline_inventory_keeps_identity_and_supply_observation(self):
        self.manager.room = {"purifier_fan_entity": "fan.native"}
        self.manager.cfg["power_switch_entity"] = "switch.supply"
        self.manager.cap = None
        self.states["fan.native"] = N(state="unavailable", attributes={})
        row = self.row()
        self.assertEqual(row["native_primary_entity_id"], "fan.native")
        self.assertEqual(row["resolved_fan_purpose"], "filtration")
        self.assertEqual(row["unavailable_source_entity_ids"], ["fan.native"])
        self.assertEqual(row["upstream_power_state"], "off")
        self.assertIsNone(self.climate_attributes()["resolved_fan_purpose"])
        self.states["switch.supply"] = N(state="unknown", attributes={})
        self.assertEqual(self.row()["upstream_power_state"], "unknown")
        del self.states["switch.supply"]
        self.assertIsNone(self.row()["upstream_power_state"])

    def test_multiple_sources_require_live_or_matching_cached_primary(self):
        self.spec.source_entities = ("climate.native", "fan.native")
        self.manager.settings["allowed"]["room"] = list(self.spec.source_entities)
        self.manager.room = {"purifier_fan_entity": "fan.native"}
        self.manager.settings["air"]["room"] = ["sensor.co2", "sensor.pm25"]
        self.manager.cap = N(primary="climate.native")
        row = self.row()
        self.assertEqual(row["native_primary_entity_id"], "climate.native")
        self.assertIsNone(row["resolved_fan_purpose"], "Companion fan role leaked to primary")

        self.manager.cap = None
        cached = {"capabilities": {"primary": "fan.native"},
                  "sources": list(self.spec.source_entities), "area": "room",
                  "source_device_id": self.spec.source_device_id}
        self.manager.equipment.records[self.spec.identifier] = cached
        self.assertEqual(self.row()["resolved_fan_purpose"], "filtration")
        for invalid in (
            {**cached, "sources": ["fan.native"]},
            {**cached, "area": "other_room"},
            {**cached, "source_device_id": "replaced_physical_device"},
            {**cached, "capabilities": {"primary": "fan.foreign"}},
            {},
        ):
            with self.subTest(record=invalid):
                self.manager.equipment.records[self.spec.identifier] = invalid
                row = self.row()
                self.assertIsNone(row["native_primary_entity_id"])
                self.assertIsNone(row["resolved_fan_purpose"])

    def test_unknown_primary_and_deselected_source_never_gain_role(self):
        self.manager.cfg["fan_purpose"] = "filtration"
        self.assertIsNone(activation.resolved_fan_purpose(self.manager, self.spec, None))
        self.assertIsNone(activation.resolved_fan_purpose(self.manager, self.spec, ""))
        self.manager.settings["allowed"]["room"] = []
        self.assertEqual(inventory.controller_inventory(self.manager), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
