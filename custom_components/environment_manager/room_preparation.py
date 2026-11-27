"""Temporary, independent Comfort requests for rooms on the overview."""
from __future__ import annotations

import asyncio

KEY = "room_preparation_enabled"

# These are also used by the native room switch and the overview information bubble.
TEXT = {
    "en": ("Prepare room", "Tap the empty room’s name to run eligible controllers at Comfort for up to {minutes} min. Preparation ends when someone enters, occupancy becomes unknown, or you turn this room setting off."),
    "el": ("Προετοιμασία δωματίου", "Πάτησε το όνομα του άδειου δωματίου για να λειτουργήσουν οι διαθέσιμοι ελεγκτές σε Άνεση για έως {minutes} λεπτά. Η προετοιμασία λήγει όταν μπει κάποιος, χαθεί η ένδειξη παρουσίας ή απενεργοποιήσεις τη ρύθμιση του δωματίου."),
    "de": ("Raum vorbereiten", "Tippe auf den Namen des leeren Raums, um geeignete Geräte bis zu {minutes} Minuten im Komfortprofil zu betreiben. Die Vorbereitung endet bei Anwesenheit, unbekannter Belegung oder wenn du diese Raumeinstellung ausschaltest."),
}


def words(manager):
    locale = getattr(getattr(manager.hass, "config", None), "language", "en")
    name, help_text = TEXT.get(locale.split("-")[0], TEXT["en"])
    return name, help_text.format(minutes=manager.arrival_preparation.timeout_minutes)


class RoomPreparation:
    def __init__(self, owner):
        self.owner = owner
        self.requests = {}
        self.shared = {}
        self.areas = set()

    def enabled(self, area):
        return self.owner.manager.settings.get("environment_rooms", {}).get(area, {}).get(KEY, True)

    def occupancy(self, area):
        from .occupancy_policy import room_presence
        cfg = self.owner.manager.settings.get("climate_rooms", {}).get(area, {})
        return room_presence(self.owner.hass, area, cfg, self.shared, known_areas=self.areas,
                             home_status=self.owner.home_status())[0]

    def deadline(self, area, occupancy):
        request = self.requests.get(area)
        if (request and self.owner._started and self.enabled(area)
                and occupancy == "unoccupied" and self.owner.clock() < request[0]):
            return request[0]
        return None

    def observe(self, shared, areas, observations):
        self.shared, self.areas = shared, areas
        for area in tuple(self.requests):
            status = observations[area][0] if area in observations else (
                self.occupancy(area) if area in areas else "unknown")
            if not self.deadline(area, status):
                self.clear(area)

    def clear(self, area):
        request = self.requests.pop(area, None)
        if request:
            request[1].cancel()

    def start(self, area):
        from homeassistant.exceptions import HomeAssistantError
        if (not self.owner._started or area not in self.areas or not self.enabled(area)
                or self.occupancy(area) != "unoccupied"):
            raise HomeAssistantError("Room preparation requires an enabled, empty room")
        if self.deadline(area, "unoccupied"):
            return
        self.clear(area)
        seconds = self.owner.timeout_minutes * 60
        def expire():
            self.clear(area)
            self.owner._changed()
        self.requests[area] = (self.owner.clock() + seconds,
                               asyncio.get_running_loop().call_later(seconds, expire))
        self.owner._changed()
