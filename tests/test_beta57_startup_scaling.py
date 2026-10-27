"""Production AST regression: Beta55 switch enumeration blocked HA's event loop.

No HA installation or physical power command is required. Assert structural
boundedness and unchanged exact source/supply ownership validation.
"""
from __future__ import annotations
import ast
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_beta57_perf_test"


def method_source(filename, *names):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"),
                     filename=filename)
    selected = [node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == set(names)
    return ast.fix_missing_locations(ast.Module(
        body=[ast.parse("from __future__ import annotations").body[0], *selected],
        type_ignores=[]))


class FailingDeepcopy(dict):
    def __deepcopy__(self, memo):
        raise AssertionError("Never recursively deep-copy config on HA event loop")


class State:
    def __init__(self, entity):
        self.entity_id = entity


class ClaimsTests(unittest.TestCase):
    def setUp(self):
        self.module_names = []
        for module_name in (PACKAGE, PACKAGE + ".device_hierarchy"):
            self.module_names.append((module_name, sys.modules.get(module_name)))
        package = types.ModuleType(PACKAGE)
        package.__path__ = []
        sys.modules[PACKAGE] = package
        hier = types.ModuleType(PACKAGE + ".device_hierarchy")
        hier.configured_area_ids = lambda settings: tuple(settings.get("rooms", ()))
        hier.configured_sources = lambda settings, area: settings.get("sources", {}).get(area, ())
        sys.modules[hier.__name__] = hier
        self.room = "bathroom"
        self.sources = [State(f"switch.{i}") for i in range(240)]
        self.settings = {"rooms":["bathroom", "kitchen"],
                         "sources":{"bathroom":["switch.owned_actuator"],
                                    "kitchen":["switch.other_output"]},
                         "equipment_controllers":{
                             "other-controller":{"power_switch_entity":"switch.17"},
                             "this-controller":{"power_switch_entity":None}},
                         "large_config":FailingDeepcopy({"payload":"x"*60000})}
        self.config_entry = types.SimpleNamespace(
            entry_id="integration1",data={},options=self.settings)
        self.calls = 0
        def entries(domain):
            self.assertEqual(domain,"environment_manager")
            self.calls += 1
            return [self.config_entry]
        self.hass = types.SimpleNamespace(
            config_entries=types.SimpleNamespace(async_entries=entries),
            states=types.SimpleNamespace(async_all=lambda d: list(self.sources))
        )
        self.manager = types.SimpleNamespace(
            entry=self.config_entry,hass=self.hass,settings=self.settings)
        self.spec = types.SimpleNamespace(
            identifier="this-controller",area_id="bathroom",
            source_entities=("climate.device",),source_device_id="native-device")
        self.locations = {f"switch.{i}": "bathroom" if i % 2 == 0 else "kitchen"
                          for i in range(240)}
        self.locations["switch.17"] = "bathroom"
        model = types.SimpleNamespace(
            SETTINGS="equipment_controllers",
            settings=lambda manager,spec: manager.settings[
                "equipment_controllers"][spec.identifier])
        namespace = {"__name__":PACKAGE+".outlet", "__package__":PACKAGE,
                     "DOMAIN":"environment_manager","model":model,
                     "entity_area":lambda hass,e:self.locations.get(e),
                     "relay_identity":lambda hass,spec,e: (
                         {"entity":e,"area":spec.area_id,
                          "registry_id":"registered_"+e}
                         if self.locations.get(e) == spec.area_id else None)}
        exec(compile(method_source("equipment_power_switch.py",
             "_configured_manager_entries","_switch_claims",
             "supply_options","permitted_supply"),
             "equipment_power_switch.py","exec"),namespace)
        self.api=namespace

    def tearDown(self):
        for k,previous in self.module_names:
            if previous is None:
                sys.modules.pop(k,None)
            else:
                sys.modules[k]=previous

    def test_one_snapshot_for_hundreds_of_switches_and_excludes_claims(self):
        options=self.api["supply_options"](self.manager,self.spec)
        self.assertEqual(self.calls,1,
                         "One switch selector must not read/copy all config entries 240 times")
        self.assertIn("switch.0",options)
        self.assertNotIn("switch.2fake",options)
        self.assertNotIn("switch.17",options)
        self.assertNotIn("switch.1",options)
        self.assertEqual(len(set(options)),len(options))

    def test_live_validation_rechecks_unloaded_entry_ownership(self):
        entity="switch.0"
        allowed=self.api["permitted_supply"](
            self.manager,self.spec,entity)
        self.assertIsNotNone(allowed)
        self.settings["equipment_controllers"]["other-controller"][
            "power_switch_entity"]=entity
        disallowed=self.api["permitted_supply"](
            self.manager,self.spec,entity)
        self.assertIsNone(disallowed,"Live validation must not use stale option cache")
        self.assertIsNone(self.api["permitted_supply"](
            self.manager,self.spec,"switch.owned_actuator"))

    def test_regression_guard_config_not_copied_in_property_path(self):
        options=self.api["supply_options"](self.manager,self.spec)
        self.assertGreater(len(options),20)


class SelectorCachingTests(unittest.TestCase):
    def test_options_are_memoized_even_on_thousands_of_state_reads(self):
        filename="select.py"
        source=ast.parse((ROOT/filename).read_text(encoding="utf-8"))
        candidates=[n for n in source.body if isinstance(n,ast.ClassDef)
                    and n.name=="EquipmentPowerSwitchSelect"]
        self.assertEqual(len(candidates),1)
        module=ast.fix_missing_locations(ast.Module(body=candidates,type_ignores=[]))
        calls=[]
        power_module=types.ModuleType(PACKAGE+".equipment_power_switch")
        def load_choices(manager,spec):
            calls.append(spec.identifier)
            return ("switch.one","switch.two")
        power_module.supply_options=load_choices
        saved={k:sys.modules.get(k) for k in (PACKAGE,PACKAGE+".equipment_power_switch")}
        package=types.ModuleType(PACKAGE);package.__path__=[]
        sys.modules[PACKAGE]=package
        sys.modules[power_module.__name__]=power_module
        class Base:
            def __init__(self,manager,spec,key):
                self._manager,self._spec,self._key=manager,spec,key
            @property
            def controller_settings(self):
                return {"power_switch_entity":None}
        try:
            ns={"__name__":PACKAGE+".selectors","__package__":PACKAGE,
                "EquipmentSelect":Base}
            exec(compile(module,filename,"exec"),ns)
            manager=types.SimpleNamespace()
            spec=types.SimpleNamespace(identifier="controller1")
            instance=ns["EquipmentPowerSwitchSelect"](manager,spec)
            for _ in range(5000):
                self.assertEqual(instance.options,["none","switch.one","switch.two"])
            self.assertEqual(len(calls),1,
                "Beta55 rebuilt all switch candidates on each HA state serialization")
            self.assertEqual(instance.current_option,"none")
        finally:
            for name,old in saved.items():
                if old is None:
                    sys.modules.pop(name,None)
                else:
                    sys.modules[name]=old


class NativeRecoveryScopeTests(unittest.TestCase):
    def test_every_native_event_only_revisits_its_affected_room(self):
        source = (ROOT/"number.py").read_text(encoding="utf-8")
        self.assertIn("watched_specs.setdefault(native_entity, []).append(spec)", source)
        self.assertIn("affected_specs = watched_specs.get(", source)
        self.assertIn("affected_areas = {spec.area_id for spec in affected_specs}", source)
        self.assertIn("for area_id in affected_areas:", source)
        self.assertIn("for spec in affected_specs:", source)
        self.assertIn("if number._area_id not in affected_areas:", source)
        self.assertIn("if (changed or availability_changed)", source)
        self.assertNotIn("elif getattr(number, \"hass\", None):", source)


class ListenerTests(unittest.TestCase):
    def test_irrelevant_state_events_do_not_read_controller_settings(self):
        text=(ROOT/"equipment_entity.py").read_text(encoding="utf-8")
        self.assertIn("_watched_upstream_switch",text)
        self.assertNotIn(
            'updated != model.settings(self._manager, self._spec).get("power_switch_entity")',
            text,
        )
        self.assertIn("if hasattr(self, \"_watched_upstream_switch\"):",text)


if __name__=="__main__":
    unittest.main()
