"""Focused Home Environment Manager reconfiguration.

Three visible sections only: choose monitored rooms, one direct editor for
each selected room, and the complete existing general-settings form. All
editors operate on the flow-local draft; the existing _finish() performs the
only durable entry update. Device grants are never created by discovery.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import probatio
from homeassistant.helpers import area_registry as ar

from .config_data import mutable_copy as deepcopy
from .const import CONF_AREAS, CONF_CLIMATE_ROOMS
from .occupancy_policy import room_sensor_choices
from . import room_sources as sources
from .room_setup import areas, field, select


def _locale_sections(hass: Any, context: Any) -> dict:
    """Use shipped locale text for *dynamic* menu labels.

    HA translates a static list of menu step IDs, but each room entry requires
    a distinct runtime step ID/name. Passing a step->label mapping is a
    supported FlowHandler menu interface; load its label from shipped locales.
    """
    requested = context.get("language") if isinstance(context, dict) else None
    requested = requested or getattr(getattr(hass, "config", None), "language", "en")
    language = str(requested or "en").replace("_", "-")
    directory = Path(__file__).parent / "translations"
    for candidate in (language, language.split("-")[0], "en"):
        candidate_path = directory / (candidate + ".json")
        if not candidate_path.is_file():
            continue
        try:
            data = json.loads(candidate_path.read_text(encoding="utf-8"))
            return data.get("options", {}).get("step", {})
        except (OSError, ValueError, TypeError):
            continue
    return {}


class ReconfigureSectionsMixin:
    """Three types of section; selected rooms appear as direct menu links."""

    def _settings_menu(self, step_id: str):
        translations = _locale_sections(self.hass, getattr(self, "context", {}))
        menu_title = translations.get("init", {}).get("menu_options", {})
        # No "extra" area is enrolled because it has a climate sensor. This
        # list is precisely the room selection saved by the user.
        selected = self._values.get(CONF_AREAS, [])
        selected = selected if isinstance(selected, list) else []
        registry = ar.async_get(self.hass)
        menu: dict[str, str] = {
            "choose_rooms": menu_title.get("choose_rooms", "Choose rooms")
        }
        self._room_menu_routes = {}
        room_title = translations.get("room_settings", {}).get(
            "title", "Room settings · {area_name}"
        )
        for index, area in enumerate(dict.fromkeys(selected)):
            if not isinstance(area, str):
                continue
            actual = registry.async_get_area(area)
            if actual is None:
                continue
            route = f"edit_room_{index}"
            self._room_menu_routes[route] = area
            try:
                label = room_title.format(area_name=actual.name)
            except (KeyError, ValueError):
                label = f"{actual.name} · Room settings"
            menu[route] = label
            # FlowHandler resolves next_step_id via getattr on THIS flow
            # instance. The registered action is scoped to the menu's saved
            # room ID, so renaming the room doesn't redirect an existing flow.
            async def open_room(user_input=None, *, _area=area):
                self._room_settings_area = _area
                return await self.async_step_room_settings()
            setattr(self, "async_step_" + route, open_room)
        menu["general_settings"] = menu_title.get(
            "general_settings", "General settings"
        )
        return self.async_show_menu(step_id=step_id, menu_options=menu)

    async def async_step_choose_rooms(self, user_input=None):
        """Select monitored rooms without silently deleting room preferences."""
        available = areas(self.hass)
        known = {choice["value"] for choice in available}
        current = self._values.get(CONF_AREAS, [])
        defaults = [area for area in current if area in known] if isinstance(current, list) else []
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = user_input.get(CONF_AREAS, [])
            if (not isinstance(selected, list) or not selected
                    or any(not isinstance(area, str) or area not in known
                           for area in selected)):
                errors["base"] = "invalid_setup_rooms"
            else:
                chosen = list(dict.fromkeys(selected))
                previous = set(defaults)
                removed = previous - set(chosen)
                revised = deepcopy(self._values)
                revised[CONF_AREAS] = chosen
                # Removing a monitored room also disables any controller /
                # shade outputs belonging to THAT room only. Keep its saved
                # entity preferences so an explicit future re-enrolment does
                # not silently restore automation grants.
                for area in removed:
                    controller = revised.get("climate_rooms", {}).get(area)
                    if isinstance(controller, dict):
                        controller["enabled"] = False
                        controller["allow_actuation"] = False
                        for device in controller.get("device_settings", {}).values():
                            if isinstance(device, dict):
                                device["auto_control"] = False
                    pid = revised.get("pid_rooms", {}).get(area)
                    if isinstance(pid, dict):
                        pid["enabled"] = False
                    shade = revised.get("shade_rooms", {}).get(area)
                    if isinstance(shade, dict):
                        shade["enabled"] = False
                        for cover in shade.get("covers", {}).values():
                            if isinstance(cover, dict):
                                cover["enabled"] = False
                self._values = revised
                return await self._finish()
        return self.async_show_form(
            step_id="choose_rooms", errors=errors,
            data_schema=probatio.Schema({
                probatio.Required(CONF_AREAS, default=defaults):
                    select(available, multiple=True),
            }),
        )

    async def async_step_room_settings(self, user_input=None):
        """Edit ALL room multiselectors, including explicit occupancy fallback.

        Reuse original 7-source picker and its existing grant-revocation rules;
        adding occupancy as the eighth selector does not rewrite any other
        area. Source defaults remain saved-empty when explicitly configured.
        """
        area = getattr(self, "_room_settings_area", None)
        rooms = self._values.get(CONF_AREAS, [])
        if not isinstance(area, str) or not isinstance(rooms, list) or area not in rooms:
            return self.async_abort(reason="setup_area_removed")
        actual = ar.async_get(self.hass).async_get_area(area)
        if actual is None:
            return self.async_abort(reason="setup_area_removed")
        saved = sources.defaults(self.hass, self._values, area)
        choices = sources.choices(self.hass, area, saved)
        defaults = {
            group: [eid for eid in saved[group]
                    if eid in {entry["value"] for entry in choices[group]}]
            for group in sources.GROUPS
        }
        stored_rooms = self._values.get(CONF_CLIMATE_ROOMS, {})
        stored_room = stored_rooms.get(area, {}) if isinstance(stored_rooms, dict) else {}
        stored_room = stored_room if isinstance(stored_room, dict) else {}
        discovered = room_sensor_choices(self.hass, area)
        configured = stored_room.get("occupancy_sensors")
        occupancy_defaults = (
            list(configured) if isinstance(configured, list) else list(discovered)
        )
        # Keep an unavailable previously selected sensor in the editor; it
        # cannot prove ON/OFF until it reports a fresh, valid HA state.
        occupancy_options = [
            {"value": eid, "label": sources.label(self.hass, eid)}
            for eid in sorted(set(discovered) | set(occupancy_defaults))
            if isinstance(eid, str) and eid.startswith("binary_sensor.")
        ]
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {}
            for group in sources.GROUPS:
                chosen = user_input.get(group, defaults[group])
                allowed = {item["value"] for item in choices[group]}
                if (not isinstance(chosen, list)
                        or any(not isinstance(eid, str) or eid not in allowed
                               for eid in chosen)):
                    errors[group] = "invalid_room_source"
                else:
                    data[group] = list(dict.fromkeys(chosen))
            occupancy = user_input.get("occupancy_sensors", [])
            available = {x["value"] for x in occupancy_options}
            if (not isinstance(occupancy, list)
                    or any(not isinstance(eid, str) or eid not in available
                           for eid in occupancy)):
                errors["occupancy_sensors"] = "invalid_room_source"
            if not errors:
                revised = deepcopy(self._values)
                # All seven source groups are edited together, ensuring any
                # removed physical device/sensor revokes stale automation.
                sources.store_selection(self.hass, revised, area, data)
                stored = revised.setdefault(CONF_CLIMATE_ROOMS, {})
                room = stored.setdefault(area, {})
                room["occupancy_sensors"] = list(dict.fromkeys(occupancy))
                self._values = revised
                return await self._finish()
        fields = {
            field(group, (user_input or {}).get(group, defaults[group])):
                select(choices[group], multiple=True)
            for group in sources.GROUPS
        }
        fields[field("occupancy_sensors", (user_input or {}).get(
            "occupancy_sensors", occupancy_defaults
        ))] = select(occupancy_options, multiple=True)
        return self.async_show_form(
            step_id="room_settings", errors=errors,
            description_placeholders={"area_name": actual.name},
            data_schema=probatio.Schema(fields),
        )

    async def async_step_general_settings(self, user_input=None):
        """The COMPLETE prior general settings form, not the short fragment."""
        # RoomSetupMixin's form includes weather, outdoor, warning, persons,
        # sleep, Occupied Rooms, notifications, media, TTS, language, AI, mold,
        # pollen and away windows. A section edit must never force the room
        # setup wizard to run first.
        self._setup_order = []
        self._setup_index = 0
        return await self.async_step_setup_general(user_input)
