"""Real pure-module behavior checks with in-memory HA substitutes only."""
from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_hem_beta56_pure"


def load(name):
    if PACKAGE not in sys.modules:
        fake = ModuleType(PACKAGE)
        fake.__path__ = [str(ROOT)]
        sys.modules[PACKAGE] = fake
    full = PACKAGE + "." + name
    if full not in sys.modules:
        spec = importlib.util.spec_from_file_location(full, ROOT / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        spec.loader.exec_module(module)
    return sys.modules[full]


class BothControllerTypes(unittest.TestCase):
    def setUp(self):
        self.algorithm = load("climate_strategy")
        self.model = load("equipment_model")

    def test_legacy_room_adapts_before_selecting_hvac_mode(self):
        cfg={"enabled": True, "controller": "device", "mode": "auto",
             "target_source": "auto_comfort", "comfort_adjustment_max_c": 1.5}
        cap={"kind":"climate","heat":True,"cool":True,
             "range":True,"modes":["off","heat","cool","heat_cool"]}
        args=dict(temp_c=26.2,capability=cap,at_home="home",
                  occupied="occupied",window_safe=True,comfort_humidity_rh=85.)
        outcome=self.algorithm.policy(cfg, **args)
        self.assertEqual(outcome.profile, "comfort")
        self.assertEqual(outcome.status if hasattr(outcome,"status") else outcome.state, "ready")
        self.assertLess(outcome.range_high_c, 26.)
        cfg["target_source"]="temperature"
        fixed=self.algorithm.policy(cfg, **args)
        self.assertEqual(fixed.range_high_c, 26.)

    def test_away_and_missing_humidity_do_not_fabricate_corrections(self):
        cfg={"enabled":True,"controller":"device","mode":"auto",
             "target_source":"auto_comfort"}
        cap={"kind":"climate","heat":True,"cool":True,"range":True,
             "modes":["off","heat","cool","heat_cool"]}
        actual=self.algorithm.policy(cfg,temp_c=25.,capability=cap,
                                     at_home="away",occupied="unoccupied",
                                     comfort_humidity_rh=90.)
        self.assertEqual(actual.profile,"away")
        self.assertEqual(actual.range_high_c,30.)
        fallback=self.algorithm.policy(cfg,temp_c=25.,capability=cap,
                                       at_home="home",occupied="occupied",
                                       comfort_humidity_rh=None)
        self.assertEqual(fallback.range_high_c,26.)

    def test_managed_pid_and_native_share_same_room_comfort_targets(self):
        model=self.model
        previous_room=model.room_config
        previous_limits=model.device_limits
        try:
            model.room_config=lambda manager,spec: {
                "target_source":"auto_comfort",
                "comfort_adjustment_max_c":1.5}
            model.device_limits=lambda manager,spec,cap:{
                "temperature_min_limit":5.,"temperature_max_limit":35.,
                "humidity_min_limit":20.,"humidity_max_limit":80.,
            }
            manager=SimpleNamespace(equipment=SimpleNamespace(
                measurements=lambda spec,cap:{"humidity":85.}))
            spec=SimpleNamespace(identifier="climate-controller",area_id="living")
            cap=SimpleNamespace()
            cfg={"control_mode":"pid","preset":"none","profile_targets":{}}
            plan={"away":"home","occupancy":"occupied","sleeping":False}
            values=model.targets(manager,spec,cap,cfg,plan)
            self.assertEqual(values["heat"],20.)
            self.assertLess(values["cool"],26.)
            manager.equipment.measurements=lambda spec,cap:{"humidity":None}
            fixed=model.targets(manager,spec,cap,cfg,plan)
            self.assertEqual(fixed["cool"],26.)
        finally:
            model.room_config=previous_room
            model.device_limits=previous_limits


class PurifierEndToEnd(unittest.TestCase):
    def test_only_qualifying_filter_gets_cadr_and_excludes_heater(self):
        model=load("equipment_model")
        activation=ModuleType(PACKAGE+".device_activation")
        activation.effective_device=lambda manager,spec,source: {
            "fan_purpose":"filtration" if source=="fan.purifier" else "extraction"}
        previous=sys.modules.get(PACKAGE+".device_activation")
        sys.modules[PACKAGE+".device_activation"]=activation
        try:
            purifier=load("purifier_capacity")
            specs=[
                SimpleNamespace(identifier="filter1",area_id="living",
                                source_entities=("fan.purifier",)),
                SimpleNamespace(identifier="heater1",area_id="living",
                                source_entities=("climate.heater",)),
            ]
            saved={"filter1":{"particle_cadr_m3h":300.,"power_switch_entity":None},
                   "heater1":{"particle_cadr_m3h":1000.,"power_switch_entity":None}}
            orig_specs, orig_settings, orig_caps = model.specs, model.settings, model.capabilities
            model.specs=lambda manager: specs
            model.settings=lambda manager,spec: saved[spec.identifier]
            model.capabilities=lambda manager,spec: SimpleNamespace(
                domain="fan",modes=("off","fan_only"),primary="fan.purifier") if spec.identifier=="filter1" else SimpleNamespace(
                domain="climate",modes=("off","heat"),primary="climate.heater")
            try:
                source=SimpleNamespace(state="on")
                hass=SimpleNamespace(states=SimpleNamespace(
                    get=lambda entity: source if entity=="fan.purifier" else None))
                manager=SimpleNamespace(hass=hass)
                rated=purifier.rated_purifiers(manager,"living")
                self.assertEqual(len(rated),1)
                self.assertEqual(rated[0]["source_entity_id"],"fan.purifier")
                self.assertEqual(rated[0]["rated_particle_cadr_m3h"],300.)
                self.assertIs(rated[0]["operating"],True)
            finally:
                model.specs, model.settings, model.capabilities=orig_specs,orig_settings,orig_caps
        finally:
            if previous is None:
                sys.modules.pop(PACKAGE+".device_activation",None)
            else:
                sys.modules[PACKAGE+".device_activation"]=previous

    def test_device_ratings_supersede_legacy_room_cadr_without_double_counting(self):
        tree=ast.parse((ROOT/"environment_extended.py").read_text(encoding="utf-8"))
        wanted=[node for node in tree.body if isinstance(node,ast.FunctionDef)
                and node.name in ("room_science","_num")]
        mod=ast.Module(body=[ast.parse("from __future__ import annotations").body[0],
                             *wanted],type_ignores=[])
        calls=[]
        def particle_filtration(volume,cadr,operating,samples,now):
            calls.append((volume,cadr,operating))
            return {"status":"running" if operating else "off"}
        ns={"math":math,"particle_filtration":particle_filtration,
            "entity_on":lambda *args:True,
            "moisture_event":lambda *args,**kw:{"status":"not_ready"},
            "overheating_degree_hours":lambda *args,**kw:{"status":"not_ready"},
            "DAY_S":86400}
        exec(compile(ast.fix_missing_locations(mod),"environment_extended.py","exec"),ns)
        report,_=ns["room_science"](
            SimpleNamespace(config=SimpleNamespace(time_zone="UTC")),
            "living",{"room_volume_m3":50.,
                      "particle_cadr_m3h":1000.,
                      "purifier_entity":"fan.legacy"},
            [],5000.,history=SimpleNamespace(),
            outside_safe=False,existing={},
            purifier_ratings=[{"source_entity_id":"fan.purifier",
                               "rated_particle_cadr_m3h":300.,"operating":True}],
        )
        self.assertEqual(calls,[(50.,300.,True)])
        self.assertEqual(report["air_purification"]["installed_rated_particle_cadr_m3h"],300.)
        self.assertEqual(report["air_purification"]["running_nominal_particle_clean_air_changes_h"],6.)
        self.assertEqual(report["air_purification"]["cad_ratings_source"],"per_purifier_device")


if __name__=="__main__":
    unittest.main()
