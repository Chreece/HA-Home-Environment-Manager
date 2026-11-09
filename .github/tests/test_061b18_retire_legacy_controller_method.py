"""Regression: retire the obsolete device-wide method without touching mode controls.

The production registry migration is extracted directly from select.py. No
Home Assistant installation, physical device or network service is touched.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "custom_components/environment_manager/select.py").read_text()
TREE = ast.parse(SOURCE)
MIGRATION = next(node for node in TREE.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name == "_retire_device_wide_control_methods")
scope = {"DOMAIN": "environment_manager"}
exec(compile(ast.Module(body=[MIGRATION], type_ignores=[]),
             "custom_components/environment_manager/select.py", "exec"), scope)
retire = scope["_retire_device_wide_control_methods"]


class Registry:
    def __init__(self):
        # A user-renamed entity still has its permanent HA unique_id.
        self.registered = {
            ("select", "environment_manager", "controllerA_control_mode"):
                "select.my_custom_name",
            ("select", "environment_manager", "controllerB_control_mode"):
                "select.legacy_b",
            ("select", "environment_manager", "controllerA_mode_heat_control_mode"):
                "select.heat_pid",
            ("select", "environment_manager", "controllerA_mode_cool_control_mode"):
                "select.cool_pid",
            ("select", "environment_manager", "controllerB_mode_dry_control_mode"):
                "select.dry_pid",
            ("select", "another_integration", "controllerA_control_mode"):
                "select.some_other_integrations_control",
            ("select", "environment_manager", "unselected_device_control_mode"):
                "select.different_physical_device",
            ("number", "environment_manager", "controllerA_control_mode"):
                "number.unrelated",
        }
        self.lookups = []
        self.deleted = []

    def async_get_entity_id(self, domain, platform, unique_id):
        self.lookups.append((domain, platform, unique_id))
        return self.registered.get((domain, platform, unique_id))

    def async_remove(self, entity_id):
        matching = [key for key, value in self.registered.items()
                    if value == entity_id]
        assert len(matching) == 1, entity_id
        self.deleted.append(entity_id)
        del self.registered[matching[0]]


registry = Registry()
saved_settings = {
    "controllerA": {"control_mode": "pid", "mode_settings": {
        "heat": {"control_mode": "pid"}, "cool": {"control_mode": "automatic"}}},
    "controllerB": {"control_mode": "manual",
                    "mode_settings": {"dry": {"control_mode": "pid"}}},
}
unchanged = deepcopy(saved_settings)
specs = [NS(identifier="controllerA"), NS(identifier="controllerB")]
retire(registry, specs)
assert registry.deleted == ["select.my_custom_name", "select.legacy_b"]
assert registry.lookups == [
    ("select", "environment_manager", "controllerA_control_mode"),
    ("select", "environment_manager", "controllerB_control_mode"),
]
assert len(registry.registered) == 6
assert {value for value in registry.registered.values()} == {
    "select.heat_pid", "select.cool_pid", "select.dry_pid",
    "select.some_other_integrations_control",
    "select.different_physical_device", "number.unrelated",
}
retire(registry, specs)
assert registry.deleted == ["select.my_custom_name", "select.legacy_b"]
assert saved_settings == unchanged, "Retirement must not alter persisted PID/manual values"

# The setup must call this exact migration and only register per-mode method
# entities. A device-wide selector must not sneak back through a new alias.
setup = next(node for node in TREE.body if isinstance(node, ast.AsyncFunctionDef)
             and node.name == "async_setup_entry")
calls = [node for node in ast.walk(setup) if isinstance(node, ast.Call)]
assert any(isinstance(node.func, ast.Name)
           and node.func.id == "_retire_device_wide_control_methods"
           for node in calls)
assert not any(isinstance(node.func, ast.Name)
               and node.func.id == "EquipmentSelect"
               and len(node.args) >= 3
               and isinstance(node.args[2], ast.Constant)
               and node.args[2].value == "control_mode"
               and not any(k.arg == "operating_mode" for k in node.keywords)
               for node in calls)
assert any(isinstance(node.func, ast.Name)
           and node.func.id == "scoped_fields"
           for node in calls)
print("HEM_B18_LEGACY_METHOD_REMOVED_AND_PER_MODE_METHODS_RETAINED=PASS")
