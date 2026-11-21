"""Exercise real advice, contact transitions, expiry and delivery grace.

The production evaluator and cooldown run with an injected clock/scheduler.
No actual Home Assistant service, storage or physical appliance is contacted.
"""
from __future__ import annotations

import ast
from dataclasses import replace
import importlib
import logging
import math
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
from typing import Any
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
PACKAGE = "hem_b10_window_grace"
package = ModuleType(PACKAGE)
package.__path__ = [str(SOURCE)]
sys.modules[PACKAGE] = package
logic = importlib.import_module(PACKAGE + ".logic")
policy = importlib.import_module(PACKAGE + ".window_close_cooldown")
const = importlib.import_module(PACKAGE + ".const")
SETTING = const.CONF_WINDOW_CLOSE_COOLDOWN_MINUTES


def room(area="living", states=(False,), *, co2=1800):
    return logic.Room(area, area.title(), tuple(
        logic.Window(f"binary_sensor.{area}_{i}", f"Window {i}", state)
        for i, state in enumerate(states)
    ), (logic.Reading(f"sensor.{area}_co2", "CO2", "co2", co2),))


def raw_plan(*rooms, bad_weather=True, environment=None, secondary=()):
    rooms = rooms or (room(),)
    plan = logic.evaluate(
        (logic.Reading("sensor.outside_co2", "Outdoor CO2", "co2", 400),),
        (logic.Weather("weather.home", "windy" if bad_weather else "sunny", 18, 50,
                       65 if bad_weather else 5),),
        (), tuple(rooms), environment=environment,
    )
    if not secondary:
        return plan
    return replace(plan,
        rooms=tuple(r for r in rooms if r.area_id not in secondary),
        climate_rooms=tuple(r for r in rooms if r.area_id in secondary),
        recommendations=tuple(r for r in plan.recommendations if r.area_id not in secondary),
        climate_recommendations=tuple(r for r in plan.recommendations if r.area_id in secondary))


class Fixture:
    def __init__(self, minutes=5):
        self.now = 10_000.0
        self.timers = []
        self.invalid_areas = set()
        self.recalculations = 0
        self.manager = N(settings={SETTING: minutes}, _active=True,
                         hass=N(states={}), entry=N(entry_id="test-entry"))
        self.manager.raw = raw_plan()
        self.cooldown = policy.WindowCloseCooldown(
            self.manager, clock=lambda: self.now, schedule=self.schedule,
            binding=lambda area, contacts: bool(contacts) and area not in self.invalid_areas)
        self.manager._recalculate = self.recalculate
        self.manager.window_close_cooldown = self.cooldown
        self.manager.plan = self.manager.raw

    def schedule(self, seconds, callback):
        timer = N(deadline=self.now + seconds, callback=callback, active=True)
        self.timers.append(timer)

        def cancel():
            timer.active = False

        return cancel

    def recalculate(self):
        self.recalculations += 1
        self.manager.plan = self.cooldown.prepare(self.manager.raw)

    def prepare(self, plan):
        self.manager.raw = plan
        self.manager.plan = self.cooldown.prepare(plan)
        return self.manager.plan

    def transition(self, area="living", index=0, before="off", after="on"):
        self.cooldown.state_changed(f"binary_sensor.{area}_{index}",
                                    N(state=before), N(state=after))

    def fire_due(self):
        for timer in tuple(self.timers):
            if timer.active and timer.deadline <= self.now:
                timer.active = False
                timer.callback()

    def start(self, *, area="living", states=(False,), secondary=()):
        self.prepare(raw_plan(room(area, states), secondary=secondary))
        self.now += 10
        self.transition(area)
        opened = (True, *states[1:])
        return self.prepare(raw_plan(room(area, opened), secondary=secondary))


class CooldownTests(unittest.TestCase):
    def test_real_bad_weather_advice_waits_from_actual_opening(self):
        f = Fixture()
        offer = f.prepare(raw_plan(room()))
        self.assertFalse(offer.outdoor_safe)
        self.assertEqual(offer.recommendations[0].action, "open")
        self.assertTrue(offer.recommendations[0].cautions)
        f.now += 120  # Reading the advice is not time spent airing.
        f.transition()
        original = raw_plan(room(states=(True,)))
        self.assertEqual(original.recommendations[0].action, "close")
        held = f.prepare(original)
        self.assertEqual(held.recommendations, ())
        self.assertEqual(held.status, "blocked")
        self.assertFalse(held.outdoor_safe)
        self.assertEqual(held.outside_reasons, original.outside_reasons)
        self.assertEqual(held.rooms, original.rooms)
        report = held.environment["living"]["window_close_cooldown"]
        self.assertEqual(report["opened_at"], 10_120)
        self.assertEqual(report["until"], 10_420)
        f.now = 10_419.99
        self.assertTrue(f.cooldown.blocks("living"))
        f.now = 10_420
        f.fire_due()
        self.assertEqual(f.manager.plan.status, "close")
        self.assertEqual(f.manager.plan.recommendations[0].action, "close")
        self.assertFalse(f.cooldown.blocks("living"))

    def test_energy_close_metadata_is_held_without_erasing_measured_evidence(self):
        f = Fixture()
        f.start()
        energy = {"window_energy_status": "close_window_to_save_energy",
                  "window_energy_direction": "window_heat_loss",
                  "measured_room_temperature_c": 20.2, "heat_target_c": 20}
        original = raw_plan(room(states=(True,)), bad_weather=False,
                            environment={"living": {"room_ventilation": energy}})
        rec = logic.Recommendation("close", "living", "Living", original.rooms[0].windows,
                                   (logic.Reason("window_heat_loss"),))
        original = replace(original, status="close", recommendations=(rec,))
        result = f.prepare(original)
        self.assertEqual(result.status, "idle")
        self.assertEqual(result.recommendations, ())
        self.assertEqual(result.environment["living"]["room_ventilation"],
                         {**energy, "window_energy_status": "opening_cooldown"})
        self.assertEqual(energy["window_energy_status"], "close_window_to_save_energy")

    def test_both_recommendation_paths_and_other_rooms_keep_correct_urgency(self):
        f = Fixture()
        f.prepare(raw_plan(room("living", (True,)), room("bedroom"), secondary=("bedroom",)))
        f.now += 10
        f.transition("bedroom")
        result = f.prepare(raw_plan(room("living", (True,)), room("bedroom", (True,)),
                                    secondary=("bedroom",)))
        self.assertEqual([r.area_id for r in result.recommendations], ["living"])
        self.assertEqual(result.climate_recommendations, ())
        self.assertEqual(result.status, "close")
        self.assertTrue(f.cooldown.blocks("bedroom"))
        self.assertFalse(f.cooldown.blocks("living"))

    def test_unsolicited_manual_opening_has_no_cooldown(self):
        f = Fixture()
        f.prepare(raw_plan(room(co2=400)))
        f.transition()
        result = f.prepare(raw_plan(room(states=(True,), co2=400)))
        self.assertEqual(result.status, "close")
        self.assertFalse(f.cooldown.blocks("living"))

    def test_startup_and_unknown_to_open_do_not_invent_a_response(self):
        for before in (None, "unknown", "unavailable"):
            with self.subTest(before=before):
                f = Fixture()
                f.prepare(raw_plan(room()))
                f.prepare(raw_plan(room(states=(None,))))
                f.transition(before=before)
                result = f.prepare(raw_plan(room(states=(True,))))
                self.assertEqual(result.status, "close")
                self.assertFalse(f.cooldown.blocks("living"))
        f = Fixture()
        self.assertEqual(f.prepare(raw_plan(room(states=(True,)))).status, "close")
        self.assertFalse(f.cooldown.blocks("living"))

    def test_snapshot_transition_is_supported_without_an_ha_event(self):
        f = Fixture()
        f.prepare(raw_plan(room()))
        f.now += 13
        self.assertEqual(f.prepare(raw_plan(room(states=(True,)))).recommendations, ())
        self.assertEqual(f.cooldown.snapshot()["rooms"]["living"]["opened_at"], f.now)

    def test_repeated_reports_and_additional_windows_never_extend_interval(self):
        f = Fixture()
        f.start(states=(False, False))
        expected = f.cooldown.snapshot()["rooms"]["living"].copy()
        for delay in (1, 55, 95):
            f.now += delay
            f.transition(before="on", after="on")
            f.prepare(raw_plan(room(states=(True, False))))
        f.transition(index=1)
        f.prepare(raw_plan(room(states=(True, True))))
        self.assertEqual(f.cooldown.snapshot()["rooms"]["living"], expected)
        f.transition(before="on", after="off")
        self.assertTrue(f.cooldown.blocks("living"), "The other aired window is still open")
        f.transition(index=1, before="on", after="off")
        self.assertFalse(f.cooldown.blocks("living"))

    def test_consumed_offer_cannot_restart_on_an_unobserved_close_reopen(self):
        f = Fixture()
        f.start()
        f.transition(before="on", after="off")
        f.now += 1
        f.transition()
        self.assertFalse(f.cooldown.blocks("living"))
        self.assertEqual(f.prepare(raw_plan(room(states=(True,)))).status, "close")
        f.transition(before="on", after="off")
        f.prepare(raw_plan(room()))  # A genuinely new OPEN offer may be followed.
        f.transition()
        self.assertTrue(f.cooldown.blocks("living"))

    def test_disappeared_offer_expires_and_new_current_offer_is_usable(self):
        f = Fixture()
        f.prepare(raw_plan(room()))
        f.prepare(raw_plan(room(co2=400)))
        f.now += policy.OFFER_MAX_AGE_SECONDS + 1
        f.transition()
        self.assertFalse(f.cooldown.blocks("living"))
        f.prepare(raw_plan(room()))
        f.transition()
        self.assertTrue(f.cooldown.blocks("living"))

    def test_zero_disables_current_and_future_grace_without_revival(self):
        f = Fixture(0)
        self.assertEqual(f.start().status, "close")
        f = Fixture()
        f.start()
        f.manager.settings[SETTING] = 0
        self.assertFalse(f.cooldown.blocks("living"))
        f.manager.settings[SETTING] = 5
        self.assertFalse(f.cooldown.blocks("living"))

    def test_preference_edits_preserve_opened_at_and_expired_cannot_revive(self):
        f = Fixture()
        f.start()
        started = f.now
        f.now += 70
        f.manager.settings[SETTING] = 10
        self.assertTrue(f.cooldown.blocks("living"))
        self.assertEqual(f.cooldown.snapshot()["rooms"]["living"]["until"], started + 600)
        f.manager.settings[SETTING] = 1
        self.assertFalse(f.cooldown.blocks("living"))
        f.manager.settings[SETTING] = 60
        self.assertFalse(f.cooldown.blocks("living"))
        f = Fixture()
        f.start()
        f.now += 301
        f.manager.settings[SETTING] = 60
        self.assertFalse(f.cooldown.blocks("living"), "An expired saved deadline is final")

    def test_invalid_preferences_use_default_and_maximum_is_bounded(self):
        for value in (None, True, "five", -1, 61, math.nan, math.inf, {}, []):
            with self.subTest(value=value):
                f = Fixture(value)
                f.start()
                state = f.cooldown.snapshot()["rooms"]["living"]
                self.assertEqual(state["until"] - state["opened_at"], 300)
        f = Fixture(60)
        f.start()
        state = f.cooldown.snapshot()["rooms"]["living"]
        self.assertEqual(state["until"] - state["opened_at"], 3600)

    def test_room_removal_contact_changes_and_invalid_binding_clear_episode(self):
        for change in ("room", "contacts", "binding"):
            with self.subTest(change=change):
                f = Fixture()
                f.start()
                if change == "room":
                    next_plan = raw_plan(room("kitchen", (True,)))
                elif change == "contacts":
                    next_plan = raw_plan(room(states=(True, False)))
                else:
                    f.invalid_areas.add("living")
                    next_plan = raw_plan(room(states=(True,)))
                f.prepare(next_plan)
                self.assertFalse(f.cooldown.blocks("living"))
                self.assertNotIn("living", f.cooldown.snapshot()["rooms"])

    def test_wrong_contact_and_ambiguous_room_ownership_cannot_arm(self):
        f = Fixture()
        f.prepare(raw_plan(room()))
        f.transition(index=17)
        self.assertFalse(f.cooldown.blocks("living"))
        shared = room()
        duplicate = replace(shared, area_id="bedroom", name="Bedroom")
        f.prepare(raw_plan(shared, duplicate))
        f.transition()
        self.assertFalse(f.cooldown.blocks("living"))
        self.assertFalse(f.cooldown.blocks("bedroom"))

    def test_expiry_timer_recalculates_current_conditions_and_does_not_send_old_close(self):
        f = Fixture()
        f.start()
        f.manager.raw = raw_plan(room(states=(True,), co2=400), bad_weather=False)
        f.now += 300
        f.fire_due()
        self.assertEqual(f.recalculations, 1)
        self.assertEqual(f.manager.plan.recommendations, ())
        self.assertEqual(f.manager.plan.status, "idle")
        self.assertFalse(any(timer.active for timer in f.timers))

    def test_only_earliest_room_deadline_is_armed_and_other_room_keeps_its_time(self):
        f = Fixture()
        f.prepare(raw_plan(room("living"), room("bedroom")))
        f.transition("living")
        f.now += 30
        f.transition("bedroom")
        f.prepare(raw_plan(room("living", (True,)), room("bedroom", (True,))))
        self.assertEqual(sum(t.active for t in f.timers), 1)
        f.now = 10_300
        f.fire_due()
        self.assertFalse(f.cooldown.blocks("living"))
        self.assertTrue(f.cooldown.blocks("bedroom"))
        self.assertEqual([r.area_id for r in f.manager.plan.recommendations], ["living"])
        self.assertEqual([t.deadline for t in f.timers if t.active], [10_330])

    def test_restore_keeps_remaining_time_and_does_not_restore_offers(self):
        f = Fixture()
        f.start()
        f.now += 60
        snapshot = f.cooldown.snapshot()
        restored = Fixture()
        restored.now = f.now + 30
        restored.cooldown.restore(snapshot)
        result = restored.prepare(raw_plan(room(states=(True,))))
        self.assertEqual(result.recommendations, ())
        self.assertEqual(restored.cooldown.snapshot()["rooms"]["living"]["until"], 10_310)
        self.assertEqual([t.deadline for t in restored.timers if t.active], [10_310])
        restored.now = 10_310
        restored.fire_due()
        self.assertEqual(restored.manager.plan.status, "close")
        f = Fixture()
        f.prepare(raw_plan(room()))
        restored = Fixture()
        restored.cooldown.restore(f.cooldown.snapshot())
        restored.transition()
        self.assertEqual(restored.prepare(raw_plan(room(states=(True,)))).status, "close")

    def test_restore_revalidates_current_contacts_and_closed_state(self):
        f = Fixture()
        f.start()
        data = f.cooldown.snapshot()
        for change in ("closed", "different_contacts", "wrong_binding"):
            with self.subTest(change=change):
                restored = Fixture()
                restored.now = f.now + 5
                restored.cooldown.restore(data)
                if change == "wrong_binding":
                    restored.invalid_areas.add("living")
                states = (False,) if change == "closed" else (True, False) if change == "different_contacts" else (True,)
                restored.prepare(raw_plan(room(states=states)))
                self.assertFalse(restored.cooldown.blocks("living"))

    def test_restored_deadline_survives_sources_loading_after_hem(self):
        source = Fixture()
        source.start()
        saved = source.cooldown.snapshot()
        contact = "binary_sensor.living_0"
        for explicit, device_class in ((None, "window"), ([contact], "door")):
            with self.subTest(explicit=explicit):
                f = Fixture()
                f.now = source.now + 30
                f.cooldown._binding = None
                f.manager.settings["selected"] = explicit
                f.cooldown.restore(saved)
                discovery = ModuleType(PACKAGE + ".discovery")
                discovery.entity_area = lambda hass, entity: "living"
                discovery.is_window_contact = lambda *args, **kwargs: True
                discovery.OPTIONAL_WINDOW_CONTACT_CLASSES = {"door", "opening"}
                sources = ModuleType(PACKAGE + ".room_sources")
                sources.selected = lambda settings, area, group: settings["selected"]
                ha = ModuleType("homeassistant")
                helpers = ModuleType("homeassistant.helpers")
                registry = ModuleType("homeassistant.helpers.entity_registry")
                registry.async_get = lambda hass: N(async_get=lambda entity: N(
                    device_class=None, original_device_class=device_class))
                helpers.entity_registry = registry
                with patch.dict(sys.modules, {
                    discovery.__name__: discovery, sources.__name__: sources,
                    ha.__name__: ha, helpers.__name__: helpers,
                    registry.__name__: registry,
                }):
                    # Legacy discovery may not expose a contact until its
                    # integration publishes a state after startup.
                    f.prepare(raw_plan(room(states=())))
                    self.assertTrue(f.cooldown.blocks("living"))
                    self.assertEqual(f.cooldown.snapshot()["rooms"]["living"],
                                     saved["rooms"]["living"])
                    f.manager.hass.states[contact] = N(state="on")
                    f.prepare(raw_plan(room(states=(True,))))
                    self.assertTrue(f.cooldown.blocks("living"))
                    self.assertEqual(f.cooldown.snapshot()["rooms"]["living"],
                                     saved["rooms"]["living"])
                    f.manager.hass.states[contact] = N(state="off")
                    f.prepare(raw_plan(room()))
                    self.assertFalse(f.cooldown.blocks("living"))

    def test_missing_source_without_verified_registry_cannot_preserve_grace(self):
        source = Fixture()
        source.start()
        for record in (None, N(device_class=None, original_device_class="motion")):
            with self.subTest(record=record):
                f = Fixture()
                f.now = source.now + 30
                f.cooldown._binding = None
                f.cooldown.restore(source.cooldown.snapshot())
                discovery = ModuleType(PACKAGE + ".discovery")
                discovery.entity_area = lambda hass, entity: "living"
                discovery.is_window_contact = lambda *args, **kwargs: True
                discovery.OPTIONAL_WINDOW_CONTACT_CLASSES = {"door", "opening"}
                sources = ModuleType(PACKAGE + ".room_sources")
                sources.selected = lambda *args: None
                ha = ModuleType("homeassistant")
                helpers = ModuleType("homeassistant.helpers")
                registry = ModuleType("homeassistant.helpers.entity_registry")
                registry.async_get = lambda hass: N(async_get=lambda entity: record)
                helpers.entity_registry = registry
                with patch.dict(sys.modules, {
                    discovery.__name__: discovery, sources.__name__: sources,
                    ha.__name__: ha, helpers.__name__: helpers,
                    registry.__name__: registry,
                }):
                    f.prepare(raw_plan(room(states=())))
                    self.assertFalse(f.cooldown.blocks("living"))
                    self.assertEqual(f.cooldown.snapshot()["rooms"], {})

    def test_restore_rejects_malformed_future_expired_or_unbounded_journal(self):
        f = Fixture()
        f.start()
        data = f.cooldown.snapshot()
        mutations = [
            lambda d: d.update(saved_at=math.nan),
            lambda d: d.update(saved_at=f.now + 1),
            lambda d: d["rooms"]["living"].update(opened_at=True),
            lambda d: d["rooms"]["living"].update(opened_at=-1),
            lambda d: d["rooms"]["living"].update(until=math.inf),
            lambda d: d["rooms"]["living"].update(until=f.now),
            lambda d: d["rooms"]["living"].update(until=f.now + 3601),
            lambda d: d["rooms"]["living"].update(contacts=[]),
            lambda d: d["rooms"]["living"].update(contacts=["switch.native"]),
            lambda d: d["rooms"]["living"].update(contacts=["binary_sensor.living_0"] * 2),
        ]
        import copy
        for mutation in mutations:
            corrupted = copy.deepcopy(data)
            mutation(corrupted)
            restored = Fixture()
            restored.now = f.now
            restored.cooldown.restore(corrupted)
            self.assertFalse(restored.cooldown.blocks("living"), corrupted)
        for malformed in (None, [], "", True, {}, {"saved_at": f.now, "rooms": []}):
            restored = Fixture()
            restored.cooldown.restore(malformed)
            self.assertEqual(restored.cooldown.snapshot()["rooms"], {})

    def test_clock_rollback_and_nonfinite_values_fail_closed_without_new_timer(self):
        for value in (None, True, -1, math.nan, math.inf, 9999):
            with self.subTest(value=value):
                f = Fixture()
                f.start()
                f.now = value
                self.assertFalse(f.cooldown.blocks("living"))
                self.assertFalse(any(timer.active for timer in f.timers))
                f.now = 10_020
                self.assertEqual(f.prepare(raw_plan(room(states=(True,)))).status, "close")

    def test_selection_removal_is_rechecked_before_deferred_dispatch(self):
        f = Fixture()
        f.start()
        f.cooldown._binding = None
        f.manager.settings["selected"] = ["binary_sensor.living_0"]
        f.manager.hass.states = {"binary_sensor.living_0": N(state="on")}
        discovery = ModuleType(PACKAGE + ".discovery")
        discovery.entity_area = lambda hass, entity: "living"
        discovery.is_window_contact = lambda *args, **kwargs: True
        sources = ModuleType(PACKAGE + ".room_sources")
        sources.selected = lambda settings, area, group: settings["selected"]
        with patch.dict(sys.modules, {discovery.__name__: discovery, sources.__name__: sources}):
            self.assertTrue(f.cooldown.blocks("living"))
            f.manager.settings["selected"] = []
            self.assertFalse(f.cooldown.blocks("living"))


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_restore_lifecycle_ignores_a_late_load_after_shutdown(self):
        source = Fixture()
        source.start()
        snapshot = source.cooldown.snapshot()
        for stopped_during_load in (False, True):
            with self.subTest(stopped_during_load=stopped_during_load):
                f = Fixture()
                f.now = source.now + 30
                writes = []

                class Store:
                    def __init__(self, hass, version, key):
                        self.key = key

                    async def async_load(self):
                        if stopped_during_load:
                            f.cooldown.quiesce()
                        return snapshot

                    def async_delay_save(self, snapshot_factory, delay):
                        pass

                    async def async_save(self, data):
                        writes.append(data)

                ha = ModuleType("homeassistant")
                ha.__path__ = []
                helpers = ModuleType("homeassistant.helpers")
                helpers.__path__ = []
                storage = ModuleType("homeassistant.helpers.storage")
                storage.Store = Store
                with patch.dict(sys.modules, {ha.__name__: ha, helpers.__name__: helpers,
                                              storage.__name__: storage}):
                    await f.cooldown.async_start()
                    f.prepare(raw_plan(room(states=(True,))))
                    self.assertEqual(f.cooldown.blocks("living"), not stopped_during_load)
                    await f.cooldown.async_stop()
                self.assertEqual(len(writes), 0 if stopped_during_load else 1)

    async def test_stop_cancels_expiry_and_saves_original_deadline(self):
        f = Fixture()
        f.start()
        original = f.cooldown.snapshot()["rooms"]
        saved = []

        async def save(data):
            saved.append(data)

        f.cooldown._store = N(async_save=save)
        f.cooldown._restored = True
        f.cooldown.quiesce()
        self.assertFalse(any(t.active for t in f.timers))
        self.assertFalse(f.cooldown.blocks("living"))
        f.now += 1
        await f.cooldown.async_stop()
        self.assertEqual(saved[0]["rooms"], original)
        self.assertEqual(f.cooldown.snapshot()["rooms"], {})
        for timer in f.timers:
            timer.callback()
        self.assertEqual(f.recalculations, 0)


def delivery_class():
    """Compile the real transport method, replacing only its external edges."""
    tree = ast.parse((SOURCE / "manager.py").read_text())
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                 and any(isinstance(method, ast.AsyncFunctionDef)
                         and method.name == "async_announce" for method in node.body))
    method = next(method for method in owner.body if isinstance(method, ast.AsyncFunctionDef)
                  and method.name == "async_announce")

    def stage(hass, name):
        hass.events.append(name)
        if hass.hook is not None:
            hass.hook(name)

    async def rewrite(hass, rec, message, language, agent):
        stage(hass, "ai")
        return message

    async def notify(hass, domain, service, data, **kwargs):
        stage(hass, domain + "." + service)
        if domain == "notify" and hass.fail_notify:
            raise RuntimeError("Simulated output failure")

    async def hub(hass, payload):
        stage(hass, "hub")
        return True

    async def persistent(hass, *args):
        stage(hass, "persistent_notification")
        return True

    scope = {**vars(const), "Any": Any,
             "_LOGGER": logging.getLogger("hem.b10.delivery"),
             "delivery_allowed": lambda hass: True,
             "announcement": lambda rec, language: ("HEM", rec.action),
             "ai_effectively_enabled": lambda settings: settings.get("ai_rewrite", False),
             "DEFAULT_AGENT": "default",
             "hub_available": lambda hass: hass.hub_ready,
             "make_hub_payload": lambda *args, **kwargs: {},
             "async_submit_hub": hub, "async_system_notification": persistent,
             "async_call_notification": notify,
             "async_rewrite_announcement": rewrite,
             "tts_language": lambda *args, **kwargs: "en"}
    cls = ast.ClassDef(name="DeliveryManager", bases=[], keywords=[], body=[method], decorator_list=[])
    future = ast.parse("from __future__ import annotations").body[0]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, cls], type_ignores=[])),
                 str(SOURCE / "manager.py"), "exec"), scope)
    return scope["DeliveryManager"]


DeliveryManager = delivery_class()


def delivery_fixture(*, use_ai=False, use_hub=False):
    f = Fixture()
    f.prepare(raw_plan(room()))
    # Keep a CLOSE work item while the contact event/refresh is still pending.
    # Its delayed transport must recheck the actual opening grace, even before
    # the asynchronous plan refresh has replaced this old work item.
    f.manager.raw = raw_plan(room(states=(True,)))
    f.manager.plan = f.manager.raw
    f.manager.settings.update({
        const.CONF_AUTO_NOTIFY: True, const.CONF_AUTO_TTS: True,
        const.CONF_TTS_ENGINE: "tts.test", const.CONF_MEDIA_PLAYERS: ["media_player.test"],
        const.CONF_NOTIFY_TARGETS: ["notify.test"], const.CONF_HUB: use_hub,
        "ai_rewrite": use_ai,
    })
    f.manager.hass.events = []
    f.manager.hass.hook = None
    f.manager.hass.hub_ready = use_hub
    f.manager.hass.fail_notify = False
    f.manager.hass.services = N(has_service=lambda domain, service: True)
    f.manager.get_language = lambda language: "en"
    f.manager._targets_in_room = lambda targets, area: list(targets)
    f.manager.async_announce = DeliveryManager.async_announce.__get__(f.manager)
    return f


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_manual_and_automatic_output_routes_respect_active_grace(self):
        for use_hub in (False, True):
            for channels in ("auto", "both", "tts", "notification"):
                with self.subTest(use_hub=use_hub, channels=channels):
                    f = delivery_fixture(use_hub=use_hub)
                    f.transition()
                    result = await f.manager.async_announce(channels=channels)
                    self.assertEqual(result["submitted"], 0)
                    self.assertEqual(f.manager.hass.events, [])

    async def test_opening_while_ai_is_waiting_prevents_stale_close_output(self):
        f = delivery_fixture(use_ai=True)
        f.manager.hass.hook = lambda stage: f.transition() if stage == "ai" else None
        result = await f.manager.async_announce(channels="both")
        self.assertEqual(result, {"submitted": 0, "errors": []})
        self.assertEqual(f.manager.hass.events, ["ai"])

    async def test_opening_between_direct_outputs_prevents_following_tts(self):
        f = delivery_fixture()
        f.manager.hass.hook = lambda stage: f.transition() if stage == "notify.send_message" else None
        result = await f.manager.async_announce(channels="both")
        self.assertEqual(result["submitted"], 1)
        self.assertEqual(f.manager.hass.events, ["notify.send_message"])

    async def test_failed_first_output_cannot_fall_back_with_a_stale_close(self):
        f = delivery_fixture()
        f.manager.hass.fail_notify = True
        f.manager.hass.hook = lambda stage: f.transition() if stage == "notify.send_message" else None
        result = await f.manager.async_announce(channels="both")
        self.assertEqual(result["submitted"], 0)
        self.assertEqual(f.manager.hass.events, ["notify.send_message"])

    async def test_dispatch_boundary_expiry_refreshes_evidence_before_announcement(self):
        f = delivery_fixture()
        f.transition()
        f.manager.raw = raw_plan(room(states=(True,), co2=400), bad_weather=False)
        f.now += 301
        result = await f.manager.async_announce(channels="both")
        self.assertEqual(f.recalculations, 1)
        self.assertEqual(f.manager.plan.status, "idle")
        self.assertEqual(result["submitted"], 0)
        self.assertEqual(f.manager.hass.events, [])

    async def test_current_close_without_grace_still_reaches_configured_outputs(self):
        f = delivery_fixture()
        result = await f.manager.async_announce(channels="both")
        self.assertEqual(result, {"submitted": 2, "errors": []})
        self.assertEqual(f.manager.hass.events, ["notify.send_message", "tts.speak"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
