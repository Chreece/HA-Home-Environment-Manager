"""Watchdog EquipmentSelect read path: bounded, mode-independent, no HA I/O.

Execute the actual production option resolver and the actual current_option
property, extracted with AST to keep this regression runnable without a full
Home Assistant installation. This tests code paths, not a substitute algorithm.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"


def function_module(filename, names):
    path = ROOT / filename
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    assert {node.name for node in nodes} == set(names)
    return ast.fix_missing_locations(ast.Module(
        body=[ast.ImportFrom(module="__future__",
                             names=[ast.alias(name="annotations")], level=0), *nodes],
        type_ignores=[]))


namespace = {
    "SETTINGS": "equipment_controllers",
    "DEVICE_SELECTS": {
        "off_state_watchdog_mode": ("monitor_recover", "monitor_only", "disabled"),
    },
}
exec(compile(function_module("equipment_model.py", {
    "_stored_settings", "power_switch_entity", "_watchdog_option", "watchdog_option",
}), str(ROOT / "equipment_model.py"), "exec"), namespace)

select_tree = ast.parse((ROOT / "select.py").read_text(encoding="utf-8"))
cls = next(node for node in select_tree.body if isinstance(node, ast.ClassDef)
           and node.name == "EquipmentSelect")
method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
              and node.name == "current_option")
select_namespace = {"equipment": NS(watchdog_option=namespace["watchdog_option"])}
exec(compile(ast.fix_missing_locations(ast.Module(
    body=[method], type_ignores=[])), str(ROOT / "select.py"), "exec"),
    select_namespace)


class NoDeepCopy:
    def __deepcopy__(self, memo):
        raise AssertionError("Inactive mode profile was deep-copied for a Select state")


class WatchdogProbe:
    _key = "off_state_watchdog_mode"
    current_option = select_namespace["current_option"]

    def __init__(self, manager, spec):
        self._manager, self._spec = manager, spec

    @property
    def controller_settings(self):
        raise AssertionError("Watchdog Select invoked the full mode/settings resolver")

    @property
    def options(self):
        raise AssertionError("Watchdog Select enumerated capabilities or other choices")


device_id = "living_room_purifier"
other_id = "another_device"
spec = NS(identifier=device_id)
# Simulate unrelated large per-mode settings that are irrelevant to this
# physical-controller-level preference. Never enumerate or copy these values.
records = {
    device_id: {
        "off_state_watchdog_mode": "monitor_only",
        "power_switch_entity": "switch.supply",
        "mode_settings_version": 1,
        "mode_settings": {"dry": {
            "pid_calibration": NoDeepCopy(),
            "profile_targets": {"sleep": list(range(50_000))},
        }},
    },
    other_id: {"off_state_watchdog_mode": "disabled",
               "profile_targets": NoDeepCopy()},
}
manager = NS(settings={namespace["SETTINGS"]: records})
probe = WatchdogProbe(manager, spec)
before = records[device_id]["mode_settings"]["dry"]["profile_targets"]
assert probe.current_option == "monitor_only"
assert namespace["power_switch_entity"](manager, spec) == "switch.supply"
assert namespace["power_switch_entity"](manager, NS(identifier=other_id)) is None
assert probe.current_option == namespace["watchdog_option"](manager, spec)
assert probe.current_option != namespace["watchdog_option"](
    manager, NS(identifier=other_id)), "Selected another physical controller"
assert records[device_id]["mode_settings"]["dry"]["profile_targets"] is before
for _ in range(1_000):
    assert probe.current_option == "monitor_only"

# Persisted values, absent legacy value and corrupt input retain b23 semantics.
for value in ("monitor_recover", "monitor_only", "disabled", None, False, 3,
              "invalid", [], {}):
    records[device_id]["off_state_watchdog_mode"] = value
    expected = value if value in namespace["DEVICE_SELECTS"]["off_state_watchdog_mode"] else "disabled"
    assert probe.current_option == expected, (value, probe.current_option)
records[device_id].pop("off_state_watchdog_mode")
assert probe.current_option == "monitor_recover"
manager.settings[namespace["SETTINGS"]][device_id] = None
assert probe.current_option == "monitor_recover"
manager.settings[namespace["SETTINGS"]] = None
assert probe.current_option == "monitor_recover"

# No mutation, state change, physical command, timer or session was required.
assert records[other_id]["off_state_watchdog_mode"] == "disabled"
assert before == {"sleep": list(range(50_000))}
print("PASS: actual watchdog Select read is controller-scoped O(1) and avoids all")
print("      inactive profile deepcopy, full resolver, capability scan and HA I/O")
