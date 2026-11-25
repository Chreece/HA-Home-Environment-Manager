"""Shared push updates for logical managed-device entities."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATED
from . import equipment_model as model
from .equipment_help import equipment_configuration_help
from .backend_text import presentation_languages
from .equipment_name_catalog import localized_equipment_name


class EquipmentEntity:
    """Mixin: all entities attach to the existing Area-hub child device."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def _equipment_init(self, manager, spec, key, *, operating_mode=None):
        self._manager, self._spec, self._key = manager, spec, key
        self._operating_mode = operating_mode
        suffix = f"mode_{operating_mode}_{key}" if operating_mode else key
        self._attr_unique_id = f"{spec.identifier}_{suffix}"
        self._attr_translation_key = f"equipment_{key}"
        # All equipment entities sort by their functional leading group:
        # PID, Power, Quiet, Control, Presence, etc. HA must not prepend the
        # parent device name ahead of the translated category. Keep unique IDs
        # and device registration unchanged, including user-customized names.
        self._attr_has_entity_name = False
        self._attr_device_info = {"identifiers": {(DOMAIN, model.device_identifier(spec))}}

        # Only the actual climate facade includes the source product name.
        # Multi-endpoint products still need an individual channel in their
        # tuning labels, AFTER the grouping prefix, to avoid duplicate titles.
        if key == "climate":
            if isinstance(spec, model.ManagedEndpoint) and spec.source_entities:
                source = spec.source_entities[0]
                native = manager.hass.states.get(source)
                channel = getattr(native, "name", None) or source
            else:
                channel = spec.name
        elif isinstance(spec, model.ManagedEndpoint):
            source = spec.source_entities[0] if spec.source_entities else ""
            native = manager.hass.states.get(source) if source else None
            channel_name = getattr(native, "name", None) or source or spec.name
            channel = f"{channel_name} · "
        else:
            channel = ""
        self._attr_translation_placeholders = {"channel": channel}
        # Home Assistant only translates the entity's name when
        # has_entity_name=True, which would prepend the source device name
        # before our category. Resolve the same translated names explicitly
        # in memory and use a full legacy name instead.
        locale = getattr(getattr(manager.hass, "config", None), "language", "en")
        self._attr_name = localized_equipment_name(key, locale, channel)
        if key in ("door_closed_eco", "door_start_coordination"):
            from .equipment_door_policy import words
            prefix = {"el": "Πόρτα", "de": "Tür"}.get(str(locale).split("-")[0], "Door")
            self._attr_name = prefix + " · " + channel + words(locale)[key]
        if operating_mode:
            from .equipment_mode_entities import setting_label
            from .operating_mode_catalog import operating_mode_label
            label = operating_mode_label(operating_mode, locale)
            self._attr_name = f"{label} · {channel}{setting_label(key, locale)}"

    @property
    def name(self):
        if getattr(self, "_key", None) != "native_full_output":
            return getattr(self, "_attr_name", None)
        # Re-evaluate capability-backed names when the native device reports
        # its modes after startup. The controller identity and any user-set
        # registry name remain unchanged.
        from .equipment_native_target import configuration_modes
        from .equipment_name_catalog import native_full_output_label
        locale = getattr(getattr(self._manager.hass, "config", None), "language", "en")
        channel = getattr(self, "_attr_translation_placeholders", {}).get("channel", "")
        group = localized_equipment_name("control_mode", locale).partition(" · ")[0]
        label = native_full_output_label(configuration_modes(self._manager, self._spec), locale)
        return f"{group} · {channel}{label}"

    @property
    def controller_settings(self):
        # HA reads availability, value and many attributes synchronously in a
        # single write. Reuse the profile for just that serialization.
        snapshot = getattr(self, "_render_settings", None)
        if snapshot is not None:
            return snapshot
        if getattr(self, "_operating_mode", None):
            if model.mode_descriptor(self._manager, self._spec, self._operating_mode) is None:
                from .equipment_mode_entities import saved_display_settings
                snapshot = saved_display_settings(self._manager, self._spec, self._operating_mode)
            else:
                snapshot = model.settings_for_mode(self._manager, self._spec, self._operating_mode)
        else:
            snapshot = model.settings(self._manager, self._spec)
        if getattr(self, "_rendering", False):
            self._render_settings = snapshot
        return snapshot

    async def _async_update_controller_settings(self, changes):
        mode = getattr(self, "_operating_mode", None)
        if mode:
            await self._manager.equipment.async_update(
                self._spec, changes, operating_mode=mode,
            )
        else:
            await self._manager.equipment.async_update(self._spec, changes)

    @property
    def extra_state_attributes(self):
        locale = self._manager.settings.get("language", "auto")
        if locale == "auto":
            locale = getattr(getattr(self._manager.hass, "config", None), "language", "en")
        key = getattr(self, "_key", "control_status")
        if key == "native_full_output":
            from .equipment_native_target import configuration_modes
            modes = configuration_modes(self._manager, self._spec)
            help_text = equipment_configuration_help(key, locale, modes=modes)
        else:
            modes = None
            help_text = equipment_configuration_help(key, locale)
        attributes = {"area_id": self._spec.area_id,
                "controller_id": self._spec.identifier,
                "source_device_id": self._spec.source_device_id,
                "source_entity_ids": list(self._spec.source_entities),
                "controller_status": self._manager.equipment.statuses.get(self._spec.identifier, {}),
                "configuration_help": help_text}
        if modes is not None:
            attributes["native_full_output_modes"] = list(modes)
        mode = getattr(self, "_operating_mode", None)
        if mode:
            from .equipment_mode_entities import scoped_metadata, scoped_help
            attributes.update(scoped_metadata(self._manager, self._spec, mode, self._key, locale))
            attributes["configuration_help"] = scoped_help(
                self._key, locale, attributes["configuration_help"],
            )
        # Localize per displayed card language, independently of the selected
        # announcement language. Only the current controller's help travels
        # with its state; this does not alter announcements or physical logic.
        translated = {}
        for language in presentation_languages(locale):
            detail = equipment_configuration_help(key, language, modes=modes) if modes is not None else (
                equipment_configuration_help(key, language))
            translated[language] = scoped_help(key, language, detail) if mode else detail
        attributes["configuration_help_locales"] = translated
        if key in ("door_closed_eco", "door_start_coordination"):
            from .equipment_door_policy import configured, words
            help_key = "eco_help" if key == "door_closed_eco" else "coord_help"
            attributes.update(
                setting_key=key,
                door_device_policy=True,
                door_room_configured=configured(self._manager, self._spec),
                setting_label=words(locale)[key],
                setting_label_locales={lang: words(lang)[key] for lang in presentation_languages(locale)},
                configuration_help=words(locale)[help_key],
                configuration_help_locales={
                    lang: words(lang)[help_key] for lang in presentation_languages(locale)
                },
            )
            if key == "door_start_coordination":
                attrs = ("inherit", "observe", "conflicts", "shared")
                attributes["option_labels"] = {key: words(locale)[key] for key in attrs}
                attributes["option_labels_locales"] = {
                    lang: {key: words(lang)[key] for key in attrs}
                    for lang in presentation_languages(locale)
                }
        return attributes

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        from .equipment_updates import EquipmentStateWrites, controller_signal
        if getattr(self._manager, "_equipment_state_writes", None) is None:
            self._manager._equipment_state_writes = EquipmentStateWrites(self.hass.loop)
        self._state_writes = self._manager._equipment_state_writes
        self._native_update_unsub = None
        self._native_watch_enabled = False
        self._native_watched_ids = frozenset()
        self.async_on_remove(self._equipment_cleanup)
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}", self._equipment_update))
        self.async_on_remove(async_dispatcher_connect(
            self.hass, controller_signal(self._manager.entry.entry_id,
                                         self._spec.identifier), self._equipment_update))

    @callback
    def _equipment_cleanup(self):
        self._state_writes.discard(self)
        self._state_writes = None
        if self._native_update_unsub is not None:
            self._native_update_unsub()
            self._native_update_unsub = None
        self._native_watch_enabled = False
        self._native_watched_ids = frozenset()

    @callback
    def _watch_native_updates(self) -> None:
        """Only this controller's exact physical sources and selected supply."""
        self._native_watch_enabled = True
        self._bind_native_updates()

    @callback
    def _bind_native_updates(self):
        from homeassistant.helpers.event import async_track_state_change_event
        upstream = model.power_switch_entity(self._manager, self._spec)
        sources = set(self._spec.source_entities)
        if isinstance(upstream, str) and upstream.startswith("switch."):
            sources.add(upstream)
        watched = frozenset(sources)
        if self._native_watched_ids == watched:
            return
        if self._native_update_unsub is not None:
            self._native_update_unsub()
            self._native_update_unsub = None
        self._native_watched_ids = watched
        self._watched_upstream_switch = upstream

        @callback
        def source_changed(event):
            old, new = event.data.get("old_state"), event.data.get("new_state")
            if (old is not None and new is not None and old.state == new.state
                    and old.attributes == new.attributes):
                return
            self._equipment_update()

        if watched:
            self._native_update_unsub = async_track_state_change_event(
                self.hass, watched, source_changed)

    @callback
    def _equipment_write(self):
        self._rendering = True
        try:
            if self._native_watch_enabled:
                self._bind_native_updates()
            self._prepare_equipment_state()
            self.async_write_ha_state()
        finally:
            self._render_settings = None
            self._rendering = False

    def _prepare_equipment_state(self):
        """Refresh dynamic metadata immediately before publishing the state."""

    @callback
    def _equipment_update(self):
        if self._state_writes is not None:
            self._state_writes.request(self)
