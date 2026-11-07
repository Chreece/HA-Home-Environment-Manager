"""Announcement choices and separate, compatible TTS provider language tags."""
from __future__ import annotations

from typing import Any

from .languages import (
    LANGUAGE_OPTIONS, announcement_language, normalize_announcement_language,
)

_AUTO_LABELS = {
    'en': 'Home Assistant language (default)',
    'de': 'Home-Assistant-Sprache (Standard)',
    'el': 'Γλώσσα Home Assistant (προεπιλογή)',
    'fr': 'Langue de Home Assistant (par défaut)',
    'es': 'Idioma de Home Assistant (predeterminado)',
    'it': 'Lingua di Home Assistant (predefinita)',
    'nl': 'Taal van Home Assistant (standaard)',
    'pt': 'Idioma do Home Assistant (predefinido)',
    'pt-BR': 'Idioma do Home Assistant (padrão)',
    'pl': 'Język Home Assistant (domyślny)',
    'ru': 'Язык Home Assistant (по умолчанию)',
    'uk': 'Мова Home Assistant (типово)',
    'tr': 'Home Assistant dili (varsayılan)',
    'cs': 'Jazyk Home Assistant (výchozí)',
    'sk': 'Jazyk Home Assistant (predvolený)',
    'hu': 'Home Assistant nyelve (alapértelmezett)',
    'ro': 'Limba Home Assistant (implicită)',
    'bg': 'Език на Home Assistant (по подразбиране)',
    'hr': 'Jezik Home Assistanta (zadano)',
    'sr': 'Језик Home Assistant-а (подразумевани)',
    'sv': 'Home Assistant-språk (standard)',
    'nb': 'Home Assistant-språk (standard)',
    'da': 'Home Assistant-sprog (standard)',
    'fi': 'Home Assistantin kieli (oletus)',
    'id': 'Bahasa Home Assistant (bawaan)',
    'vi': 'Ngôn ngữ Home Assistant (mặc định)',
    'th': 'ภาษา Home Assistant (ค่าเริ่มต้น)',
    'hi': 'Home Assistant की भाषा (डिफ़ॉल्ट)',
    'zh-Hans': 'Home Assistant 语言（默认）',
    'zh-Hant': 'Home Assistant 語言（預設）',
    'ja': 'Home Assistant の言語（既定）',
    'ko': 'Home Assistant 언어 (기본값)',
    'ar': 'لغة Home Assistant (الافتراضية)',
    'he': 'שפת Home Assistant (ברירת מחדל)',
    'fa': 'زبان Home Assistant (پیش\u200cفرض)',
    'bn': 'Home Assistant-এর ভাষা (ডিফল্ট)',
    'ur': 'Home Assistant کی زبان (پہلے سے طے شدہ)',
    'ta': 'Home Assistant மொழி (இயல்புநிலை)',
}


def _canonical(value: Any) -> str:
    return str(value or "").strip().replace("_", "-").casefold()


def _provider_entity(hass: Any, entity_id: str | None):
    if not isinstance(entity_id, str) or not entity_id.startswith("tts."):
        return None
    try:
        from homeassistant.components.tts.const import DATA_COMPONENT
        component = hass.data.get(DATA_COMPONENT)
        if component is not None:
            entity = component.get_entity(entity_id)
            if entity is not None:
                return entity
    except Exception:
        pass
    return None


def provider_languages(hass: Any, entity_id: str | None) -> tuple[tuple[str, ...], str | None]:
    """Read entity capabilities; keep exact provider spellings for service calls."""
    entity = _provider_entity(hass, entity_id)
    languages = None
    default = None
    if entity is not None:
        try:
            languages = list(entity.supported_languages)
        except (AttributeError, TypeError):
            languages = None
        try:
            default = entity.default_language
        except (AttributeError, TypeError):
            default = None
    if not languages and isinstance(entity_id, str):
        state = hass.states.get(entity_id)
        attrs = state.attributes if state is not None else {}
        raw = attrs.get("supported_languages")
        if isinstance(raw, (list, tuple)):
            languages = list(raw)
        default = default or attrs.get("default_language")
    cleaned = tuple(dict.fromkeys(
        item for item in (languages or ()) if isinstance(item, str) and item.strip()
    ))
    return cleaned, (default if isinstance(default, str) and default.strip() else None)


def announcement_language_options(hass: Any) -> list[dict[str, str]]:
    """All HEM languages; provider capabilities never restrict text choices."""
    ui_language = announcement_language(hass)
    return [
        {"value": "auto", "label": _AUTO_LABELS.get(ui_language, _AUTO_LABELS["en"])},
        *(dict(option) for option in LANGUAGE_OPTIONS),
    ]


def language_options(hass: Any, entity_id: str | None = None) -> list[dict[str, str]]:
    """Compatibility API for the shared announcement-language setting."""
    return announcement_language_options(hass)


def preferred_language(hass: Any, entity_id: str | None, saved: str | None) -> str:
    """Show the saved announcement choice without substituting a provider default."""
    return normalize_announcement_language(saved) or "auto"


def supports_language(hass: Any, entity_id: str | None, value: str) -> bool:
    """Validate supported announcement languages, including old provider tags."""
    return normalize_announcement_language(value) is not None


def tts_language(hass: Any, entity_id: str | None, selected: str | None = "auto", *,
                 text_language: str | None = None) -> str:
    """Use a provider tag for this language, never another language's default.

    Preserve an exact legacy regional selection where possible, then match
    translated locale meanings. Portuguese variants and Chinese scripts are
    distinct. If capabilities offer no match, send the resolved language
    explicitly so the provider can reject it through existing delivery error
    handling instead of silently speaking with an unrelated default voice.
    A caller that already built text keeps that locale if HA changes while
    an AI rewrite or another delivery channel is awaiting a response.
    """
    requested = selected
    if requested is None or str(requested).strip().casefold() == "auto":
        requested = getattr(getattr(hass, "config", None), "language", "en")
    wanted = text_language or announcement_language(hass, selected)
    supported, default = provider_languages(hass, entity_id)
    exact = next((tag for tag in supported if _canonical(tag) == _canonical(requested)
                  and normalize_announcement_language(tag) == wanted), None)
    if exact is not None:
        return exact
    # Prefer the provider's base tag to an arbitrary regional variant.
    exact = next((tag for tag in supported if _canonical(tag) == _canonical(wanted)), None)
    if exact is not None:
        return exact
    # A default regional voice is useful only within the chosen language.
    compatible_default = next((tag for tag in supported
                               if _canonical(tag) == _canonical(default)
                               and normalize_announcement_language(tag) == wanted), None)
    if compatible_default is not None:
        return compatible_default
    return next((tag for tag in supported
                 if normalize_announcement_language(tag) == wanted), wanted)
