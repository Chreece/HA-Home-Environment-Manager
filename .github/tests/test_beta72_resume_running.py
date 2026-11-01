"""Beta72: actual EquipmentRuntime.async_resume and native power reconciliation.

No live HA or actuator calls. Source methods are extracted unmodified from
the integration, while HA states, service ACK and config writes are deterministic.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as N

BASE = Path(__file__).resolve().parents[2]
NOW = 100000.0


class HomeAssistantError(Exception):
    pass


def state(value="heat", domain="climate", *, changed=NOW-900):
    return N(
        state=value, domain=domain,
        attributes={"hvac_action":"heating"} if domain=="climate" else {},
        last_changed=datetime.fromtimestamp(changed, timezone.utc),
    )


def finite(value, low, high):
    try:
        number=float(value)
        return number if low<=number<=high else None
    except (TypeError,ValueError,OverflowError):
        return None


def off(value):
    if value is None: return False
    if value.domain in ("number","input_number"):
        return finite(value.state,0,100)==0
    return value.state=="off"


def snapshot(value):
    if value is None or value.state in ("unknown","unavailable"):
        return None
    return {"state":value.state,"attributes":dict(value.attributes)}


def matches(observed, expected):
    return observed is not None and observed.state==expected.get("state")


identity={"entity":"switch.plug","registry_id":"original-relay","device_id":"plug-device","area":"wohnzimmer"}
spec=N(identifier="living-heater",area_id="wohnzimmer",
       source_device_id="thermostat-device",
       source_entities=("climate.heater",))


class Model:
    SETTINGS="equipment_controllers"
    @staticmethod
    def settings(manager, spec):
        return manager.settings[Model.SETTINGS][spec.identifier]
    @staticmethod
    def capabilities(manager, spec):
        return manager.cap
    @staticmethod
    def permission(manager, spec, cap):
        return (True, manager.native_permission)
    @staticmethod
    def control_modes(manager, spec):
        return ("existing","automatic","pid","manual","off")
    @staticmethod
    def timing(manager, spec, cap):
        return (600.0, 600.0, 7200.0)


pkg=ModuleType("beta72_fixture");pkg.__path__=[]
power_mod=ModuleType("beta72_fixture.equipment_power_switch")
activation=ModuleType("beta72_fixture.device_activation")
power_mod.permitted_supply=lambda manager, spec, entity, expected=None: (
    dict(identity)
    if manager.switch_permission and entity==identity["entity"]
    and (expected is None or expected==identity)
    else None
)
activation.authorized=lambda manager,spec: manager.native_permission
sys.modules[pkg.__name__]=pkg
sys.modules[power_mod.__name__]=power_mod
sys.modules[activation.__name__]=activation

src=ast.parse((BASE/"equipment_runtime.py").read_text(encoding="utf-8"))
klass=next(x for x in src.body if isinstance(x,ast.ClassDef) and x.name=="EquipmentRuntime")
func=next(x for x in klass.body if isinstance(x,ast.AsyncFunctionDef) and x.name=="async_resume")
ns={"__name__":"beta72_fixture.equipment_runtime","__package__":"beta72_fixture",
    "HomeAssistantError":HomeAssistantError,"asyncio":asyncio,"model":Model,
    "deepcopy":deepcopy,"snapshot":snapshot,"matches":matches,"output_off":off,
    "finite":finite,
    "foreign_owner_hold":lambda hass,owner,e: hass.manager.foreign_owner,
}
exec(compile(ast.Module(body=[func],type_ignores=[]),"equipment_runtime.py","exec"),ns)
real_resume=ns["async_resume"]


class Runtime:
    def __init__(self, native="heat", supply=None, *, mode="pid",
                 prior_owned=False, supply_owned=False, cap=True):
        self.now=NOW
        self._active=self._ready=True
        self._started=NOW-450
        self._memory={spec.identifier:("old","old",123)}
        self._profile_wake={spec.identifier:{"until":NOW+50}}
        self._fan_allocations={spec.identifier:{"speed":20}}
        self._pid_offline_previews={spec.identifier:{"status":"prepared"}}
        self._mutex=asyncio.Lock()
        self.calls=[]
        self.saved=[]
        self.scheduled=0
        self.status=None
        self.on_save=None
        self.states={"climate.heater":state(native)} if native is not None else {}
        if supply is not None: self.states["switch.plug"]=state(supply,"switch")
        self.hass=N(states=N(get=self.states.get),config_entries=N(),manager=None)
        self.manager=N(
            hass=self.hass, entry=N(entry_id="hem",options={}),
            native_permission=True,switch_permission=True,foreign_owner=None,
            cap=N(primary="climate.heater",domain="climate",
                  modes=("off","heat","cool")) if cap else None,
            settings={Model.SETTINGS:{spec.identifier:{
                "control_mode":mode,"power_switch_entity":"switch.plug"
                 if supply is not None else None,
            }}},
        )
        self.hass.manager=self.manager
        self.manager.entry.options=deepcopy(self.manager.settings)
        def update_entry(entry,*,options):
            entry.options=deepcopy(options)
            self.manager.settings=deepcopy(options)
        self.hass.config_entries.async_update_entry=update_entry
        self.record={
            "sources":list(spec.source_entities),"area":spec.area_id,
            "source_device_id":spec.source_device_id,
            "baseline":{"climate.heater":snapshot(self.states.get("climate.heater"))},
            "paused":"physical_manual_override",
            "pending":None,
            "power":{"climate.heater":{"since":NOW-750,"min_on":600,"max_on":7200}}
                     if prior_owned else {},
            "off_at":{},
            "upstream":({
                "entity":"switch.plug","identity":dict(identity),
                "owned":supply_owned,"pending":None,"paused":None
            } if supply is not None else {}),
        }
    def clock(self):return self.now
    def _record(self,spec):return self.record
    def _current_spec(self,spec):return True
    def _lock(self,key):return self._mutex
    def _observed_off_since(self,e,now):
        s=self.states.get(e)
        return s.last_changed.timestamp() if s is not None else now
    async def _save(self):
        self.saved.append(deepcopy(self.record))
        if self.on_save:
            callback,self.on_save=self.on_save,None
            callback()
    def _status(self,spec,status,**kwargs):self.status=(status,kwargs)
    def schedule(self):self.scheduled+=1
    async_resume=real_resume


async def must_reject(r, reason):
    prior=deepcopy(r.record)
    try:await r.async_resume(spec)
    except HomeAssistantError as e:
        assert reason in str(e), (reason,str(e))
    else:raise AssertionError("Resume accepted unsafe state")
    assert r.calls==[],r.calls
    assert r.record["paused"]==prior["paused"] or (
        r.record["paused"]=="physical_state_changed_during_resume")


async def run():
    # The exact user regression: known controller-owned live HEAT cannot
    # require physical OFF merely because the user paused or changed target.
    prior=Runtime(prior_owned=True)
    before=deepcopy(prior.record["power"])
    await prior.async_resume(spec)
    assert prior.record["power"]==before,prior.record
    assert prior.record["paused"] is None
    assert prior.record["baseline"]["climate.heater"]["state"]=="heat"
    assert prior.status[0]=="controlling" and prior.scheduled==1,prior.status
    assert prior._started==NOW-450 and prior.calls==[]
    assert not prior._memory and not prior._profile_wake
    # HA can synthesize a very recent last_changed at startup while the
    # physical radiator actually remained ON. Preserve the stored confirmed
    # timestamp, rather than inventing another minimum-ON period.
    rerun=Runtime(prior_owned=True)
    rerun.states["climate.heater"]=state("heat",changed=NOW-80)
    await rerun.async_resume(spec)
    assert rerun.record["power"]["climate.heater"]["since"]==NOW-750
    # The Resume click is explicit authorization to take over an active
    # physical heater that was never automatically adopted by polling.
    unowned=Runtime()
    await unowned.async_resume(spec)
    assert unowned.record["power"]["climate.heater"]=={
       "since":NOW-900,"min_on":600.,"max_on":7200.,
    }
    assert not unowned.calls
    # Existing physical OFF duration must NOT restart at the Resume click.
    idle=Runtime(native="off")
    await idle.async_resume(spec)
    assert idle.record["power"]=={}
    assert idle.record["off_at"]["climate.heater"]==NOW-900
    assert idle._started==NOW-450

    # Manual changes can return to the formerly chosen automatic method,
    # never guess one when none was previously recorded.
    manual=Runtime(mode="manual",prior_owned=True)
    manual.record["resume_control_mode"]="pid"
    await manual.async_resume(spec)
    assert Model.settings(manual.manager,spec)["control_mode"]=="pid"
    assert "resume_control_mode" not in manual.record
    assert not manual.calls
    # With no remembered prior controller, Manual remains Manual.
    no_prior=Runtime(mode="manual")
    await no_prior.async_resume(spec)
    assert Model.settings(no_prior.manager,spec)["control_mode"]=="manual"

    for switch_owned in (True,False):
        switched=Runtime(supply="on",prior_owned=True,supply_owned=switch_owned)
        await switched.async_resume(spec)
        assert switched.record["upstream"]["owned"]==switch_owned
        assert switched.states["switch.plug"].state=="on" and not switched.calls
    unplugged=Runtime(native=None,supply="off",cap=False)
    await unplugged.async_resume(spec)
    assert unplugged.record["paused"] is None
    assert unplugged.record["upstream"]["owned"] is False
    assert not unplugged.record["power"] and unplugged.scheduled==1

    old_device=Runtime(prior_owned=True)
    old_device.record["source_device_id"]="previous-device"
    await must_reject(old_device,"Stored physical controller identity changed")
    orphan_relay=Runtime(supply="on",supply_owned=True)
    orphan_relay.record["upstream"].pop("identity")
    await must_reject(orphan_relay,"ownership identity")
    failed=Runtime()
    failed.manager.native_permission=False
    await must_reject(failed,"not authorized")
    wrong=Runtime()
    wrong.states["climate.heater"]=state("unknown")
    await must_reject(wrong,"unavailable")
    conflict=Runtime()
    conflict.manager.foreign_owner="different-controller"
    await must_reject(conflict,"different controller")
    prior_intent=Runtime(prior_owned=True)
    prior_intent.record["pending"]={
       "phase":"intent","entity":"climate.heater","expected":{"state":"heat"},
       "power":True,
    }
    await must_reject(prior_intent,"interrupted native command")
    mismatch=Runtime(prior_owned=True)
    mismatch.record["pending"]={
       "phase":"commanded","entity":"climate.heater","expected":{"state":"cool"},
       "power":True,
    }
    await must_reject(mismatch,"interrupted native command")
    accepted=Runtime()
    accepted.record["pending"]={
       "phase":"commanded","entity":"climate.heater","expected":{"state":"heat"},
       "power":True,
    }
    await accepted.async_resume(spec)
    assert accepted.record["pending"] is None and accepted.record["power"]

    relay_conflict=Runtime(supply="on")
    relay_conflict.manager.switch_permission=False
    await must_reject(relay_conflict,"identity")
    relay_pending=Runtime(supply="on")
    relay_pending.record["upstream"]["pending"]={
       "phase":"intent","desired":"on","identity":dict(identity),
    }
    await must_reject(relay_pending,"upstream power command")
    relay_ack=Runtime(supply="on")
    relay_ack.record["upstream"]["pending"]={
       "phase":"commanded","desired":"on","identity":dict(identity),
    }
    await relay_ack.async_resume(spec)
    assert relay_ack.record["upstream"]["owned"] is True
    # If the physical heater moves while Store is awaited, keep the pause.
    race=Runtime()
    race.on_save=lambda: race.states.__setitem__("climate.heater",state("off"))
    await must_reject(race,"changed during Resume")
    assert race.scheduled==0
    assert race.record["paused"]=="physical_state_changed_during_resume"

    print("PASS Beta72: owned and explicit unowned running Resume, manual->PID, "
          "ON/OFF supply ownership, no physical service, preserved dwell, "
          "no capability invention, uncertain command refusal, foreign-owner "
          "gate and persisted state-race hold")


asyncio.run(run())
