"""Exercise real optional transports across HA startup, timeouts and stop.

Only HA registries/providers are simulated. Notification code, lifecycle
guards, response deadlines and delivery decisions are the production modules.
No real service, notification recipient or appliance is contacted.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
PACKAGE = "hem_074b5_notification_fixture"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package


def stub(name, **values):
    module = ModuleType(name)
    module.__dict__.update(values)
    sys.modules[name] = module
    return module


ha = stub("homeassistant", __path__=[])
helpers = stub("homeassistant.helpers", __path__=[])
areas = stub("homeassistant.helpers.area_registry", async_get=lambda hass: N(
    async_get_area=lambda area: N(name="Living room") if area == "room" else None))
entities = stub("homeassistant.helpers.entity_registry", async_get=lambda hass: N(
    async_get=lambda entity: N(platform="mobile_app", disabled_by=None)
    if entity.startswith("notify.") else None))
helpers.area_registry, helpers.entity_registry = areas, entities
ha.helpers = helpers
stub(PACKAGE + ".discovery", entity_area=lambda *args: "room",
     is_window=lambda *args: True, is_window_contact=lambda *args, **kwargs: True)
stub(PACKAGE + ".occupancy_policy", _bool_presence=lambda value: False,
     home_presence=lambda *args, **kwargs: ("away", None, None))
stub(PACKAGE + ".room_sources", native=lambda *args: True, selected=lambda *args: [])
stub(PACKAGE + ".equipment_model", settings=lambda *args: {"announce_device_errors": True})

delivery = importlib.import_module(PACKAGE + ".notification_delivery")
hub = importlib.import_module(PACKAGE + ".hub_delivery")
review = importlib.import_module(PACKAGE + ".pid_review")
shade = importlib.import_module(PACKAGE + ".shade_delivery")
faults = importlib.import_module(PACKAGE + ".device_faults")
away = importlib.import_module(PACKAGE + ".away_windows")
const = importlib.import_module(PACKAGE + ".const")


class Services:
    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.stalled = set()
        self.failed = set()
        self.entered = asyncio.Event()
        self.cancelled = []
        self.stop_on_cancel = False
        self.after_call = None
        self.accepted = True
        self.available = {
            ("persistent_notification", "create"),
            ("persistent_notification", "dismiss"),
            ("notify", "send_message"), ("notify", "mobile_app_phone"),
            ("notify", "announcement_hub"), ("tts", "speak"),
        }

    def has_service(self, domain, service):
        return (domain, service) in self.available

    async def async_call(self, domain, service, data, **kwargs):
        key = (domain, service)
        self.calls.append((domain, service, deepcopy(data), kwargs))
        self.entered.set()
        if key in self.stalled:
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                self.cancelled.append(key)
                if self.stop_on_cancel:
                    self.hass.state = "stopping"
                raise
        if self.after_call is not None:
            self.after_call()
        if key in self.failed:
            raise RuntimeError("Provider unavailable")
        return {"accepted": self.accepted} if key == ("notify", "announcement_hub") else None


def fixture(state="running"):
    hass = N(state=state, config=N(language="en"), data={}, hub_installed=False,
             states=N(get=lambda entity: None, async_all=lambda domain: [
                 N(entity_id="person.owner", state="not_home", attributes={})
             ] if domain == "person" else []))
    hass.services = Services(hass)
    hass.config_entries = N(async_entries=lambda domain: [N(state=N(value="loaded"))]
                            if hass.hub_installed and domain == "announcement_hub" else [])
    manager = N(hass=hass, entry=N(entry_id="home"), _active=True, _tasks=set(), settings={
        const.CONF_NOTIFY_TARGETS: ["notify.mobile_app_phone"],
        const.CONF_AUTO_NOTIFY: True, const.CONF_AUTO_TTS: False,
        const.CONF_TTS_ENGINE: "tts.voice", const.CONF_MEDIA_PLAYERS: ["media_player.room"],
        const.CONF_LANGUAGE: "en", const.CONF_SHADE_ANNOUNCE: True,
        const.CONF_AWAY_WINDOWS_PERSONS: ["person.owner"],
        const.CONF_AWAY_WINDOWS_DELIVERY: ["mobile_notification"],
    })
    manager._targets_in_room = lambda targets, area: targets
    spec = N(identifier="device", area_id="room", source_device_id="native", name="Heater")
    pending = {
        "id": "a" * 32, "state": "pending", "algorithm": "performance_v1",
        "current": {"kp": 10., "ki": .1, "kd": 0.},
        "apply": {"kp": 9., "ki": .1, "kd": 0.}, "validated_windows": 2,
    }
    return manager, spec, pending


def calls(manager, spec, pending):
    return {
        "review_publish": lambda: review.async_publish_review(manager.hass, manager, spec, pending),
        "review_clear": lambda: review.async_clear_review(manager.hass, manager, spec),
        "shade": lambda: shade.async_announce_before_move(manager, area="room", action="close"),
        "fault": lambda: faults._deliver_device_notice(manager, spec, "Title", "Message", "en",
                                                        area_name="Living room", kind="native_fault"),
        "away": lambda: away.deliver_notice(manager, (("binary_sensor.window", "Window"),)),
        "system": lambda: hub.async_system_notification(manager.hass, "Title", "Message", "room"),
        "hub": lambda: hub.async_submit_hub(manager.hass, {"text": "Message"}),
    }


class NotificationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_paths_hold_before_running_and_through_every_stop_state(self):
        for state in ("not_running", "starting", "stopping", "final_write", "stopped", None):
            for name in calls(*fixture()):
                with self.subTest(state=state, path=name):
                    manager, spec, pending = fixture(state)
                    manager.hass.hub_installed = True
                    self.assertFalse(await calls(manager, spec, pending)[name]())
                    self.assertEqual(manager.hass.services.calls, [])

    async def test_successful_review_keeps_target_actions_and_same_clear_identity(self):
        manager, spec, pending = fixture()
        self.assertTrue(await review.async_publish_review(manager.hass, manager, spec, pending))
        publish = manager.hass.services.calls
        self.assertEqual([row[:2] for row in publish], [
            ("persistent_notification", "create"), ("notify", "mobile_app_phone")])
        mobile = publish[-1][2]
        self.assertEqual([action["action"] for action in mobile["data"]["actions"]], [
            "HEM_PID_REVIEW_APPROVE_" + pending["id"], "HEM_PID_REVIEW_DISCARD_" + pending["id"]])
        self.assertTrue(await review.async_clear_review(manager.hass, manager, spec))
        clear = manager.hass.services.calls[-2:]
        self.assertEqual(clear[0][2]["notification_id"], publish[0][2]["notification_id"])
        self.assertEqual(clear[1][2]["data"]["tag"], mobile["data"]["tag"])

    async def test_stalled_direct_transport_times_out_and_is_cancelled(self):
        manager, _, _ = fixture()
        services = manager.hass.services
        services.stalled.add(("notify", "send_message"))
        with patch.object(delivery, "DIRECT_RESPONSE_TIMEOUT", .01):
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(delivery.async_call_notification(
                    manager.hass, "notify", "send_message", {"message": "test"}), .5)
        self.assertEqual(services.cancelled, [("notify", "send_message")])

    async def test_timed_out_mobile_review_does_not_claim_delivery_or_clear(self):
        manager, spec, pending = fixture()
        manager.hass.services.stalled.add(("notify", "mobile_app_phone"))
        with patch.object(delivery, "DIRECT_RESPONSE_TIMEOUT", .01):
            self.assertFalse(await review.async_publish_review(manager.hass, manager, spec, pending))
            self.assertFalse(await review.async_clear_review(manager.hass, manager, spec))
        self.assertNotIn("notified_at", pending)
        self.assertNotIn("notification_cleared", pending)
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(len(manager.hass.services.cancelled), 2)

    async def test_cancellation_propagates_without_fallback_for_every_transport(self):
        for name in calls(*fixture()):
            with self.subTest(path=name):
                manager, spec, pending = fixture()
                if name == "hub":
                    manager.hass.hub_installed = True
                services = manager.hass.services
                services.stalled = set(services.available)
                task = asyncio.create_task(calls(manager, spec, pending)[name]())
                await asyncio.wait_for(services.entered.wait(), .5)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertEqual(len(services.calls), 1)

    async def test_stop_during_first_channel_prevents_every_later_channel(self):
        for name in ("review_publish", "review_clear", "shade", "fault"):
            with self.subTest(path=name):
                manager, spec, pending = fixture()
                manager.settings[const.CONF_AUTO_TTS] = True
                services = manager.hass.services
                services.after_call = lambda: setattr(manager.hass, "state", "stopping")
                self.assertFalse(await calls(manager, spec, pending)[name]())
                self.assertEqual(len(services.calls), 1)

    async def test_stop_at_timeout_prevents_persistent_fallback(self):
        for name in ("shade", "fault", "away"):
            with self.subTest(path=name):
                manager, spec, pending = fixture()
                services = manager.hass.services
                services.stalled.add(("notify", "send_message"))
                services.stop_on_cancel = True
                with patch.object(delivery, "DIRECT_RESPONSE_TIMEOUT", .01):
                    self.assertFalse(await calls(manager, spec, pending)[name]())
                self.assertEqual([row[:2] for row in services.calls], [("notify", "send_message")])

    async def test_live_hub_rejection_never_uses_direct_fallback(self):
        for name in ("shade", "fault", "away"):
            with self.subTest(path=name):
                manager, spec, pending = fixture()
                manager.hass.hub_installed = True
                manager.settings[const.CONF_HUB] = True
                manager.hass.services.accepted = False
                self.assertFalse(await calls(manager, spec, pending)[name]())
                self.assertEqual([row[:2] for row in manager.hass.services.calls],
                                 [("notify", "announcement_hub")])

    async def test_hub_deadline_cancels_transport_and_never_claims_acceptance(self):
        manager, _, _ = fixture()
        manager.hass.hub_installed = True
        manager.hass.services.stalled.add(("notify", "announcement_hub"))
        with patch.object(hub, "HUB_RESPONSE_TIMEOUT", .01):
            self.assertFalse(await hub.async_submit_hub(manager.hass, {"text": "Message"}))
        self.assertEqual(manager.hass.services.cancelled, [("notify", "announcement_hub")])

    async def test_completed_hub_ack_is_not_discarded_when_stop_begins(self):
        manager, _, _ = fixture()
        manager.hass.hub_installed = True
        manager.hass.services.after_call = lambda: setattr(manager.hass, "state", "stopping")
        self.assertTrue(await hub.async_submit_hub(manager.hass, {"text": "Message"}))

    async def test_fault_quiesce_cancels_all_work_and_shutdown_drains_it(self):
        manager, _, _ = fixture()
        monitor = faults.NativeDeviceFaultMonitor(manager)
        monitor.active = True
        foreground = asyncio.create_task(asyncio.sleep(100))
        background = asyncio.create_task(asyncio.sleep(100))
        monitor._tasks.add(foreground)
        monitor._offline_tasks["native"] = background
        monitor.quiesce(shutdown=True)
        self.assertFalse(monitor.active)
        self.assertEqual(monitor._tasks, {foreground})
        self.assertEqual(monitor._offline_tasks, {"native": background})
        await monitor.async_stop(shutdown=True)
        self.assertTrue(foreground.cancelled())
        self.assertTrue(background.cancelled())
        self.assertEqual(monitor._tasks, set())
        self.assertEqual(monitor._offline_tasks, {})

    async def test_fault_work_uses_entry_background_ownership_only_while_running(self):
        manager, spec, _ = fixture("starting")
        created = []

        def background(hass, work, name):
            created.append(name)
            return asyncio.create_task(work, name=name)

        manager.entry.async_create_background_task = background
        manager.hass.async_create_task = lambda work: self.fail("Optional notices cannot enter startup tasks")
        monitor = faults.NativeDeviceFaultMonitor(manager)
        monitor.active = True
        report = {"status": "fault", "code": "E1"}
        with patch.object(faults, "_faults_for", return_value=report), \
                patch.object(faults, "_signature", return_value=("E1",)), \
                patch.object(monitor, "_offline_problems", return_value={"native": (spec, ("climate.unit",))}):
            monitor._refresh_spec(spec)
            monitor._sync_offline_alerts()
            self.assertEqual(created, [])
            manager.hass.state = "running"
            monitor._fingerprints.clear()
            monitor._refresh_spec(spec)
            monitor._sync_offline_alerts()
            self.assertEqual(len(created), 2)
            self.assertEqual(len(monitor._tasks), 1)
            self.assertEqual(len(monitor._offline_tasks), 1)
            await monitor.async_stop(shutdown=True)
        self.assertEqual(manager.hass.services.calls, [])

    async def test_away_submission_uses_owned_background_task(self):
        manager, _, _ = fixture()
        manager.settings[const.CONF_AWAY_WINDOWS_ALERT] = True
        created = []

        def background(hass, work, name):
            created.append(name)
            return asyncio.create_task(work, name=name)

        manager.entry.async_create_background_task = background
        manager.hass.async_create_task = lambda work: self.fail("Away notices cannot enter startup tasks")
        alert = away.AwayWindowAlert(manager)
        alert._armed = True
        with patch.object(away, "confirmed_home_state", return_value="away"), \
                patch.object(away, "open_windows", return_value=(("binary_sensor.window", "Window"),)):
            alert._fire(None)
            self.assertEqual(len(created), 1)
            pending = alert._pending_task
            self.assertIn(pending, manager._tasks)
            alert.stop()
            await asyncio.gather(pending, return_exceptions=True)
            await asyncio.sleep(0)
        self.assertEqual(manager.hass.services.calls, [])
        self.assertEqual(manager._tasks, set())
        self.assertIsNone(alert._pending_task)

    async def test_away_stop_cancels_pending_send_and_does_not_schedule_retry(self):
        manager, _, _ = fixture()
        alert = away.AwayWindowAlert(manager)
        alert._armed = True
        alert._pending_task = asyncio.create_task(asyncio.sleep(100))
        pending = alert._pending_task
        alert.stop()
        await asyncio.gather(pending, return_exceptions=True)
        self.assertTrue(pending.cancelled())
        self.assertFalse(alert._armed)
        manager.hass.state = "stopping"
        alert._schedule(1)
        self.assertIsNone(alert._timer)


if __name__ == "__main__":
    unittest.main()
