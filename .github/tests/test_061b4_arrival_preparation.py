"""Arrival preparation uses a durable deadline and current physical authority.

The real arrival state machine, live presence policy and equipment model run
against simulated HA state, storage and timer transport. Native dispatch cases
also execute the existing production journal/recheck and dwell machinery. No
Home Assistant instance, physical device or service acknowledgement is faked.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as N
import unittest


ROOT = Path(__file__).resolve().parents[2]
timing = runpy.run_path(str(Path(__file__).with_name("test_061b1_operating_timing.py")))
away = runpy.run_path(str(Path(__file__).with_name("test_beta121_away_profile.py")))
fixture = away["fixture"]
PACKAGE, model = away["package"], away["model"]
arrival = importlib.import_module(PACKAGE + ".arrival_preparation")
occupancy = fixture["occupancy"]
PERSON, ROOMS, AREA = (fixture[key] for key in ("PERSON", "ROOMS", "AREA"))
sys.modules[PACKAGE + ".equipment_model"] = model
activation = importlib.import_module(PACKAGE + ".device_activation")
# Restore real presence/model reads in the transport-only native fixture.
# Both package aliases resolve the same entry registry and actual policy.
sys.modules[timing["PACKAGE"] + ".arrival_preparation"] = arrival
sys.modules[timing["PACKAGE"] + ".occupancy_policy"] = occupancy
timing["model"].plan_for = model.plan_for
timing["production"].live_device_permission = occupancy.live_device_permission


class HomeAssistantError(RuntimeError):
    pass


fixture["module"]("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
fixture["module"]("homeassistant.core", callback=lambda function: function)
fixture["module"]("homeassistant.helpers.dispatcher",
                  async_dispatcher_send=lambda *args: None,
                  async_dispatcher_connect=lambda *args: lambda: None)
fixture["module"]("homeassistant.helpers.entity_registry",
                  async_get=lambda hass: hass.entity_registry)


class Entity:
    @property
    def extra_state_attributes(self):
        return {}

    def async_write_ha_state(self):
        self.writes = getattr(self, "writes", 0) + 1


fixture["module"]("homeassistant.components", __path__=[])
fixture["module"]("homeassistant.components.button", ButtonEntity=Entity)
fixture["module"]("homeassistant.components.number", NumberEntity=Entity, NumberMode=N(BOX="box"))
fixture["module"]("homeassistant.helpers.entity", Entity=Entity, EntityCategory=N(CONFIG="config"))
# The actual platforms are loaded whole; unrelated optional mold calibration
# does not participate in these new global controls.
fixture["module"](PACKAGE + ".mold_controls", async_recalculate_mold_factor=None)
buttons = importlib.import_module(PACKAGE + ".button")
numbers = importlib.import_module(PACKAGE + ".number")
groups = importlib.import_module(PACKAGE + ".room_hubs")

# The legacy thermostat path runs its complete room planner, arbitration and
# native driver. Only HA registry/state/temperature transport is supplied here;
# its target, presence, ownership, ACK and command decisions remain production.
LEGACY_PACKAGE = "hem_arrival_legacy"
fixture["module"](LEGACY_PACKAGE, __path__=[str(ROOT)])
fixture["module"](
    LEGACY_PACKAGE + ".discovery",
    entity_area=lambda hass, entity: hass.entity_areas.get(entity),
    _device_class=lambda hass, state: state.attributes.get("device_class", ""),
    temperature_sensor_c=lambda hass, entity, minutes: float(hass.states.get(entity).state)
    if hass.states.get(entity) is not None and hass.states.get(entity).state not in
    ("unknown", "unavailable") else None,
    is_stale=lambda state, minutes: not occupancy._fresh(state, minutes),
    is_window=lambda hass, state: state.attributes.get("device_class") == "window",
    reading=lambda *args, **kwargs: None,
)
legacy_rooms = importlib.import_module(LEGACY_PACKAGE + ".climate_rooms")
legacy_arbitration = importlib.import_module(LEGACY_PACKAGE + ".climate_arbitration")
legacy_native = importlib.import_module(LEGACY_PACKAGE + ".climate_native")


class Registry:
    def __init__(self):
        self.entities = {}

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

    def async_get_entity_id(self, domain, platform, unique_id):
        return next((entity_id for entity_id, record in self.entities.items()
                     if entity_id.partition(".")[0] == domain
                     and record.platform == platform and record.unique_id == unique_id), None)


class Store:
    """Controlled I/O transport: storage completion does not grant authority."""

    def __init__(self, saved=None):
        self.saved = deepcopy(saved)
        self.writes = []
        self.fail_save = False
        self.fail_load = False
        self.block_next = False
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.after_save = None

    async def async_load(self):
        if self.fail_load:
            raise OSError("fixture read failure")
        return deepcopy(self.saved)

    async def async_save(self, snapshot):
        value = deepcopy(snapshot)
        self.writes.append(value)
        if self.block_next:
            self.block_next = False
            self.entered.set()
            await self.release.wait()
        if self.fail_save:
            raise OSError("fixture write failure")
        self.saved = value
        if self.after_save is not None:
            self.after_save()


class Timers:
    def __init__(self, clock):
        self.clock = clock
        self.entries = []

    def __call__(self, hass, delay, callback):
        timer = N(deadline=self.clock() + delay, delay=delay,
                  callback=callback, cancelled=False)
        self.entries.append(timer)

        def cancel():
            timer.cancelled = True

        return cancel

    def fire(self, timer):
        # Deliberately allow an already-queued cancelled callback to run.
        timer.callback(None)


class Context:
    def __init__(self, *, entry_id="entry", saved=None, timeout=60):
        self.source = away["AwayProfileTests"]()
        self.source.setUp()
        self.hass, self.manager = self.source.hass, self.source.manager
        self.manager.entry = N(entry_id=entry_id)
        self.manager._active = True
        self.manager.settings["arrival_preparation_timeout_minutes"] = timeout
        self.hass.data = {}
        self.hass.entity_registry = Registry()
        self.tasks = set()
        self.hass.async_create_task = self.create_task
        self.recalculations = []
        self.manager._recalculate = self.recalculate
        self.now = 2_000_000_000.0
        self.store = Store(saved)
        self.timers = Timers(lambda: self.now)
        self.helper = self.make_helper()

    def create_task(self, coro, *args, **kwargs):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def recalculate(self, **kwargs):
        self.recalculations.append(self.now)

    def make_helper(self):
        helper = arrival.ArrivalPreparation(
            self.manager, store=self.store, clock=lambda: self.now,
            schedule=self.timers,
        )
        self.manager.arrival_preparation = helper
        return helper

    async def start(self):
        await self.helper.async_start()
        return self

    async def settle(self):
        while self.tasks:
            await asyncio.gather(*tuple(self.tasks))

    def presence(self, state, **kwargs):
        self.hass.put(PERSON, state, **kwargs)

    def plan(self):
        return model.plan_for(self.manager, self.source.spec)

    def profile(self):
        plan = self.plan()
        cfg = model.settings(self.manager, self.source.spec)
        return model.profile_name(cfg, plan)


class ArrivalCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.contexts = []

    async def context(self, **kwargs):
        context = await Context(**kwargs).start()
        self.contexts.append(context)
        return context

    async def asyncTearDown(self):
        for context in self.contexts:
            await context.helper.async_stop()
            await context.settle()


class DeadlineTests(ArrivalCase):
    async def test_prepare_uses_home_targets_without_changing_presence_or_settings(self):
        context = await self.context()
        settings = deepcopy(context.manager.settings)
        cached = deepcopy(context.source.cached)
        self.assertEqual(context.profile(), "away")
        await context.helper.async_prepare()
        snapshot = context.helper.snapshot()
        self.assertTrue(snapshot["active"])
        self.assertEqual(snapshot["expires_at"], context.now + 3600)
        self.assertEqual(snapshot["timeout_minutes"], 60)
        self.assertEqual(snapshot["home_status"], "away")
        self.assertTrue(context.helper.active_for("away"))
        plan = context.plan()
        self.assertEqual((plan["away"], plan["occupancy"]), ("away", "unoccupied"))
        self.assertEqual(context.profile(), "home")
        self.assertEqual(context.source.evaluate()[2], 21.0)
        self.assertEqual(context.manager.settings, settings)
        self.assertEqual(context.source.cached, cached)
        self.assertTrue(context.store.writes)

    async def test_home_unknown_and_restored_inputs_cannot_start_preparation(self):
        for state, attributes in (
            ("home", {}), ("unknown", {}), ("unavailable", {}),
            ("not_home", {"restored": True}),
        ):
            with self.subTest(state=state, attributes=attributes):
                context = await self.context()
                context.presence(state, attributes=attributes)
                try:
                    await context.helper.async_prepare()
                except HomeAssistantError:
                    pass
                self.assertFalse(context.helper.active_for("away"))
                self.assertFalse(context.helper.snapshot()["active"])

    async def test_renew_extends_deadline_and_old_callback_cannot_end_new_request(self):
        context = await self.context(timeout=2)
        await context.helper.async_prepare()
        first = context.timers.entries[-1]
        context.now += 60
        await context.helper.async_prepare()
        renewed = context.helper.snapshot()["expires_at"]
        self.assertEqual(renewed, context.now + 120)
        self.assertTrue(first.cancelled)
        context.now = first.deadline
        context.timers.fire(first)
        await context.settle()
        self.assertTrue(context.helper.active_for("away"))
        self.assertEqual(context.helper.snapshot()["expires_at"], renewed)

    async def test_deadline_expires_without_waiting_for_timer_and_returns_away_targets(self):
        context = await self.context(timeout=1)
        await context.helper.async_prepare()
        context.now += 60
        self.assertFalse(context.helper.active_for("away"))
        self.assertEqual(context.profile(), "away")
        self.assertEqual(context.source.evaluate()[2], 10.0)
        context.timers.fire(context.timers.entries[-1])
        await context.settle()
        self.assertFalse(context.helper.snapshot()["active"])
        restored = await self.context(saved=context.store.saved)
        self.assertFalse(restored.helper.active_for("away"))

    async def test_actual_arrival_ends_override_and_does_not_rearm_on_later_departure(self):
        context = await self.context()
        await context.helper.async_prepare()
        context.presence("home")
        context.hass.put(ROOMS, '["living"]')
        context.helper.observe("home")
        await context.settle()
        self.assertFalse(context.helper.snapshot()["active"])
        self.assertEqual(context.profile(), "comfort")
        context.presence("not_home")
        context.hass.put(ROOMS, "[]")
        self.assertFalse(context.helper.active_for("away"))
        self.assertEqual(context.profile(), "away")
        restored = await self.context(saved=context.store.saved)
        self.assertFalse(restored.helper.active_for("away"))

    async def test_restart_preserves_absolute_deadline_and_unknown_presence_holds_authority(self):
        context = await self.context(timeout=30)
        await context.helper.async_prepare()
        deadline = context.helper.snapshot()["expires_at"]
        context.now += 300
        await context.helper.async_stop()
        context.presence("unknown")
        context.helper = context.make_helper()
        await context.helper.async_start()
        self.assertEqual(context.helper.snapshot()["expires_at"], deadline)
        self.assertFalse(context.helper.active_for("unknown"))
        plan = context.plan()
        self.assertEqual(plan["away"], "unknown")
        self.assertFalse(plan.get("arrival_preparing", False))
        self.assertEqual(model.automatic_profile_reason(
            model.settings(context.manager, context.source.spec), plan,
        ), "house_occupancy_unknown")
        context.presence("not_home")
        self.assertTrue(context.helper.active_for("away"))
        self.assertEqual(context.helper.snapshot()["expires_at"], deadline)
        self.assertEqual(context.profile(), "home")

    async def test_prepare_write_failure_cannot_publish_home_authority(self):
        context = await self.context()
        context.store.fail_save = True
        try:
            await context.helper.async_prepare()
        except (OSError, HomeAssistantError):
            pass
        self.assertFalse(context.helper.active_for("away"))
        self.assertEqual(context.profile(), "away")
        context.store.fail_save = False

    async def test_arrival_during_prepare_save_cannot_publish_stale_home_override(self):
        context = await self.context()
        context.store.block_next = True
        prepare = asyncio.create_task(context.helper.async_prepare())
        await asyncio.wait_for(context.store.entered.wait(), 2)
        self.assertFalse(context.helper.active_for("away"))
        context.presence("home")
        context.helper.observe("home")
        context.store.release.set()
        await prepare
        await context.settle()
        self.assertFalse(context.helper.snapshot()["active"])
        restored = await self.context(saved=context.store.saved)
        self.assertFalse(restored.helper.active_for("away"))

    async def test_cancel_invalidates_in_flight_prepare_before_waiting_for_storage(self):
        context = await self.context()
        context.store.block_next = True
        prepare = asyncio.create_task(context.helper.async_prepare())
        await asyncio.wait_for(context.store.entered.wait(), 2)
        cancel = asyncio.create_task(context.helper.async_cancel())
        await asyncio.sleep(0)
        self.assertFalse(context.helper.active_for("away"))
        context.store.release.set()
        await asyncio.gather(prepare, cancel)
        await context.settle()
        self.assertFalse(context.helper.snapshot()["active"])
        restored = await self.context(saved=context.store.saved)
        self.assertFalse(restored.helper.active_for("away"))

    async def test_aborted_renewal_keeps_original_expiry_timer_effective(self):
        context = await self.context(timeout=2)
        await context.helper.async_prepare()
        timer = context.timers.entries[-1]
        deadline = context.helper.snapshot()["expires_at"]
        context.now += 30
        context.store.block_next = True
        renewal = asyncio.create_task(context.helper.async_prepare())
        await asyncio.wait_for(context.store.entered.wait(), 2)
        context.presence("unknown")
        context.helper.observe("unknown")
        context.store.release.set()
        await renewal
        self.assertEqual(context.helper.snapshot()["expires_at"], deadline)
        context.now = deadline
        context.timers.fire(timer)
        await context.settle()
        self.assertIsNone(context.helper.expires_at)
        self.assertIsNone(context.store.saved["expires_at"])

    async def test_unload_cancels_timer_but_preserves_original_deadline(self):
        context = await self.context()
        await context.helper.async_prepare()
        deadline = context.helper.snapshot()["expires_at"]
        timer = context.timers.entries[-1]
        await context.helper.async_stop()
        self.assertTrue(timer.cancelled)
        context.timers.fire(timer)
        await context.settle()
        self.assertFalse(context.helper.active_for("away"))
        context.now += 120
        context.helper = context.make_helper()
        await context.helper.async_start()
        self.assertTrue(context.helper.active_for("away"))
        self.assertEqual(context.helper.snapshot()["expires_at"], deadline)

    async def test_expired_malformed_or_failed_storage_cannot_resume_preparation(self):
        now = 2_000_000_000.0
        for saved in (
            {"started_at": now - 120, "expires_at": now},
            {"started_at": now + 1, "expires_at": now + 60},
            {"started_at": now - 1, "expires_at": now + 86400},
            {"started_at": True, "expires_at": now + 60},
            {"started_at": now - 1, "expires_at": "NaN"},
            {"expires_at": now + 60},
        ):
            with self.subTest(saved=saved):
                context = await self.context(saved=saved)
                self.assertFalse(context.helper.active_for("away"))
                self.assertEqual(context.profile(), "away")
        context = Context(saved={"started_at": now - 1, "expires_at": now + 60})
        self.contexts.append(context)
        context.store.fail_load = True
        with self.assertLogs(arrival.__name__, level="ERROR"):
            await context.start()
        self.assertFalse(context.helper.active_for("away"))


class PolicyTests(ArrivalCase):
    def effective_device(self, context, *, requirement="occupied", power=True, **config):
        spec = context.source.spec
        context.source.room.update(enabled=True, allow_actuation=True,
                                   selected_devices=list(spec.source_entities))
        context.hass.put(spec.source_entities[0], "off", area=AREA, attributes={
            "hvac_modes": ["off", "heat"], "supported_features": 1,
            "temperature": 10.0, "min_temp": 5.0, "max_temp": 35.0,
            "target_temp_step": 0.5, "temperature_unit": "°C",
        })
        context.source.room["device_settings"] = {
            spec.source_entities[0]: {"auto_control": True, "sleep_behavior": "normal",
                                      "fan_purpose": "extraction", "hardware_confirmed": True,
                                      "method": "native" if power else "setpoint"},
        }
        saved = context.manager.settings[model.SETTINGS][spec.identifier]
        saved.update(presence_requirement=requirement, **config)
        return activation.effective_device(context.manager, spec, spec.source_entities[0])

    def permission(self, context, device, plan=None):
        return occupancy.live_device_permission(
            context.hass, AREA, context.source.room,
            context.plan() if plan is None else plan, device,
        )

    async def test_preparation_allows_empty_room_without_fabricating_room_presence(self):
        context = await self.context()
        device = self.effective_device(context)
        self.assertEqual(self.permission(context, device), ("held", "room_not_occupied"))
        await context.helper.async_prepare()
        self.assertEqual(self.permission(context, device), ("eligible", "preparing_for_arrival"))
        self.assertEqual(context.plan()["occupancy"], "unoccupied")
        # A source failure is a hold, even with the old active plan in hand.
        plan = context.plan()
        context.presence("unknown")
        self.assertEqual(self.permission(context, device, plan)[0], "held")
        self.assertFalse(context.plan()["arrival_preparing"])
        context.presence("not_home")
        self.assertEqual(self.permission(context, device)[0], "eligible")

    async def test_explicit_modes_and_presets_never_inherit_preparation_permission(self):
        context = await self.context()
        await context.helper.async_prepare()
        active_plan = context.plan()
        for mode, preset in (("manual", "none"), ("off", "none"),
                             ("existing", "none"), ("automatic", "away"),
                             ("pid", "home"), ("pid", "sleep")):
            with self.subTest(mode=mode, preset=preset):
                device = self.effective_device(context, control_mode=mode, preset=preset)
                plan = context.plan()
                self.assertFalse(plan["arrival_preparing"])
                self.assertEqual(self.permission(context, device, plan)[0], "held")
                self.assertEqual(self.permission(context, device, active_plan)[0], "held")
                if preset != "none":
                    self.assertEqual(context.profile(), preset)

    async def test_disabled_control_sleep_pause_and_absent_only_keep_their_policies(self):
        context = await self.context()
        await context.helper.async_prepare()
        device = self.effective_device(context, requirement="absent")
        self.assertEqual(self.permission(context, device), ("eligible", "device_policy_approved"))
        device["auto_control"] = False
        self.assertEqual(self.permission(context, device), ("held", "device_auto_control_disabled"))
        self.assertEqual(occupancy.device_permission(
            {"auto_control": True, "presence_requirement": "occupied", "sleep_behavior": "pause"},
            "unoccupied", "away", True, preparing_arrival=True,
        ), ("held", "sleep_room_control_paused"))

    async def test_legacy_and_managed_setpoint_only_controls_keep_presence_restriction(self):
        context = await self.context()
        await context.helper.async_prepare()
        setpoint_only = self.effective_device(context, power=False)
        self.assertEqual(model.permission(context.manager, context.source.spec, context.source.cap),
                         (True, False))
        self.assertEqual(context.profile(), "home")
        self.assertEqual(self.permission(context, setpoint_only), ("held", "room_not_occupied"))
        for requirement in ("occupied", "home", "room"):
            legacy = {"auto_control": True, "sleep_behavior": "normal",
                      "presence_requirement": requirement}
            self.assertNotEqual(self.permission(context, legacy)[0], "eligible")
        legacy["presence_requirement"] = "always"
        self.assertEqual(self.permission(context, legacy)[0], "eligible")
        native = self.effective_device(context, power=True)
        self.assertEqual(self.permission(context, native), ("eligible", "preparing_for_arrival"))

    async def test_stale_deadline_cancel_and_other_entry_cannot_borrow_permission(self):
        context = await self.context(timeout=2)
        device = self.effective_device(context)
        await context.helper.async_prepare()
        old = context.plan()
        context.now += 30
        await context.helper.async_prepare()
        self.assertEqual(self.permission(context, device, old),
                         ("held", "arrival_preparation_changed"))
        plan = context.plan()
        other = {**device, "_arrival_preparation_entry_id": "other-entry"}
        self.assertEqual(self.permission(context, other, plan),
                         ("held", "arrival_preparation_changed"))
        await context.helper.async_cancel()
        self.assertEqual(self.permission(context, device, plan),
                         ("held", "arrival_preparation_changed"))
        self.assertEqual(self.permission(context, device), ("held", "room_not_occupied"))

    async def test_entity_registry_resolves_renamed_ids_only_for_exact_entry(self):
        context = await self.context()
        for role, (domain, suffix) in arrival.ENTITY_SUFFIXES.items():
            entity = f"{domain}.my_renamed_{role}"
            context.hass.entity_registry.entities[entity] = N(
                platform=arrival.DOMAIN, config_entry_id="entry", unique_id=f"entry_{suffix}",
            )
        self.assertEqual(context.helper.snapshot()["entity_ids"], {
            role: f"{domain}.my_renamed_{role}"
            for role, (domain, _) in arrival.ENTITY_SUFFIXES.items()
        })
        context.hass.entity_registry.entities["button.my_renamed_prepare"].config_entry_id = "other"
        self.assertIsNone(context.helper.snapshot()["entity_ids"]["prepare"])


class NativeEntityTests(ArrivalCase):
    def controls(self, context):
        context.manager.entry.data = deepcopy(context.manager.settings)
        context.manager.entry.options = {}

        def update(entry, *, options):
            entry.options = deepcopy(options)
            context.manager.settings = {**entry.data, **entry.options}

        context.hass.config_entries = N(async_update_entry=update)
        context.manager._device_hierarchy = {
            "device_subentries": {"entry": "home-subentry", "entry_area_living": "room-subentry"},
        }
        return (buttons.ArrivalPreparationButton(context.manager, "prepare"),
                buttons.ArrivalPreparationButton(context.manager, "cancel"),
                numbers.ArrivalPreparationTimeoutNumber(context.manager))

    async def test_controls_share_exact_home_hub_and_native_actions_control_same_episode(self):
        context = await self.context()
        prepare, cancel, timeout = self.controls(context)
        controls = (prepare, cancel, timeout)
        self.assertEqual([entity._attr_unique_id for entity in controls], [
            "entry_prepare_for_arrival", "entry_cancel_arrival_preparation",
            "entry_arrival_preparation_timeout",
        ])
        for control in controls:
            self.assertEqual(control._attr_device_info["identifiers"], {(arrival.DOMAIN, "entry")})
            self.assertEqual(control.extra_state_attributes["entry_id"], "entry")
            self.assertTrue(control.extra_state_attributes.get("configuration_help"))
        batches = []
        groups.async_add_grouped_entities(
            context.manager, lambda entities, **options: batches.append((tuple(entities), options)), controls,
        )
        self.assertEqual(batches, [(controls, {"config_subentry_id": "home-subentry"})])
        self.assertTrue(prepare.available)
        self.assertFalse(cancel.available)
        await prepare.async_press()
        self.assertTrue(cancel.available)
        self.assertEqual(context.profile(), "home")
        context.presence("unknown")
        self.assertFalse(prepare.available)
        self.assertTrue(cancel.available, "An armed episode remains cancellable while presence is unknown")
        await cancel.async_press()
        self.assertFalse(cancel.available)
        self.assertFalse(context.helper.armed)

    async def test_timeout_writer_validates_range_and_only_changes_next_press(self):
        context = await self.context()
        prepare, cancel, timeout = self.controls(context)
        self.assertEqual((timeout._attr_native_min_value, timeout._attr_native_max_value,
                          timeout._attr_native_step, timeout._attr_native_unit_of_measurement),
                         (1, 1440, 1, "min"))
        self.assertEqual(timeout.native_value, 60)
        before = deepcopy(context.manager.settings)
        await prepare.async_press()
        deadline = context.helper.expires_at
        await timeout.async_set_native_value(90)
        self.assertEqual(context.manager.entry.options, {arrival.CONF_TIMEOUT: 90})
        self.assertEqual(timeout.native_value, 90)
        self.assertEqual(context.helper.expires_at, deadline)
        self.assertEqual(context.manager.settings, {**before, arrival.CONF_TIMEOUT: 90})
        context.now += 10
        await prepare.async_press()
        self.assertEqual(context.helper.expires_at, context.now + 90 * 60)
        for value in (0, 1441, 1.5, True, "invalid", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(HomeAssistantError):
                await timeout.async_set_native_value(value)
        self.assertEqual(timeout.native_value, 90)
        for value in (1, 1440):
            await timeout.async_set_native_value(value)
            self.assertEqual(timeout.native_value, value)
        saved_deadline = context.helper.expires_at
        await context.helper.async_stop()
        context.helper = context.make_helper()
        await context.helper.async_start()
        self.assertEqual(context.helper.expires_at, saved_deadline)
        self.assertEqual(timeout.native_value, 1440)


class LegacyNativeTests(ArrivalCase):
    async def legacy(self, *, mode="heat"):
        context = await self.context(timeout=1)
        entity = context.source.spec.source_entities[0]
        sensor = "sensor.legacy_temperature"
        context.hass.put(sensor, "20" if mode == "heat" else "26", area=AREA)
        state = context.hass.put(entity, mode, area=AREA, attributes={
            "hvac_modes": ["off", "heat", "cool"], "supported_features": 1,
            "temperature": 20.5 if mode == "heat" else 25.5,
            "min_temp": 5.0, "max_temp": 35.0, "target_temp_step": 0.5,
            "temperature_unit": "°C", "hvac_action": "idle",
        })
        context.manager.settings[model.SETTINGS] = {}
        cfg = context.source.room
        cfg.update(
            enabled=True, allow_actuation=True, controller="device", mode="auto",
            climate_entity=entity, temperature_entity=sensor, auto_switch_hvac=True,
            selected_devices=[entity], prefer_native_auto=False,
            profiles={"home": {"heat_c": 21.0, "cool_c": 25.0},
                      "away": {"heat_c": 19.0, "cool_c": 27.0}},
            device_settings={entity: {
                "auto_control": True, "presence_requirement": "always",
                "sleep_behavior": "normal", "method": "setpoint",
            }},
        )
        calls = []

        async def call(domain, service, data, **kwargs):
            calls.append((domain, service, deepcopy(data), deepcopy(kwargs)))

        context.hass.services = N(has_service=lambda *args: True, async_call=call)
        driver = legacy_native.NativeClimateControl(
            context.hass, "entry", clock=lambda: context.now,
        )
        driver._active = driver.ready = True
        driver.started = context.now - 600
        driver._store = fixture["Store"]()
        return context, cfg, state, driver, calls

    def report(self, context, cfg):
        shared = context.manager.presence_continuity.context(
            context.manager.settings["occupancy_global"],
        )
        report, _ = legacy_rooms.gather(
            context.hass, N(area_id=AREA, readings=(), windows=()), cfg,
            global_presence=shared, known_areas={AREA}, now=context.now,
            arrival_preparation=context.helper.context(
                context.helper.home_status(), eligible=arrival.room_eligible(cfg),
            ),
        )
        report["coordination"] = legacy_arbitration.room_coordination(
            context.hass, AREA, cfg, report, now=context.now,
        )
        return report

    async def tick(self, context, cfg, driver, report=None):
        report = self.report(context, cfg) if report is None else report
        driver.schedule({AREA: cfg}, {AREA: report})
        await context.settle()
        return report

    async def test_legacy_native_restores_away_target_in_deadband_without_power_or_mode_change(self):
        for mode, home, away, direction in (("heat", 21., 19., -1), ("cool", 25., 27., 1)):
            with self.subTest(mode=mode):
                context, cfg, state, driver, calls = await self.legacy(mode=mode)
                await context.helper.async_prepare()
                report = await self.tick(context, cfg, driver)
                self.assertEqual(report["profile"], "home")
                self.assertEqual([call[2] for call in calls], [{"temperature": home}])
                self.assertNotEqual(state.attributes["temperature"], home,
                                    "Service completion cannot fabricate native acknowledgement")
                self.assertEqual(driver.expected[AREA]["temperature"], home)
                state.attributes["temperature"] = home  # Actual native report.
                context.now += 60
                report = await self.tick(context, cfg, driver)
                self.assertEqual((report["profile"], report["temperature_target_c"]), ("away", away))
                self.assertEqual(len(calls), 1, "Expiry retains the existing native write interval")
                context.now += 240
                for step in range(1, 5):
                    await self.tick(context, cfg, driver)
                    expected = home + direction * .5 * step
                    self.assertEqual(calls[-1][2], {"temperature": expected})
                    self.assertEqual(len(calls), step + 1)
                    state.attributes["temperature"] = expected
                    context.now += 300
                self.assertEqual(state.attributes["temperature"], away)
                self.assertEqual(state.state, mode)
                self.assertEqual(context.helper.home_status(), "away")
                self.assertFalse(driver.paused)
                self.assertTrue(all(call[:2] == ("climate", "set_temperature") for call in calls))

    async def test_deadband_target_maintenance_cannot_switch_a_changed_native_mode(self):
        for changed in ("off", "cool", "fan_only"):
            with self.subTest(changed=changed):
                context, cfg, state, driver, calls = await self.legacy()
                report = self.report(context, cfg)
                self.assertEqual(report["reason"], "native_profile_setpoint_within_deadband")
                self.assertEqual(report["mode"], "heat")
                state.state = changed
                await self.tick(context, cfg, driver, report)
                self.assertEqual(calls, [])
                self.assertEqual(state.state, changed)
                self.assertNotIn(AREA, driver.expected_hvac)

    async def test_deadband_does_not_fabricate_secondary_demand_or_bypass_pause_or_explicit_off(self):
        for restriction in ("secondary", "paused", "off", "presence"):
            with self.subTest(restriction=restriction):
                context, cfg, state, driver, calls = await self.legacy()
                if restriction == "secondary":
                    cfg["heat_climate_entity"] = "climate.secondary"
                    context.hass.put("climate.secondary", "off", area=AREA,
                                     attributes=deepcopy(state.attributes))
                elif restriction == "paused":
                    driver.paused[AREA] = "user_paused"
                elif restriction == "off":
                    cfg["mode"] = "off"
                else:
                    cfg["device_settings"][state.entity_id]["presence_requirement"] = "occupied"
                report = await self.tick(context, cfg, driver)
                self.assertEqual(calls, [])
                if restriction == "secondary":
                    self.assertEqual(report["mode"], "off")
                    self.assertEqual(report["equipment_plan"]["thermal"]["status"], "no_thermal_demand")


class NativeRuntime(timing["TimingRuntime"]):
    """Actual native decisions with real arrival/presence/profile selection."""

    def __init__(self, *, method="automatic", off_age=1200, timeout=60):
        super().__init__(profile={"control_mode": method, "presence_requirement": "occupied"},
                         off_age=off_age)
        self.source = fixture["Hass"]()
        self.source.put(PERSON, "not_home")
        self.source.put(ROOMS, "[]")
        self.hass.states = self.source.states
        self.state.entity_id = timing["PRIMARY"]
        self.hass.states.data[timing["PRIMARY"]] = self.state
        self.hass.config = self.source.config
        self.hass.entity_areas = self.source.entity_areas
        self.hass.entity_areas[timing["PRIMARY"]] = timing["SPEC"].area_id
        room = N(id="room", name="Room", aliases=())
        self.hass.areas = N(async_get_area=lambda key: room if key == "room" else None,
                            async_list_areas=lambda: [room])
        self.hass.data = {}
        self.hass.entity_registry = Registry()
        self.hass.entity_registry.entities[timing["PRIMARY"]] = N(
            entity_id=timing["PRIMARY"], platform="native_fixture", device_id="thermostat",
            id="native-record", unique_id="native-heater", config_entry_id="native-entry",
        )
        self.tasks = set()
        self.hass.async_create_task = self.create_task
        shared = {"home_trackers": [PERSON], "occupied_rooms_entity": ROOMS,
                  "source_stale_minutes": 240}
        self.manager.entry.data["occupancy_global"] = shared
        self.manager.entry.data[arrival.CONF_TIMEOUT] = timeout
        self.manager.entry.data["climate_rooms"]["room"]["profiles"]["away"] = {
            "heat_c": 10.0, "cool_c": 30.0, "humidity": 60.0,
        }
        self.manager.plan = N(environment={"room": {"climate_plan": {
            "status": "ready", "away": "away", "occupancy": "unoccupied", "sleeping": False,
            "window_safe": True, "global_presence": shared, "known_presence_areas": ["room"],
        }}})
        self.manager.presence_continuity = fixture["continuity"].PresenceContinuity(
            self.hass, "test_entry", store=fixture["Store"](),
        )
        self.manager._active = True
        self.manager._recalculate = lambda **kwargs: None
        self.store = Store()
        self.timers = Timers(self.clock)
        self.helper = arrival.ArrivalPreparation(
            self.manager, store=self.store, clock=self.clock, schedule=self.timers,
        )
        self.manager.arrival_preparation = self.helper
        self.after_persist = None

    def create_task(self, coro, *args, **kwargs):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def start(self):
        await self.helper.async_start()
        await self.helper.async_prepare()
        return self

    async def close(self):
        await self.helper.async_stop()
        while self.tasks:
            await asyncio.gather(*tuple(self.tasks))

    async def _save(self):
        await super()._save()
        if self.after_persist is not None:
            await self.after_persist(self)

    async def tick_once(self):
        await self.tick(timing["SPEC"])


class NativeDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtimes = []

    async def runtime(self, **kwargs):
        runtime = await NativeRuntime(**kwargs).start()
        self.runtimes.append(runtime)
        return runtime

    async def asyncTearDown(self):
        for runtime in self.runtimes:
            await runtime.close()

    async def test_preparation_does_not_bypass_off_dwell_or_invent_native_acknowledgement(self):
        runtime = await self.runtime(off_age=100)
        await runtime.tick_once()
        self.assertEqual(runtime.calls, [])
        self.assertIn("minimum_off_hold", [status for status, _ in runtime.statuses])
        runtime.now += 500
        await runtime.tick_once()
        self.assertEqual([call["data"] for call in runtime.calls], [{"hvac_mode": "heat"}])
        self.assertEqual(runtime.state.state, "off")
        self.assertFalse(runtime.record["power"])
        self.assertEqual(runtime.record["pending"]["phase"], "commanded")

    async def test_expiry_stops_owned_preparation_after_native_minimum_on_and_keeps_ack_required(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                runtime = await self.runtime(method=method, timeout=1)
                runtime.own_running(age=1)
                runtime.now += 60
                await runtime.tick_once()
                self.assertEqual(runtime.calls, [])
                self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")
                runtime.now += 539
                await runtime.tick_once()
                self.assertEqual([call["data"] for call in runtime.calls], [{"hvac_mode": "off"}])
                self.assertEqual(runtime.state.state, "heat")
                self.assertIn(timing["PRIMARY"], runtime.record["power"])
                runtime.report(mode="off")
                await runtime._reconcile(timing["SPEC"])
                self.assertFalse(runtime.record["power"])
                self.assertFalse(runtime.record["pending"])
                self.assertEqual(runtime.record["off_at"][timing["PRIMARY"]], runtime.now)

    async def test_unrestricted_setpoint_only_controller_restores_away_without_power_permission(self):
        for method in ("automatic", "pid"):
            with self.subTest(method=method):
                runtime = await self.runtime(method=method, timeout=1)
                room = runtime.manager.entry.data["climate_rooms"]["room"]
                room["profiles"]["away"]["heat_c"] = 19.0
                room["device_settings"][timing["PRIMARY"]]["method"] = "setpoint"
                saved = runtime.manager.entry.data[model.SETTINGS][timing["SPEC"].identifier]
                saved["presence_requirement"] = "always"
                runtime.report(mode="heat", temperature=20.5)
                runtime.measurement = 20.0
                self.assertEqual(timing["model"].permission(
                    runtime.manager, timing["SPEC"], runtime.cap), (True, False))
                await runtime.tick_once()
                self.assertEqual([call["data"] for call in runtime.calls], [{"temperature": 21.0}])
                runtime.report(temperature=21.0)
                await runtime._reconcile(timing["SPEC"])
                for target in (20.5, 20.0, 19.5, 19.0):
                    runtime.now += 300
                    await runtime.tick_once()
                    self.assertEqual(runtime.calls[-1]["data"], {"temperature": target})
                    runtime.report(temperature=target)
                    await runtime._reconcile(timing["SPEC"])
                self.assertEqual(len(runtime.calls), 5)
                self.assertTrue(all(call["service"] == "set_temperature" for call in runtime.calls))
                self.assertFalse(runtime.record["power"])
                self.assertFalse(runtime.record.get("paused"))
                self.assertEqual(runtime.state.state, "heat")

    async def test_expiry_cancel_or_unknown_during_command_yield_cannot_send_home_start(self):
        for method in ("automatic", "pid"):
            for stage in ("intent_save", "command_lock"):
                for change in ("expire", "cancel", "unknown"):
                    with self.subTest(method=method, stage=stage, change=change):
                        runtime = await self.runtime(method=method, timeout=1)
                        intent = asyncio.Event()

                        async def revoke():
                            if change == "expire":
                                runtime.now += 60
                            elif change == "cancel":
                                await runtime.helper.async_cancel()
                            else:
                                runtime.source.put(PERSON, "unknown")

                        async def after_save(controller):
                            if (controller.record.get("pending") or {}).get("phase") == "intent":
                                controller.after_persist = None
                                if stage == "intent_save":
                                    await revoke()
                                intent.set()

                        runtime.after_persist = after_save
                        if stage == "intent_save":
                            await runtime.tick_once()
                        else:
                            await runtime._commands.acquire()
                            task = asyncio.create_task(runtime.tick_once())
                            try:
                                await asyncio.wait_for(intent.wait(), 2)
                                await revoke()
                            finally:
                                runtime._commands.release()
                                await task
                        self.assertTrue(intent.is_set(), runtime.statuses)
                        self.assertEqual(runtime.calls, [], runtime.statuses)
                        self.assertFalse(runtime.record["pending"])
                        self.assertFalse(runtime.record.get("paused"))

    async def test_expiry_while_awaiting_mode_ack_cannot_retry_home_or_write_old_target(self):
        runtime = await self.runtime(timeout=1)
        runtime.manager.entry.data[model.SETTINGS][timing["SPEC"].identifier]["presence_requirement"] = "always"
        await runtime.tick_once()
        self.assertEqual([call["data"] for call in runtime.calls], [{"hvac_mode": "heat"}])
        runtime.now += 60
        await runtime.tick_once()
        self.assertEqual(len(runtime.calls), 1)
        runtime.report(mode="heat")
        await runtime._reconcile(timing["SPEC"])
        self.assertIn(timing["PRIMARY"], runtime.record["power"])
        runtime.now += 30  # Native startup target grace has also completed.
        await runtime._send(
            timing["SPEC"], runtime.cap, timing["PRIMARY"], "set_temperature",
            {"temperature": 35.0}, {"attributes": {"temperature": 35.0}},
            power=False, mode="heat", automatic=True,
        )
        self.assertEqual(len(runtime.calls), 1, "A late physical ACK cannot authorize the old Home target")
        self.assertEqual(runtime.state.state, "heat")
        await runtime._power(timing["SPEC"], runtime.cap, "off", automatic=True)
        self.assertEqual(len(runtime.calls), 1, "Expiry does not erase an acknowledged minimum ON hold")
        self.assertEqual(runtime.statuses[-1][0], "minimum_on_hold")

    async def test_preparation_still_obeys_window_manual_pause_and_native_defrost(self):
        for protection in ("window", "paused", "defrost"):
            with self.subTest(protection=protection):
                runtime = await self.runtime()
                if protection == "window":
                    runtime.window.update(blocked=True, status="window_pause_active")
                elif protection == "paused":
                    runtime.record["paused"] = "manual_override"
                else:
                    runtime.state.attributes["hvac_action"] = "defrosting"
                await runtime.tick_once()
                self.assertEqual(runtime.calls, [], runtime.statuses)
                self.assertFalse(runtime.record["power"])


if __name__ == "__main__":
    unittest.main()
