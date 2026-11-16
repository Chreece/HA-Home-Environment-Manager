"""v0.7.2: sensor verification labels/help and per-room science state gates.

Read actual shipped catalogs, translations and frontend. No HA services,
sensor mutations, network access or device actuation.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
CC = ROOT / "custom_components/environment_manager"
CARD = (CC / "frontend/air-quality-advisor-card.js").read_text(encoding="utf-8")
NAMES = runpy.run_path(str(CC / "equipment_name_catalog.py"))["EQUIPMENT_TRANSLATED_NAMES"]
HELP = runpy.run_path(str(CC / "equipment_help.py"))["equipment_configuration_help"]

assert "data-hem-science072" in CARD
assert "_scienceOpen072" in CARD
assert "node?.isConnected" in CARD
assert "scienceKey=String(room.area_id)" in CARD
assert "HEM_SCIENCE_PERSISTENCE072_END" in CARD


def values_for(obj, key):
    if isinstance(obj, dict):
        for name, value in obj.items():
            if name == key:
                yield value
            yield from values_for(value, key)
    elif isinstance(obj, list):
        for item in obj:
            yield from values_for(item, key)


for locale, name_fragment, help_fragment in (
    ("en", "PM2.5 verified", "OFF (default)"),
    ("el", "Επιβεβαιωμένη μέτρηση PM2.5", "Ανενεργό"),
    ("de", "PM2.5-Messung bestätigt", "Aus (Standard)"),
):
    native = NAMES[locale]["sensor_verified"]
    assert name_fragment in native and "{channel}" in native
    details = HELP("sensor_verified", locale)
    assert "PM2.5" in details and help_fragment in details
    assert len(details.split("\n\n")) >= 4
    assert all(term in details for term in (
        ("ON:", "OFF (default)", "room's PM2.5 source")
        if locale == "en" else
        ("Ενεργό", "Ανενεργό", "δωματίου") if locale == "el"
        else ("Ein:", "Aus (Standard)", "Raum")
    ))
    json_file = CC / ("strings.json" if locale == "en" else f"translations/{locale}.json")
    source = json.loads(json_file.read_text(encoding="utf-8"))
    assert source["entity"]["switch"]["equipment_sensor_verified"]["name"] == native
    values = list(values_for(source, "device_sensor_verified"))
    assert len(values) == 4, (locale, len(values))
    assert all("PM2.5" in value for value in values), (locale, values)
    assert all("Required" not in value and "Απαιτείται" not in value and
               "Erforderlich" not in value for value in values)

# Mirror strings.json and translations/en.json for the canonical English UI.
english = json.loads((CC / "translations/en.json").read_text(encoding="utf-8"))
assert english["entity"]["switch"]["equipment_sensor_verified"]["name"] == NAMES["en"]["sensor_verified"]
assert all("PM2.5" in value for value in values_for(english, "device_sensor_verified"))

print("PASS v0.7.2 science expansion state + PM2.5 verification label/help EN EL DE")
