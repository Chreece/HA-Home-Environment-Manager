"""Pre-movement shade notices routed through existing announcement choices.

A Home-level opt-in is separate from window-airing announcements. The text is
a factual movement notice, never a request for AI to operate covers.
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
from .hub_delivery import hub_available, make_hub_payload, async_submit_hub, hub_ai_options
from .languages import announcement_language
from .tts_languages import tts_language
from .announcement_text import SHADE_MESSAGES

MESSAGES = SHADE_MESSAGES


def _language(manager: Any) -> str:
    return announcement_language(manager.hass, manager.settings.get(CONF_LANGUAGE, "auto"))


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
    entity_id: str | None = None, required: bool | None = None,
) -> bool:
    """Announce ONE room action before movement. Never send cover commands."""
    config = manager.settings
    announce = config.get(CONF_SHADE_ANNOUNCE) is True if required is None else required
    if not announce:
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
    if entity_id is not None:
        # A per-cover permission must not announce that ALL room covers will move.
        source = manager.hass.states.get(entity_id)
        name = getattr(source, "name", None) or entity_id
        message = MESSAGES[lang][f"{action}_cover"].format(
            room=area_record.name, cover=name,
        )
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
            language=lang,
            use_ai=False, agent_id="default",
        )
        payload.update(hub_ai_options(config))
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
                    {"media_player_entity_id": players, "message": message,
                     "language": tts_language(hass, engine, config.get(CONF_LANGUAGE, "auto"),
                                              text_language=lang)},
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
