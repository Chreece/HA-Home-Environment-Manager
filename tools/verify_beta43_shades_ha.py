"""Native Home Assistant 2026.10 window-shade discovery and opt-in entities.

Real area/entity registries and CoverEntityFeature, no external cover integration,
no physical service calls or actuation during setup/opt-in configuration.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import MappingProxyType, SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntries, ConfigEntry, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers import entity_registry as er
from custom_components.environment_manager import room_sources
from custom_components.environment_manager.shade_cooling import (
    evaluate_conditions, eligible_shade,
)
from custom_components.environment_manager.switch import ShadeCoolingSwitch
from custom_components.environment_manager.number import ShadeCoolingNumber
from custom_components.environment_manager.device_controls import update_device_setting
from custom_components.environment_manager.logic import Window


def entry(domain, identity, data):
    return ConfigEntry(data=data,options={},domain=domain,entry_id=identity,
        title=identity,source=SOURCE_USER,unique_id=identity,version=1,
        minor_version=1,discovery_keys=MappingProxyType({}),subentries_data=())


async def test(directory):
    hass=HomeAssistant(directory)
    hass.config_entries=ConfigEntries(hass,{})
    dr.async_setup(hass)
    await ar.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    area=ar.async_get(hass).async_create("Solar-shading room")
    native=entry("demo","physical-shutter",{});
    hass.config_entries._entries[native.entry_id]=native
    device=dr.async_get(hass).async_get_or_create(
        config_entry_id=native.entry_id,identifiers={("demo","roller-1")},
        name="Room window shade",
    )
    dr.async_get(hass).async_update_device(device.id,area_id=area.id)
    registration=er.async_get(hass)
    ids={}
    sources=[
        ("shade","cover","shutter","open",{"supported_features":int(CoverEntityFeature.CLOSE)}),
        ("garage","cover","garage","open",{"supported_features":int(CoverEntityFeature.CLOSE)}),
        ("window","binary_sensor","window","off",{}),
        ("temperature","sensor","temperature","27",{"unit_of_measurement":"°C"}),
    ]
    for name,domain,klass,state,additional in sources:
        item=registration.async_get_or_create(domain,"demo",name,
            config_entry=native,device_id=device.id,
            original_name=name,original_device_class=klass)
        hass.states.async_set(item.entity_id,state,{
            **additional,"device_class":klass,
        })
        ids[name]=item.entity_id
    hass.states.async_set("sun.sun","above_horizon",{
        "elevation":35.,"azimuth":180.,
    })

    choices=room_sources.choices(hass,area.id)
    assert [item["value"] for item in choices["shades"]]==[ids["shade"]]
    assert ids["garage"] not in [item["value"] for item in choices["shades"]]
    assert ids["shade"] not in [item["value"] for item in choices["windows"]]
    selected={
        key:([ids["shade"]] if key=="shades" else
             [ids["window"]] if key=="windows" else
             [ids["temperature"]] if key=="temperature" else [])
        for key in room_sources.GROUPS
    }
    settings={"areas":[area.id],"room_sources":{area.id:selected},
              "shade_rooms":{area.id:{"enabled":False}}}
    managed=entry("environment_manager","manager-shading",settings)
    hass.config_entries._entries[managed.entry_id]=managed

    class Manager:
        _active=False
        @property
        def settings(self):
            return {**self.entry.data,**self.entry.options}
    manager=Manager();manager.hass=hass;manager.entry=managed
    managed.runtime_data=manager
    toggle=ShadeCoolingSwitch(manager,managed.entry_id,area.id)
    temp=ShadeCoolingNumber(manager,managed.entry_id,area.id,"close_above_c")
    solar=ShadeCoolingNumber(manager,managed.entry_id,area.id,"min_sun_elevation")
    assert not toggle.is_on
    assert temp.native_value==25 and solar.native_value==10
    assert toggle.unique_id==managed.entry_id+"_area_"+area.id+"_shade_cooling_enabled"
    assert toggle.device_info["identifiers"]=={("environment_manager",managed.entry_id+"_area_"+area.id)}
    assert eligible_shade(hass,area.id,ids["shade"],tuple(selected["shades"]))[0]
    assert not eligible_shade(hass,area.id,ids["garage"],(ids["garage"],))[0]
    await toggle.async_turn_on()
    assert toggle.is_on
    await temp.async_set_native_value(26)
    assert temp.native_value==26
    windows=(Window(ids["window"],"Window",False),)
    state,evidence=evaluate_conditions(active=True,
        selected_shades=(ids["shade"],),temperature_c=27,windows=windows,
        sun_state=hass.states.get("sun.sun"),threshold=temp.native_value,
        min_sun_elevation=solar.native_value)
    assert state=="closing_recommended" and evidence["sun_elevation"]==35.
    await toggle.async_turn_off()
    assert not toggle.is_on
    assert hass.states.get(ids["shade"]).state=="open", "Physical shade untouched"
    assert hass.services.has_service("cover","close_cover") is False
    await hass.async_block_till_done()
    await hass.async_stop(force=True)
    print("HA 2026.10: exact native shutter discovery, opt-in room controls and no physical writes: PASS")


if __name__=="__main__":
    with TemporaryDirectory(prefix="shade-cooling-") as tmp:
        asyncio.run(test(tmp))
