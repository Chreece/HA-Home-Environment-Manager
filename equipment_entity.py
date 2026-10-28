"""Shared push updates for logical managed-device entities."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATED
from . import equipment_model as model
from .equipment_text import DEVICE_HELP
from .equipment_name_catalog import localized_equipment_name


class EquipmentEntity:
    """Mixin: all entities attach to the existing Area-hub child device."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def _equipment_init(self, manager, spec, key):
        self._manager, self._spec, self._key = manager, spec, key
        self._attr_unique_id = f"{spec.identifier}_{key}"
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

    @property
    def controller_settings(self):
        return model.settings(self._manager, self._spec)

    @property
    def extra_state_attributes(self):
        locale = self._manager.settings.get("language", "auto")
        if locale == "auto":
            locale = getattr(getattr(self._manager.hass, "config", None), "language", "en")
        locale = str(locale).replace("_", "-").casefold()
        language = next((key for key in DEVICE_HELP if key.casefold() == locale), locale.split("-")[0])
        return {"area_id": self._spec.area_id,
                "source_device_id": self._spec.source_device_id,
                "source_entity_ids": list(self._spec.source_entities),
                "controller_status": self._manager.equipment.statuses.get(self._spec.identifier, {}),
                "configuration_help": DEVICE_HELP.get(language, DEVICE_HELP["en"])}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        from .equipment_updates import controller_signal
        self._equipment_write_handle = None
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
        if self._equipment_write_handle is not None:
            self._equipment_write_handle.cancel()
            self._equipment_write_handle = None
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
        upstream = model.settings(self._manager, self._spec).get("power_switch_entity")
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
        self._equipment_write_handle = None
        self.async_write_ha_state()

    @callback
    def _equipment_update(self):
        if self._native_watch_enabled:
            self._bind_native_updates()
        # One serialization for this entity per loop turn even when a native
        # source, a config change and its controller status arrive together.
        if self._equipment_write_handle is None:
            self._equipment_write_handle = self.hass.loop.call_soon(self._equipment_write)
