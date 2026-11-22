"""Reproduce the HEM card's exact setting-level classification.

The catalog also lists native Home Assistant flow labels for navigation. Those
flows are not filtered by the card, and a catalog entry does not prove that a
particular device exposes a control. Dynamic card identities have explicit
source references rather than guesses from translated labels or entity names.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "custom_components/environment_manager"
POLICY = SOURCE / "frontend/settings-audit-policy.json"
DOMAINS = ("number", "select", "switch", "time", "button")
LEVELS = ("basic", "advanced", "expert")
ROOM_SOURCE_FIELDS = (
    "windows", "door_sensors", "air_quality", "temperature", "humidity",
    "climate_devices", "shades", "occupancy_sensors",
)


def inventory():
    catalog = json.loads((SOURCE / "strings.json").read_text())
    policy = json.loads(POLICY.read_text())
    assert policy["version"] == 2 and tuple(policy["levels"]) == LEVELS
    native = policy["native_levels"]
    home = policy["home_option_levels"]
    room = policy["room_option_levels"]
    dynamic = policy["dynamic_native"]
    static = {key for domain in DOMAINS for key in catalog["entity"].get(domain, {})}
    # Every known identity has an explicit classification. New fields stay
    # visible at Basic in the card until this audit is updated.
    assert set(native) == static | set(dynamic), "Native identity inventory differs"
    assert set(home) == set(catalog["options"]["step"]["setup_general"]["data"])
    assert set(room) == set(ROOM_SOURCE_FIELDS)
    for mapping in (native, home, room):
        assert set(mapping.values()) <= set(LEVELS), "Unknown settings level"
    for kind, mapping in (("native", native), ("home_options", home), ("room_options", room)):
        assert all(mapping.get(key) == "basic" for key in policy["always_basic"][kind]), (
            "Essential setup, control and protection settings must remain Basic", kind,
        )
    for key in ("equipment_kp", "equipment_ki", "equipment_kd"):
        assert native[key] == "advanced", "Manual PID gains belong in Advanced"
    for key in ("equipment_pid_process_gain", "equipment_pid_time_constant_minutes",
                "equipment_pid_dead_time_minutes", "equipment_pid_lambda_minutes",
                "equipment_pid_apply_calibration", "equipment_pid_apply_fan_capacity"):
        assert native[key] == "expert", "Model tuning and its apply actions belong together"

    paths = {}
    for path in SOURCE.glob("*.py"):
        if (path.name.endswith("_catalog.py") or path.name.endswith("_help.py")
                or path.name == "setting_option_explanations.py"):
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                paths.setdefault(node.value, set()).add(f"{path.relative_to(ROOT)}:{node.lineno}")

    records = []
    for domain in DOMAINS:
        for key, values in catalog["entity"].get(domain, {}).items():
            records.append({
                "kind": "native_catalog", "platform": domain, "key": key,
                "name": values.get("name", key), "presentation": native[key],
                "same_property_options_alias": policy["home_aliases"].get(key),
                "catalog_path": f"strings.json/entity/{domain}/{key}",
                "literal_references": sorted(paths.get(key, ()))[:6],
                "consumer_status": "capability_and_registry_dependent_native_control",
            })
    for section in ("config", "options"):
        for step, values in catalog.get(section, {}).get("step", {}).items():
            for key, name in values.get("data", {}).items():
                # These are the only native Options forms adapted by the card.
                # Initial setup and historical Options pages keep their own UI.
                adapted = section == "options" and step in ("setup_general", "edit_room")
                mapping = home if step == "setup_general" else room
                records.append({
                    "kind": "form_catalog", "surface": section, "step": step,
                    "key": key, "name": name,
                    "presentation": mapping.get(key, "basic") if adapted else "native_flow_unchanged",
                    "catalog_path": f"strings.json/{section}/step/{step}/data/{key}",
                    "literal_references": sorted(paths.get(key, ()))[:6],
                    "consumer_status": "card_adapts_options_form" if adapted
                    else "catalog_only_step_reachability_not_proven",
                })
    for key, definition in dynamic.items():
        kind = ("dynamic_door" if key.startswith("door_") else
                "dynamic_mode_target" if key.startswith("equipment_target_") else
                "dynamic_device")
        record = {
            "kind": kind, "key": key, "presentation": native[key],
            "definition": f"custom_components/environment_manager/{definition}",
        }
        if kind == "dynamic_door":
            record["consumer"] = "custom_components/environment_manager/door_settings.py:async_update"
        elif kind == "dynamic_mode_target":
            record["consumer"] = "custom_components/environment_manager/equipment_mode_settings.py:resolve_settings"
        records.append(record)
    # Room door selection is generated in the Options schema and does not
    # have a static strings.json label entry in every source locale.
    for key, level in room.items():
        records.append({
            "kind": "card_room_source", "key": key, "presentation": level,
            "definition": "custom_components/environment_manager/reconfigure_rooms.py:async_step_room_settings",
        })

    text = (SOURCE / "frontend/home-environment-manager-card.js").read_text()
    start = text.index("const auditPolicyB8=") + len("const auditPolicyB8=")
    embedded, _ = json.JSONDecoder().raw_decode(text[start:])
    assert embedded == policy, "Embedded UI policy and audit source differ"
    return {
        "baseline": "cbdf94b1db46d477d7ba24dc575cd37b70363554",
        "scope": "Cumulative Basic, Advanced and Expert presentation in the HEM card",
        "limitations": [
            "Catalog entries are not counts of controls shown on any device.",
            "Literal references are navigation aids, not proof of use or non-use.",
            "Only the card's adapted Options forms are filtered; native Home Assistant setup and Options flows are unchanged.",
            "Native controls still depend on actual capabilities, registry ownership and current source selection.",
            "Visibility does not change saved values, permissions, validation, calibration or physical safety rules.",
        ],
        "counts": dict(Counter(record["kind"] for record in records)),
        "level_counts": {
            "native_identities": dict(Counter(native.values())),
            "home_option_keys": dict(Counter(home.values())),
            "room_source_groups": dict(Counter(room.values())),
        },
        "policy": policy, "settings": records,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = inventory()
    output = ROOT / "docs/settings-inventory.json"
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        assert output.read_text() == encoded, "Regenerate settings inventory after changing catalog or code references"
    else:
        output.parent.mkdir(exist_ok=True)
        output.write_text(encoded)
    print("PASS: settings inventory", result["counts"], "levels", result["level_counts"])
