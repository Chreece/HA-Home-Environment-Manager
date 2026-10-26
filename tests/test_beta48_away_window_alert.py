"""Verified all-residents-away window warnings, exact Hub people/channels and lifecycle."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from test_discovery import FakeHass, MockState, adapter


def fixture_home():
    a = MockState("person.alex", "home")
    b = MockState("person.jo", "not_home")
    door = MockState("binary_sensor.living_window", "on", device_class="window")
    second = MockState("binary_sensor.kitchen_window", "on", device_class="window")
    offline = MockState("binary_sensor.offline_window", "unavailable", device_class="window")
    shade = MockState("cover.living_blind", "open", device_class="window")
    extra = MockState("binary_sensor.unselected_window", "on", device_class="window")
    states = (a,b,door,second,offline,shade,extra)
    hass = FakeHass(states, {
        a.entity_id: None, b.entity_id: None,
        door.entity_id: "living", second.entity_id: "kitchen",
        offline.entity_id: "living", shade.entity_id: "living",
        extra.entity_id: "living",
    })
    hass._area_entries = {
        "living":SimpleNamespace(name="Living room",id="living"),
        "kitchen":SimpleNamespace(name="Kitchen",id="kitchen"),
    }
    data = {
        "areas":["living","kitchen"],
        "room_sources":{
            "living":{"windows":[door.entity_id,offline.entity_id]},
            "kitchen":{"windows":[second.entity_id]},
        },
        "occupancy_global":{"home_trackers":[a.entity_id,b.entity_id]},
        "away_open_window_alert":True,
    }
    return hass,data,a,b,door,second


def test_every_person_must_be_confirmed_away_not_unknown(adapter):
    from custom_components.environment_manager.away_windows import confirmed_home_state
    hass, settings, first, second, *_ = fixture_home()
    assert confirmed_home_state(hass,settings) == "home"
    first.state = "not_home"
    assert confirmed_home_state(hass,settings) == "away"
    second.state = "unavailable"
    assert confirmed_home_state(hass,settings) == "unknown"
    second.state = "not_home"
    other = MockState("device_tracker.extra", "unknown")
    hass._values[other.entity_id] = other
    settings["occupancy_global"]["home_trackers"].append(other.entity_id)
    assert confirmed_home_state(hass,settings) == "unknown"
    other.state="not_home"
    assert confirmed_home_state(hass,settings) == "away"
    first.state="home"
    assert confirmed_home_state(hass,settings) == "home"


def test_only_selected_actual_open_window_contacts_are_reported(adapter):
    from custom_components.environment_manager.away_windows import open_windows, watched_entities
    hass,settings, *_ = fixture_home()
    result = open_windows(hass,settings)
    assert [eid for eid,_ in result] == [
        "binary_sensor.kitchen_window","binary_sensor.living_window"
    ]
    assert all("Window" not in label or ":" in label for _,label in result)
    assert "person.alex" in watched_entities(hass,settings)
    assert "binary_sensor.offline_window" in watched_entities(hass,settings)
    settings["excluded_window_entities"] = ["binary_sensor.kitchen_window"]
    assert [e for e,_ in open_windows(hass,settings)] == ["binary_sensor.living_window"]
    settings["room_sources"]["living"]["windows"] = []
    assert open_windows(hass,settings) == (), "Explicit empty is not autodiscovery"
    settings["room_sources"]["living"]["windows"] = ["binary_sensor.unselected_window"]
    assert [e for e,_ in open_windows(hass,settings)] == ["binary_sensor.unselected_window"]


def test_no_window_alert_when_only_away_unknown_contacts(adapter):
    from custom_components.environment_manager.away_windows import open_windows
    hass,settings, *_=fixture_home()
    settings["room_sources"]["living"]["windows"]=["binary_sensor.offline_window"]
    settings["room_sources"]["kitchen"]["windows"]=[]
    assert open_windows(hass,settings)==()


def test_person_channels_do_not_expand_to_all_devices(adapter):
    from custom_components.environment_manager.away_windows import (
        configured_recipients, deliver_notice,
    )
    hass,settings, *_=fixture_home()
    settings.update({
        "away_windows_target_people":["person.alex"],
        "away_windows_delivery_channels":[
            "mobile_notification","watch_tts","mobile_notification",
        ],
    })
    people, channels=configured_recipients(hass,settings)
    assert people==["person.alex"]
    assert channels==["mobile_notification","watch_tts"]
    calls=[]
    class Services:
        def has_service(self,d,s):
            return d=="notify" and s=="announcement_hub"
        async def async_call(self,d,s,data,**kw):
            calls.append((d,s,data,kw))
            return {"accepted":True,"job_id":str(len(calls))}
    hass.services=Services()
    hass.config_entries=SimpleNamespace(async_entries=lambda domain:[
        SimpleNamespace(state="loaded")] if domain=="announcement_hub" else [])
    hass.data={"announcement_hub":{"manager":SimpleNamespace(running=True)}}
    manager=SimpleNamespace(hass=hass,settings=settings,get_language=lambda _: "el")
    windows=(("binary_sensor.living_window","Σαλόνι: Παράθυρο"),)
    assert asyncio.run(deliver_notice(manager,windows))
    assert len(calls)==2
    by_destination={tuple(x[2]["person_destination"]):x[2] for x in calls}
    mobile=by_destination[("mobile",)]
    watch=by_destination[("watch",)]
    assert mobile["service"]==["notification"]
    assert mobile["target_person"]==["person.alex"]
    assert "text_notify" in mobile and "text_tts" not in mobile
    assert watch["service"]==["companion_tts"]
    assert watch["companion_tts"] is True
    assert "text_tts" in watch and "text_notify" not in watch
    for _,_,p,_ in calls:
        assert p["occupied_only"] is False
        assert "area" not in p and "integration" not in p and "device" not in p
        assert "room" not in p["person_destination"]
        assert "ανοιχτ" in (p.get("text_tts") or p.get("text_notify")).lower()


def test_unconfigured_hub_persons_never_fall_back_to_room_or_broadcast(adapter):
    from custom_components.environment_manager.away_windows import deliver_notice
    hass,settings,*_=fixture_home()
    calls=[]
    hass.services=SimpleNamespace(
        has_service=lambda d,s:True,
        async_call=lambda *a,**k:calls.append((a,k)),
    )
    hass.config_entries=SimpleNamespace(async_entries=lambda domain:[
        SimpleNamespace(state="loaded")])
    manager=SimpleNamespace(hass=hass,settings=settings,get_language=lambda _: "en")
    assert not asyncio.run(deliver_notice(manager,(("binary_sensor.living_window","Living: Window"),)))
    assert calls==[]


def test_restart_while_away_does_not_alert_and_new_departure_deduplicates(adapter):
    from custom_components.environment_manager.away_windows import AwayWindowAlert
    hass, settings, first, second, window, *_=fixture_home()
    settings["away_windows_target_people"]=["person.alex"]
    settings["away_windows_delivery_channels"]=["mobile_notification"]
    hass.config_entries=SimpleNamespace(async_entries=lambda domain:[])
    class Services:
        calls=[]
        def has_service(self,d,s):
            return d=="persistent_notification" and s=="create"
        async def async_call(self,d,s,payload,**kwargs):
            self.calls.append((d,s,payload))
    service=Services()
    hass.services=service
    manager=SimpleNamespace(
        hass=hass,settings=settings,entry=SimpleNamespace(entry_id="test"),
        _active=True,_tasks=set(),get_language=lambda _: "en",
    )
    timers=[]
    def schedule(hass,seconds,callback):
        slot={"seconds":seconds,"callback":callback,"cancel":False}
        timers.append(slot)
        return lambda:slot.__setitem__("cancel",True)
    hass.async_create_task=asyncio.create_task
    alert=AwayWindowAlert(manager,call_later=schedule)

    async def scenario():
        first.state="not_home"
        alert.observe(initial=True)
        assert timers==[],"Startup-away must not resend a prior trip"
        first.state="home"
        alert.observe()
        first.state="not_home"
        alert.observe()
        assert timers[-1]["seconds"]==60
        timers[-1]["callback"](None)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert len(service.calls)==1
        alert.observe()
        assert len(timers)==1,"No repeat for the same open contacts"
        first.state="home"
        alert.observe()
        first.state="not_home"
        alert.observe()
        assert len(timers)==2,"Next real departure may send"
        first.state="unavailable"
        alert.observe()
        assert timers[-1]["cancel"],"Unknown person cancels the pending departure"
        alert.stop()
    asyncio.run(scenario())


def test_no_hub_means_home_assistant_persistent_notification_without_room_audio(adapter):
    from custom_components.environment_manager.away_windows import deliver_notice
    hass,settings,*_=fixture_home()
    calls=[]
    class Services:
        def has_service(self,d,s):
            return (d,s)==("persistent_notification","create")
        async def async_call(self,d,s,data,**kwargs):
            calls.append((d,s,data))
    hass.services=Services()
    hass.config_entries=SimpleNamespace(async_entries=lambda domain:[])
    manager=SimpleNamespace(hass=hass,settings=settings,get_language=lambda _: "de")
    assert asyncio.run(deliver_notice(manager,(("binary_sensor.living_window","Wohnzimmer: Fenster"),)))
    assert len(calls)==1 and calls[0][:2]==("persistent_notification","create")
    assert "Fenster" in calls[0][2]["message"]
    assert "notification_id" in calls[0][2]


def test_away_alert_is_opt_in_and_not_a_motorized_window_command():
    from pathlib import Path
    root=Path(__file__).parents[1]/"custom_components/environment_manager"
    notifier=(root/"away_windows.py").read_text(encoding="utf-8")
    switch=(root/"switch.py").read_text(encoding="utf-8")
    assert "CONF_AWAY_WINDOWS_ALERT" in switch
    assert "settings.get(CONF_AWAY_WINDOWS_ALERT) is not True" in notifier
    assert '"notify", "send_message"' in notifier
    assert '"notify", "announcement_hub"' not in notifier or "async_submit_hub" in notifier
    assert "cover.close_cover" not in notifier and "cover.open_cover" not in notifier


def test_general_setup_has_person_and_channel_multi_select_when_hub_installed(monkeypatch, adapter):
    from test_room_setup import build
    from test_area_config_flow import _make_options
    options = _make_options(monkeypatch, adapter)
    options.hass._values["person.alex"] = MockState("person.alex","home")
    options.hass.config_entries = SimpleNamespace(async_entries=lambda domain:[
        SimpleNamespace(state="loaded")] if domain=="announcement_hub" else [])
    asyncio.run(options.async_step_init())
    form = asyncio.run(options.async_step_setup_rooms({"areas":["living"]}))
    assert form["step_id"] == "setup_room_sources"
    answer = {str(key): key.default for key in form["data_schema"]}
    form = asyncio.run(options.async_step_setup_room_sources(answer))
    assert form["step_id"] == "setup_general"
    fields = form["data_schema"]
    assert "away_open_window_alert" in fields
    assert fields["away_windows_target_people"].config.multiple is True
    assert fields["away_windows_delivery_channels"].config.multiple is True
    assert set(fields["away_windows_delivery_channels"].config.options) >= {
        "mobile_notification","mobile_tts","watch_notification","watch_tts"}
    options._values["away_open_window_alert"] = False
    defaults = {str(key): key.default for key in fields}
    invalid = asyncio.run(options.async_step_setup_general({
        **defaults,"away_open_window_alert":True,
        "away_windows_target_people":[]}))
    assert invalid["errors"]["base"]=="invalid_away_windows_recipients"
    valid = asyncio.run(options.async_step_setup_general({
        **defaults,"away_open_window_alert":True,
        "away_windows_target_people":["person.alex"],
        "away_windows_delivery_channels":["mobile_notification","watch_tts"]}))
    assert valid["completed"]["data"]["away_open_window_alert"] is True
    assert valid["completed"]["data"]["away_windows_target_people"] == ["person.alex"]
    assert valid["completed"]["data"]["away_windows_delivery_channels"] == [
        "mobile_notification","watch_tts"]


def test_all_shipped_locales_have_away_window_home_controls():
    from pathlib import Path
    import json
    component = Path(__file__).parents[1] / "custom_components/environment_manager"
    docs=[component/"strings.json",*sorted((component/"translations").glob("*.json"))]
    assert len(docs)==39
    for file in docs:
        doc=json.loads(file.read_text(encoding="utf-8"))
        assert "home_away_open_window_alert" in doc["entity"]["switch"],file
        assert set(doc["selector"]["away_window_delivery"]["options"]) == {
            "mobile_notification","mobile_tts","watch_notification","watch_tts",
            "tablet_notification","tablet_tts","other_notification","other_tts"}
        for key in ("away_open_window_alert","away_windows_target_people",
                    "away_windows_delivery_channels"):
            for section in ("config","options"):
                page=doc[section]["step"]["setup_general"]
                assert key in page["data"] and key in page["data_description"],(file,key)
