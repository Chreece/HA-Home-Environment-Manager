"""Bundled presentation text, independent of Home Assistant and device control.

The generated catalog is imported with the integration's Python modules. A
lookup never opens a file, calls a service, or contacts a translation provider.
English source messages are stable keys shared with the card's build catalog.
"""
from __future__ import annotations

if __package__:
    from .backend_text_catalog import TEXT
    from .languages import SUPPORTED_LANGUAGE_TAGS, resolve_language
else:  # Pure catalog regression tests can also execute this file directly.
    import importlib
    from pathlib import Path
    import sys
    from types import ModuleType

    _package_name = "_hem_catalog_text"
    if _package_name not in sys.modules:
        _package = ModuleType(_package_name)
        _package.__path__ = [str(Path(__file__).parent)]
        sys.modules[_package_name] = _package
    TEXT = importlib.import_module(_package_name + ".backend_text_catalog").TEXT
    _languages = importlib.import_module(_package_name + ".languages")
    SUPPORTED_LANGUAGE_TAGS = _languages.SUPPORTED_LANGUAGE_TAGS
    resolve_language = _languages.resolve_language


_SUPPORTED = frozenset(SUPPORTED_LANGUAGE_TAGS)


def translated_text(source: str, language: str) -> str:
    """Resolve an exact message; preserve unknown future messages verbatim."""
    locale = language if isinstance(language, str) and language in _SUPPORTED else resolve_language(language)
    return TEXT.get(source, {}).get(locale, source)


def translated_variants(existing: dict[str, str]) -> dict[str, str]:
    """Resolve reviewed exact-source text, retaining unknown future variants."""
    source = existing["en"]
    reviewed = TEXT.get(source, {})
    return {
        locale: reviewed.get(locale) or existing.get(locale) or source
        for locale in SUPPORTED_LANGUAGE_TAGS
    }


def complete_catalog(catalog: dict) -> dict:
    """Complete locale-first nested catalogs from the static translation memory."""
    english = catalog["en"]

    def complete(source, existing, locale):
        if isinstance(source, dict):
            existing = existing if isinstance(existing, dict) else {}
            return {**existing, **{
                key: complete(value, existing.get(key), locale)
                for key, value in source.items()
            }}
        if isinstance(source, (tuple, list)):
            existing = existing if isinstance(existing, (tuple, list)) else ()
            return type(source)(complete(value, existing[index] if index < len(existing) else None, locale)
                                for index, value in enumerate(source))
        if isinstance(source, str):
            return existing if existing and existing != source else translated_text(source, locale)
        return source if existing is None else existing

    return {locale: complete(english, catalog.get(locale), locale)
            for locale in SUPPORTED_LANGUAGE_TAGS}


def presentation_languages(language: str) -> tuple[str, ...]:
    """Bound entity attributes while retaining an English key for card lookups.

    The card bundles the same translations for an independently selected UI
    language. Publishing every long translation on each entity state would
    unnecessarily multiply recorder and websocket payloads.
    """
    return tuple(dict.fromkeys(("en", "el", "de", resolve_language(language))))
