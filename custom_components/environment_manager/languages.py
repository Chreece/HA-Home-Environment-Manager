"""Supported Home Assistant UI and announcement languages.

A locale fallback is explicit: region variants map to their language unless
Portuguese or Chinese script variants are separately translated.
"""
from __future__ import annotations

import re
from typing import Any

from .locale_pack_europe import LOCALES as _EUROPE
from .locale_pack_europe2 import LOCALES as _EUROPE2
from .locale_pack_global import LOCALES as _GLOBAL

EXTRA_LOCALES = {**_EUROPE, **_EUROPE2, **_GLOBAL}
BASE_NATIVE = {
    "en": "English",
    "de": "Deutsch",
    "el": "Ελληνικά",
    "fr": "Français",
    "es": "Español",
}
SUPPORTED_LANGUAGE_TAGS = (*BASE_NATIVE, *EXTRA_LOCALES)
NATIVE_NAMES = {**BASE_NATIVE, **{tag: loc["native"] for tag, loc in EXTRA_LOCALES.items()}}
LANGUAGE_OPTIONS = tuple(
    {"value": lang, "label": NATIVE_NAMES[lang]}
    for lang in sorted(SUPPORTED_LANGUAGE_TAGS, key=lambda tag: NATIVE_NAMES[tag].casefold())
)
_RTL = frozenset(tag for tag, loc in EXTRA_LOCALES.items() if loc.get("rtl"))


def normalize_announcement_language(value: Any) -> str | None:
    """Validate a choice, preserving supported script and regional meanings.

    Older versions saved provider tags such as ``en_GB`` or ``de-DE``.
    They still select the same translated language, independently of which
    TTS provider happens to be installed. Unknown languages are not English
    selections: callers validating user input must reject them.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().replace("_", "-").casefold()
    if text == "auto":
        return "auto"
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*", text):
        return None
    folded = {tag.casefold(): tag for tag in SUPPORTED_LANGUAGE_TAGS}
    if text in folded:
        return folded[text]
    parts = text.split("-")
    root = parts[0]
    if root == "zh":
        # An explicit script is authoritative even when the region differs.
        if "hant" in parts:
            return "zh-Hant"
        if "hans" in parts:
            return "zh-Hans"
        return "zh-Hant" if any(part in ("tw", "hk", "mo") for part in parts) else "zh-Hans"
    if root == "pt":
        return "pt-BR" if "br" in parts else "pt"
    if root == "no":
        root = "nb"
    return folded.get(root)


def announcement_language(hass: Any, selected: str | None = "auto") -> str:
    """Resolve the announcement language at send time, including HA default."""
    if selected is None or str(selected).strip().casefold() == "auto":
        selected = getattr(getattr(hass, "config", None), "language", "en")
    language = normalize_announcement_language(selected)
    return language if language not in (None, "auto") else "en"


def resolve_language(language: str | None) -> str:
    """Resolve HA BCP47 language tags without collapsing script distinctions."""
    text = str(language or "en").strip().replace("_", "-").lower()
    if text in ("", "auto"):
        return "en"
    folded = {tag.lower(): tag for tag in SUPPORTED_LANGUAGE_TAGS}
    if text in folded:
        return folded[text]
    if text.startswith("zh"):
        if any(token in text for token in ("hant", "-tw", "-hk", "-mo")):
            return "zh-Hant"
        return "zh-Hans"
    if text.startswith("pt-"):
        return "pt-BR" if text == "pt-br" else "pt"
    root = text.split("-", 1)[0]
    if root == "no":
        return "nb"
    return folded.get(root, "en")

RTL_LANGUAGES = _RTL
