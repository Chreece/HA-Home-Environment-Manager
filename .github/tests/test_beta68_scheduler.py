"""Exact manager callbacks: bounded source bursts and no self feedback."""
import ast,asyncio,sys,json
from pathlib import Path
from types import ModuleType,SimpleNamespace as N
ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType('schedule68');pkg.__path__=[];sys.modules[pkg.__name__]=pkg
sources=ModuleType('schedule68.room_sources');sources.native=lambda hass,eid:not eid.startswith('sensor.hem_');sys.modules[sources.__name__]=sources
ns={'__name__':'schedule68.manager','__package__':'schedule68','callback':lambda f:f,'Event':object}
tree=ast.parse((ROOT/'manager.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AirQualityManager')
names=('_queue_source_refresh','_flush_source_refresh','_on_state_changed')
nodes=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'manager.py','exec'),ns)
class Manager:
 pass
for name in names:setattr(Manager,name,ns[name])
async def main():
 m=Manager();m._active=True;m._source_refresh_handle=None;m.hass=N(loop=asyncio.get_running_loop())
 m._tracked={'sensor.native','sensor.hem_logical'};count=[];observations=[]
 m._recalculate=lambda:count.append(observations[-1])
 for i in range(10000):
  observations.append(i)
  m._on_state_changed(N(data={'entity_id':'sensor.native','old_state':N(state=str(i-1),attributes={}), 'new_state':N(state=str(i),attributes={})}))
 assert not count
 await asyncio.sleep(0)
 assert count==[9999],count
 for i in range(10000):
  m._on_state_changed(N(data={'entity_id':'sensor.unrelated'}))
  m._on_state_changed(N(data={'entity_id':'sensor.hem_logical'}))
 await asyncio.sleep(0)
 assert count==[9999]
 m._queue_source_refresh();m._active=False
 await asyncio.sleep(0)
 assert count==[9999] and m._source_refresh_handle is None
 print(json.dumps({'test':'manager-source-bursts','relevant_events':10000,'recalculations':1,'latest_evidence_seen':9999,'ignored_unrelated_and_generated':20000,'inactive_recalculations':0}))
asyncio.run(main())
