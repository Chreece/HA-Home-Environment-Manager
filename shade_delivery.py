"""Pre-movement shade notices routed through existing announcement choices.

A Home-level opt-in is separate from window-airing announcements. The text is
a fixed safety statement, never AI rewritten or a request to operate covers.
A queue acceptance is not proof of audible playback; caller waits a grace
period after accepted notice and fully revalidates before any cover movement.

If notice delivery is opted in but cannot be submitted, NO cover moves.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .const import (
    CONF_AUTO_NOTIFY, CONF_AUTO_TTS, CONF_HUB, CONF_LANGUAGE, CONF_NOTIFY_TARGETS,
    CONF_MEDIA_PLAYERS, CONF_TTS_ENGINE, CONF_SHADE_ANNOUNCE,
)
from .hub_delivery import hub_available, make_hub_payload, async_submit_hub

MESSAGES = {
    "en": {
        "title": "Window shading",
        "close": "The window shades in {room} will close shortly to reduce solar heating.",
        "open": "The window shades in {room} will open shortly because shading is no longer needed.",
    },
    "el": {
        "title": "Σκίαση παραθύρων",
        "close": "Τα σκίαστρα στο {room} θα κλείσουν σύντομα για να μειώσουν τη ζέστη από τον ήλιο.",
        "open": "Τα σκίαστρα στο {room} θα ανοίξουν σύντομα επειδή δεν χρειάζεται πλέον σκίαση.",
    },
    "de": {
        "title": "Fensterbeschattung",
        "close": "Die Fensterrollos in {room} werden gleich geschlossen, um die Sonneneinstrahlung zu verringern.",
        "open": "Die Fensterrollos in {room} werden gleich geöffnet, da die Beschattung nicht mehr benötigt wird.",
    },
    "fr": {
        "title": "Protection solaire",
        "close": "Les stores de {room} vont bientôt se fermer pour réduire la chaleur solaire.",
        "open": "Les stores de {room} vont bientôt s'ouvrir car la protection solaire n'est plus nécessaire.",
    },
    "es": {
        "title": "Protección solar",
        "close": "Las persianas de {room} se cerrarán pronto para reducir el calor del sol.",
        "open": "Las persianas de {room} se abrirán pronto porque ya no hace falta protección solar.",
    },
}


def _language(manager: Any) -> str:
    configured = manager.settings.get(CONF_LANGUAGE, "auto")
    if callable(getattr(manager, "get_language", None)):
        configured = manager.get_language(None)
    elif configured == "auto":
        configured = getattr(getattr(manager.hass, "config", None), "language", "en")
    locale = str(configured).replace("_", "-").lower().split("-")[0]
    return locale if locale in MESSAGES else "en"


def _targets(manager: Any, entities: Any, room: str) -> list[str]:
    if not isinstance(entities, list):
        return []
    if callable(getattr(manager, "_targets_in_room", None)):
        return manager._targets_in_room(entities, room)
    from .discovery import entity_area
    return [item for item in entities if isinstance(item, str)
            and (entity_area(manager.hass, item) in (None, room))]


async def async_announce_before_move(
    manager: Any, *, area: str, action: str,
) -> bool:
    """Announce ONE room action before movement. Never send cover commands."""
    config = manager.settings
    if config.get(CONF_SHADE_ANNOUNCE) is not True:
        return True
    from homeassistant.helpers import area_registry as ar

    if action not in ("close", "open"):
        return False
    area_record = ar.async_get(manager.hass).async_get_area(area)
    if area_record is None:
        return False
    lang = _language(manager)
    title = MESSAGES[lang]["title"]
    message = MESSAGES[lang][action].format(room=area_record.name)
    speech = bool(config.get(CONF_AUTO_TTS))
    visual = bool(config.get(CONF_AUTO_NOTIFY)) or not speech
    prefer_hub = config.get(CONF_HUB) is True
    hass = manager.hass

    # Respect Hub delivery ownership: a live Hub rejection cannot trigger
    # a duplicate native notification.
    if prefer_hub and hub_available(hass):
        notice = SimpleNamespace(area_name=area_record.name, action=action)
        payload = make_hub_payload(
            notice, title, message, speech=speech, visual=visual,
            language=str(config.get(CONF_LANGUAGE, "auto")),
            use_ai=False, agent_id="default",
        )
        return await async_submit_hub(hass, payload)

    result = False
    if visual:
        receivers = _targets(manager, config.get(CONF_NOTIFY_TARGETS, []), area)
        if receivers and hass.services.has_service("notify", "send_message"):
            try:
                await hass.services.async_call("notify", "send_message",
                    {"title": title, "message": message},
                    target={"entity_id": receivers}, blocking=True)
                result = True
            except Exception:
                pass
    if speech:
        engine = config.get(CONF_TTS_ENGINE)
        players = _targets(manager, config.get(CONF_MEDIA_PLAYERS, []), area)
        if engine and players and hass.services.has_service("tts", "speak"):
            try:
                await hass.services.async_call(
                    "tts", "speak",
                    {"media_player_entity_id": players, "message": message},
                    target={"entity_id": engine}, blocking=True,
                )
                result = True
            except Exception:
                pass
    if not result and visual and hass.services.has_service("persistent_notification", "create"):
        try:
            await hass.services.async_call(
                "persistent_notification", "create",
                {"title": title, "message": message,
                 "notification_id": f"environment_manager_shades_{area}_{action}"},
                blocking=True,
            )
            result = True
        except Exception:
            return False
    return result
