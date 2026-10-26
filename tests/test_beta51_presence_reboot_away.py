"""Beta51: strict, restart-safe Away evidence and cooldown for every controller.

The checks use actual timestamps and a persisted Home Assistant Store analogue.
No native physical HVAC commands are issued by the presence calculations.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from test_discovery import FakeHass, MockState, adapter
from custom_components.environment_manager.occupancy_policy import (
    _after_away_cooldown, home_presence,
)
from custom_components.environment_manager.presence_continuity import (
    PresenceContinuity, source_signature,
)


def negative(entity: str, *, minutes: int = 11) -> MockState:
    domain = entity.partition(".")[0]
    value = (
        "not_home" if domain in ("person", "device_tracker") else
        "off" if domain == "binary_sensor" else
        "[]" if entity.endswith("rooms") else "0"
    )
    state = MockState(entity, value)
    state.last_changed = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return state


class FakeStore:
    def __init__(self):
        self.saved = None
        self.writes = []

    async def async_load(self):
        return dict(self.saved) if isinstance(self.saved, dict) else None

    def async_delay_save(self, snapshot, seconds):
        self.saved = snapshot()
        self.writes.append(("delay", seconds, self.saved))

    async def async_save(self, snapshot):
        self.saved = dict(snapshot)
        self.writes.append(("flush", 0, self.saved))


def test_all_negative_explicit_home_trackers_override_empty_room_cooldown(adapter):
    count = negative("number.users_at_home")
    tracker = negative("person.resident")
    empty = negative("sensor.occupied_rooms", minutes=1)
    empty.state = "[]"
    h = FakeHass([count, tracker, empty])
    cfg = {"home_trackers": [count.entity_id, tracker.entity_id],
           "occupied_rooms_entity": empty.entity_id,
           "away_cooldown_minutes": 30}
    assert home_presence(h, cfg)[:2] == ("away", "all_selected_home_trackers_away")
    # An independently confirmed resident at home always takes priority.
    count.state = "1"
    assert home_presence(h, cfg)[0] == "home"
    count.state = "0"
    tracker.state = "unavailable"
    assert home_presence(h, cfg)[0] == "unknown"
    tracker.state = "not_home"
    empty.state = "unavailable"
    assert home_presence(h, cfg)[0] == "unknown"


def test_room_only_absence_still_honors_new_cooldown(adapter):
    empty = negative("sensor.occupied_rooms", minutes=2)
    empty.state = "[]"
    room = negative("binary_sensor.living_presence", minutes=2)
    h = FakeHass([empty, room], {room.entity_id: "living"})
    cfg = {"occupied_rooms_entity": empty.entity_id,
           "room_occupancy_sensors": [room.entity_id],
           "away_cooldown_minutes": 10}
    assert home_presence(h, cfg) == (
        "home", "no_occupied_rooms_cooldown",
        [empty.entity_id, room.entity_id])
    empty.last_changed = datetime.now(timezone.utc) - timedelta(minutes=11)
    assert home_presence(h, cfg)[0] == "away"
    room.state = "on"
    assert home_presence(h, cfg)[0] == "home"


def test_last_changed_is_reset_on_reboot_but_persisted_absence_is_not(adapter):
    room = negative("number.people_in_living", minutes=16)
    h = FakeHass([room], {room.entity_id: "living"})
    cfg = {"room_occupancy_sensors": [room.entity_id],
           "away_cooldown_minutes": 10}
    disk = FakeStore()
    first = PresenceContinuity(h, "entry", store=disk)
    asyncio.run(first.async_start())
    original = first.context(cfg)
    assert home_presence(h, original)[0] == "away"
    assert disk.saved["verified_absence_since"] == pytest.approx(
        room.last_changed.timestamp(), abs=1)
    asyncio.run(first.async_stop())

    # HA recreated its state object when booting: its observed last_changed
    # no longer tells us that the source was already zero before the reboot.
    room.last_changed = datetime.now(timezone.utc) - timedelta(seconds=4)
    assert home_presence(h, cfg)[0] == "home", "Beta50 regressed to Home here"
    restored = PresenceContinuity(h, "entry", store=disk)
    asyncio.run(restored.async_start())
    effective = restored.context(cfg)
    assert home_presence(h, effective)[0] == "away"
    assert effective["_verified_absence_since"] == pytest.approx(
        disk.saved["verified_absence_since"])


def test_still_cooling_down_when_rebooted_preserves_remaining_period(adapter):
    count = negative("input_number.present_people", minutes=3)
    h = FakeHass([count])
    cfg = {"room_occupancy_sensors": [count.entity_id], "away_cooldown_minutes": 10}
    disk = FakeStore()
    first = PresenceContinuity(h, "entry", store=disk)
    asyncio.run(first.async_start())
    assert home_presence(h, first.context(cfg))[0] == "home"
    asyncio.run(first.async_stop())
    count.last_changed = datetime.now(timezone.utc)
    second = PresenceContinuity(h, "entry", store=disk)
    asyncio.run(second.async_start())
    assert home_presence(h, second.context(cfg))[0] == "home"
    # Seven minutes have passed since the persisted, first verified zero.
    second._since = datetime.now(timezone.utc).timestamp() - 11 * 60
    assert home_presence(h, second.context(cfg))[0] == "away"


def test_source_change_or_observed_home_revokes_saved_absence(adapter):
    a = negative("binary_sensor.living_presence", minutes=25)
    b = negative("binary_sensor.kitchen_presence", minutes=1)
    h = FakeHass([a, b], {
        a.entity_id: "living", b.entity_id: "kitchen"})
    store = FakeStore()
    p = PresenceContinuity(h, "entry", store=store)
    asyncio.run(p.async_start())
    cfg = {"room_occupancy_sensors": [a.entity_id], "away_cooldown_minutes": 10}
    assert home_presence(h, p.context(cfg))[0] == "away"
    expanded = {**cfg, "room_occupancy_sensors": [a.entity_id, b.entity_id]}
    assert source_signature(cfg) != source_signature(expanded)
    assert home_presence(h, p.context(expanded))[0] == "home"
    b.state = "on"
    assert home_presence(h, p.context(expanded))[0] == "home"
    assert store.saved["verified_absence_since"] is None
    b.state = "off"
    b.last_changed = datetime.now(timezone.utc)
    assert home_presence(h, p.context(expanded))[0] == "home"


def test_unknown_or_stale_after_restart_never_counts_as_away(adapter):
    item = negative("number.home_count", minutes=20)
    h = FakeHass([item])
    cfg = {"room_occupancy_sensors": [item.entity_id],
           "away_cooldown_minutes": 10}
    store = FakeStore()
    old = PresenceContinuity(h, "entry", store=store)
    asyncio.run(old.async_start())
    assert home_presence(h, old.context(cfg))[0] == "away"
    asyncio.run(old.async_stop())
    start = store.saved["verified_absence_since"]

    item.last_changed = datetime.now(timezone.utc)
    restored = PresenceContinuity(h, "entry", store=store)
    asyncio.run(restored.async_start())
    for raw in ("unknown", "unavailable", "nan", "-1"):
        item.state = raw
        context = restored.context(cfg)
        assert "_verified_absence_since" not in context
        assert home_presence(h, context)[0] == "unknown"
    item.state = "0"
    item.last_reported = datetime.now(timezone.utc) - timedelta(hours=5)
    assert home_presence(h, restored.context(cfg))[0] == "unknown"
    item.last_reported = datetime.now(timezone.utc)
    assert home_presence(h, restored.context(cfg))[0] == "away"
    assert store.saved["verified_absence_since"] == start


def test_no_new_presence_or_actuator_permission_is_inferred(adapter):
    h = FakeHass([])
    cfg = {"room_occupancy_sensors": [], "home_trackers": []}
    p = PresenceContinuity(h, "entry", store=FakeStore())
    asyncio.run(p.async_start())
    shared = p.context(cfg)
    assert "_verified_absence_since" not in shared
    assert home_presence(h, shared)[0] == "home"
    assert "climate" not in p.__class__.__module__
    # No HA service manager or device registry is involved.


def test_no_negative_evidence_during_source_identity_change(adapter):
    src = negative("sensor.occupied_rooms", minutes=40)
    src.state = "[]"
    h = FakeHass([src])
    cfg = {"occupied_rooms_entity": src.entity_id,
           "occupied_rooms_attribute": "__state__",
           "away_cooldown_minutes": 10}
    disk = FakeStore()
    prior = PresenceContinuity(h, "entry", store=disk)
    asyncio.run(prior.async_start())
    assert home_presence(h, prior.context(cfg))[0] == "away"
    asyncio.run(prior.async_stop())
    src.last_changed = datetime.now(timezone.utc)
    changed = {**cfg, "occupied_rooms_attribute": "areas"}
    assert home_presence(h, PresenceContinuity(h, "entry", store=disk).context(changed))[0] == "unknown"
    assert "_verified_absence_since" not in PresenceContinuity(h, "entry", store=disk).context(changed)


def test_cooldown_never_completes_before_actual_elapsed_time():
    now = datetime.now(timezone.utc)
    fresh = SimpleNamespace(last_changed=now-timedelta(minutes=2))
    assert _after_away_cooldown([fresh], 10, "empty")[0] == "home"
    assert _after_away_cooldown([fresh], 10, "empty",
                                verified_since=(now-timedelta(minutes=11)).timestamp())[0] == "away"
    assert _after_away_cooldown([fresh], 10, "empty",
                                verified_since=(now+timedelta(hours=1)).timestamp())[0] == "home"
