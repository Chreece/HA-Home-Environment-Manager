"""Beta84: one gain authority, actionable PID recommendations and replay safety.

Pure simulation; never reaches a Home Assistant instance or its actuators.
"""
from __future__ import annotations

import asyncio
import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[2]
pkg=ModuleType("hem_beta84_test")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("pid_calibration","pid_passive","pid_review"):
    loader=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(loader)
    sys.modules[loader.name]=module
    loader.loader.exec_module(module)
review=sys.modules[pkg.__name__+".pid_review"]
assert review.selected_method({})=="adaptive_suggest"
assert review.selected_method({"pid_adaptation_mode":"bounded"})=="adaptive_auto"
assert review.selected_method({"pid_calibration_method":"manual","pid_adaptation_mode":"bounded"})=="adaptive_auto"
assert review.selected_method({"pid_calibration_method":"cohen_coon","pid_adaptation_mode":"bounded"})=="cohen_coon"
assert review.selected_method({"pid_calibration_method":"imc_lambda","pid_adaptation_mode":"observe"})=="imc_lambda"
assert review.selected_method({"pid_calibration_method":"manual","pid_adaptation_mode":"disabled"})=="manual"
for k,v in (("adaptive_suggest","observe"),("adaptive_auto","bounded"),
            ("cohen_coon","disabled"),("manual","disabled")):
    assert review.legacy_mode(k)==v
assert len(set(review.ALL_METHODS))==5

cfg={"pid_calibration_method":"adaptive_suggest","kp":20.,"ki":.2,"kd":3.}
summary={
    "status":"suggestion_only", "confidence":"medium", "valid_cycles":3,
    "last_cycle_at":200., "metric":"temperature",
    "suggested_gains":{"kp":80.,"ki":1.,"kd":0.}
}
proposal=review.proposal_for(cfg,summary,"room:device:exact",now=201.)
assert proposal is not None and review.is_pending(proposal)
assert proposal["current"]=={"kp":20.,"ki":.2,"kd":3.}
assert proposal["apply"]=={"kp":22.,"ki":.22,"kd":3.}
assert proposal["recommended"]==summary["suggested_gains"]
assert proposal["cycle_at"]==200.
token=proposal["id"]
assert review.decode_mobile_action(f"{review.ACTION_PREFIX}APPROVE_{token}")==("approve",token)
assert review.decode_mobile_action(f"{review.ACTION_PREFIX}DISCARD_{token}")==("discard",token)
assert review.decode_mobile_action(f"{review.ACTION_PREFIX}APPROVE_notatoken") is None
assert review.decode_mobile_action(f"FOREIGN_APP_APPROVE_{token}") is None
assert not review.is_pending({**proposal,"state":"discarded"})
assert not review.is_pending({**proposal,"id":"invalid"})
assert review.proposal_for({**cfg,"pid_calibration_method":"cohen_coon"},
                           summary,"ctx",201.) is None
assert review.proposal_for(cfg,{**summary,"valid_cycles":2},"ctx",201.) is None

class MockServices:
    def __init__(self):
        self.calls=[]
    def has_service(self,domain,service):
        return ((domain,service) in {
            ("persistent_notification","create"),
            ("persistent_notification","dismiss"),
            ("notify","mobile_app_phone"),
            ("notify","mobile_app_tablet"),
        })
    async def async_call(self,domain,service,data,**kwargs):
        self.calls.append((domain,service,data,kwargs))

async def notification_test():
    services=MockServices()
    hass=NS(services=services)
    manager=NS(entry=NS(entry_id="abc"),settings={
        "notify_entities":["notify.mobile_app_phone","notify.mobile_app_phone",
                           "notify.nonmobile","notify.mobile_app_tablet"],
    })
    spec=NS(identifier="device1",name="Heating unit")
    assert await review.async_publish_review(hass,manager,spec,proposal)
    assert len(services.calls)==3,services.calls
    for domain,target,data,_ in services.calls:
        assert "20" in data["message"] and "22" in data["message"]
        assert "model target 80" in data["message"]
        if domain=="notify":
            actions=data["data"]["actions"]
            assert [a["title"] for a in actions]==["Approve","Discard"]
            assert all(a["authenticationRequired"] for a in actions)
            assert all(token in a["action"] for a in actions)
    await review.async_clear_review(hass,manager,spec)
    assert len(services.calls)==6
    assert services.calls[3][1]=="dismiss"
    assert all(x[2]["message"]=="clear_notification" for x in services.calls[4:])
    # No implicit broadcast if no explicitly configured Companion target.
    services.calls.clear()
    manager.settings["notify_entities"]=[]
    assert await review.async_publish_review(hass,manager,spec,proposal)
    assert len(services.calls)==1 and services.calls[0][0]=="persistent_notification"

asyncio.run(notification_test())

# AST check: the real runtime must verify a review before AND after the
# storage await, and the old independent passive selector must not be added.
tree=ast.parse((ROOT/"equipment_runtime.py").read_text())
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef)
           and n.name=="EquipmentRuntime")
update=next(n for n in klass.body if isinstance(n,ast.AsyncFunctionDef)
            and n.name=="async_update")
checks=[n for n in ast.walk(update) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Attribute)
        and n.func.attr=="_pid_review_authorized"]
assert len(checks)==2,checks
guard=next(n for n in klass.body if isinstance(n,ast.FunctionDef)
           and n.name=="_pid_review_authorized")
guard_source=ast.get_source_segment((ROOT/"equipment_runtime.py").read_text(),guard)
assert "observed_output_off" in guard_source
assert "created_at" in guard_source and "previous_gains" in guard_source
assert 'is_pending(review)' in guard_source
selector=(ROOT/"select.py").read_text()
assert 'EquipmentSelect(manager, spec, "pid_adaptation_mode")' not in selector
assert 'EquipmentSelect(manager, spec, "pid_calibration_method")' in selector
button=(ROOT/"button.py").read_text()
assert 'EquipmentPIDReviewButton' in button
assert 'in ("imc_lambda","cohen_coon")' in button
status=(ROOT/"equipment_status.py").read_text()
assert '"pid_review"' in status
# Every supported HA locale must have all five calibration modes and two
# real native button entities, including the Greek and German catalogues.
import json
for p in (ROOT/"strings.json",*(ROOT/"translations").glob("*.json")):
    data=json.loads(p.read_text(encoding="utf-8"))
    assert set(data["entity"]["select"]["equipment_pid_calibration_method"]["state"])==set(review.ALL_METHODS),p
    for action in ("approve","discard"):
        assert data["entity"]["button"][f"equipment_pid_review_{action}"]["name"],p
assert len(list((ROOT/"translations").glob("*.json")))==38
print("BETA84_UNIFIED_TUNING_REVIEW_ACTIONS_NOTIFICATIONS_AND_LOCALES=PASS")
