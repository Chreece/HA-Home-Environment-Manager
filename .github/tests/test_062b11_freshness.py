"""Freshness policy from real HEM code, including its actual stale readers.

No Home Assistant service calls or timing mocks that invent same-value updates.
"""
from __future__ import annotations
import ast
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
import sys,types,unittest
from types import SimpleNamespace as N

ROOT=Path(__file__).resolve().parents[2]/'custom_components/environment_manager'
PKG='hem_b11_test'
package=types.ModuleType(PKG);package.__path__=[str(ROOT)];sys.modules[PKG]=package
spec=importlib.util.spec_from_file_location(PKG+'.freshness_policy',ROOT/'freshness_policy.py')
policy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=policy;spec.loader.exec_module(policy)
NOW=datetime(2026,11,12,18,0,tzinfo=timezone.utc)

def state(domain,age=0,change_days=5,reported=True,state='50',restored=False):
    s=N(domain=domain,state=state,attributes={'restored':restored},
        last_updated=NOW-timedelta(minutes=age),
        last_reported=(NOW-timedelta(minutes=age)) if reported else None,
        last_changed=NOW-timedelta(days=change_days))
    return s

def extracted(path,name,global_values):
    tree=ast.parse((ROOT/path).read_text())
    func=next(f for f in ast.walk(tree) if isinstance(f,ast.FunctionDef) and f.name==name)
    m=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),func],type_ignores=[])
    ns={'__package__':PKG,**global_values}
    exec(compile(ast.fix_missing_locations(m),str(ROOT/path),'exec'),ns)
    return ns[name]

class TestPolicy(unittest.TestCase):
    def test_auto_defaults_and_custom_are_valid_and_independent(self):
        env=policy.configured_limit({},family='environment',minutes_key='max_age_minutes',mode_key='max_age_mode')
        home=policy.configured_limit({},family='home_presence',minutes_key='source_stale_minutes',mode_key='source_freshness_mode')
        room=policy.configured_limit({},family='room_presence',minutes_key='occupancy_stale_minutes',mode_key='occupancy_freshness_mode')
        self.assertEqual((env.mode,home.mode,room.mode),('auto','auto','auto'))
        for typ,expected in [('weather',180),('sensor',90),('binary_sensor',None)]:
            self.assertEqual(policy.effective_minutes(state(typ),env),expected)
        self.assertEqual(policy.effective_minutes(state('sensor'),home),240)
        self.assertEqual(policy.effective_minutes(state('sensor'),room),240)
        manual=policy.configured_limit({'max_age_mode':'custom','max_age_minutes':15},family='environment',minutes_key='max_age_minutes',mode_key='max_age_mode')
        self.assertEqual(policy.effective_minutes(state('weather'),manual),15)
        self.assertEqual(policy.effective_minutes(state('sensor'),manual),15)
        self.assertEqual(policy.effective_minutes(state('binary_sensor'),manual),15)

    def test_bad_config_fails_to_finite_defaults(self):
        for value in (-1,0,'bad',float('nan'),float('inf'),True,10**1000):
            with self.subTest(value=str(value)[:15]):
                conf={'max_age_minutes':value,'max_age_mode':'garbage'}
                configured=policy.configured_limit(conf,family='environment',minutes_key='max_age_minutes',mode_key='max_age_mode')
                self.assertEqual(float(configured),90)
                self.assertEqual(configured.mode,'auto')

    def test_real_discovery_stale_reader_and_repeated_same_value(self):
        f=extracted('discovery.py','is_stale',{'dt_util':N(utcnow=lambda:NOW),'timedelta':timedelta})
        auto=policy.configured_limit({},family='environment',minutes_key='max_age_minutes',mode_key='max_age_mode')
        self.assertFalse(f(state('weather',age=179),auto))
        self.assertTrue(f(state('weather',age=181),auto))
        self.assertFalse(f(state('sensor',age=89),auto))
        self.assertTrue(f(state('sensor',age=91),auto))
        # The physical reading has been 50 for five days, but HA has
        # actually re-published that unchanged value within the age limit.
        self.assertFalse(f(state('sensor',age=3,change_days=5),auto))
        self.assertTrue(f(state('sensor',age=91,change_days=5),auto))
        self.assertFalse(f(state('binary_sensor',age=9999),auto))
        self.assertTrue(f(state('binary_sensor',age=9999,restored=True),auto))
        self.assertTrue(f(state('sensor',age=3,state='unavailable'),auto))
        missing_stamp=state('sensor');missing_stamp.last_updated=None;missing_stamp.last_reported=None
        self.assertTrue(f(missing_stamp,auto))
        future=state('sensor');future.last_reported=NOW+timedelta(seconds=8)
        self.assertTrue(f(future,auto))
        custom=policy.configured_limit({'max_age_mode':'custom','max_age_minutes':30},family='environment',minutes_key='max_age_minutes',mode_key='max_age_mode')
        self.assertTrue(f(state('weather',age=31),custom))
        self.assertFalse(f(state('weather',age=29),custom))

    def test_real_home_presence_freshness_never_inferrs_away_from_stale(self):
        f=extracted('occupancy_policy.py','_fresh',{'datetime':datetime,'timezone':timezone})
        auto=policy.configured_limit({},family='home_presence',minutes_key='source_stale_minutes',mode_key='source_freshness_mode')
        # Reader uses actual wall clock. This test uses a current stamp.
        now=datetime.now(timezone.utc)
        current=state('sensor');current.last_reported=now-timedelta(minutes=200)
        self.assertTrue(f(current,auto))
        current.last_reported=now-timedelta(minutes=241)
        self.assertFalse(f(current,auto))
        current.last_reported=now-timedelta(minutes=3);current.state='unavailable'
        self.assertFalse(f(current,auto))
        current.state='0';current.attributes['restored']=True
        self.assertFalse(f(current,auto))
        current.attributes['restored']=False
        self.assertTrue(f(current,auto))
        current.last_reported=now+timedelta(minutes=1)
        self.assertFalse(f(current,auto))

    def test_report_age_not_last_changed_and_no_magic_zero(self):
        s=state('weather',age=9,change_days=30)
        self.assertEqual(policy.observed_age_seconds(s,now=NOW),540)
        s.last_reported=None
        self.assertEqual(policy.observed_age_seconds(s,now=NOW),540)
        s.last_updated=None
        self.assertIsNone(policy.observed_age_seconds(s,now=NOW))

if __name__=='__main__':unittest.main(verbosity=2)
