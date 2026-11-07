"""Physical endpoint consent survives mutable room evidence, never replacement."""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'hem_061b6_authorization'
package = ModuleType(PACKAGE)
package.__path__ = []
sys.modules[PACKAGE] = package
model = ModuleType(PACKAGE + '.equipment_model')
model.settings = lambda manager, spec: manager.profile
sys.modules[model.__name__] = model
helpers = sys.modules.setdefault('homeassistant.helpers', ModuleType('homeassistant.helpers'))
registry = ModuleType('homeassistant.helpers.entity_registry')
registry.async_get = lambda hass: hass.registry
helpers.entity_registry = registry
sys.modules[registry.__name__] = registry
scope = {'__package__': PACKAGE, 'mutable_copy': deepcopy}
names = {'authority_context', 'authorization_matches', 'authorized'}
nodes = [node for node in ast.parse((ROOT / 'device_activation.py').read_text()).body
         if isinstance(node, ast.FunctionDef) and node.name in names]
exec(compile(ast.Module(nodes, []), 'device_activation.py', 'exec'), scope)
activation = ModuleType(PACKAGE + '.device_activation')
activation.__dict__.update({name: scope[name] for name in names})
sys.modules[activation.__name__] = activation
permission_scope = {
    '__package__': PACKAGE, 'settings': model.settings,
    'room_config': lambda manager, spec: manager.settings.get('climate_rooms', {}).get(spec.area_id, {}),
    'device_config': lambda manager, spec, entity: {},
}
permission_node = next(node for node in ast.parse((ROOT / 'equipment_model.py').read_text()).body
                       if isinstance(node, ast.FunctionDef) and node.name == 'permission')
exec(compile(ast.Module([permission_node], []), 'equipment_model.py', 'exec'), permission_scope)
retry_scope = {'__package__': PACKAGE, 'OPTION': 'timed_setpoint_sequence'}
retry_node = next(node for node in ast.parse((ROOT / 'equipment_setpoint_sequence.py').read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name == 'retry_settings_match')
exec(compile(ast.Module([retry_node], []), 'equipment_setpoint_sequence.py', 'exec'), retry_scope)


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.rows = {
            'climate.native': N(id='registry-1', unique_id='device-native-1'),
            'fan.native': N(id='registry-2', unique_id='device-fan-1'),
        }
        self.spec = N(area_id='bedroom', source_device_id='physical-1',
                      source_entities=('climate.native', 'fan.native'))
        self.manager = N(profile={}, settings={}, hass=N(registry=N(async_get=self.rows.get)))
        self.original = scope['authority_context'](self.manager, self.spec)
        self.manager.profile['_native_authorization'] = deepcopy(self.original)

    def test_same_selected_device_survives_room_sources_and_order(self):
        self.manager.settings.update(
            room_sources={'bedroom': {'temperature': ['sensor.new', 'sensor.old']}},
            climate_rooms={'bedroom': {'source_revision': 8}},
        )
        self.spec.source_entities = tuple(reversed(self.spec.source_entities))
        self.assertTrue(scope['authorized'](self.manager, self.spec))
        self.assertEqual(scope['authority_context'](self.manager, self.spec), self.original)

    def test_legacy_grant_migrates_only_same_hardware(self):
        saved = deepcopy(self.original)
        saved.pop('version')
        saved.update(inputs={'humidity': ['sensor.old']}, source_revision=1,
                     excluded=['sensor.retired'], pins={'climate.native': {'selection_generation': 3}})
        saved['sources'].reverse()
        self.manager.profile['_native_authorization'] = saved
        self.assertTrue(scope['authorized'](self.manager, self.spec))
        self.rows['climate.native'] = N(id='registry-1', unique_id='replacement-device')
        self.assertFalse(scope['authorized'](self.manager, self.spec))

    def test_missing_registry_identity_holds_until_same_identity_returns(self):
        source = self.rows.pop('climate.native')
        self.assertFalse(scope['authorized'](self.manager, self.spec))
        self.assertEqual(self.manager.profile['_native_authorization'], self.original)
        self.rows['climate.native'] = source
        self.assertTrue(scope['authorized'](self.manager, self.spec))

    def test_moved_added_removed_and_replaced_hardware_require_new_selection(self):
        for key, value in (('area_id', 'office'), ('source_device_id', 'physical-2'),
                           ('source_entities', ('climate.native',)),
                           ('source_entities', ('climate.native', 'fan.native', 'fan.other'))):
            with self.subTest(key=key, value=value):
                changed = N(**{**vars(self.spec), key: value})
                self.assertFalse(scope['authorized'](self.manager, changed))
        self.rows['fan.native'] = N(id='recreated-registry-row', unique_id='device-fan-1')
        self.assertFalse(scope['authorized'](self.manager, self.spec))

    def test_visible_method_without_saved_grant_never_confers_consent(self):
        self.manager.profile = {'control_mode': 'pid'}
        self.assertFalse(scope['authorized'](self.manager, self.spec))
        malformed = {'area': 'bedroom', 'physical_device': 'physical-1',
                     'sources': [['climate.native', None, None]]}
        self.assertFalse(scope['authorization_matches'](malformed, malformed))

    def test_pid_permission_consumer_accepts_sensor_change_but_rejects_replaced_device(self):
        cap = N(domain='climate', primary='climate.native', modes=('off', 'heat'))
        saved = deepcopy(self.original)
        saved.pop('version')
        saved.update(inputs={'temperature': ['sensor.before']}, source_revision=1)
        self.manager.profile.update(control_mode='pid', _native_authorization=saved)
        self.manager.settings.update(
            room_sources={'bedroom': {'temperature': ['sensor.after'], 'humidity': ['sensor.room']}},
            climate_rooms={'bedroom': {'source_revision': 9}},
        )
        self.assertEqual(permission_scope['permission'](self.manager, self.spec, cap), (True, True))
        self.assertEqual(self.manager.profile['control_mode'], 'pid')
        self.rows['climate.native'] = N(id='new-registry-row', unique_id='new-native-device')
        self.assertEqual(permission_scope['permission'](self.manager, self.spec, cap), (False, False))
        self.assertEqual(self.manager.profile['control_mode'], 'pid', 'A hold does not alter the saved choice')

    def test_pending_command_accepts_only_same_physical_grant_migration(self):
        legacy = deepcopy(self.original)
        legacy.pop('version')
        legacy.update(inputs={'temperature': ['sensor.old']}, source_revision=3)
        legacy['sources'].reverse()
        saved = {'control_mode': 'pid', 'requested_mode': 'heat', '_native_authorization': legacy}
        current = {**saved, '_native_authorization': deepcopy(self.original)}
        compare = retry_scope['retry_settings_match']
        self.assertTrue(compare(saved, current))
        self.assertFalse(compare(saved, {**current, 'requested_mode': 'cool'}))
        self.assertFalse(compare(saved, {**current, 'control_mode': 'manual'}))
        current['_native_authorization']['sources'][0][2] = 'replacement-device'
        self.assertFalse(compare(saved, current))


if __name__ == '__main__':
    unittest.main(verbosity=2)
