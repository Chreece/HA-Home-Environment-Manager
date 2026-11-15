"""B22: all fixed native selector choices have useful, localized explanations.

Audit from shipped production metadata and Home Assistant catalogs, not a
mocked list of settings. Dynamic source/vendor options are purpose-described
by their owning entity; they must never receive invented generic semantics.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "custom_components/environment_manager"
catalog = json.loads((SRC / "strings.json").read_text(encoding="utf-8"))
descriptions = runpy.run_path(str(SRC / "setting_option_explanations.py"))
option_help_locales = descriptions["option_help_locales"]

# One retired PID adaptation selector remains in legacy translations solely
# for compatibility; it is not exposed by the current device menus.
retired = {"equipment_pid_adaptation_mode"}
active = {
    key: tuple(values.get("state", {}))
    for key, values in catalog["entity"]["select"].items()
    if values.get("state") and key not in retired
}
assert len(active) >= 18, "Unexpected removal of fixed option catalog entries"

expected = {
    **active,
    "equipment_door_start_coordination": ("inherit", "observe", "conflicts", "shared"),
    "door_kind": ("interior", "fire", "exterior"),
    "door_coordination": ("observe", "conflicts", "shared"),
}
for key, options in expected.items():
    mapped = option_help_locales(key)
    assert set(mapped) == {"en", "el", "de"}, (key, mapped)
    for locale, descriptions_for_locale in mapped.items():
        assert set(descriptions_for_locale) == set(options), (locale, key, options)
        for value, explanation in descriptions_for_locale.items():
            assert isinstance(explanation, str) and len(explanation.strip()) >= 40, (
                locale, key, value, explanation,
            )
            assert explanation.strip() != value, (locale, key, value)
            assert "<script" not in explanation.lower(), (locale, key, value)

# Every legacy and current Form entry now has purpose text in the
# canonical English and native Greek/German catalogs, including room navigation.
for source in ("strings.json", "translations/en.json", "translations/el.json", "translations/de.json"):
    translated = json.loads((SRC / source).read_text(encoding="utf-8"))
    for family in ("config", "options"):
        for step, fields in translated[family].get("step", {}).items():
            for key in fields.get("data", {}):
                text = fields.get("data_description", {}).get(key)
                assert isinstance(text, str) and len(text.strip()) >= 20, (
                    source, family, step, key,
                )

# The real HA metadata bridge publishes locale-specific option help while
# retaining the existing server-value IDs and all native option validators.
for file, marker in (
    ("settings_help.py", '"option_help_locales"'),
    ("select.py", '"option_help_locales"'),
    ("door_entities.py", '"option_help_locales"'),
):
    assert marker in (SRC / file).read_text(encoding="utf-8"), file

door = runpy.run_path(str(SRC / "equipment_door_policy.py"))["WORDS"]
assert door["el"]["inherit"] == "Χρήση κανόνων κάθε πόρτας"
for locale, prefix in (("en", "What it does:"), ("el", "Τι κάνει:"), ("de", "Wirkung:")):
    for topic in ("eco_help", "coord_help"):
        assert prefix in door[locale][topic] and "\n\n" in door[locale][topic]

assert option_help_locales("nonexistent_future_field") == {}
print("PASS: complete fixed native choices in EN/EL/DE; legacy navigation, "
      "per-device door purpose, native metadata and form explanations")
