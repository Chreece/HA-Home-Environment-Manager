"""Beta98: edits are accepted during native ACK and Auto can recover itself.

This uses production async_update, Continue button's real availability,
physical-ACK gate, existing Resume verifier, and guarded queued supply release.
No physical HA services run, nor is a pending command discarded on timeout.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import runpy
from types import SimpleNamespace as N, MethodType

ROOT=Path(__file__).resolve().parents[2]
base=runpy.run_path(str(ROOT/'.github/tests/test_beta61_supply_selection.py'))
# The Beta72 suite runs its asyncio fixture at module load; execute it
# before entering this test's own event loop.
resume_fixture=runpy.run_path(str(ROOT/'.github/tests/test_beta72_resume_running.py'))
Controller=base['Controller']
Model=base['Model']
NativeCap=base['NativeCap']
spec=base['spec']
states=base['states']
state=base['state']
async_update=base['async_update']

def method(path,name,klass='EquipmentRuntime'):
    tree=ast.parse((ROOT/path).read_text(encoding='utf-8'))
    parent=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==klass)
    node=next(n for n in parent.body
              if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
              and n.name==name)
    return node

async def tests():
    Model.CAP=NativeCap()
    states['climate.appliance']=state('off')
    states['switch.plug']=state('off','switch')
    c=Controller()
    c._pid_passive_observers={}
    c._pid_passive_tasks={}
    c._ready=True
    c.record['paused']='physical_acknowledgement_missing'
    c.record['pending']={
        'phase':'commanded','entity':'climate.appliance',
        'expected':{'state':'heat'},'when':1699999900,
        'service':'set_hvac_mode','data':{'hvac_mode':'heat'},
        'power':True,'min_on':600,'max_on':7200,'attempts':4,
    }
    c.record['baseline']={
        'climate.appliance':{'state':'off','attributes':{'temperature':20}}
    }
    c.record['off_at']={'climate.appliance':1699999400}
    before=deepcopy(c.record['pending'])
    baseline=deepcopy(c.record['baseline'])
    off_at=deepcopy(c.record['off_at'])
    await async_update(c,spec,{'power_switch_cooldown_seconds':1800})
    assert Model.settings(c.manager,spec)['power_switch_cooldown_seconds']==1800
    assert c.record['pending']==before
    assert c.record['baseline']==baseline and c.record['off_at']==off_at
    assert c.record['paused']=='physical_acknowledgement_missing'
    assert c.record['automatic_continue_requested']['method']=='pid'
    assert not c.service_calls
    assert c.statuses[-1][0][1]=='awaiting_physical_acknowledgement'
    assert c.statuses[-1][1]['settings_saved'] is True

    # User can also change the selected algorithm and other preferences
    # without clearing an uncertain compressor-start journal.
    await async_update(c,spec,{'control_mode':'automatic'})
    assert Model.settings(c.manager,spec)['control_mode']=='automatic'
    assert c.record['pending']==before and c.record['baseline']==baseline
    assert c.record['automatic_continue_requested']['method']=='automatic'
    assert c.record['paused']=='physical_acknowledgement_missing'

    # A previously owned switch can be safely reconfigured, but the old
    # physical binding is immutable until safe OFF/ACK/dwell reconciliation.
    c.record['upstream']={'entity':'switch.old','owned':True,
                          'pending':None,'paused':None}
    await async_update(c,spec,{'power_switch_entity':'switch.plug'})
    assert Model.settings(c.manager,spec)['power_switch_entity'] is None
    assert c.record['queued_power_switch']['requested']=='switch.plug'
    assert c.record['pending']==before
    assert c.record['upstream']['owned'] is True
    assert not c.service_calls

    # Physical ACK alone is not a user wait prompt: it is the old command
    # having reached its expected real state. A plain available entity
    # with a different mode or a two-check timeout is not a valid ACK.
    scope={}
    gate=method('equipment_runtime.py','_automatic_recovery_gate')
    exec(compile(ast.Module(body=[gate],type_ignores=[]),
                 'equipment_runtime.py','exec'),scope)
    gate=scope['_automatic_recovery_gate']
    c._native_settle_remaining=lambda sp:0.0
    c.resume_information=lambda sp:{'decision':'verified','requested':'heat','observed':'off'}
    assert gate(c,spec)['ready'] is False
    assert gate(c,spec)['reason']=='previous_command_not_yet_confirmed'
    c.resume_information=lambda sp:{'decision':'confirmed','requested':'heat','observed':'heat'}
    assert gate(c,spec)['ready'] is True
    c.record['upstream']['pending']={'phase':'commanded','desired':'on'}
    c.record['upstream']['entity']='switch.plug'
    assert gate(c,spec)['ready'] is False
    states['switch.plug']=state('on','switch')
    assert gate(c,spec)['ready'] is True
    c.record['upstream']['pending']['phase']='intent'
    assert gate(c,spec)['ready'] is False
    c.record['upstream']['pending']=None
    c.record['upstream']['owned']=False
    c.record['power']={}
    c.record['pending']=None
    c.record['upstream']['entity']='switch.old'

    # Queue is applied only after old output and outlet are unowned, with
    # no native command; the stored switch is never silently reassigned
    # while a previously owned supply may still be energized.
    env=dict(base['runtime_env'])
    node=method('equipment_runtime.py','_apply_queued_power_switch')
    exec(compile(ast.Module(body=[node],type_ignores=[]),
                 'equipment_runtime.py','exec'),env)
    helper=env['_apply_queued_power_switch']
    assert await helper(c,spec)
    assert Model.settings(c.manager,spec)['power_switch_entity']=='switch.plug'
    assert 'queued_power_switch' not in c.record
    assert not c.service_calls

    # The real button's property decides availability from actual controller
    # recovery/pending state, not simply the selected PID/Automatic string.
    button=method('button.py','available','EquipmentResumeButton')
    ns={}
    exec(compile(ast.Module(body=[button],type_ignores=[]),'button.py','exec'),ns)
    prop=ns['available']
    getter=prop.fget if isinstance(prop,property) else prop
    c.records={spec.identifier:c.record}
    control=N(_spec=spec,_manager=N(equipment=c),
              controller_settings=Model.settings(c.manager,spec))
    c.record['paused']=None
    c.record['pending']=None
    c.record.pop('automatic_continue_requested',None)
    assert getter(control) is False
    c.record['pending']={'entity':'climate.appliance'}
    assert getter(control) is True
    c.record['pending']=None
    c.record['paused']='native_retry_policy_changed'
    assert getter(control) is True
    c.record['paused']=None
    control.controller_settings={'control_mode':'manual'}
    assert getter(control) is True

    # Actual no-service Resume uses the current physical state and proves
    # successful ACK before clearing the pending journal and queued method.
    Runtime=resume_fixture['Runtime']
    physical_spec=resume_fixture['spec']
    h=Runtime(prior_owned=True)
    h.record['paused']='physical_acknowledgement_missing'
    h.record['pending']={
        'phase':'commanded','entity':'climate.heater',
        'service':'set_hvac_mode','expected':{'state':'heat'},
        'when':h.now-240,'power':True,'output_on':True,
        'min_on':600,'max_on':7200,
    }
    h.record['automatic_continue_requested']={
        'at':h.now,'method':'pid','awaiting_physical_verification':True,
    }
    h._ready=True
    env={'model':resume_fixture['Model'],
         'HomeAssistantError':resume_fixture['HomeAssistantError']}
    node=method('equipment_runtime.py','_apply_automatic_reconciliation')
    exec(compile(ast.Module(body=[node],type_ignores=[]),
                 'equipment_runtime.py','exec'),env)
    apply_auto=env['_apply_automatic_reconciliation']
    await apply_auto(h,physical_spec)
    assert h.record['pending'] is None and h.record['paused'] is None
    assert 'automatic_continue_requested' not in h.record
    assert h.record['power']['climate.heater']['min_on']==600
    assert Model.settings(c.manager,spec)['control_mode']=='automatic'
    assert h.calls==[], 'resume must not command physical HA device'

    # The wording explicitly explains why a live HA state is NOT by itself
    # an acknowledgement, with no repeated button press instructions.
    words=resume_fixture['helper_module'].automatic_recovery_message
    evidence={'entity':'climate.heater','requested':'heat','observed':'off'}
    for lang in ('en','el','de'):
        message=words(evidence,language=lang)
        assert 'climate.heater' in message and 'heat' in message and 'off' in message
        assert 'press' not in message.casefold() or 'do not need' in message.casefold()

    print('BETA98_NONBLOCKING_USER_PREFS_POSITIVE_ACK_GATE_AND_AUTO_REARM=PASS')

asyncio.run(tests())
