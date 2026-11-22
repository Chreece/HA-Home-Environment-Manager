"""Exercise quiet-hours form validation, native editors and shared persistence."""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import time, timezone
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
fixture_path = ROOT / ".github/tests/test_061b5_language_settings.py"
fixture = ModuleType("hem080_quiet_settings_fixture")
fixture.__file__ = str(fixture_path)
tree = ast.parse(fixture_path.read_text())
root_node = next(node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "ROOT"
                         for target in node.targets))
root_node.value = ast.Call(func=ast.Name(id="Path", ctx=ast.Load()),
                          args=[ast.Constant(str(SOURCE))], keywords=[])
sys.modules[fixture.__name__] = fixture
exec(compile(ast.fix_missing_locations(tree), str(fixture_path), "exec"), fixture.__dict__)
fixture.ns.update(TimeEntity=fixture.Entity, time=time)
fixture.production("time.py", {"HomeQuietHoursTime"}, fixture.ns)
HomeQuietHoursTime = fixture.ns["HomeQuietHoursTime"]
update = fixture.ns["update_device_setting"]
text = importlib.import_module(fixture.PKG + ".quiet_hours_text").QUIET_HOURS_TEXT

ENABLED = "quiet_hours_enabled"
START = "quiet_hours_start"
END = "quiet_hours_end"


class QuietHoursSettingsTests(unittest.IsolatedAsyncioTestCase):
    async def test_defaults_are_disabled_and_reading_form_does_not_save(self):
        flow = fixture.GeneralFlow(language="el", keep={"existing": 17})
        before = deepcopy(flow._values)
        form = await flow.async_step_setup_general()
        fields = {str(key): (key.default, widget.kind)
                  for key, widget in form["data_schema"].items()}
        self.assertEqual(fields[ENABLED], (False, "BooleanSelector"))
        self.assertEqual(fields[START], ("22:00:00", "TimeSelector"))
        self.assertEqual(fields[END], ("08:00:00", "TimeSelector"))
        self.assertEqual(flow._values, before)
        self.assertEqual(flow.saved, 0)

    async def test_overnight_and_same_day_schedules_save_atomically(self):
        for start, end in (("22:30", "08:15"), ("12:00:05", "14:15:25")):
            with self.subTest(start=start):
                flow = fixture.GeneralFlow(language="de", keep={"existing": 17})
                result = await flow.async_step_setup_general({
                    ENABLED: True, START: start, END: end,
                })
                self.assertTrue(result["saved"][ENABLED])
                self.assertEqual(result["saved"][START], time.fromisoformat(start).isoformat())
                self.assertEqual(result["saved"][END], time.fromisoformat(end).isoformat())
                self.assertEqual(result["saved"]["keep"], {"existing": 17})
                self.assertEqual(result["saved"]["language"], "de")
                self.assertEqual(flow.saved, 1)

    async def test_invalid_form_does_not_partially_change_unrelated_settings(self):
        invalids = (
            {ENABLED: "true"}, {START: "24:00"}, {END: "08:60"},
            {START: None}, {END: True}, {START: "22:00+01:00"},
            {START: "22:00:00.500"}, {ENABLED: True, START: "08:00", END: "08:00:00"},
        )
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                flow = fixture.GeneralFlow(language="el", **{
                    ENABLED: False, START: "22:00:00", END: "08:00:00",
                })
                before = deepcopy(flow._values)
                form = await flow.async_step_setup_general({"language": "de", **invalid})
                self.assertIn("invalid_quiet_hours", form["errors"].values())
                self.assertEqual(flow._values, before)
                self.assertEqual(flow.saved, 0)

    async def test_disabled_equal_interval_can_be_repaired_but_not_enabled(self):
        manager = fixture.Manager(**{START: "08:00:00", END: "08:00:00"})
        with self.assertRaises(ValueError):
            await update(manager, "global_setting", ENABLED, True)
        self.assertEqual(manager.saved, [])
        await update(manager, "global_setting", START, time(22, 30))
        await update(manager, "global_setting", ENABLED, True)
        self.assertEqual(manager.settings[START], "22:30:00")
        self.assertTrue(manager.settings[ENABLED])
        with self.assertRaises(ValueError):
            await update(manager, "global_setting", END, "22:30:00")
        self.assertEqual(manager.settings[END], "08:00:00")
        manager.entry.options[END] = "invalid"
        await update(manager, "global_setting", ENABLED, False)
        self.assertFalse(manager.settings[ENABLED])

    async def test_native_times_share_form_values_and_never_target_one_room(self):
        manager = fixture.Manager(language="el", **{ENABLED: True})
        start = HomeQuietHoursTime(manager, manager.entry.entry_id, START)
        end = HomeQuietHoursTime(manager, manager.entry.entry_id, END)
        self.assertEqual(start._attr_unique_id, "existing_entry_home_quiet_hours_start")
        self.assertEqual(start.native_value, time(22))
        self.assertEqual(end.native_value, time(8))
        await start.async_set_value(time(23, 15, 30))
        await end.async_set_value(time(7, 45))
        self.assertEqual(manager.settings[START], "23:15:30")
        self.assertEqual(manager.settings[END], "07:45:00")
        self.assertEqual(manager.settings["keep"], {"room": "unchanged"})
        self.assertEqual(manager.settings["language"], "el")
        before = deepcopy(manager.settings)
        for key, value in ((START, "25:00"), (END, time(8, tzinfo=timezone.utc)),
                           (ENABLED, 1)):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    await update(manager, "global_setting", key, value)
                self.assertEqual(manager.settings, before)
        for key, value in ((START, "22:00"), (END, "06:00"), (ENABLED, False)):
            with self.assertRaises(ValueError):
                await update(manager, "global_setting", key, value, area="bedroom")
        self.assertEqual(manager.settings, before)
        manager.entry.options[START] = "invalid"
        self.assertIsNone(start.native_value)

    async def test_native_times_update_when_general_options_change(self):
        manager = fixture.Manager()
        entity = HomeQuietHoursTime(manager, manager.entry.entry_id, START)
        entity.hass = manager.hass
        await entity.async_added_to_hass()
        self.assertEqual(len(manager.hass.listeners), 1)
        manager.entry.options[START] = "21:30:00"
        next(iter(manager.hass.listeners.values()))()
        self.assertEqual(entity.native_value, time(21, 30))
        self.assertEqual(entity.writes, 1)
        for remove in entity.removers:
            remove()
        self.assertFalse(manager.hass.listeners)

    def test_labels_help_and_errors_are_complete_in_every_supported_language(self):
        self.assertEqual(set(text), set(fixture.languages.SUPPORTED_LANGUAGE_TAGS))
        for locale, labels in text.items():
            with self.subTest(locale=locale):
                catalog = json.loads((SOURCE / "translations" / f"{locale}.json").read_text())
                for surface in ("config", "options"):
                    form = catalog[surface]["step"]["setup_general"]
                    for key, prefix in ((ENABLED, "enabled"), (START, "start"), (END, "end")):
                        self.assertEqual(form["data"][key], labels[prefix + "_label"])
                        self.assertEqual(form["data_description"][key], labels[prefix + "_help"])
                    self.assertEqual(catalog[surface]["error"]["invalid_quiet_hours"], labels["invalid_error"])
                self.assertEqual(catalog["entity"]["switch"]["equipment_quiet_hours"]["name"], labels["device_label"])
                for key, prefix in ((START, "start"), (END, "end")):
                    manager = fixture.Manager()
                    manager.hass.config.language = locale
                    entity = HomeQuietHoursTime(manager, manager.entry.entry_id, key)
                    self.assertEqual(entity.name, labels[prefix + "_label"])
                    self.assertEqual(entity.extra_state_attributes["configuration_help"], labels[prefix + "_help"])


if __name__ == "__main__":
    unittest.main()
