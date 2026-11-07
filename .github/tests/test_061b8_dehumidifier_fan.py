"""Advertised DRY fan stages and live quiet ceilings through native dispatch.

Production model, PID, fan allocation, quiet policy, journals and power dwell
execute with isolated HA transport and qualified room/sleep observations.
Fan speed is independent of the compressor's binary PWM timing.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]
fixture = runpy.run_path(str(ROOT / '.github/tests/test_061b7_runtime_mold.py'))
Base, model, production, PACKAGE = (
    fixture[name] for name in ('MoldRuntime', 'model', 'production', 'PACKAGE'))
fixture['b']['base']['extract'](ROOT / 'equipment_runtime.py', (
    '_quiet_context', '_quiet_fan_correction_required', '_defer_obsolete_quiet_fan_retry',
), production.__dict__)
allocator = importlib.import_module(PACKAGE + '.pid_output_allocator')
capacity = importlib.import_module(PACKAGE + '.pid_fan_capacity')
occupancy = importlib.import_module(PACKAGE + '.occupancy_policy')
# These are the already-qualified room facts at the HA input boundary. The
# actual quiet policy below chooses which configured flag applies to them.
occupancy.home_presence = lambda *args: ('home', 'qualified_fixture', [])
occupancy.controlled_sleep_presence = lambda hass, *args, **kwargs: (
    hass.fixture.manager.plan.get('sleeping'), 'qualified_fixture')
production.room_presence = lambda hass, *args, **kwargs: (
    hass.fixture.manager.plan.get('occupancy'), 'qualified_fixture', [])


class FanRuntime(Base):
    _quiet_context = production._quiet_context
    _quiet_fan_correction_required = production._quiet_fan_correction_required
    _defer_obsolete_quiet_fan_retry = production._defer_obsolete_quiet_fan_retry

    def __init__(self, *, names=('Low', 'Medium', 'High'), method='pid',
                 humidity_target=False, **profile):
        super().__init__(method=method, humidity_target=humidity_target, minimum=30)
        self.state.attributes.update(fan_modes=list(names), fan_mode=names[-1], humidity=50)
        self.state.attributes['supported_features'] |= model.FAN
        raw = self.raw()
        raw.update(_native_timing_version=1, min_on_seconds=120., min_off_seconds=120.,
                   max_on_seconds=7200.)
        raw['mode_settings']['dry'].update({
            'kp': 100., 'ki': 0., 'kd': 0., 'sample_seconds': 120.,
            'cycle_seconds': 600., **profile,
        })
        self.manager.entry.options[model.SETTINGS][self.spec.identifier] = raw

    def feedback(self, *, fan=None, mode=None, human=False):
        if mode is not None:
            self.report(mode=mode)
        if fan is not None:
            self.state.attributes['fan_mode'] = fan
        self.state.last_updated = datetime.fromtimestamp(self.now, timezone.utc)
        if human:
            self.state.context.user_id = 'real-user'
            self.state.context.parent_id = None
            self.state.context.id = 'new-human-action'


class Driver:
    def __init__(self, **kwargs):
        self.r = FanRuntime(**kwargs)
        self.origin = self.r.now
        self.seen = 0
        self.events = []

    async def at(self, seconds, *, acknowledge=True, acknowledge_humidity=False):
        r = self.r
        assert seconds >= r.now - self.origin
        r.now = self.origin + seconds
        for _ in range(8):
            await r.evaluate()
            calls = r.calls[self.seen:]
            self.seen = len(r.calls)
            if not calls:
                break
            for call in calls:
                self.events.append((seconds, call['service'], deepcopy(call['data'])))
                if acknowledge:
                    if call['service'] == 'set_hvac_mode':
                        r.feedback(mode=call['data']['hvac_mode'])
                    elif call['service'] == 'set_fan_mode':
                        r.feedback(fan=call['data']['fan_mode'])
                    elif call['service'] == 'set_humidity' and acknowledge_humidity:
                        r.state.attributes['humidity'] = call['data']['humidity']
            if not acknowledge:
                break


class FanStagesTests(unittest.IsolatedAsyncioTestCase):
    async def test_pid_selects_only_advertised_low_medium_high_stages(self):
        for names in (('low', 'medium', 'high'), ('Low', 'Medium', 'High')):
            for demand, index in ((10., 0), (50., 1), (90., 2)):
                with self.subTest(names=names, demand=demand):
                    r = FanRuntime(names=names)
                    r.state.attributes['fan_mode'] = names[0 if index == 2 else 2]
                    r.own_running(age=700)
                    physical = deepcopy((r.record['power'], r.record['off_at']))
                    self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, demand, True))
                    self.assertEqual(r.calls[-1]['service'], 'set_fan_mode')
                    self.assertEqual(r.calls[-1]['data'], {'fan_mode': names[index]})
                    self.assertEqual((r.record['power'], r.record['off_at']), physical)
                    self.assertFalse(r.record['pending']['power'])

    async def test_occupied_and_sleep_quiet_rules_cap_both_named_case_variants(self):
        for names in (('low', 'medium', 'high'), ('Low', 'Medium', 'High')):
            for rule in ('quiet_occupied', 'quiet_sleep'):
                for method in ('automatic', 'pid'):
                    with self.subTest(names=names, rule=rule, method=method):
                        r = FanRuntime(names=names, method=method, **{rule: True})
                        r.manager.plan.update(occupancy='occupied' if rule == 'quiet_occupied' else 'unoccupied',
                                              sleeping=rule == 'quiet_sleep')
                        r.own_running(age=700)
                        self.assertTrue(r._quiet_context(r.spec, r.cfg, r.manager.plan))
                        self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan,
                                                    90. if method == 'pid' else None, True))
                        self.assertEqual(r.calls[-1]['data'], {'fan_mode': names[0]})

    async def test_quiet_is_a_ceiling_and_does_not_raise_a_lower_normal_stage(self):
        r = FanRuntime(method='automatic', quiet_occupied=True, quiet_fan_mode='Medium',
                       fan_mode='Low')
        r.own_running(age=700)
        self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, None, True))
        self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})

    async def test_saved_quiet_label_uses_only_a_unique_advertised_case_match(self):
        for names in (('Low', 'Medium', 'High'), ('LOW', 'MEDIUM', 'HIGH')):
            with self.subTest(names=names):
                r = FanRuntime(names=names, quiet_occupied=True, quiet_fan_mode='low')
                r.own_running(age=700)
                self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True))
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': names[0]})
        self.assertIsNone(allocator.quiet_discrete_fan_speed(
            'High', modes=('Low', 'LOW', 'High'), quiet_mode='low'))
        self.assertIsNone(allocator.quiet_discrete_fan_speed(
            'High', modes=('Low', 'High'), quiet_mode='unadvertised'))

    async def test_current_quiet_caps_a_precomputed_measured_allocation(self):
        r = FanRuntime(quiet_sleep=True)
        curve = capacity.build_model(percentage=False, advertised_modes=r.cap.fan_modes,
                                     measured={'pid_capacity_stage_1': 30., 'pid_capacity_stage_2': 65.})
        old = capacity.allocate(90., curve, quiet=False, quiet_mode=None, quiet_percentage=30,
                                fan_min_percentage=1, fan_max_percentage=100)
        self.assertEqual(old.speed, 'High')
        r.manager.plan['sleeping'] = True
        r.own_running(age=700)
        self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True, old.speed))
        self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})
        current = capacity.allocate(90., curve, quiet=True, quiet_mode=None, quiet_percentage=30,
                                    fan_min_percentage=1, fan_max_percentage=100)
        self.assertEqual(current.speed, 'Low')
        self.assertEqual(current.compensated_duty_percent, 100.)

    async def test_dry_compressor_retains_pwm_and_native_minimum_off_with_staged_fan(self):
        d = Driver(kp=1.)
        await d.at(0)
        r = d.r
        self.assertEqual(d.events[0][1:], ('set_hvac_mode', {'hvac_mode': 'dry'}))
        self.assertIn((0, 'set_fan_mode', {'fan_mode': 'Low'}), d.events)
        self.assertIsNotNone(r.status['pid_pwm_effective_cycle_seconds'])
        self.assertLess(r.status['demand_percent'], 10.)
        await d.at(126)
        self.assertEqual(d.events[-1][1:], ('set_hvac_mode', {'hvac_mode': 'off'}))
        confirmed_off = r.record['off_at'][r.primary]
        await d.at(245.999)
        self.assertEqual(r.state.state, 'off')
        self.assertEqual(r.record['off_at'][r.primary], confirmed_off)
        self.assertEqual(sum(service == 'set_hvac_mode' and data.get('hvac_mode') == 'dry'
                             for _, service, data in d.events), 1)

    async def test_quiet_correction_precedes_optional_humidity_target(self):
        d = Driver(humidity_target=True, quiet_occupied=True, kp=10.)
        await d.at(0)
        services = [(service, data) for _, service, data in d.events]
        self.assertEqual(services[:3], [
            ('set_hvac_mode', {'hvac_mode': 'dry'}),
            ('set_fan_mode', {'fan_mode': 'Low'}),
            ('set_humidity', {'humidity': 30.}),
        ])
        self.assertEqual(d.r.state.attributes['humidity'], 50)
        self.assertEqual(d.r.state.attributes['fan_mode'], 'Low')

    async def test_new_quiet_rule_yields_an_optional_target_before_its_retry_deadline(self):
        for method in ('pid', 'automatic'):
            with self.subTest(method=method):
                d = Driver(method=method, humidity_target=True, quiet_sleep=True,
                           preset='comfort')
                await d.at(0)
                r = d.r
                target = deepcopy(r.record['pending'])
                self.assertEqual(target['data'], {'humidity': 30.})
                self.assertEqual(target['attempts'], 1)
                physical = deepcopy((r.record['power'], r.record['off_at']))
                r.manager.plan['sleeping'] = True
                await d.at(1, acknowledge=False)
                self.assertEqual(r.record['pending']['service'], 'set_fan_mode')
                self.assertEqual(r.record['pending']['data'], {'fan_mode': 'Low'})
                self.assertEqual(sum(service == 'set_humidity' for _, service, _ in d.events), 1)
                self.assertEqual((r.record['power'], r.record['off_at']), physical)
                # Target retries cannot occupy the pending Low command's slot.
                await d.at(59.999, acknowledge=False)
                self.assertEqual(r.record['pending']['data'], {'fan_mode': 'Low'})
                r.feedback(fan='Low')
                await d.at(59.999)
                self.assertEqual(sum(service == 'set_humidity' for _, service, _ in d.events), 1)
                await d.at(60)
                self.assertEqual(r.record['pending']['data'], {'humidity': 30.})
                self.assertEqual(r.record['pending']['attempts'], 2)
                self.assertEqual(r.record['pending']['when'], target['when'])
                self.assertEqual(sum(service == 'set_humidity' for _, service, _ in d.events), 2)
                self.assertEqual(r.state.attributes['humidity'], 50)
                self.assertEqual(r.state.attributes['fan_mode'], 'Low')
                self.assertFalse(r.record.get('paused'))

    async def test_pending_high_retry_yields_to_quiet_and_keeps_late_feedback_evidence(self):
        r = FanRuntime(quiet_sleep=True)
        r.state.attributes['fan_mode'] = 'Medium'
        r.own_running(age=700)
        self.assertTrue(await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True))
        original = deepcopy(r.record['pending'])
        physical = deepcopy((r.record['power'], r.record['off_at']))
        r.manager.plan['sleeping'] = True
        await r.evaluate(60)
        self.assertIsNone(r.record['pending'])
        retained = r.record['unconfirmed_native_target']
        self.assertTrue(retained['superseded_for_quiet'])
        for key, value in original.items():
            self.assertEqual(retained[key], value)
        self.assertEqual((r.record['power'], r.record['off_at']), physical)
        await r.evaluate()
        self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})
        self.assertEqual(sum(c['data'] == {'fan_mode': 'High'} for c in r.calls), 1)
        # The obsolete High arrives after the Low request, then Low ACKs.
        r.feedback(fan='High')
        await r.evaluate(1)
        self.assertFalse(r.record.get('paused'))
        self.assertNotIn('unconfirmed_native_target', r.record)
        self.assertEqual(r.record['pending']['data'], {'fan_mode': 'Low'})
        r.feedback(fan='Low')
        await r.evaluate(1)
        self.assertIsNone(r.record['pending'])
        # A later real user High is no longer concealed as an old ACK.
        r.now += 1
        r.feedback(fan='High', human=True)
        await r.evaluate()
        self.assertEqual(r.record['paused'], 'physical_manual_override')
        self.assertEqual(sum(c['data'] == {'fan_mode': 'High'} for c in r.calls), 1)

    async def test_real_manual_change_matching_deferred_high_is_not_a_late_ack(self):
        for change in ('fan', 'mode'):
            with self.subTest(change=change):
                r = FanRuntime(quiet_sleep=True)
                r.state.attributes['fan_mode'] = 'Medium'
                r.own_running(age=700)
                await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True)
                r.manager.plan['sleeping'] = True
                await r.evaluate(60)
                self.assertIn('unconfirmed_native_target', r.record)
                r.now += 1
                r.feedback(fan='High' if change == 'fan' else None,
                           mode='heat' if change == 'mode' else None, human=True)
                await r.evaluate()
                self.assertEqual(r.record['paused'], 'physical_manual_override')
                self.assertEqual(len(r.calls), 1)

    async def test_late_high_after_low_ack_is_consumed_once_then_quiet_is_restored(self):
        r = FanRuntime(quiet_sleep=True)
        r.state.attributes['fan_mode'] = 'Medium'
        r.own_running(age=700)
        await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True)
        r.manager.plan['sleeping'] = True
        await r.evaluate(60)
        await r.evaluate()
        self.assertEqual(r.record['pending']['data'], {'fan_mode': 'Low'})
        r.feedback(fan='Low')
        await r.evaluate(1)
        self.assertIsNone(r.record['pending'])
        self.assertIn('unconfirmed_native_target', r.record)
        r.feedback(fan='High')
        await r.evaluate(1)
        self.assertFalse(r.record.get('paused'))
        self.assertNotIn('unconfirmed_native_target', r.record)
        self.assertEqual(r.record['pending']['data'], {'fan_mode': 'Low'})
        self.assertEqual(sum(c['data'] == {'fan_mode': 'High'} for c in r.calls), 1)
        r.feedback(fan='Low')
        await r.evaluate(1)
        r.now += 1
        r.feedback(fan='High', human=True)
        await r.evaluate()
        self.assertEqual(r.record['paused'], 'physical_manual_override')

    async def test_quiet_change_during_retry_persistence_does_not_dispatch_high(self):
        for yield_number in (1, 2):
            with self.subTest(yield_number=yield_number):
                r = FanRuntime(quiet_sleep=True)
                r.state.attributes['fan_mode'] = 'Medium'
                r.own_running(age=700)
                await r._fan(r.spec, r.cap, r.cfg, r.manager.plan, 90., True)
                original = deepcopy(r.record['pending'])
                save = r._save
                yields = 0
                async def saving():
                    nonlocal yields
                    await save()
                    if (r.record.get('pending') or {}).get('phase') == 'retry_intent':
                        yields += 1
                        if yields == yield_number:
                            r.manager.plan['sleeping'] = True
                r._save = saving
                await r.evaluate(60)
                self.assertGreaterEqual(yields, yield_number)
                self.assertIsNone(r.record['pending'])
                self.assertFalse(r.record.get('paused'))
                retained = r.record['unconfirmed_native_target']
                for key, value in original.items():
                    self.assertEqual(retained[key], value)
                self.assertEqual(len(r.calls), 1)
                await r.evaluate()
                self.assertEqual(r.calls[-1]['data'], {'fan_mode': 'Low'})

    async def test_quiet_never_retires_a_physical_power_ack_journal(self):
        r = FanRuntime(quiet_sleep=True)
        await r.evaluate()
        self.assertTrue(r.record['pending']['power'])
        original = deepcopy(r.record['pending'])
        r.manager.plan['sleeping'] = True
        await r.evaluate(60)
        self.assertTrue(r.record['pending']['power'])
        self.assertGreaterEqual(r.record['pending']['attempts'], original['attempts'])
        self.assertEqual(r.record['pending']['when'], original['when'])
        self.assertEqual(r.record['pending']['data'], {'hvac_mode': 'dry'})
        self.assertNotIn('unconfirmed_native_target', r.record)
        self.assertFalse(r.record['power'])
        self.assertFalse(any(call['service'] == 'set_fan_mode' for call in r.calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)
