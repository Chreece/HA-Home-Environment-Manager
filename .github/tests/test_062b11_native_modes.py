"""Production Home/Room native freshness selectors persist without hardware commands."""
from __future__ import annotations
import asyncio
from pathlib import Path
import runpy
import unittest

BASE = Path(__file__).resolve().parents[2]
fix = runpy.run_path(str(BASE / '.github/tests/test_bugfix_native_settings.py'))
Fixture = fix['Fixture']
AREA = fix['AREA']

class ModePersistence(unittest.IsolatedAsyncioTestCase):
    async def test_automatic_defaults_and_custom_writes_for_all_three_scopes(self):
        case = Fixture(online=False, room={'enabled': False, 'allow_actuation': False})
        await case.setup()
        selectors = {
            'env': case.added['select']['entry_home_global_threshold_mode_max_age_mode'],
            'home': case.added['select']['entry_home_global_policy_source_freshness_mode'],
            'room': case.get('select', 'climate_policy_occupancy_freshness_mode'),
        }
        original = fix['copy_config'](case.settings)
        for key, entity in selectors.items():
            with self.subTest(key=key):
                self.assertEqual(entity.current_option, 'auto')
                self.assertEqual(entity._attr_options, ['auto', 'custom'])
        self.assertEqual(fix['copy_config'](case.settings), original)
        self.assertFalse(case.saved)
        for key, entity in selectors.items():
            with self.subTest(write=key):
                await entity.async_select_option('custom')
                self.assertEqual(entity.current_option, 'custom')
        self.assertEqual(case.settings['thresholds']['max_age_mode'], 'custom')
        self.assertEqual(case.settings['occupancy_global']['source_freshness_mode'], 'custom')
        self.assertEqual(case.room['occupancy_freshness_mode'], 'custom')
        self.assertFalse(case.room['allow_actuation'])
        self.assertFalse(case.room['enabled'])
        self.assertEqual(case.settings['climate_rooms']['other'], {'keep': 'room'})
        self.assertFalse(fix['activation'].authorized(case, case.spec))
        # A reload must restore all three selections without configuration migration.
        again = Fixture(online=False, room={'enabled': False}, options=fix['copy_config'](case.entry.options))
        await again.setup()
        self.assertEqual(again.added['select']['entry_home_global_threshold_mode_max_age_mode'].current_option, 'custom')
        self.assertEqual(again.added['select']['entry_home_global_policy_source_freshness_mode'].current_option, 'custom')
        self.assertEqual(again.get('select', 'climate_policy_occupancy_freshness_mode').current_option, 'custom')
        for key, entity in selectors.items():
            with self.subTest(reject=key), self.assertRaises(ValueError):
                await entity.async_select_option('unlimited')

if __name__=='__main__':
    unittest.main(verbosity=2)
