"""Regression checks for HEM's upstream-relay OFF interlocks.

Run: python3 -m unittest discover -s tests -p 'test_supply_safety.py' -v
No Home Assistant installation or physical service calls are needed. These
tests extract the *real* helper/tick functions from equipment_power_switch.py.
"""
from __future__ import annotations

import ast
import asyncio
from collections.abc import Mapping
import math
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "equipment_power_switch.py"
NAMES = {
    "observed_output_off", "native_outputs_idle", "idle_cooldown_ready",
    "_dispatch_safe", "_send", "before_tick",
}


def finite(value, low, high):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and low <= number <= high else None


def functions_under_test():
    source = SOURCE.read_text(encoding="utf-8")
    parsed = ast.parse(source, filename=str(SOURCE))
    functions = [
        n for n in parsed.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in NAMES
    ]
    if {n.name for n in functions} != NAMES:
        raise AssertionError("Safety functions are missing or renamed")
    module = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            *functions,
        ],
        type_ignores=[],
    )
    namespace = {
        "Mapping": Mapping,
        "finite": finite,
        "_SWITCH_STATES": ("off", "on"),
        "_IDLE_HVAC_ACTIONS": frozenset(("off", "idle")),
        "MIN_UPSTREAM_IDLE_SECONDS": 60.0,
    }
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


class State:
    def __init__(self, domain, state, action=None):
        self.domain = domain
        self.state = state
        self.attributes = {} if action is None else {"hvac_action": action}


class States:
    def __init__(self, states):
        self.values = states

    def get(self, entity):
        return self.values.get(entity)


class PowerSafetyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        ns = functions_under_test()
        self.ns = ns
        self.spec = SimpleNamespace(
            identifier="managed-1", area_id="bathroom",
            source_entities=("climate.native", "fan.aux"),
        )
        self.cap = SimpleNamespace(primary="climate.native")
        self.cfg = {
            "power_switch_entity": "switch.supply",
            "power_switch_cooldown_seconds": 60,
            "pause_on_window_open": False,
        }
        self.states = States({
            "switch.supply": State("switch", "on"),
            "climate.native": State("climate", "off", "off"),
            "fan.aux": State("fan", "off"),
        })
        self.record = {
            "upstream": {
                "entity": "switch.supply", "identity": {"entity": "switch.supply"},
                "owned": True, "idle_since": None, "on_at": 500,
            },
            "power": {}, "pending": None,
        }
        self.sent = []
        self.saves = 0
        self.service_calls = []

        async def service_call(domain, action, data, **kwargs):
            self.service_calls.append((domain, action, data, kwargs))
        self.runtime = SimpleNamespace(
            manager=SimpleNamespace(settings=self.cfg),
            hass=SimpleNamespace(
                states=self.states,
                services=SimpleNamespace(
                    has_service=lambda domain, service: True,
                    async_call=service_call,
                ),
            ),
            _active=True, _ready=True, _started=500,
            _commands=asyncio.Lock(),
            _pid_offline_previews={},
            _current_spec=lambda spec: True,
            clock=lambda: self.now,
            _record=lambda spec: self.record,
            _status=lambda *a, **kw: None,
        )
        self.now = 1000.0

        async def save():
            self.saves += 1

        async def observe(*args):
            return None

        async def send(*args, **kwargs):
            self.sent.append(args[-1])
            return True

        self.runtime._save = save
        self.real_send = ns["_send"]
        ns.update({
            "model": SimpleNamespace(settings=lambda manager, spec: manager.settings),
            "permitted_supply": lambda *args: self.record["upstream"]["identity"],
            "verified_capabilities": lambda *args: self.cap,
            "observe_supply_state": observe,
            "approved_demand": lambda *args: self.demand,
            "supply_minimum_on": lambda *args: True,
            "device_supply_dwell": lambda *args: (120, 600),
            "_send": send,
        })
        self.demand = False

    def test_native_mode_off_with_active_hvac_action_is_not_idle(self):
        off = self.ns["observed_output_off"]
        for action in ("heating", "cooling", "drying", "fan", "defrosting",
                       "preheating", "unknown", "unavailable", "starting"):
            with self.subTest(action=action):
                self.assertFalse(off(State("climate", "off", action)))
        for action in (None, "idle", "off"):
            with self.subTest(safe_action=action):
                self.assertTrue(off(State("climate", "off", action)))
        self.assertFalse(off(State("climate", "dry", "idle")))
        self.assertFalse(off(State("climate", "unavailable")))
        self.assertTrue(off(State("number", "0")))
        self.assertFalse(off(State("number", "0", "drying")))
        self.assertFalse(off(State("number", "1")))

    def test_all_native_endpoints_must_be_idle(self):
        check = self.ns["native_outputs_idle"]
        self.assertTrue(check(self.runtime, self.spec, self.cap))
        self.states.values["fan.aux"] = State("fan", "on")
        self.assertFalse(check(self.runtime, self.spec, self.cap))
        self.states.values["fan.aux"] = State("fan", "unavailable")
        self.assertFalse(check(self.runtime, self.spec, self.cap))

    def test_cooldown_never_shorter_than_one_minute(self):
        check = self.ns["idle_cooldown_ready"]
        relay = {"idle_since": 940}
        self.assertFalse(check(self.cfg, relay, 999, 500))
        self.assertTrue(check(self.cfg, relay, 1000, 500))
        self.cfg["power_switch_cooldown_seconds"] = 600
        self.assertFalse(check(self.cfg, relay, 1000, 500))
        self.assertTrue(check(self.cfg, relay, 1540, 500))
        self.cfg["power_switch_cooldown_seconds"] = 0
        self.assertFalse(check(self.cfg, relay, 99999, 500))
        self.cfg["power_switch_cooldown_seconds"] = 60
        self.assertFalse(check(self.cfg, relay, 1000, 950))
        self.assertTrue(check(self.cfg, relay, 1010, 950))

    def test_tick_starts_cooldown_on_verified_native_stop(self):
        tick = self.ns["before_tick"]
        # No switch command during the first verified idle minute.
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertEqual(self.record["upstream"]["idle_since"], 1000)
        self.assertEqual(self.sent, [])
        self.now = 1059.9
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertEqual(self.sent, [])
        self.now = 1060
        self.assertTrue(await tick(self.runtime, self.spec))
        self.assertEqual(self.sent, ["off"])

    def test_working_device_resets_cooldown_and_blocks_switch(self):
        tick = self.ns["before_tick"]
        await tick(self.runtime, self.spec)
        self.now = 1020
        self.states.values["climate.native"] = State("climate", "off", "drying")
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertIsNone(self.record["upstream"]["idle_since"])
        self.now = 1050
        self.states.values["climate.native"] = State("climate", "off", "idle")
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertEqual(self.record["upstream"]["idle_since"], 1050)
        self.now = 1109
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertEqual(self.sent, [])
        self.now = 1110
        self.assertTrue(await tick(self.runtime, self.spec))
        self.assertEqual(self.sent, ["off"])

    def test_unknown_state_and_supply_outage_clear_idle_timer(self):
        tick = self.ns["before_tick"]
        await tick(self.runtime, self.spec)
        self.now += 30
        self.states.values["fan.aux"] = State("fan", "unavailable")
        self.assertFalse(await tick(self.runtime, self.spec))
        self.assertIsNone(self.record["upstream"]["idle_since"])
        self.states.values["fan.aux"] = State("fan", "off")
        self.now += 30
        await tick(self.runtime, self.spec)
        self.assertEqual(self.record["upstream"]["idle_since"], self.now)
        self.states.values["switch.supply"] = State("switch", "unavailable")
        self.now += 30
        self.assertTrue(await tick(self.runtime, self.spec))
        self.assertIsNone(self.record["upstream"]["idle_since"])
        self.assertEqual(self.sent, [])

    async def test_hardware_off_command_revalidates_after_store_yield(self):
        send = self.real_send
        relay = self.record["upstream"]
        relay["idle_since"] = 900
        # Physical state changes while the HEM intent is being persisted.
        original_save = self.runtime._save
        saves = 0

        async def state_change_during_save():
            nonlocal saves
            saves += 1
            await original_save()
            if saves == 1:
                self.states.values["climate.native"] = State(
                    "climate", "off", "drying"
                )

        self.runtime._save = state_change_during_save
        sent = await send(
            self.runtime, self.spec, self.record, relay["identity"], "off"
        )
        self.assertFalse(sent)
        self.assertEqual(self.service_calls, [])
        self.assertIsNone(relay.get("pending"))

    def test_final_dispatch_cannot_cut_power_after_state_changes(self):
        check = self.ns["_dispatch_safe"]
        relay = self.record["upstream"]
        relay["idle_since"] = 900
        self.assertTrue(check(self.runtime, self.spec, self.record,
                              self.cfg, "switch.supply", "off"))
        for action in ("heating", "cooling", "drying", "defrosting"):
            self.states.values["climate.native"] = State("climate", "off", action)
            self.assertFalse(check(self.runtime, self.spec, self.record,
                                   self.cfg, "switch.supply", "off"))
        self.states.values["climate.native"] = State("climate", "off", "idle")
        self.record["pending"] = {"desired": "off"}
        self.assertFalse(check(self.runtime, self.spec, self.record,
                               self.cfg, "switch.supply", "off"))
        self.record["pending"] = None
        self.runtime._started = 980
        self.assertFalse(check(self.runtime, self.spec, self.record,
                               self.cfg, "switch.supply", "off"))
        self.runtime._started = 500
        self.demand = True
        self.assertFalse(check(self.runtime, self.spec, self.record,
                               self.cfg, "switch.supply", "off"))


if __name__ == "__main__":
    unittest.main()
