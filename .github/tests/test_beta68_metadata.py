"""Metadata-only discovery and legacy window reads must stay bounded."""
import ast,math
from collections.abc import Callable,Iterable
from pathlib import Path
from types import SimpleNamespace as N
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
def functions(filename,names,ns):
 tree=ast.parse((ROOT/filename).read_text());body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert len(body)==len(names)
 exec(compile(ast.Module(body=body,type_ignores=[]),filename,'exec'),ns)
sp=N(identifier='device',source_entities=('humidifier.real',),area_id='room')
hass=N();manager=N(hass=hass);cleanups=[]
entry=N(runtime_data=manager,async_on_unload=cleanups.append)
watch={};added=[];scans=[]
def track(hass,ids,cb):
 watch.update(ids=set(ids),callback=cb)
 return lambda:watch.clear()
def candidate():
 scans.append(1);return [N(_attr_unique_id='new-capability')]
ns={'Any':object,'Callable':Callable,'Iterable':Iterable,'callback':lambda fn:fn,
 'equipment':N(specs=lambda m:[sp]),'async_track_state_change_event':track,
 'async_add_grouped_entities':lambda m,add,items:added.extend(items)}
functions('equipment_feature_registration.py',('register_late_capabilities',),ns)
ns['register_late_capabilities'](hass,entry,None,[],candidate)
assert watch['ids']=={'humidifier.real'}
old=N(attributes={'device_class':'unknown','supported_features':0})
new=N(attributes={'device_class':'dehumidifier','supported_features':0})
watch['callback'](N(data={'entity_id':'humidifier.real','old_state':old,'new_state':new}))
assert len(scans)==len(added)==1
for i in range(10000):
 watch['callback'](N(data={'entity_id':'humidifier.real','old_state':N(attributes={**new.attributes,'humidity':i}), 'new_state':N(attributes={**new.attributes,'humidity':i+1})}))
assert len(scans)==1
watch['callback'](N(data={'entity_id':'humidifier.real','old_state':new,'new_state':N(attributes={**new.attributes,'supported_features':1})}))
assert len(scans)==2 and len(added)==1
for cleanup in cleanups:cleanup()
assert not watch
# Existing discovered room contacts are read from the captured plan. No
# whole-home discovery or permission to turn ON is inferred from absence.
now=1000.
state=N(state='off',last_changed=datetime.fromtimestamp(800,tz=timezone.utc))
runtime=N(manager=N(settings={},plan=N(environment={},rooms=(N(area_id='room',windows=(N(entity_id='binary_sensor.window'),)),),climate_rooms=())),hass=N(states=N(get=lambda key:state)),clock=lambda:now)
ns={'Any':object,'math':math,'model':N(), 'RESUME_SECONDS':60.,'POLICY_KEY':'pause_on_window_open',
 'selected':lambda *args:None,'entity_area':lambda *args:'room','is_window':lambda *args:True}
functions('equipment_window.py',('_stamp','evaluate'),ns)
p=ns['evaluate'](runtime,sp,{'pause_on_window_open':True})
assert p['contacts']==['binary_sensor.window'] and not p['blocked']
state.state='on';assert ns['evaluate'](runtime,sp,{'pause_on_window_open':True})['stop_requested']
runtime.manager.plan=N(environment={},rooms=(),climate_rooms=())
p=ns['evaluate'](runtime,sp,{'pause_on_window_open':True});assert p['blocked'] and p['status']=='window_state_unknown'
print('PASS humidity-class arrival discovers once; 10000 numeric changes do not rebuild controls; legacy contacts use captured inventory; missing plan holds safely')
