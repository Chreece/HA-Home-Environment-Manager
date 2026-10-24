"""Close-only solar window shading tests: exact device, no unsafe movement."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from test_discovery import MockState, FakeHass, adapter
from custom_components.environment_manager.shade_cooling import (
    ShadeCoolingController, evaluate_conditions, eligible_shade,
    CONF_SHADE_ROOMS, HOLD_SECONDS,
)
from custom_components.environment_manager import room_sources
from custom_components.environment_manager.logic import Window


def make_room(*, temp=27.0, sun=45.0, window="closed",
              shade_state="open", enabled=True, cover_class="shutter",
              supported_features=2, hours_old=0, second_cover=False):
    cover=MockState("cover.room_shutter",shade_state,device_class=cover_class)
    cover.attributes["supported_features"]=supported_features
    door=MockState("cover.garage", "open", device_class="garage")
    door.attributes["supported_features"]=2
    actual_window=MockState("binary_sensor.room_window",
                            "off" if window=="closed" else
                            "unavailable" if window=="unknown" else "on",
                            device_class="window")
    sensor=MockState("sensor.room_temperature", temp, unit="°C",
                     device_class="temperature",hours_old=hours_old)
    sun_entity=MockState("sun.sun","above_horizon" if sun is not None else "unknown")
    if sun is not None:
        sun_entity.attributes["elevation"]=sun
    sources=[cover,door,actual_window,sensor,sun_entity]
    if second_cover:
        another=MockState("cover.room_blind","open",device_class="blind")
        another.attributes["supported_features"]=2
        sources.append(another)
    hass=FakeHass(sources, {source.entity_id:"room" for source in sources
                            if source.entity_id!="sun.sun"})
    class Services:
        available=True
        def __init__(self):self.calls=[]
        def has_service(self,domain,service):
            return self.available and (domain,service)==("cover","close_cover")
        async def async_call(self,domain,service,data,*,target,blocking):
            assert (domain,service,data)==("cover","close_cover",{})
            assert blocking
            assert list(target)==["entity_id"] and target["entity_id"].startswith("cover.")
            self.calls.append((domain,service,data,target))
            hass.states.get(target["entity_id"]).state="closing"
    hass.services=Services()
    entry=SimpleNamespace(entry_id="room-shading",data={
        "areas":["room"],
        "room_sources":{"room":{
            "temperature":[sensor.entity_id],"windows":[actual_window.entity_id],
            "shades":[cover.entity_id,*(
                ["cover.room_blind"] if second_cover else []
            )],
        }},
        CONF_SHADE_ROOMS:{"room":{"enabled":enabled,"close_above_c":25.0,
                                  "min_sun_elevation":10.}},
    },options={})
    class Manager:
        _active=False
        def __init__(self):
            self.entry=entry
            self.hass=hass
            self.plan=SimpleNamespace(
                rooms=(SimpleNamespace(area_id="room",
                    windows=(Window(actual_window.entity_id,"Window",
                          None if window=="unknown" else window=="open"),)),),
                climate_rooms=(),
            )
        @property
        def settings(self):return {**self.entry.data,**self.entry.options}
        def _shade_updated(self):pass
    manager=Manager()
    class Store:
        fail=False
        def __init__(self):self.writes=[]
        async def async_save(self,content):
            if self.fail:raise RuntimeError("persist unavailable")
            self.writes.append(content)
    controller=ShadeCoolingController(manager,clock=lambda:10000)
    controller._started=0
    controller._active=controller._ready=True
    controller._store=Store()
    manager.shading=controller
    return SimpleNamespace(hass=hass,manager=manager,control=controller,
                           cover=cover,window=actual_window,sensor=sensor,
                           sun=sun_entity,entry=entry)


@pytest.mark.parametrize("window,sun,temperature,enabled,reason", [
    ("closed",45,27,False,"disabled"),
    ("open",45,27,True,"window_open_or_unknown"),
    ("unknown",45,27,True,"window_open_or_unknown"),
    ("closed",None,27,True,"sun_not_verified"),
    ("closed",2,27,True,"sun_below_shading_threshold"),
    ("closed",45,23,True,"room_below_cooling_threshold"),
])
def test_solar_shade_readiness_never_infers_missing_evidence(
    adapter,window,sun,temperature,enabled,reason,
):
    h=make_room(window=window,sun=sun,temp=temperature,enabled=enabled)
    asyncio.run(h.control._tick("room"))
    assert h.control.statuses["room"]["status"]==reason
    assert h.hass.services.calls==[]


def test_native_cover_selector_excludes_garages_windows_and_unknown_capabilities(adapter):
    h=make_room()
    cover=MockState("cover.other_roller","open",device_class="blind")
    cover.attributes["supported_features"]=2
    h.hass._values[cover.entity_id]=cover
    h.hass._entity_areas[cover.entity_id]="other"
    selections=room_sources.choices(h.hass,"room")
    assert {obj["value"] for obj in selections["shades"]}=={"cover.room_shutter"}
    assert selections["windows"] and selections["shades"]
    assert not eligible_shade(h.hass,"room","cover.garage",(
        "cover.garage",))[0]
    assert not eligible_shade(h.hass,"room","cover.other_roller",(
        "cover.other_roller",))[0]
    h.cover.attributes["supported_features"]=0
    assert not eligible_shade(h.hass,"room",h.cover.entity_id,(
        h.cover.entity_id,))[0]


def test_selection_never_automatically_arms_shade_closing(adapter):
    h=make_room(enabled=False)
    assert room_sources.selected(h.manager.settings,"room","shades")==(
        "cover.room_shutter",)
    assert asyncio.run(h.control._tick("room")) is None
    assert h.hass.services.calls==[]


def test_explicit_close_exact_entity_and_manual_reopen_is_not_fought(adapter):
    h=make_room()
    asyncio.run(h.control._tick("room"))
    assert len(h.hass.services.calls)==1
    command=h.hass.services.calls[0]
    assert command==("cover","close_cover",{},{
        "entity_id":"cover.room_shutter",
    })
    assert h.control.statuses["room"]["status"]=="close_command_sent"
    assert len(h.control._store.writes)==1
    h.cover.state="open"  # User manually raised roller shade after our close
    asyncio.run(h.control._tick("room"))
    assert len(h.hass.services.calls)==1
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]==(
        "recent_close_or_manual_reopen_hold")
    # Re-arm only after persistent two-hour manual-override hold.
    h.control.clock=lambda:10000+HOLD_SECONDS+1
    asyncio.run(h.control._tick("room"))
    assert len(h.hass.services.calls)==2


def test_storage_failure_blocks_physical_close(adapter):
    h=make_room()
    h.control._store.fail=True
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    assert not h.control._ready
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]==(
        "storage_failure_no_command")


def test_disabled_service_and_invalid_source_location_hold_closed(adapter):
    h=make_room()
    h.hass.services.available=False
    asyncio.run(h.control._tick("room"))
    assert h.control.statuses["room"]["status"]=="close_cover_service_unavailable"
    h.hass.services.available=True
    h.hass._entity_areas[h.cover.entity_id]="other"
    asyncio.run(h.control._tick("room"))
    assert h.hass.services.calls==[]
    assert h.control.statuses["room"]["covers"][h.cover.entity_id]=="cover_wrong_room"


def test_stale_room_temperature_cannot_close_shade(adapter):
    h=make_room(hours_old=20)
    asyncio.run(h.control._tick("room"))
    assert h.control.statuses["room"]["status"]=="temperature_not_verified"
    assert h.hass.services.calls==[]


def test_window_shade_settings_validate_exact_room_and_are_off_by_default(adapter):
    h=make_room(enabled=False)
    from custom_components.environment_manager.device_controls import update_device_setting
    def update_entry(entry,**kwargs):
        for key,value in kwargs.items():
            setattr(entry,key,value)
    h.hass.config_entries=SimpleNamespace(async_update_entry=update_entry)
    asyncio.run(update_device_setting(
        h.manager,"area_shading","close_above_c",24.5,area="room"
    ))
    assert h.manager.settings["shade_rooms"]["room"]["enabled"] is False
    asyncio.run(update_device_setting(
        h.manager,"area_shading","enabled",True,area="room"
    ))
    assert h.manager.settings["shade_rooms"]["room"]["enabled"] is True
    with pytest.raises(Exception):
        asyncio.run(update_device_setting(
            h.manager,"area_shading","enabled",True,area="other"
        ))
    h.hass._entity_areas[h.cover.entity_id]="other"
    with pytest.raises(Exception):
        asyncio.run(update_device_setting(
            h.manager,"area_shading","enabled",True,area="room"
        ))


def test_deselecting_shades_revokes_auto_close_approval(adapter):
    h=make_room()
    data={**h.manager.settings}
    data["shade_rooms"]={"room":{"enabled":True}}
    prior=room_sources.selected(data,"room","shades")
    assert prior == ("cover.room_shutter",)
    groups={key: list(room_sources.selected(data,"room",key) or ())
            for key in room_sources.GROUPS}
    groups["shades"]=[]
    room_sources.store_selection(h.hass,data,"room",groups)
    assert data["shade_rooms"]["room"]["enabled"] is False
    assert room_sources.selected(data,"room","shades")==()


def test_only_safe_window_cover_types_eligible_never_awning(adapter):
    h=make_room()
    classes=["shade","blind","shutter","curtain"]
    for klass in classes:
        h.cover.attributes["device_class"]=klass
        assert eligible_shade(h.hass,"room",h.cover.entity_id,(
            h.cover.entity_id,))[0]
    for klass in ["awning","garage","gate","door","window","damper"]:
        h.cover.attributes["device_class"]=klass
        assert not eligible_shade(h.hass,"room",h.cover.entity_id,(
            h.cover.entity_id,))[0]
