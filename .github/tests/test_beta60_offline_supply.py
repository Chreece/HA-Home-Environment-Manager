"""Beta60 offline switch commissioning: exercise actual source code, no HA startup."""
from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def functions(file, names, globals_):
    nodes = ast.parse(source(file)).body
    chosen = [
        node for node in nodes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    assert {n.name for n in chosen} == set(names)
    exec(compile(ast.Module(body=chosen, type_ignores=[]), file, "exec"), globals_)
    return [globals_[name] for name in names]


def finite(value, low, high):
    try:
        number = float(value)
        return number if low <= number <= high else None
    except (TypeError, ValueError):
        return None


st = lambda state, domain="climate": NS(state=state, domain=domain, attributes={})
states = {
    "switch.plug": st("off", "switch"),
    "climate.appliance": st("unavailable"),
}
hass = NS(states=NS(get=states.get))
spec = NS(identifier="test_controller", area_id="guest", source_device_id="appliance",
          source_entities=("climate.appliance",))
env = {"Any": Any, "finite": finite}
observed_output_off, supply_off_for_pairing = functions(
    "equipment_power_switch.py",
    ("observed_output_off", "supply_off_for_pairing"), env
)
assert supply_off_for_pairing(hass, spec, "switch.plug")
states.pop("climate.appliance")
assert supply_off_for_pairing(hass, spec, "switch.plug")
states["climate.appliance"] = st("off")
assert supply_off_for_pairing(hass, spec, "switch.plug")
states["climate.appliance"] = st("heat")
assert not supply_off_for_pairing(hass, spec, "switch.plug")
states["climate.appliance"] = st("unknown")
assert supply_off_for_pairing(hass, spec, "switch.plug")
states["switch.plug"] = st("on", "switch")
assert not supply_off_for_pairing(hass, spec, "switch.plug")
states["switch.plug"] = st("unavailable", "switch")
assert not supply_off_for_pairing(hass, spec, "switch.plug")
states["switch.plug"] = st("off", "switch")
states["climate.appliance"] = st("unavailable")
assert not observed_output_off(states["climate.appliance"]), (
    "Unavailable native output must NEVER become verified idle"
)

class HomeAssistantError(Exception):
    pass


module = ModuleType("beta60_probe")
module.__path__ = []
switch_module = ModuleType("beta60_probe.equipment_power_switch")
switch_module.supply_off_for_pairing = supply_off_for_pairing
switch_module.permitted_supply = lambda manager, spec, entity, expected=None: (
    {"entity": entity, "registry_id": "immutable-plug-id",
     "device_id": "external-plug", "area": spec.area_id}
    if entity == "switch.plug" and getattr(manager, "permit", True)
    else None
)
sys.modules[module.__name__] = module
sys.modules[switch_module.__name__] = switch_module


class Model:
    SETTINGS = "equipment_controllers"
    NUMBER_FIELDS = {"power_switch_cooldown_seconds": (60, 86400)}
    @staticmethod
    def capabilities(manager, spec):
        return None
    @staticmethod
    def settings(manager, spec):
        stored = manager.settings.get(Model.SETTINGS, {}).get(spec.identifier, {})
        return {
            "power_switch_entity": None,
            "power_switch_cooldown_seconds": 600,
            "control_mode": "pid",
            **stored,
        }


env2 = {
    "__name__": "beta60_probe.runtime",
    "__package__": "beta60_probe",
    "HomeAssistantError": HomeAssistantError,
    "model": Model,
    "finite": finite,
    "asyncio": asyncio,
    "deepcopy": __import__("copy").deepcopy,
}
(async_update,) = functions("equipment_runtime.py", ("async_update",), env2)


class Controller:
    def __init__(self):
        self._ready = True
        self.record = {"power": {}, "pending": None, "upstream": {}}
        self.settings = {}
        self.entry = NS(options={}, data={}, entry_id="test-entry")
        self.manager = NS(entry=self.entry, settings=self.settings,
                          _active=False, permit=True)
        def save_entry(entry, *, options):
            entry.options = options
            self.manager.settings = {**entry.data, **entry.options}
        self.hass = NS(states=NS(get=states.get),
                       config_entries=NS(async_update_entry=save_entry))
        self.manager.hass = self.hass
        self.lock = asyncio.Lock()
        self.statuses = []
    def _lock(self, _):
        return self.lock
    def _current_spec(self, _):
        return True
    def _record(self, _):
        return self.record
    def _status(self, *args, **kwargs):
        self.statuses.append((args, kwargs))


async def case(state_supply="off", state_native="unavailable", *,
               permit=True, busy=False, race=False):
    states["switch.plug"] = st(state_supply, "switch")
    states["climate.appliance"] = st(state_native)
    controller = Controller()
    controller.manager.permit = permit
    if busy:
        controller.record["upstream"]["owned"] = True
    if race:
        class FlipToOn:
            async def __aenter__(self):
                states["switch.plug"] = st("on", "switch")
            async def __aexit__(self, *_):
                return False
        controller.manager._device_settings_write_lock = FlipToOn()
    try:
        await async_update(controller, spec, {"power_switch_entity": "switch.plug"})
    except HomeAssistantError:
        assert controller.manager.settings.get(Model.SETTINGS, {}) == {}, (
            "Failure must not save an unsafe assignment"
        )
        return False, controller
    assert (controller.manager.settings[Model.SETTINGS][spec.identifier]
            ["power_switch_entity"] == "switch.plug")
    assert "capabilities" not in controller.record, (
        "Unpowered appliance must not gain invented capabilities"
    )
    return True, controller


async def run():
    ok, controller = await case()
    assert ok, "Confirmed-OFF supply plus unavailable native appliance MUST pair"
    assert (await case(state_native="off"))[0]
    assert not (await case(state_native="heat"))[0]
    assert not (await case(state_supply="on"))[0]
    assert not (await case(state_supply="unavailable"))[0]
    assert not (await case(permit=False))[0]
    assert not (await case(busy=True))[0]
    assert not (await case(race=True))[0]

    # A successfully paired but never observed appliance MUST NOT trigger
    # automatic ON from an unavailable source with no verified capabilities.
    states["switch.plug"] = st("off", "switch")
    env3 = {
        "__name__": "beta60_probe.switch",
        "__package__": "beta60_probe",
        "Any": Any,
        "model": Model,
        "_SWITCH_STATES": ("off", "on"),
        "permitted_supply": switch_module.permitted_supply,
        "verified_capabilities": lambda runtime, spec: None,
    }
    (before_tick,) = functions("equipment_power_switch.py", ("before_tick",), env3)
    record = controller.record
    record["area"] = spec.area_id
    record["sources"] = list(spec.source_entities)
    commands = []
    async def save():
        commands.append("save")
    def status(_, status, **kwargs):
        commands.append(("status", status, kwargs))
    controller._save = save
    controller._status = status
    controller.clock = lambda: 1700000000
    result = await before_tick(controller, spec)
    assert result is True
    assert record["upstream"]["owned"] is False
    assert any(isinstance(a, tuple) and
               a[2].get("reason") == "upstream_switch_capabilities_not_verified"
               for a in commands), commands
    assert all(action == "save" or action[0] == "status" for action in commands)
    assert "capabilities" not in record

    # Additional branch gates verified without running Home Assistant.
    runtime = source("equipment_runtime.py")
    assert "selected_supply and model.sources_available(self.manager, spec)" in runtime
    assert "permitted_supply(self.manager, spec, selected_supply) is None" in runtime
    assert "or not supply_off_for_pairing(self.hass, spec, selected_supply)" in runtime
    assert "not supply_off_for_pairing(self.hass, spec, selected)" in runtime
    print("PASS: offline pairing; unavailable native; ON/active/claimed/busy/race refusals; no unverified automatic power-on")


asyncio.run(run())
