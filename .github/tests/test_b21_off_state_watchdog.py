"""No false physical-ON assertion from a room temperature anomaly."""
import importlib.util
from pathlib import Path

source = Path(__file__).resolve().parents[2] / "custom_components/environment_manager/off_state_watchdog.py"
spec = importlib.util.spec_from_file_location("off_state_watchdog", source)
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Watch = module.ThermalWatch


def watch():
    return Watch(("sensor.living_room_temperature",), 100)


def sample(w, at, temp, *, target=20, sources=("sensor.living_room_temperature",),
           off=100, clear=True, physical=None):
    return w.observe(now=at, temperature_c=temp, target_c=target,
        source_ids=sources, off_since=off,
        other_heat_sources_clear=clear, independent_heat_output=physical)


w = watch()
assert sample(w, 100, 20) == "none"
assert sample(w, 400, 20.5) == "none"
assert sample(w, 700, 21) == "none"
assert sample(w, 1000, 21.6) == "none"
assert sample(w, 1300, 22.0) == "none"
assert sample(w, 1600, 22.4) == "none"
assert sample(w, 1900, 22.8) == "suspected"
assert sample(w, 2200, 23.0, physical=True) == "confirmed"
assert sample(w, 2500, 23.1, physical=False) == "suspected"
assert sample(w, 2800, 23.4, clear=False) == "none"
assert sample(w, 3100, 23.8) == "none"  # cannot bridge uncertain source
assert sample(w, 3400, 24.0, sources=("sensor.other",)) == "none"
assert sample(w, 3700, 24.1, off=3000) == "none"
assert sample(w, 4000, None) == "none"
assert sample(w, 4300, 24.3) == "none"
assert sample(w, 4900, 24.5) == "none"  # stale gap invalidates trend
assert sample(w, 5800, 24.7) == "none"
w = watch()
assert sample(w, 1900, 24) == "none"  # single hot reading not enough
assert sample(w, 2200, 24.3) == "none"
assert sample(w, 2500, 24.5) == "none"  # below 0.7 rise
assert sample(w, 2800, 24.8) == "suspected"
w = watch()
assert sample(w, 1900, 20) == "none"
assert sample(w, 2200, 21, target=21) == "none"
assert sample(w, 2500, 22, target=21) == "none"
assert sample(w, 2800, 22.4, target=21) == "none"  # target gap below 1.5
assert sample(w, 3100, 22.6, target=21) == "suspected"
print("B21_THERMAL_ANOMALY_EVIDENCE_NO_FALSE_PHYSICAL_ON=PASS")
