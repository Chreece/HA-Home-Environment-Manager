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
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}", self._equipment_update))

    def _watch_native_updates(self) -> None:
        """Refresh physical facades/quiet controls only when their source changes.

        Stored controller preferences are independent of physical availability,
        while available native options and physical HVAC truth are dynamic.
        Subscribe only to this controller's exact physical inputs, never to the
        generated Manager entities, to avoid dispatcher/event feedback loops.
        """
        from homeassistant.const import EVENT_STATE_CHANGED

        selected = frozenset(self._spec.source_entities)

        @callback
        def source_changed(event):
            updated = event.data.get("entity_id")
            if (updated not in selected and
                    updated != model.settings(self._manager, self._spec).get("power_switch_entity")):
                return
            old, new = event.data.get("old_state"), event.data.get("new_state")
            if (old is not None and new is not None
                    and old.state == new.state
                    and old.attributes == new.attributes):
                return
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, source_changed)
        )

    @callback
    def _equipment_update(self):
        self.async_write_ha_state()
