"""Weather-aware shade closing and exact owned reopening regressions.

Every physical move is explicitly scoped to a selected native shade. Only a
confirmed integration-close can be reopened. User opening forever latches a
manual override until deliberate disable/enable, including HA restarts.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from test_discovery import adapter, MockState
from test_beta43_shade_cooling import make_room
from custom_components.environment_manager.shade_weather import (
    weather_evidence, ALL_KNOWN,
)
from custom_components.environment_manager.shade_cooling import (
    ShadeCoolingController, OPEN_STABLE_SECONDS, HOLD_SECONDS,
)


@pytest.mark.parametrize("condition,should_close", [
    ("sunny",True),("partlycloudy",True),
    ("cloudy",False),("fog",False),("rainy",False),("pouring",False),
    ("windy",False),("windy-variant",False),("snowy",False),
    ("hail",False),("lightning",False),("lightning-rainy",False),
    ("exceptional",False),("unavailable",False),
])
def test_only_explicit_solar_weather_may_close_shades(adapter,condition,should_close):
    h=make_room()
    h.hass.states.get("weather.room").state=condition
    result,evidence=weather_evidence(h.hass,h.manager.settings)
    assert bool(result=="weather_solar")==should_close
    asyncio.run(h.control._tick("room"))
    assert bool(h.hass.services.calls)==should_close, (condition,h.control.statuses)


def test_weather_must_be_configured_fresh_complete_and_consistent(adapter):
    h=make_room()
    settings=dict(h.manager.settings)
    settings["weather_entities"]=[]
    assert weather_evidence(h.hass,settings)[0]=="weather_not_configured"
    h.entry.data["weather_entities"]=[]
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    h.entry.data["weather_entities"]=["weather.room"]
    weather=h.hass.states.get("weather.room")
    weather.last_updated=datetime.now(timezone.utc)-timedelta(hours=7)
    assert weather_evidence(h.hass,h.manager.settings)[0]=="weather_stale"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    weather.last_updated=datetime.now(timezone.utc)
    second=MockState("weather.second","rainy")
    h.hass._values[second.entity_id]=second
    h.entry.data["weather_entities"]=["weather.room","weather.second"]
    assert weather_evidence(h.hass,h.manager.settings)[0]=="weather_conflicting"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    second.state="sunny"
    assert weather_evidence(h.hass,h.manager.settings)[0]=="weather_solar"
    asyncio.run(h.control._tick("room"))
    assert [c[1] for c in h.hass.services.calls]==["close_cover"]


def _take_ownership(h):
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls and h.hass.services.calls[-1][1]=="close_cover"
    assert h.control._records[h.cover.entity_id]["phase"]=="closing_requested"
    h.cover.state="closed"
    asyncio.run(h.control._tick("room"))
    assert h.control._records[h.cover.entity_id]["phase"]=="owned_closed"


def test_owned_close_reopens_after_stable_clouds_not_other_covers(adapter):
    h=make_room(second_cover=True)
    # Only the first shutter belongs to a confirmed close. Simulate an
    # unrelated blind already closed before Manager was enabled.
    second=h.hass.states.get("cover.room_blind")
    second.state="closed"
    _take_ownership(h)
    assert second.entity_id not in h.control._records
    h.hass.states.get("weather.room").state="cloudy"
    asyncio.run(h.control._tick("room"))
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]=="waiting_for_stable_release"
    assert [c[1] for c in h.hass.services.calls]==["close_cover"]
    h.control.clock=lambda:10000+OPEN_STABLE_SECONDS+1
    asyncio.run(h.control._tick("room"))
    assert [c[1] for c in h.hass.services.calls]==["close_cover","open_cover"]
    assert h.hass.services.calls[-1][-1]=={"entity_id":"cover.room_shutter"}
    assert h.control._records[h.cover.entity_id]["phase"]=="opening_requested"
    h.cover.state="open"
    asyncio.run(h.control._tick("room"))
    assert h.control._records[h.cover.entity_id]["phase"]=="released"
    assert h.hass.services.calls[-1][1]=="open_cover"
    h.hass.states.get("weather.room").state="sunny"
    asyncio.run(h.control._tick("room"))
    assert len(h.hass.services.calls)==2, "No auto-reclosing in same day"


def test_verified_sunset_opens_owned_cover_but_not_user_closed_cover(adapter):
    h=make_room(second_cover=True)
    h.hass.states.get("cover.room_blind").state="closed"
    _take_ownership(h)
    h.sun.state="below_horizon"
    h.sun.attributes["elevation"]=-9
    asyncio.run(h.control._tick("room"))
    assert [c[1] for c in h.hass.services.calls]==["close_cover","open_cover"]
    assert h.hass.services.calls[-1][-1]["entity_id"]==h.cover.entity_id


def test_weather_hazard_holds_owned_shade_instead_of_automatically_opening(adapter):
    h=make_room()
    _take_ownership(h)
    h.sun.state="below_horizon"
    h.hass.states.get("weather.room").state="windy"
    asyncio.run(h.control._tick("room"))
    assert [c[1] for c in h.hass.services.calls]==["close_cover"]
    assert h.control._records[h.cover.entity_id]["phase"]=="owned_closed"


def test_manual_reopening_latches_forever_until_explicit_room_rearm(adapter):
    h=make_room()
    _take_ownership(h)
    h.cover.state="opening"
    asyncio.run(h.control._tick("room"))
    record=h.control._records[h.cover.entity_id]
    assert record["phase"]=="manual_override"
    h.cover.state="open"
    h.control.clock=lambda:10000+HOLD_SECONDS*20
    asyncio.run(h.control._tick("room"))
    assert len(h.hass.services.calls)==1
    # A restart must not erase the durable record or permit movement.
    new=ShadeCoolingController(h.manager,clock=lambda:10000+HOLD_SECONDS*40,
        announcement_grace_seconds=0)
    new._store=h.control._store
    new._records=dict(h.control._records)
    new._active=new._ready=True
    new._started=0
    asyncio.run(new._tick("room"))
    assert len(h.hass.services.calls)==1
    # Deliberate OFF->ON increments authorization revision via public editor;
    # it is NOT just a two-hour timer.
    from custom_components.environment_manager.device_controls import update_device_setting
    h.hass.config_entries=SimpleNamespace(async_update_entry=lambda entry,**kw:
        [setattr(entry,key,val) for key,val in kw.items()])
    asyncio.run(update_device_setting(h.manager,"area_shading","enabled",False,area="room"))
    asyncio.run(update_device_setting(h.manager,"area_shading","enabled",True,area="room"))
    assert h.manager.settings["shade_rooms"]["room"]["authorization_revision"]==1
    asyncio.run(new._tick("room"))
    assert len(h.hass.services.calls)==2
    assert new._records[h.cover.entity_id]["phase"]=="closing_requested"


def test_b43_legacy_close_history_is_not_claimed_as_owned(adapter):
    h=make_room()
    h.control._records[h.cover.entity_id]={"area":"room","command_at":10000,
                                            "phase":"legacy_manual_hold",
                                            "revision":0}
    h.cover.state="closed"
    h.sun.state="below_horizon"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    assert h.control._records[h.cover.entity_id]["phase"]=="legacy_manual_hold"


def test_no_open_on_unverified_close_or_unknown_cover_state(adapter):
    h=make_room()
    asyncio.run(h.control._tick("room"))
    h.sun.state="below_horizon"
    asyncio.run(h.control._tick("room"))
    assert not any(x[1]=="open_cover" for x in h.hass.services.calls)
    h.control.clock=lambda:10000+400
    asyncio.run(h.control._tick("room"))
    assert h.control._records[h.cover.entity_id]["phase"]=="manual_override"
    assert not any(x[1]=="open_cover" for x in h.hass.services.calls)


def test_announce_failure_holds_movement_and_success_is_before_cover_service(adapter,monkeypatch):
    from custom_components.environment_manager import shade_cooling
    h=make_room()
    h.entry.options={"shade_announce_before_movement":True}
    order=[]
    async def denied(manager,*,area,action):
        order.append(("announcement_denied",action))
        return False
    monkeypatch.setattr(shade_cooling,"async_announce_before_move",denied)
    asyncio.run(h.control._tick("room"))
    assert order==[("announcement_denied","close")]
    assert h.hass.services.calls==[]
    async def granted(manager,*,area,action):
        order.append(("announcement",action))
        assert h.hass.services.calls==[]
        return True
    monkeypatch.setattr(shade_cooling,"async_announce_before_move",granted)
    asyncio.run(h.control._tick("room"))
    assert order[-1]==("announcement","close")
    assert len(h.hass.services.calls)==1


def test_weather_turns_rainy_during_preannouncement_so_no_cover_moves(adapter,monkeypatch):
    from custom_components.environment_manager import shade_cooling
    h=make_room()
    h.entry.options={"shade_announce_before_movement":True}
    async def changed(manager,*,area,action):
        h.hass.states.get("weather.room").state="rainy"
        return True
    monkeypatch.setattr(shade_cooling,"async_announce_before_move",changed)
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]==(
        "conditions_changed_after_announcement")


def test_user_opens_during_preannouncement_no_command(adapter,monkeypatch):
    from custom_components.environment_manager import shade_cooling
    h=make_room()
    h.entry.options={"shade_announce_before_movement":True}
    async def changed(manager,*,area,action):
        h.cover.state="opening"
        return True
    monkeypatch.setattr(shade_cooling,"async_announce_before_move",changed)
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]==(
        "conditions_changed_after_announcement")
