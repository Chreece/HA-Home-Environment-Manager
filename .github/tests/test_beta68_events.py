"""Real source, deterministic event-load/lifecycle tests without hardware I/O.

--real-ha uses installed Home Assistant's dispatcher and indexed event helper.
The ordinary run uses a deliberately strict event-loop adapter, not hardware.
"""
from __future__ import annotations
import asyncio, ast, importlib, sys, tempfile, time, json
from pathlib import Path
from types import ModuleType, SimpleNamespace as N
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
REAL='--real-ha' in sys.argv
pkg=ModuleType('hem68test');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
# Only settings lookups are stubbed. Dispatch, entity listener code, state
# serialization scheduling and cancellation use the exact shipped source.
model=ModuleType('hem68test.equipment_model')
model.settings=lambda manager,spec:manager.settings.get(spec.identifier,{})
sys.modules[model.__name__]=model

if REAL:
 from homeassistant.core import HomeAssistant,callback
 from homeassistant.helpers.dispatcher import async_dispatcher_connect,async_dispatcher_send
else:
 def callback(fn): return fn
 ha=ModuleType('homeassistant');ha.__path__=[]
 core=ModuleType('homeassistant.core');core.callback=callback
 helpers=ModuleType('homeassistant.helpers');helpers.__path__=[]
 dispatch=ModuleType('homeassistant.helpers.dispatcher')
 events=ModuleType('homeassistant.helpers.event')
 def async_dispatcher_connect(hass,signal,fn):
  hass.signals[signal].append(fn)
  return lambda:hass.signals[signal].remove(fn)
 def async_dispatcher_send(hass,signal,*args):
  for fn in tuple(hass.signals[signal]): fn(*args)
 def track(hass,ids,fn):
  for key in ids:hass.watchers[key].append(fn)
  def remove():
   for key in ids:hass.watchers[key].remove(fn)
  return remove
 dispatch.async_dispatcher_connect=async_dispatcher_connect
 dispatch.async_dispatcher_send=async_dispatcher_send
 events.async_track_state_change_event=track
 sys.modules.update({'homeassistant':ha,'homeassistant.core':core,
  'homeassistant.helpers':helpers,'homeassistant.helpers.dispatcher':dispatch,
  'homeassistant.helpers.event':events})

updates=importlib.import_module('hem68test.equipment_updates')
entities=importlib.import_module('hem68test.equipment_entity')
const=importlib.import_module('hem68test.const')

class FakeStates:
 def __init__(self,hass):self.items={};self.hass=hass
 def get(self,key):return self.items.get(key)
 def async_set(self,key,value,attrs=None):
  old=self.items.get(key);new=N(state=value,attributes=attrs or {})
  self.items[key]=new
  event=N(data={'entity_id':key,'old_state':old,'new_state':new})
  for fn in tuple(self.hass.watchers[key]):fn(event)

class ProbeBase:
 async def async_added_to_hass(self):pass
 def async_on_remove(self,fn):self.cleanups.append(fn)
 def async_write_ha_state(self):self.writes+=1
 async def remove(self):
  for fn in reversed(self.cleanups):fn()
  self.cleanups.clear()

class Probe(entities.EquipmentEntity,ProbeBase):
 def __init__(self,manager,spec):
  self.hass=manager.hass;self._manager=manager;self._spec=spec
  self.cleanups=[];self.writes=0

async def main():
 if REAL:
  tmp=tempfile.TemporaryDirectory();hass=HomeAssistant(tmp.name)
 else:
  hass=N(loop=asyncio.get_running_loop(),signals=defaultdict(list),watchers=defaultdict(list))
  hass.states=FakeStates(hass)
 manager=N(hass=hass,entry=N(entry_id='entry'),settings={})
 runtime=N(hass=hass,manager=manager,_active=True,statuses={},_fan_allocations={},_pid_offline_previews={})
 runtime._presentation_updates=updates.EquipmentUpdates(runtime)
 # Extract actual source _status, not a test substitute for its decisions.
 tree=ast.parse((ROOT/'equipment_runtime.py').read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='EquipmentRuntime')
 fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_status')
 ns={'Any':object}
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'equipment_runtime.py','exec'),ns)
 status=ns['_status']
 specs=[N(identifier=f'device-{i}',source_entities=(f'climate.native_{i}',)) for i in range(24)]
 probes=[]
 for sp in specs:
  for _ in range(40):
   p=Probe(manager,sp);await p.async_added_to_hass();probes.append(p)
 # Real callback is left alive to prove HEM does not broadcast the whole
 # entry from an equipment-only status update.
 global_calls=[]
 undo=async_dispatcher_connect(hass,f'{const.SIGNAL_UPDATED}_entry',lambda:global_calls.append(True))
 for i in range(1000):status(runtime,specs[0],'window_close_warmup',remaining=60-i/1000)
 assert runtime.statuses[specs[0].identifier]['remaining']<60
 await asyncio.sleep(.03)
 assert sum(p.writes for p in probes)==40, sum(p.writes for p in probes)
 assert not global_calls
 # 24 simultaneous devices, multiple changes per turn: one presentation per
 # device, not all 960 entities for each of 12,000 statuses.
 before=sum(p.writes for p in probes)
 started=time.monotonic()
 for i in range(500):
  for sp in specs:status(runtime,sp,'window_close_warmup',remaining=i)
 await asyncio.sleep(.03)
 assert sum(p.writes for p in probes)-before==960
 assert not runtime._presentation_updates.pending and runtime._presentation_updates.handle is None
 # Physical sources use indexed subscriptions, ignore unrelated traffic,
 # replace a changed upstream ID and clean up on unload.
 physical=probes[0];physical._watch_native_updates()
 manager.settings[specs[0].identifier]={'power_switch_entity':'switch.plug_a'}
 physical._equipment_update();await asyncio.sleep(.02)
 count=physical.writes
 for i in range(10000):hass.states.async_set('sensor.unrelated',str(i))
 await asyncio.sleep(.02)
 assert physical.writes==count
 for i in range(1000):hass.states.async_set('climate.native_0','off',{'current_temperature':20+i/1000})
 await asyncio.sleep(.03)
 assert physical.writes==count+1,(REAL,physical.writes,count)
 manager.settings[specs[0].identifier]['power_switch_entity']='switch.plug_b'
 physical._equipment_update();await asyncio.sleep(.02);count=physical.writes
 hass.states.async_set('switch.plug_a','on');await asyncio.sleep(.02)
 assert physical.writes==count
 hass.states.async_set('switch.plug_b','on');await asyncio.sleep(.02)
 assert physical.writes==count+1
 # Scheduled presentation must be cancelled before detached entities write.
 status(runtime,specs[0],'window_open_pause')
 runtime._active=False;runtime._presentation_updates.close()
 for p in probes:await p.remove()
 count=sum(p.writes for p in probes)
 hass.states.async_set('climate.native_0','dry')
 async_dispatcher_send(hass,updates.controller_signal('entry','device-0'))
 await asyncio.sleep(.03)
 assert sum(p.writes for p in probes)==count
 undo()
 if REAL:
  await hass.async_stop(force=True);tmp.cleanup()
 print(json.dumps({'test':'real-ha-event-bus' if REAL else 'strict-event-adapter',
  'logical_entities':960,'status_changes':12000,'presentation_writes':960,
  'unrelated_events':10000,'writes_for_unrelated_events':0,
  'source_burst_events':1000,'source_burst_writes':1,
  'unload_leaks':0,'seconds':round(time.monotonic()-started,3)}))

asyncio.run(main())
