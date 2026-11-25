"""Actual native mode entities: metadata, bounds and exact scoped writes.

Only HA transport/base classes are replaced. The production model, entity
mixin, getters, setters and capability-derived field builders run unchanged.
Runtime persistence/actuation is exercised by the companion runtime gate.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from dataclasses import asdict
import importlib
from pathlib import Path
import runpy
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
b = runpy.run_path(str(ROOT / '.github/tests/test_beta110_device_setting.py'))
model, switch = b['model'], b['platform']
helper = importlib.import_module(b['PKG'] + '.equipment_mode_entities')
catalog = importlib.import_module(b['PKG'] + '.operating_mode_catalog')
class Entity:
    available = True
ns = {'__name__': b['PKG'] + '.scoped_entities', '__package__': b['PKG'],
      'EquipmentEntity': switch.EquipmentEntity, 'SelectEntity': Entity,
      'NumberEntity': Entity, 'ButtonEntity': Entity, 'equipment': model,
      'NumberMode': N(BOX='box'), 'EntityCategory': N(CONFIG='config'),
      'callback': lambda fn: fn}
for filename, names in {
    'select.py': {'EquipmentSelect'},
    'number.py': {'EquipmentNumber', '_equipment_numbers', '_registered_number'},
    'button.py': {'EquipmentCalibrationButton', 'EquipmentFanCapacityButton', 'EquipmentPIDReviewButton'},
}.items():
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    exec(compile(ast.Module(nodes, []), filename, 'exec'), ns)

# Execute the actual facade properties and target writer; only unrelated HA
# platform construction is omitted. Physical readings stay on the appliance.
climate = next(node for node in ast.parse((ROOT / 'climate.py').read_text()).body
               if isinstance(node, ast.ClassDef) and node.name == 'ManagedClimate')
facade_names = {'current_humidity', '_target', 'min_humidity', 'max_humidity',
                'async_set_humidity'}
facade = ast.ClassDef(name='HumidityFacade', bases=[ast.Name(id='EquipmentEntity', ctx=ast.Load())],
    keywords=[], decorator_list=[], body=[node for node in climate.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in facade_names
        or isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == 'target_humidity' for target in node.targets)])
ns.update(model=model, finite=model.finite, HomeAssistantError=ValueError)
exec(compile(ast.fix_missing_locations(ast.Module([facade], [])), 'climate.py', 'exec'), ns)
runtime = next(node for node in ast.parse((ROOT / 'equipment_runtime.py').read_text()).body
               if isinstance(node, ast.ClassDef) and node.name == 'EquipmentRuntime')
setter = next(node for node in runtime.body
              if isinstance(node, ast.AsyncFunctionDef) and node.name == 'async_set_targets')
setter_ns = {**ns, 'deepcopy': deepcopy}
exec(compile(ast.Module([setter], []), 'equipment_runtime.py', 'exec'), setter_ns)

class ModeEntities(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.f = b['SettingTests'](); self.f.setUp()
        self.m, self.spec = self.f.manager, self.f.a
        self.m.hass.registry.async_get = lambda entity: N(id='registry-' + entity, unique_id='native-' + entity)
        self.f.states['climate.a'].attributes.update(
            hvac_modes=['off', 'heat', 'cool', 'dry', 'fan_only', 'auto', 'heat_cool'],
            supported_features=model.TEMP | model.FAN | model.SWING,
            fan_modes=['low', 'medium', 'high'], swing_modes=['off', 'vertical'],
            min_temp=7, max_temp=32, min_humidity=30, max_humidity=75)
        self.m.entry.options[model.SETTINGS][self.spec.identifier] = {
            'control_mode': 'pid', 'kp': 9, 'mode_settings_version': 1,
            'mode_settings': {'heat': {'control_mode': 'pid', 'kp': 12},
                              'cool': {'control_mode': 'manual', 'kp': 22}}}
        self.m.equipment.active_control_mode = lambda spec: 'heat'
        self.m.equipment.clock = lambda: 100000.
        self.writes, self.actions = [], []
        async def write(spec, changes, *, operating_mode=None):
            self.writes.append((spec.identifier, deepcopy(changes), operating_mode))
            raw = self.m.entry.options[model.SETTINGS][spec.identifier]
            self.m.entry.options[model.SETTINGS][spec.identifier] = model.persist_changes(
                raw, changes, operating_mode=operating_mode)
        self.m.equipment.async_update = write
        async def apply(spec, *, operating_mode=None):
            self.actions.append((spec.identifier, operating_mode))
        self.m.equipment.async_apply_pid_calibration = apply
        self.m.equipment.async_apply_fan_capacity = apply

    def entity(self, platform, key, mode):
        return ns['Equipment' + platform](self.m, self.spec, key, operating_mode=mode)

    async def test_separate_methods_gains_and_physical_registration(self):
        heat = self.entity('Select', 'control_mode', 'heat')
        cool = self.entity('Select', 'control_mode', 'cool')
        self.assertEqual((heat.current_option, cool.current_option), ('pid', 'manual'))
        self.assertNotEqual(heat._attr_unique_id, cool._attr_unique_id)
        self.assertEqual(heat._attr_device_info, cool._attr_device_info)
        self.assertEqual(heat._attr_device_info['identifiers'], {('environment_manager', self.spec.identifier)})
        await cool.async_select_option('automatic')
        gain = self.entity('Number', 'kp', 'cool')
        await gain.async_set_native_value(17)
        self.assertEqual(self.entity('Number', 'kp', 'heat').native_value, 12)
        self.assertEqual(gain.native_value, 17)
        self.assertEqual(model.settings(self.m, self.spec)['kp'], 12)
        self.assertEqual([r[2] for r in self.writes], ['cool', 'cool'])
        attrs = cool.extra_state_attributes
        self.assertEqual((attrs['operating_mode'], attrs['settings_scope'], attrs['setting_key']),
                         ('cool', 'operating_mode', 'control_mode'))
        self.assertEqual(attrs['controller_id'], self.spec.identifier)
        self.assertEqual(attrs['source_entity_ids'], ['climate.a'])
        self.assertTrue(attrs['operating_mode_label'] and attrs['setting_label'])
        self.assertIn('pid', attrs['option_labels'])

    async def test_profile_targets_are_mode_local_and_within_native_bounds(self):
        heat = self.entity('Number', 'target_home_heat', 'heat')
        dry = self.entity('Number', 'target_home_humidity', 'dry')
        self.assertEqual((heat._attr_native_min_value, heat._attr_native_max_value), (7, 32))
        self.assertEqual((dry._attr_native_min_value, dry._attr_native_max_value), (30, 75))
        await heat.async_set_native_value(23)
        await dry.async_set_native_value(51)
        self.assertEqual(heat.native_value, 23)
        self.assertEqual(dry.native_value, 51)
        self.assertNotIn('humidity', model.settings_for_mode(self.m, self.spec, 'heat')['profile_targets']['home'])
        self.assertEqual([r[2] for r in self.writes], ['heat', 'dry'])

    async def test_mold_profile_editors_keep_surface_targets_and_independent_profiles(self):
        self.m.entry.data.update(areas=['room'], use_mold_indicator=True)
        raw = self.m.entry.options[model.SETTINGS][self.spec.identifier]
        values = {'home': 88., 'comfort': 60., 'eco': 92., 'sleep': 55., 'away': 85.}
        raw['mode_settings']['dry'] = {'control_mode': 'automatic',
            'profile_targets': {profile: {'humidity': target} for profile, target in values.items()}}
        before_heat = deepcopy(raw['mode_settings']['heat'])
        editors = {profile: self.entity('Number', f'target_{profile}_humidity', 'dry')
                   for profile in values}
        for profile, editor in editors.items():
            with self.subTest(profile=profile):
                self.assertEqual(editor.native_value, values[profile])
                self.assertEqual((editor._attr_native_min_value, editor._attr_native_max_value), (1., 100.))
                self.assertEqual(editor.extra_state_attributes['target_basis'], 'mold_surface_rh')
                self.assertEqual(editor.extra_state_attributes['target_metric'], 'mold')
        await editors['eco'].async_set_native_value(90.)
        self.assertEqual(editors['eco'].native_value, 90.)
        for profile in values.keys() - {'eco'}:
            self.assertEqual(editors[profile].native_value, values[profile])
        self.assertEqual(self.m.entry.options[model.SETTINGS][self.spec.identifier]['mode_settings']['heat'], before_heat)
        manual = self.entity('Number', 'target_manual_humidity', 'dry')
        self.assertEqual((manual._attr_native_min_value, manual._attr_native_max_value), (30, 75))
        self.assertEqual(manual.extra_state_attributes['target_basis'], 'room_relative_humidity')

    def test_mold_editor_basis_tracks_enablement_and_control_method_without_calibration(self):
        self.m.entry.data.update(areas=['room'], use_mold_indicator=True)
        raw = self.m.entry.options[model.SETTINGS][self.spec.identifier]
        raw['mode_settings']['dry'] = {'control_mode': 'pid',
            'profile_targets': {'home': {'humidity': 88.}}}
        editor = self.entity('Number', 'target_home_humidity', 'dry')
        self.assertEqual(editor.native_value, 88., 'A target remains editable while calibration is unavailable')
        for changes, method, expected in (
            ({'use_mold_indicator': False}, 'pid', (30, 75)),
            ({'use_mold_indicator': True, 'areas': ['other']}, 'pid', (30, 75)),
            ({'areas': ['room']}, 'manual', (30, 75)),
            ({}, 'existing', (30, 75)),
            ({}, 'automatic', (1., 100.)),
        ):
            with self.subTest(changes=changes, method=method):
                self.m.entry.data.update(changes)
                raw['mode_settings']['dry']['control_mode'] = method
                editor._sync_mode_target_bounds()
                self.assertEqual((editor._attr_native_min_value, editor._attr_native_max_value), expected)
                self.assertEqual(editor.extra_state_attributes['target_basis'],
                                 'mold_surface_rh' if expected == (1., 100.) else 'room_relative_humidity')

    async def test_facade_profile_target_roundtrip_uses_the_declared_measurement_basis(self):
        self.m.entry.data.update(areas=['room'], use_mold_indicator=True)
        raw = self.m.entry.options[model.SETTINGS][self.spec.identifier]
        values = {'home': 65., 'comfort': 60., 'eco': 90., 'sleep': 55., 'away': 85.}
        raw['mode_settings']['dry'] = {'control_mode': 'pid', 'preset': 'none',
            'profile_targets': {profile: {'humidity': target} for profile, target in values.items()}}
        self.m.equipment.active_control_mode = lambda spec: 'dry'
        self.m.equipment.measurements = lambda *args: {'humidity': 49.4}
        self.m.equipment.async_set_targets = lambda spec, target: setter_ns['async_set_targets'](
            self.m.equipment, spec, target)
        view = ns['HumidityFacade']()
        view._equipment_init(self.m, self.spec, 'climate')
        view._caps = model.capabilities(self.m, self.spec)
        view._state = self.f.states['climate.a']
        view._state.attributes.update(current_humidity=47., humidity=50.)
        physical = deepcopy(view._state.attributes)
        live = {'away': 'home', 'occupancy': 'occupied', 'sleeping': False}
        ready = True

        def evidence(manager, spec, cap, config, requested, limits):
            mold = model.uses_mold_target(manager, spec, cap, config)
            return {'target_basis': 'mold_surface_rh' if mold else 'room_relative_humidity',
                'control_target': requested, 'control_measurement': 64.4 if mold else 49.4,
                'target_ready': ready if mold else True,
                'effective_humidity_target': 46. if mold and ready else None if mold else requested}

        with patch.object(model, 'plan_for', side_effect=lambda *args: live), \
             patch.object(model, '_humidity_demand', side_effect=evidence):
            for plan, expected in (
                ({'away': 'home', 'occupancy': 'occupied', 'sleeping': False}, 'comfort'),
                ({'away': 'home', 'occupancy': 'unoccupied', 'sleeping': False}, 'home'),
                ({'away': 'home', 'occupancy': 'unoccupied', 'sleeping': False, 'door_eco_active': True}, 'eco'),
                ({'away': 'home', 'occupancy': 'occupied', 'sleeping': True}, 'sleep'),
                ({'away': 'away', 'occupancy': 'unoccupied', 'sleeping': False}, 'away'),
            ):
                with self.subTest(profile=expected):
                    live.clear(); live.update(plan)
                    self.assertEqual(view.target_humidity, values[expected])
                    self.assertEqual(view.current_humidity, 64.4)
                    self.assertEqual((view.min_humidity, view.max_humidity), (1., 100.))
            live.clear(); live.update(away='home', occupancy='unoccupied', sleeping=False, door_eco_active=True)
            await view.async_set_humidity(95.)
            self.assertEqual(view.target_humidity, 95.)
            saved = self.m.entry.options[model.SETTINGS][self.spec.identifier]['mode_settings']['dry']['profile_targets']
            self.assertEqual(saved['eco']['humidity'], 95.)
            self.assertEqual(saved['comfort']['humidity'], 60.)
            ready = False
            self.assertIsNone(view.current_humidity)
            self.assertEqual(view.target_humidity, 95.)
            self.m.entry.data['use_mold_indicator'] = False
            self.assertEqual(view.current_humidity, 49.4)
            self.assertEqual((view.min_humidity, view.max_humidity), (30, 75))
            self.assertEqual(view.target_humidity, 75.)
        self.assertEqual(view._state.attributes, physical, 'The physical appliance keeps its own RH readings and target')

    async def test_native_choices_switches_and_calibration_route_to_own_mode(self):
        quiet = switch.EquipmentQuietSwitch(self.m, self.spec, 'quiet_sleep', operating_mode='cool')
        await quiet.async_turn_on()
        self.assertTrue(quiet.is_on)
        self.assertFalse(model.settings_for_mode(self.m, self.spec, 'heat')['quiet_sleep'])
        fan = self.entity('Select', 'fan_mode', 'cool')
        self.assertEqual(fan.options, ['low', 'medium', 'high'])
        await fan.async_select_option('medium')
        self.assertEqual(fan.current_option, 'medium')
        for cls in ('EquipmentCalibrationButton', 'EquipmentFanCapacityButton'):
            await ns[cls](self.m, self.spec, operating_mode='dry').async_press()
        self.assertEqual(self.actions, [(self.spec.identifier, 'dry')] * 2)
        self.assertEqual([r[2] for r in self.writes], ['cool', 'cool'])

    def test_actual_capabilities_drive_mode_fields_without_duplicate_ids(self):
        selectors = list(helper.scoped_fields(self.m, self.spec, 'select'))
        self.assertEqual(sum(key == 'control_mode' for mode, key in selectors), 6)
        self.assertNotIn('pid', self.entity('Select', 'control_mode', 'auto').options)
        self.assertIn('pid', self.entity('Select', 'control_mode', 'fan_only').options)
        self.assertIn('pid', self.entity('Select', 'control_mode', 'dry').options)
        ids = []
        for platform, cls in (('select', 'Select'), ('number', 'Number')):
            for mode, key in helper.scoped_fields(self.m, self.spec, platform):
                entity = self.entity(cls, key, mode)
                ids.append(entity._attr_unique_id)
                self.assertNotIn('min_on_seconds', key)
                self.assertNotIn('min_off_seconds', key)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(('dry', 'target_home_heat'), list(helper.scoped_fields(self.m, self.spec, 'number')))

    def test_offline_configuration_survives_only_exact_verified_sources(self):
        cap = model.capabilities(self.m, self.spec)
        self.m.equipment.records[self.spec.identifier] = {
            'area': self.spec.area_id, 'source_device_id': self.spec.source_device_id,
            'sources': list(self.spec.source_entities), 'capabilities': asdict(cap),
            'capabilities_authority': importlib.import_module(b['PKG'] + '.device_activation').authority_context(self.m, self.spec)}
        self.f.states.pop('climate.a')
        method = self.entity('Select', 'control_mode', 'cool')
        gain = self.entity('Number', 'kp', 'cool')
        self.assertTrue(method.available)
        self.assertTrue(gain.available)
        self.assertEqual(gain.native_value, 22)
        self.m.equipment.records[self.spec.identifier]['source_device_id'] = 'replacement'
        self.assertFalse(method.available)
        self.assertFalse(gain.available)
        self.assertIsNone(method.current_option)
        self.assertIsNone(gain.native_value)
        self.assertEqual(method.extra_state_attributes['operating_mode'], 'cool')
        self.assertEqual(gain.extra_state_attributes['operating_mode'], 'cool')

    def test_withdrawn_mode_serializes_unavailable_properties_without_crashing(self):
        self.m.entry.options[model.SETTINGS][self.spec.identifier]['mode_settings']['cool'].update(
            control_mode='pid', pid_calibration_method='imc_lambda')
        entities = [self.entity('Select', 'control_mode', 'cool'),
                    self.entity('Number', 'kp', 'cool'),
                    self.entity('Number', 'target_home_cool', 'cool'),
                    ns['EquipmentCalibrationButton'](self.m, self.spec, operating_mode='cool'),
                    ns['EquipmentFanCapacityButton'](self.m, self.spec, operating_mode='cool'),
                    ns['EquipmentPIDReviewButton'](self.m, self.spec, 'approve', operating_mode='cool'),
                    switch.EquipmentQuietSwitch(self.m, self.spec, 'quiet_sleep', operating_mode='cool')]
        self.f.states['climate.a'].attributes['hvac_modes'] = ['off', 'heat']
        for entity in entities:
            with self.subTest(entity=entity._attr_unique_id):
                self.assertFalse(entity.available)
                self.assertEqual(entity.extra_state_attributes['operating_mode'], 'cool')
                if hasattr(type(entity), 'current_option'):
                    self.assertIsNone(entity.current_option)
                if hasattr(type(entity), 'native_value'):
                    self.assertIsNone(entity.native_value)
                if hasattr(type(entity), 'is_on'):
                    self.assertIsInstance(entity.is_on, bool)

    def test_capacity_button_requires_actual_curve_inputs_and_target_bounds_refresh(self):
        button = ns['EquipmentFanCapacityButton'](self.m, self.spec, operating_mode='heat')
        self.assertTrue(button.available)
        self.f.states['climate.a'].attributes['fan_modes'] = ['auto']
        self.assertFalse(button.available)
        self.assertNotIn(('heat', 'pid_apply_fan_capacity'), list(helper.scoped_fields(self.m, self.spec, 'button')))
        target = self.entity('Number', 'target_home_heat', 'heat')
        self.f.states['climate.a'].attributes.update(min_temp=12, max_temp=29, target_temp_step=1)
        target.hass = self.m.hass
        target._native_watch_enabled = False
        writes = []
        target._state_writes = N(request=writes.append)
        target.async_write_ha_state = lambda: None
        target._equipment_update()
        self.assertEqual(writes, [target])
        writes[0]._equipment_write()
        self.assertEqual((target._attr_native_min_value, target._attr_native_max_value,
                          target._attr_native_step), (12, 29, 1))

    def test_all_locales_have_labels_and_native_option_mappings(self):
        self.assertEqual(len(catalog.MODE_LABELS), 38)
        for locale in catalog.MODE_LABELS:
            for mode in model.operating_modes(self.m, self.spec):
                self.assertTrue(catalog.operating_mode_label(mode, locale))
            self.assertTrue(catalog.operating_mode_ui_labels(locale)['parameters'])
            self.assertIn('pid', catalog.mode_option_labels('control_mode', locale))
            for target in ('target_manual_humidity', 'target_sleep_heat'):
                self.assertNotIn('{', helper.setting_label(target, locale))

if __name__ == '__main__':
    unittest.main(verbosity=2)
