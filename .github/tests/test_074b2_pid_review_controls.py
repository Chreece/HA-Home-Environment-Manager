"""Real review-button lifecycle, backed by the production pure review helper.

Only the HA entity base/registry and the final runtime authorization decision
are fixtures. The button class and proposal lifecycle are executed unchanged;
the runtime guard itself has separate production-path integration coverage.
No HA service, storage write, or physical device is available in this test.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import MethodType, ModuleType, SimpleNamespace as NS
from typing import Any
import unittest


SOURCE = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
PACKAGE = "hem_074b2_review_controls"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", SOURCE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("pid_calibration")
passive = load("pid_passive")
review_helper = load("pid_review")
model = ModuleType(f"{PACKAGE}.equipment_model")
model.mode_control_modes = lambda manager, spec, mode: ("pid",) if mode in ("heat", "cool") else ()
sys.modules[model.__name__] = model


class EntityBase:
    def _equipment_init(self, manager, spec, key, *, operating_mode=None):
        self._manager, self._spec, self._key = manager, spec, key
        self._operating_mode = operating_mode

    @property
    def controller_settings(self):
        return self._manager.cfg

    @property
    def extra_state_attributes(self):
        return {"controller_id": self._spec.identifier}


tree = ast.parse((SOURCE / "button.py").read_text())
button_class = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == "EquipmentPIDReviewButton")
namespace = {"__name__": f"{PACKAGE}.button", "__package__": PACKAGE,
             "EquipmentEntity": EntityBase, "ButtonEntity": type("ButtonEntity", (), {}),
             "EntityCategory": NS(CONFIG="config")}
exec(compile(ast.Module(body=[button_class], type_ignores=[]), "production review button", "exec"), namespace)
ReviewButton = namespace["EquipmentPIDReviewButton"]


class ReviewControlsTests(unittest.TestCase):
    NOW = 2_000_000.

    def setUp(self):
        self.now = self.NOW
        self.cfg = {
            "control_mode": "pid", "operating_mode": "heat", "requested_mode": "heat",
            "pid_calibration_method": "adaptive_suggest", "kp": 10., "ki": .1, "kd": 0.,
            "sample_seconds": 300., "cycle_seconds": 3600., "min_on_seconds": 600.,
            "min_off_seconds": 600., "max_on_seconds": 7200., "power_switch_entity": None,
            "power_switch_cooldown_seconds": 300.,
        }
        context = passive.identity("room", ["climate.unit"], "climate.unit", "heat",
                                   "temperature", "sensor.room", "home", 21., None, None)
        summary = {"status": "suggestion_only", "confidence": "medium", "valid_cycles": 3,
                   "last_cycle_at": self.now - 300., "suggested_gains": {"kp": 20., "ki": .2, "kd": 0.}}
        self.proposal = review_helper.proposal_for(self.cfg, summary, context, self.now - 100.)
        self.proposal["operating_mode"] = "heat"
        self.record = {"pid_passive": {"context": context, "summary": summary, "cycles": []},
                       "pid_passive_review": self.proposal}
        self.spec = NS(identifier="controller")
        self.guard_calls = []
        self.guard_preview_flags = []
        self.authorized = True
        self.runtime = NS(
            _active=True, _ready=True, records={self.spec.identifier: self.record},
            clock=lambda: self.now, context=context,
        )
        self.runtime._pid_learning_context = lambda spec, **kwargs: self.runtime.context

        def authorize(spec, changes, token, *, read_only=False):
            self.guard_calls.append((spec.identifier, deepcopy(changes), token))
            self.guard_preview_flags.append(read_only)
            return self.authorized

        self.runtime._pid_review_authorized = authorize
        self.manager = NS(cfg=self.cfg, equipment=self.runtime)
        self.approve = ReviewButton(self.manager, self.spec, "approve", operating_mode="heat")
        self.discard = ReviewButton(self.manager, self.spec, "discard", operating_mode="heat")

    def test_valid_approve_uses_exact_runtime_guard_payload(self):
        self.assertTrue(self.approve.available)
        self.assertEqual(len(self.guard_calls), 1)
        self.assertEqual(self.guard_preview_flags, [True])
        identifier, changes, token = self.guard_calls[0]
        self.assertEqual((identifier, token), (self.spec.identifier, self.proposal["id"]))
        self.assertEqual({key: changes[key] for key in ("kp", "ki", "kd")}, self.proposal["apply"])
        evidence = changes["pid_last_calibration"]
        self.assertEqual(evidence["proposal_id"], self.proposal["id"])
        self.assertEqual(evidence["previous_gains"], self.proposal["current"])
        self.assertEqual(evidence["applied_gains"], self.proposal["apply"])
        self.assertEqual(evidence["operating_mode"], "heat")
        self.assertTrue(self.discard.available)
        self.assertEqual(len(self.guard_calls), 1, "Discard never requests gain-application authority")
        self.assertTrue(self.approve.extra_state_attributes["pending"])

    def test_expiry_is_inclusive_and_stale_pending_remains_discardable(self):
        self.proposal["created_at"] = self.now - review_helper.REVIEW_MAX_AGE_S
        self.assertTrue(self.approve.available)
        self.now += .001
        self.guard_calls.clear()
        before = deepcopy(self.record)
        self.assertFalse(self.approve.available)
        self.assertTrue(self.discard.available)
        attributes = self.approve.extra_state_attributes
        self.assertEqual(attributes["review_state"], "expired")
        self.assertEqual(attributes["review_reason"], "recommendation_expired")
        self.assertFalse(attributes["pending"])
        self.assertIsNone(attributes["next_gains"])
        self.assertEqual(self.guard_calls, [])
        self.assertEqual(self.record, before)

    def test_timing_gain_and_context_changes_block_approve_before_guard(self):
        cases = (
            lambda: self.cfg.update(sample_seconds=600.),
            lambda: self.cfg.update(kp=12.),
            lambda: setattr(self.runtime, "context", "changed physical context"),
            lambda: self.record["pid_passive"]["summary"].update(last_cycle_at=self.now),
        )
        for mutate in cases:
            self.setUp()
            mutate()
            with self.subTest(reason=self.approve.extra_state_attributes.get("review_reason")):
                self.assertFalse(self.approve.available)
                self.assertTrue(self.discard.available)
                self.assertEqual(self.guard_calls, [])

    def test_persisted_expired_review_can_be_dismissed_but_discarded_cannot_replay(self):
        self.proposal.update(state="expired", reason="recommendation_expired")
        self.assertFalse(self.approve.available)
        self.assertTrue(self.discard.available)
        self.proposal["state"] = "discarded"
        self.assertFalse(self.approve.available)
        self.assertFalse(self.discard.available)
        self.assertEqual(self.approve.extra_state_attributes["review_reason"], "recommendation_discarded")

    def test_committed_application_consumes_stale_pending_actions_without_mutation(self):
        self.cfg.update(self.proposal["apply"])
        self.cfg["pid_last_calibration"] = {
            "method": "passive_approved_imc_lambda", "proposal_id": self.proposal["id"],
            "cycle_at": self.proposal["cycle_at"], "operating_mode": "heat",
            "previous_gains": deepcopy(self.proposal["current"]),
            "applied_gains": deepcopy(self.proposal["apply"]),
        }
        before = deepcopy((self.record, self.cfg))
        self.assertFalse(self.approve.available)
        self.assertFalse(self.discard.available)
        self.assertEqual(self.approve.extra_state_attributes["review_state"], "applied")
        self.assertEqual(self.guard_calls, [])
        self.assertEqual((self.record, self.cfg), before)

    def test_missing_current_context_or_runtime_guard_fails_closed(self):
        self.runtime.context = None
        self.assertFalse(self.approve.available)
        self.assertTrue(self.discard.available)
        self.assertEqual(self.guard_calls, [])
        self.runtime.context = self.proposal["context"]
        self.runtime._pid_review_authorized = None
        self.assertFalse(self.approve.available)

    def test_physical_or_recovery_hold_from_guard_disables_only_approval(self):
        self.authorized = False
        self.assertFalse(self.approve.available)
        self.assertTrue(self.discard.available)
        self.assertEqual(len(self.guard_calls), 1)

    def test_inactive_or_other_mode_and_malformed_tokens_never_enable_approve(self):
        other = ReviewButton(self.manager, self.spec, "approve", operating_mode="cool")
        self.assertFalse(other.available)
        self.proposal["id"] = "not-an-authorized-token"
        self.assertFalse(self.approve.available)
        self.assertFalse(self.discard.available)
        self.runtime._active = False
        self.assertFalse(self.approve.available)
        self.assertFalse(self.discard.available)
        self.assertEqual(self.guard_calls, [])


class PreviewPurityTests(unittest.TestCase):
    """Real button -> guard -> gate -> window/airing policy, with no writes."""

    NOW = ReviewControlsTests.NOW

    def setUp(self):
        ReviewControlsTests.setUp(self)
        runtime = self.runtime
        self.spec.area_id, self.spec.source_entities = "room", ("climate.unit",)
        self.spec.source_device_id = "physical"
        self.cap = NS(primary="climate.unit", domain="climate", humidifying=False,
                      modes=("off", "heat"))
        self.native = NS(state="off", domain="climate", entity_id="climate.unit",
                         attributes={"hvac_action": "off", "fan_mode": None, "percentage": None})
        self.window = NS(state="off", domain="binary_sensor", entity_id="binary_sensor.window",
                         attributes={"device_class": "window"},
                         last_changed=datetime.fromtimestamp(self.now - 120, timezone.utc))
        states = {"climate.unit": self.native, "binary_sensor.window": self.window}
        self.effects = []
        runtime.manager, runtime.hass = self.manager, NS(states=NS(get=states.get))
        runtime._started = self.now - 600
        runtime._current_spec = lambda spec: True
        runtime._record = lambda spec: self.record
        runtime.measurements = lambda *args: {
            "temperature": 20., "temperature_selected_entities": ["sensor.room"]}
        runtime._window_policy_cache = {}
        self.manager.entry = NS(entry_id="entry")
        self.manager.hass = runtime.hass
        self.manager.plan = NS(environment={"room": {
            "room_presence": {"home": "home", "sleeping": False},
            "climate_plan": {"away": "home", "sleeping": False}}})
        self.manager.settings = {"automatic_notifications": True}
        self.cfg.update(pause_on_window_open=True, announce_before_start=False)
        model.ManagedDevice = model.Capabilities = object
        model.settings = lambda *args: self.cfg
        model.capabilities = lambda *args: self.cap
        model.plan_for = lambda *args: self.manager.plan.environment["room"]["climate_plan"]
        model.targets = lambda *args: {"heat": 21.}
        model.profile_name = lambda *args: "home"
        model.permission = lambda *args: (True, True)
        model.room_config = lambda *args: {}
        for name, values in {
            "discovery": {"entity_area": lambda *args: "room",
                          "is_window_contact": lambda *args, **kwargs: True,
                          "is_window": lambda *args: True},
            "room_sources": {"selected": lambda *args: ["binary_sensor.window"]},
            "device_activation": {"effective_device": lambda *args, **kwargs: {"auto_control": True}},
        }.items():
            module = ModuleType(f"{PACKAGE}.{name}")
            module.__dict__.update(values)
            sys.modules[module.__name__] = module
        self.window_policy = load("equipment_window")
        self.wait_module = load("window_open_wait")
        finite = lambda value, lo, hi: (float(value) if type(value) in (int, float)
                                       and lo <= value <= hi else None)
        power = ModuleType(f"{PACKAGE}.equipment_power_switch")
        power.__dict__.update(Any=Any, Mapping=Mapping, finite=finite,
                              _IDLE_HVAC_ACTIONS=frozenset(("off", "idle")))
        power_tree = ast.parse((SOURCE / "equipment_power_switch.py").read_text())
        off = next(node for node in power_tree.body if isinstance(node, ast.FunctionDef)
                   and node.name == "observed_output_off")
        exec(compile(ast.Module(body=[off], type_ignores=[]), "production native OFF", "exec"), power.__dict__)
        sys.modules[power.__name__] = power
        tree = ast.parse((SOURCE / "equipment_runtime.py").read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "EquipmentRuntime")
        names = ("_pid_review_authorized", "_gate", "_window_policy")
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in ("snapshot", "output_off")]
        namespace = {"__name__": f"{PACKAGE}.runtime", "__package__": PACKAGE,
                     "Any": Any, "model": model, "STARTUP_SECONDS": 300, "finite": finite,
                     "passive_identity": passive.identity, "MONITORED": ("hvac_action",),
                     "foreign_owner_hold": lambda *args: None,
                     "_physical_climate_conflict": lambda *args: None,
                     "live_device_permission": lambda *args: ("eligible", "eligible")}
        exec(compile(ast.Module(body=[*functions, *methods], type_ignores=[]),
                     "production review guard and gate", "exec"), namespace)
        for name in names:
            setattr(runtime, name, MethodType(namespace[name], runtime))

    def changes(self):
        return {**self.proposal["apply"], "pid_last_calibration": {
            "method": "passive_approved_imc_lambda", "proposal_id": self.proposal["id"],
            "cycle_at": self.proposal["cycle_at"], "previous_gains": self.proposal["current"],
            "applied_gains": self.proposal["apply"], "operating_mode": "heat"}}

    def airing(self, timeout=60):
        self.cfg.update(announce_before_start=True, window_open_timeout_minutes=timeout / 60)

        def schedule(seconds, callback):
            self.effects.append(("scheduled", seconds))
            return lambda: self.effects.append("cancelled replacement")

        waiter = self.wait_module.WindowOpeningWait(self.manager, clock=lambda: self.now,
                                                   schedule=schedule)
        target = self.wait_module._Demand("climate.unit", self.spec.identifier, "Heater",
                                         "heat", True, True, True, True, 300, {})
        episode = self.wait_module._Episode(
            "open", "heat", ("binary_sensor.window",), target, "window_open_wait",
            self.now - 10, self.now + 290, 300,
            cancel=lambda: self.effects.append("cancelled original"),
        )
        waiter._rooms = {"room": {"climate.unit": episode}}
        # Qualified current room demand is the fixture boundary. The entire
        # production episode/hold/status and timer-management path runs.
        waiter._demands = lambda *args: {"climate.unit": replace(target, timeout_seconds=timeout)}
        self.manager.window_open_wait = waiter
        return waiter, episode

    def test_button_preview_never_establishes_or_changes_window_cache(self):
        for opened in (True, False):
            with self.subTest(opened=opened):
                self.window.state = "on" if opened else "off"
                self.runtime._window_policy_cache = {}
                before = deepcopy((self.record, self.cfg, self.runtime._window_policy_cache))
                self.assertEqual(self.approve.available, not opened)
                self.assertEqual((self.record, self.cfg, self.runtime._window_policy_cache), before)
                self.assertEqual(self.effects, [])
        # Preview also does not create a missing cache attribute.
        del self.runtime._window_policy_cache
        self.assertTrue(self.approve.available)
        self.assertFalse(hasattr(self.runtime, "_window_policy_cache"))
        # Execution retains its original evidence-update behavior.
        self.assertTrue(self.runtime._pid_review_authorized(self.spec, self.changes(), self.proposal["id"]))
        self.assertEqual(self.runtime._window_policy_cache[self.spec.identifier]["status"], "window_closed_ready")

    def test_live_window_warmup_preview_is_conservative_and_read_only(self):
        self.window.state = "on"
        self.runtime._window_policy(self.spec, self.cfg)
        self.window.state = "off"
        self.window.last_changed = datetime.fromtimestamp(self.now, timezone.utc)
        before = deepcopy(self.runtime._window_policy_cache)
        self.assertFalse(self.approve.available)
        self.assertEqual(self.runtime._window_policy_cache, before)
        info = self.runtime._window_policy(self.spec, self.cfg, read_only=True)
        self.assertEqual(info["status"], "window_close_warmup")
        self.assertEqual(info["remaining_seconds"], 60.)
        self.assertEqual(self.runtime._window_policy_cache, before)

    def test_airing_preview_uses_shorter_timeout_without_mutating_episode_or_timer(self):
        waiter, episode = self.airing(timeout=60)
        before = deepcopy((self.record, self.runtime._window_policy_cache, episode))
        for _ in range(3):
            self.assertFalse(self.approve.available)
        projected = self.wait_module.managed_start_hold(
            self.runtime, self.spec, self.cap, self.cfg, "heat", read_only=True)
        self.assertEqual(projected["remaining_seconds"], 50)
        self.assertEqual(projected["timeout_seconds"], 60)
        self.assertEqual(projected["device_waits"][0]["remaining_seconds"], 50)
        self.assertEqual((self.record, self.runtime._window_policy_cache, episode), before)
        self.assertEqual(self.effects, [])
        # The normal execution guard still updates the shorter live consent.
        self.assertFalse(self.runtime._pid_review_authorized(self.spec, self.changes(), self.proposal["id"]))
        self.assertEqual(episode.timeout_seconds, 60)
        self.assertEqual(episode.until, episode.since + 60)
        self.assertEqual(self.effects, ["cancelled original", ("scheduled", 50)])

    def test_elapsed_shorter_airing_preview_does_not_finish_or_cancel_episode(self):
        _, episode = self.airing(timeout=60)
        self.now += 60
        before = deepcopy(episode)
        self.assertTrue(self.approve.available)
        self.assertEqual(episode, before)
        self.assertEqual(self.effects, [])
        self.assertTrue(self.runtime._pid_review_authorized(self.spec, self.changes(), self.proposal["id"]))
        self.assertEqual(episode.phase, "window_open_timeout")
        self.assertEqual(self.effects, ["cancelled original"])

    def test_gate_preview_does_not_allocate_record_or_consume_door_budget(self):
        self.cfg.update(pause_on_window_open=False)
        self.native.state = "heat"
        self.native.attributes["hvac_action"] = "heating"
        self.runtime._door_start_budget = NS(records={self.spec.identifier: {"since": self.now}})
        before = deepcopy((self.runtime.records, self.runtime._door_start_budget.records))

        def forbidden_record(spec):
            raise AssertionError("Read-only gate must not allocate a record")

        self.runtime._record = forbidden_record
        self.runtime._gate(self.spec, self.cap, self.cfg, model.plan_for(self.manager, self.spec),
                           "heat", read_only=True)
        self.assertEqual((self.runtime.records, self.runtime._door_start_budget.records), before)
        self.assertEqual(self.effects, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
