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


def _locale_menu(language: str) -> tuple[str, str, str]:
    """Resolve the dialog's locale for runtime-labelled area menu options.

    HA accepts menu_options as a mapping from step ID to literal label.
    Reuse our shipped translation files instead of inventing a new locale
    catalog or assuming the browser language matches HA's system language.
    """
    # Runs in Home Assistant's executor, never on the asyncio event loop.
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
                # The shipped menu key is setup_general. Beta79/80 looked
                # up general_settings instead and always rendered English.
                values.get("setup_general")
                or steps["setup_general"]["title"],
                room,
            )
        except (OSError, TypeError, ValueError, KeyError):
            continue
    return "Choose rooms", "General settings", "Settings · {area_name}"


class ReconfigureRoomsMixin:
    """Direct per-room entries, not a second climate- or PID-specific wizard."""

    _ROOM_PREFIX = "async_step_edit_room_"

    def _selected_edit_rooms(self) -> list[tuple[str, str]]:
        from .device_hierarchy import configured_area_ids

        registry = ar.async_get(self.hass)
        # Room hubs may exist for climate/PID devices outside air-quality
        # monitoring. Use their existing bounded membership, without adding
        # monitored areas or granting any device control by opening settings.
        values = configured_area_ids(self._values)
        result = []
        for area in dict.fromkeys(values):
            if not isinstance(area, str) or not area:
                continue
            record = registry.async_get_area(area)
            if record is not None:
                result.append((area, record.name))
        return result

    async def _room_edit_menu(self) -> dict[str, str]:
        context = getattr(self, "context", None)
        language = context.get("language") if isinstance(context, dict) else None
        language = language or getattr(
            getattr(self.hass, "config", None), "language", "en"
        )
        # Locale JSON is packaged with the integration but reading it from
        # HA's event loop triggers the blocking-I/O detector. Resolve the
        # three menu labels off-loop while retaining all shipped languages.
        choose, general, room_template = await self.hass.async_add_executor_job(
            _locale_menu, str(language)
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

    async def async_step_setup_rooms(self, user_input=None):
        """Use the established translated form key in edit mode only.

        Existing Home Assistant frontends may retain the older step catalog
        across a custom integration update. Initial setup is unaffected.
        """
        if getattr(self, "_menu_mode", False):
            return await self.async_step_choose_rooms(user_input)
        return await super().async_step_setup_rooms(user_input)

    async def async_step_edit_room(self, user_input=None):
        """Preserve the existing translated room editor step ID."""
        if getattr(self, "_menu_mode", False):
            return await self.async_step_room_settings(user_input)
        return await super().async_step_edit_room(user_input)

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
            # HA frontend translations for this established step have been
            # shipped since initial setup; avoid a new unlocalized Options key.
            step_id="setup_rooms", errors=errors,
            data_schema=probatio.Schema({
                probatio.Required(CONF_AREAS, default=default):
                    select(options, multiple=True),
            }),
        )

    async def async_step_room_settings(self, user_input=None):
        """Edit all selected sources in one room; never auto-operate hardware."""
        from .occupancy_policy import room_sensor_choices
        from .discovery import entity_area
        from .room_doors import door_choices
        from .const import CONF_OCCUPANCY_GLOBAL
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
        legacy_global = self._values.get(CONF_OCCUPANCY_GLOBAL, {})
        legacy_global = legacy_global if isinstance(legacy_global, dict) else {}
        legacy = legacy_global.get("room_occupancy_sensors", [])
        legacy_local = [
            eid for eid in legacy if isinstance(eid, str)
            and eid.startswith("binary_sensor.")
            and entity_area(self.hass, eid) == area
        ] if isinstance(legacy, list) else []
        suggested = (actual_occupancy if isinstance(actual_occupancy, list)
                     else sorted(set(discovered) | set(legacy_local)))
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
        # Door contacts are opt-in. Unlike presence defaults, observing a
        # DOOR-class sensor never automatically selects it or enables Eco.
        old_doors = current.get("door_sensors")
        saved_doors = old_doors if isinstance(old_doors, list) else []
        options["door_sensors"] = door_choices(self.hass, area, saved_doors)
        allowed_doors = {item["value"] for item in options["door_sensors"]}
        defaults["door_sensors"] = [
            eid for eid in saved_doors if eid in allowed_doors
        ]
        errors = {}
        if user_input is not None:
            picked = {}
            for group in (*sources.GROUPS, "occupancy_sensors", "door_sensors"):
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
                if (not isinstance(previous, dict) and not selected_sources["shades"]
                        and selected_sources == {k: defaults[k] for k in sources.GROUPS}):
                    # Initial save materializes existing sensor discovery.
                    # Newly enrolled covers must use store_selection below,
                    # which revokes any stale per-cover automation grants.
                    self._values.setdefault(sources.CONF_ROOM_SOURCES, {})[area] = deepcopy(selected_sources)
                elif not isinstance(previous, dict) or any(
                        previous.get(group, []) != selected_sources[group]
                        for group in sources.GROUPS):
                    # True source changes use the existing independent
                    # revocation path (no new hardware permissions).
                    sources.store_selection(self.hass, self._values, area, selected_sources)
                # A legacy room without a door configuration is already
                # equivalent to an unselected [] contact list. Do not mutate
                # its Options payload on an unchanged/no-op Save. Still store
                # explicit clearing when an earlier list actually existed.
                occupancy_changed = (
                    not isinstance(actual_occupancy, list)
                    or actual_occupancy != picked["occupancy_sensors"]
                )
                doors_changed = (
                    old_doors != picked["door_sensors"]
                    if isinstance(old_doors, list)
                    else bool(picked["door_sensors"])
                )
                if occupancy_changed or doors_changed:
                    rooms = self._values.setdefault(CONF_CLIMATE_ROOMS, {})
                    cfg = deepcopy(rooms.get(area, {}))
                    if occupancy_changed:
                        cfg["occupancy_sensors"] = picked["occupancy_sensors"]
                    if doors_changed:
                        cfg["door_sensors"] = picked["door_sensors"]
                    rooms[area] = cfg
                # Retire legacy global room-source duplicates only for THIS
                # verified area. Other rooms/unassigned sources remain intact
                # until their own editors can migrate them safely.
                if legacy_local:
                    previous = legacy_global.get("room_occupancy_sensors", [])
                    remaining = [eid for eid in previous if eid not in legacy_local]
                    self._values[CONF_OCCUPANCY_GLOBAL] = {
                        **legacy_global, "room_occupancy_sensors": remaining,
                    }
                return await self._finish()
        return self.async_show_form(
            step_id="edit_room", errors=errors,
            description_placeholders={"area_name": room.name},
            data_schema=probatio.Schema({
                field(group, (user_input or {}).get(group, defaults[group])):
                    select(options[group], multiple=True)
                for group in (*sources.GROUPS, "occupancy_sensors", "door_sensors")
            }),
        )

    async def async_step_general_settings(self, user_input=None):
        """All common sources, presentation and global limits on one page."""
        return await self.async_step_setup_general(user_input)
