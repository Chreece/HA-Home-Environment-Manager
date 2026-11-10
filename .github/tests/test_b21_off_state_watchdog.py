"""Deterministic evidence and OFF-only retry budget, no device-specific fixtures."""
import importlib.util
from pathlib import Path
import sys

source = Path(__file__).resolve().parents[2] / "custom_components/environment_manager/off_state_watchdog.py"
spec = importlib.util.spec_from_file_location("off_state_watchdog", source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

Watch, due = module.ThermalWatch, module.recovery_due


def sample(w, at, temp, *, target=20, sources=("sensor.room_temperature",),
           off=100, clear=True, physical=None):
    return w.observe(now=at, temperature_c=temp, target_c=target,
        source_ids=sources, off_since=off,
        other_heat_sources_clear=clear, independent_heat_output=physical)


w = Watch(("sensor.room_temperature",), 100)
assert sample(w, 100, 20) == "none"
assert sample(w, 400, 20.3) == "none"
assert sample(w, 700, 20.5) == "none"
assert sample(w, 1600, 22.0) == "none"   # settling: residual radiator heat
assert sample(w, 1900, 21.0) == "none"  # start a fresh trend AFTER settling
assert sample(w, 2020, 21.2) == "none"
assert sample(w, 2140, 21.4) == "none"
assert sample(w, 2260, 21.5) == "none"
assert sample(w, 2380, 21.7) == "none"
assert sample(w, 2500, 22.0) == "none"
assert sample(w, 2620, 22.2) == "none"
assert sample(w, 2740, 22.4) == "none"
assert sample(w, 2860, 22.6) == "suspected"
assert sample(w, 2980, 22.8, physical=True) == "confirmed"
assert sample(w, 3100, 23.0, physical=False) == "suspected"
assert sample(w, 3220, 23.2, clear=False) == "none"
assert sample(w, 3340, 23.6) == "none"
assert sample(w, 3460, 23.7, sources=("sensor.other",)) == "none"
assert sample(w, 3580, 24.0, off=3000) == "none"
assert sample(w, 3700, None) == "none"
assert sample(w, 5000, 24.2) == "none"  # gap invalidates the old trend

w = Watch(("sensor.room_temperature",), 100)
assert sample(w, 1900, 24.0) == "none"
assert sample(w, 2200, 24.3) == "none"
assert sample(w, 2500, 24.5) == "none"
assert sample(w, 2800, 24.8) == "suspected"
assert sample(w, 3100, 24.9, target=24.0) == "none"  # not above target

assert module.verified_heat_shutdown("climate", ("heat", "off"), "heat", None)
assert module.verified_heat_shutdown("climate", ("heat", "cool", "auto", "off"), "auto", "heating")
assert module.verified_heat_shutdown("switch", ("off", "heat"), "on", None)
assert not module.verified_heat_shutdown("climate", ("cool", "off"), "cool", None)
assert not module.verified_heat_shutdown("climate", ("heat", "cool", "auto", "off"), "auto", "idle")
assert not module.verified_heat_shutdown("fan", ("off", "heat"), "on", None)

ledger={"off_since":100,"attempts":0, "last_attempt_at":None}
assert not due(ledger,100+1799,guarded=True)
assert not due(ledger,100+2800,guarded=False)
assert due(ledger,100+2800,guarded=True)
ledger["attempts"]=1
ledger["last_attempt_at"]=2900
assert not due(ledger,3000,guarded=True)
assert due(ledger,3500,guarded=True)
ledger["attempts"]=2
assert not due(ledger,4500,guarded=True)
ledger["attempts"]=0
assert not due(ledger,100+24*3600+1,guarded=True)
print("B21_THERMAL_ANOMALY_BOUND_TO_HEM_SHUTDOWN_AND_MAX_TWO_OFF_RETRIES=PASS")
