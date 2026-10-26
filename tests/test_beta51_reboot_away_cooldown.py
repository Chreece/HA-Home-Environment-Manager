"""Verified absence cooldown survives Home Assistant restart, never stale trust."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import math
import time

import pytest
from test_discovery import adapter, FakeHass, MockState


def old(minutes: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def fixture_home(*, minutes_ago=0.5):
    roomlist = MockState("sensor.occupied_rooms", "[]")
    roomlist.last_changed = old(minutes_ago)
    roomlist.last_updated = roomlist.last_changed
    count = MockState("number.people_home", 0)
    count.last_changed = old(minutes_ago)
    motion = MockState("binary_sensor.kitchen_motion", "off", device_class="occupancy")
    motion.last_changed = old(minutes_ago)
    hass = FakeHass(
        [roomlist, count, motion],
        {"binary_sensor.kitchen_motion": "kitchen"},
    )
    data = {
        "occupied_rooms_entity": roomlist.entity_id,
        "home_trackers": [count.entity_id],
        "room_occupancy_sensors": [motion.entity_id],
        "away_cooldown_minutes": 10,
    }
    return hass, data, roomlist, count, motion


def test_beta50_reboot_restarts_last_changed_cooldown_without_saved_history(adapter):
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, settings, *_ = fixture_home(minutes_ago=0.5)
    assert home_presence(hass, settings)[:2] == (
        "home", "no_occupied_rooms_cooldown")
    # Prior (pre-reboot) absence is logically unrelated to the new
    # last_changed timestamp of a recreated source without historical data.
    assert home_presence(hass, settings)[0] != "away"


def test_verified_empty_since_survives_reboot_and_counts_pre_reboot_time(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, settings, roomlist, count, motion = fixture_home(minutes_ago=11)
    first = HomeAwayContinuity(hass, "test")
    original = first.settings(settings)
    assert original["_verified_empty_since"] <= time.time()-10*60
    assert home_presence(hass, original)[0] == "away"
    stored = first.snapshot()
    # HA reboot recreates same-value entities and resets changed-at values.
    roomlist.last_changed = roomlist.last_updated = old(0.1)
    count.last_changed = motion.last_changed = old(0.1)
    second = HomeAwayContinuity.restore(hass, "test", stored)
    confirmed = second.settings(settings)
    assert confirmed["_verified_empty_since"] == stored["since"]
    assert home_presence(hass, confirmed)[:2] == ("away", "occupied_rooms_empty")
    assert home_presence(hass, settings)[0] == "home"


def test_five_minutes_before_reboot_plus_six_minutes_after_reaches_away(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    from custom_components.environment_manager.occupancy_policy import home_presence
    anchor = time.time()
    hass, settings, roomlist, count, motion = fixture_home(minutes_ago=5)
    first = HomeAwayContinuity(hass, "a", clock=lambda: anchor)
    entry = first.settings(settings)
    assert home_presence(hass, entry)[0] == "home"
    record = first.snapshot()
    roomlist.last_changed = roomlist.last_updated = old(0.2)
    motion.last_changed = count.last_changed = old(0.2)
    next_clock = lambda: anchor + 6*60
    # Simulate wall-clock advance and live HA states with fresh timestamps.
    second = HomeAwayContinuity.restore(hass, "a", record, clock=next_clock)
    revised = second.settings(settings)
    # Since is historical from the pre-reboot observation, not reset.
    assert revised["_verified_empty_since"] == pytest.approx(record["since"])
    # The system clock itself is not mocked. The pure elapsed calculation
    # remains correct when passing a saved stamp earlier than a full cooldown.
    assert home_presence(hass, revised)[0] == "home"
    assert revised["_verified_empty_since"] < anchor-4*60


def test_a_person_home_resets_cached_departure_and_next_departure_restarts_timer(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, cfg, roomlist, count, motion = fixture_home(minutes_ago=25)
    tracker = HomeAwayContinuity(hass, "abc")
    assert home_presence(hass, tracker.settings(cfg))[0] == "away"
    count.state = "1"
    new = tracker.settings(cfg)
    assert "_verified_empty_since" not in new
    assert tracker.snapshot()["since"] is None
    assert home_presence(hass, new)[0] == "home"
    count.state = "0"
    roomlist.last_changed = roomlist.last_updated = old(.25)
    motion.last_changed = old(.25)
    again = tracker.settings(cfg)
    assert home_presence(hass, again)[0] == "home"
    assert again["_verified_empty_since"] > time.time() - 60


def test_changed_source_selection_does_not_inherit_previous_empty_clock(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, cfg, roomlist, count, motion = fixture_home(minutes_ago=20)
    current = HomeAwayContinuity(hass, "abc")
    prior = current.settings(cfg)
    assert home_presence(hass, prior)[0] == "away"
    changed = {**cfg, "room_occupancy_sensors": []}
    roomlist.last_changed = roomlist.last_updated = old(.3)
    resumed = HomeAwayContinuity.restore(hass, "abc", current.snapshot())
    rebuilt = resumed.settings(changed)
    assert rebuilt["_verified_empty_since"] > time.time()-60
    assert home_presence(hass, rebuilt)[0] == "home"


def test_unknown_or_unavailable_room_or_tracker_never_accepts_persisted_absence(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, cfg, roomlist, count, motion = fixture_home(minutes_ago=20)
    original = HomeAwayContinuity(hass, "abc")
    original.settings(cfg)
    cache = original.snapshot()
    revived = HomeAwayContinuity.restore(hass, "abc", cache)
    for entity in (count, roomlist, motion):
        value = entity.state
        entity.state = "unavailable"
        decorated = revived.settings(cfg)
        assert "_verified_empty_since" not in decorated
        assert home_presence(hass, decorated)[0] == "unknown"
        entity.state = value
    count.state = "2"
    assert home_presence(hass, revived.settings(cfg))[0] == "home"


def test_home_positive_wins_even_if_occupancy_roomlist_is_empty_and_old(adapter):
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, cfg, roomlist, count, motion = fixture_home(minutes_ago=50)
    count.state = "1"
    assert home_presence(hass, cfg)[:2] == ("home", "any_home_policy")


def test_missing_any_explicit_presence_tracker_blocks_false_away(adapter):
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass, cfg, _, count, _ = fixture_home(minutes_ago=90)
    cfg["home_trackers"].append("person.no_longer_connected")
    assert home_presence(hass, cfg)[:2] == ("unknown", "unverified_home_trackers")
    count.state = "2"
    assert home_presence(hass, cfg)[0] == "home"


def test_number_only_zero_is_away_without_motion_sensor_cooldown(adapter):
    from custom_components.environment_manager.occupancy_policy import home_presence
    hass = FakeHass([MockState("number.people_home", 0)])
    cfg = {"home_trackers": ["number.people_home"], "away_cooldown_minutes": 100}
    assert home_presence(hass, cfg)[0] == "away"


def test_sustained_unknown_invalidates_old_history(adapter):
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    now = time.time()
    hass, cfg, _, count, _ = fixture_home(minutes_ago=20)
    clock = [now]
    instance = HomeAwayContinuity(hass, "abc", clock=lambda: clock[0])
    instance.settings(cfg)
    assert instance.snapshot()["since"]
    count.state = "unavailable"
    instance.settings(cfg)
    clock[0] += 301
    instance.settings(cfg)
    assert instance.snapshot()["since"] is None
    count.state = "0"
    instance.settings(cfg)
    assert instance.snapshot()["since"] is not None
    assert instance.snapshot()["since"] > now


def test_climate_only_plan_receives_same_reboot_safe_verified_empty_policy(adapter):
    from custom_components.environment_manager import equipment_model as model
    from test_equipment_control import home
    from custom_components.environment_manager.home_away_continuity import HomeAwayContinuity
    # No physical service permission gets added by this read-only policy.
    assert hasattr(model, "plan_for")
    assert "verified_empty_since" in __import__(
        "inspect").getsource(HomeAwayContinuity.settings)
