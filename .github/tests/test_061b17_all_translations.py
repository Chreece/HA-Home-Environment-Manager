"""Fail if any HEM-supported locale drops a native setting or dropdown state.

These fields drive both the categorized HEM device dialog and native Home
Assistant entity UIs. Stable option IDs must remain invariant for services.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANGUAGES = ROOT / "custom_components/environment_manager/translations"
FILES = sorted(LANGUAGES.glob("*.json"))
assert len(FILES) == 38, f"Expected 38 supported HEM translations: {len(FILES)}"


def strings(value, prefix=""):
    result = {}
    if isinstance(value, dict):
        for key, member in value.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(member, dict):
                result.update(strings(member, full))
            elif isinstance(member, str):
                result[full] = member
            else:
                raise AssertionError(f"Non-string translation leaf: {full}")
    return result


all_languages = {file.stem: strings(json.loads(file.read_text(encoding="utf-8")))
                 for file in FILES}
master = all_languages["en"]
canonical = set(master)
window_key = "entity.switch.equipment_announce_before_start.name"
required = (
    window_key,
    "entity.sensor.equipment_control_status.state.physical_device_startup_timeout",
    "entity.number.equipment_power_switch_cooldown_seconds.name",
    "entity.number.equipment_power_switch_cooldown_seconds.state_attributes.configuration_help.name",
    "entity.select.equipment_power_switch_entity.name",
    "entity.select.equipment_power_switch_entity.state_attributes.configuration_help.name",
)
profile = "entity.select.area_manual_profile.state."
method = "entity.select.equipment_control_mode.state."
presence = "entity.select.equipment_presence_requirement.state."
for lang, values in all_languages.items():
    missing = sorted(canonical - values.keys())
    extra = sorted(values.keys() - canonical)
    assert not missing and not extra, (
        f"{lang}: missing {len(missing)} keys: {missing[:25]}; "
        f"unexpected {len(extra)}: {extra[:25]}"
    )
    assert all(value.strip() for value in values.values()), f"{lang}: empty translation string"
    assert all(values.get(key) for key in required), f"{lang}: missing device control label"
    assert "{channel}" not in values[window_key], (
        f"{lang}: per-device toggle should not repeat the channel/device prefix"
    )
    assert len(values[window_key]) >= 20, f"{lang}: window-prompt label is incomplete"
    for group, states in (
        (profile, ("auto", "comfort", "home", "away", "sleep", "eco")),
        (method, ("existing", "automatic", "manual", "off", "pid")),
        (presence, ("always", "occupied", "absent")),
    ):
        assert all(values.get(group + state) for state in states), (
            f"{lang}: missing state labels for {group}"
        )
print("HEM_B17_ALL_38_LOCALES_AND_NATIVE_DROPDOWN_VALUES=PASS")
