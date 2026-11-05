"""Execute the real demand and upstream dispatch predicates at PID targets.

Only HA state access and unrelated physical interlocks are fixtures. The
actual output_required and _dispatch_safe implementations are extracted from
the production module. No Home Assistant services or real devices are used.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
import os
from pathlib import Path
import runpy
from types import SimpleNamespace as N
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("HEM_TEST_SUPPLY_SOURCE", ROOT / "equipment_power_switch.py"))
FINITE = runpy.run_path(str(ROOT / "pid_math.py"))["finite"]


def production_functions():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    names = {"output_required", "_dispatch_safe"}
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise AssertionError("Production demand/dispatch predicates are missing")
    module = ast.Module(body=[ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0,
    ), *functions], type_ignores=[])
    namespace = {"finite": FINITE, "Any": Any, "Mapping": Mapping}
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


def capability(*modes, domain="climate", humidifying=False):
    return N(primary=f"{domain}.appliance", domain=domain,
             modes=("off", *modes), humidifying=humidifying)


class PidSupplyCutoffTests(unittest.TestCase):
    def setUp(self):
        self.ns = production_functions()
        self.required = self.ns["output_required"]

    def demand(self, cap, measured, *, direction=None, method="pid", targets=None):
        return self.required(
            cap, targets if targets is not None else {
                "heat": 21., "cool": 22., "humidity": 60.,
            }, measured, method=method, requested_mode=direction,
            fan_purpose=None, plan={},
        )

    def test_heating_and_cooling_end_at_target_in_every_native_actuator_domain(self):
        for domain in ("climate", "switch", "input_boolean", "number", "input_number"):
            for direction, pairs in (
                ("heat", ((20.999, True), (21., False), (22.1, False), (40., False))),
                ("cool", ((22.001, True), (22., False), (20.9, False), (5., False))),
            ):
                for explicit in (None, direction):
                    for value, expected in pairs:
                        with self.subTest(domain=domain, direction=direction,
                                          requested=explicit, value=value):
                            cap = capability(direction, domain=domain)
                            self.assertIs(self.demand(cap, {"temperature": value},
                                                      direction=explicit), expected)

    def test_selected_direction_does_not_need_an_opposite_target(self):
        cap = capability("heat", "cool")
        for bad_opposite in (None, "unknown", float("nan"), True, -500.):
            for direction, selected, actual, expected in (
                ("heat", 21., 20.9, True), ("heat", 21., 21., False),
                ("heat", 21., 30., False), ("cool", 22., 22.1, True),
                ("cool", 22., 22., False), ("cool", 22., 10., False),
            ):
                targets = {direction: selected,
                           "cool" if direction == "heat" else "heat": bad_opposite}
                with self.subTest(direction=direction, actual=actual,
                                  opposite=bad_opposite):
                    self.assertIs(self.demand(cap, {"temperature": actual},
                                              direction=direction, targets=targets), expected)

    def test_humidity_uses_the_correct_side_with_no_pid_hysteresis(self):
        devices = (
            (capability("auto", domain="humidifier", humidifying=True), "auto", True),
            (capability("dry", domain="humidifier"), "dry", False),
            (capability("dry"), "dry", False),
            (capability("heat", "cool", "dry"), "dry", False),
            (capability("dry", "fan_only"), None, False),
        )
        for cap, direction, increasing in devices:
            for value in (59.999, 60., 60.001):
                expected = value < 60. if increasing else value > 60.
                with self.subTest(domain=cap.domain, modes=cap.modes,
                                  increasing=increasing, value=value):
                    self.assertIs(self.demand(cap, {"humidity": value},
                                              direction=direction), expected)

    def test_dual_direction_supply_is_idle_inside_the_actual_comfort_band(self):
        for cap, requested in ((capability("heat", "cool"), None),
                               (capability("heat_cool"), "heat_cool"),
                               (capability("auto"), "auto")):
            for value, expected in ((20.999, True), (21., False), (21.5, False),
                                    (22., False), (22.001, True)):
                with self.subTest(modes=cap.modes, requested=requested, value=value):
                    self.assertIs(self.demand(cap, {"temperature": value},
                                              direction=requested), expected)
        for goals in ({"heat": 21.}, {"cool": 22.}, {"heat": 23., "cool": 22.}):
            self.assertIsNone(self.demand(capability("heat", "cool"),
                                         {"temperature": 21.5}, targets=goals))

    def test_invalid_or_missing_directional_evidence_never_becomes_idle_proof(self):
        for direction, metric, cap in (
            ("heat", "temperature", capability("heat")),
            ("cool", "temperature", capability("cool")),
            ("dry", "humidity", capability("dry")),
            ("auto", "humidity", capability("auto", domain="humidifier", humidifying=True)),
        ):
            for value in (None, "unknown", "unavailable", float("nan"), float("inf"), True, -500.):
                with self.subTest(direction=direction, invalid=value):
                    self.assertIsNone(self.demand(cap, {metric: value}, direction=direction))
            key = "humidity" if metric == "humidity" else direction
            self.assertIsNone(self.demand(cap, {metric: 25.}, direction=direction,
                                         targets={key: "unknown"}))
        self.assertIsNone(self.demand(capability("heat"), {"temperature": 20.},
                                     direction="cool"))

    def test_manual_and_automatic_policies_keep_their_existing_semantics(self):
        cap = capability("heat", "cool")
        self.assertIs(self.demand(cap, {"temperature": 40.}, direction="heat", method="manual"), True)
        self.assertIs(self.demand(cap, {}, direction="off", method="manual"), False)
        self.assertIs(self.demand(cap, {}, method="off"), False)
        self.assertIsNone(self.demand(cap, {}, method="existing"))
        # Automatic mode retains its configured target-band hysteresis.
        self.assertIsNone(self.demand(cap, {"temperature": 21.1}, direction="heat", method="automatic"))
        self.assertIs(self.demand(cap, {"temperature": 20.}, direction="heat", method="automatic"), True)
        self.assertIs(self.demand(cap, {"temperature": 21.5}, direction="heat", method="automatic"), False)
        dry = capability("dry")
        self.assertIsNone(self.demand(dry, {"humidity": 60.1}, direction="dry", method="automatic"))
        self.assertIs(self.demand(dry, {"humidity": 63.}, direction="dry", method="automatic"), True)
        self.assertIs(self.demand(dry, {"humidity": 57.}, direction="dry", method="automatic"), False)

    def test_upstream_dispatch_rechecks_target_without_bypassing_off_interlocks(self):
        cap = capability("heat")
        source = cap.primary
        switch = "switch.supply"
        record = {"upstream": {"owned": False}, "power": {}, "pending": None}
        states = {source: N(state="off"), switch: N(state="off")}
        runtime = N(
            manager=N(), _started=0., _current_spec=lambda spec: True,
            clock=lambda: 1000., hass=N(states=N(get=states.get)), measured=20.,
        )
        gate = self.ns["_dispatch_safe"]
        self.ns.update(
            verified_capabilities=lambda *args: cap,
            supply_minimum_off=lambda *args: True,
            supply_minimum_on=lambda *args: True,
            idle_cooldown_ready=lambda *args: True,
            observed_output_off=lambda state: state.state == "off",
            native_outputs_idle=lambda *args: True,
            approved_demand=lambda *args: self.demand(
                cap, {"temperature": runtime.measured}, direction="heat"),
        )
        spec = N()
        self.assertTrue(gate(runtime, spec, record, {}, switch, "on"))
        runtime.measured = 21.  # Sensor changed while queued/persisting an ON.
        self.assertFalse(gate(runtime, spec, record, {}, switch, "on"))
        runtime.measured = 22.5  # Beyond the unrelated cooling target, too.
        self.assertFalse(gate(runtime, spec, record, {}, switch, "on"))
        states[switch].state = "on"
        self.assertFalse(gate(runtime, spec, record, {}, switch, "off"), "No power ownership")
        record["upstream"]["owned"] = True
        self.assertTrue(gate(runtime, spec, record, {}, switch, "off"))
        record["power"][source] = {"since": 100.}
        self.assertFalse(gate(runtime, spec, record, {}, switch, "off"), "Native output still owned")
        record["power"].clear()
        self.ns["native_outputs_idle"] = lambda *args: False
        self.assertFalse(gate(runtime, spec, record, {}, switch, "off"), "No physical idle proof")


if __name__ == "__main__":
    unittest.main(verbosity=2)
