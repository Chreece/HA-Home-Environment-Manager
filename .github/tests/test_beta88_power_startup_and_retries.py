"""Beta88: native startup grace, fully driven binary targets, and three ACK retries.

Tests extract actual HEM code and use simulated Home Assistant state/services.
No device commands are executed on a real Home Assistant installation.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "equipment_runtime.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
METHODS = next(n for n in TREE.body if isinstance(n, ast.ClassDef)
               and n.name == "EquipmentRuntime")


def finite(value, low, high):
    try:
        number = float(value)
        return number if math.isfinite(number) and low <= number <= high else None
    except (ValueError, TypeError, OverflowError):
        return None


def snapshot(state):
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    return {"state": state.state, "attributes": dict(state.attributes)}


def matches(state, expected):
    if state is None or state.state in ("unknown", "unavailable"):
        return False
    return (("state" not in expected or state.state == expected["state"])
            and all(state.attributes.get(k) == v
                    for k, v in expected.get("attributes", {}).items()))


def changes(old, new):
    if old is None or new is None or old["state"] != new["state"]:
        return ("state",)
    return tuple(k for k in ("temperature", "humidity", "fan_mode",
                             "percentage", "preset_mode")
                 if k in old["attributes"] and k in new["attributes"]
                 and old["attributes"][k] != new["attributes"][k])


@dataclass
class Cap:
    primary: str = "climate.heater"
    domain: str = "climate"
    modes: tuple = ("off", "heat", "cool")
    temperature: bool = True
    humidity: bool = False


class Model:
    TEMP = 1
    HUMIDITY = 4

    @staticmethod
    def settings(manager, spec):
        return manager.settings["cfg"]

    @staticmethod
    def capabilities(manager, spec):
        return manager.cap

    @staticmethod
    def sources_available(manager, spec):
        return manager.hass.states.get(spec.source_entities[0]).state not in ("unknown", "unavailable")

    @staticmethod
    def plan_for(manager, spec):
        return manager.plan

    @staticmethod
    def room_config(manager, spec):
        return manager.room

    @staticmethod
    def profile_name(cfg, plan):
        return plan["profile"]

    @staticmethod
    def permission(manager, spec, cap):
        return True, manager.power_permission

    @staticmethod
    def device_limits(manager, spec, cap):
        return {"temperature_min_limit": 10.0, "temperature_max_limit": 30.0,
                "humidity_min_limit": 20.0, "humidity_max_limit": 80.0}

    @staticmethod
    def features(state):
        return state.attributes.get("supported_features", 1)


pkg = ModuleType("hem_beta88_fixture")
pkg.__path__ = []
supply = ModuleType("hem_beta88_fixture.equipment_power_switch")
supply.approved_demand = lambda runtime, spec, cfg, cap: runtime.demand
sys.modules[pkg.__name__] = pkg
sys.modules[supply.__name__] = supply


def extract():
    helpers = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
               and n.name in ("native_retry_decision", "snapshot", "matches",
                              "_manual_output_changes")]
    constants = [n for n in TREE.body if isinstance(n, ast.Assign)
                 and any(isinstance(target, ast.Name) and (
                     target.id.startswith("NATIVE_")
                     or target.id in ("MONITORED", "SETTABLE_OUTPUT_ATTRIBUTES"))
                     for target in n.targets)]
    requested = ("_retry_pending", "_native_target")
    methods = [n for n in METHODS.body if isinstance(n, ast.AsyncFunctionDef)
               and n.name in requested]
    assert len(methods) == len(requested)
    scope = {
        "__name__": "hem_beta88_fixture.equipment_runtime",
        "__package__": "hem_beta88_fixture",
        "asyncio": asyncio, "finite": finite, "model": Model,
        "snapshot": snapshot, "matches": matches,
        "_manual_output_changes": changes, "asdict": asdict,
        "entity_area": lambda hass, entity: "kitchen",
        "foreign_owner_hold": lambda hass, entry, entity: None,
        "NATIVE_COMMAND_MAX_ATTEMPTS": 4,
        "NATIVE_COMMAND_RETRY_SECONDS": 30,
        "NATIVE_OFF_FEEDBACK_GRACE_SECONDS": 60,
        "NATIVE_RECONNECT_SETTLE_SECONDS": 30,
        "NATIVE_RECONNECT_EXTRA_ATTEMPTS": 2,
        "target_to_unit": lambda value, unit: float(value),
        "target_from_unit": lambda value, unit: float(value),
        "quantize_target": lambda value, step, low, high:
            min(high, max(low, round(float(value) / step) * step)),
    }
    exec(compile(ast.Module(body=[*constants, *helpers, *methods], type_ignores=[]),
                 str(SOURCE), "exec"), scope)
    return scope


NS = extract()
# The target guard executes the actual production target calculation with
# explicit room-profile inputs, rather than a fixture granting every command.
target_source = ast.parse((ROOT / "equipment_model.py").read_text(encoding="utf-8"))
target_function = next(n for n in target_source.body
                       if isinstance(n, ast.FunctionDef) and n.name == "targets")
# Target defaults now come from the same pure module as the room editors.
for helper in ("climate_equipment", "pid_math", "comfort_targets", "climate_strategy"):
    helper_spec = importlib.util.spec_from_file_location(
        f"hem_beta88_fixture.{helper}", ROOT / f"{helper}.py")
    helper_module = importlib.util.module_from_spec(helper_spec)
    sys.modules[helper_spec.name] = helper_module
    helper_spec.loader.exec_module(helper_module)
strategy = sys.modules["hem_beta88_fixture.climate_strategy"]
target_scope = {
    "room_config": Model.room_config,
    "profile_name": Model.profile_name,
    "device_limits": Model.device_limits,
    "DEFAULT_PROFILE_TARGETS": strategy.DEFAULT_PROFILE_TARGETS,
    "profile_humidity_target": strategy.profile_humidity_target,
    "PRESETS": ast.literal_eval(next(
        node.value for node in target_source.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PRESETS" for target in node.targets)
    )),
}
profile_guard = next(node for node in target_source.body
                     if isinstance(node, ast.FunctionDef) and node.name == "automatic_profile_reason")
target_tree = ast.Module(body=[ast.ImportFrom(
    module="__future__", names=[ast.alias(name="annotations")], level=0,
), target_function, profile_guard], type_ignores=[])
exec(compile(ast.fix_missing_locations(target_tree), "equipment_model.py", "exec"), target_scope)
Model.targets = staticmethod(target_scope["targets"])
Model.automatic_profile_reason = staticmethod(target_scope["automatic_profile_reason"])
sys.modules["hem_beta88_fixture.equipment_model"] = Model
pkg.equipment_model = Model
runtime_module = ModuleType("hem_beta88_fixture.equipment_runtime")
runtime_module.__dict__.update(NS)
sys.modules[runtime_module.__name__] = runtime_module
for helper in ("pid_math", "equipment_setpoint_sequence", "equipment_pid_safety"):
    helper_spec = importlib.util.spec_from_file_location(
        f"hem_beta88_fixture.{helper}", ROOT / f"{helper}.py")
    helper_module = importlib.util.module_from_spec(helper_spec)
    sys.modules[helper_spec.name] = helper_module
    helper_spec.loader.exec_module(helper_module)
SPEC = SimpleNamespace(identifier="controller", area_id="kitchen",
                       source_entities=("climate.heater",))


class State:
    def __init__(self, mode="off", *, temperature=20, presets=(), changed=0.0):
        self.domain = "climate"
        self.state = mode
        # Existing-state fixtures have already completed native startup.
        # Tests of a newly acknowledged ON supply the actual newer timestamp.
        self.last_changed = SimpleNamespace(timestamp=lambda: changed)
        self.attributes = {
            "temperature": temperature, "temperature_unit": "°C",
            "min_temp": 5, "max_temp": 35, "target_temp_step": 0.5,
            "hvac_modes": ["off", "heat", "cool"],
            "preset_modes": list(presets), "supported_features": 1,
        }


class SimRuntime:
    _retry_pending = NS["_retry_pending"]
    _native_target = NS["_native_target"]

    def __init__(self, mode="off", *, manual=False):
        self.now = 1000.0
        self.state = State(mode, presets=("manual",) if manual else ())
        self.calls = []
        self.statuses = []
        self.saves = 0
        self.record = {"baseline": {"climate.heater": snapshot(self.state)},
                       "capabilities": asdict(Cap()), "power": {},
                       "upstream": {}}
        self._active = self._ready = True
        self._commands = asyncio.Semaphore(1)
        self.demand = True
        self.manager = SimpleNamespace(
            settings={"cfg": {"control_mode": "pid", "requested_mode": "heat",
                              "sample_seconds": 120,
                              "power_switch_entity": None}},
            cap=Cap(), plan={"away": "home", "profile": "home"},
            room={"profiles": {"home": {
                "heat_c": 21., "cool_c": 26., "humidity": 50.,
            }}},
            power_permission=True,
            entry=SimpleNamespace(entry_id="test"),
        )
        self.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity: self.state),
            services=SimpleNamespace(
                has_service=lambda domain, action: True,
                async_call=self._call,
            ),
        )
        self.manager.hass = self.hass

    def clock(self):
        return self.now

    def measurements(self, spec, cap):
        return {"temperature": 18., "humidity": 55., "co2": None, "pm25": None}

    def _record(self, spec):
        return self.record

    def _status(self, spec, status, **details):
        self.statuses.append((status, details))

    def _identity_ok(self, spec):
        return True

    def _current_spec(self, spec):
        return True

    def _gate(self, *args, **kwargs):
        return None

    def _stop_policy_verified(self, *args, **kwargs):
        return True

    def _shutdown_allowed(self, *args, **kwargs):
        return True

    async def _save(self):
        self.saves += 1

    async def _pause(self, spec, reason):
        self.record["paused"] = reason
        self._status(spec, "paused", reason=reason)
        await self._save()

    async def _call(self, domain, action, data, **kwargs):
        self.calls.append((domain, action, dict(data)))

    async def _send(self, spec, cap, entity, service, data, expected, **kwargs):
        self.calls.append((entity, service, dict(data)))
        return True

    def pending(self):
        cfg = self.manager.settings["cfg"]
        self.record["pending"] = {
            "entity": "climate.heater", "service": "set_hvac_mode",
            "data": {"hvac_mode": "heat"}, "expected": {"state": "heat"},
            "power": True, "phase": "commanded",
            "attempts": 1, "when": self.now, "last_attempt_at": self.now,
            "retry_context": {
                "settings": dict(cfg), "profile": "home",
                "mode": "heat", "automatic": True,
                "shutdown": False, "policy_stop": None,
                "upstream_owned": None,
            },
        }
        return self.record["pending"]


class CommandRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_retries_before_no_ack_diagnostic(self):
        r = SimRuntime()
        p = r.pending()
        r.now += 29
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(len(r.calls), 0)
        self.assertNotIn("paused", r.record)
        for attempt in (2, 3, 4):
            r.now += 30
            await r._retry_pending(SPEC, p, r.now)
            self.assertEqual(p["attempts"], attempt)
            self.assertEqual(len(r.calls), attempt - 1)
            self.assertEqual(p["phase"], "commanded")
            self.assertNotIn("paused", r.record)
        r.now += 30
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(len(r.calls), 3)
        self.assertEqual(r.record["paused"], "physical_acknowledgement_missing")
        self.assertEqual(r.statuses[-1][1]["command_retries_completed"], 3)

    async def test_unavailable_device_does_not_consume_retries(self):
        r = SimRuntime()
        p = r.pending()
        r.now += 45
        r.state.state = "unavailable"
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(p["attempts"], 1)
        self.assertEqual(r.calls, [])
        self.assertNotIn("paused", r.record)
        r.state.state = "off"
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(p["attempts"], 2)

    async def test_changed_consent_never_replays_stale_command(self):
        r = SimRuntime()
        p = r.pending()
        r.manager.settings["cfg"]["requested_mode"] = "cool"
        r.now += 30
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(r.calls, [])
        self.assertEqual(p["attempts"], 1)
        self.assertEqual(r.record["paused"], "native_retry_authority_or_state_changed")

    async def test_physical_manual_change_blocks_retry(self):
        r = SimRuntime()
        p = r.pending()
        r.state.state = "cool"
        r.now += 30
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(r.calls, [])
        self.assertEqual(r.record["paused"], "native_retry_authority_or_state_changed")

    async def test_ambiguous_native_service_failure_holds(self):
        r = SimRuntime()
        p = r.pending()
        r.now += 30

        async def failed(*args, **kwargs):
            raise TimeoutError("physical service uncertain")

        r.hass.services.async_call = failed
        await r._retry_pending(SPEC, p, r.now)
        self.assertEqual(p["phase"], "retry_intent")
        self.assertEqual(r.record["paused"], "native_command_failed_or_uncertain")
        self.assertNotEqual(r.record["paused"], "physical_acknowledgement_missing")

    async def test_binary_heat_cool_full_setpoints_with_native_limits(self):
        for mode, expected in (("heat", 35.0), ("cool", 5.0)):
            with self.subTest(mode=mode):
                r = SimRuntime(mode)
                r.now = 5000
                r.manager.settings["cfg"]["requested_mode"] = mode
                self.assertTrue(await r._native_target(
                    SPEC, r.manager.cap, mode,
                    {"heat": 19.0, "cool": 26.0}, None, True))
                self.assertEqual(r.calls[-1][2], {"temperature": expected})

    async def test_automatic_native_manual_preset_still_uses_full_binary_output(self):
        r = SimRuntime("heat", manual=True)
        r.manager.settings["cfg"]["control_mode"] = "automatic"
        r.now = 5000
        self.assertTrue(await r._native_target(
            SPEC, r.manager.cap, "heat",
            {"heat": 18.0, "cool": 26.0}, None, True))
        self.assertEqual(r.calls[-1][2], {"temperature": 35.0})

    async def test_pid_native_manual_preset_still_uses_full_binary_output(self):
        r = SimRuntime("heat", manual=True)
        r.now = 5000
        self.assertTrue(await r._native_target(
            SPEC, r.manager.cap, "heat",
            {"heat": 18.0, "cool": 26.0}, None, True))
        self.assertEqual(r.calls[-1][2], {"temperature": 35.0})

    async def test_without_native_power_permission_keeps_soft_trim(self):
        r = SimRuntime("heat")
        r.now = 5000
        r.manager.power_permission = False
        # Automatic dispatch re-resolves the saved profile after any await;
        # the configured goal and this fixture's supplied target must agree.
        r.manager.room["profiles"]["home"]["heat_c"] = 18.0
        self.assertTrue(await r._native_target(
            SPEC, r.manager.cap, "heat",
            {"heat": 18.0, "cool": 26.0}, None, True))
        self.assertEqual(r.calls[-1][2], {"temperature": 19.5})

    async def test_native_off_has_no_setpoint_write(self):
        r = SimRuntime("off")
        self.assertFalse(await r._native_target(
            SPEC, r.manager.cap, "heat",
            {"heat": 19.0, "cool": 26.0}, None, True))
        self.assertEqual(r.calls, [])


class SupplyBootTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_supply_allows_sixty_seconds_and_reserves_pid(self):
        src = runpy.run_path(str(ROOT / ".github/tests/test_beta83_supply_safety.py"))
        case = src["PowerSafetyTests"]()
        case.setUp()
        case.cfg["control_mode"] = "pid"
        case.demand = True
        case.now = 1000.0
        case.states.values["climate.native"].state = "unavailable"
        relay = case.record["upstream"]
        relay["on_at"] = 995.0
        relay["native_wake"] = {
            "identity": dict(relay["identity"]),
            "on_at": 995.0, "off_at": 400.0, "reconciled": False,
        }
        statuses = []
        case.runtime._status = lambda spec, status, **kw: statuses.append((status, kw))
        case.ns["prepare_offline_pid"] = lambda *args: {
            "status": "prepared_proportional_only",
            "integral_frozen": True, "native_output_active": False,
        }
        self.assertTrue(await case.ns["before_tick"](case.runtime, case.spec))
        self.assertEqual(statuses[-1][0], "waiting_for_physical_device")
        self.assertEqual(statuses[-1][1]["startup_remaining_seconds"], 55)
        self.assertTrue(statuses[-1][1]["pid_demand_reserved"])
        self.assertFalse(statuses[-1][1]["native_output_confirmed"])
        self.assertEqual(case.sent, [])
        self.assertTrue(case.runtime._pid_offline_previews[case.spec.identifier]["integral_frozen"])
        case.now = 1060.0
        self.assertTrue(await case.ns["before_tick"](case.runtime, case.spec))
        self.assertEqual(statuses[-1][0], "physical_device_startup_timeout")
        self.assertEqual(case.sent, [])
        self.assertEqual(case.states.values["switch.supply"].state, "on")
        case.states.values["climate.native"].state = "off"
        case.now = 1065.0
        self.assertFalse(await case.ns["before_tick"](case.runtime, case.spec))
        self.assertEqual(case.sent, [])




class SupplyRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        src = runpy.run_path(str(ROOT / ".github/tests/test_beta83_supply_safety.py"))
        case = src["PowerSafetyTests"]()
        case.setUp()
        case.demand = True
        case.now = 1000.0
        relay = case.record["upstream"]
        relay["owned"] = False
        case.states.values["switch.supply"].state = "off"
        relay["pending"] = {
            "desired": "on", "when": 1000.0,
            "identity": dict(relay["identity"]),
            "phase": "commanded", "attempts": 1,
            "last_attempt_at": 1000.0, "cold_start": False,
        }
        # Run the REAL upstream safety decision, with the physical fixture's
        # minimum-OFF already met. The stage-specific mock never grants power
        # when live demand changes or the native climate reports running.
        case.ns["supply_minimum_off"] = lambda *args: True
        case.ns["asyncio"] = asyncio
        case.ns["UPSTREAM_COMMAND_MAX_ATTEMPTS"] = 4
        case.ns["UPSTREAM_COMMAND_RETRY_SECONDS"] = 30
        tree = ast.parse((ROOT / "equipment_power_switch.py").read_text(encoding="utf-8"))
        retry = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                     and n.name == "retry_pending_supply")
        exec(compile(ast.Module(body=[retry], type_ignores=[]),
                     "equipment_power_switch.py", "exec"), case.ns)
        case.runtime._status = lambda spec, status, **kw: self.statuses.append((status, kw))
        self.statuses = []
        self.case = case

    async def test_switch_turn_on_repeats_three_times_before_ack_missing(self):
        c = self.case
        relay = c.record["upstream"]
        c.now = 1029
        self.assertTrue(await c.ns["before_tick"](c.runtime, c.spec))
        self.assertEqual(c.service_calls, [])
        for attempt in (2, 3, 4):
            c.now += 30
            self.assertTrue(await c.ns["before_tick"](c.runtime, c.spec))
            self.assertEqual(relay["pending"]["attempts"], attempt)
            self.assertEqual(len(c.service_calls), attempt - 1)
            self.assertEqual(c.service_calls[-1][:2], ("switch", "turn_on"))
            self.assertNotIn("paused", relay)
        c.now += 30
        self.assertTrue(await c.ns["before_tick"](c.runtime, c.spec))
        self.assertEqual(len(c.service_calls), 3)
        self.assertEqual(relay["paused"], "upstream_switch_ack_missing")
        self.assertEqual(self.statuses[-1][1]["command_retries_completed"], 3)

    async def test_switch_retry_revalidates_live_pid_demand(self):
        c = self.case
        c.demand = False
        c.now += 30
        self.assertTrue(await c.ns["before_tick"](c.runtime, c.spec))
        self.assertEqual(c.service_calls, [])
        self.assertEqual(c.record["upstream"]["pending"]["attempts"], 1)
        self.assertEqual(c.record["upstream"]["paused"],
                         "upstream_retry_policy_or_feedback_changed")

    async def test_active_native_device_blocks_supply_retry(self):
        c = self.case
        c.states.values["climate.native"].state = "heat"
        c.now += 30
        await c.ns["before_tick"](c.runtime, c.spec)
        self.assertEqual(c.service_calls, [])
        self.assertEqual(c.record["upstream"]["paused"],
                         "upstream_retry_policy_or_feedback_changed")

    async def test_switch_turn_on_ack_stops_retries(self):
        c = self.case
        c.states.values["switch.supply"].state = "on"
        c.now += 30
        # Successful ACK intentionally allows native processing to proceed,
        # so before_tick returns False rather than holding the native tick.
        self.assertFalse(await c.ns["before_tick"](c.runtime, c.spec))
        self.assertEqual(c.service_calls, [])
        self.assertIsNone(c.record["upstream"]["pending"])
        self.assertTrue(c.record["upstream"]["owned"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
