"""Beta64 targeted behavior regressions against actual HA integration functions.

Never sends a command to real Home Assistant or a physical device.
"""
from __future__ import annotations

import ast
import asyncio
import copy
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
BASE = 1793100000.0


def extract(file, names, scope):
    tree = ast.parse((ROOT / file).read_text(encoding="utf-8"))
    found = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            found.append(node)
        if isinstance(node, ast.ClassDef):
            found.extend(child for child in node.body
                         if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and child.name in names)
    assert {node.name for node in found} == set(names), (file, names)
    exec(compile(ast.Module(body=found, type_ignores=[]), file, "exec"), scope)
    return tuple(scope[name] for name in names)


@dataclass(frozen=True)
class Capabilities:
    primary: str = "climate.comfee"
    domain: str = "climate"
    modes: tuple[str, ...] = ("off", "dry")
    humidity: bool = True
    humidifying: bool = False


def state(mode, *, when=None):
    return NS(state=mode, domain="climate",
              attributes={"hvac_action": "idle" if mode == "off" else "drying"},
              last_changed=datetime.fromtimestamp(
                  BASE - 1800 if when is None else when, timezone.utc))


def finite(value, minimum, maximum):
    try:
        value = float(value)
        return value if minimum <= value <= maximum else None
    except (TypeError, ValueError, OverflowError):
        return None


def output_off(item):
    return item is not None and item.state == "off"


pkg = ModuleType("beta64_probe")
pkg.__path__ = []
activation = ModuleType("beta64_probe.device_activation")
occupancy = ModuleType("beta64_probe.occupancy_policy")
arbitration = ModuleType("beta64_probe.climate_arbitration")
power_mod = ModuleType("beta64_probe.equipment_power_switch")
sys.modules.update({
    pkg.__name__: pkg,
    activation.__name__: activation,
    occupancy.__name__: occupancy,
    arbitration.__name__: arbitration,
    power_mod.__name__: power_mod,
})

(device_permission,) = extract("occupancy_policy.py", ("device_permission",),
                              {"Mapping": Mapping})
occupancy.live_device_permission = lambda hass, area, room, plan, device: device_permission(
    device, "occupied", "home", plan["sleeping"]
)
activation.authorized = lambda manager, spec: manager.authorized
activation.effective_device = lambda manager, spec, entity: {
    "auto_control": manager.authorized,
    "sleep_behavior": manager.sleep_behavior,
    "presence_requirement": "always",
}
arbitration._contact_interlock = lambda hass, area, plan: plan["window_safe"]

class Model:
    @staticmethod
    def settings(manager, spec):
        return manager.settings["equipment_controllers"][spec.identifier]
    @staticmethod
    def room_config(manager, spec):
        return manager.room
    @staticmethod
    def plan_for(manager, spec):
        return manager.plan
    @staticmethod
    def targets(manager, spec, cap, cfg, plan):
        return {"humidity": manager.target, "heat": 18., "cool": 26.}
    @staticmethod
    def capabilities(manager, spec):
        return manager.cap
    @staticmethod
    def sources_available(manager, spec):
        s = manager.hass.states.get(spec.source_entities[0])
        return s is not None and s.state not in ("unavailable", "unknown")
    @staticmethod
    def permission(manager, spec, cap):
        return True, manager.authorized
    @staticmethod
    def timing(manager, spec, cap, config=None):
        return 600, 600, 7200


spec = NS(identifier="sleep-comfee", area_id="schlafzimmer",
          source_device_id="comfee", source_entities=("climate.comfee",))
IDENTITY = {"entity": "switch.strip", "registry_id": "real-switch-id",
            "device_id": "physical-plug", "area": spec.area_id}


class Simulator:
    def __init__(self, *, sleeping=True, native="dry", supply="on", authorized=True,
                 owned=True, humidity=68., target=60., sleep_behavior="pause"):
        self.now = BASE
        self._ready = True
        self._active = True
        self._started = BASE - 1800
        self._memory = {}
        self._fan_allocations = {}
        self._invalidated = set()
        self._pid_offline_previews = {}
        self._commands = asyncio.Semaphore(1)
        self._save_log = []
        self.issued = []
        self.statuses = {}
        self.manager = NS(
            room={},
            cap=Capabilities(),
            settings={"equipment_controllers": {spec.identifier: {
                "control_mode": "pid", "requested_mode": "dry",
                "power_switch_entity": "switch.strip",
                "power_switch_cooldown_seconds": 600,
            }}},
            plan={"sleeping": sleeping, "window_safe": True},
            sleep_behavior=sleep_behavior,
            authorized=authorized, target=target,
        )
        self.hass = NS(states=NS(get=lambda entity: self.states.get(entity)), services=NS())
        self.manager.hass = self.hass
        self.manager.equipment = self
        self.states = {"switch.strip": state(supply), "climate.comfee": state(native)}
        self.hass.services.has_service = lambda domain, action: (
            (domain, action) in (
                ("climate", "set_hvac_mode"), ("switch", "turn_off"),
                ("switch", "turn_on")))
        self.on_save = None
        async def invoke(domain, action, data, *, target, blocking):
            self.issued.append((domain, action, target["entity_id"], dict(data)))
            if domain == "climate" and action == "set_hvac_mode":
                self.states["climate.comfee"] = state(data["hvac_mode"], when=self.now)
            elif domain == "switch":
                self.states["switch.strip"] = state("off" if action == "turn_off" else "on",
                                                     when=self.now)
        self.hass.services.async_call = invoke
        self.records = {spec.identifier: {
            "area": spec.area_id, "sources": list(spec.source_entities),
            "source_device_id": spec.source_device_id,
            "power": {}, "pending": None, "baseline": {},
            "off_at": {}, "upstream": {
                "entity": "switch.strip", "identity": dict(IDENTITY),
                "owned": owned, "idle_since": None,
            },
        }}
        self.record = self.records[spec.identifier]
        self.hass.config = NS(time_zone="Europe/Berlin")

    def clock(self):
        return self.now
    def _record(self, spec):
        return self.record
    def _current_spec(self, spec):
        return True
    def _identity_ok(self, spec):
        return True
    def _status(self, spec, status, **kwargs):
        self.statuses[spec.identifier] = {"status": status, **kwargs}
    def measurements(self, spec, cap):
        return {"humidity": self.humidity, "temperature": 20.}
    def _quiet_context(self, *args):
        return False
    async def _save(self):
        self._save_log.append(copy.deepcopy(self.record))
        if self.on_save is not None:
            cb, self.on_save = self.on_save, None
            cb()
    def _gate(self, spec, cap, cfg, plan, mode, *, automatic=True):
        if not self._active or not self._ready or self.record.get("paused"):
            return "controller_inactive"
        return None

    async def _reconcile(self, spec):
        pending = self.record.get("pending")
        if not pending:
            return True
        entity = pending["entity"]
        actual = self.states.get(entity)
        if actual is None or actual.state != pending["expected"]["state"]:
            return False
        self.record["pending"] = None
        if pending.get("power"):
            if pending.get("output_on") is False:
                self.record["power"].pop(entity, None)
                self.record["off_at"][entity] = self.now
            else:
                self.record["power"][entity] = {
                    "since": self.now, "min_on": pending["min_on"],
                    "max_on": pending["max_on"],
                }
        await self._save()
        return True


def permitted(manager, spec, entity, expected=None):
    if not manager.authorized or entity != "switch.strip":
        return None
    return dict(IDENTITY) if expected is None or expected == IDENTITY else None


power_env = {
    "__name__": "beta64_probe.equipment_power_switch",
    "__package__": "beta64_probe",
    "Any": Any, "Mapping": Mapping,
    "model": Model, "finite": finite, "permitted_supply": permitted,
    "UPSTREAM_MIN_OFF_SECONDS": 600, "UPSTREAM_ACK_SECONDS": 120,
    "_SWITCH_STATES": ("off", "on"),
    "output_required": lambda cap, targets, measured, **args: (
        True if measured["humidity"] > targets["humidity"]+2 else
        False if measured["humidity"] < targets["humidity"]-2 else None
    ),
    "observed_output_off": output_off,
    "_observed_off_since": lambda state, now: state.last_changed.timestamp(),
    "verified_capabilities": lambda runtime, spec: runtime.manager.cap,
}
(approved_demand, dispatch_safe, before_tick, send) = extract(
    "equipment_power_switch.py",
    ("approved_demand", "_dispatch_safe", "before_tick", "_send"),
    power_env,
)
power_env.update({
    "approved_demand": approved_demand,
    "_dispatch_safe": dispatch_safe,
    "_send": send,
    "prepare_offline_pid": lambda *args: {},
})
power_mod.approved_demand = approved_demand
power_mod.before_tick = before_tick

runtime_env = {
    "__name__": "beta64_probe.equipment_runtime",
    "__package__": "beta64_probe",
    "Any": Any, "model": Model, "asdict": asdict, "finite": finite,
    "asyncio": asyncio, "deepcopy": copy.deepcopy, "output_off": output_off,
    "snapshot": lambda item: (
        {"state": item.state, "attributes": dict(item.attributes)}
        if item is not None else None
    ),
    "matches": lambda s, expected: s is not None and s.state == expected.get("state"),
    "entity_area": lambda hass, entity: spec.area_id,
    "STARTUP_SECONDS": 300,
}
(stop_policy, native_send, native_power, tick) = extract(
    "equipment_runtime.py",
    ("_stop_policy_verified", "_send", "_power", "tick"),
    runtime_env,
)
# Simulated class uses the actual runtime implementation methods.
Simulator._stop_policy_verified = stop_policy
Simulator._send = native_send
Simulator._power = native_power

# Native "shutdown=True" uses the existing verified prior ownership/dwell
# checker. This stub enforces the same major physical safety conditions.
Simulator._shutdown_allowed = lambda self, spec, entity, expected: (
    entity in self.record["power"]
    and expected.get("state") == "off"
    and self.now - self.record["power"][entity]["since"] >= 600
    and self.states[entity].state not in ("unknown", "unavailable")
)


async def test_permissions_and_sleep_off():
    dev = {"auto_control": True, "sleep_behavior": "pause", "presence_requirement": "always"}
    assert device_permission(dev, "occupied", "home", True) == (
        "held", "sleep_room_control_paused")
    assert device_permission(dev, "occupied", "home", False)[0] == "eligible"
    assert device_permission(dev, "occupied", "home", None) == (
        "held", "sleep_room_evidence_unknown")
    sim = Simulator()
    cfg = Model.settings(sim.manager, spec)
    assert approved_demand(sim, spec, cfg, sim.manager.cap) is False
    assert sim._stop_policy_verified(spec, sim.manager.cap, "sleep")
    await tick(sim, spec)
    assert sim.issued == [("climate", "set_hvac_mode", "climate.comfee", {"hvac_mode": "off"})], sim.issued
    assert sim.record["pending"] is not None
    assert len(sim._save_log) >= 2
    # Its sleeping state remains active after physical acknowledgment: no
    # setpoint/fan operations are allowed, but external cooldown proceeds.
    assert await sim._reconcile(spec)
    await before_tick(sim, spec)
    assert sim.issued[0][0] == "climate"
    assert sim.record["upstream"]["idle_since"] == BASE
    sim.now += 599
    await before_tick(sim, spec)
    assert len(sim.issued) == 1, sim.issued
    sim.now += 1
    await before_tick(sim, spec)
    assert sim.issued[-1][:3] == ("switch", "turn_off", "switch.strip"), sim.issued
    assert sim.record["upstream"]["pending"]["desired"] == "off"
    await before_tick(sim, spec)
    assert sim.record["upstream"]["owned"] is False
    assert sim.states["switch.strip"].state == "off"
    assert len(sim.issued) == 2


async def test_idle_stop_and_demand_recovery():
    sim = Simulator(sleeping=False, humidity=53)
    cfg = Model.settings(sim.manager, spec)
    assert approved_demand(sim, spec, cfg, sim.manager.cap) is False
    assert sim._stop_policy_verified(spec, sim.manager.cap, "idle")
    await tick(sim, spec)
    assert sim.issued[0][:3] == ("climate", "set_hvac_mode", "climate.comfee")
    assert sim.issued[0][3] == {"hvac_mode": "off"}
    assert await sim._reconcile(spec)
    await before_tick(sim, spec)
    assert sim.record["upstream"]["idle_since"] == BASE
    sim.humidity = 68
    assert approved_demand(sim, spec, cfg, sim.manager.cap) is True
    sim.now += 650
    await before_tick(sim, spec)
    assert sim.states["switch.strip"].state == "on", "Renewed need cancels power-off countdown"
    assert sim.record["upstream"].get("idle_since") is None
    assert len(sim.issued) == 1

    # Once idle is continuous for the configured cooldown, external OFF follows
    # only if the relay was owned by the integration.
    sim.humidity = 53
    await before_tick(sim, spec)
    sim.now += 601
    await before_tick(sim, spec)
    assert sim.states["switch.strip"].state == "off"


async def test_sleep_blocks_and_no_unowned_plug_off():
    sim = Simulator(sleeping=True, native="off", supply="off", owned=False)
    # No OFF appliance means no ON permission during verified sleeping pause.
    assert approved_demand(sim, spec, Model.settings(sim.manager, spec), sim.manager.cap) is False
    await before_tick(sim, spec)
    assert not sim.issued
    sim = Simulator(sleeping=True, native="off", supply="on", owned=False)
    await before_tick(sim, spec)
    sim.now += 1000
    await before_tick(sim, spec)
    assert not sim.issued, "Unowned ON supply must not be adopted/cut"
    assert sim.states["switch.strip"].state == "on"
    sim.manager.plan["sleeping"] = None
    assert approved_demand(sim, spec, Model.settings(sim.manager, spec), sim.manager.cap) is None
    assert not sim._stop_policy_verified(spec, sim.manager.cap, "sleep")


async def test_no_native_stop_on_races_or_unsafe_hardware():
    # No native OFF for source which hasn't been explicitly authorized.
    sim = Simulator(sleeping=True, authorized=False)
    await tick(sim, spec)
    assert not sim.issued
    # Physical minimum-ON duration holds before any native shutdown.
    sim = Simulator(sleeping=True)
    sim.states["climate.comfee"] = state("dry", when=BASE-90)
    await tick(sim, spec)
    assert not sim.issued
    # Do not run native shutdown once sleep ended during the durable intent.
    sim = Simulator(sleeping=True)
    sim.record["capabilities"] = asdict(sim.manager.cap)
    sim.on_save = lambda: sim.manager.plan.__setitem__("sleeping", False)
    await tick(sim, spec)
    assert not sim.issued
    assert sim.record.get("pending") is None
    # Likewise, changing IDLE demand during persistence invalidates stop.
    sim = Simulator(sleeping=False, humidity=53)
    sim.record["capabilities"] = asdict(sim.manager.cap)
    sim.on_save = lambda: setattr(sim, "humidity", 69)
    await tick(sim, spec)
    assert not sim.issued
    assert sim.record.get("pending") is None


async def main():
    await test_permissions_and_sleep_off()
    await test_idle_stop_and_demand_recovery()
    await test_sleep_blocks_and_no_unowned_plug_off()
    await test_no_native_stop_on_races_or_unsafe_hardware()
    print("PASS: sleep Pause turns native OFF and holds, unknown sleep blocks ON, measured idle turns OFF, owned relay 600s cooldown, resumed demand cancels cooldown, physical min-on, async races, unowned supply protection")


asyncio.run(main())
