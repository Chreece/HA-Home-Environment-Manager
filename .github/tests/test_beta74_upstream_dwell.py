"""Beta74 actual switch controller: independent per-device ON/OFF and cooldown.

Exercise real `before_tick`, `_send`, `_dispatch_safe`, cold-start minimums,
persisted physical ACK timestamps and in-session state observation, using the
Beta64 isolated HA simulator plus current source functions. Never controls HA.
"""
from __future__ import annotations

import asyncio
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
b=runpy.run_path(str(ROOT/'.github/tests/test_beta64_sleep_idle.py'))
Simulator, Model, spec = b['Simulator'],b['Model'],b['spec']
before_tick, send=b['before_tick'],b['send']
dispatch_safe=b['dispatch_safe']
supply_minimum_on=b['supply_minimum_on']
supply_minimum_off=b['supply_minimum_off']
device_supply_dwell=b['device_supply_dwell']
clock=b['BASE']
state=b['state']

# The real model.timing() applies these native per-device minimums. The
# fixture models only the same-domain configured physical minimums.
Model.timing=staticmethod(lambda manager, spec, cap, config=None: (
    max(600, (config or Model.settings(manager,spec))['min_on_seconds']),
    max(600, (config or Model.settings(manager,spec))['min_off_seconds']),
    7200,
))
def simulate(*, on=900, off=1200, cooldown=180,
             supply='on', owned=True, on_age=0,
             native='off', humidity=53):
    sim=Simulator(sleeping=False,supply=supply,native=native,
                  owned=owned,humidity=humidity)
    cfg=Model.settings(sim.manager,spec)
    cfg.update(min_on_seconds=on,min_off_seconds=off,
               power_switch_cooldown_seconds=cooldown)
    sim.states['switch.strip']=state(supply,when=clock-on_age)
    if supply=='on' and owned:
        sim.record['upstream'].update(
            on_at=clock-on_age,on_min_seconds=on)
    if supply=='off':
        sim.record['upstream'].update(
            off_at=clock-on_age,off_min_seconds=off)
    return sim

def supply_calls(sim,desired=None):
    rows=[c for c in sim.issued if c[0]=='switch']
    return [row for row in rows if desired is None or row[1]=='turn_'+desired]


async def tests():
    # Fast cooldown never bypasses physical minimum ON for a heater or
    # compressor. Once both timers have expired, send exactly ONE OFF.
    sim=simulate(on=900,off=1200,cooldown=60,on_age=300)
    assert await before_tick(sim,spec) is False
    assert sim.record['upstream']['idle_since']==clock
    assert not supply_calls(sim)
    for elapsed in (60,599):
        sim.now=clock+elapsed
        # After cooldown it reports a physical minimum-ON hold; that is
        # a handled controller status (True), not a new physical command.
        assert await before_tick(sim,spec) is True
        assert not supply_calls(sim),elapsed
    sim.now=clock+600
    assert await before_tick(sim,spec) is True
    assert len(supply_calls(sim,'off'))==1,sim.issued
    assert sim.record['upstream']['pending']['min_off_seconds']==1200
    assert sim.record['upstream']['pending']['min_on_seconds']==900
    # Confirm physical switch ACK only after the real switch reports OFF.
    sim.now+=1
    assert await before_tick(sim,spec) is True
    relay=sim.record['upstream']
    assert relay['owned'] is False and relay['pending'] is None
    assert relay['off_at']==clock+601 and relay['off_min_seconds']==1200
    assert len(supply_calls(sim,'off'))==1

    # Demand comes back at t+1000: still below 20min OFF dwell. No ON.
    sim.humidity=68
    for elapsed in (1,1199):
        sim.now=clock+601+elapsed
        assert await before_tick(sim,spec) is True
        assert not supply_calls(sim,'on'),elapsed
    sim.now=clock+601+1200
    assert await before_tick(sim,spec) is True
    assert len(supply_calls(sim,'on'))==1
    assert relay['pending']['min_on_seconds']==900
    sim.now+=1
    # The acknowledged ON relay now hands normal control to the native
    # appliance (False means no upstream hold, not a failed ACK).
    assert await before_tick(sim,spec) is False
    assert relay['owned'] is True and relay['pending'] is None
    assert relay['on_at']==sim.now
    assert relay['on_min_seconds']==900

    # No need to wait another artificial 300sec startup to cut proven idle
    # equipment. Long-lived supply already satisfies min ON; 60sec cooldown
    # is the only remaining delay.
    efficient=simulate(on=600,off=900,cooldown=60,on_age=1500)
    efficient._started=clock-20
    await before_tick(efficient,spec)
    assert efficient.record['upstream']['idle_since']==clock
    efficient.now=clock+60
    await before_tick(efficient,spec)
    assert len(supply_calls(efficient,'off'))==1

    # A stricter native minimum takes precedence over the user-shortened
    # cooldown; extending it while already ON must also extend the hold.
    changed=simulate(on=600,off=600,cooldown=60,on_age=800)
    await before_tick(changed,spec)
    changed.manager.settings['equipment_controllers'][spec.identifier][
        'min_on_seconds']=1800
    changed.now=clock+60
    await before_tick(changed,spec)
    assert not supply_calls(changed)
    changed.now=clock+1000
    await before_tick(changed,spec)
    assert len(supply_calls(changed,'off'))==1

    # Return of demand cancels the idle countdown, rather than cutting an
    # otherwise needed appliance after the original cooldown expires.
    needed=simulate(on=600,off=600,cooldown=300,on_age=1000)
    await before_tick(needed,spec)
    needed.now=clock+100
    needed.humidity=68
    await before_tick(needed,spec)
    assert needed.record['upstream'].get('idle_since') is None
    needed.now=clock+1000
    await before_tick(needed,spec)
    assert not supply_calls(needed,'off')

    # Don't claim or switch OFF someone else's already ON outlet.
    unowned=simulate(on=600,off=600,cooldown=60,on_age=10000,owned=False)
    for age in (0,500,1000):
        unowned.now=clock+age
        assert await before_tick(unowned,spec) is False
    assert not supply_calls(unowned)

    # No false 'idle' from unavailable or active downstream equipment.
    for native in ('unavailable','dry'):
        unsafe=simulate(on=600,off=600,cooldown=60,
                        on_age=2000,native=native)
        await before_tick(unsafe,spec)
        unsafe.now=clock+999
        await before_tick(unsafe,spec)
        assert not supply_calls(unsafe),native
    active=simulate(on=600,off=600,cooldown=60,on_age=2000)
    active.record['pending']={'entity':'climate.comfee'}
    await before_tick(active,spec)
    active.now=clock+999
    await before_tick(active,spec)
    assert not supply_calls(active),'In-flight native operation'

    # HA reset last_changed to NOW for a continuously OFF switch during
    # reboot. The previously acknowledged OFF timestamp must remain valid.
    reboot=simulate(on=600,off=1200,cooldown=60,
                    on_age=1600,supply='off',owned=False,humidity=68)
    reboot.states['switch.strip']=state('off',when=clock)
    assert supply_minimum_off(
        reboot,spec,Model.settings(reboot.manager,spec),reboot.manager.cap,
        reboot.record['upstream'],reboot.states['switch.strip'],clock
    )
    await before_tick(reboot,spec)
    assert len(supply_calls(reboot,'on'))==1
    assert reboot.record['upstream']['off_at']==clock-1600

    # Per-device configured MIN OFF longer than legacy constant; a fresh
    # demand may NEVER override that time or a retained greater OFF minimum.
    longer=simulate(on=600,off=2400,cooldown=60,
                    on_age=900,supply='off',owned=False,humidity=68)
    assert not supply_minimum_off(
        longer,spec,Model.settings(longer.manager,spec),longer.manager.cap,
        longer.record['upstream'],longer.states['switch.strip'],clock
    )
    await before_tick(longer,spec)
    assert not supply_calls(longer,'on')
    longer.now=clock+1499
    await before_tick(longer,spec)
    assert not supply_calls(longer,'on')
    longer.now=clock+1500
    await before_tick(longer,spec)
    assert len(supply_calls(longer,'on'))==1

    # If a user toggles an unowned relay ON then back OFF between separate
    # controller ticks, the old OFF dwell must not authorize an immediate ON.
    manual=simulate(on=600,off=1800,cooldown=60,
                    on_age=4000,supply='off',owned=False,humidity=53)
    manual.states['switch.strip']=state('off',when=clock-4000)
    await before_tick(manual,spec)
    assert not supply_calls(manual), "Unowned relay must not be powered without demand"
    manual.humidity=53
    manual.states['switch.strip']=state('on',when=clock+5)
    manual.now=clock+5
    await before_tick(manual,spec)
    manual.states['switch.strip']=state('off',when=clock+10)
    manual.now=clock+10
    manual.humidity=68
    await before_tick(manual,spec)
    assert not supply_calls(manual,'on'),manual.record['upstream']
    assert manual.record['upstream']['off_at']==clock+10

    # Repeated unchanged states must not continuously write Store.
    stable=simulate(on=900,off=1200,cooldown=300,on_age=1600)
    await before_tick(stable,spec)
    count=len(stable._save_log)
    for age in (10,20,30,40):
        stable.now=clock+age
        await before_tick(stable,spec)
    assert len(stable._save_log)==count

    # Cold-start policy has no verified native device capabilities, but
    # still inherits the stricter configured per-device ON/OFF minimum.
    blind=simulate(on=1800,off=2400,cooldown=60,
                   on_age=3000,supply='off',owned=False,humidity=68)
    blind.manager.cap=None
    assert device_supply_dwell(
       blind,spec,Model.settings(blind.manager,spec),None)==(1800,2400)
    # Each configured device/supply retains its own minimums; a 10-minute
    # radiator cannot shorten an 30-minute compressor's ON protection.
    radiator=simulate(on=600,off=1800,cooldown=60,on_age=1200)
    compressor=simulate(on=1800,off=2400,cooldown=60,on_age=1200)
    for device in (radiator,compressor):
        await before_tick(device,spec)
        device.now=clock+60
        await before_tick(device,spec)
    assert len(supply_calls(radiator,'off'))==1
    assert not supply_calls(compressor,'off')
    compressor.now=clock+600
    await before_tick(compressor,spec)
    assert len(supply_calls(compressor,'off'))==1

    # Status attributes expose the actual persisted ON/OFF history and
    # calculated wait. The diagnostic read must never command hardware.
    import ast
    from types import SimpleNamespace as N
    tree=ast.parse((ROOT/'equipment_status.py').read_text())
    klass=next(n for n in tree.body if isinstance(n,ast.ClassDef)
               and n.name=='ControllerStatusSensor')
    method=next(n for n in klass.body if isinstance(n,ast.FunctionDef)
                and n.name=='extra_state_attributes')
    method.decorator_list=[]
    Model.profile_name=staticmethod(lambda cfg,plan:'home')
    ns={'equipment':Model}
    exec(compile(ast.Module(body=[method],type_ignores=[]),
                 'equipment_status.py','exec'),ns)
    radiator.manager.plan=N(environment={})
    view=N(_manager=radiator.manager,_spec=spec,
           controller_settings=Model.settings(radiator.manager,spec))
    commands_before=len(radiator.issued)
    attrs=ns['extra_state_attributes'](view)
    assert attrs['upstream_device_minimum_on_seconds']==600
    assert attrs['upstream_device_minimum_off_seconds']==1800
    assert attrs['upstream_power_state']=='off' or attrs['upstream_power_state']=='on'
    assert len(radiator.issued)==commands_before

    print('PASS Beta74: actual relay native minimum ON/OFF, ACK timestamps, '
          'demand-safe cooldown, no premature OFF/ON, legacy state recovery, '
          'manual transitions, unowned and unknown-source safeguards, '
          'no unchanged-state persistence storm')


asyncio.run(tests())
