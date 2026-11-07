"""Binary climate targets through the real tick, dispatch and ACK machinery.

No Home Assistant instance or physical equipment is used. The fixture supplies
HA state/service/registry transport, saved configuration, measurements, startup
readiness and room-policy inputs. It executes the production capability model,
PID math, tick, power/target selection, command persistence/rechecks, ACK matching,
retry and safety gates together. In particular, none of _native_target, _send,
_power or _reconcile is replaced by an expected-output stub.

HEM_TEST_RUNTIME_SOURCE may point to an older equipment_runtime.py to verify
that these behavioral cases fail on a release before the fix. CI leaves it unset.
"""
from __future__ import annotations

import ast
import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib.util
import math
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(os.environ.get("HEM_TEST_RUNTIME_SOURCE", ROOT / "equipment_runtime.py"))
PACKAGE = "hem_onoff_extrema_fixture"
PRIMARY = "climate.native_thermostat"
SPEC = N(identifier="binary_controller", area_id="room", source_device_id="thermostat",
         source_entities=(PRIMARY,))


def module(name):
    result = ModuleType(name)
    result.__package__ = name.rpartition(".")[0]
    sys.modules[name] = result
    return result


package = module(PACKAGE)
package.__path__ = []


def load_pure(name, filename):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def extract(path, names, scope, *, constants=()):
    """Compile the named production definitions unchanged, without HA imports."""
    selected = []
    for item in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if item.name in names:
                selected.append(item)
            elif isinstance(item, ast.ClassDef):
                selected.extend(n for n in item.body if isinstance(
                    n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names)
        elif isinstance(item, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constants for target in item.targets
        ):
            selected.append(item)
    actual = {item.name for item in selected if hasattr(item, "name")}
    assert actual == set(names), (str(path), set(names) - actual)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    tree = ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[]))
    exec(compile(tree, str(path), "exec"), scope)


maths = load_pure("pid_math", "pid_math.py")
phase = load_pure("pid_phase", "pid_phase.py")
load_pure("dry_mode", "dry_mode.py")
model = module(f"{PACKAGE}.equipment_model")
model.__dict__.update(dataclass=dataclass, math=math, finite=maths.finite,
                      target_from_unit=maths.target_from_unit,
                      configured_sources=lambda settings, area: (PRIMARY,),
                      room_config=lambda manager, spec: manager.room)
extract(ROOT / "equipment_model.py", (
    "Capabilities", "_strings", "features", "capabilities", "PIDMemory",
    "pid_step", "duty_on", "profile_name", "automatic_profile_reason",
), model.__dict__, constants=("TEMP", "RANGE", "HUMIDITY", "FAN", "PRESET", "SWING",
                             "SWING_H", "HVAC_MODES", "PRESETS"))
# The feature constants share a tuple assignment in the production source.
model.TEMP, model.RANGE, model.HUMIDITY, model.FAN = 1, 2, 4, 8
model.PRESET, model.SWING, model.SWING_H = 16, 32, 512
model.settings = lambda manager, spec: manager.settings
model.plan_for = lambda manager, spec: manager.plan
model.targets = lambda manager, spec, cap, cfg, plan: dict(manager.targets)
model.permission = lambda manager, spec, cap: (manager.soft_grant, manager.power_grant)
model.timing = lambda manager, spec, cap: (600.0, 600.0, 7200.0)
model.device_limits = lambda manager, spec, cap: {
    "temperature_min_limit": 10.0, "temperature_max_limit": 30.0,
    "humidity_min_limit": 20.0, "humidity_max_limit": 80.0,
}
model.sources_available = lambda manager, spec: all(
    (state := manager.hass.states.get(entity)) is not None
    and state.state not in ("unknown", "unavailable") for entity in spec.source_entities
)

# The target-crossing guard uses the real capability/target/measurement model
# above. Keep its import conditional so the same behavioral suite can be run
# against an isolated immutable release that predates this helper.
if (ROOT / "equipment_pid_safety.py").exists():
    load_pure("equipment_pid_safety", "equipment_pid_safety.py")


def live_permission(hass, area, room, plan, device):
    if hass.fixture.sleeping and device.get("sleep_behavior") == "pause":
        return "ineligible", "sleep_room_control_paused"
    return "eligible", None


activation = module(f"{PACKAGE}.device_activation")
activation.authorized = lambda manager, spec: manager.soft_grant
activation.effective_device = lambda manager, spec, entity, *, cap=None: manager.device
activation.mutable_copy = deepcopy
extract(ROOT / "device_activation.py", ("authority_context", "authorization_matches"), activation.__dict__)
occupancy = module(f"{PACKAGE}.occupancy_policy")
occupancy.live_device_permission = live_permission
windows = module(f"{PACKAGE}.equipment_window")
windows.evaluate = lambda runtime, spec, cfg=None: dict(runtime.window)
supply = module(f"{PACKAGE}.equipment_power_switch")
supply.__dict__.update(model=model, finite=maths.finite, Mapping=Mapping)
extract(ROOT / "equipment_power_switch.py", ("approved_demand", "output_required"), supply.__dict__)


async def no_upstream_switch(runtime, spec):
    assert runtime.manager.settings["power_switch_entity"] is None
    return False


supply.before_tick = no_upstream_switch
# The real shutdown gate reads registry identity; this is the fixture's one
# registered native entity, never a replacement for the gate itself.
helpers = sys.modules.setdefault("homeassistant.helpers", ModuleType("homeassistant.helpers"))
registry = ModuleType("homeassistant.helpers.entity_registry")
registry.async_get = lambda hass: N(async_get=lambda entity: N(
    platform="native_fixture", device_id=SPEC.source_device_id,
    id="registry-" + entity, unique_id="native-" + entity,
) if entity == PRIMARY else None)
helpers.entity_registry = registry
sys.modules[registry.__name__] = registry
ha = sys.modules.setdefault("homeassistant", ModuleType("homeassistant"))
ha.helpers = helpers

production = module(f"{PACKAGE}.equipment_runtime")
production.__dict__.update(
    asyncio=asyncio, deepcopy=deepcopy, asdict=asdict, model=model,
    finite=maths.finite, target_to_unit=maths.target_to_unit,
    target_from_unit=maths.target_from_unit, quantize_target=maths.quantize_target,
    DOMAIN="environment_manager", live_device_permission=live_permission,
    entity_area=lambda hass, entity: SPEC.area_id if entity == PRIMARY else None,
    foreign_owner_hold=lambda hass, entry, entity: hass.fixture.foreign_owner,
    _physical_climate_conflict=lambda hass, area, room, primary, mode: None,
)
METHODS = ("tick", "_native_target", "_send", "_power", "_reconcile", "_retry_pending",
           "_gate", "_stop_policy_verified", "_shutdown_allowed", "_window_policy", "_fan")
extract(RUNTIME, (*METHODS, "output_off", "snapshot", "matches", "_manual_output_changes",
                  "native_retry_decision"), production.__dict__, constants=(
    "ACK_SECONDS", "STARTUP_SECONDS", "NATIVE_COMMAND_MAX_ATTEMPTS",
    "NATIVE_COMMAND_RETRY_SECONDS", "NATIVE_OFF_FEEDBACK_GRACE_SECONDS",
    "NATIVE_RECONNECT_SETTLE_SECONDS", "NATIVE_RECONNECT_EXTRA_ATTEMPTS",
    "SETTABLE_OUTPUT_ATTRIBUTES", "MONITORED",
))
load_pure("equipment_setpoint_sequence", "equipment_setpoint_sequence.py")
load_pure("equipment_native_target", "equipment_native_target.py")


class NativeRuntime:
    def __init__(self, method="pid", mode="heat", *, absent=(), manual_preset=False,
                 low=5.0, high=35.0, step=0.5, unit="°C", off_age=1200.0):
        self.now = 100000.0
        self._started = self.now - 10000
        self._active = self._ready = True
        self._invalidated = set()
        self._memory, self._profile_wake, self._fan_allocations = {}, {}, {}
        self._pid_offline_previews = {}
        self._commands = asyncio.Semaphore(1)
        self.sleeping = False
        self.foreign_owner = None
        self.startup_ready = True
        self.settle_seconds = 0
        self.window = {"blocked": False, "stop_requested": False,
                       "status": "ready", "remaining_seconds": 0}
        self.calls, self.statuses, self.persisted = [], [], []
        self.measurement = 18.6 if mode == "heat" else 29.0
        self.manager = N(
            settings={
                # Exercise the optional Beta109 start/stop sequence explicitly.
                "timed_setpoint_sequence": True,
                "control_mode": method, "requested_mode": mode, "preset": "none",
                "kp": 10.0, "ki": 0.1, "kd": 0.0, "sample_seconds": 300.0,
                "cycle_seconds": 3600.0, "min_on_seconds": 600.0,
                "min_off_seconds": 600.0, "max_on_seconds": 7200.0,
                "pause_on_window_open": True, "pid_fan_capacity_mode": "legacy",
                "quiet_sleep": False, "quiet_occupied": False,
                "swing_mode": None, "swing_horizontal_mode": None,
                "profile_targets": {}, "profile_fans": {}, "power_switch_entity": None,
            },
            targets={"heat": 21.0, "cool": 26.0, "humidity": 50.0},
            plan={"away": "home", "occupancy": "occupied", "window_safe": True},
            room={}, device={"sleep_behavior": "normal"},
            soft_grant=True, power_grant=True, entry=N(entry_id="test_entry"),
        )
        self.state = N(
            domain="climate", state="off", context=N(user_id=None, parent_id=None),
            attributes={
                "temperature": low if mode == "heat" else high,
                "temperature_unit": unit, "min_temp": low, "max_temp": high,
                "target_temp_step": step, "hvac_modes": ["off", "heat", "cool"],
                "preset_modes": ["manual"] if manual_preset else [],
                "supported_features": 1, "hvac_action": "idle",
            },
            last_changed=datetime.fromtimestamp(self.now - off_age, timezone.utc),
        )
        for key in absent:
            self.state.attributes.pop(key)
        self.hass = N(
            fixture=self, states=N(get=lambda entity: self.state if entity == PRIMARY else None),
            services=N(has_service=lambda domain, service: True, async_call=self.service_call),
        )
        self.manager.hass = self.hass
        self.record = {
            "sources": list(SPEC.source_entities), "source_device_id": SPEC.source_device_id,
            "area": SPEC.area_id, "power": {}, "baseline": {}, "off_at": {},
            "pending": None, "upstream": {},
        }
        self.records = {SPEC.identifier: self.record}

    def clock(self):
        return self.now

    def _record(self, spec):
        return self.record

    def _current_spec(self, spec):
        return True

    def _identity_ok(self, spec):
        return True

    def _startup_readiness(self, spec):
        return {"ready": self.startup_ready, "reason": "startup_fixture_hold"}

    def _native_settle_remaining(self, spec):
        return self.settle_seconds

    async def _observe_native_running(self, spec, cap, state):
        pass  # No restart/reconnect adoption; only actual mode ACK creates ownership.

    async def _reconcile_native_after_supply_wake(self, spec, cap):
        return True  # This fixture has no external supply switch.

    def _quiet_context(self, *args):
        return False

    def measurements(self, spec, cap):
        return {"temperature": self.measurement, "humidity": 50.0, "pm25": None, "co2": None}

    def _status(self, spec, value, **details):
        self.statuses.append((value, details))

    async def _save(self):
        self.persisted.append(deepcopy(self.record))

    async def _pause(self, spec, reason):
        self.record["paused"] = reason
        self._status(spec, "paused", reason=reason)
        await self._save()

    async def service_call(self, domain, service, data, **kwargs):
        # Transport success deliberately does NOT alter the native HA state.
        self.calls.append({"domain": domain, "service": service, "data": deepcopy(data),
                           "target": deepcopy(kwargs.get("target"))})

    def report(self, *, mode=None, temperature=None):
        if mode is not None and mode != self.state.state:
            self.state.state = mode
            self.state.last_changed = datetime.fromtimestamp(self.now, timezone.utc)
        if temperature is not None:
            self.state.attributes["temperature"] = temperature

    def own_running(self, age=100.0):
        self.report(mode=self.manager.settings["requested_mode"])
        self.state.last_changed = datetime.fromtimestamp(self.now - age, timezone.utc)
        self.record["power"][PRIMARY] = {"since": self.now - age, "min_on": 600.0,
                                         "max_on": 7200.0}
        self.record["baseline"][PRIMARY] = production.snapshot(self.state)


for method in METHODS:
    setattr(NativeRuntime, method, getattr(production, method))


class OnOffNativeExtremaTests(unittest.IsolatedAsyncioTestCase):
    async def test_on_ack_then_exact_target_for_both_methods_and_optional_metadata(self):
        for method in ("pid", "automatic"):
            for mode, expected in (("heat", 35.0), ("cool", 5.0)):
                for absent in ((), ("temperature_unit",), ("target_temp_step",),
                               ("temperature_unit", "target_temp_step")):
                    for manual_preset in (False, True):
                        with self.subTest(method=method, mode=mode, absent=absent,
                                          manual_preset=manual_preset):
                            runtime = NativeRuntime(method, mode, absent=absent,
                                                    manual_preset=manual_preset)
                            await runtime.tick(SPEC)
                            self.assertEqual(runtime.calls, [{
                                "domain": "climate", "service": "set_hvac_mode",
                                "data": {"hvac_mode": mode}, "target": {"entity_id": PRIMARY},
                            }])
                            self.assertEqual(runtime.state.state, "off")
                            self.assertFalse(runtime.record["power"])
                            self.assertEqual(runtime.record["pending"]["phase"], "commanded")
                            runtime.now += 5
                            await runtime.tick(SPEC)
                            self.assertEqual(len(runtime.calls), 1, "No target before native mode ACK")
                            runtime.report(mode=mode)
                            await runtime.tick(SPEC)
                            self.assertEqual(len(runtime.calls), 1, "Native ON begins the 30-second setpoint grace")
                            runtime.now += 30
                            await runtime.tick(SPEC)
                            self.assertEqual(runtime.calls[-1], {
                                "domain": "climate", "service": "set_temperature",
                                "data": {"temperature": expected}, "target": {"entity_id": PRIMARY},
                            }, runtime.statuses)
                            self.assertEqual(len(runtime.calls), 2)
                            self.assertIn(PRIMARY, runtime.record["power"])
                            self.assertNotEqual(runtime.state.attributes["temperature"], expected)
                            self.assertEqual(runtime.record["pending"]["phase"], "commanded")
                            self.assertEqual(runtime.statuses[-1][0], "command_sent")
                            runtime.now += 5
                            await runtime.tick(SPEC)
                            self.assertEqual(len(runtime.calls), 2, "Pending target must serialize commands")
                            self.assertEqual(runtime.statuses[-1][0], "awaiting_physical_acknowledgement")
                            runtime.report(temperature=expected)
                            await runtime.tick(SPEC)
                            self.assertIsNone(runtime.record["pending"])
                            self.assertEqual(len(runtime.calls), 2, "ACKed extremum needs no repeated command")

    async def test_delayed_target_ack_retries_the_same_native_payload(self):
        # Automatic retains its existing ongoing retry policy. PID's three
        # total full-output requests are covered by the dedicated b8 gate.
        runtime = NativeRuntime(method="automatic", absent=("temperature_unit", "target_temp_step"))
        runtime.own_running()
        await runtime.tick(SPEC)
        self.assertEqual(len(runtime.calls), 1, runtime.statuses)
        original = deepcopy(runtime.calls[-1])
        for attempt in (2, 3, 4):
            runtime.now += 60
            await runtime.tick(SPEC)
            self.assertEqual(runtime.calls[-1], original)
            self.assertEqual(runtime.record["pending"]["attempts"], attempt)
            self.assertNotIn("paused", runtime.record)
        runtime.report(temperature=35.0)
        await runtime.tick(SPEC)
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(len(runtime.calls), 4)

    async def test_reported_bound_is_not_rounded_or_converted(self):
        for method in ("pid", "automatic"):
            for mode, expected in (("heat", 30.2), ("cool", 5.1)):
                with self.subTest(method=method, mode=mode):
                    runtime = NativeRuntime(method, mode, low=5.1, high=30.2, step=0.5)
                    runtime.own_running()
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1]["data"], {"temperature": expected})
            runtime = NativeRuntime(method, "heat", low=45.0, high=95.0, step=1.0, unit="°F")
            runtime.own_running()
            await runtime.tick(SPEC)
            self.assertEqual(runtime.calls[-1]["data"], {"temperature": 95.0})

    async def test_missing_required_feedback_preserves_its_blocker(self):
        for method in ("pid", "automatic"):
            for field, status in (("min_temp", "physical_capabilities_unavailable"),
                                  ("max_temp", "physical_capabilities_unavailable"),
                                  ("temperature", "native_setpoint_unavailable")):
                with self.subTest(method=method, field=field):
                    runtime = NativeRuntime(method, absent=(field,))
                    runtime.own_running()
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls, [])
                    self.assertEqual(runtime.statuses[-1][0], status)
                    self.assertIsNone(runtime.record["pending"])

    async def test_unavailable_service_keeps_dispatch_blocker_visible(self):
        runtime = NativeRuntime()
        runtime.own_running()
        runtime.hass.services.has_service = lambda domain, service: service != "set_temperature"
        await runtime.tick(SPEC)
        self.assertEqual(runtime.calls, [])
        self.assertIsNone(runtime.record["pending"])
        self.assertEqual(runtime.statuses[-1], (
            "native_service_unavailable", {"service": "climate.set_temperature"},
        ))

    async def test_off_no_demand_and_safety_holds_never_write_on_extreme(self):
        for method in ("pid", "automatic"):
            for mode in ("heat", "cool"):
                with self.subTest(method=method, mode=mode, case="minimum_off"):
                    runtime = NativeRuntime(method, mode, off_age=100.0)
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls, [])
                    self.assertEqual(runtime.statuses[-1][0], "minimum_off_hold")
                with self.subTest(method=method, mode=mode, case="idle_off"):
                    runtime = NativeRuntime(method, mode)
                    runtime.measurement = 23.0
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls, [])
                with self.subTest(method=method, mode=mode, case="idle_running"):
                    runtime = NativeRuntime(method, mode)
                    runtime.own_running(age=900.0)
                    runtime.measurement = 23.0
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1]["data"], {
                        "temperature": 5.0 if mode == "heat" else 35.0,
                    })
                    runtime.now += 30
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                    self.assertEqual(len(runtime.calls), 2)
            for hold in ("startup", "unavailable", "window", "sleep", "defrost", "foreign", "settling"):
                with self.subTest(method=method, hold=hold):
                    runtime = NativeRuntime(method)
                    runtime.own_running(age=900.0)
                    if hold == "startup":
                        runtime.startup_ready = False
                    elif hold == "unavailable":
                        runtime.state.state = "unavailable"
                    elif hold == "window":
                        runtime.window.update(blocked=True, stop_requested=True, status="window_open_pause")
                    elif hold == "sleep":
                        runtime.sleeping = True
                        runtime.manager.device["sleep_behavior"] = "pause"
                    elif hold == "defrost":
                        runtime.state.attributes["hvac_action"] = "defrosting"
                    elif hold == "foreign":
                        runtime.foreign_owner = "other_controller_owns_source"
                    else:
                        runtime.settle_seconds = 30.0
                    await runtime.tick(SPEC)
                    if hold in ("window", "sleep"):
                        self.assertEqual(runtime.calls[-1]["data"], {"temperature": 5.0})
                        runtime.now += 30
                        await runtime.tick(SPEC)
                        self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                        self.assertEqual(len(runtime.calls), 2)
                    else:
                        self.assertEqual(runtime.calls, [])

    async def test_pwm_off_phase_corrects_target_only_during_mandatory_on_hold(self):
        for age, expected in ((100.0, 35.0), (900.0, 5.0)):
            with self.subTest(age=age):
                runtime = NativeRuntime(absent=("temperature_unit", "target_temp_step"))
                runtime.own_running(age=age)
                cfg = runtime.manager.settings
                signature, _, _ = phase.phase_decision(
                    None, metric="temperature", target=21.0, increasing=True, profile="comfort",
                    mode="heat", preset="none", kp=cfg["kp"], ki=cfg["ki"], kd=cfg["kd"],
                    cycle_s=3600.0, min_on_s=600.0, min_off_s=600.0, measured=runtime.measurement,
                )
                memory = model.PIDMemory(measured=runtime.measurement, stamp=runtime.now, demand=24.0)
                runtime._memory[SPEC.identifier] = signature, memory, runtime.now - 1500.0
                await runtime.tick(SPEC)
                self.assertEqual(len(runtime.calls), 1, runtime.statuses)
                self.assertEqual(runtime.calls[-1]["service"], "set_temperature", runtime.statuses)
                self.assertEqual(runtime.calls[-1]["data"], {"temperature": expected})
                if age == 900:
                    runtime.now += 30
                    await runtime.tick(SPEC)
                    self.assertEqual(runtime.calls[-1]["data"], {"hvac_mode": "off"})
                    self.assertEqual(len(runtime.calls), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
