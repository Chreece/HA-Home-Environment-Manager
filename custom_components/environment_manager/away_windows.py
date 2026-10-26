"""Opt-in, verified all-away notification for still-open physical windows.

Departure is a verified HOME -> AWAY transition, not a guessed startup state.
Only included, live native window contacts count; covers are not contacts.
Once each episode's opened contacts are reported, ordinary polling does not
repeat the alert. New openings can produce a separate announcement.
No physical window/cover/HVAC action exists in this module.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

from .const import (
    CONF_AREAS, CONF_EXCLUDED_WINDOWS, CONF_LANGUAGE, CONF_NOTIFY_TARGETS,
    CONF_OCCUPANCY_GLOBAL, CONF_AWAY_WINDOWS_ALERT,
    CONF_AWAY_WINDOWS_PERSONS, CONF_AWAY_WINDOWS_DELIVERY, DOMAIN,
)
from .discovery import entity_area, is_window
from .hub_delivery import hub_installed, hub_available, async_submit_hub, async_system_notification
from .occupancy_policy import _bool_presence, home_presence
from .room_sources import native, selected

_LOGGER = logging.getLogger(__name__)
DEPARTURE_STABLE_SECONDS = 60
RETRY_SECONDS = 300

# Mobile / Watch / Tablet are explicit Announcement Hub per-person slots.
# "phone TTS" specifically uses the companion app speech channel, never a
# room player, whole-house TTS provider, or generic Snapcast client.
DELIVERY_CHANNELS = {
    "mobile_notification": ("mobile", "notification"),
    "mobile_tts": ("mobile", "companion_tts"),
    "watch_notification": ("watch", "notification"),
    "watch_tts": ("watch", "companion_tts"),
    "tablet_notification": ("tablet", "notification"),
    "tablet_tts": ("tablet", "companion_tts"),
    "other_notification": ("other", "notification"),
    "other_tts": ("other", "companion_tts"),
}
DEFAULT_DELIVERY = ("mobile_notification",)

MESSAGES = {
    "en": ("Windows left open", "Everyone has left home, but these windows are still open: {windows}. Please close them."),
    "el": ("Ανοιχτά παράθυρα ενώ λείπουν όλοι", "Όλοι έχουν φύγει από το σπίτι, αλλά τα παρακάτω παράθυρα παραμένουν ανοιχτά: {windows}. Παρακαλώ κλείστε τα."),
    "de": ("Offene Fenster bei Abwesenheit", "Alle haben das Haus verlassen, aber diese Fenster sind noch offen: {windows}. Bitte schließt sie."),
    "fr": ("Fenêtres ouvertes en votre absence", "Tout le monde a quitté la maison, mais ces fenêtres sont encore ouvertes : {windows}. Veuillez les fermer."),
    "es": ("Ventanas abiertas fuera de casa", "Todos han salido de casa, pero estas ventanas siguen abiertas: {windows}. Por favor, ciérralas."),
    "it": ("Finestre aperte quando non c'è nessuno", "Tutti sono usciti, ma queste finestre sono ancora aperte: {windows}. Per favore chiudetele."),
}


def configured_recipients(hass: Any, settings: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Return only currently existing explicitly selected HA person identities."""
    available = {state.entity_id for state in hass.states.async_all("person")}
    raw_people = settings.get(CONF_AWAY_WINDOWS_PERSONS, [])
    raw_channels = settings.get(CONF_AWAY_WINDOWS_DELIVERY, DEFAULT_DELIVERY)
    people = (list(dict.fromkeys(raw_people))
              if isinstance(raw_people, list) and all(isinstance(v, str) for v in raw_people)
              else [])
    channels = (list(dict.fromkeys(raw_channels))
                if isinstance(raw_channels, list) and all(isinstance(v, str) for v in raw_channels)
                else list(DEFAULT_DELIVERY) if isinstance(raw_channels, tuple) else [])
    if any(p not in available for p in people) or any(c not in DELIVERY_CHANNELS for c in channels):
        return [], []
    return people, channels


def confirmed_home_state(hass: Any, settings: Mapping[str, Any]) -> str:
    """All HA persons AND explicitly configured trackers must be confirmed away.

    A single real 'home' wins. Unknown, unavailable, missing, stale and an empty
    tracker list without Person entities cannot prove that everyone left.
    Also obey room/occupancy checks and the existing away cooldown.
    """
    global_cfg = settings.get(CONF_OCCUPANCY_GLOBAL, {})
    if not isinstance(global_cfg, Mapping):
        global_cfg = {}
    persons = [state.entity_id for state in hass.states.async_all("person")]
    configured_trackers = global_cfg.get("home_trackers", [])
    configured_trackers = configured_trackers if isinstance(configured_trackers, list) else []
    ids = list(dict.fromkeys([
        *persons,
        *(entity for entity in configured_trackers if isinstance(entity, str)
          and entity.startswith(("person.", "device_tracker.", "binary_sensor."))),
    ]))
    if not ids:
        return "unknown"
    max_age = global_cfg.get("source_stale_minutes", 240)
    try:
        age = min(1440.0, max(1.0, float(max_age)))
    except (TypeError, ValueError, OverflowError):
        age = 240.0
    readings = [_bool_presence(hass.states.get(entity), age) for entity in ids]
    if any(value is True for value in readings):
        return "home"
    if any(value is None for value in readings):
        return "unknown"
    # All explicitly configured persons/trackers are negative. Shared
    # occupancy or occupied-room evidence can still veto a departure.
    status, _, _ = home_presence(hass, global_cfg, fallback_trackers=persons)
    return "away" if status == "away" else status if status == "home" else "unknown"


def open_windows(hass: Any, settings: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Collect actual ON Window-class binary contacts in configured rooms."""
    from homeassistant.helpers import area_registry as ar
    from .device_hierarchy import configured_area_ids

    registry = ar.async_get(hass)
    source_rooms = settings.get("room_sources", {})
    area_ids = list(configured_area_ids(settings))
    if isinstance(source_rooms, Mapping):
        area_ids.extend(area for area in source_rooms if isinstance(area, str))
    excluded = set(settings.get(CONF_EXCLUDED_WINDOWS, ()) or ())
    by_area: list[tuple[str, str]] = []
    for area in dict.fromkeys(area_ids):
        registered = registry.async_get_area(area)
        if registered is None:
            continue
        chosen = selected(settings, area, "windows")
        if chosen is None:
            # Backwards compatibility only for areas never configured in the
            # new Room Setup. Explicit [] never triggers autodiscovery.
            ids = [
                state.entity_id for state in hass.states.async_all("binary_sensor")
                if entity_area(hass, state.entity_id) == area and is_window(hass, state)
            ]
        else:
            ids = list(chosen)
        for entity_id in dict.fromkeys(ids):
            if entity_id in excluded or not native(hass, entity_id):
                continue
            state = hass.states.get(entity_id)
            if (state is None or entity_area(hass, entity_id) != area
                    or not is_window(hass, state) or state.state != "on"):
                continue
            name = str(getattr(state, "name", None) or entity_id).strip()[:100]
            by_area.append((entity_id, f"{registered.name}: {name}"))
    return tuple(sorted(by_area))


def watched_entities(hass: Any, settings: Mapping[str, Any]) -> set[str]:
    """Track every configured away-evidence source and eligible window contact."""
    from .device_hierarchy import configured_area_ids

    globals_ = settings.get(CONF_OCCUPANCY_GLOBAL, {})
    globals_ = globals_ if isinstance(globals_, Mapping) else {}
    tracked = {item.entity_id for item in hass.states.async_all("person")}
    for field in ("home_trackers", "room_occupancy_sensors"):
        values = globals_.get(field, [])
        if isinstance(values, list):
            tracked.update(item for item in values if isinstance(item, str))
    rooms_id = globals_.get("occupied_rooms_entity")
    if isinstance(rooms_id, str) and rooms_id:
        tracked.add(rooms_id)
    sources = settings.get("room_sources", {})
    areas = list(configured_area_ids(settings))
    if isinstance(sources, Mapping):
        areas.extend(k for k in sources if isinstance(k, str))
    for area in dict.fromkeys(areas):
        choices = selected(settings, area, "windows")
        if choices is not None:
            tracked.update(choices)
        else:
            tracked.update(
                item.entity_id for item in hass.states.async_all("binary_sensor")
                if entity_area(hass, item.entity_id) == area and is_window(hass, item)
            )
    return tracked


def compose_message(language: str, windows: tuple[tuple[str, str], ...]) -> tuple[str, str]:
    lang = str(language or "en").replace("_", "-").split("-", 1)[0].casefold()
    title, template = MESSAGES.get(lang, MESSAGES["en"])
    labels = [label for _, label in windows]
    visible = "; ".join(labels[:20])
    if len(labels) > 20:
        visible += f"; +{len(labels) - 20}"
    return title, template.format(windows=visible)


async def deliver_notice(manager: Any, windows: tuple[tuple[str, str], ...]) -> bool:
    """Dispatch only user-authorized person slots, never fall back to speakers."""
    hass = manager.hass
    settings = manager.settings
    language = manager.get_language(None) if callable(getattr(manager, "get_language", None)) else settings.get(CONF_LANGUAGE, "en")
    title, text = compose_message(language, windows)
    if hub_installed(hass):
        people, choices = configured_recipients(hass, settings)
        if not people or not choices:
            _LOGGER.warning("Away-window alert needs person and delivery selections in General settings")
            return False
        if not hub_available(hass):
            _LOGGER.warning("Away-window alert not delivered: configured Announcement Hub is unavailable")
            return False
        # Keep each destination's channel selection independent. A user asking
        # for phone text and watch speech must not receive unsolicited phone
        # speech or a watch push. Each Hub request is explicitly person-bound.
        grouped: dict[str, list[str]] = {}
        for choice in choices:
            slot, service = DELIVERY_CHANNELS[choice]
            grouped.setdefault(slot, []).append(service)
        success = True
        for slot, services in grouped.items():
            services = list(dict.fromkeys(services))
            visual = "notification" in services
            speech = "companion_tts" in services
            payload: dict[str, Any] = {
                "title": title, "level": "warning",
                "target_person": people, "person_destination": [slot],
                "service": services, "occupied_only": False,
                "companion_tts": speech,
                "use_ai": False,
            }
            if visual:
                payload["text_notify"] = text
            if speech:
                payload["text_tts"] = text
            if not await async_submit_hub(hass, payload):
                success = False
        return success

    # Standalone mode: only explicit direct mobile-app notify entities, never
    # a TV, home speaker, room, or randomly discovered person/device.
    notified = False
    if hass.services.has_service("notify", "send_message"):
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        mobile = []
        for entity_id in settings.get(CONF_NOTIFY_TARGETS, []) or []:
            entry = registry.async_get(entity_id) if isinstance(entity_id, str) else None
            if (entry is not None and getattr(entry, "platform", None) == "mobile_app"
                    and getattr(entry, "disabled_by", None) is None):
                mobile.append(entity_id)
        if mobile:
            try:
                await hass.services.async_call(
                    "notify", "send_message", {"title": title, "message": text},
                    target={"entity_id": mobile}, blocking=True,
                )
                notified = True
            except asyncio.CancelledError:
                raise
            except Exception as error:
                _LOGGER.warning("Away-window direct mobile notification failed: %s", error)
    return notified or await async_system_notification(
        hass, title, text, "open_windows_away",
    )


class AwayWindowAlert:
    """Debounced one-per-new-open-window per departure alert coordinator."""

    def __init__(self, manager: Any, *, call_later: Any = None) -> None:
        self.manager = manager
        self._call_later = call_later
        self._armed = False
        self._episode = 0
        self._sent: set[str] = set()
        self._timer: Any = None
        self._pending_task: Any = None

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            cancel, self._timer = self._timer, None
            cancel()

    def stop(self) -> None:
        self._cancel_timer()
        # Manager unload cancels all registered async send tasks.
        self._armed = False
        self._episode += 1
        self._sent.clear()

    def _schedule(self, seconds: int) -> None:
        if self._timer is not None:
            return
        if self._call_later is None:
            from homeassistant.helpers.event import async_call_later
            self._call_later = async_call_later
        self._timer = self._call_later(self.manager.hass, seconds, self._fire)

    def observe(self, *, initial: bool = False) -> None:
        settings = self.manager.settings
        if not getattr(self.manager, "_active", False) or settings.get(CONF_AWAY_WINDOWS_ALERT) is not True:
            self.stop()
            return
        current = confirmed_home_state(self.manager.hass, settings)
        if current == "home":
            # A fresh HOME reading establishes a new departure. Restart while
            # AWAY never produces a duplicate alert.
            if self._sent or self._timer or not self._armed:
                self._episode += 1
            self._armed = True
            self._sent.clear()
            self._cancel_timer()
            return
        if current != "away":
            self._cancel_timer()
            return
        if not self._armed or initial:
            return
        opened = open_windows(self.manager.hass, settings)
        if any(entity_id not in self._sent for entity_id, _ in opened):
            if self._pending_task is None:
                self._schedule(DEPARTURE_STABLE_SECONDS)
        else:
            self._cancel_timer()

    def _fire(self, _now: Any) -> None:
        self._timer = None
        if not getattr(self.manager, "_active", False):
            return
        settings = self.manager.settings
        if settings.get(CONF_AWAY_WINDOWS_ALERT) is not True or not self._armed:
            return
        if confirmed_home_state(self.manager.hass, settings) != "away":
            return
        opened = open_windows(self.manager.hass, settings)
        if not any(entity_id not in self._sent for entity_id, _ in opened):
            return
        if self._pending_task is not None:
            return
        episode = self._episode
        task = self.manager.hass.async_create_task(self._deliver(opened, episode))
        self._pending_task = task
        tasks = getattr(self.manager, "_tasks", None)
        if isinstance(tasks, set):
            tasks.add(task)
        def finished(done: Any) -> None:
            if self._pending_task is done:
                self._pending_task = None
            if isinstance(tasks, set):
                tasks.discard(done)
            if not done.cancelled() and done.exception() is not None:
                _LOGGER.error("Away-window delivery task failed: %r", done.exception())
            # Recheck any extra opening that appeared while delivery ran.
            if getattr(self.manager, "_active", False):
                self.observe()
        task.add_done_callback(finished)

    async def _deliver(self, opened: tuple[tuple[str, str], ...], episode: int) -> None:
        # Recheck immediately before service calls, not just at initial timer.
        if (self._episode != episode or not self._armed
                or confirmed_home_state(self.manager.hass, self.manager.settings) != "away"):
            return
        succeeded = await deliver_notice(self.manager, opened)
        if self._episode != episode:
            return
        if succeeded:
            self._sent.update(entity_id for entity_id, _ in opened)
        else:
            # A temporary Hub outage must not broaden delivery to room audio
            # or spam the service every 30-second controller recomputation.
            self._schedule(RETRY_SECONDS)
