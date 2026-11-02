"""Beta90: no fabricated window opening, real registry contact and strict holds.

Extract actual native policy and arbitration source. Hardware-free tests.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace as Obj
import runpy
import unittest

ROOT=Path(__file__).resolve().parents[2]
# Import the production AST-backed legacy safety regressions, including
# real open, unknown, and sixty-second post-close interlocks.
prior=runpy.run_path(str(ROOT/'.github/tests/test_beta66_windows.py'))
spec=prior['spec']
make=prior['make']
Model=prior['Model']
contact=prior['contact']

class TestWindowEvidence(unittest.TestCase):
    def test_without_configured_window_no_phantom_contact(self):
        s=make(opened=False)
        # No explicit room_sources; manager.plan may not have climate_plan
        # until the next planner tick. Previously this generated [""] and
        # permanently blocked a real purifier with window_state_unknown.
        s.manager.settings.pop('room_sources',None)
        s.manager.plan=Obj(
            environment={},
            rooms=(Obj(area_id=spec.area_id,windows=()),),
            climate_rooms=(),
        )
        result=s._window_policy(spec)
        self.assertEqual(result['status'],'window_contacts_not_configured')
        self.assertFalse(result['blocked'])
        self.assertEqual(result['contacts'],[])
        self.assertEqual(result['open_contacts'],[])
        self.assertEqual(result['unknown_contacts'],[])

    def test_missing_room_plan_does_not_authorize_no_window(self):
        s=make(opened=False)
        s.manager.settings.pop('room_sources',None)
        # Absence of a whole room plan is not a known zero-window inventory.
        info=s._window_policy(spec)
        self.assertEqual(info['status'],'window_state_unknown')
        self.assertEqual(info['evidence'],'room_window_inventory_unavailable')
        self.assertTrue(info['blocked'])
        self.assertEqual(info['contacts'],[])

    def test_real_unavailable_selected_contact_remains_blocking_and_named(self):
        s=make(opened=False)
        s.manager.settings['room_sources'][spec.area_id]['windows']=[
            'binary_sensor.unavailable_window'
        ]
        info=s._window_policy(spec)
        self.assertEqual(info['status'],'window_state_unknown')
        self.assertTrue(info['blocked'])
        self.assertEqual(info['unknown_contacts'],['binary_sensor.unavailable_window'])
        self.assertEqual(info['contact_states']['binary_sensor.unavailable_window'],'missing')
        self.assertFalse(info['open_contacts'])

    def test_actual_open_contact_reported_only_when_physically_on(self):
        s=make(opened=False)
        self.assertEqual(s._window_policy(spec)['contact_states']['binary_sensor.window'],'off')
        contact(s,'on')
        info=s._window_policy(spec)
        self.assertTrue(info['blocked'])
        self.assertEqual(info['status'],'window_open_pause')
        self.assertEqual(info['open_contacts'],['binary_sensor.window'])
        self.assertEqual(info['contact_states']['binary_sensor.window'],'on')

    def test_real_gate_recognizes_registry_inherited_window_class(self):
        text=(ROOT/'climate_arbitration.py').read_text(encoding='utf-8')
        tree=ast.parse(text)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
                  and n.name=='_contact_interlock')
        class State:
            domain='binary_sensor'
            def __init__(self,value):
                self.state=value
                self.attributes={} # Original HA registry owns device_class.
        state=State('off')
        hass=Obj(states=Obj(get=lambda id:state))
        ns={
            'Any':object,
            'entity_area':lambda h,e:'bedroom',
            'is_window':lambda h,s:s.domain=='binary_sensor' and
                getattr(s,'registry_class','window')=='window',
        }
        exec(compile(ast.Module(body=[node],type_ignores=[]),
                     'climate_arbitration.py','exec'),ns)
        gate=ns['_contact_interlock']
        plan={'window_safe':True,'window_contacts':['binary_sensor.window']}
        self.assertTrue(gate(hass,'bedroom',plan),
                        'HA-registry device class must be accepted even when state attributes omit it')
        state.state='on'
        self.assertFalse(gate(hass,'bedroom',plan))
        state.state='unknown'
        self.assertFalse(gate(hass,'bedroom',plan))
        state.state='off'
        ns['entity_area']=lambda h,e:'other_room'
        self.assertFalse(gate(hass,'bedroom',plan))

if __name__=='__main__':
    unittest.main(verbosity=2)
