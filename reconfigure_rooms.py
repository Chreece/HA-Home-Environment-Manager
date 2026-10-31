"""One room-centric Configure / Reconfigure menu with bounded editing.

Room selections, source inventories and global inputs are edited independently.
Dynamic menu entries use HA's supported menu_options mapping (key -> literal
label), and __getattr__ supplies only methods for saved, registered Area IDs.
The physical grants / controller algorithms remain on device entities.
"""
from __future__ import annotations

from .config_data import mutable_copy as deepcopy
from typing import Any
import json
from pathlib import Path

import probatio
from homeassistant.helpers import area_registry as ar, entity_registry as er

from .const import CONF_AREAS, CONF_CLIMATE_ROOMS
from .room_setup import areas, select, field
from . import room_sources as sources


def _locale_menu(hass: Any, context: Any) -> tuple[str, str, str]:
    """Resolve the dialog's locale for runtime-labelled area menu options.

    HA accepts menu_options as a mapping from step ID to literal label.
    Reuse our shipped translation files instead of inventing a new locale
    catalog or assuming the browser language matches HA's system language.
    """
    language = context.get("language") if isinstance(context, dict) else None
    language = language or getattr(getattr(hass, "config", None), "language", "en")
    text = str(language or "en").replace("_", "-")
    translations = Path(__file__).parent / "translations"
    for candidate in dict.fromkeys((text, text.split("-")[0], "en")):
        file = translations / (candidate + ".json")
        if not file.is_file():
            continue
        try:
            steps = json.loads(file.read_text(encoding="utf-8"))["options"]["step"]
            values = steps["init"]["menu_options"]
            room = steps["room_settings"]["title"]
            return (
                values.get("choose_rooms", "Choose rooms"),
                values.get("general_settings", "General settings"),
                room,
            )
        except (OSError, TypeError, ValueError, KeyError):
            continue
    return "Choose rooms", "General settings", "Settings · {area_name}"


class ReconfigureRoomsMixin:
    """Direct per-room entries, not a second climate- or PID-specific wizard."""

    _ROOM_PREFIX = "async_step_edit_room_"

    def _selected_edit_rooms(self) -> list[tuple[str, str]]:
        registry = ar.async_get(self.hass)
        values = self._values.get(CONF_AREAS, [])
        if not isinstance(values, list):
            return []
        result = []
        for area in dict.fromkeys(values):
            if not isinstance(area, str) or not area:
                continue
            record = registry.async_get_area(area)
            if record is not None:
                result.append((area, record.name))
        return result

    def _room_edit_menu(self) -> dict[str, str]:
        choose, general, room_template = _locale_menu(
            self.hass, getattr(self, "context", {})
        )
        result = {"choose_rooms": choose}
        # menu_options is explicitly a mapping of step IDs to literal display
        # names in HA. Dynamically registered Area IDs are validated again
        # when the menu item is invoked (never trust a stale browser menu).
        for area, name in self._selected_edit_rooms():
            try:
                label = room_template.format(area_name=name)
            except (ValueError, KeyError):
                label = f"Settings · {name}"
            result[f"edit_room_{area}"] = label
        result["general_settings"] = general
        return result

    def __getattr__(self, name: str):
        if name.startswith(self._ROOM_PREFIX):
            area = name[len(self._ROOM_PREFIX):]
            if area and area in {key for key, _ in self._selected_edit_rooms()}:
                async def open_selected_room(user_input=None):
                    self._room_edit_area = area
                    return await self.async_step_room_settings(user_input)
                return open_selected_room
        raise AttributeError(name)

    async def async_step_choose_rooms(self, user_input=None):
        """Change the list of monitored areas on one page, preserving drafts."""
        options = areas(self.hass)
        valid = {item["value"] for item in options}
        prior = self._values.get(CONF_AREAS, [])
        default = [area for area in prior if area in valid] if isinstance(prior, list) else []
        errors = {}
        if user_input is not None:
            chosen = user_input.get(CONF_AREAS, [])
            if (not isinstance(chosen, list) or not chosen
                    or any(not isinstance(v, str) or v not in valid for v in chosen)):
                errors["base"] = "invalid_setup_rooms"
            else:
                selected = list(dict.fromkeys(chosen))
                if selected != prior:
                    # Existing restrictions must revoke automation only for
                    # rooms explicitly removed. Unchanged rooms keep grants.
                    sources.restrict_rooms(self._values, selected)
                return await self._finish()
        return self.async_show_form(
            step_id="choose_rooms", errors=errors,
            data_schema=probatio.Schema({
                probatio.Required(CONF_AREAS, default=default):
                    select(options, multiple=True),
            }),
        )

    async def async_step_room_settings(self, user_input=None):
        """Edit all selected sources in one room; never auto-operate hardware."""
        from .occupancy_policy import room_sensor_choices
        from .discovery import entity_area
        area = getattr(self, "_room_edit_area", None)
        registered = {key for key, _ in self._selected_edit_rooms()}
        if area not in registered:
            return self.async_abort(reason="setup_area_removed")
        room = ar.async_get(self.hass).async_get_area(area)
        saved = sources.defaults(self.hass, self._values, area)
        options = sources.choices(self.hass, area, saved)
        defaults = {
            group: [eid for eid in saved[group]
                    if eid in {item["value"] for item in options[group]}]
            for group in sources.GROUPS
        }
        configs = self._values.get(CONF_CLIMATE_ROOMS, {})
        configs = configs if isinstance(configs, dict) else {}
        current = configs.get(area, {})
        current = current if isinstance(current, dict) else {}
        actual_occupancy = current.get("occupancy_sensors")
        discovered = room_sensor_choices(self.hass, area)
        suggested = (actual_occupancy if isinstance(actual_occupancy, list)
                     else discovered)
        # Keep unavailable selected sensors visible when the HA entity
        # registry still confirms this exact room; never accept another area.
        permitted = sorted(set(discovered) | {
            eid for eid in suggested if isinstance(eid, str)
            and eid.startswith("binary_sensor.")
            and entity_area(self.hass, eid) == area
        })
        options["occupancy_sensors"] = [
            {"value": eid, "label": sources.label(self.hass, eid)}
            for eid in permitted
        ]
        defaults["occupancy_sensors"] = [
            eid for eid in suggested if eid in permitted
        ]
        errors = {}
        if user_input is not None:
            picked = {}
            for group in (*sources.GROUPS, "occupancy_sensors"):
                # Optional HA multi-select fields are absent when explicitly
                # cleared. Never reinstate old defaults on a submit.
                value = user_input.get(group, [])
                valid = {item["value"] for item in options[group]}
                if (not isinstance(value, list)
                        or any(not isinstance(eid, str) or eid not in valid
                               for eid in value)):
                    errors[group] = "invalid_room_source"
                else:
                    picked[group] = list(dict.fromkeys(value))
            if not errors:
                selected_sources = {k: picked[k] for k in sources.GROUPS}
                existing = self._values.get(sources.CONF_ROOM_SOURCES, {})
                previous = existing.get(area) if isinstance(existing, dict) else None
                if (not isinstance(previous, dict) and
                        selected_sources == {k: defaults[k] for k in sources.GROUPS}):
                    # Initial save materializes existing discovery as explicit
                    # choices without touching device safety grants/PID pins.
                    self._values.setdefault(sources.CONF_ROOM_SOURCES, {})[area] = deepcopy(selected_sources)
                elif not isinstance(previous, dict) or any(
                        previous.get(group, []) != selected_sources[group]
                        for group in sources.GROUPS):
                    # True source changes use the existing independent
                    # revocation path (no new hardware permissions).
                    sources.store_selection(self.hass, self._values, area, selected_sources)
                if (not isinstance(actual_occupancy, list)
                        or actual_occupancy != picked["occupancy_sensors"]):
                    rooms = self._values.setdefault(CONF_CLIMATE_ROOMS, {})
                    cfg = deepcopy(rooms.get(area, {}))
                    cfg["occupancy_sensors"] = picked["occupancy_sensors"]
                    rooms[area] = cfg
                return await self._finish()
        return self.async_show_form(
            step_id="room_settings", errors=errors,
            description_placeholders={"area_name": room.name},
            data_schema=probatio.Schema({
                field(group, (user_input or {}).get(group, defaults[group])):
                    select(options[group], multiple=True)
                for group in (*sources.GROUPS, "occupancy_sensors")
            }),
        )

    async def async_step_general_settings(self, user_input=None):
        """All common sources, presentation and global limits on one page."""
        return await self.async_step_setup_general(user_input)
