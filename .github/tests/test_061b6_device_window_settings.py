"""Device airing preferences persist independently without touching actuators."""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = runpy.run_path(str(ROOT / ".github/tests/test_beta110_device_setting.py"))
model, platform = BASE["model"], BASE["platform"]


class NumberBase:
    available = True


namespace = {
    "__name__": BASE["PKG"] + ".number", "__package__": BASE["PKG"],
    "EquipmentEntity": platform.EquipmentEntity, "NumberEntity": NumberBase,
    "equipment": model, "NumberMode": N(BOX="box"),
    "EntityCategory": N(CONFIG="config"), "callback": lambda method: method,
}
tree = ast.parse((ROOT / "number.py").read_text())
nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
         and node.name in ("EquipmentNumber", "_equipment_numbers", "_registered_number")]
exec(compile(ast.Module(nodes, []), "number.py", "exec"), namespace)


class WindowSettingsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = BASE["SettingTests"]()
        self.fixture.setUp()
        self.manager = self.fixture.manager
        self.a, self.b = self.fixture.a, self.fixture.b

    async def test_default_off_strict_boolean_and_independent_persistence(self):
        switch = platform.EquipmentWindowAnnouncementSwitch(self.manager, self.a)
        other = platform.EquipmentWindowAnnouncementSwitch(self.manager, self.b)
        self.assertFalse(switch.is_on)
        self.assertEqual(model.settings(self.manager, self.a)["window_open_timeout_minutes"], 5)
        cfg = self.manager.entry.options[model.SETTINGS][self.a.identifier]
        for invalid in (None, "true", "false", 1, 0, [], {}):
            cfg["announce_before_start"] = invalid
            self.assertFalse(switch.is_on)
        before = deepcopy(self.manager.entry.options)
        records = deepcopy(self.fixture.holds)
        self.fixture.states.clear()
        self.manager.equipment._tasks[self.a.identifier] = N(done=lambda: False)
        self.assertTrue(switch.available)
        await switch.async_turn_on()
        before[model.SETTINGS][self.a.identifier]["announce_before_start"] = True
        self.assertEqual(self.manager.entry.options, before)
        self.assertTrue(platform.EquipmentWindowAnnouncementSwitch(self.manager, self.a).is_on)
        self.assertFalse(other.is_on)
        await switch.async_turn_off()
        self.assertFalse(switch.is_on)
        self.assertEqual(self.fixture.holds, records)
        self.assertEqual(switch.extra_state_attributes["window_announcement_role"], "policy")

    async def test_number_stays_editable_offline_and_uses_own_profile(self):
        number = namespace["EquipmentNumber"](self.manager, self.a, "window_open_timeout_minutes")
        self.assertEqual((number._attr_native_min_value, number._attr_native_max_value), (0, 30))
        self.assertEqual(number._attr_native_unit_of_measurement, "min")
        self.assertEqual(number.native_value, 5)
        records = deepcopy(self.fixture.holds)
        self.fixture.states.clear()
        self.manager.equipment._tasks[self.a.identifier] = N(done=lambda: False)
        self.assertTrue(number.available)
        for value in (0, 7, 30):
            await number.async_set_native_value(value)
            self.assertEqual(number.native_value, value)
        self.assertEqual(model.settings(self.manager, self.b)["window_open_timeout_minutes"], 5)
        self.assertEqual(self.fixture.holds, records)
        self.assertEqual(number.extra_state_attributes["window_announcement_role"], "timeout")

    async def test_invalid_preferences_do_not_change_saved_authority(self):
        before = deepcopy(self.manager.entry.options)
        for payload in ({"announce_before_start": "true"}, {"announce_before_start": 1},
                        {"window_open_timeout_minutes": True},
                        {"window_open_timeout_minutes": -1},
                        {"window_open_timeout_minutes": 31},
                        {"window_open_timeout_minutes": float("nan")},
                        {"window_open_timeout_minutes": float("inf")},
                        {"announce_before_start": True, "control_mode": "automatic"}):
            with self.assertRaises(ValueError):
                await self.manager.equipment.async_update(self.a, payload)
        self.assertEqual(self.manager.entry.options, before)

    def test_indoor_remediation_capabilities_exclude_extraction(self):
        cfg = self.manager.entry.options[model.SETTINGS][self.a.identifier]
        for cap in (
            model.Capabilities("climate.a", "climate", ("off", "dry"), humidity=True),
            model.Capabilities("humidifier.a", "humidifier", ("off", "auto"), humidity=True, humidifying=True),
            model.Capabilities("switch.a", "switch", ("off", "heat")),
        ):
            self.assertTrue(model.window_alternative_supported(self.manager, self.a, cap))
        fan = model.Capabilities("fan.a", "fan", ("off", "fan_only"))
        cfg["fan_purpose"] = "extraction"
        self.assertFalse(model.window_alternative_supported(self.manager, self.a, fan))
        cfg["fan_purpose"] = "filtration"
        self.assertTrue(model.window_alternative_supported(self.manager, self.a, fan))

    def test_all_supported_names_and_help_are_available(self):
        names = BASE["names"]
        for locale in names.EQUIPMENT_TRANSLATED_NAMES:
            for key in ("announce_before_start", "window_open_timeout_minutes"):
                label = names.localized_equipment_name(key, locale, "Channel · ")
                self.assertIn("Channel · ", label)
                self.assertIn(" · ", label)
                self.assertNotIn("{", label)

    async def test_purifier_role_change_registers_control_once_without_restart(self):
        fan = BASE["Device"]("filter", "room", "Fan", "fan_device", ("fan.filter",))
        self.fixture.devices.append(fan)
        self.manager._device_hierarchy["controllers"][fan.identifier] = {"spec": fan}
        self.manager.entry.data["sources"]["room"].append("fan.filter")
        self.fixture.states["fan.filter"] = N(state="off", attributes={"supported_features": 1})
        self.manager.entry.options[model.SETTINGS][fan.identifier] = {"fan_purpose": "extraction"}
        added = []
        await platform.async_setup_entry(self.manager.hass, self.manager.entry, added.extend)
        def controls():
            return [e for e in added if isinstance(e, platform.EquipmentWindowAnnouncementSwitch)
                    and e._spec.identifier == fan.identifier]
        self.assertEqual(controls(), [])
        self.manager.entry.options[model.SETTINGS][fan.identifier]["fan_purpose"] = "filtration"
        self.manager.hass.policy_change()
        self.manager.hass.policy_change()
        self.assertEqual(len(controls()), 1)
        self.assertFalse(controls()[0].is_on)


if __name__ == "__main__":
    unittest.main(verbosity=2)
