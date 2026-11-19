"""Full production PID review, settings, restart and notification lifecycle.

Extend the existing native runtime fixture. Guards, scoped settings writer,
context store, observer, review execution, startup, maintenance and notification
delivery are production code. Only HA state/notification transport, qualified
room inputs, clock and JSON Store transport are isolated. No hardware is used.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / ".github/tests/test_074_pid_adaptation_scope.py"))
model, production, SPEC, PRIMARY, passive, review = (
    fixture[key] for key in ("model", "production", "SPEC", "PRIMARY", "passive", "review")
)
PACKAGE = fixture["fixture"]["PACKAGE"]
SPEC.name = "Fixture heating controller"
store = importlib.import_module(PACKAGE + ".pid_learning_store")
production.PassiveObserver = passive.PassiveObserver
METHODS = (
    "_record", "_save", "async_start", "_pid_learning_context",
    "_pid_review_maintenance", "_schedule_pid_review_notice", "_deliver_pid_review_notice",
    "_pid_passive_observe", "_interrupt_pid_learning", "_pid_learning_observed",
)
fixture["fixture"]["base"]["extract"](
    ROOT / "custom_components/environment_manager/equipment_runtime.py",
    METHODS, production.__dict__,
)


class MemoryStore:
    """JSON roundtrip transport; the actual runtime _save() owns persistence."""
    def __init__(self, owner, payload=None):
        self.owner = owner
        self.payload = deepcopy(payload) if payload is not None else {
            "version": 1, "records": deepcopy(owner.records),
        }

    async def async_load(self):
        return json.loads(json.dumps(self.payload, allow_nan=False))

    async def async_save(self, payload):
        self.payload = json.loads(json.dumps(payload, allow_nan=False))
        self.owner.persisted.append(deepcopy(self.payload["records"][SPEC.identifier]))


class LifecycleRuntime(fixture["AdaptiveRuntime"]):
    def __init__(self, *, method="adaptive_suggest", supply=False):
        profile = fixture["profile"](method=method)
        if supply:
            profile["power_switch_entity"] = "switch.supply"
        super().__init__(profile=profile)
        self._save_lock = asyncio.Lock()
        self._store = MemoryStore(self)
        self._pid_review_tasks, self._pid_review_notice_attempts = {}, {}
        self._pid_learning_generation, self._pid_learning_edges = {}, {}
        self._pid_learning_observed_edges, self._pid_learning_holds = {}, {}
        self.notice_dispatches = []
        self.config_commits = []
        self.hardware_calls = []
        self.fail_create = self.fail_dismiss = self.fail_mobile = False
        self.cancel_after_commit = False
        self.extra_states = {"switch.supply": N(state="on", attributes={})} if supply else {}
        if supply:
            self.registry_rows["switch.supply"] = N(
                entity_id="switch.supply", id="supply-registry", unique_id="supply-native",
                device_id="separate-supply-device", platform="native", area_id=SPEC.area_id,
            )
            # Area lookup is HA registry transport. The actual relay identity
            # and cross-controller claim guards still execute unchanged.
            supply_module = importlib.import_module(PACKAGE + ".equipment_power_switch")
            supply_module.entity_area = lambda hass, entity: (
                getattr(hass.registry.async_get(entity), "area_id", None)
            )
        original_get = self.hass.states.get
        self.hass.states.get = lambda entity: self.extra_states.get(entity, original_get(entity))
        self.hass.config_entries.async_update_entry = self.commit_entry

    def commit_entry(self, entry, *, data=None, options=None):
        # Commit through the original fixture's HA config-entry transport.
        # The production async_update method remains intact on both sides.
        fixture["fixture"]["Runtime"].update_entry(entry, data=data, options=options)
        self.config_commits.append(deepcopy(entry.options))
        last = self.cfg.get("pid_last_calibration")
        if (self.cancel_after_commit and isinstance(last, dict)
                and last.get("method") == "passive_approved_imc_lambda"):
            self.cancel_after_commit = False
            raise asyncio.CancelledError("Injected interruption after actual gain commit")

    def create_task(self, coroutine):
        if coroutine.cr_code.co_name == "_deliver_pid_review_notice":
            saved = self._store.payload["records"][SPEC.identifier]
            self.notice_dispatches.append(deepcopy(saved.get("pid_passive_review")))
        return super().create_task(coroutine)

    async def service_call(self, domain, service, data, **kwargs):
        call = {"domain": domain, "service": service, "data": deepcopy(data),
                "target": deepcopy(kwargs.get("target"))}
        self.calls.append(call)
        if domain not in ("persistent_notification", "notify"):
            self.hardware_calls.append(call)
            raise AssertionError("Review lifecycle must not dispatch hardware commands")
        if service == "create" and self.fail_create:
            raise RuntimeError("Injected notification delivery failure")
        if service == "dismiss" and self.fail_dismiss:
            raise RuntimeError("Injected notification clear failure")
        if domain == "notify" and service == "mobile_app_phone" and self.fail_mobile:
            raise RuntimeError("Injected selected mobile delivery failure")

    async def drain(self):
        while self.queued_tasks:
            tasks, self.queued_tasks = self.queued_tasks, []
            await asyncio.gather(*tasks)

    def seed_evidence(self):
        context, cycle_at, mode = self.evidence()
        ledger = deepcopy(self.record[store.ACTIVE])
        metric = ledger["summary"]["metric"]
        store.activate(self.record, context, self.now, metric, self.cfg["sample_seconds"])
        store.remember(self.record, ledger, self.now)
        return context, cycle_at, mode

    async def seed_review(self):
        context, _, mode = self.seed_evidence()
        proposal = review.proposal_for(self.cfg, self.record[store.ACTIVE]["summary"],
                                       context, self.now)
        assert proposal is not None
        self.record["pid_passive_review"] = proposal
        await self._save()
        return proposal

    async def restart(self):
        saved = deepcopy(self._store.payload)
        owner = self

        class RestartStore(MemoryStore):
            def __init__(self, *args, **kwargs):
                super().__init__(owner, saved)

        storage = ModuleType("homeassistant.helpers.storage")
        storage.Store = RestartStore
        with patch.dict(sys.modules, {storage.__name__: storage}):
            await self.async_start()
        self.record = self.records[SPEC.identifier]
        assert self._ready, "Actual startup must successfully load and maintain the ledger"
        await self.drain()

    async def complete_natural_cycle(self):
        context, _, _ = self.seed_evidence()
        ledger = deepcopy(self.record[store.ACTIVE])
        ledger["cycles"] = ledger["cycles"][:4]
        for row in ledger["cycles"]:
            row["at"] -= 40000
        store.remember(self.record, ledger, self.now)
        observer = passive.PassiveObserver(self.record[store.ACTIVE], now=self.now)
        options = dict(context=context, metric="temperature", direction=1,
                       sample_seconds=300, safe=True)
        start = self.now - 42 * 300
        for index in range(6):
            observer.observe(at=start - (6 - index) * 300, value=17.,
                             on=False, owned=False, **options)
        for index in range(42):
            value = 17. + 4. * (1. - math.exp(-max(0., index * 5. - 10.) / 28.))
            observer.observe(at=start + index * 300, value=value, on=True,
                             owned=True, **options)
        assert len(observer.cycles) == 4 and observer.on
        self._pid_passive_observers[SPEC.identifier] = observer
        self.readings["temperature"] = 21.
        cfg, cap = self.cfg, self.cap
        plan = model.plan_for(self.manager, SPEC)
        target = model.targets(self.manager, SPEC, cap, cfg, plan)
        await self._pid_passive_observe(
            SPEC, cfg, cap, plan, target, self.measurements(SPEC, cap),
            self.record, self.state, "heat", "temperature", target["heat"], True, True,
        )


for method in METHODS:
    setattr(LifecycleRuntime, method, getattr(production, method))


class ReviewLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_upstream_holds_block_both_real_auto_and_approved_writers(self):
        for method in ("adaptive_auto", "adaptive_suggest"):
            for hold in (None, "paused", "pending", "unavailable"):
                with self.subTest(method=method, hold=hold):
                    runtime = LifecycleRuntime(method=method, supply=True)
                    evidence = runtime.seed_evidence()
                    pending = await runtime.seed_review() if method == "adaptive_suggest" else None
                    if hold == "paused":
                        runtime.record["upstream"]["paused"] = "upstream_switch_manual_override"
                    elif hold == "pending":
                        runtime.record["upstream"]["pending"] = {"desired": "off"}
                    elif hold == "unavailable":
                        runtime.extra_states["switch.supply"].state = "unavailable"
                    before = deepcopy(runtime.raw())
                    if pending is not None:
                        accepted = await runtime.async_review_pid(SPEC, "approve", token=pending["id"])
                        self.assertEqual(accepted, hold is None)
                    else:
                        await runtime.apply(evidence)
                    await runtime.drain()
                    if hold is None:
                        self.assertEqual(runtime.cfg["kp"], 22.)
                    else:
                        self.assertEqual(runtime.raw(), before)
                    self.assertEqual(runtime.hardware_calls, [])

    async def test_timing_mismatch_rejects_pending_review_without_gain_change(self):
        runtime = LifecycleRuntime()
        pending = await runtime.seed_review()
        pending["tuning_settings"]["sample_seconds"] += 120
        before = deepcopy(runtime.raw())
        self.assertFalse(await runtime.async_review_pid(SPEC, "approve", token=pending["id"]))
        await runtime._pid_review_maintenance(SPEC, notify=False)
        self.assertEqual(runtime.raw(), before)
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "expired")
        self.assertEqual(runtime.record["pid_passive_review"]["reason"], "tuning_settings_changed")
        await runtime.drain()
        self.assertEqual(runtime.hardware_calls, [])

    async def test_48_hour_expiry_is_read_only_in_projection_then_persisted_by_maintenance(self):
        runtime = LifecycleRuntime()
        pending = await runtime.seed_review()
        created = pending["created_at"]
        at_limit = review.review_projection(pending, runtime.cfg, created + 48 * 3600,
                                           saved=runtime.record[store.ACTIVE])
        self.assertEqual(at_limit["state"], "pending")
        runtime.now = created + 48 * 3600 + 1
        before = deepcopy(runtime.record)
        projected = review.review_projection(pending, runtime.cfg, runtime.now,
                                              saved=runtime.record[store.ACTIVE])
        self.assertEqual(projected["state"], "expired")
        self.assertEqual(runtime.record, before)
        await runtime._pid_review_maintenance(SPEC, notify=False)
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "expired")
        self.assertEqual(runtime.persisted[-1]["pid_passive_review"]["reason"],
                         "recommendation_expired")
        self.assertFalse(await runtime.async_review_pid(SPEC, "approve", token=pending["id"]))
        await runtime.drain()
        self.assertEqual(runtime.cfg["kp"], 20.)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_cancellation_after_committed_gains_reconciles_exact_receipt_after_restart(self):
        runtime = LifecycleRuntime()
        pending = await runtime.seed_review()
        runtime.cancel_after_commit = True
        with self.assertRaises(asyncio.CancelledError):
            await runtime.async_review_pid(SPEC, "approve", token=pending["id"])
        self.assertEqual(runtime.cfg["kp"], 22., "Actual config-entry commit already happened")
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "pending")
        self.assertTrue(review.review_application_matches(pending, runtime.cfg))
        writes = len(runtime.config_commits)
        await runtime.restart()
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "applied")
        self.assertEqual(runtime.persisted[-1]["pid_passive_review"]["state"], "applied")
        self.assertFalse(await runtime.async_review_pid(SPEC, "approve", token=pending["id"]))
        await runtime._pid_review_maintenance(SPEC, notify=False)
        self.assertEqual(len(runtime.config_commits), writes, "Recovery never reapplies gains")
        self.assertEqual(runtime.hardware_calls, [])

    async def test_manual_gain_change_expires_review_and_matching_numbers_do_not_fake_receipt(self):
        runtime = LifecycleRuntime()
        pending = await runtime.seed_review()
        await runtime.async_update(SPEC, dict(pending["apply"]), operating_mode="heat")
        await runtime._pid_review_maintenance(SPEC, notify=False)
        self.assertFalse(review.review_application_matches(pending, runtime.cfg))
        self.assertEqual({key: runtime.cfg[key] for key in ("kp", "ki", "kd")}, pending["apply"])
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "expired")
        self.assertFalse(await runtime.async_review_pid(SPEC, "approve", token=pending["id"]))
        await runtime.drain()
        self.assertEqual(runtime.cfg["kp"], 22.)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_suggest_auto_toggle_preserves_completed_context_bank(self):
        runtime = LifecycleRuntime()
        runtime.seed_evidence()
        before = deepcopy(runtime.record[store.BANK])
        for method in ("adaptive_auto", "adaptive_suggest"):
            await runtime.async_update(SPEC, {"pid_calibration_method": method}, operating_mode="heat")
            self.assertEqual(runtime.cfg["pid_calibration_method"], method)
            self.assertEqual(runtime.record[store.BANK], before)
            self.assertEqual(runtime.record[store.ACTIVE]["summary"]["valid_cycles"], 5)
        await runtime.drain()
        self.assertEqual(runtime.hardware_calls, [])

    async def test_manual_gain_edit_for_inactive_heat_clears_only_heat_contexts(self):
        runtime = LifecycleRuntime()
        heat, _, _ = runtime.seed_evidence()
        await runtime.async_request_mode(SPEC, "cool")
        cool, _, _ = runtime.seed_evidence()
        self.assertEqual(set(runtime.record[store.BANK]), {heat, cool})
        cool_before = deepcopy(runtime.record[store.BANK][cool])
        await runtime.async_update(SPEC, {"kp": 21.}, operating_mode="heat")
        self.assertEqual(set(runtime.record[store.BANK]), {cool})
        self.assertEqual(runtime.record[store.BANK][cool], cool_before)
        self.assertEqual(runtime.record[store.ACTIVE]["context"], cool)
        self.assertEqual(runtime.cfg["kp"], 20.)
        self.assertEqual(model.settings_for_mode(runtime.manager, SPEC, "heat")["kp"], 21.)
        await runtime.drain()
        self.assertEqual(runtime.hardware_calls, [])

    async def test_actual_startup_expires_cycle_evidence_without_a_new_cycle(self):
        runtime = LifecycleRuntime()
        runtime.seed_evidence()
        await runtime._save()
        runtime.now += passive.MAX_AGE_S
        await runtime.restart()
        self.assertEqual(runtime.record[store.ACTIVE]["summary"]["valid_cycles"], 0)
        self.assertNotIn("suggested_gains", runtime.record[store.ACTIVE]["summary"])
        self.assertEqual(runtime.persisted[-1][store.ACTIVE]["cycles"], [])
        self.assertEqual(runtime._pid_passive_observers, {})
        self.assertEqual(runtime.hardware_calls, [])

    async def test_completed_review_is_persisted_before_notice_dispatch_and_failed_delivery_retries_on_restart(self):
        runtime = LifecycleRuntime()
        runtime.fail_create = True
        with self.assertLogs(review._LOGGER, level="ERROR"):
            await runtime.complete_natural_cycle()
            await runtime.drain()
        pending = runtime.record["pid_passive_review"]
        self.assertEqual(pending["state"], "pending")
        self.assertIsNone(pending.get("notified_at"))
        self.assertTrue(runtime.notice_dispatches)
        self.assertEqual(runtime.notice_dispatches[0]["id"], pending["id"])
        self.assertEqual(runtime.notice_dispatches[0]["state"], "pending")
        runtime.fail_create = False
        await runtime.restart()
        self.assertEqual(runtime.record["pid_passive_review"]["notified_at"], runtime.now)
        self.assertEqual(sum(c["service"] == "create" for c in runtime.calls), 2)
        await runtime._pid_review_maintenance(SPEC)
        await runtime.drain()
        self.assertEqual(sum(c["service"] == "create" for c in runtime.calls), 2)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_failed_notice_clear_is_replayed_after_restart_without_reapplying(self):
        runtime = LifecycleRuntime()
        pending = await runtime.seed_review()
        await runtime._pid_review_maintenance(SPEC)
        await runtime.drain()
        runtime.fail_dismiss = True
        self.assertTrue(await runtime.async_review_pid(SPEC, "discard", token=pending["id"]))
        await runtime.drain()
        self.assertEqual(runtime.record["pid_passive_review"]["state"], "discarded")
        self.assertIsNot(runtime.record["pid_passive_review"].get("notification_cleared"), True)
        runtime.fail_dismiss = False
        await runtime.restart()
        self.assertIs(runtime.record["pid_passive_review"]["notification_cleared"], True)
        self.assertEqual(runtime.calls[-1]["service"], "dismiss")
        self.assertEqual(runtime.cfg["kp"], 20.)
        self.assertEqual(runtime.hardware_calls, [])

    async def test_partial_mobile_failure_retries_same_notice_without_gains_or_hardware(self):
        runtime = LifecycleRuntime()
        notify_setting = importlib.import_module(PACKAGE + ".const").CONF_NOTIFY_TARGETS
        runtime.manager.entry.options[notify_setting] = ["notify.mobile_app_phone"]
        pending = await runtime.seed_review()
        runtime.fail_mobile = True
        with self.assertLogs(review._LOGGER, level="ERROR"):
            await runtime._pid_review_maintenance(SPEC)
            await runtime.drain()
        self.assertNotIn("notified_at", runtime.record["pid_passive_review"],
                         "HA success must not mark a failed selected phone as delivered")
        first_create = next(c for c in runtime.calls if c["service"] == "create")
        first_mobile = next(c for c in runtime.calls if c["service"] == "mobile_app_phone")
        runtime.fail_mobile = False
        runtime.now += 301
        await runtime._pid_review_maintenance(SPEC)
        await runtime.drain()
        creates = [c for c in runtime.calls if c["service"] == "create"]
        mobiles = [c for c in runtime.calls if c["service"] == "mobile_app_phone"]
        self.assertEqual(len(creates), 2)
        self.assertEqual(len(mobiles), 2)
        self.assertEqual(creates[-1]["data"]["notification_id"],
                         first_create["data"]["notification_id"])
        self.assertEqual(mobiles[-1]["data"]["data"]["tag"],
                         first_mobile["data"]["data"]["tag"])
        self.assertEqual(mobiles[-1]["data"]["data"]["actions"],
                         first_mobile["data"]["data"]["actions"])
        self.assertEqual(runtime.record["pid_passive_review"]["id"], pending["id"])
        self.assertEqual(runtime.record["pid_passive_review"]["notified_at"], runtime.now)
        delivered_calls = deepcopy(runtime.calls)
        runtime.now += 600
        await runtime._pid_review_maintenance(SPEC)
        await runtime.drain()
        self.assertEqual(runtime.calls, delivered_calls)
        self.assertEqual(runtime.cfg["kp"], 20.)
        self.assertEqual(runtime.config_commits, [])
        self.assertEqual(runtime.hardware_calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
