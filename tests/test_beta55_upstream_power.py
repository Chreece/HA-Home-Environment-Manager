"""Beta55 upstream outlet behavior: real production AST, no HA services.

The tests call the code that is shipped, with minimal fake HA surfaces.
No real native device or relay may be actuated in these tests.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def extract(*names, injections=None):
    src = ROOT / "equipment_power_switch.py"
    tree = ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name in names]
    if {n.name for n in funcs} != set(names):
        raise AssertionError("Expected production functions were not found")
    module = ast.Module(body=[ast.parse("from __future__ import annotations").body[0],
                              *funcs], type_ignores=[])
    ns = dict(injections or {})
    exec(compile(ast.fix_missing_locations(module), str(src), "exec"), ns)
    return ns


def finite(value, low, high):
    if type(value) not in (int, float):
        return None
    try:
        return float(value) if float("-inf") < value < float("inf") and low <= value <= high else None
    except (ValueError, OverflowError, TypeError):
        return None


class State:
    def __init__(self, value, at=0, domain="switch", attributes=None):
        self.state = value
        self.domain = domain
        self.attributes = attributes or {}
        self.last_changed = datetime.fromtimestamp(at, timezone.utc)


class HassStates:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, name):
        return self.mapping.get(name)


class Harness:
    def __init__(self, switch="on", native="off", *, now=2000, owned=True,
                 demand=False, idle_since=None):
        self.spec = SimpleNamespace(
            identifier="controller1", area_id="bathroom",
            source_device_id="device1", source_entities=("climate.unit",))
        self.cap = SimpleNamespace(primary="climate.unit", modes=("off", "heat"),
                                   domain="climate", temperature=True)
        self.settings = {"power_switch_entity": "switch.supply",
                         "power_switch_cooldown_seconds": 600.,
                         "control_mode": "automatic"}
        self.outlet = State(switch, 0)
        self.native = State(native, 100) if native is not None else None
        self.hass = SimpleNamespace(
            states=HassStates({"switch.supply": self.outlet,
                               "climate.unit": self.native}),
            services=SimpleNamespace(has_service=lambda *args: True),
        )
        self.manager = SimpleNamespace(
            settings={"equipment_controllers": {}}, hass=self.hass)
        self.record = {"area": "bathroom", "sources": ["climate.unit"],
                       "source_device_id": "device1", "power": {},
                       "pending": None, "baseline": {}, "off_at": {},
                       "upstream": {"entity": "switch.supply",
                                    "identity": {"entity": "switch.supply"},
                                    "owned": owned, "pending": None,
                                    "idle_since": idle_since, "off_at": 0}}
        self.clock_value = float(now)
        self.sent = []
        self.statuses = []
        self.saved = 0
        self.demand = demand
        self.runtime = SimpleNamespace(
            manager=self.manager, hass=self.hass, _active=True,
            _ready=True, _started=0, clock=lambda: self.clock_value,
            _record=lambda spec: self.record,
            _current_spec=lambda spec: True,
            _save=self._save, _status=self._status,
        )

    async def _save(self):
        self.saved += 1

    def _status(self, spec, state, **kw):
        self.statuses.append((state, kw))

    async def send(self, runtime, spec, record, identity, desired):
        self.sent.append(desired)
        return True

    def functions(self):
        identity = {"entity": "switch.supply"}
        state = self.outlet
        ns = {
            "model": SimpleNamespace(settings=lambda manager, spec: self.settings),
            "permitted_supply": lambda manager, spec, entity, expected=None: (
                identity if expected in (None, identity) and entity == "switch.supply" else None),
            "verified_capabilities": lambda runtime, spec: self.cap,
            "approved_demand": lambda runtime, spec, cfg, cap: self.demand,
            "_send": self.send,
            "UPSTREAM_MIN_OFF_SECONDS": 600,
            "UPSTREAM_ACK_SECONDS": 120,
            "_SWITCH_STATES": ("off", "on"),
            "observed_output_off": lambda state: state is not None and state.state == "off",
            "finite": finite,
        }
        functions = extract("_observed_off_since", "before_tick", injections=ns)
        return functions["before_tick"]


class SwitchRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_native_never_commands_power_off(self):
        h = Harness(native=None, owned=True, demand=False, idle_since=1000)
        handled = await h.functions()(h.runtime, h.spec)
        self.assertFalse(handled)
        self.assertEqual(h.sent, [])

    async def test_verified_idle_then_cooldown_turns_outlet_off(self):
        h = Harness(native="off", owned=True, demand=False, idle_since=1000)
        self.assertTrue(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, ["off"])

    async def test_idle_timer_begins_without_immediate_cut(self):
        h = Harness(native="off", owned=True, demand=False, idle_since=None)
        self.assertFalse(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.record["upstream"]["idle_since"], 2000.)
        self.assertEqual(h.sent, [])

    async def test_unknown_demand_never_counts_as_idle(self):
        h = Harness(native="off", owned=True, demand=None, idle_since=1000)
        self.assertFalse(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, [])
        self.assertIsNone(h.record["upstream"]["idle_since"])

    async def test_returned_demand_resets_idle_timer(self):
        h = Harness(native="off", owned=True, demand=True, idle_since=1000)
        self.assertFalse(await h.functions()(h.runtime, h.spec))
        self.assertIsNone(h.record["upstream"]["idle_since"])
        self.assertGreater(h.saved, 0)

    async def test_controller_recovers_unavailable_native_by_powering_supply(self):
        h = Harness(switch="off", native=None, owned=False, demand=True)
        self.assertTrue(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, ["on"])

    async def test_never_autostart_during_minimum_off(self):
        h = Harness(switch="off", native=None, owned=False, demand=True, now=2000)
        h.record["upstream"]["off_at"] = 1800
        self.assertTrue(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, [])

    async def test_manual_switch_off_after_ownership_requires_reconciliation(self):
        h = Harness(switch="off", native="off", owned=True, demand=True)
        self.assertTrue(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, [])
        self.assertEqual(h.record["upstream"]["paused"], "upstream_switch_manual_override")

    async def test_pending_turn_on_ack_is_reconciled(self):
        h = Harness(switch="on", native=None, owned=False, demand=True)
        h.record["upstream"]["pending"] = {
            "identity": h.record["upstream"]["identity"],
            "desired": "on", "when": 1900,
        }
        self.assertFalse(await h.functions()(h.runtime, h.spec))
        self.assertTrue(h.record["upstream"]["owned"])
        self.assertIsNone(h.record["upstream"]["pending"])

    async def test_pending_ack_timeout_pauses_instead_of_retrying(self):
        h = Harness(switch="off", native=None, owned=False, demand=True)
        h.record["upstream"]["pending"] = {
            "identity": h.record["upstream"]["identity"],
            "desired": "on", "when": 1800,
        }
        self.assertTrue(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, [])
        self.assertEqual(h.record["upstream"]["paused"], "upstream_switch_ack_missing")

    async def test_native_owned_output_never_loses_supply(self):
        h = Harness(native="off", owned=True, demand=False, idle_since=1000)
        h.record["power"] = {"climate.unit": {"since": 100, "min_on": 600, "max_on": 7200}}
        self.assertFalse(await h.functions()(h.runtime, h.spec))
        self.assertEqual(h.sent, [])


class DemandTests(unittest.TestCase):
    def setUp(self):
        self.required = extract("output_required", injections={"finite": finite})["output_required"]
        self.target = {"heat": 20.0, "cool": 26.0, "humidity": 60.0}
        self.plan = {"air_actions": {"outdoor_air_verified": True,
                                    "thresholds": {"co2_operational_ppm": 900,
                                                   "pm25_short_term_action_ug_m3": 20}}}

    def run_demand(self, cap, readings, method="automatic", mode=None,
                   purpose=None):
        return self.required(
            cap, self.target, readings, method=method,
            requested_mode=mode, fan_purpose=purpose, plan=self.plan,
        )

    def test_heat_demand_and_no_demand(self):
        cap = SimpleNamespace(domain="climate", modes=("off", "heat"), humidifying=False)
        self.assertTrue(self.run_demand(cap, {"temperature": 18}))
        self.assertFalse(self.run_demand(cap, {"temperature": 22}))
        self.assertIsNone(self.run_demand(cap, {"temperature": None}))

    def test_dehumidifier_demand_requires_actual_relative_humidity(self):
        cap = SimpleNamespace(domain="humidifier", modes=("off", "dry"), humidifying=False)
        self.assertTrue(self.run_demand(cap, {"humidity": 67}))
        self.assertIsNone(self.run_demand(cap, {"humidity": "unknown"}))

    def test_fan_requires_qualified_outdoor_air(self):
        cap = SimpleNamespace(domain="fan", modes=("off", "fan_only"))
        self.assertTrue(self.run_demand(cap, {"co2": 1100}, purpose="extraction"))
        self.plan["air_actions"]["outdoor_air_verified"] = False
        self.assertIsNone(self.run_demand(cap, {"co2": 1100}, purpose="extraction"))

    def test_controller_manual_does_not_claim_automatic_demand(self):
        cap = SimpleNamespace(domain="climate", modes=("off", "heat"))
        self.assertIsNone(self.run_demand(cap, {}, method="manual"))
        self.assertTrue(self.run_demand(cap, {}, method="manual", mode="heat"))
        self.assertFalse(self.run_demand(cap, {}, method="off"))


class ModeTranslations(unittest.TestCase):
    def test_greek_away_is_absent_not_combined_home_off(self):
        data = json.loads((ROOT / "translations" / "el.json").read_text())
        selected = data["entity"]["select"]["area_manual_profile"]["state"]
        preset = data["entity"]["climate"]["equipment_climate"]["state_attributes"]["preset_mode"]["state"]
        self.assertEqual(selected["away"], "Απών")
        self.assertEqual(preset["away"], "Απών")
        self.assertEqual(selected["home"], "Σπίτι")
        self.assertEqual(preset["home"], "Σπίτι")
        self.assertEqual(set(selected), {"none", "home", "away", "sleep", "eco", "comfort"})

    def test_unchanged_internal_canonical_automation_keys(self):
        source = (ROOT / "select.py").read_text(encoding="utf-8")
        self.assertIn('PROFILE_OPTIONS = ("auto", "comfort", "home", "away", "sleep", "eco")',
                      source)
        self.assertIn('"none", "home", "comfort", "away", "sleep", "eco"', 
                      (ROOT / "equipment_model.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
