"""Beta63 cold-start regression: exercise the actual source functions.

This is an isolated HA simulator, not a substitute for powered hardware tests.
It intentionally never mocks a successful native climate service while offline.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NOW = 1_798_000_000.0


class FakeState:
    def __init__(self, value, age=900):
        self.state = value
        self.last_changed = datetime.fromtimestamp(NOW - age, timezone.utc)
        self.attributes = {}


class Cap:
    def __init__(self, primary, domain, modes, *, temperature=False, humidity=False):
        self.primary, self.domain, self.modes = primary, domain, modes
        self.temperature, self.humidity = temperature, humidity
        self.humidifying = False


class Model:
    Capabilities = Cap
    @staticmethod
    def settings(manager, spec):
        return manager.settings["controllers"][spec.identifier]
    @staticmethod
    def room_config(manager, spec):
        return {
            "enabled": True,
            "dry_climate_entity": spec.source_entities[0] if manager.dry_role else None,
        }
    @staticmethod
    def targets(manager, spec, cap, cfg, plan):
        return {"humidity": manager.target_rh, "heat": 21, "cool": 27}
    @staticmethod
    def plan_for(manager, spec):
        return manager.plan
    @staticmethod
    def timing(manager, spec, cap, config=None):
        cfg = config or Model.settings(manager, spec)
        return (
            max(600, cfg.get("min_on_seconds", 600)),
            max(600, cfg.get("min_off_seconds", 600)),
            7200,
        )
    @staticmethod
    def sources_available(manager, spec):
        return manager.native_online
    @staticmethod
    def capabilities(manager, spec):
        if manager.native_online:
            return Cap(spec.source_entities[0], "climate", ("off", "dry"), humidity=True)
        return (Cap(spec.source_entities[0], "climate", manager.offline_modes, humidity=True)
                if manager.offline_modes else None)


pkg = ModuleType("beta63_runtime")
pkg.__path__ = []
activation = ModuleType("beta63_runtime.device_activation")
occupancy = ModuleType("beta63_runtime.occupancy_policy")
arbitration = ModuleType("beta63_runtime.climate_arbitration")
activation.authorized = lambda manager, spec: manager.authorized
activation.effective_device = lambda manager, spec, entity: {"presence_requirement": "always"}
occupancy.live_device_permission = lambda hass, area, room, plan, live: (
    ("eligible", "good") if plan.get("permission") else ("held", "blocked")
)
arbitration._contact_interlock = lambda hass, area, plan: bool(plan.get("window_safe"))
sys.modules.update({
    pkg.__name__: pkg,
    activation.__name__: activation,
    occupancy.__name__: occupancy,
    arbitration.__name__: arbitration,
})

def finite(value, lower, upper):
    try:
        v = float(value)
        return v if lower <= v <= upper else None
    except (TypeError, ValueError, OverflowError):
        return None


def load_functions(path, names, globals_):
    body = ast.parse((ROOT / path).read_text(encoding="utf-8")).body
    selected = [
        node for node in body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    assert {node.name for node in selected} == set(names), (path, names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), path, "exec"), globals_)
    return tuple(globals_[name] for name in names)


spec = NS(
    identifier="sleeproom_comfee_controller", area_id="bedroom",
    source_device_id="comfee-device-id", source_entities=("climate.comfee",)
)
IDENTITY = {
    "entity": "switch.power_strip", "registry_id": "immutable-switch-id",
    "device_id": "real-switch-device-id", "area": "bedroom"
}

def permit(manager, spec, entity, expected=None):
    if not manager.switch_valid or entity != IDENTITY["entity"]:
        return None
    if expected is not None and expected != IDENTITY:
        return None
    return dict(IDENTITY)


globals_ = {
    "__name__": "beta63_runtime.equipment_power_switch",
    "__package__": "beta63_runtime",
    "Any": Any, "Mapping": Mapping,
    "model": Model, "finite": finite,
    "UPSTREAM_MIN_OFF_SECONDS": 600,
    "UPSTREAM_ACK_SECONDS": 120,
    "_SWITCH_STATES": ("off", "on"),
    "permitted_supply": permit,
}
(output_required, off_since, verified_capabilities,
 approved_demand, cold_start_direction_demand, cold_start_dispatch_safe,
 dispatch_safe, send, before_tick, device_supply_dwell, supply_off_since,
 supply_minimum_on, supply_minimum_off, observe_supply_state) = load_functions(
    "equipment_power_switch.py",
    ("output_required", "_observed_off_since", "verified_capabilities",
     "approved_demand", "cold_start_direction_demand",
     "cold_start_dispatch_safe", "_dispatch_safe", "_send", "before_tick",
     "device_supply_dwell", "supply_off_since", "supply_minimum_on",
     "supply_minimum_off", "observe_supply_state"),
    globals_,
)
# Resolve normal source-function references in the test module's namespace.
globals_["observed_output_off"] = lambda native: native is not None and native.state == "off"
globals_["prepare_offline_pid"] = lambda *args: {}
globals_["relay_identity"] = lambda hass, spec, entity: dict(IDENTITY) if entity == IDENTITY["entity"] else None

# Module imports for managed climate availability and interface.
switch_mod = ModuleType("beta63_runtime.equipment_power_switch")
switch_mod.relay_identity = globals_["relay_identity"]
switch_mod.verified_capabilities = verified_capabilities
sys.modules[switch_mod.__name__] = switch_mod


class Simulator:
    def __init__(self, *, supply="off", age=900, rh=68, target_rh=60,
                 direction="dry", method="pid", authorized=True,
                 permission=True, window_safe=True,
                 offline_modes=None, dry_role=False):
        self._active = True
        self._ready = True
        self._started = NOW - 1800
        self._commands = asyncio.Semaphore(1)
        self._pid_offline_previews = {}
        self._save_log = []
        self.service_calls = []
        self.on_save = None
        self.native_online = False
        self.native_states = {}
        self.states = {"switch.power_strip": FakeState(supply, age)}
        self.manager = NS(
            settings={"controllers": {spec.identifier: {
                "power_switch_entity": "switch.power_strip",
                "control_mode": method,
                "requested_mode": direction,
                "power_switch_cooldown_seconds": 600,
                "min_on_seconds": 600, "min_off_seconds": 600,
            }}},
            native_online=False,
            authorized=authorized,
            switch_valid=True,
            target_rh=target_rh,
            offline_modes=offline_modes,
            dry_role=dry_role,
            plan={"permission": permission, "window_safe": window_safe},
        )
        self.records = {}
        self.hass = NS(states=NS(get=self.states.get), services=NS())
        self.manager.hass = self.hass
        self.manager.equipment = self
        self.measurement_rh = rh
        self.hass.services.has_service = lambda d, s: d == "switch" and s in ("turn_on", "turn_off")

        async def call(domain, action, data, *, target, blocking):
            assert domain == "switch"
            entity = target["entity_id"]
            self.service_calls.append((entity, action))
            self.states[entity] = FakeState("on" if action == "turn_on" else "off", 0)
        self.hass.services.async_call = call

    def clock(self):
        return NOW
    def _record(self, sp):
        return self.records.setdefault(sp.identifier, {
            "area": sp.area_id,
            "sources": list(sp.source_entities),
            "source_device_id": sp.source_device_id,
            "power": {}, "pending": None,
            "upstream": {}, "off_at": {}, "baseline": {},
        })
    def _current_spec(self, sp):
        return True
    def _status(self, sp, status, **kwargs):
        self.status = (status, kwargs)
    async def _save(self):
        self._save_log.append(copy.deepcopy(self.records))
        # Trigger races at the real durable intent, not at a fixed Store
        # write count: Beta74 may additionally persist first OFF observation
        # before an external ON command is commissioned.
        record = self.records.get(spec.identifier, {})
        pending = record.get("upstream", {}).get("pending", {})
        if (self.on_save is not None and isinstance(pending, dict)
                and pending.get("phase") == "intent"):
            on_save = self.on_save
            self.on_save = None
            on_save()
    def measurements(self, sp, cap):
        return {"humidity": self.measurement_rh, "temperature": 20}


def patch_manager(sim):
    sim.manager.native_online = sim.native_online


async def drive(sim):
    patch_manager(sim)
    return await before_tick(sim, spec)


async def test_cold_start():
    sim = Simulator()
    assert await drive(sim) is True
    assert sim.service_calls == [("switch.power_strip", "turn_on")], sim.service_calls
    record = sim._record(spec)
    assert record["upstream"]["pending"]["cold_start"] is True
    assert record["upstream"]["owned"] is False
    assert "capabilities" not in record
    assert sim._save_log, "Power intent must be durably recorded before I/O"
    assert await drive(sim) is True
    assert record["upstream"]["pending"] is None
    assert record["upstream"]["owned"] is True
    assert sim.status[1]["reason"] == "upstream_on_native_device_not_reporting"
    assert len(sim.service_calls) == 1
    sim.native_online = True
    sim.states["climate.comfee"] = FakeState("off")
    # Real native mode and capabilities are now observable; ordinary control
    # can proceed, while the supply stays ON and owned.
    assert await drive(sim) is False
    assert len(sim.service_calls) == 1


async def test_single_mode_and_room_role():
    # DRY-only Comfee sources commonly have no requested_mode configured.
    # HA-advertised single DRY mode (not a verified live state) or explicit
    # room dehumidifier role can be used only to restore its separate supply.
    for hints in (
        {"offline_modes": ("off", "dry")},
        {"dry_role": True},
    ):
        sim = Simulator(direction=None, **hints)
        assert await drive(sim) is True, hints
        assert sim.service_calls == [("switch.power_strip", "turn_on")], hints
        assert "capabilities" not in sim._record(spec), (
            "Never promote stale native mode hints to verified capabilities"
        )


async def test_negative():
    # Unknown/absent native source is acceptable only when independently
    # measured demand and explicit mode authorization are both TRUE.
    for kw in (
        {"rh": None}, {"rh": 61}, {"target_rh": None},
        {"direction": None}, {"direction": "auto"},
        {"direction": None, "offline_modes": ("off", "heat", "cool")},
        {"method": "existing"}, {"method": "off"},
        {"method": "manual"}, {"authorized": False},
        {"permission": False}, {"window_safe": False},
        {"age": 120}, {"supply": "on"}, {"supply": "unavailable"},
    ):
        sim = Simulator(**kw)
        assert await drive(sim) is True, kw
        assert sim.service_calls == [], (kw, sim.service_calls)

    for change in ("identity", "demand", "supply", "settings"):
        sim = Simulator()
        def mutate():
            if change == "identity":
                sim.manager.switch_valid = False
            elif change == "demand":
                sim.measurement_rh = 55
            elif change == "supply":
                sim.states["switch.power_strip"] = FakeState("on")
            elif change == "settings":
                sim.manager.settings = {"controllers": {spec.identifier: {
                    **sim.manager.settings["controllers"][spec.identifier],
                    "requested_mode": "heat",
                }}}
        sim.on_save = mutate
        assert await drive(sim) is True
        assert sim.service_calls == [], change

    # Existing native output ownership blocks a second, supply-level wake.
    for flag in ("power", "pending"):
        sim = Simulator()
        record = sim._record(spec)
        if flag == "power":
            record["power"]["climate.comfee"] = {"since": NOW-100}
        else:
            record["pending"] = {"entity": "climate.comfee"}
        assert await drive(sim) is True
        assert sim.service_calls == [], flag

    sim = Simulator()
    sim.states["climate.comfee"] = FakeState("dry")
    assert await drive(sim) is True
    assert sim.service_calls == [], "Physical native output already active"


async def test_ui():
    tree = ast.parse((ROOT / "climate.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManagedClimate")
    wanted = ("available", "hvac_modes", "hvac_mode")
    methods = {}
    for name in wanted:
        node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
        node.decorator_list = []
        ns = {"__name__": "beta63_runtime.climate",
              "__package__": "beta63_runtime", "HVACMode": NS(OFF="off")}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "climate.py", "exec"), ns)
        methods[name] = ns[name]

    sim = Simulator()
    sim._current_spec = lambda sp: True
    view = NS(
        _caps=None, _state=None,
        controller_settings=sim.manager.settings["controllers"][spec.identifier],
        _manager=NS(equipment=sim, hass=sim.hass), _spec=spec,
        available=True,
    )
    assert methods["available"](view) is True
    assert methods["hvac_modes"](view) == ["off"]
    assert methods["hvac_mode"](view) == "off"
    sim.states["switch.power_strip"] = FakeState("unavailable")
    assert methods["available"](view) is False


async def main():
    await test_cold_start()
    await test_single_mode_and_room_role()
    await test_negative()
    await test_ui()
    print("PASS: previously authorized DRY cold-start, intent before service, ACK ownership, native recovery, 14 holds, 4 dispatch races, UI availability")


asyncio.run(main())
