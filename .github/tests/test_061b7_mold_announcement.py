"""Generic mold/window advice obeys the physical device's airing preference."""
from dataclasses import replace
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace as N
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(ROOT / '.github/tests/test_061b6_window_wait.py'))
Manager, SPEC, logic = b['Manager'], b['SPEC'], b['logic']


def mold_room(*, enabled=False, mixed=False):
    manager = Manager()
    manager.cfg['announce_before_start'] = enabled
    manager.set_state('climate.dry', 'off', {'friendly_name': 'Badezimmer Comfee'})
    manager.measurements['humidity'] = 55.8
    # The production calibrated mold model is covered by the mold demand gate.
    # Here its effective drying target enters the real demand/wait state machine.
    manager.targets['humidity'] = 48.8
    reasons = [logic.Reason('inside_mold', 'Mold indication', '80 %')]
    if mixed:
        reasons.append(logic.Reason('inside_co2', 'CO2', '1400 ppm'))
    recommendation = replace(manager.original.recommendations[0], area_name='Badezimmer', reasons=tuple(reasons))
    manager.original = replace(manager.original, recommendations=(recommendation,))
    manager._recalculate()
    return manager


class MoldAnnouncementPolicy(unittest.TestCase):
    def test_disabled_device_option_suppresses_general_mold_request_without_any_prior_episode(self):
        manager = mold_room()
        rec = manager.plan.recommendations[0]
        self.assertEqual(rec.wait_devices, ())
        self.assertIsNone(manager.gate())
        self.assertFalse(manager.window_open_wait.should_announce(rec))
        self.assertEqual(manager.window_open_wait.announcement_request(rec).reasons, ())
        self.assertFalse(manager.window_open_wait._rooms.get('room'))

    def test_other_window_reason_remains_but_covered_mold_cause_is_removed(self):
        manager = mold_room(mixed=True)
        rec = manager.plan.recommendations[0]
        self.assertTrue(manager.window_open_wait.should_announce(rec))
        rendered = manager.window_open_wait.announcement_request(rec)
        self.assertEqual([r.code for r in rendered.reasons], ['inside_co2'])
        self.assertEqual([r.code for r in rec.reasons], ['inside_mold', 'inside_co2'])
        self.assertEqual(rec.wait_seconds, 0)

    def test_no_wait_remedy_prevents_same_problem_sibling_request_and_wait(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed):
                manager = mold_room(mixed=mixed)
                sibling, cap = b['second_device'](manager, enabled=True)
                manager._recalculate()
                rec = manager.plan.recommendations[0]
                self.assertEqual(rec.wait_devices, ())
                self.assertEqual(rec.wait_seconds, 0)
                self.assertIsNone(manager.gate())
                self.assertIsNone(b['held'](manager, sibling, cap))
                self.assertFalse(manager.window_open_wait.status('room')['active'])
                self.assertIs(manager.window_open_wait.should_announce(rec), mixed)
                self.assertEqual([r.code for r in manager.window_open_wait.announcement_request(rec).reasons],
                                 ['inside_co2'] if mixed else [])

    def test_ready_no_wait_sibling_releases_live_hold_and_cannot_accept_an_old_wait(self):
        for already_accepted in (False, True):
            with self.subTest(already_accepted=already_accepted):
                manager = mold_room(enabled=True, mixed=True)
                sibling, cap = b['second_device'](manager, enabled=False)
                manager.set_state(cap.primary, 'unavailable')
                manager._recalculate()
                rec = manager.plan.recommendations[0]
                self.assertEqual(len(rec.wait_devices), 1)
                self.assertEqual(manager.gate(), 'window_request_pending')
                manager.window_open_wait.begin_submission(rec)
                if already_accepted:
                    self.assertTrue(manager.window_open_wait.submitted(rec))
                    self.assertEqual(manager.gate(), 'window_open_wait')
                manager.set_state(cap.primary, 'off')
                # Live dispatch and outbound filtering must not wait for the
                # next planner refresh to recognize the immediate remedy.
                self.assertIsNone(manager.gate())
                rendered = manager.window_open_wait.announcement_request(rec)
                self.assertEqual([r.code for r in rendered.reasons], ['inside_co2'])
                self.assertEqual(rendered.wait_devices, ())
                self.assertEqual(rendered.wait_seconds, 0)
                self.assertFalse(manager.window_open_wait.submitted(rec))
                manager._recalculate()
                self.assertFalse(manager.window_open_wait.status('room')['active'])
                self.assertIsNone(b['held'](manager, sibling, cap))

    def test_no_wait_dryer_preserves_unrelated_purifier_request_and_co2_reason(self):
        manager = mold_room(mixed=True)
        sibling, cap = b['second_device'](manager, enabled=True)
        cap = replace(cap, modes=('off', 'fan_only'), humidity=False)
        manager.capabilities[sibling.identifier] = cap
        manager.settings['equipment_controllers'][sibling.identifier]['requested_mode'] = 'fan_only'
        manager.measurements['pm25'] = 40
        manager.original.environment['room']['climate_plan']['air_actions'] = {
            'outdoor_air_verified': True,
            'thresholds': {'pm25_short_term_action_ug_m3': 25, 'co2_operational_ppm': 1000}}
        rec = replace(manager.original.recommendations[0], reasons=(
            *manager.original.recommendations[0].reasons,
            logic.Reason('inside_pm25', 'PM2.5', '40 µg/m³')))
        manager.original = replace(manager.original, recommendations=(rec,))
        activation = sys.modules[b['model'].__name__.rpartition('.')[0] + '.device_activation']
        with patch.object(activation, 'effective_device', return_value={
                'auto_control': True, 'fan_purpose': 'filtration', 'sensor_verified': True}):
            manager._recalculate()
            rec = manager.plan.recommendations[0]
            self.assertEqual([row['entity_id'] for row in rec.wait_devices], [cap.primary])
            self.assertIsNone(manager.gate())
            self.assertTrue(manager.window_open_wait.should_announce(rec))
            rendered = manager.window_open_wait.announcement_request(rec)
            self.assertEqual([r.code for r in rendered.reasons], ['inside_co2', 'inside_pm25'])
            self.assertEqual([row['entity_id'] for row in rendered.wait_devices], [cap.primary])
            self.assertEqual(rendered.wait_seconds, 600)

    def test_enabled_mold_request_names_device_and_binds_accepted_timeout(self):
        manager = mold_room(enabled=True)
        rec = manager.plan.recommendations[0]
        self.assertTrue(manager.window_open_wait.should_announce(rec))
        self.assertEqual(rec.wait_devices[0]['friendly_name'], 'Badezimmer Comfee')
        self.assertEqual(rec.wait_devices[0]['timeout_seconds'], 300)
        self.assertEqual(manager.gate(), 'window_request_pending')
        manager.window_open_wait.begin_submission(rec)
        self.assertTrue(manager.window_open_wait.submitted(rec))
        self.assertEqual(manager.gate(), 'window_open_wait')
        manager.advance(300)
        self.assertIsNone(manager.gate())
        self.assertFalse(manager.window_open_wait.should_announce(manager.plan.recommendations[0]))

    def test_unavailable_unauthorized_or_paused_device_does_not_hide_needed_airing(self):
        for problem in ('unavailable', 'unauthorized', 'paused'):
            with self.subTest(problem=problem):
                manager = mold_room()
                if problem == 'unavailable':
                    manager.set_state('climate.dry', 'unavailable')
                elif problem == 'unauthorized':
                    manager.authorized = False
                else:
                    manager.equipment.records[SPEC.identifier]['paused'] = 'physical_manual_override'
                manager._recalculate()
                rec = manager.plan.recommendations[0]
                self.assertTrue(manager.window_open_wait.should_announce(rec))
                self.assertEqual(rec.wait_devices, (), 'Never promise an unavailable device will start')
                self.assertEqual(manager.window_open_wait.announcement_request(rec).reasons, rec.reasons)

    def test_closing_advice_and_unrelated_problem_are_unchanged(self):
        manager = mold_room()
        rec = manager.plan.recommendations[0]
        closed = replace(rec, action='close')
        self.assertIs(manager.window_open_wait.announcement_request(closed), closed)
        self.assertTrue(manager.window_open_wait.should_announce(closed))
        unrelated = replace(rec, reasons=(logic.Reason('inside_voc', 'VOC', '900 ppb'),))
        self.assertIs(manager.window_open_wait.announcement_request(unrelated), unrelated)
        self.assertTrue(manager.window_open_wait.should_announce(unrelated))

    def test_unavailable_device_with_wrong_room_supply_cannot_hide_mold(self):
        manager = mold_room()
        manager.cfg['power_switch_entity'] = 'switch.supply'
        manager.set_state('climate.dry', 'unavailable')
        manager.set_state('switch.supply', 'off')
        manager.hass.areas['switch.supply'] = 'another_room'
        manager._recalculate()
        rec = manager.plan.recommendations[0]
        self.assertTrue(manager.window_open_wait.should_announce(rec))
        self.assertEqual(manager.window_open_wait.announcement_request(rec).reasons, rec.reasons)

    def test_missing_secondary_native_endpoint_cannot_hide_mold(self):
        for value in (None, 'unknown', 'unavailable'):
            with self.subTest(value=value):
                manager = mold_room()
                spec = N(**{**vars(SPEC), 'source_entities': ('climate.dry', 'fan.dry')})
                manager.specs = (spec,)
                manager.equipment.records[spec.identifier]['sources'] = list(spec.source_entities)
                if value is not None:
                    manager.set_state('fan.dry', value)
                manager._recalculate()
                rec = manager.plan.recommendations[0]
                self.assertTrue(manager.window_open_wait.should_announce(rec))
                self.assertEqual(manager.window_open_wait.announcement_request(rec).reasons, rec.reasons)
                self.assertEqual(rec.wait_devices, ())

    def test_mold_inhibited_humidifier_cannot_cover_low_humidity_advice(self):
        manager = mold_room()
        spec = N(**{**vars(SPEC), 'source_entities': ('humidifier.room',)})
        manager.specs = (spec,)
        manager.capabilities[spec.identifier] = replace(b['Cap'](), primary='humidifier.room',
            domain='humidifier', modes=('off', 'auto'), humidifying=True)
        manager.equipment.records[spec.identifier]['sources'] = list(spec.source_entities)
        manager.set_state('humidifier.room', 'off')
        manager.cfg['requested_mode'] = 'auto'
        # A native minimum can keep the effective target above current RH
        # despite the calibrated surface model requiring even lower RH.
        manager.measurements['humidity'] = 35
        manager.targets['humidity'] = 40
        rec = replace(manager.original.recommendations[0], reasons=(
            logic.Reason('inside_low_humidity', 'RH', '35 %'),))
        manager.original = replace(manager.original, recommendations=(rec,))
        with patch.object(b['model'], 'humidity_demand', create=True,
                          return_value={'mold_protection_required': True}):
            manager._recalculate()
            current = manager.plan.recommendations[0]
            self.assertEqual(current.wait_devices, ())
            self.assertTrue(manager.window_open_wait.should_announce(current))
            self.assertEqual(manager.window_open_wait.announcement_request(current).reasons,
                             current.reasons)


class MoldAIDelivery(unittest.IsolatedAsyncioTestCase):
    async def test_ready_remedy_with_option_off_sends_nothing_to_direct_or_hub(self):
        delivery = runpy.run_path(str(ROOT / '.github/tests/test_061b5_announcement_delivery.py'))
        for use_hub in (False, True):
            for ai_enabled in (False, True):
                with self.subTest(use_hub=use_hub, ai_enabled=ai_enabled):
                    source = mold_room()
                    manager = delivery['fixture']('en')
                    manager.settings.update({delivery['const'].CONF_HUB: use_hub,
                                             'ai_rewrite': ai_enabled})
                    manager.hass.hub_installed = use_hub
                    manager.plan = source.plan
                    manager.window_open_wait = source.window_open_wait
                    result = await manager.async_announce(channels='auto')
                    self.assertEqual(result, {'submitted': 0, 'errors': []})
                    self.assertEqual(manager.hass.services.calls, [])
                    self.assertEqual(manager.hass.rewrites, [])
                    self.assertIsNone(source.gate())
                    self.assertFalse(source.window_open_wait.status('room')['active'])

    async def test_unrelated_co2_reaches_direct_and_hub_without_covered_mold_or_device_wait(self):
        delivery = runpy.run_path(str(ROOT / '.github/tests/test_061b5_announcement_delivery.py'))
        for use_hub in (False, True):
            for ai_enabled in (False, True):
                with self.subTest(use_hub=use_hub, ai_enabled=ai_enabled):
                    source = mold_room(mixed=True)
                    manager = delivery['fixture']('en')
                    manager.settings.update({delivery['const'].CONF_HUB: use_hub,
                                             'ai_rewrite': ai_enabled})
                    manager.hass.hub_installed = use_hub
                    manager.plan = source.plan
                    manager.window_open_wait = source.window_open_wait
                    result = await manager.async_announce(channels='auto')
                    self.assertGreater(result['submitted'], 0)
                    for call in manager.hass.services.calls:
                        content = call.data.get('text', call.data.get('message', ''))
                        self.assertIn('1400 ppm', content)
                        self.assertNotIn('80 %', content)
                        self.assertNotIn('Badezimmer Comfee', content)
                        self.assertNotIn('will start', content)
                        if use_hub:
                            self.assertEqual((call.domain, call.service), ('notify', 'announcement_hub'))
                            self.assertIs(call.data['use_ai'], ai_enabled)
                    self.assertIsNone(source.gate())
                    self.assertFalse(source.window_open_wait.status('room')['active'])
                    self.assertEqual([r.code for r in source.plan.recommendations[0].reasons],
                                     ['inside_mold', 'inside_co2'])

    async def test_filtered_opening_reasons_reach_the_local_ai_prompt(self):
        # Execute the real manager delivery method with simulated HA channels.
        delivery = runpy.run_path(str(ROOT / '.github/tests/test_061b5_announcement_delivery.py'))
        source = mold_room(mixed=True)
        manager = delivery['fixture']('en')
        manager.settings['ai_rewrite'] = True
        manager.plan = source.plan
        manager.window_open_wait = source.window_open_wait
        seen = []
        async def rewrite(hass, rec, message, language, agent):
            seen.append(([r.code for r in rec.reasons], message))
            return message
        with patch.dict(delivery['scope'], {'async_rewrite_announcement': rewrite}):
            result = await manager.async_announce(channels='auto')
        self.assertGreater(result['submitted'], 0)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], ['inside_co2'])
        self.assertNotIn('80 %', seen[0][1])
        self.assertIn('1400 ppm', seen[0][1])

if __name__ == '__main__':
    unittest.main(verbosity=2)
