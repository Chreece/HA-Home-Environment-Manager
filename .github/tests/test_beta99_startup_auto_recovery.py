"""Beta99: actual persisted HEM restart records recover without user reset.

Real production async_start, _startup_readiness, _automatic_recovery_gate,
_apply_automatic_reconciliation and async_resume run against isolated native
Home Assistant states and storage. No physical service dispatch occurs.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import runpy
from types import MethodType

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta73_restart_power_history.py'))
Controller=base['Controller']
Parent=base['Parent']
spec=base['spec']
state=base['state']
snap=base['snap']
NOW=base['NOW']
Model=base['Model']
HomeAssistantError=base['HomeAssistantError']
source=ast.parse((ROOT/'equipment_runtime.py').read_text())
cl=next(n for n in source.body if isinstance(n,ast.ClassDef)
        and n.name=='EquipmentRuntime')

def production_method(name,namespace):
    method=next(n for n in cl.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
                and n.name==name)
    scope=dict(namespace)
    exec(compile(ast.Module(body=[method],type_ignores=[]),
                 'equipment_runtime.py','exec'),scope)
    return scope[name]

readiness=production_method('_startup_readiness',{
    'model':Model,'snapshot':snap,
    '_manual_output_changes':base['physical_changes'],
    'HA_READY_COOLDOWN_SECONDS':60,
    'NATIVE_STARTUP_STABLE_SECONDS':60,
})
apply=production_method('_apply_automatic_reconciliation',{
    'HomeAssistantError':HomeAssistantError,'model':Model,
})
gate=production_method('_automatic_recovery_gate',{})

async def test_startup():
    pending={
        'phase':'intent','entity':'climate.heater','service':'set_hvac_mode',
        'data':{'hvac_mode':'off'},'expected':{'state':'off'},'when':NOW-300,
        'power':True,'output_on':False,'min_on':600,'max_on':7200,
        'attempts':1,
    }
    r=Controller(native='off',native_report_age=900,pending=pending,owned=True)
    r.states['climate.heater'].attributes.update(
        {'hvac_action':'idle','temperature':20}
    )
    r._startup_source_observed={}
    r._startup_source_since={}
    r._startup_source_done=set()
    r._ha_running_since=None
    r._startup_readiness=MethodType(readiness,r)
    r._automatic_recovery_gate=MethodType(gate,r)
    r._apply_automatic_reconciliation=MethodType(apply,r)
    r._native_settle_remaining=lambda sp:0.0
    r.resume_information=lambda sp: {'decision':'first_check',
        'entity':'climate.heater','requested':'off','observed':'off'}
    # The persisted *intent* is uncertain. Startup must NOT invent that it
    # was sent or immediately clear an old heating ON ownership.
    await r.async_start()
    assert r.record['paused']=='restart_reconciliation_required'
    req=r.record.get('automatic_continue_requested')
    assert req and req['method']=='pid' and req['origin']=='automatic_restart_reconciliation',r.record
    assert r.record['pending']==pending
    assert r.record['power'], 'durable compressor ON interval was lost'
    assert not r.actual_commands

    # Core reports HA not fully running: do not perform restart ownership
    # checks, baseline adoption or manual-override checks.
    r.hass.is_running=True
    # HA's is_running is already True during STARTING. Only CoreState.running
    # after startup may begin HEM's controller cooldown.
    r.hass.state=type('CoreState',(),{'value':'STARTING'})()
    assert r._startup_readiness(spec)['reason']=='home_assistant_still_starting'
    r.hass.state=type('CoreState',(),{'value':'RUNNING'})()
    assert r._startup_readiness(spec)['reason']=='home_assistant_ready_cooldown'
    r.now+=59
    assert r._startup_readiness(spec)['reason']=='home_assistant_ready_cooldown'
    r.now+=1
    assert r._startup_readiness(spec)['reason']=='native_startup_stabilizing'

    # Native firmware updates its heating target while HA initializes.
    r.now+=40
    r.states['climate.heater'].attributes['temperature']=24
    assert r._startup_readiness(spec)['reason']=='native_startup_stabilizing'
    r.now+=59
    assert r._startup_readiness(spec)['reason']=='native_startup_stabilizing'
    r.now+=1
    assert r._startup_readiness(spec)['ready'], '60 seconds stable required'
    # Source remains OFF: completion never invents a new heating command.
    assert not r.actual_commands

    # The first automatic verification stores a real native observation,
    # but NEVER dispatches the interrupted physical command.
    await r._apply_automatic_reconciliation(spec)
    assert r.record['pending']==pending
    assert 'pending_resume_probe' in r.record
    assert r.record['paused']=='restart_reconciliation_required'
    assert not r.actual_commands

    # After a second unchanged independently sampled HA state >=60 seconds
    # later, the same existing Resume verifier may retire the old intent
    # and safely restore PID with minimum-OFF protection.
    r.now+=60
    await r._apply_automatic_reconciliation(spec)
    assert r.record['pending'] is None
    assert not r.record.get('paused')
    assert not r.record.get('automatic_continue_requested')
    assert r.record['power']=={}
    assert r.record['off_at']['climate.heater']==r.now
    assert not r.actual_commands, 'start-up reconciliation emitted a service'

    # An old MANUAL controller is not silently promoted to Automatic; its
    # stored human selection remains authoritative.
    manual=Controller(native='off',pending=pending,owned=False)
    manual.manager.settings[Model.SETTINGS][spec.identifier]['control_mode']='manual'
    manual.manager.entry.options=deepcopy(manual.manager.settings)
    manual.manager.original_store={'version':1,'records':deepcopy(manual.records)}
    await manual.async_start()
    assert 'automatic_continue_requested' not in manual.record
    assert manual.record['paused']=='restart_reconciliation_required'
    print('BETA99_STARTUP_60SEC_STABLE_AUTO_RECONCILES_PERSISTED_INTENT_WITHOUT_SERVICE=PASS')

asyncio.run(test_startup())
