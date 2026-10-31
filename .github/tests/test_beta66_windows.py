"""Exercise real window policy and runtime command boundaries without hardware."""
from __future__ import annotations
import asyncio, runpy, ast, sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[2]
b=runpy.run_path(str(ROOT/'.github/tests/test_beta64_sleep_idle.py'))
prior=runpy.run_path(str(ROOT/'.github/tests/test_beta61_supply_selection.py'))
Simulator, Model, spec = b['Simulator'],b['Model'],b['spec']
extract=b['extract']; state=b['state']; BASE=b['BASE']

window=ModuleType('beta64_probe.equipment_window')
window.__dict__.update({
 'Any':object,'math':__import__('math'),'model':Model,'RESUME_SECONDS':60.,
 'POLICY_KEY':'pause_on_window_open',
 'entity_area':lambda hass,entity: spec.area_id if entity.startswith(('binary_sensor.window','climate.','switch.')) else 'elsewhere',
 'is_window':lambda hass,s:s.domain=='binary_sensor' and s.attributes.get('device_class')=='window',
 'selected':lambda settings,area,group:settings.get('room_sources',{}).get(area,{}).get(group),
})
extract('equipment_window.py',('_stamp','evaluate'),window.__dict__)
sys.modules[window.__name__]=window
b['runtime_env'].update({
 'foreign_owner_hold':lambda *args:None,
 '_contact_interlock':lambda hass,area,p:p.get('window_safe',True),
 '_physical_climate_conflict':lambda *args:None,
})
policy, gate = extract('equipment_runtime.py',('_window_policy','_gate'),b['runtime_env'])
Simulator._window_policy=policy
Simulator._gate=gate

def make(*,opened=True,supply='on',native='dry',enabled=True):
 s=Simulator(sleeping=False,supply=supply,native=native)
 s.manager.entry=NS(entry_id='entry')
 s.manager.settings['room_sources']={spec.area_id:{'windows':['binary_sensor.window']}}
 # The real controller reads its persisted settings each tick. Never edit
 # the temporary DEFAULTS+stored copy returned by Model.settings(): doing so
 # previously disabled the supply's window subscriber in this test harness.
 s.manager.settings['equipment_controllers'][spec.identifier]['pause_on_window_open']=enabled
 s.manager.plan.update(window_contacts=['binary_sensor.window'],window_safe=not opened)
 contact(s,'on' if opened else 'off',when=BASE-1800)
 return s

def contact(s,value,when=None,entity='binary_sensor.window'):
 w=state(value,when=s.now if when is None else when)
 w.entity_id=entity; w.domain='binary_sensor';w.attributes={'device_class':'window'}
 s.states[entity]=w
 s.manager.plan['window_safe']=value=='off'
 return w

async def main():
 # Regression: HA recreates a CLOSED binary_sensor on restart and gives its
 # brand-new HA State a recent last_changed even though the window never
 # actually moved. This is NOT an open->close transition: zero extra delay.
 for restored_age in (0, 1, 20, 50):
  restored=make(opened=False,native='off')
  contact(restored,'off',when=restored.now-restored_age)
  initial=restored._window_policy(spec)
  assert initial['status']=='window_closed_ready', (restored_age,initial)
  assert initial['blocked'] is False and initial['remaining_seconds']==0
  # Repeated ticks, plus a harmless OFF metadata restamp, cannot re-arm it.
  for elapsed in (1,10,30,59,61):
   restored.now=BASE+elapsed
   next_state=restored._window_policy(spec)
   assert next_state['status']=='window_closed_ready', (elapsed,next_state)
  # A NEW last_changed timestamp on a verified contact can hide a
  # brief open->closed transition between control ticks. Conservatively
  # enforce recovery in this situation (unlike the very first HA snapshot).
  contact(restored,'off',when=restored.now)
  assert restored._window_policy(spec)['status']=='window_close_warmup'
  restored.now+=59
  assert restored._window_policy(spec)['blocked']
  restored.now+=1
  assert restored._window_policy(spec)['status']=='window_closed_ready'

 # Real open->closed and unknown->closed transitions must still wait 60s.
 for first in ('on','unknown'):
  cold=make(opened=True,native='off')
  contact(cold,first,when=BASE)
  first_result=cold._window_policy(spec)
  assert first_result['blocked'] is True
  contact(cold,'off',when=BASE)
  closing=cold._window_policy(spec)
  assert closing['status']=='window_close_warmup' and closing['remaining_seconds']==60
  cold.now=BASE+59
  assert cold._window_policy(spec)['blocked'] is True
  cold.now=BASE+60
  assert cold._window_policy(spec)['status']=='window_closed_ready'

 # Adding a new source is NOT an already-verified continuous closure.
 changed=make(opened=False,native='off')
 assert changed._window_policy(spec)['status']=='window_closed_ready'
 changed.manager.settings['room_sources'][spec.area_id]['windows'].append(
  'binary_sensor.window2'
 )
 contact(changed,'off',when=BASE-100,entity='binary_sensor.window2')
 assert changed._window_policy(spec)['status']=='window_close_warmup'
 changed.now=BASE+60
 assert changed._window_policy(spec)['status']=='window_closed_ready'

 s=make();cfg=Model.settings(s.manager,spec)
 assert s._window_policy(spec)['status']=='window_open_pause'
 assert b['approved_demand'](s,spec,cfg,s.manager.cap) is False
 await b['tick'](s,spec)
 assert s.issued==[('climate','set_hvac_mode','climate.comfee',{'hvac_mode':'off'})],s.issued
 assert await s._reconcile(spec)
 for _ in range(4):
  s.now+=10;await b['tick'](s,spec)
 assert len(s.issued)==1
 assert s.statuses[spec.identifier]['status']=='window_open_pause'
 contact(s,'off')
 start=s.now
 for seconds in (0,1,30,59):
  s.now=start+seconds
  p=s._window_policy(spec);assert p['status']=='window_close_warmup',(seconds,p)
  assert b['approved_demand'](s,spec,cfg,s.manager.cap) is False
  await b['tick'](s,spec)
  assert len(s.issued)==1
 s.now=start+60
 assert s._window_policy(spec)['status']=='window_closed_ready'
 assert b['approved_demand'](s,spec,cfg,s.manager.cap) is True
 assert not await s._power(spec,s.manager.cap,'dry',automatic=True)
 assert s.statuses[spec.identifier]['status']=='minimum_off_hold'
 s.now=BASE+700
 assert await s._power(spec,s.manager.cap,'dry',automatic=True)
 assert s.issued[-1][3]=={'hvac_mode':'dry'}

 # Disabled is genuinely per device; unrelated protection stays in place.
 s=make(enabled=False);cfg=Model.settings(s.manager,spec)
 assert not s._window_policy(spec)['blocked']
 assert b['approved_demand'](s,spec,cfg,s.manager.cap) is True
 assert s._gate(spec,s.manager.cap,cfg,s.manager.plan,'dry',automatic=True) is None
 assert not s._stop_policy_verified(spec,s.manager.cap,'window')

 s=make(native='unavailable',supply='off');s.record['upstream']['owned']=False
 for _ in range(3):
  s.now+=1000;assert await b['before_tick'](s,spec)
 assert not s.issued
 contact(s,'off');start=s.now
 s.now+=59;assert await b['before_tick'](s,spec);assert not s.issued
 s.now=start+60;assert await b['before_tick'](s,spec)
 assert s.issued, {'policy':s._window_policy(spec),
                   'status':s.statuses.get(spec.identifier),
                   'relay':s.record.get('upstream'),
                   'now':s.now}
 assert s.issued[-1][:3]==('switch','turn_on','switch.strip')

 # Unknown contact is not closed; recovery restarts 60 seconds.
 s=make(native='off');contact(s,'unavailable')
 assert s._window_policy(spec)['status']=='window_state_unknown'
 contact(s,'off',when=BASE-3000)
 p=s._window_policy(spec);assert p['remaining_seconds']==60,p
 s.now+=59;assert s._window_policy(spec)['blocked']
 s.now+=1;assert not s._window_policy(spec)['blocked']
 contact(s,'on');assert s._window_policy(spec)['stop_requested']
 contact(s,'off');s.now+=40;assert s._window_policy(spec)['blocked']
 contact(s,'on');assert s._window_policy(spec)['status']=='window_open_pause'
 s.now+=5;contact(s,'off');assert s._window_policy(spec)['remaining_seconds']==60
 s.manager.settings['room_sources'][spec.area_id]['windows'].append('binary_sensor.window2')
 contact(s,'on',entity='binary_sensor.window2');assert s._window_policy(spec)['blocked']
 contact(s,'off',entity='binary_sensor.window2');s.now+=59;assert s._window_policy(spec)['blocked']
 s.now+=1;assert not s._window_policy(spec)['blocked']
 s.manager.settings['room_sources'][spec.area_id]['windows']=[]
 assert s._window_policy(spec)['status']=='window_contacts_not_configured'

 # Opening after durable ON intent aborts the physical command.
 s=make(opened=False,native='off');cfg=Model.settings(s.manager,spec)
 s.record['capabilities']=b['asdict'](s.manager.cap)
 s.on_save=lambda:contact(s,'on')
 assert not await s._power(spec,s.manager.cap,'dry',automatic=True)
 assert not s.issued and s.record.get('pending') is None
 p=s._window_policy(spec)
 assert p['blocked']
 assert s._gate(spec,s.manager.cap,cfg,s.manager.plan,'off',automatic=False)=='window_open_pause'
 assert s._gate(spec,s.manager.cap,cfg,s.manager.plan,'off',automatic=False,window_stop=True) is None

 # An explicit OFF must remain allowed even with open windows.
 s=make();Model.settings(s.manager,spec)['control_mode']='off'
 await b['tick'](s,spec)
 assert s.issued[-1][3]=={'hvac_mode':'off'}

 # Offline configuration must not clear unrelated manual-override latches.
 c=prior['Controller']();old_spec=prior['spec'];c.record['paused']='physical_manual_override'
 await prior['async_update'](c,old_spec,{'pause_on_window_open':False})
 assert c.manager.settings[prior['Model'].SETTINGS][old_spec.identifier]['pause_on_window_open'] is False
 assert c.record['paused']=='physical_manual_override'
 try: await prior['async_update'](c,old_spec,{'pause_on_window_open':'true'})
 except prior['HomeAssistantError']: pass
 else: raise AssertionError('must reject string booleans')
 print('PASS Beta66: actual native OFF; no control open/59s; resume at 60s; hardware dwell; supply wake guard; reopens/unknown/multiple contacts; async dispatch race; disabled option; offline edits')

asyncio.run(main())
