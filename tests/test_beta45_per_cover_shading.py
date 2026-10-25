"""Regression tests for independent, fail-safe room cover controllers."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from test_discovery import adapter, MockState
from test_beta43_shade_cooling import make_room
from custom_components.environment_manager.shade_cooling import (
    cover_config, selectable_windows,
)
from custom_components.environment_manager.device_hierarchy import managed_shade_devices


def _editor(h):
    h.hass.config_entries = SimpleNamespace(async_update_entry=lambda entry, **kw:
        [setattr(entry, key, val) for key, val in kw.items()])


def _set(h, key, value, cover=None):
    from custom_components.environment_manager.device_controls import update_device_setting
    return asyncio.run(update_device_setting(
        h.manager, "shade_device", key, value, area="room",
        entity_id=cover or h.cover.entity_id,
    ))


def _arm(h, *, cover=None, window=None):
    _set(h, "window_entity", window or h.window.entity_id, cover)
    _set(h, "enabled", True, cover)


def test_exact_per_cover_window_and_default_disarmed(adapter):
    h = make_room(enabled=False)
    _editor(h)
    cover = h.cover.entity_id
    assert selectable_windows(h.hass, h.manager.settings, "room") == (h.window.entity_id,)
    _set(h, "window_entity", h.window.entity_id)
    assert cover_config(h.manager.settings, "room", cover)["enabled"] is False
    assert cover_config(h.manager.settings, "room", cover)["window_entity"] == h.window.entity_id
    _arm(h)
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls[-1][-1] == {"entity_id": cover}
    assert h.manager.settings["shade_rooms"]["room"]["covers"][cover]["enabled"] is True


def test_each_cover_uses_only_its_associated_window(adapter):
    h = make_room(enabled=False, second_cover=True)
    _editor(h)
    extra = MockState("binary_sensor.second_window", "on", device_class="window")
    h.hass._values[extra.entity_id] = extra
    h.hass._entity_areas[extra.entity_id] = "room"
    h.entry.data["room_sources"]["room"]["windows"].append(extra.entity_id)
    another = "cover.room_blind"
    _arm(h)
    _arm(h, cover=another, window=extra.entity_id)
    asyncio.run(h.control._tick("room"))
    assert [call[-1]["entity_id"] for call in h.hass.services.calls] == [h.cover.entity_id]
    assert h.control.statuses["room"]["covers"][another] == "window_open_or_unknown"
    h.hass.services.calls.clear()
    h.hass.states.get(another).state = "open"
    extra.state = "off"
    h.hass.states.get("weather.room").state = "rainy"
    # This now-closed second contact is not a reason to move without sun.
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls == []


def test_invalid_cross_room_window_and_missing_window_never_arm(adapter):
    h = make_room(enabled=False)
    _editor(h)
    with pytest.raises(Exception):
        _set(h, "enabled", True)
    other = MockState("binary_sensor.hallway_window", "off", device_class="window")
    h.hass._values[other.entity_id] = other
    h.hass._entity_areas[other.entity_id] = "hallway"
    with pytest.raises(Exception):
        _set(h, "window_entity", other.entity_id)
    _arm(h)
    _set(h, "window_entity", "none")
    assert cover_config(h.manager.settings, "room", h.cover.entity_id)["enabled"] is False
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls == []


def test_manual_close_pauses_one_cover_across_ticks_until_rearmed(adapter):
    h = make_room(enabled=False)
    _editor(h)
    _arm(h)
    h.hass.states.get("weather.room").state = "rainy"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls == []
    # The resident closes the shutter locally, not through this integration.
    h.cover.state = "closing"
    asyncio.run(h.control._tick("room"))
    record = h.control._records[h.cover.entity_id]
    assert record["phase"] == "manual_override"
    assert h.control._store.writes, "The pause must be durably stored"
    h.cover.state = "open"
    h.hass.states.get("weather.room").state = "sunny"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls == []
    # Re-enabling this exact cover (not another room device) clears its latch.
    previous = cover_config(h.manager.settings, "room", h.cover.entity_id)
    _set(h, "enabled", True)  # A deliberate ON rearms a paused cover.
    assert cover_config(h.manager.settings, "room", h.cover.entity_id)[
        "authorization_revision"] > previous["authorization_revision"]
    asyncio.run(h.control._tick("room"))
    assert [item[1] for item in h.hass.services.calls] == ["close_cover"]


def test_independent_per_cover_announcement_failure_blocks_motor(adapter, monkeypatch):
    from custom_components.environment_manager import shade_cooling
    h = make_room(enabled=False)
    _editor(h)
    _arm(h)
    _set(h, "announce", True)
    received = []
    async def reject(manager, *, area, action, entity_id, required):
        received.append((area, action, entity_id, required))
        return False
    monkeypatch.setattr(shade_cooling, "async_announce_before_move", reject)
    asyncio.run(h.control._tick("room"))
    assert received == [("room", "close", h.cover.entity_id, True)]
    assert h.hass.services.calls == []


def test_cover_devices_distinct_from_climate_equipment(adapter):
    h = make_room(enabled=False, second_cover=True)
    specs = managed_shade_devices(h.hass, h.entry.entry_id, h.manager.settings)
    assert len(specs) == 2
    assert {spec.source_entities[0] for spec in specs} == {
        "cover.room_blind", h.cover.entity_id,
    }
    assert len({spec.identifier for spec in specs}) == 2
    assert all(spec.area_id == "room" for spec in specs)


def test_manual_open_while_owned_stays_durably_paused(adapter):
    h = make_room(enabled=False)
    _editor(h)
    _arm(h)
    asyncio.run(h.control._tick("room"))
    h.cover.state = "closed"
    asyncio.run(h.control._tick("room"))
    assert h.control._records[h.cover.entity_id]["phase"] == "owned_closed"
    h.cover.state = "opening"
    asyncio.run(h.control._tick("room"))
    assert h.control._records[h.cover.entity_id]["phase"] == "manual_override"
    h.cover.state = "open"
    asyncio.run(h.control._tick("room"))
    assert [c[1] for c in h.hass.services.calls] == ["close_cover"]
