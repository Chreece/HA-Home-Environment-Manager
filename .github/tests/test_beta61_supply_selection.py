"""Beta61: configuration is not power ownership; execute actual controller methods."""
from __future__ import annotations

import ast
import asyncio
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def extract(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    chosen = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            chosen.append(node)
        if isinstance(node, ast.ClassDef):
            chosen.extend(
                method for method in node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                and method.name in names
            )
    assert {node.name for node in chosen} == set(names), (filename, names)
    exec(compile(ast.Module(body=chosen, type_ignores=[]), filename, "exec"), namespace)
    return tuple(namespace[n] for n in names)


def finite(value, low, high):
    try:
        number = float(value)
        return number if low <= number <= high else None
    except (TypeError, ValueError):
        return None


def state(value, domain="climate"):
    return NS(state=value, domain=domain, name="Physical", attributes={})


states = {}
spec = NS(identifier="managed-appliance", area_id="guest",
          source_device_id="appliance-device", source_entities=("climate.appliance",))


class HomeAssistantError(Exception):
    pass


@dataclass
class NativeCap:
    primary: str = "climate.appliance"
    domain: str = "climate"
    modes: tuple = ("off", "heat", "cool")
    fan_modes: tuple = ()
    swing_modes: tuple = ()
    swing_horizontal_modes: tuple = ()
    fan_entity: str | None = None
    fan_percentage: bool = False
    temperature: bool = True
    humidity: bool = False
    min_temp: float = 5
    max_temp: float = 35
    min_humidity: float = 20
    max_humidity: float = 80


class Model:
    SETTINGS = "equipment_controllers"
    CAP = None
    DEFAULTS = {
        "control_mode": "pid", "power_switch_entity": None,
        "power_switch_cooldown_seconds": 600, "cycle_seconds": 3600,
        "min_on_seconds": 600, "min_off_seconds": 600,
        "pid_calibration_method": "manual",
        "pid_fan_capacity_mode": "legacy", "pid_fan_capacity_for_mode": "choose",
        "pid_fan_capacity_models": {}, "preset": "none",
        "requested_mode": None, "profile_targets": {}, "profile_fans": {},
        "quiet_sleep": False, "quiet_occupied": False,
    }
    NUMBER_FIELDS = {"power_switch_cooldown_seconds": (60, 86400)}
    PID_MODEL_FIELDS = {}
    PID_FAN_CAPACITY_FIELDS = {}
    PID_CALIBRATION_METHODS = ("manual",)
    PID_FAN_CAPACITY_METHODS = ("legacy",)
    PID_FAN_DIRECTIONS = ("heat", "cool", "dry")
    PRESETS = ("none",)
    QUIET_FLAGS = ("quiet_sleep", "quiet_occupied")
    DEVICE_SELECTS = {}

    @staticmethod
    def capabilities(manager, spec):
        return Model.CAP

    @staticmethod
    def sources_available(manager, spec):
        return all(
            (native := states.get(entity)) is not None
            and native.state not in ("unavailable", "unknown")
            for entity in spec.source_entities
        )

    @staticmethod
    def control_modes(manager, spec):
        return ("existing", "pid", "automatic", "manual", "off")

    @staticmethod
    def permission(manager, spec, cap):
        return True, True

    @staticmethod
    def timing(manager, spec, cap, config=None):
        return 600, 600, 7200

    @staticmethod
    def settings(manager, spec):
        values = manager.settings.get(Model.SETTINGS, {}).get(spec.identifier, {})
        return {**Model.DEFAULTS, **values}


pkg = ModuleType("beta61_probe")
pkg.__path__ = []
switch_mod = ModuleType("beta61_probe.equipment_power_switch")
device_mod = ModuleType("beta61_probe.device_activation")
switch_mod.permitted_supply = lambda manager, spec, entity, expected=None: (
    {
        "entity": entity,
        "registry_id": "physical-immutable-id",
        "device_id": "external-supply",
        "area": spec.area_id,
    }
    if entity == "switch.plug" and getattr(manager, "permit", True)
    and (expected is None or expected.get("registry_id") == "physical-immutable-id")
    else None
)
device_mod.authority_context = lambda manager, spec: ("unchanged-authorization",)
sys.modules.update({
    "beta61_probe": pkg,
    "beta61_probe.equipment_power_switch": switch_mod,
    "beta61_probe.device_activation": device_mod,
})

runtime_env = {
    "__name__": "beta61_probe.equipment_runtime",
    "__package__": "beta61_probe",
    "HomeAssistantError": HomeAssistantError,
    "model": Model,
    "asyncio": asyncio,
    "deepcopy": __import__("copy").deepcopy,
    "finite": finite,
    "asdict": asdict,
    "fan_capacity_model_is_valid": lambda *args, **kw: False,
    "output_off": lambda native: native is not None and native.state == "off",
    "snapshot": lambda native: {"state": native.state} if native is not None else None,
}
(async_update,) = extract("equipment_runtime.py", ("async_update",), runtime_env)


class Controller:
    def __init__(self, *, previously_selected=False):
        self._ready = True
        self._active = True
        self._started = 1699998000
        self.record = {
            "sources": list(spec.source_entities), "area": spec.area_id,
            "power": {}, "pending": None, "upstream": {},
        }
        previous = (
            {Model.SETTINGS: {spec.identifier: {
                "power_switch_entity": "switch.plug"
            }}}
            if previously_selected else {}
        )
        self.entry = NS(options=previous, data={}, entry_id="config-entry")
        self.manager = NS(entry=self.entry, settings=previous,
                          _active=False, permit=True)
        self.service_calls = []
        self.hass = NS(states=NS(get=states.get), config_entries=NS())
        self.manager.hass = self.hass

        def save_entry(entry, *, options):
            self.entry.options = options
            self.manager.settings = {**entry.data, **options}
        self.hass.config_entries.async_update_entry = save_entry
        self.lock = asyncio.Lock()
        self._memory = {}
        self._fan_allocations = {}
        self._pid_offline_previews = {}
        self.statuses = []
        self.saved_records = 0
        self.clock = lambda: 1700000000

    def _lock(self, key):
        return self.lock

    def _current_spec(self, spec):
        return True

    def _record(self, spec):
        return self.record

    def _status(self, *args, **kwargs):
        self.statuses.append((args, kwargs))

    async def _save(self):
        self.saved_records += 1

    async def _reconcile(self, spec):
        return False

    def _legacy_busy(self, spec):
        return None


async def scenario(supply="off", native="unavailable", *, capabilities=False,
                   permit=True, upstream_owned=False, native_owned=False,
                   pending=False, race=None, remove=False):
    Model.CAP = NativeCap() if capabilities else None
    if supply is None:
        states.pop("switch.plug", None)
    else:
        states["switch.plug"] = state(supply, "switch")
    if native is None:
        states.pop("climate.appliance", None)
    else:
        states["climate.appliance"] = state(native)
    controller = Controller(previously_selected=remove)
    controller.manager.permit = permit
    if upstream_owned:
        controller.record["upstream"]["owned"] = True
    if native_owned:
        controller.record["power"]["climate.appliance"] = {
            "since": 1699998000, "min_on": 600, "max_on": 7200,
        }
    if pending:
        controller.record["pending"] = {"entity": "climate.appliance"}
    if race:
        class RacingConfiguration:
            async def __aenter__(self):
                if race == "identity":
                    controller.manager.permit = False
                elif race == "state":
                    states["switch.plug"] = state("on", "switch")
                elif race == "disconnected":
                    states.pop("switch.plug", None)
                else:
                    raise AssertionError(race)
            async def __aexit__(self, *args):
                return False
        controller.manager._device_settings_write_lock = RacingConfiguration()

    selected = None if remove else "switch.plug"
    old = "switch.plug" if remove else None
    try:
        await async_update(controller, spec, {"power_switch_entity": selected})
    except HomeAssistantError:
        assert Model.settings(controller.manager, spec)["power_switch_entity"] == old, (
            "Unsafe edit changed settings"
        )
        return False, controller
    assert Model.settings(controller.manager, spec)["power_switch_entity"] == selected
    assert controller.record["upstream"].get("owned") is not True, (
        "No selection may establish external supply ownership"
    )
    if not capabilities or native in ("unknown", "unavailable", None) or remove:
        assert "capabilities" not in controller.record, (
            "A disconnected native appliance must not gain unverified capabilities"
        )
    else:
        assert controller.record["capabilities"]["primary"] == "climate.appliance"
    assert controller.service_calls == [], (
        "Changing a selector must not command the switch"
    )
    return True, controller


async def main():
    # All supply states and all native output states are valid CONFIGURATION.
    for with_cap in (False, True):
        for supply in ("off", "on", "unknown", "unavailable", None):
            for native in ("off", "heat", "unknown", "unavailable", None):
                success, _ = await scenario(
                    supply, native, capabilities=with_cap
                )
                assert success, (supply, native, with_cap)

        assert (await scenario("off", "unavailable", capabilities=with_cap,
                               race="state"))[0], "State changes do not invalidate configuration"
        assert (await scenario("on", "heat", capabilities=with_cap,
                               race="disconnected"))[0]
        assert not (await scenario("off", "unavailable", capabilities=with_cap,
                                   race="identity"))[0], "Identity races must reject"
        assert not (await scenario("on", "heat", capabilities=with_cap,
                                   permit=False))[0], "Cross-room/claimed/own supply rejects"
        assert not (await scenario("on", "heat", capabilities=with_cap,
                                   upstream_owned=True))[0], "Old owned relay cannot be reassigned"
        assert not (await scenario("on", "heat", capabilities=with_cap,
                                   pending=True))[0], "Pending native command requires reconciliation"
        assert (await scenario("on", "heat", capabilities=with_cap,
                               native_owned=True))[0], "Native running output must not block pure pairing"
        for supply in ("off", "on", "unavailable"):
            assert (await scenario(supply, "heat", capabilities=with_cap,
                                   remove=True))[0], "Unowned supply can be unselected"

    # The native and upstream ownership states must remain separate.
    success, controller = await scenario("on", "heat", capabilities=True,
                                         native_owned=True)
    assert success
    supply_env = {
        "model": Model, "Any": Any, "finite": finite,
        "permitted_supply": switch_mod.permitted_supply,
        "_SWITCH_STATES": ("off", "on"),
        "UPSTREAM_MIN_OFF_SECONDS": 600,
        "UPSTREAM_ACK_SECONDS": 120,
        "verified_capabilities": lambda runtime, spec: NativeCap(),
        "approved_demand": lambda runtime, spec, cfg, cap: True,
        "cold_start_direction_demand": lambda runtime, spec, cfg: None,
        "cold_start_dispatch_safe": lambda runtime, spec, record, cfg, entity: False,
        "prepare_offline_pid": lambda runtime, spec, cap, cfg, demand: {},
        "observed_output_off": lambda native: native is not None
                                        and native.state == "off",
        "_observed_off_since": lambda state, now: now - 7200,
        "_send": lambda *args: (_ for _ in ()).throw(
            AssertionError("A newly paired supply must not be operated")
        ),
    }
    extract(
        "equipment_power_switch.py",
        ("device_supply_dwell", "supply_off_since",
         "supply_minimum_on", "supply_minimum_off",
         "observe_supply_state"), supply_env,
    )
    before_tick, dispatch_safe = extract(
        "equipment_power_switch.py",
        ("before_tick", "_dispatch_safe"), supply_env,
    )
    record = controller.record
    record["upstream"] = {}
    # Initially ON and unowned: do not turn the outlet OFF; native control runs.
    states["switch.plug"] = state("on", "switch")
    assert await before_tick(controller, spec) is False
    assert record["upstream"]["owned"] is False
    # If physically switched OFF while native ownership remains unresolved,
    # do not turn it back ON even after a long minimum-OFF interval.
    states["switch.plug"] = state("off", "switch")
    assert await before_tick(controller, spec) is True
    assert record["upstream"]["owned"] is False
    assert controller.statuses[-1][0][1] == "owned_shutdown_identity_or_dwell_hold"
    assert not dispatch_safe(
        controller, spec, record, Model.settings(controller.manager, spec),
        "switch.plug", "on"
    )
    # An unavailable supply causes an isolated wait, never a service call.
    states["switch.plug"] = state("unavailable", "switch")
    assert await before_tick(controller, spec) is True
    assert record["upstream"]["owned"] is False

    # No controller can cut power to an already-ON but still-unowned supply.
    states["switch.plug"] = state("on", "switch")
    record["power"].clear()
    assert not dispatch_safe(
        controller, spec, record, Model.settings(controller.manager, spec),
        "switch.plug", "off"
    )
    # A saved OFF supply with NO verified downstream capabilities must remain
    # idle instead of using unavailable attributes to invent device authority.
    success, offline = await scenario(
        "off", "unavailable", capabilities=False
    )
    assert success
    supply_env["verified_capabilities"] = lambda runtime, spec: None
    before_tick_no_cap, = extract(
        "equipment_power_switch.py", ("before_tick",), supply_env
    )
    states["switch.plug"] = state("off", "switch")
    assert await before_tick_no_cap(offline, spec) is True
    assert offline.record["upstream"]["owned"] is False
    assert "capabilities" not in offline.record
    print("PASS: 50 cross-product pairings, live-state races, identity and ownership guards, zero switch commands")


asyncio.run(main())
