"""Beta77: OFF external supply can be re-armed without adopting a stale native ON.

Extracts the real runtime methods from the installed source. No HA services,
device commands or mutations outside the fixture. Includes the Beta72 running
and identity-race regressions before the new power-supply cases.
"""
from __future__ import annotations
import ast
import asyncio
import importlib.util
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta72_resume_running.py'))
Runtime=base['Runtime']
spec=base['spec']
state=base['state']
HomeAssistantError=base['HomeAssistantError']

tree=ast.parse((ROOT/'equipment_runtime.py').read_text(encoding='utf-8'))
klass=next(node for node in tree.body if isinstance(node,ast.ClassDef)
           and node.name=='EquipmentRuntime')
fn=next(node for node in klass.body if isinstance(node,ast.AsyncFunctionDef)
        and node.name=='_reconcile')
namespace={
    **base['ns'],
    'model':base['Model'],
    'snapshot':base['snapshot'],
    'matches':base['matches'],
    '_manual_output_changes':lambda old,new: ('state',)
       if old.get('state')!=new.get('state') else (),
}
exec(compile(ast.Module(body=[fn],type_ignores=[]),
             'equipment_runtime.py','exec'),namespace)
# Reconciliation imports the production target/sequencing helpers using this
# runtime's package. Export the same simulated model and actual runtime globals.
package=base['pkg']
sys.modules[package.__name__+'.equipment_model']=base['Model']
package.equipment_model=base['Model']
runtime_module=ModuleType(namespace['__name__'])
runtime_module.__dict__.update(namespace)
sys.modules[runtime_module.__name__]=runtime_module
helper_spec=importlib.util.spec_from_file_location(
    package.__name__+'.equipment_setpoint_sequence', ROOT/'equipment_setpoint_sequence.py')
sequence_module=importlib.util.module_from_spec(helper_spec)
sys.modules[helper_spec.name]=sequence_module
helper_spec.loader.exec_module(sequence_module)
Runtime._reconcile=namespace['_reconcile']

async def pause(self,spec,reason):
    self.record['paused']=reason
    await self._save()
Runtime._pause=pause

def create_offline(*, native='dry'):
    r=Runtime(native=native,supply='off')
    r.manager.cap.modes=('off','dry')
    # The exact legacy checkpoint: configured relay but no persisted upstream
    # record, no native ownership, baseline OFF and a stored manual-override
    # pause. The native climate may keep showing DRY after its relay is OFF.
    r.record['upstream']={}
    r.record['baseline']={'climate.heater':{'state':'off','attributes':{}}}
    return r

async def rejects(r, text):
    try:
        await r.async_resume(spec)
    except HomeAssistantError as e:
        assert text in str(e),(text,str(e))
    else:
        raise AssertionError('Unsafe resume accepted')
    assert r.record['paused']=='physical_manual_override'
    assert r.calls==[] and r.scheduled==0

async def run():
    # Native DRY is an untrusted status behind an isolated physical relay:
    # Resume may arm the logical PID without claiming live native power.
    ghost=create_offline()
    await ghost.async_resume(spec)
    assert ghost.record['paused'] is None
    assert ghost.record['power']=={}
    assert ghost.record['upstream']['entity']=='switch.plug'
    assert ghost.record['upstream']['owned'] is False
    assert ghost.record['upstream']['off_at'] <= ghost.now
    assert ghost.record['baseline']['climate.heater']['state']=='dry'
    assert not ghost.record.get('native_power_observations',{}).get('climate.heater')
    assert ghost.status[0]=='awaiting_evaluation', ghost.status
    assert ghost.scheduled==1 and ghost.calls==[]
    assert ghost.manager.settings['equipment_controllers'][spec.identifier]['control_mode']=='pid'

    # Do not fabricate native OFF acknowledgement; an OFF relay cannot ACK
    # an interrupted native command or certify a previously-owned output.
    active_owned=create_offline()
    active_owned.record['power']['climate.heater']={
        'since':active_owned.now-800,'min_on':600,'max_on':7200}
    await rejects(active_owned,'unresolved controller power ownership')
    pending=create_offline()
    pending.record['pending']={
        'phase':'commanded','entity':'climate.heater','expected':{'state':'dry'}}
    await rejects(pending,'pending native command')
    relay_owned=create_offline()
    relay_owned.record['upstream']['owned']=True
    relay_owned.record['upstream']['identity']=dict(base['identity'])
    await rejects(relay_owned,'unresolved controller power ownership')
    unauthorized=create_offline()
    unauthorized.manager.switch_permission=False
    await rejects(unauthorized,'identity')

    # An OFF -> ON supply race during the Store write must invalidate Resume.
    raced=create_offline()
    raced.on_save=lambda:raced.states.__setitem__('switch.plug',state('on','switch'))
    try:
        await raced.async_resume(spec)
    except HomeAssistantError as e:
        assert 'changed during Resume' in str(e),e
    else:
        raise AssertionError('Relay transition during Resume was not rejected')
    assert raced.record['paused']=='physical_state_changed_during_resume'
    assert raced.scheduled==0 and raced.calls==[]

    # Same-tick OFF-supply race must not falsely assert Manual. An
    # unattributed state change after supply return is NOT evidence a user
    # touched the device; HEM also must not adopt unowned ON equipment.
    short=create_offline()
    short.record['paused']=None
    assert await short._reconcile(spec) is False
    assert short.record['paused'] is None and short.status[0]=='waiting_for_physical_device'
    assert short.calls==[]
    live=create_offline()
    live.record['paused']=None
    live.states['switch.plug']=state('on','switch')
    assert await live._reconcile(spec) is True
    assert live.record.get('paused') is None
    assert live.record['power']=={}
    assert live.record['baseline']['climate.heater']['state']=='dry'
    assert live.calls==[]
    # A direct authenticated HA edit still selects Manual, even with the
    # relay available and native mode physically ON.
    direct=create_offline()
    direct.record['paused']=None
    direct.record['native_control_confirmed']={'climate.heater':{'at':0.,'context_id':None}}
    direct.states['switch.plug']=state('on','switch')
    direct.states['climate.heater'].context=N(user_id='actual-user',parent_id=None)
    assert not await direct._reconcile(spec)
    assert direct.record['paused']=='physical_manual_override'

    supply=(ROOT/'equipment_power_switch.py').read_text(encoding='utf-8')
    assert ('runtime._status(spec, "waiting_for_physical_device",\n'
            '                            reason="upstream_switch_off_but_native_reports_active")'
           ) in supply
    assert 'if not supply_minimum_off(' in supply
    assert 'if not observed_output_off(native)' not in supply or (
       'reason="upstream_switch_off_but_native_reports_active"' in supply)

    print('BETA77_OFFLINE_SUPPLY_RESUME=PASS; NO_ACTUATOR_COMMANDS; SAFETY_CONFLICTS_HOLD')

asyncio.run(run())
