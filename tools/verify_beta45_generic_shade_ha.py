"""HA 2026.10 real-registry smoke: native classless roller covers appear.

Inventory tests only. No cover service call or automation authorization.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import MappingProxyType

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.config_entries import ConfigEntries, ConfigEntry, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers import entity_registry as er
from custom_components.environment_manager.room_sources import choices, category
from custom_components.environment_manager.shade_cooling import eligible_shade
from custom_components.environment_manager.room_setup import RoomSetupMixin
from custom_components.environment_manager.compact_options import CompactOptionsMixin


def entry(domain, identity):
    return ConfigEntry(
        data={}, options={}, domain=domain, entry_id=identity,
        title=identity, source=SOURCE_USER, unique_id=identity,
        version=1, minor_version=1,
        discovery_keys=MappingProxyType({}), subentries_data=(),
    )


class Wizard(RoomSetupMixin, CompactOptionsMixin):
    def __init__(self, hass, room):
        self.hass = hass
        self._values = {"areas": [room]}
        self._editing = False
        self._setup_order = [room]
        self._setup_index = 0

    def async_show_form(self, **kwargs):
        return kwargs

    def async_abort(self, **kwargs):
        raise AssertionError(kwargs)

    async def _finish(self):
        raise AssertionError("Inventory test may not save or issue cover writes")


async def check(tmp):
    hass = HomeAssistant(tmp)
    hass.config_entries = ConfigEntries(hass, {})
    dr.async_setup(hass)
    await ar.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    area_registry = ar.async_get(hass)
    guests = area_registry.async_create("Gästezimmer")
    kitchen = area_registry.async_create("Küche")
    living = area_registry.async_create("Wohnzimmer")
    physical = entry("demo", "real-covers")
    hass.config_entries._entries[physical.entry_id] = physical
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    entities = {}

    for room, key, label, state, klass in [
        (guests, "ksenonas_rolo_aristera", "Ξενώνας Ρολό Δεξιά", "open", None),
        (guests, "gastezimmer_rollo_rechts_rolo_5", "Ξενώνας Ρολό Αριστερά", "open", None),
        (living, "wohnzimmer_rollo_links_rolo_3", "Καθιστικό Ρολό Αριστερά", "open", None),
        (kitchen, "kuche_rollo", "Κουζίνα Ρολό", "unknown", None),
        (guests, "garage", "Garage", "open", "garage"),
        (guests, "external_awning", "Awning", "open", "awning"),
    ]:
        product = device_registry.async_get_or_create(
            config_entry_id=physical.entry_id,
            identifiers={("demo", key)}, name=label,
        )
        device_registry.async_update_device(product.id, area_id=room.id)
        item = entity_registry.async_get_or_create(
            "cover", "demo", key, config_entry=physical, device_id=product.id,
            original_name=label, original_device_class=klass,
        )
        properties = {"supported_features": int(CoverEntityFeature.OPEN
                                                | CoverEntityFeature.CLOSE
                                                | CoverEntityFeature.SET_POSITION
                                                | CoverEntityFeature.STOP),
                      "friendly_name": label}
        if klass:
            properties["device_class"] = klass
        hass.states.async_set(item.entity_id, state, properties)
        entities[key] = item.entity_id

    expected={entities["ksenonas_rolo_aristera"],
              entities["gastezimmer_rollo_rechts_rolo_5"]}
    found={item["value"] for item in choices(hass, guests.id)["shades"]}
    assert found == expected, (found,expected)
    assert entities["wohnzimmer_rollo_links_rolo_3"] in {
        item["value"] for item in choices(hass, living.id)["shades"]}
    assert entities["kuche_rollo"] in {
        item["value"] for item in choices(hass, kitchen.id)["shades"]}

    selected = tuple(sorted(expected))
    assert all(eligible_shade(hass, guests.id, item, selected)[0] for item in selected)
    assert eligible_shade(hass, kitchen.id, entities["kuche_rollo"],
                          (entities["kuche_rollo"],)) == (False, "cover_unavailable")
    assert entities["garage"] not in found and entities["external_awning"] not in found

    # The actual options-flow room form (not merely a helper) must show them.
    wizard=Wizard(hass, guests.id)
    form=await wizard.async_step_setup_room_sources()
    assert form["step_id"] == "setup_room_sources"
    from custom_components.environment_manager.room_sources import GROUPS
    assert list(form["data_schema"].schema) == list(GROUPS)
    options = next(
        selector.config["options"]
        for field, selector in form["data_schema"].schema.items()
        if str(field) == "shades"
    )
    assert {item["value"] for item in options} == expected
    assert not any(item["value"] == entities["garage"] for item in options)

    assert not hass.services.has_service("cover","close_cover")
    await hass.async_block_till_done()
    await hass.async_stop(force=True)
    print("Home Assistant 2026.10: generic roller shutter room selector, unknown availability and garage exclusion: PASS")


if __name__ == "__main__":
    with TemporaryDirectory(prefix="hem-generic-cover-") as folder:
        asyncio.run(check(folder))
