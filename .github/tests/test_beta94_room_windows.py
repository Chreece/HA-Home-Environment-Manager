"""Beta94: only the managed device's own real windows may hold its output.

Exercises production equipment_window.evaluate, EquipmentRuntime._gate and
equipment_power_switch.approved_demand through pre-existing native command
harnesses. No live HA services, switch calls, or physical device writes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import runpy
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]
b=runpy.run_path(str(ROOT/'.github/tests/test_beta66_windows.py'))
make,contact,spec,Model=(b[k] for k in ('make','contact','spec','Model'))
approved=b['b']['approved_demand']

async def scenarios():
    # A bedroom WINDOW opening cannot pause a purifier/dehumidifier belonging
    # to another room. Even a polluted old global plan may claim all windows
    # are open: the real per-controller local source is authoritative.
    r=make(opened=False,native='off')
    contact(r,'on',entity='binary_sensor.foreign_window')
    r.manager.settings['room_sources'][spec.area_id]['windows']=[
        'binary_sensor.window','binary_sensor.foreign_window']
    r.manager.plan.update(window_contacts=['binary_sensor.foreign_window'],
                          window_safe=False)
    policy=r._window_policy(spec)
    assert policy['status']=='window_closed_ready',policy
    assert policy['contacts']==['binary_sensor.window'],policy
    assert policy['ignored_other_room_contacts']==['binary_sensor.foreign_window'],policy
    assert not policy['blocked']
    cfg=Model.settings(r.manager,spec)
    assert r._gate(spec,r.manager.cap,cfg,r.manager.plan,'dry',automatic=True) is None
    assert approved(r,spec,cfg,r.manager.cap) is True

    # Another room can OPEN and CLOSE repeatedly without resetting this
    # device's own verified closed-contact timer or controller mode.
    for index in range(6):
        contact(r,'off' if index%2 else 'on',entity='binary_sensor.foreign_window')
        assert not r._window_policy(spec)['blocked']
        assert r._gate(spec,r.manager.cap,cfg,r.manager.plan,'dry',automatic=True) is None
        assert cfg['control_mode']=='pid'
        assert not r.record.get('paused')

    # A genuine local OPEN must stop the native output; closing it must
    # recover after sixty continuously verified seconds even if the old
    # whole-room plan still claims window_safe=False.
    contact(r,'on')
    policy=r._window_policy(spec)
    assert policy['blocked'] and policy['stop_requested'],policy
    assert r._gate(spec,r.manager.cap,cfg,r.manager.plan,'dry',automatic=True)=='window_open_pause'
    contact(r,'off',when=r.now)
    for seconds in (0,10,30,59):
        r.now=b['BASE']+seconds
        policy=r._window_policy(spec)
        assert policy['blocked'] and policy['status']=='window_close_warmup',policy
    r.now=b['BASE']+60
    policy=r._window_policy(spec)
    assert policy['status']=='window_closed_ready' and not policy['blocked'],policy
    assert r._gate(spec,r.manager.cap,cfg,r.manager.plan,'dry',automatic=True) is None
    assert approved(r,spec,cfg,r.manager.cap) is True
    assert cfg['control_mode']=='pid'
    assert not r.record.get('paused')

    # A room with NO selected local contacts is not held by another room's
    # OPEN or by a stale global plan.
    no_windows=make(opened=False,native='off')
    no_windows.manager.settings['room_sources'][spec.area_id]['windows']=[]
    no_windows.manager.plan.update(
        window_contacts=['binary_sensor.foreign_window'],window_safe=False)
    contact(no_windows,'on',entity='binary_sensor.foreign_window')
    p=no_windows._window_policy(spec)
    assert p['contacts']==[] and not p['blocked'],p
    cfg2=Model.settings(no_windows.manager,spec)
    assert approved(no_windows,spec,cfg2,no_windows.manager.cap) is True
    assert no_windows._gate(
        spec,no_windows.manager.cap,cfg2,no_windows.manager.plan,'dry',automatic=True
    ) is None

    # Legacy unconfigured rooms prefer the local inventory even if the
    # climate_plan contains a stale foreign window inventory.
    fallback=make(opened=False,native='off')
    fallback.manager.settings.pop('room_sources',None)
    fallback.manager.plan=N(
        rooms=(N(area_id=spec.area_id,windows=()),),
        climate_rooms=(),
        environment={spec.area_id:{'climate_plan':{
            'window_contacts':['binary_sensor.foreign_window'],
            'window_safe':False}}},
    )
    result=fallback._window_policy(spec)
    assert result['status']=='window_contacts_not_configured',result
    assert not result['blocked']

    # A selected LOCAL unavailable contact still fails closed and must not
    # be considered closed just because every foreign window is shut.
    unknown=make(opened=False,native='off')
    unknown.manager.settings['room_sources'][spec.area_id]['windows']=[
        'binary_sensor.window','binary_sensor.window_unavailable']
    p=unknown._window_policy(spec)
    assert p['blocked'] and p['status']=='window_state_unknown',p
    assert p['unknown_contacts']==['binary_sensor.window_unavailable'],p

    tick = b['b']['tick']
    # Lose a local contact while DRY is already running. A second, closed
    # contact cannot authorize continued operation or an early restart.
    for lost_state in ('unavailable', 'unknown', 'missing', 'restored'):
        running = make(opened=False)
        room = running.manager.settings['room_sources'][spec.area_id]
        room['windows'].append('binary_sensor.window2')
        contact(running, 'off', entity='binary_sensor.window2')
        assert not running._window_policy(spec)['blocked']
        entity = 'binary_sensor.window'
        if lost_state == 'missing':
            del running.states[entity]
        elif lost_state == 'restored':
            running.states[entity].attributes['restored'] = True
        else:
            contact(running, lost_state)
        await tick(running, spec)
        assert running.issued == [
            ('climate', 'set_hvac_mode', 'climate.comfee', {'hvac_mode': 'off'})
        ], (lost_state, running.issued, running.statuses)
        assert await running._reconcile(spec)
        await tick(running, spec)
        assert running.statuses[spec.identifier]['status'] == 'window_state_unknown'
        assert running._window_policy(spec)['open_contacts'] == []
        contact(running, 'off')
        assert running._window_policy(spec)['remaining_seconds'] == 60
        running.now += 59
        await tick(running, spec)
        assert len(running.issued) == 1
        running.now += 1
        assert not running._window_policy(spec)['blocked']

    for protection in ('no_power_permission', 'defrosting', 'device_opt_out'):
        running = make(opened=False, enabled=protection != 'device_opt_out')
        contact(running, 'unavailable')
        if protection == 'no_power_permission':
            running.manager.authorized = False
        elif protection == 'defrosting':
            running.states['climate.comfee'].attributes['hvac_action'] = 'defrosting'
        if protection == 'device_opt_out':
            assert not running._window_policy(spec)['blocked']
            assert not running._stop_policy_verified(spec, running.manager.cap, 'window')
        else:
            await tick(running, spec)
            assert not running.issued, (protection, running.issued)

    # A contact can disappear while a native ON intent is being persisted.
    starting = make(opened=False, native='off')
    starting.record['capabilities'] = b['b']['asdict'](starting.manager.cap)
    starting.on_save = lambda: contact(starting, 'unavailable')
    assert not await starting._power(spec, starting.manager.cap, 'dry', automatic=True)
    assert not starting.issued and starting.record.get('pending') is None

    dwelling = make(opened=False)
    dwelling.states['climate.comfee'] = b['state']('dry', when=dwelling.now)
    contact(dwelling, 'unavailable')
    await tick(dwelling, spec)
    assert not dwelling.issued
    assert dwelling.statuses[spec.identifier]['status'] == 'minimum_on_hold'
    dwelling.now += 600
    await tick(dwelling, spec)
    assert dwelling.issued == [('climate', 'set_hvac_mode', 'climate.comfee', {'hvac_mode': 'off'})]
    print('BETA94_ROOM_SCOPED_WINDOW_OPEN_CLOSE_60S_NO_CROSS_ROOM_PAUSE=PASS')

asyncio.run(scenarios())
