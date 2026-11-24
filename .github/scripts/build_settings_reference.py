"""Render the public settings directory using HEM's shipped English form and entity catalogs."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "custom_components/environment_manager"
DEST = ROOT / "docs/settings-reference.md"
DYNAMIC_NAMES = {
    "door_kind": "Interior or exterior door",
    "door_target_area": "Room on the other side of the door",
    "door_coordination": "Door coordination policy",
    "door_energy_meter": "Energy meter for the doorway policy",
    "equipment_door_closed_eco": "Use Eco with closed doors",
    "equipment_door_start_coordination": "Coordinate equipment starts across doors",
    "equipment_preset": "Native device preset",
    "equipment_fan_mode": "Native fan mode",
    "equipment_swing_mode": "Native vertical swing mode",
    "equipment_swing_horizontal_mode": "Native horizontal swing mode",
    "equipment_power_switch_cooldown_seconds": "Supply switch cooldown (seconds)",
}


def cell(value):
    return " ".join(value.split()).replace("|", r"\|")


def dynamic_name(key):
    if key in DYNAMIC_NAMES:
        return DYNAMIC_NAMES[key]
    prefix, profile, metric = key.removeprefix("equipment_").split("_")
    assert prefix == "target"
    return f"{profile.title()} profile · {metric} target"


def render():
    strings = json.loads((COMPONENT / "strings.json").read_text())
    policy = json.loads((COMPONENT / "frontend/settings-audit-policy.json").read_text())
    steps = strings["options"]["step"]
    lines = ["# HEM settings reference", "",
             "Open the gear in the card header for home settings or the gear beside a room name for its settings. Expand a device controller for its controls. Basic, Advanced and Expert are cumulative display levels. The registered appliance, selected sources and control permissions determine which items are available.", "",
             "[Home options](#home-options) · [Room sources](#room-sources) · [Native controls](#native-controls) · [Setup and options fields](#setup-and-options-fields) · [Configuration guide](advanced-configuration.md)", ""]
    for title, step, scope in [("Home options", "setup_general", "home"), ("Room sources", "edit_room", "room")]:
        lines.extend([f"## {title}", "", "| Setting | Level | What it controls |",
                      "| --- | --- | --- |"])
        for key, name in steps[step]["data"].items():
            level = policy[f"{scope}_option_levels"][key]
            help_text = steps[step]["data_description"].get(key, "")
            lines.append(f"| {cell(name)} | {level.title()} | {cell(help_text)} |")
        lines.append("")
    lines += ["## Native controls", "",
              "Look up the label or its translation key when comparing settings across installations. Home Assistant assigns entity IDs locally. Selectors with hardware-dependent choices show the options reported by the paired device. A button performs its named action when pressed.", ""]
    catalog = {key: (domain, entry) for domain in ("number", "select", "switch", "time", "button")
               for key, entry in strings["entity"][domain].items()}
    groups = {"Home": [], "Room": [], "Appliance": [], "Doors": [], "Shading": []}
    for key, level in policy["native_levels"].items():
        if key in catalog:
            domain, entry = catalog[key]
            name = entry["name"].replace("{channel}", "")
            choices = ", ".join(entry.get("state", {}).values())
        else:
            name, domain, choices = dynamic_name(key), "", ""
        group = next((title for prefix, title in (("area_", "Room"), ("equipment_", "Appliance"),
                      ("door_", "Doors"), ("shade_", "Shading")) if key.startswith(prefix)), "Home")
        groups[group].append((name, level, domain, choices, key))
    for title, rows in groups.items():
        if not rows:
            continue
        lines.extend([f"### {title}", "", "| Setting | Level | Control or choices | Translation key |",
                      "| --- | --- | --- | --- |"])
        for name, level, domain, choices, key in sorted(rows):
            lines.append(f"| {cell(name)} | {level.title()} | {cell(choices or domain or 'Device or context dependent')} | `{key}` |")
        lines.append("")
    lines += ["## Setup and options fields", "",
              "This index includes the labels in Home Assistant's initial setup and options catalogs, including conditional and older forms. Current availability depends on the setup path. The card's home and room tables above correspond to its active source editors.", ""]
    for section in ("config", "options"):
        for key, step in strings[section]["step"].items():
            fields = step.get("data", {})
            if fields:
                lines += [f"**{section.title()} / {cell(step.get('title', key))}** (`{key}`)", "",
                          ", ".join(f"{cell(label)} (`{field}`)" for field, label in fields.items()), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    if parser.parse_args().check:
        assert DEST.read_text() == render(), "Regenerate the settings reference"
    else:
        DEST.write_text(render())
