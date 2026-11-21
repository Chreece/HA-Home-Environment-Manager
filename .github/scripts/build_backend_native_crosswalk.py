"""Build reviewed native/backend help reuse and its required native conditions."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".github/translations/backend_native_crosswalk"
PACKAGE = "hem_native_backend_build"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/environment_manager")]
sys.modules[PACKAGE] = package
settings = importlib.import_module(PACKAGE + ".settings_help")
languages = importlib.import_module(PACKAGE + ".languages")


def build():
    sources = json.loads((DATA / "messages.json").read_text())
    authored = {source: {"en": source} for source in sources}
    seen = set()
    for path in sorted(DATA.glob("*.txt")):
        for line in path.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            locale, *values = line.split("|")
            assert locale not in seen and len(values) == len(sources), (path, locale)
            seen.add(locale)
            for source, value in zip(sources, values):
                assert value.strip(), (path, locale, source)
                authored[source][locale] = value
    assert seen == set(languages.SUPPORTED_LANGUAGE_TAGS) - {"en"}
    entries = json.loads((ROOT / ".github/localization/native_backend_help_crosswalk.json").read_text())["entries"]
    memory = {}
    for entry in entries:
        decision, source = entry["decision"], entry["source"]
        if decision == "exact_prefix_requires_suffix":
            base = entry["base_source"]
            suffix = entry["suffix"]
            assert base + " " + suffix == source
            assert settings.configuration_help(entry["setting_key"], "en") == base
            memory[source] = {
                locale: settings.configuration_help(entry["setting_key"], locale) + " " + authored[suffix][locale]
                for locale in languages.SUPPORTED_LANGUAGE_TAGS
            }
        elif decision == "reviewed_same_field":
            assert settings.configuration_help(entry["setting_key"], "en") == entry["base_source"]
            memory[source] = {
                locale: source if locale == "en" else settings.configuration_help(entry["setting_key"], locale)
                for locale in languages.SUPPORTED_LANGUAGE_TAGS
            }
        elif decision == "same_field_requires_unit":
            memory[source] = authored[source]
            assert all("°C" in value for value in memory[source].values())
    assert len(memory) == 9
    return memory


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--memory-output", type=Path)
    args = parser.parse_args()
    memory = build()
    rendered = json.dumps(memory, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    destination = ROOT / ".github/localization/native_residual_backend_crosswalk.json"
    if args.check:
        assert destination.read_text() == rendered, "Native/backend help crosswalk must be regenerated"
    else:
        destination.write_text(rendered)
    if args.memory_output:
        args.memory_output.write_text(rendered)
    print(f"{'Verified' if args.check else 'Built'} {len(memory)} native help messages in all 38 languages")
