"""Beta98: native reconnect settling and bounded post-outage retry.

Production functions are executed against deterministic HA snapshots.
No actual service or device changes are made. Crucially, a climate entity
becoming AVAILABLE is not proof of physical acknowledgement or user control.
"""
from __future__ import annotations
import asyncio
import ast
from pathlib import Path
import runpy
from types import MethodType

ROOT=Path(__file__).resolve().parents[2]
source=ast.parse((ROOT/'equipment_runtime.py').read_text())
runtime_class=next(n for n in source.body if isinstance(n,ast.ClassDef)
                   and n.name=='EquipmentRuntime')
def extract(name):
    n=next(x for x in runtime_class.body
           if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))
           and x.name==name)
    scope={
        'NATIVE_RECONNECT_SETTLE_SECONDS':30,
        'NATIVE_COMMAND_MAX_ATTEMPTS':4,
        'NATIVE_COMMAND_RECONNECT_EXTRA_ATTEMPTS':2,
        'NATIVE_RECONNECT_EXTRA_ATTEMPTS':2,
        'NATIVE_COMMAND_RETRY_SECONDS':30,
    }
    exec(compile(ast.Module(body=[n],type_ignores=[]),
                 'equipment_runtime.py','exec'),scope)
    return scope[name]
watch=extract('observe_native_availability')
settle=extract('_native_settle_remaining')
retry_after=extract('_retry_after_verified_reconnect')

async def tests():
    b=runpy.run_path(str(ROOT/'.github/tests/test_beta89_automatic.py'))
    controller=b['FakeController']
    FakeState=b['FakeState']
    spec=b['SPEC']
    Model=b['Model']
    r=controller('automatic')
    r.now=1000.0
    r.clock=lambda:r.now
    r._native_ready_since={}
    r._native_reconnect_epoch={}
    r._native_settled_for={}
    r.observe_native_availability=MethodType(watch,r)
    r._native_settle_remaining=MethodType(settle,r)

    # Home Assistant reports an unavailable climate entity; on return its
    # firmware first publishes HEAT, then adjusts its native setpoints and
    # preset. None of that may demote Automatic during the first 30 seconds.
    r.state=FakeState('unavailable')
    assert r._native_settle_remaining(spec) is None
    restored=FakeState('heat',temperature=30,preset_mode='startup')
    r.observe_native_availability('climate.native',r.state,restored)
    r.state=restored
    assert r._native_reconnect_epoch['climate.native']==1000.0
    for seconds in (0,10,29):
        r.now=1000+seconds
        r.state=FakeState('heat',temperature=30-seconds*.1,
                          preset_mode='startup' if seconds<29 else 'auto')
        assert not await r._reconcile(spec),seconds
        assert Model.settings(r.manager,spec)['control_mode']=='automatic'
        assert not r.record.get('paused'),r.record
        assert r._native_settle_remaining(spec)>0
    r.now=1030
    assert await r._reconcile(spec)
    assert r.record['baseline']['climate.native']==b['sn'](r.state)
    assert r._native_settled_for[(spec.identifier,'climate.native')]==1000.0
    # A genuinely identified HA user change after settling remains Manual.
    # An anonymous firmware state change is no longer treated as a person.
    r.now=1031
    r.state=FakeState('cool',temperature=20)
    r.state.context=type('Context',(),{'user_id':'ha-user','parent_id':None})()
    assert not await r._reconcile(spec)
    assert r.record['paused']=='physical_manual_override'
    assert Model.settings(r.manager,spec)['control_mode']=='manual'

    # Online→offline resets the grace clock, another genuine offline→online
    # starts a fresh 30s interval. No reconnect retry is credited at HA
    # initial registration (old_state=None).
    zero=controller()
    zero.now=3000.
    zero.clock=lambda:zero.now
    zero._native_ready_since={}
    zero._native_reconnect_epoch={}
    zero.observe_native_availability=MethodType(watch,zero)
    zero._native_settle_remaining=MethodType(settle,zero)
    zero.observe_native_availability('climate.native',None,FakeState('off'))
    assert 'climate.native' not in zero._native_reconnect_epoch
    assert zero._native_settle_remaining(spec)==30
    zero.state=FakeState('unavailable')
    zero.observe_native_availability(
        'climate.native',FakeState('heat'),zero.state)
    assert zero._native_settle_remaining(spec) is None
    zero.now=3010.
    zero.state=FakeState('off')
    zero.observe_native_availability(
        'climate.native',FakeState('unavailable'),zero.state)
    assert zero._native_settle_remaining(spec)==30

    # Four normal attempts total, with 30s retry spacing; offline periods
    # consume zero attempts. Only a VERIFIED offline→online edge after the
    # old attempt may grant at most TWO extra attempts (one per reconnect).
    b88=runpy.run_path(str(ROOT/'.github/tests/test_beta88_power_startup_and_retries.py'))
    # Reuse the same package as the production retry helpers loaded below.
    retry_after.__globals__.update(
        model=b88['Model'], __name__=b88['pkg'].__name__+'.equipment_runtime',
        __package__=b88['pkg'].__name__,
    )
    Sim=b88['SimRuntime']
    s=b88['SPEC']
    sim=Sim()
    sim._native_ready_since={}
    sim._native_reconnect_epoch={}
    sim._native_settled_for={}
    sim.observe_native_availability=MethodType(watch,sim)
    sim._native_settle_remaining=MethodType(settle,sim)
    sim._retry_after_verified_reconnect=MethodType(retry_after,sim)
    pending=sim.pending()
    # First registration starts the 30-second stabilization clock, not
    # physical power ownership or a fictitious reconnect grant.
    assert sim._native_settle_remaining(s)==30
    sim.now+=29
    await sim._retry_pending(s,pending,sim.now)
    assert pending['attempts']==1 and sim.calls==[]
    for expected in (2,3,4):
        sim.now+=30
        await sim._retry_pending(s,pending,sim.now)
        assert pending['attempts']==expected
        assert len(sim.calls)==expected-1
    sim.now+=30
    await sim._retry_pending(s,pending,sim.now)
    assert sim.record['paused']=='physical_acknowledgement_missing'
    before=len(sim.calls)
    assert not await sim._retry_after_verified_reconnect(s)
    assert len(sim.calls)==before

    for number in (1,2):
        old=sim.state
        sim.now+=10
        sim.observe_native_availability('climate.heater',old,b88['State']('unavailable'))
        sim.state=b88['State']('unavailable')
        await sim._retry_pending(s,pending,sim.now)
        assert pending['attempts']==4+number-1
        sim.now+=10
        new=b88['State']('off')
        sim.observe_native_availability('climate.heater',sim.state,new)
        sim.state=new
        sim.now+=29
        assert not await sim._retry_after_verified_reconnect(s)
        assert len(sim.calls)==before
        sim.now+=1
        assert await sim._retry_after_verified_reconnect(s)
        assert pending['attempts']==4+number,pending
        assert pending['reconnect_retry_uses']==number,pending
        assert pending['phase']=='commanded'
        assert len(sim.calls)==before+1
        before=len(sim.calls)
        assert not await sim._retry_after_verified_reconnect(s)

    sim.now+=10
    sim.observe_native_availability(
        'climate.heater',sim.state,b88['State']('unavailable'))
    sim.state=b88['State']('unavailable')
    sim.now+=10
    sim.observe_native_availability(
        'climate.heater',sim.state,b88['State']('off'))
    sim.state=b88['State']('off')
    sim.now+=31
    assert not await sim._retry_after_verified_reconnect(s)
    assert len(sim.calls)==before,'must never endlessly replay a stuck command'

    # Even a real fresh reconnect cannot replay an OBSOLETE command after
    # the user changed the desired mode while the device was unavailable.
    old=b88['SimRuntime']()
    old._native_ready_since={}
    old._native_reconnect_epoch={}
    old.observe_native_availability=MethodType(watch,old)
    old._native_settle_remaining=MethodType(settle,old)
    old._retry_after_verified_reconnect=MethodType(retry_after,old)
    p=old.pending()
    p['attempts']=4
    p['last_attempt_at']=old.now
    old.record['paused']='physical_acknowledgement_missing'
    old.manager.settings['cfg']['requested_mode']='cool'
    old.now+=10
    old.observe_native_availability('climate.heater',
        b88['State']('unavailable'),b88['State']('off'))
    old.now+=30
    assert not await old._retry_after_verified_reconnect(s)
    assert old.calls==[] and old.record['pending'] is p

    print('BETA98_RECONNECT_30SEC_GRACE_4_NORMAL_PLUS_2_REAL_RECONNECT_RETRIES=PASS')

asyncio.run(tests())
