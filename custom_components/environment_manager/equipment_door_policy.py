"""Per-physical-controller door preferences; no native device or door commands.

Only a user-selected and still verified contact in the controller's own HA
Area exposes these settings. Legacy room options remain a fallback until the
individual controller receives an explicit preference. The coordination
selector applies to a device's new Automatic starts across a VERIFIED OPEN
interior connection, never to closed doors or a peer's actuator.
"""
from __future__ import annotations

from collections.abc import Mapping

COORDINATION_OPTIONS = ("inherit", "observe", "conflicts", "shared")
DEVICE_DOOR_KEYS = frozenset(("door_closed_eco", "door_start_coordination"))

WORDS = {
    "en": {
        "door_closed_eco": "Eco when door closed and room unoccupied",
        "door_start_coordination": "Device start coordination across open doors",
        "eco_help": "For THIS device only. Eco requires every selected room door securely closed for 120 seconds, verified room vacancy, someone home, safe room humidity and temperature, closed windows and no sleep or arrival priority. Unknown or missing evidence never authorizes Eco. Existing control and protection rules still apply.",
        "coord_help": "For THIS device's new Automatic starts only. A verified interior door must be explicitly linked to another room, open for at least 30 seconds, and a qualified peer must already be running. A start delay is bounded to 3 minutes and never starts or stops another device. CLOSED doors never synchronize starts. The inherited choice preserves the previously configured per-door coordination policy.",
        "inherit": "Follow existing door policy",
        "observe": "No coordination",
        "conflicts": "Delay opposing starts",
        "shared": "Coordinate eligible starts",
    },
    "el": {
        "door_closed_eco": "Eco με κλειστή πόρτα και άδειο δωμάτιο",
        "door_start_coordination": "Συντονισμός εκκινήσεων μέσω ανοιχτής πόρτας",
        "eco_help": "Ισχύει ΜΟΝΟ για αυτή τη συσκευή. Το Eco απαιτεί όλες οι επιλεγμένες πόρτες να είναι επιβεβαιωμένα κλειστές για 120 δευτερόλεπτα, αξιόπιστη απουσία από το δωμάτιο, κάποιον στο σπίτι, ασφαλή υγρασία και θερμοκρασία, κλειστά παράθυρα και καμία προτεραιότητα ύπνου ή άφιξης. Άγνωστα δεδομένα δεν ενεργοποιούν Eco. Οι υπόλοιποι έλεγχοι ασφαλείας παραμένουν ενεργοί.",
        "coord_help": "Ισχύει ΜΟΝΟ για νέες αυτόματες εκκινήσεις αυτής της συσκευής. Απαιτείται ρητά συνδεδεμένη εσωτερική πόρτα προς άλλο χώρο, επιβεβαιωμένα ανοιχτή για τουλάχιστον 30 δευτερόλεπτα, και κατάλληλη συσκευή ήδη σε λειτουργία στον άλλο χώρο. Η αναμονή δεν ξεπερνά τα 3 λεπτά και δεν ενεργοποιεί ή απενεργοποιεί άλλες συσκευές. Οι ΚΛΕΙΣΤΕΣ πόρτες δεν προκαλούν συντονισμό. Η κληρονομημένη επιλογή διατηρεί την παλιά ρύθμιση ανά πόρτα.",
        "inherit": "Διατήρηση πολιτικής πόρτας",
        "observe": "Χωρίς συντονισμό",
        "conflicts": "Καθυστέρηση αντίθετων εκκινήσεων",
        "shared": "Συντονισμός επιτρεπόμενων εκκινήσεων",
    },
    "de": {
        "door_closed_eco": "Eco bei geschlossener Tür und leerem Raum",
        "door_start_coordination": "Gerätestarts über offene Türen koordinieren",
        "eco_help": "Gilt NUR für dieses Gerät. Eco benötigt alle gewählten Türen seit 120 Sekunden nachweislich geschlossen, verlässlich leeren Raum, Anwesenheit im Haus, sichere Feuchte und Temperatur, geschlossene Fenster und keinen Vorrang für Schlaf oder Ankunft. Fehlende oder unbekannte Nachweise erlauben kein Eco. Alle übrigen Schutzregeln gelten weiter.",
        "coord_help": "Gilt NUR für neue Automatikstarts dieses Geräts. Erforderlich sind eine ausdrücklich verknüpfte Innentür zu einem anderen Raum, mindestens 30 Sekunden nachweislich offen, sowie ein passendes bereits laufendes Gerät im anderen Raum. Die Verzögerung ist auf drei Minuten begrenzt, ohne fremde Geräte zu starten oder auszuschalten. GESCHLOSSENE Türen koordinieren keine Starts. Die Vererbungsoption bewahrt bisherige Einstellungen je Tür.",
        "inherit": "Bisherige Türregel übernehmen",
        "observe": "Keine Koordinierung",
        "conflicts": "Gegenläufige Starts verzögern",
        "shared": "Zulässige Starts koordinieren",
    },
}


def words(language):
    locale = str(language or "en").split("-")[0].split("_")[0].lower()
    return WORDS.get(locale, WORDS["en"])


def selected_room_contacts(settings, area):
    rooms = settings.get("climate_rooms", {})
    room = rooms.get(area, {}) if isinstance(rooms, Mapping) else {}
    selected = room.get("door_sensors", ()) if isinstance(room, Mapping) else ()
    if not isinstance(selected, (tuple, list)):
        return ()
    return tuple(dict.fromkeys(
        entity for entity in selected
        if isinstance(entity, str) and entity.startswith("binary_sensor.")
    ))


def configured(manager, spec):
    """Use exact selected same-Area HA door sources, including offline contacts.

    An entity moved to a different Area or reclassified as a window cannot
    enable new device policy editors. No new HA registry or device identity.
    """
    from .door_settings import editable_contact
    return any(editable_contact(manager.hass, manager.settings, spec.area_id, entity)
               for entity in selected_room_contacts(manager.settings, spec.area_id))


def effective_eco(manager, spec, raw):
    """A per-device explicit Boolean overrides the old shared room setting."""
    explicit = raw.get("door_closed_eco")
    if type(explicit) is bool:
        return explicit
    from . import equipment_model
    return equipment_model.room_config(manager, spec).get("closed_door_eco") is True


def effective_coordination(raw):
    choice = raw.get("door_start_coordination", "inherit")
    return choice if choice in COORDINATION_OPTIONS else "observe"
