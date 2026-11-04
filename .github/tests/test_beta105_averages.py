"""Beta105: contributor-qualified averages, persistence, provenance, and RH fallback.

Uses the same actual Home Assistant unit fixtures as Beta65. No real
devices are operated and no Recorder/database history is queried.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import math
import runpy

ROOT=Path(__file__).resolve().parents[2]
fixture=runpy.run_path(str(ROOT/'.github/tests/test_beta65_data.py'))
env,mod,logic,dash,constants=(fixture[key] for key in
    ('env','history_mod','logic','dash','constants'))
R,ha,now=fixture['R'],fixture['hass'],fixture['now']
instant=now.timestamp()
room=logic.Room('room','Room',(logic.Window('binary_sensor.window','Window',False),),(
    R('sensor.rh_a','RH A','humidity',58.),
    R('sensor.rh_b','RH B','humidity',62.),
    R('sensor.co2','CO2','co2',760.),
    R('sensor.pm_a','PM A','pm25',12.),
    R('sensor.pm_b','PM B','pm25',20.),
    R('sensor.invalid','Invalid','humidity',None),
))
values=env._display_measurement_evidence(ha,room,indoor_t=None,
    temperature_inputs=None,temperature_entity=None,max_age=90)
assert values['humidity']=={
    'value':60.0,'source_ids':['sensor.rh_a','sensor.rh_b'],'source_count':2}
assert values['pm25']['value']==16.0 and values['pm25']['source_count']==2
assert values['co2']['source_count']==1
assert 'invalid' not in str(values)
h=mod.EnvironmentHistory()
assert h.add_average('room','humidity',values['humidity']['source_ids'],60.,now=instant)
assert not h.add_average('room','humidity',values['humidity']['source_ids'],61.,now=instant+60)
assert h.add_average('room','humidity',values['humidity']['source_ids'],61.,now=instant+900)
trend=h.average_trend('room','humidity',values['humidity']['source_ids'])
assert [point['v'] for point in trend]==[60.,61.]
old=h.snapshot()
assert old['version']==1 and len(old['averages']['room']['humidity']['points'])==2
restored=mod.EnvironmentHistory.restore(old,now=instant+900)
assert restored.average_trend('room','humidity',values['humidity']['source_ids'])==trend
assert restored.add_average('room','humidity',['sensor.rh_a','sensor.rh_c'],63.,now=instant+1800)
assert len(restored.average_trend('room','humidity',['sensor.rh_a','sensor.rh_c']))==1
assert restored.average_trend('room','humidity',values['humidity']['source_ids'])==[]
assert not restored.add_average('room','humidity',['sensor.rh_a'],58.,now=instant+2700)
assert len(restored.average_trend('room','humidity',['sensor.rh_a','sensor.rh_c']))==1
assert not restored.add_average('room','humidity',['sensor.bad','sensor.bad'],58.,now=instant+2700)
assert not restored.add_average('room','humidity',['sensor.a','sensor.b'],float('nan'),now=instant+2700)
broken={'version':1,'areas':{},'daily':{},'averages':{'room':{
    'humidity':{'sources':['sensor.x',{}], 'points':[{'t':instant,'v':50}]}}}}
assert mod.EnvironmentHistory.restore(broken,now=instant).averages=={}
for i in range(770):
    restored.add_average('room','pm25',['sensor.pm_a','sensor.pm_b'],
                         5+(i%3),now=instant+900*i)
points=restored.averages['room']['pm25']['points']
assert len(points)<=mod.AVG_MAX_POINTS
assert len(restored.average_trend('room','pm25',['sensor.pm_a','sensor.pm_b']))<=73
# One stale or invalid input never claims two contributors, even if 2 selected.
room_partial=replace(room,readings=(
    R('sensor.rh_a','RH A','humidity',58.),
    R('sensor.rh_b','RH B','humidity',None)))
assert env._display_measurement_evidence(ha,room_partial,indoor_t=None,
    temperature_inputs=None,temperature_entity=None,max_age=90)['humidity']['source_count']==1
# Mold fallback is a *derived* single room value; source list belongs to the
# real physical humidity contributors and is labeled as an average.
fallback=R('sensor.not_native_average','RH mean','humidity',60.,{
    'fallback_for_mold':True,'humidity_sensor_count':2})
plan=logic.evaluate((),(),(),(replace(room,readings=(fallback,)),),
                    constants.DEFAULT_THRESHOLDS)
plan=replace(plan,environment={'room':{'measurement_evidence':{
    'humidity':{**values['humidity'],'trend':trend}}}})
payload=dash.dashboard_snapshot(plan,constants.DEFAULT_THRESHOLDS)
item=payload['rooms'][0]['readings'][0]
assert item['average_evidence']['source_count']==2
assert item['average_evidence']['area_id']=='room'
assert item['average_evidence']['trend']==trend
print('BETA105_PERSISTED_AVERAGES_EXACT_SOURCE_MEMBERSHIP_AND_FALLBACK=PASS')
