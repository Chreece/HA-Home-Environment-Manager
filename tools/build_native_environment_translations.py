#!/usr/bin/env python3
"""Build complete sensor/environment form explanations from reviewed locale rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / ".github/translations"
OUTPUT = ROOT / ".github/localization/native_residual_environment.json"
TOKENS = {
    0: ("°C/°F",), 3: ("3", "5"), 4: ("1–100", "0–5", "HEM"),
    6: ("AQI", "EPA", "0-500", "Home Assistant"),
    9: ("Home Environment Manager",), 11: ("CADR",), 12: ("HCHO", "eCO₂"),
    13: ("100", "Bq/m³", "300"), 14: ("ISO 7730",), 15: ("ISO 7730",),
    34: ("m³", "CADR"), 35: ("m³/h",), 36: ("CO₂", "NDIR", "eCO₂", "VOC"),
    37: ("VOC",), 38: ("HCHO", "30", "100", "µg/m³"), 39: ("LAeq",),
    40: ("EDI", "lux"), 41: ("m/s",), 42: ("met", "1.0", "1.2"),
    43: ("clo", "0.5", "1.0"),
    27: ("AQI", "EPA", "EEA", "0-500"), 28: ("AQI",),
    32: ("Home Assistant",), 49: ("PM2.5", "µg/m³", "AQI"),
    52: ("PM2.5", "µg/m³", "AQI", "eCO₂", "VOC"),
    75: ("Announcement Hub",), 76: ("HA",), 80: ("Bq/m³", "pCi/L"),
    81: ("HCHO", "µg/m³", "mg/m³", "VOC"), 82: ("dB(A)",),
    83: ("lux",), 84: ("°C", "PMV", "PPD"), 85: ("m/s", "PMV", "PPD"),
    152: ("Home Assistant",), 200: ("Home Assistant",),
}


def build() -> dict:
    manifest = json.loads((AUTHORING / "native_environment_sources.json").read_text())
    sources = {entry["index"]: entry["source"] for entry in manifest["sources"]}
    locales = {path.stem for path in (ROOT / "custom_components/environment_manager/translations").glob("*.json")} - {"en"}
    messages = {text: {"en": text} for text in sources.values()}
    covered = set()
    for group, indices in manifest["groups"].items():
        assert not covered.intersection(indices), f"Repeated source group: {group}"
        covered.update(indices)
        path = AUTHORING / "native_environment_locales" / f"{group}.txt"
        seen = set()
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            locale, *values = line.split("|")
            assert locale in locales and locale not in seen, (path, locale)
            seen.add(locale)
            assert len(values) == len(indices), (path, locale, len(values))
            for index, text in zip(indices, values):
                source = sources[index]
                assert text.strip() and text != source, (index, locale)
                assert set(re.findall(r"\{[^{}]+\}", text)) == set(re.findall(r"\{[^{}]+\}", source)), (index, locale, "placeholders")
                for token in TOKENS.get(index, ()):
                    candidate = text.replace("Home-Assistant", "Home Assistant")
                    assert token.casefold() in candidate.casefold(), (index, locale, token)
                messages[source][locale] = text
        assert seen == locales, (path, sorted(locales - seen))
    # The three input-picker descriptions have an identical complete body and
    # differ only in a standalone topic prefix. Expand that exact family without
    # translating a generic substitute or changing the source's conditions.
    for family in manifest.get("prefix_families", []):
        base = family["base"]
        labels = family["labels"]
        for index in family["indices"]:
            assert index not in covered, (index, "repeated prefix variant")
            covered.add(index)
            for locale in ["en", *sorted(locales)]:
                base_label, *variant_labels = labels[locale]
                label = variant_labels[family["indices"].index(index)]
                base_text = messages[sources[base]][locale]
                assert base_text.startswith(base_label), (base, locale, "topic prefix")
                translated = label + base_text[len(base_label):]
                if locale == "en":
                    assert translated == sources[index], (index, "different source body")
                messages[sources[index]][locale] = translated
    assert covered == set(sources), "Every declared source needs one locale group"
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    messages = build()
    text = json.dumps(messages, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        assert OUTPUT.read_text() == text, "Environment form catalog is stale; rebuild it"
    else:
        OUTPUT.write_text(text)
    if args.export:
        args.export.write_text(text)
    print(f"Environment form catalog: {len(messages)} complete sources × 38 languages")


if __name__ == "__main__":
    main()
