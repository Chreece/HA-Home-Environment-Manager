"""Beta75 native reattachment after controlled, acknowledged external supply ON.

Runs the actual EquipmentRuntime native wake handler and native power gate.
No services are sent to a real Home Assistant installation. Prior Beta73
simulation is reused to exercise the real native minimum-OFF guard.
"""
from __future__ import annotations

import ast
import asyncio
import runpy
import sys
from pathlib import Path
from types import ModuleType
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[2]
b=runpy.run_path(str(ROOT/'.github/tests/test_beta73_restart_power_history.py'))
C=b['Controller']
M=b['ExtendedModel']
spec=b['spec']
state=b['state']
NOW=b['NOW']
identity=b['base']['identity']
helper_ns=b['namespace']

activation=ModuleType('beta73_fixture.device_activation')
activation.authorized=lambda manager,spec: manager.native_permission
sys.modules[activation.__name__]=activation
supply=sys.modules['beta73_fixture.equipment_power_switch']
supply.device_supply_dwell=lambda runtime, spec, cfg, cap: (
    M.timing(runtime.manager,spec,cap)[:2]
)

tree=ast.parse((ROOT/'equipment_runtime.py').read_text(encoding='utf-8'))
klass=next(t for t in tree.body if isinstance(t,ast.ClassDef) and t.name=='EquipmentRuntime')
wake=next(x for x in klass.body if isinstance(x,ast.AsyncFunctionDef)
          and x.name=='_reconcile_native_after_supply_wake')
reconcile=next(x for x in klass.body if isinstance(x,ast.AsyncFunctionDef)
          and x.name=='_reconcile')
exec(compile(ast.Module(body=[wake,reconcile],type_ignores=[]),
             'equipment_runtime.py','exec'),helper_ns)
C._reconcile_native_after_supply_wake=helper_ns[wake.name]
C._reconcile=helper_ns[reconcile.name]

def create(mode='off', *, supply_owned=True, off_age=1800, boot_mode='heat'):
    r=C(owned=False,native=mode,supply='on',supply_owned=supply_owned)
    r._ready=r._active=True
    r._started=NOW-5000
    r.manager.settings[M.SETTINGS][spec.identifier]['requested_mode']=boot_mode
    r.manager.settings[M.SETTINGS][spec.identifier]['control_mode']='pid'
    r.record['power'].clear()
    r.record['pending']=None
    r.record['off_at']={'climate.heater':NOW-400}
    r.record['baseline']={'climate.heater':b['snap'](state('heat',changed=NOW-4000))}
    r.record['native_power_observations']={}
    r.record['upstream'].update({
        'entity':'switch.plug','identity':dict(identity),
        'owned':supply_owned,'pending':None,'paused':None,
        'off_at':NOW-off_age,'on_at':NOW,
        'native_wake':{
            'off_at':NOW-off_age,'on_at':NOW,
            'identity':dict(identity),'reconciled':False,
        },
    })
    r.states['climate.heater']=state(mode,changed=NOW-2)
    r.actual_commands=[]
    return r

async def evaluate():
    # The relay has been OFF 1800 seconds; it was just powered ON by HEM.
    # The native 'off' entity reappears 2 sec ago. DO NOT add a second
    # 600-second native minimum-OFF hold.
    off=create()
    assert await off._reconcile_native_after_supply_wake(spec,off.manager.cap)
    assert off.record['off_at']['climate.heater']==NOW-1800
    assert off.record['baseline']['climate.heater']['state']=='off'
    assert off.record['upstream']['native_wake']['native_state']=='off'
    # The real manual-override baseline reconciler must also accept the
    # reconnected appliance; a stale pre-supply baseline cannot pause it.
    assert await off._reconcile(spec)
    assert off.record.get('paused') is None
    assert await off._power(spec,off.manager.cap,'heat',automatic=False), (
        off.status,off.record)
    assert off.actual_commands[-1][1]=={'hvac_mode':'heat'}
    assert off.record['upstream']['native_wake']['reconciled'] is True

    # A genuine native ON is observed after the first controlled command.
    # Invalidate old supply-OFF credit so a subsequent real ON->OFF
    # cannot bypass the next full native minimum-OFF.
    off.states['climate.heater']=state('heat',changed=NOW)
    await off._observe_native_running(spec,off.manager.cap,
                                      off.states['climate.heater'])
    assert 'native_wake' not in off.record['upstream']
    off.now=NOW+10
    off.states['climate.heater']=state('off',changed=NOW+10)
    assert not await off._power(spec,off.manager.cap,'heat',automatic=False), (
        'New physical native OFF must observe new native min-OFF')
    assert off.status[0]=='minimum_off_hold'

    # An OFF report recreated with a different last_changed after
    # reconnection can hide an intervening manual ON->OFF. It must destroy
    # the old supply-off credit and start a genuine new native hold.
    changed_stamp=create()
    assert await changed_stamp._reconcile_native_after_supply_wake(
        spec,changed_stamp.manager.cap)
    changed_stamp.now=NOW+15
    changed_stamp.states['climate.heater']=state(
        'off',changed=NOW+15)
    await changed_stamp._observe_native_running(
        spec,changed_stamp.manager.cap,
        changed_stamp.states['climate.heater'])
    assert 'native_wake' not in changed_stamp.record['upstream']
    assert not await changed_stamp._power(
        spec,changed_stamp.manager.cap,'heat',automatic=False)
    assert changed_stamp.status[0]=='minimum_off_hold'

    # HA restart with supply still ON cannot prove there was no physical
    # native ON->OFF in the downtime. Discard credit, not the independent
    # historical relay ON/OFF minimums.
    after_restart=create()
    after_restart.manager.original_store={
        'version':1,'records':deepcopy(after_restart.records)
    }
    await after_restart.async_start()
    assert 'native_wake' not in after_restart.record['upstream']
    assert after_restart.record['upstream']['owned'] is True
    assert not await after_restart._power(
        spec,after_restart.manager.cap,'heat',automatic=False)

    # A powered device may itself restore an already-ON HEAT mode. That
    # ON came from HEM's explicitly acknowledged power restoration, not
    # a user-turned-on unrelated switch. It becomes supervised WITHOUT
    # another ON/OFF command, with a fresh conservative minimum-ON.
    active=create('heat')
    assert await active._reconcile_native_after_supply_wake(
        spec,active.manager.cap)
    owner=active.record['power']['climate.heater']
    assert owner['since']==NOW
    assert owner['min_on']==600. and owner['max_on']==7200.
    assert active.record['baseline']['climate.heater']['state']=='heat'
    assert await active._reconcile(spec)
    assert active.record.get('paused') is None
    assert not active.actual_commands
    assert not await active._power(
        spec,active.manager.cap,'off',automatic=False,shutdown=True)
    assert active.status[0]=='minimum_on_hold'
    active.now=NOW+600
    assert await active._power(
        spec,active.manager.cap,'off',automatic=False,shutdown=True)

    # Non-climate physical endpoints report HA "on" or an actual %
    # rather than their assigned "heat"/"dry"/"fan_only" capability role.
    # The same exact-device handoff must work for all supported domains.
    from types import SimpleNamespace as N
    for domain,entity,raw,role in (
        ('switch','switch.heater','on','heat'),
        ('input_boolean','input_boolean.heater','on','heat'),
        ('fan','fan.ventilator','on','fan_only'),
        ('humidifier','humidifier.dryer','on','dry'),
        ('number','number.valve','65','heat'),
        ('input_number','input_number.valve','55','cool'),
    ):
        variant=create('off')
        source=N(
            identifier=spec.identifier,area_id=spec.area_id,
            source_device_id=spec.source_device_id,
            source_entities=(entity,),
        )
        variant.states.pop('climate.heater')
        native=state(raw,domain=domain,changed=NOW-2)
        if domain in ('number','input_number'):
            native.attributes.update(
                unit_of_measurement='%', min=0, max=100,
            )
        variant.states[entity]=native
        variant.record['sources']=[entity]
        variant.record['baseline']={entity:b['snap'](native)}
        variant.manager.cap=N(
            primary=entity,domain=domain,modes=('off',role),
        )
        variant.manager.settings[M.SETTINGS][spec.identifier]['requested_mode']=role
        assert await variant._reconcile_native_after_supply_wake(
            source,variant.manager.cap), (domain,variant.status)
        assert entity in variant.record['power'],(domain,variant.record)
        assert not variant.actual_commands

    # A native proportional endpoint that actually reports 0% was OFF
    # through the external supply's disconnected interval as well.
    valve=create('off')
    valve_source=N(
        identifier=spec.identifier,area_id=spec.area_id,
        source_device_id=spec.source_device_id,
        source_entities=('number.valve',),
    )
    valve.states.pop('climate.heater')
    valve_off=state('0',domain='number',changed=NOW-2)
    valve_off.attributes.update(unit_of_measurement='%',min=0,max=100)
    valve.states['number.valve']=valve_off
    valve.record['sources']=['number.valve']
    valve.manager.cap=N(primary='number.valve',domain='number',
                          modes=('off','heat'))
    assert await valve._reconcile_native_after_supply_wake(
        valve_source,valve.manager.cap)
    assert valve.record['off_at']['number.valve']==NOW-1800
    assert await valve._power(
        valve_source,valve.manager.cap,'heat',automatic=False)

    # The startup check should run ONLY ONCE for an ACKed relay.
    n=len(active._saved)
    assert await active._reconcile_native_after_supply_wake(
        spec,active.manager.cap)
    assert len(active._saved)==n

    # The external relay being ON is insufficient. It must be previously
    # powered and acknowledged BY HEM for this exact native device.
    manual=create('heat',supply_owned=False)
    assert not await manual._reconcile_native_after_supply_wake(
        spec,manual.manager.cap)
    assert manual.record['power']=={}

    wrong_identity=create('heat')
    wrong_identity.record['upstream']['native_wake']['identity']['registry_id']='spoofed'
    assert not await wrong_identity._reconcile_native_after_supply_wake(
        spec,wrong_identity.manager.cap)
    assert not wrong_identity.record['power']

    unknown=create('heat')
    unknown.record['upstream']['native_wake']['on_at']=NOW-120
    assert not await unknown._reconcile_native_after_supply_wake(
        spec,unknown.manager.cap)
    assert not unknown.record['power']

    incomplete=create('off',off_age=300)
    assert not await incomplete._reconcile_native_after_supply_wake(
        spec,incomplete.manager.cap)
    assert not incomplete.actual_commands

    unauthorized=create('heat')
    unauthorized.manager.native_permission=False
    assert not await unauthorized._reconcile_native_after_supply_wake(
        spec,unauthorized.manager.cap)
    assert not unauthorized.record['power']

    pending=create('heat')
    pending.record['pending']={'entity':'climate.heater','phase':'intent'}
    assert not await pending._reconcile_native_after_supply_wake(
        spec,pending.manager.cap)
    assert not pending.record['power']

    # Multi-mode HVAC cannot be silently adopted when a mode wasn't
    # selected before HEM energised its upstream switch.
    ambiguous=create('cool')
    ambiguous.manager.settings[M.SETTINGS][spec.identifier]['requested_mode']=None
    assert not await ambiguous._reconcile_native_after_supply_wake(
        spec,ambiguous.manager.cap)
    assert ambiguous.record['power']=={}
    mismatch=create('cool')
    assert not await mismatch._reconcile_native_after_supply_wake(
        spec,mismatch.manager.cap)
    assert not mismatch.record['power']

    conflict=create('heat')
    conflict.manager.foreign_owner='other-automation'
    assert not await conflict._reconcile_native_after_supply_wake(
        spec,conflict.manager.cap)
    assert not conflict.record['power']

    # No native ON or minimum-off exemption when the source is offline.
    unavailable=create('off')
    unavailable.states['climate.heater']=state('unavailable',changed=NOW-2)
    assert not await unavailable._reconcile_native_after_supply_wake(
        spec,unavailable.manager.cap)

    # Tick must perform wake ownership reconciliation before baseline
    # manual-override checks or any native service request.
    src=(ROOT/'equipment_runtime.py').read_text()
    p=src.index('await self._reconcile_native_after_supply_wake(spec, cap)')
    assert p<src.index('if not await self._reconcile(spec):',p)
    assert 'relay.pop("native_wake", None)' in (
        ROOT/'equipment_power_switch.py').read_text()
    print('PASS Beta75: acknowledged supply OFF interval prevents extra native '
          'minimum-OFF; supervised restored ON without commands; genuine '
          'second native OFF remains protected; all ownership and mode '
          'refusals; one-shot boot handoff')


asyncio.run(evaluate())
