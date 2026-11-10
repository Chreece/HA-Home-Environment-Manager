"""HEM's OFF-response model is generic: no radio vendor, device ID or model."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

root = Path(__file__).resolve().parents[2] / "custom_components/environment_manager"
pkg = ModuleType("test_hem_b22_profiles")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg


def load(name):
    filename = root / (name + ".py")
    spec = importlib.util.spec_from_file_location(pkg.__name__ + "." + name, filename)
    instance = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = instance
    spec.loader.exec_module(instance)
    return instance


profiles = load("off_state_profiles")
detector = load("off_state_watchdog")
class Cap(NS):
    pass

def cap(domain, modes, **kw):
    return Cap(domain=domain, modes=tuple(modes), **kw)

heat = cap("climate", ("off", "heat", "cool", "auto"))
cool = cap("climate", ("off", "heat", "cool", "auto", "heat_cool"))
dry = cap("climate", ("off", "dry"))
rh_up = cap("humidifier", ("off", "auto"), humidifying=True)
rh_down = cap("humidifier", ("off", "dry"), humidifying=False)
heat_switch = cap("switch", ("off", "heat"))
cool_percent = cap("number", ("off", "cool"))
not_heater = cap("fan", ("off", "fan_only"))

assert profiles.shutdown_effect(heat, "heat", "heating") == "heat"
assert profiles.shutdown_effect(cool, "cool", "cooling") == "cool"
assert profiles.shutdown_effect(cool, "auto", "cooling") == "cool"
assert profiles.shutdown_effect(cool, "heat_cool", "heating") == "heat"
assert profiles.shutdown_effect(cool, "auto", "idle") is None
assert profiles.shutdown_effect(dry, "dry", "drying") == "dry"
assert profiles.shutdown_effect(rh_up, "on", None) == "humidify"
assert profiles.shutdown_effect(rh_down, "on", None) == "dry"
assert profiles.shutdown_effect(heat_switch, "on", None) == "heat"
assert profiles.shutdown_effect(cool_percent, "43", None) == "cool"
assert profiles.shutdown_effect(not_heater, "on", None) is None
assert profiles.shutdown_effect(heat_switch, "off", None) is None
assert profiles.shutdown_effect(heat_switch, "unavailable", None) is None

def observe(effect, target, points, *, clear=True):
    w=detector.ThermalWatch(("sensor.independent",),100,effect=effect)
    traces=[]
    for at, value in points:
        traces.append(w.observe(
            now=at, temperature_c=value, target_c=target,
            source_ids=("sensor.independent",),off_since=100,
            other_heat_sources_clear=clear, direction=effect,
            room_temperature_c=21.0 if effect in ("humidify","dry") else None))
    return traces

cool_trace=observe("cool", 22, [(100,24),(1000,23),(1900,23.2),
    (2140,22.8),(2380,22.4),(2620,21.6),(2860,20.5)])
assert cool_trace[:-1] == ["none"]*6 and cool_trace[-1]=="suspected", cool_trace
assert observe("heat",20,[(1900,21),(2200,21.8),(2500,22.6),(2800,23)])[-1]=="suspected"
rh_up_trace=observe("humidify",50,[(1900,60),(2700,55),(2900,53),
    (3200,55),(3500,57),(3800,60),(4100,62)])
assert rh_up_trace[:-1]==["none"]*6 and rh_up_trace[-1]=="suspected",rh_up_trace
rh_down_trace=observe("dry",50,[(1900,30),(2700,45),(2900,56),
    (3200,53),(3500,49),(3800,45),(4100,41)])
assert rh_down_trace[:-1]==["none"]*6 and rh_down_trace[-1]=="suspected",rh_down_trace

# An RH trend caused by cooling/warming ALONE must never trigger a fault
# or an actuator retry: absolute water vapor did not increase/decrease.
def psychrometric(effect, points):
    w = detector.ThermalWatch(("sensor.independent",), 100, effect=effect)
    return [w.observe(now=at, temperature_c=rh, target_c=50.,
        source_ids=w.source_ids, off_since=100.,
        other_heat_sources_clear=True, direction=effect,
        room_temperature_c=temp) for at, temp, rh in points]

assert psychrometric("humidify", [
    (2900,22.,53.),(3200,21.,55.),(3500,20.,57.),
    (3800,19.,60.),(4100,18.,62.)
])[-1] == "none", "RH rise from cooling must not implicate humidifier"
assert psychrometric("dry", [
    (2900,18.,56.),(3200,19.5,53.),(3500,21.,49.),
    (3800,22.5,45.),(4100,24.,41.)
])[-1] == "none", "RH fall from warming must not implicate dehumidifier"
no_temp = detector.ThermalWatch(("sensor.independent",), 100, effect="dry")
assert no_temp.observe(now=4200., temperature_c=40.,target_c=50.,
    source_ids=no_temp.source_ids,off_since=100.,
    other_heat_sources_clear=True,direction="dry") == "none"

w = detector.ThermalWatch(("sensor.independent",), 100)
for at,temp in [(1900,21),(2200,21.5)]:
    assert w.observe(now=at,temperature_c=temp,target_c=20,
        source_ids=w.source_ids,off_since=100,other_heat_sources_clear=True)=="none"
assert w.observe(now=2500,temperature_c=22,target_c=24,
    source_ids=w.source_ids,off_since=100,other_heat_sources_clear=True)=="none"
assert w.samples == [(2500,22)]  # target change invalidates slope
assert observe("humidify", 50, [(2900,52),(3200,58),(3500,60),(3800,64),
    (4100,66)], clear=False)[-1]=="none"
for effect in profiles.EFFECTS:
    for lang in ("en", "de", "el", "fr"):
        for kind in ("suspected", "exhausted"):
            title,message=profiles.notice(effect,lang,kind,
                name="Device", room="Room",first=40,current=45,target=42,
                attempts=2)
            assert "Device" in message and "Room" in message
            assert title and "42.0" in message
print("B22_ALL_FOUR_OUTPUT_DIRECTIONS_SOURCE_TARGET_AND_NOTICE_GATES=PASS")
