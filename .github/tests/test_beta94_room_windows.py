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
        'binary_sensor.window','binary_sensor.unavailable_window']
    p=unknown._window_policy(spec)
    assert p['blocked'] and p['status']=='window_state_unknown',p
    assert p['unknown_contacts']==['binary_sensor.unavailable_window'],p
    print('BETA94_ROOM_SCOPED_WINDOW_OPEN_CLOSE_60S_NO_CROSS_ROOM_PAUSE=PASS')

asyncio.run(scenarios())
