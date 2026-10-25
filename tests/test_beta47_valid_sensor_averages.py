"""Beta47: every numeric room source uses valid-only means and exposes discarded inputs."""
from __future__ import annotations

import asyncio

import pytest

from test_discovery import MockState, FakeHass, adapter
from test_mold_device_controls import model, mold_editor
from custom_components.environment_manager.logic import Reading, Room, Weather, Window, evaluate
from custom_components.environment_manager.room_sources import (
    aggregate, room_temperature_evidence,
)


def test_selected_room_temperature_ignores_unknown_stale_outlier_and_wrong_area(adapter):
    good = MockState("sensor.good_temperature", 20, device_class="temperature", unit="°C")
    converted = MockState("sensor.converted_temp", 77, device_class="temperature", unit="°F")
    missing = MockState("sensor.offline_temperature", "unavailable", device_class="temperature", unit="°C")
    stale = MockState("sensor.stale_temperature", 23, device_class="temperature", unit="°C", hours_old=4)
    foreign = MockState("sensor.foreign_temperature", 30, device_class="temperature", unit="°C")
    home = FakeHass([good,converted,missing,stale,foreign],{
        good.entity_id:"living",converted.entity_id:"living",missing.entity_id:"living",
        stale.entity_id:"living",foreign.entity_id:"elsewhere",
    })
    inputs = [good.entity_id,converted.entity_id,missing.entity_id,stale.entity_id,foreign.entity_id]
    reading, status = aggregate(home, inputs, "living", "temperature", 90)
    assert reading == pytest.approx(22.5)
    assert status == "selected_partial_mean"
    value, evidence = room_temperature_evidence(
        home,{"room_sources":{"living":{"temperature":inputs}}},"living", age_minutes=90)
    assert value == pytest.approx(22.5) and evidence["partial"]
    assert evidence["valid_count"] == 2 and evidence["ignored_count"] == 3
    assert {p["reason"] for p in evidence["invalid_sources"]} == {
        "sensor_unavailable","invalid_or_stale_temperature","sensor_wrong_area"}
    good.state = "unknown"
    converted.state = "nan"
    assert aggregate(home, inputs, "living", "temperature", 90)[0] is None


def test_all_other_measured_metrics_are_averaged_with_unit_normalization(adapter):
    states = [
        MockState("sensor.humidity_good", 55, device_class="humidity", unit="%"),
        MockState("sensor.humidity_bad", "unavailable", device_class="humidity", unit="%"),
        MockState("sensor.humidity_second", 75, device_class="humidity", unit="%"),
        MockState("sensor.humidity_invalid", 150, device_class="humidity", unit="%"),
        MockState("sensor.co2_one", 1100, device_class="co2", unit="ppm"),
        MockState("sensor.co2_two", 1300, device_class="co2", unit="ppm"),
        MockState("sensor.pm25_one", 0.02, device_class="pm25", unit="mg/m³"),
        MockState("sensor.pm25_two", 10, device_class="pm25", unit="µg/m³"),
        MockState("sensor.pressure_one", 100000, device_class="atmospheric_pressure", unit="Pa"),
        MockState("sensor.pressure_two", 1020, device_class="atmospheric_pressure", unit="hPa"),
    ]
    home=FakeHass(states,{s.entity_id:"living" for s in states})
    for inputs,group,expected in (
        ([s.entity_id for s in states[:4]],"humidity",65),
        ([s.entity_id for s in states[4:6]],"air_quality",1200),
        ([s.entity_id for s in states[6:8]],"air_quality",15),
        ([s.entity_id for s in states[8:]],"pressure",1010),
    ):
        value, status=aggregate(home,inputs,"living",group,90)
        assert value == pytest.approx(expected)
        assert status in ("selected_partial_mean","selected_mean")
    states[0].state="unknown"
    states[2].state="unavailable"
    assert aggregate(home,[s.entity_id for s in states[:4]],"living","humidity",90)[0] is None


def test_ventilation_uses_one_mean_per_pollutant_not_any_high_sensor():
    room=Room("living","Living",(
        Window("binary_sensor.win","Window",False),
    ), (
        Reading("sensor.low","Low CO2","co2",700),
        Reading("sensor.high","High CO2","co2",1700),
    ))
    outside=(Reading("sensor.pm","PM","pm25",8),)
    weather=(Weather("weather.home","sunny",20,45,8),)
    result=evaluate(outside,weather,(),(room,))
    assert result.status == "open"  # mean = 1200, threshold includes equality
    with_missing=Room(room.area_id,room.name,room.windows,(
        Reading("sensor.low","Low CO2","co2",None),
        Reading("sensor.high","High CO2","co2",1700),
    ))
    result=evaluate(outside,weather,(),(with_missing,))
    assert result.status == "open"
    with_valid_low=Room(room.area_id,room.name,room.windows,(
        Reading("sensor.low","Low CO2","co2",700),
        Reading("sensor.high","High CO2","co2",1500),
    ))
    assert evaluate(outside,weather,(),(with_valid_low,)).status == "idle"


def test_weather_numeric_mean_ignores_unavailable_but_rain_remains_hazard():
    room=Room("living","Living",(Window("binary_sensor.win","Window",True),),
              (Reading("sensor.rh","RH","humidity",55),))
    outside=(Reading("sensor.pm","PM","pm25",8),)
    w=(Weather("weather.offline",None,None),
       Weather("weather.good","sunny",10,50,4),
       Weather("weather.second","sunny",30,50,4))
    report=evaluate(outside,w,(),(room,),
                    {"min_outdoor_temp":0,"max_outdoor_temp":25})
    assert report.status == "idle"  # average 20 C, offline condition ignored
    bad=evaluate(outside,w+(Weather("weather.rain","rainy",None),),(),(room,),
                 {"min_outdoor_temp":0,"max_outdoor_temp":25})
    assert bad.status == "close"  # rain is a categorical hazard, never averaged


def test_mold_button_uses_multi_room_and_weather_means_with_offline_member(mold_editor):
    module, Err=mold_editor
    manager, revisions, _=model()
    extra=MockState("sensor.living_second_temperature",23,device_class="temperature",unit="°C")
    manager.hass._values[extra.entity_id]=extra
    manager.hass._entity_areas[extra.entity_id]="living"
    second_weather=MockState("weather.backup","sunny")
    second_weather.attributes.update({"temperature":8,"temperature_unit":"°C"})
    manager.hass._values[second_weather.entity_id]=second_weather
    manager.entry.options.update({
        "room_sources":{"living":{"temperature":["sensor.living_temperature",extra.entity_id]}},
        "weather_entities":["weather.home","weather.backup"],
    })
    calibrated=asyncio.run(module.async_recalculate_mold_factor(manager,"living"))
    assert calibrated == pytest.approx(15/6.5)
    info=manager.settings["mold_rooms"]["living"]
    assert info["indoor_temperature_entity"] is None
    assert info["indoor_temperature_entities"] == ["sensor.living_temperature",extra.entity_id]
    assert info["outdoor_weather_entity"] is None
    assert info["outdoor_weather_entities"] == ["weather.home","weather.backup"]
    assert info["calibrated_indoor_c"] == 22
    assert info["calibrated_outdoor_c"] == 7
    extra.state="unavailable"
    second_weather.attributes.pop("temperature")
    updated=asyncio.run(module.async_recalculate_mold_factor(manager,"living"))
    assert updated == pytest.approx((21-6)/(13.5-6))
    assert len(revisions) == 2
    manager.hass.states.get("sensor.living_temperature").state="unknown"
    before=dict(manager.settings["mold_rooms"]["living"])
    with pytest.raises(Err,match="Indoor temperature"):
        asyncio.run(module.async_recalculate_mold_factor(manager,"living"))
    assert manager.settings["mold_rooms"]["living"] == before


def test_mold_estimate_uses_calibrated_provider_mean_with_partial_weather():
    from custom_components.environment_manager.mold import estimate_mold_for_room
    room=Room("living","Living",(),(
        Reading("sensor.rh_a","RH A","humidity",60),
        Reading("sensor.rh_b","RH B","humidity",None),
    ))
    cfg={"calibration_factor":2.0,"outdoor_weather_entities":["weather.a","weather.b"],
         "indoor_temperature_entities":["sensor.ta","sensor.tb"]}
    report=estimate_mold_for_room(room,21,(
        Weather("weather.a","sunny",6),Weather("weather.b",None,None)),cfg)
    assert report.value is not None
    assert report.details["status"] == "ready"
    assert report.details["outdoor_weather_entities"] == ["weather.a","weather.b"]
    unavailable=estimate_mold_for_room(room,21,(
        Weather("weather.a",None,None),Weather("weather.b",None,None)),cfg)
    assert unavailable.value is None
    assert "outdoor_temperature" in unavailable.details["missing_inputs"]
