"""Room-owned door metadata controls and a small automation/diagnostic sensor."""
from __future__ import annotations

from hashlib import sha256

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, SIGNAL_UPDATED
from .door_settings import async_update, editable_contact, inventory, target_areas
from .room_doors import contact_options

WORDS = {
    "en": {"target_area": "Connects to room", "kind": "Door purpose",
           "report_timeout_minutes": "Expected report timeout", "none": "Not connected",
           "interior": "Interior", "fire": "Fire/safety door", "exterior": "Exterior",
           "status": "Door context", "removed": "Unavailable room",
           "target_help": "Optional explicit connection to another configured room. The sensor stays in its original Area. An open connection is a possible air path, not measured airflow or proof of occupancy. No doors or locks are operated.",
           "kind_help": "Declare the physical door purpose. Fire/safety and exterior doors are excluded from transfer-air suggestions. HEM never recommends holding a fire door open or operates doors or locks.",
           "timeout_help": "Minutes since the contact last reported. Leave 0 for event-only contacts: a door remaining closed is not a sensor failure. Enable only when this source reliably reports at a known interval. Expired/missing reports make the contact unknown and block door Eco."},
    "el": {"target_area": "Συνδέεται με χώρο", "kind": "Τύπος πόρτας",
           "report_timeout_minutes": "Όριο χρόνου αναφοράς", "none": "Χωρίς σύνδεση",
           "interior": "Εσωτερική", "fire": "Πυράντοχη / ασφαλείας", "exterior": "Εξωτερική",
           "status": "Κατάσταση θυρών", "removed": "Μη διαθέσιμος χώρος",
           "target_help": "Προαιρετική σύνδεση με άλλον ρυθμισμένο χώρο. Ο αισθητήρας παραμένει στον αρχικό του χώρο. Ανοιχτή σύνδεση σημαίνει πιθανή διαδρομή αέρα, όχι μετρημένη ροή ή απόδειξη παρουσίας. Δεν ελέγχονται πόρτες ή κλειδαριές.",
           "kind_help": "Δήλωσε τον πραγματικό τύπο πόρτας. Πυράντοχες/ασφαλείας και εξωτερικές πόρτες εξαιρούνται από συμβουλές μεταφοράς αέρα. Το HEM δεν προτείνει να παραμένει ανοιχτή πυράντοχη πόρτα και δεν κινεί πόρτες ή κλειδαριές.",
           "timeout_help": "Λεπτά από την τελευταία αναφορά. Άφησε 0 για αισθητήρες που αναφέρουν μόνο αλλαγές: παρατεταμένο κλείσιμο δεν σημαίνει βλάβη. Ενεργοποίησέ το μόνο για πηγές με γνωστό διάστημα αναφοράς. Εκπρόθεσμη/ελλιπής αναφορά σημαίνει άγνωστη κατάσταση και εμποδίζει το Eco πόρτας."},
    "de": {"target_area": "Verbunden mit Raum", "kind": "Türart",
           "report_timeout_minutes": "Erwartete Meldefrist", "none": "Nicht verbunden",
           "interior": "Innentür", "fire": "Brand-/Sicherheitstür", "exterior": "Außentür",
           "status": "Türkontext", "removed": "Raum nicht verfügbar",
           "target_help": "Optionale ausdrückliche Verbindung zu einem anderen eingerichteten Raum. Der Sensor bleibt seinem ursprünglichen Bereich zugeordnet. Eine offene Verbindung ist ein möglicher Luftweg, kein gemessener Luftstrom oder Anwesenheitsnachweis. Keine Tür-/Schlossbetätigung.",
           "kind_help": "Tatsächliche Türart angeben. Brand-/Sicherheits- und Außentüren sind von Überströmungshinweisen ausgeschlossen. HEM empfiehlt nie das Offenhalten einer Brandschutztür und betätigt keine Türen oder Schlösser.",
           "timeout_help": "Minuten seit der letzten Meldung. Bei Kontakten, die nur Änderungen melden, 0 lassen: Eine lange geschlossene Tür ist kein Sensorfehler. Nur bei bekanntem, verlässlichem Meldeintervall aktivieren. Abgelaufene/fehlende Meldungen ergeben Unbekannt und sperren Tür-Eco."},
}


def words(manager):
    locale = str(getattr(getattr(manager.hass, "config", None), "language", "en")).split("-")[0]
    return WORDS.get(locale, WORDS["en"])


class DoorEntity:
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:door"

    def __init__(self, manager, area, contact, key):
        self._manager, self._area, self._contact, self._key = manager, area, contact, key
        suffix = sha256(contact.encode()).hexdigest()[:16]
        self._attr_unique_id = f"{manager.entry.entry_id}_area_{area}_door_{suffix}_{key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{manager.entry.entry_id}_area_{area}")}}

    @property
    def name(self):
        state = self._manager.hass.states.get(self._contact)
        label = getattr(state, "name", None) or self._contact
        return f"{label} · {words(self._manager)[self._key]}"

    @property
    def available(self):
        return editable_contact(self._manager.hass, self._manager.settings, self._area, self._contact)

    def _config(self):
        room = self._manager.settings.get("climate_rooms", {}).get(self._area, {})
        return contact_options(room, self._contact)

    @property
    def extra_state_attributes(self):
        help_key = {"target_area": "target_help", "kind": "kind_help",
                    "report_timeout_minutes": "timeout_help"}[self._key]
        return {"setting_display_name": self.name, "setting_key": "door_" + self._key,
                "door_source_entity": self._contact, "door_setting_key": self._key,
                "configuration_help": words(self._manager)[help_key]}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}", self._update))

    @callback
    def _update(self):
        self.async_write_ha_state()


class DoorSelect(DoorEntity, SelectEntity):
    def _choices(self):
        text = words(self._manager)
        if self._key == "kind":
            return {text[key]: key for key in ("interior", "fire", "exterior")}
        choices = {text["none"]: None}
        areas = target_areas(self._manager.hass, self._manager.settings, self._area)
        if self._config()["kind"] != "exterior":
            # Area IDs make same-named HA Areas unambiguous; storage always
            # uses the ID, never a translated or user-editable room title.
            choices.update({f"{name} [{area}]": area for area, name in areas.items()})
        saved = self._config()["target_area"]
        if saved is not None and saved not in choices.values():
            choices[f"{text['removed']} [{saved}]"] = saved
        return choices

    @property
    def options(self):
        return list(self._choices())

    @property
    def current_option(self):
        value = self._config()[self._key]
        return next((label for label, key in self._choices().items() if key == value), None)

    async def async_select_option(self, option):
        choices = self._choices()
        if option not in choices:
            raise ValueError("Door option changed; refresh the room settings")
        await async_update(self._manager, self._area, self._contact, self._key, choices[option])
        self.async_write_ha_state()


class DoorReportTimeout(DoorEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 10080
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX

    def __init__(self, manager, area, contact):
        super().__init__(manager, area, contact, "report_timeout_minutes")

    @property
    def native_value(self):
        return self._config()["report_timeout_minutes"]

    async def async_set_native_value(self, value):
        await async_update(self._manager, self._area, self._contact, self._key, value)
        self.async_write_ha_state()


class RoomDoorContextSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "room_door_context"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["not_configured", "open", "closed", "settling", "unknown"]
    _attr_icon = "mdi:door"

    def __init__(self, manager, area):
        self._manager, self._area = manager, area
        entry = manager.entry.entry_id
        self._attr_unique_id = f"{entry}_area_{area}_door_context"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry}_area_{area}")}}

    def _report(self):
        environment = getattr(getattr(self._manager, "plan", None), "environment", {}) or {}
        return environment.get(self._area, {}).get("door_context", {})

    @property
    def native_value(self):
        value = self._report().get("boundary", "unknown")
        return value if value in self._attr_options else "unknown"

    @property
    def extra_state_attributes(self):
        item = self._report()
        return {"contacts_complete": item.get("contacts_complete", False),
                "contact_count": len(item.get("contacts", [])),
                "unverified_contacts": [x["entity_id"] for x in item.get("contacts", [])
                                        if x.get("health") != "ok"][:16],
                "connected_rooms": item.get("connected_rooms", [])[:16],
                "advisory_codes": list(dict.fromkeys(x["code"] for x in item.get("advisories", [])))[:12],
                "quiet_boundary": item.get("quiet_boundary", False),
                "presence_recheck_hint": item.get("presence_recheck_hint", False),
                "advisory_only": True}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{SIGNAL_UPDATED}_{self._manager.entry.entry_id}", self._update))

    @callback
    def _update(self):
        self.async_write_ha_state()


def select_entities(manager):
    return [DoorSelect(manager, area, contact, key)
            for area, contact in inventory(manager.hass, manager.settings)
            for key in ("target_area", "kind")]


def number_entities(manager):
    return [DoorReportTimeout(manager, area, contact)
            for area, contact in inventory(manager.hass, manager.settings)]


def sensor_entities(manager):
    return [RoomDoorContextSensor(manager, area)
            for area in sorted({area for area, _ in inventory(manager.hass, manager.settings)})]
