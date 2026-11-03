"""Beta95: full event/temperature simulations of the production room monitor.

No physical devices, HA service calls, network requests or guessed AQ sensor
readings. Test timed wake, actual long-absence return, outdoor holds, explicit
opening, heating/cooling temperature slopes and original HVAC setpoints.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace as N
import sys

ROOT=Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Window:
    entity_id:str
    name:str
    opened:bool|None

@dataclass(frozen=True)
class Reason:
    code:str
    label:str=''
    value:str=''

@dataclass(frozen=True)
class Recommendation:
    action:str
    area_id:str
    area_name:str
    windows:tuple[Window,...]
    reasons:tuple[Reason,...]

pkg=ModuleType('beta95_room')
pkg.__path__=[]
const=ModuleType('beta95_room.const')
const.SUPPORTED_AIR_METRICS=("aqi","co2","pm25","pm10","voc","voc_parts","no2","o3","so2")
source=ModuleType('beta95_room.room_sources')
source.selected=lambda settings,area,group:settings.get('room_sources',{}).get(area,{}).get(group)
equipment=ModuleType('beta95_room.equipment_model')
sys.modules.update({name:module for name,module in (
    ('beta95_room',pkg),('beta95_room.const',const),
    ('beta95_room.room_sources',source),
    ('beta95_room.equipment_model',equipment)
)})
tree=ast.parse((ROOT/'room_ventilation.py').read_text())
tree.body=[node for node in tree.body
           if not isinstance(node,ast.ImportFrom) or node.level==0]
loaded=ModuleType('beta95_room.room_ventilation')
loaded.__package__='beta95_room'
sys.modules[loaded.__name__]=loaded
scope=loaded.__dict__
scope.update({'Reason':Reason,'Recommendation':Recommendation,'Window':Window})
exec(compile(ast.fix_missing_locations(tree),'room_ventilation.py','exec'),scope)
Monitor=scope['RoomVentilationMonitor']
assert scope['VACANCY_SECONDS']==7200

clock={'at':10000.}
monitor=Monitor(clock=lambda:clock['at'])
closed=(Window('binary_sensor.bedroom_window','Bedroom window',False),)
opened=(Window('binary_sensor.bedroom_window','Bedroom window',True),)

def observe(occupancy='occupied',sleeping=False,*,air=False,external=True,
            windows=closed,temp=21.,heat=20.,cool=26.,area='bedroom'):
    return monitor.observe(
        area=area,name='Bedroom',windows=windows,occupancy=occupancy,
        sleeping=sleeping,has_air_sensor=air,outside_safe=external,
        temperature_c=temp,heat_target_c=heat,cool_target_c=cool,
    )

# Cold-start current occupancy is NOT evidence of a newly arriving person.
status,rec=observe()
assert rec is None and status['air_refresh_status']=='time_based_monitoring'

# Verified vacancy is explicitly timed, not inferred from absence of motion.
clock['at']+=5
observe('unoccupied')
clock['at']+=3600
assert observe('occupied')[1] is None
clock['at']+=5
observe('unoccupied')
clock['at']+=7201
status,rec=observe('occupied',external=False)
assert rec is None and status['pending_reason']=='air_refresh_return'
assert status['air_refresh_status']=='outdoor_or_window_not_verified'
clock['at']+=100
status,rec=observe()
assert rec is not None and rec.action=='open'
assert rec.reasons[0].code=='air_refresh_return'
assert [x.entity_id for x in rec.windows]==['binary_sensor.bedroom_window']
assert not any(k in status for k in ('co2_ppm','estimated_co2','measured_aqi'))
monitor.acknowledge('bedroom','air_refresh_return')
assert observe()[1] is None
assert monitor._rooms['bedroom'].pending is None

# A short vacancy after a previous reminder must not cause a second nudge.
clock['at']+=10
observe('unoccupied')
clock['at']+=1800
assert observe()[1] is None
assert observe('unoccupied')[1] is None
clock['at']+=7200
assert observe()[1] is None # four-hour per-room antispam

# Once a real sleep transition ends, the room can get a new refresh reminder.
clock['at']+=14400
observe('occupied',True)
clock['at']+=20
status,rec=observe('occupied',False)
assert rec and rec.reasons[0].code=='air_refresh_wake'
assert status['air_refresh_status']=='refresh_recommended'
monitor.acknowledge('bedroom','air_refresh_wake')
assert observe()[1] is None

# A local AQ sensor, even temporarily unavailable, disables the proxy.
clock['at']+=20000
observe('occupied',True,air=True)
status,rec=observe('occupied',False,air=True)
assert rec is None and status['air_refresh_status']=='indoor_air_sensor_present'
assert not status['has_indoor_pollutant_sensor'] is False

# Unknown occupancy cannot fake a return after long absence, and a newly
# observed already-awake room does not fake a wake event.
second=Monitor(clock=lambda:clock['at'])
assert second.observe(area='kitchen',name='Kitchen',windows=closed,
    occupancy='occupied',sleeping=False,has_air_sensor=False,
    outside_safe=True,temperature_c=21,heat_target_c=None,cool_target_c=None)[1] is None
second.observe(area='kitchen',name='Kitchen',windows=closed,
    occupancy='unoccupied',sleeping=False,has_air_sensor=False,
    outside_safe=True,temperature_c=21,heat_target_c=None,cool_target_c=None)
clock['at']+=10000
second.observe(area='kitchen',name='Kitchen',windows=closed,
    occupancy='unknown',sleeping=None,has_air_sensor=False,
    outside_safe=True,temperature_c=21,heat_target_c=None,cool_target_c=None)
status,rec=second.observe(area='kitchen',name='Kitchen',windows=closed,
    occupancy='occupied',sleeping=False,has_air_sensor=False,
    outside_safe=True,temperature_c=21,heat_target_c=None,cool_target_c=None)
assert rec is None and status['air_refresh_status']=='time_based_monitoring'

# Heat loss: a verified OPEN plus sustained trend near the actual heat target.
energy=Monitor(clock=lambda:clock['at'])
def energy_observe(windows,temp,heat=20.,cool=26.,external=True):
    return energy.observe(area='bath',name='Bathroom',windows=windows,
        occupancy='unknown',sleeping=None,has_air_sensor=True,
        outside_safe=external,temperature_c=temp,
        heat_target_c=heat,cool_target_c=cool)
assert energy_observe(opened,21.7)[1] is None
clock['at']+=90
assert energy_observe(opened,21.0)[1] is None,'at least 180s evidence'
clock['at']+=100
status,rec=energy_observe(opened,20.7,external=False)
assert rec and rec.action=='close'
assert rec.reasons[0].code=='window_heat_loss'
assert status['window_energy_direction']=='window_heat_loss'
assert status['automatic_device_actuation'] is False
assert rec.reasons[0].value.startswith('20.7 °C / 20.0 °C')
# Closing resets the alert and removes any pending advice.
assert energy_observe(closed,20.7)[1] is None
assert energy_observe(opened,20.7)[1] is None

# Cooling: only a measured warming trend near a real cooling setpoint.
cooling=Monitor(clock=lambda:clock['at'])
def cool_test(temp,windows=opened):
    return cooling.observe(area='office',name='Office',windows=windows,
        occupancy='occupied',sleeping=False,has_air_sensor=True,
        outside_safe=True,temperature_c=temp,
        heat_target_c=None,cool_target_c=25.)
assert cool_test(23.5)[1] is None
clock['at']+=200
status,rec=cool_test(24.35)
assert rec and rec.reasons[0].code=='window_cooling_loss'
assert status['window_energy_direction']=='window_cooling_loss'
assert cool_test(23.0,closed)[1] is None

# No temperature or no real heat/cool capability -> no fake thermal warning.
dry=Monitor(clock=lambda:clock['at'])
for temp in (21.,19.,17.):
    status,rec=dry.observe(area='dry',name='DRY',windows=opened,
        occupancy='occupied',sleeping=False,has_air_sensor=False,
        outside_safe=True,temperature_c=temp,heat_target_c=None,
        cool_target_c=None)
    assert rec is None and status['window_energy_status']=='temperature_or_thermal_target_unavailable'
    clock['at']+=190

# No AQ sensor: true. RH-only, humidity and light are not pollutant sensors.
room=N(area_id='bedroom',readings=[
    N(entity_id='sensor.rh',metric='humidity',value=55),
    N(entity_id='sensor.light',metric='illuminance',value=50)])
assert not scope['has_indoor_air_sensor'](room,{})
room.readings.append(N(entity_id='sensor.co2',metric='co2',value=None))
assert scope['has_indoor_air_sensor'](room,{})
room.readings.pop()
assert scope['has_indoor_air_sensor'](room,{'room_sources':{
    'bedroom':{'air_quality':['sensor.offline_co2']}}})
assert not scope['has_indoor_air_sensor'](room,{'room_sources':{
    'bedroom':{'air_quality':[]}}})

# Production thermal target helper excludes DRY-only climate even if it
# advertises a generic current_temperature attribute.
spec=N(area_id='bedroom')
equipment.specs=lambda manager:(spec,)
equipment.settings=lambda manager,sp:{'control_mode':'pid'}
equipment.capabilities=lambda manager,sp:N(
    domain='climate',modes=('off','dry'),temperature=False,temperature_range=False)
equipment.targets=lambda manager,sp,cap,cfg,plan:{'heat':20.,'cool':26.}
assert scope['thermal_targets'](N(), 'bedroom',{})==(None,None)
equipment.capabilities=lambda manager,sp:N(
    domain='climate',modes=('off','heat','cool'),temperature=True,temperature_range=False)
assert scope['thermal_targets'](N(),'bedroom',{})==(20.,26.)
assert scope['thermal_targets'](N(),'other',{})==(None,None)

print('BETA95_WAKE_RETURN_NO_AQ_FAKE_SENSOR_AND_OPEN_WINDOW_THERMAL_TREND=PASS')
