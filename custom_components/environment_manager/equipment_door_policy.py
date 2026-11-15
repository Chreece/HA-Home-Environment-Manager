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
        "eco_help": "What it does: When this room is empty and its selected doors stay closed, HEM may use this device's configured Eco targets instead of its normal Home targets, reducing unnecessary operation. It does not force an immediate power-off.\n\nWhen it applies: All selected doors must be verified closed for two minutes, the room verified empty, someone confirmed home, windows verified closed, and temperature/humidity within safe limits. Sleep and Prepare for Arrival have priority. Missing evidence never enables Eco; device protections still apply.",
        "coord_help": "What it does: Helps prevent unnecessary or conflicting operation between devices in two rooms connected by an open interior door. For example, it may briefly delay starting heating if a connected room is already cooling. It NEVER starts, stops or changes the other device.\n\nWhen it works: Only for this device's NEW Automatic start, with a verified linked interior door open for at least 30 seconds, a suitable already-running device in the other room, and non-urgent verified local conditions. A delay cannot exceed three minutes. Shared operation also checks measured improvement after one minute and releases the delay if evidence is insufficient. Closed doors cause no coordination.\n\nChoosing «Use each door's existing rule» follows the older Room Settings policy for each connected door; «No coordination» disables waiting for this device. The choices below explain the other policies.",
        "inherit": "Use each door's existing rule",
        "observe": "No coordination",
        "conflicts": "Delay opposing starts",
        "shared": "Coordinate eligible starts",
    },
    "el": {
        "door_closed_eco": "Eco με κλειστή πόρτα και άδειο δωμάτιο",
        "door_start_coordination": "Συντονισμός εκκινήσεων μέσω ανοιχτής πόρτας",
        "eco_help": "Τι κάνει: Όταν το δωμάτιο είναι άδειο και οι πόρτες του παραμένουν κλειστές, το HEM μπορεί να χρησιμοποιήσει τους οικονομικούς στόχους Eco μόνο για αυτή τη συσκευή, αντί για τους συνηθισμένους στόχους Home. Δεν την κλείνει υποχρεωτικά αμέσως.\n\nΠότε ισχύει: Όλες οι επιλεγμένες πόρτες πρέπει να είναι επιβεβαιωμένα κλειστές για δύο λεπτά, το δωμάτιο άδειο, κάποιος να βρίσκεται στο σπίτι, τα παράθυρα κλειστά και οι τιμές θερμοκρασίας/υγρασίας ασφαλείς. Ο ύπνος και η Προετοιμασία άφιξης έχουν προτεραιότητα. Άγνωστα δεδομένα δεν ενεργοποιούν Eco· ισχύουν πάντα οι προστασίες της συσκευής.",
        "coord_help": "Τι κάνει: Προσπαθεί να αποφύγει άσκοπη ή αντικρουόμενη λειτουργία συσκευών σε δύο δωμάτια που επικοινωνούν μέσω ανοιχτής εσωτερικής πόρτας. Για παράδειγμα, μπορεί να καθυστερήσει λίγο την εκκίνηση θέρμανσης όταν στο διπλανό δωμάτιο λειτουργεί ήδη ψύξη. ΔΕΝ ανοίγει, κλείνει ή αλλάζει τη δεύτερη συσκευή.\n\nΠότε λειτουργεί: Μόνο σε ΝΕΑ αυτόματη εκκίνηση αυτής της συσκευής, όταν έχει οριστεί σύνδεση των δύο χώρων, η πόρτα είναι επιβεβαιωμένα ανοιχτή επί 30 δευτερόλεπτα και λειτουργεί ήδη κατάλληλη συσκευή στον άλλο χώρο. Η ανάγκη εδώ πρέπει να μην είναι επείγουσα. Η αναμονή διαρκεί το πολύ τρία λεπτά. Στον κοινό συντονισμό ελέγχει αν βελτιώθηκαν πραγματικά οι μετρήσεις μετά από ένα λεπτό· διαφορετικά συνεχίζει κανονικά. Με κλειστή πόρτα δεν γίνεται συντονισμός.\n\nΗ επιλογή «Χρήση κανόνων κάθε πόρτας» εφαρμόζει τους ήδη αποθηκευμένους κανόνες κάθε συνδεδεμένης πόρτας, αν υπάρχουν, χωρίς να τους αλλάζει. Η επιλογή «Χωρίς συντονισμό» καταργεί την αναμονή για αυτή τη συσκευή. Παρακάτω εξηγείται τι κάνει καθεμία από τις επιλογές.",
        "inherit": "Χρήση κανόνων κάθε πόρτας",
        "observe": "Χωρίς συντονισμό",
        "conflicts": "Καθυστέρηση αντίθετων εκκινήσεων",
        "shared": "Συντονισμός επιτρεπόμενων εκκινήσεων",
    },
    "de": {
        "door_closed_eco": "Eco bei geschlossener Tür und leerem Raum",
        "door_start_coordination": "Gerätestarts über offene Türen koordinieren",
        "eco_help": "Wirkung: Wenn der Raum leer und seine ausgewählten Türen geschlossen sind, kann HEM für dieses Gerät die sparsameren Eco-Sollwerte statt der normalen Home-Sollwerte verwenden. Es wird dadurch nicht sofort zwangsweise ausgeschaltet.\n\nVoraussetzungen: Alle gewählten Türen seit zwei Minuten nachweislich geschlossen, Raum nachweislich leer, jemand zu Hause, Fenster bestätigt geschlossen, sichere Temperatur/Feuchte. Schlaf und Ankunftsvorbereitung haben Vorrang. Fehlende Messwerte aktivieren kein Eco; Geräteschutz bleibt gültig.",
        "coord_help": "Wirkung: Vermeidet unnötige oder gegensätzliche Gerätearbeit zwischen zwei Räumen mit offener Innentür. Beispielsweise kann ein neuer Heizstart kurz warten, wenn im verbundenen Raum bereits gekühlt wird. Das andere Gerät wird NIEMALS ein- oder ausgeschaltet oder umgestellt.\n\nVoraussetzungen: Nur ein NEUER Automatikstart dieses Geräts, eine ausdrücklich verknüpfte Innentür seit mindestens 30 Sekunden bestätigt offen, ein geeignetes laufendes Nachbargerät und kein dringender lokaler Bedarf. Die Wartezeit beträgt höchstens drei Minuten. Bei gemeinsamer Nutzung wird nach einer Minute eine tatsächliche Messwertverbesserung geprüft; ohne Nachweis wird die Verzögerung freigegeben. Bei geschlossener Tür gibt es keine Koordinierung.\n\n«Bestehende Regeln jeder Tür verwenden» übernimmt die bisherigen Regeln der einzelnen verbundenen Tür. «Keine Koordinierung» verzögert dieses Gerät nie. Die folgenden Optionen werden einzeln erläutert.",
        "inherit": "Bestehende Regeln jeder Tür verwenden",
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
    rooms = manager.settings.get("climate_rooms", {})
    room = rooms.get(spec.area_id, {}) if isinstance(rooms, Mapping) else {}
    return isinstance(room, Mapping) and room.get("closed_door_eco") is True


def effective_coordination(raw):
    choice = raw.get("door_start_coordination", "inherit")
    return choice if choice in COORDINATION_OPTIONS else "observe"
