"""Build full native PID, device-input and shared explanations from reviewed rows."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
package = ModuleType("hem_native_residual_build")
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[package.__name__] = package
languages = importlib.import_module(package.__name__ + ".languages").SUPPORTED_LANGUAGE_TAGS


def digits(value):
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in value).replace(",", ".").replace("٫", ".")


def build(family):
    data = ROOT / ".github/translations" / ("native_backend_" + family)
    sources = json.loads((data / "sources.json").read_text())
    memory = {item["en"]: {"en": item["en"]} for item in sources}
    seen = set()
    for path in sorted(data.glob("*.txt")):
        for line in path.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            locale, *values = line.split("|")
            assert locale not in seen, (family, locale, "duplicate")
            seen.add(locale)
            assert len(values) == len(sources), (family, locale, len(values))
            for item, value in zip(sources, values):
                assert value.strip() and value != item["en"], (family, locale, item["id"])
                if family == "pid":
                    required = {18: ("Kp", "Ki", "Kd", "%", "°C"), 56: ("HEAT", "COOL"),
                                58: ("22", "°C"), 59: ("0.25", "°C"), 60: ("0", "°C"),
                                86: ("climate.*",), 87: ("10", "°C/°F"), 138: ("0.5", "°C")}
                elif family == "inputs":
                    required = {88: ("climate.*",), 89: ("°C", "°F"),
                                91: ("climate.*", "HEAT"), 92: ("climate.*", "COOL"),
                                93: ("climate.*", "DRY"), 94: ("climate.*", "FAN_ONLY"),
                                95: ("humidifier.*",), 96: ("dehumidifier.*",),
                                97: ("fan.*", "CO₂"), 98: ("fan.*", "PM2.5", "HEPA"),
                                99: ("%",), 100: ("CO₂", "ppm", "NDIR", "eCO₂"),
                                101: ("PM2.5", "µg/m³"), 103: ("Home Assistant",),
                                104: ("AQI",), 105: ("Home Assistant",), 108: ("%",),
                                109: ("CO₂", "ppm", "NDIR", "TVOC", "eCO₂"),
                                110: ("PM2.5", "µg/m³")}
                else:
                    required = {202: ("Home Assistant",), 203: ("Announcement Hub",),
                                205: ("90",), 206: ("AQI", "0–500")}
                for token in required.get(item["id"], ()):
                    assert token in digits(value).replace("Home-Assistant", "Home Assistant"), (family, locale, item["id"], token)
                memory[item["en"]][locale] = value
    assert seen == set(languages) - {"en"}, (family, set(languages) - {"en"} - seen)
    return memory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", choices=("pid", "inputs", "final", "all"), default="all")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--memory-output", type=Path)
    args = parser.parse_args()
    merged = {}
    for family in ("pid", "inputs", "final") if args.family == "all" else (args.family,):
        memory = build(family)
        merged.update(memory)
        rendered = json.dumps(memory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        destination = ROOT / ".github/localization" / ("native_residual_backend_" + family + ".json")
        if args.check:
            assert destination.read_text() == rendered, (family, "must be regenerated")
        else:
            destination.write_text(rendered)
        print(f"{'Verified' if args.check else 'Built'} {len(memory)} {family} explanations in all 38 languages")
    if args.memory_output:
        args.memory_output.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
