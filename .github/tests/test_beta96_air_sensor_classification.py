"""Beta96: light, sound and airflow are not indoor pollutant measurements.

Execute the production source classifier on HA-like states, including genuine
CO2/PM/VOC sensors, unavailable devices, and absence of any AQ source.
"""
from __future__ import annotations
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
prior=runpy.run_path(str(ROOT/'.github/tests/test_beta95_room_ventilation.py'))
classifier=prior['scope']['has_indoor_air_sensor']
pkg='beta95_room'
discovery=ModuleType(pkg+'.discovery')
discovery.supported_metric=lambda hass,state,*,outdoor=False: (
    state.attributes.get('metric'))
discovery._device_class=lambda hass,state:state.attributes.get('device_class','')
sys.modules[discovery.__name__]=discovery

def state(value,klass,metric=None):
    return N(state=value,attributes={
        'device_class':klass,'metric':metric
    })
values={
    'sensor.bedroom_lux':state('10','illuminance','illuminance'),
    'sensor.bedroom_noise':state('35','sound_pressure','sound'),
    'sensor.bedroom_air_speed':state('0.2','',None),
    'sensor.bedroom_co2':state('unavailable','carbon_dioxide','co2'),
    'sensor.bedroom_radon':state('40','radon',None),
    'sensor.bedroom_pm25':state('4','pm25','pm25'),
}
hass=N(states=N(get=lambda entity:values.get(entity)))
room=N(area_id='bedroom',readings=[])

def configured(*ids):
    return {'room_sources':{'bedroom':{'air_quality':list(ids)}}}

# Only lux/noise/air-speed are *real sensors*, but none measure indoor
# pollution. Those rooms still need time/occupancy ventilation reminders.
for ids in (
    ('sensor.bedroom_lux',),
    ('sensor.bedroom_lux','sensor.bedroom_noise'),
    ('sensor.bedroom_lux','sensor.bedroom_noise','sensor.bedroom_air_speed'),
):
    assert not classifier(room,configured(*ids),hass),ids

# A source that identifies a real pollutant counts even if it is currently
# unavailable. Do not assert that indoor CO2 or other pollutants are zero.
for entity in ('sensor.bedroom_co2','sensor.bedroom_pm25','sensor.bedroom_radon'):
    assert classifier(room,configured(entity),hass),entity

# Selected missing source is ambiguous: avoid silently inventing no sensor.
assert classifier(room,configured('sensor.unknown_selected_source'),hass)

# A room that has a measured CO2 or PM device also suppresses proxy timing,
# regardless of whether its reported value is currently unavailable.
room.readings=[N(entity_id='sensor.bedroom_co2',metric='co2',value=None)]
assert classifier(room,configured('sensor.bedroom_lux'),hass)
room.readings=[N(entity_id='sensor.bedroom_light',metric='illuminance',value=150)]
assert not classifier(room,configured('sensor.bedroom_lux'),hass)
assert not classifier(room,configured(),hass)
assert not classifier(room,{},hass)

print('BETA96_LUX_SOUND_AIRSPEED_NOT_POLLUTANT_CO2_UNAVAILABLE_STILL_PRESENT=PASS')
