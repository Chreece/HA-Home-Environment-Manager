"""Beta70: profile transition restarts a logical PWM phase, not physical dwell.

Execute the actual EquipmentRuntime.tick source, real PID step, real duty_on
and real profile name with isolated HA state and physical output stubs.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, asdict
import importlib.util
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

ROOT = Path(__file__).resolve().parents[2]


def extract(file, names, ns):
    nodes = ast.parse((ROOT / file).read_text()).body
    chosen = []
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in names:
            chosen.append(node)
        if isinstance(node, ast.ClassDef):
            chosen.extend(c for c in node.body if isinstance(
                c, (ast.FunctionDef, ast.AsyncFunctionDef)) and c.name in names)
    assert {n.name for n in chosen} == set(names), (file, names)
    exec(compile(ast.Module(body=chosen, type_ignores=[]), file, "exec"), ns)
    return tuple(ns[x] for x in names)


phase_ns = {"math": math, "TARGET_CHANGE_C": 0.25, "COMFORT_ERROR_C": 0.5}
(phase_decision,) = extract("pid_phase.py", ("phase_decision",), phase_ns)
model_ns = {"math": math, "dataclass": dataclass}
PIDMemory, pid_step, duty_on, profile_name = extract(
    "equipment_model.py", ("PIDMemory", "pid_step", "duty_on", "profile_name"),
    model_ns,
)
assert duty_on(12.0, 0.0, 3600, 600, 600, starting=True) is False

# Meaningful changes trigger only a NEW LOGICAL phase and one-shot wake intent.
base, reset, prime = phase_decision(
    None, metric="temperature", target=21., increasing=True, profile="comfort",
    mode="heat", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=19.8,
)
assert reset and prime
same, reset, prime = phase_decision(
    base, metric="temperature", target=21.12, increasing=True,
    profile="comfort", mode="heat", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=19.8,
)
assert same == base and not reset and not prime, "Small target noise must not restart cycles"
up, reset, prime = phase_decision(
    base, metric="temperature", target=22., increasing=True, profile="comfort",
    mode="heat", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=19.8,
)
assert reset and prime
down, reset, prime = phase_decision(
    base, metric="temperature", target=18., increasing=True, profile="away",
    mode="heat", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=19.8,
)
assert reset and not prime, "Away transition must not force a pulse"
only_profile, reset, prime = phase_decision(
    base, metric="temperature", target=21., increasing=True, profile="home",
    mode="heat", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=19.8,
)
assert reset and not prime
cool, reset, prime = phase_decision(
    base, metric="temperature", target=17., increasing=False, profile="comfort",
    mode="cool", preset="none", kp=10., ki=.1, kd=0.,
    cycle_s=3600, min_on_s=600, min_off_s=600, measured=20.,
)
assert reset and prime

pkg = ModuleType("test_beta70")
pkg.__path__ = []
supply = ModuleType("test_beta70.equipment_power_switch")
async def supply_tick(runtime, spec):
    return False
supply.before_tick = supply_tick
sys.modules[pkg.__name__] = pkg
sys.modules[supply.__name__] = supply


@dataclass(frozen=True)
class Cap:
    primary: str = "climate.wohnzimmer"
    domain: str = "climate"
    modes: tuple = ("off", "heat")
    temperature: bool = True
    humidity: bool = False
    fan_entity: str | None = None
    fan_modes: tuple = ()
    fan_percentage: bool = False


spec = N(
    identifier="wohnzimmer_controller", area_id="wohnzimmer",
    source_device_id="native-heater", source_entities=("climate.wohnzimmer",),
)
settings = {
    "control_mode": "pid", "requested_mode": "heat", "preset": "none",
    "kp": 10., "ki": .1, "kd": 0.,
    "sample_seconds": 300., "cycle_seconds": 3600.,
    "min_on_seconds": 600., "min_off_seconds": 600.,
    "pause_on_window_open": False, "pid_fan_capacity_mode": "legacy",
    "quiet_sleep": False, "quiet_occupied": False,
    "swing_mode": None, "swing_horizontal_mode": None,
    "profile_targets": {}, "profile_fans": {},
}
def make_profile(config, plan):
    return profile_name(config, plan)

model = N(
    settings=lambda manager, spec: manager.settings,
    plan_for=lambda manager, spec: manager._harness.plan,
    sources_available=lambda manager, spec: True,
    capabilities=lambda manager, spec: Cap(),
    profile_name=make_profile,
    targets=lambda manager, spec, cap, cfg, plan: {
        "heat": manager.goals[make_profile(cfg, plan)],
        "cool": 26., "humidity": 50.,
    },
    permission=lambda manager, spec, cap: (True, True),
    timing=lambda manager, spec, cap: (600., 600., 7200.),
    pid_step=pid_step, duty_on=duty_on,
)
runtime_ns = {
    "__name__": "test_beta70.equipment_runtime",
    "__package__": "test_beta70",
    "model": model,
    "asdict": asdict,
    "output_off": lambda s: s is not None and s.state == "off",
    "snapshot": lambda s: None if s is None else {"state": s.state, "attributes": dict(s.attributes)},
    "finite": lambda v, lo, hi: v if isinstance(v,(float,int)) and lo <= v <= hi else None,
}
(tick,) = extract("equipment_runtime.py", ("tick",), runtime_ns)


class Harness:
    def __init__(self, *, off_age=1200):
        self.now = 100000.
        self._active = self._ready = True
        self._started = self.now-10000
        self._invalidated = set()
        self._memory = {}
        self._profile_wake = {}
        self._fan_allocations = {}
        self._pid_offline_previews = {}
        self.manager = N(
            settings=dict(settings),
            goals={"away":16., "home":18., "comfort":21.,
                   "sleep":18., "manual":21., "eco":17.},
        )
        self.plan = {"away":"away", "occupancy":"unoccupied"}
        self.manager._harness = self
        self.state = N(state="off", domain="climate",
                       attributes={"hvac_action":"idle"}, last_changed=N(
                         timestamp=lambda: self.now-off_age))
        self.hass = N(states=N(get=lambda entity: self.state if entity == Cap().primary else None))
        self.records = {"power": {}, "baseline": {}, "off_at": {}, "pending": None}
        self.actions = []
        self.status = None
        self.measurement = 19.8
    def _record(self, spec): return self.records
    def _current_spec(self, spec): return True
    def clock(self): return self.now
    async def _save(self): pass
    async def _reconcile(self, spec): return True
    def _stop_policy_verified(self, spec, cap, policy): return False
    def _gate(self, spec, cap, cfg, plan, mode, *, automatic=True): return None
    def measurements(self, spec, cap): return {"temperature":self.measurement,"humidity":51.28,"pm25":None,"co2":None}
    def _status(self, spec, value, **details): self.status = (value, details)
    async def _power(self, spec, cap, desired, **kw):
        if desired != "off":
            if self.now - self.state.last_changed.timestamp() < 600:
                self.status = ("minimum_off_hold", {})
                return False
            self.actions.append(desired)
            self.state.state = "heat"
        return True
    async def _native_target(self,*a): return False
    async def _fan(self,*a): return False
    def _quiet_context(self,*a): return None


async def tests():
    # First Away tick has no heating demand (room 19.8, Away target 16).
    r=Harness()
    await tick(r,spec)
    assert not r.actions and r.status[0] == "within_target_band", r.status
    assert r._memory[spec.identifier][0][3] == "away"
    # Room occupied: away->comfort profile and target goes 16 -> 21.
    # 10%/C * 1.2 C = 12% duty (7.2 minutes) < physical min ON 10 minutes.
    r.plan = {"away":"home","occupancy":"occupied"}
    await tick(r,spec)
    assert r.actions == ["heat"], (r.actions,r.status,r._profile_wake)

    # If output was physically switched OFF only 3 minutes ago, the logical
    # phase rebase must NOT bypass the 10-minute physical minimum OFF.
    x=Harness(off_age=180)
    await tick(x,spec)
    x.plan = {"away":"home","occupancy":"occupied"}
    await tick(x,spec)
    assert x.actions==[] and x.status[0]=="minimum_off_hold"
    pending=x._profile_wake.get(spec.identifier)
    assert pending and pending["profile"]=="comfort",pending
    x.now += 421
    await tick(x,spec)
    assert x.actions==["heat"],(x.status,x.actions)
    # A small dynamic target adjustment must not restart a pending cycle.
    y=Harness()
    y.plan={"away":"home","occupancy":"occupied"}
    await tick(y,spec)
    old_signature, old_memory, old_anchor = y._memory[spec.identifier]
    y.manager.goals["comfort"]=21.1
    y.now += 10
    await tick(y,spec)
    assert y._memory[spec.identifier][0] == old_signature
    assert y._memory[spec.identifier][2] == old_anchor
    print("PASS: profile transition immediate ON, below-minimum duty, 600s hardware OFF hold, recovery pending, jitter-resistant phase")
asyncio.run(tests())
