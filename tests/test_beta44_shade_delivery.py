"""Home-wide shade pre-movement announcements are exact-room and fail safe."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from test_discovery import adapter
from test_beta43_shade_cooling import make_room
from custom_components.environment_manager.shade_delivery import (
    async_announce_before_move,
)
from custom_components.environment_manager.const import CONF_SHADE_ANNOUNCE


def test_home_opt_in_is_disabled_by_default_and_saved_independently(adapter):
    from custom_components.environment_manager.device_controls import update_device_setting
    from pathlib import Path
    h=make_room()
    h.hass.config_entries=SimpleNamespace(async_update_entry=lambda entry,**kw:
        [setattr(entry,key,val) for key,val in kw.items()])
    assert h.manager.settings.get(CONF_SHADE_ANNOUNCE,False) is False
    asyncio.run(update_device_setting(h.manager,"global_setting",CONF_SHADE_ANNOUNCE,True))
    assert h.manager.settings[CONF_SHADE_ANNOUNCE] is True
    asyncio.run(update_device_setting(h.manager,"global_setting",CONF_SHADE_ANNOUNCE,False))
    assert h.manager.settings[CONF_SHADE_ANNOUNCE] is False
    # Entity class identity/HA properties are validated in the installed
    # Home Assistant 2026.10 smoke job, not in this lightweight fixture.
    source=(Path(__file__).resolve().parents[1]/
            "custom_components/environment_manager/switch.py").read_text()
    assert "CONF_SHADE_ANNOUNCE" in source and "HomeSettingSwitch" in source

def test_disabled_announcement_has_no_delivery_or_cover_effect(adapter):
    h=make_room()
    assert asyncio.run(async_announce_before_move(h.manager,area="room",action="close"))
    assert h.hass.services.calls==[]


def test_home_announcement_direct_room_notification_submitted_before_move(adapter):
    h=make_room()
    h.entry.options={
        CONF_SHADE_ANNOUNCE:True, "automatic_notifications":True,
        "notify_entities":["notify.room_phone"],
        "language":"el",
    }
    h.hass._entity_areas["notify.room_phone"]="room"
    calls=[]
    h.hass.services.has_service=lambda domain,service: (domain,service)==("notify","send_message")
    async def send(domain,service,data,*,target=None,blocking=False):
        calls.append((domain,service,data,target,blocking))
    h.hass.services.async_call=send
    assert asyncio.run(async_announce_before_move(h.manager,area="room",action="open"))
    assert len(calls)==1
    domain,service,data,target,blocking=calls[0]
    assert (domain,service)==("notify","send_message")
    assert target=={"entity_id":["notify.room_phone"]}
    assert blocking
    assert "ανοίξουν" in data["message"]
    assert "Σκίαση" in data["title"]


def test_unavailable_delivery_fails_closed(adapter):
    h=make_room()
    h.entry.options={CONF_SHADE_ANNOUNCE:True}
    assert not asyncio.run(async_announce_before_move(
        h.manager,area="room",action="close"))
    assert h.hass.services.calls==[]


def test_persistent_visual_notification_fallback_when_enabled(adapter):
    h=make_room()
    h.entry.options={CONF_SHADE_ANNOUNCE:True}
    calls=[]
    h.hass.services.has_service=lambda domain,service: (
        domain,service)==("persistent_notification","create")
    async def send(domain,service,data,*,blocking=False,target=None):
        calls.append((domain,service,data,blocking))
    h.hass.services.async_call=send
    assert asyncio.run(async_announce_before_move(h.manager,area="room",action="close"))
    assert calls[0][0:2]==("persistent_notification","create")
    assert calls[0][3] is True
    assert "room" in calls[0][2]["message"]


def test_hub_rejection_does_not_duplicate_native_notifications(adapter,monkeypatch):
    from custom_components.environment_manager import shade_delivery as delivery
    h=make_room()
    h.entry.options={
        CONF_SHADE_ANNOUNCE:True,"use_announcement_hub":True,
        "automatic_tts":True,"automatic_notifications":True,
    }
    payload=[]
    monkeypatch.setattr(delivery,"hub_available",lambda hass:True)
    async def rejected(hass,message):
        payload.append(message)
        return False
    monkeypatch.setattr(delivery,"async_submit_hub",rejected)
    assert not asyncio.run(async_announce_before_move(h.manager,area="room",action="close"))
    assert len(payload)==1
    assert payload[0]["use_ai"] is False
    assert payload[0]["text"].startswith("The window shades")
    assert payload[0]["area"]==["room"]
    assert h.hass.services.calls==[]


def test_global_switch_label_present_in_every_locale():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/"custom_components/environment_manager"
    catalogs=[root/"strings.json",*sorted((root/"translations").glob("*.json"))]
    assert len(catalogs)==39
    for path in catalogs:
        source=json.loads(path.read_text(encoding="utf-8"))
        assert len(source["entity"]["switch"]["home_shade_announce_before_movement"]["name"])>5
        assert "area_shading_enabled" in source["entity"]["switch"]
