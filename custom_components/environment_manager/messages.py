"""Human-readable recommendations; action language is independent of HA UI."""

from __future__ import annotations

from collections.abc import Mapping
from math import ceil, isfinite

from .logic import Reason, Recommendation
from .languages import EXTRA_LOCALES, resolve_language
from .mold_text import MOLD_NAMES
from .recommendation_text import (
    CLIMATE_WINDOW_TEXT,
    ROOM_VENTILATION_TEXT as EXTRA_ROOM_VENTILATION_TEXT,
)
from .window_open_text import WINDOW_OPEN_TEXT, WEATHER_CAUTION_CODES, ROOM_WINDOW_NAMES


TEXT = {
    "en": {
        "open": "Open {windows} in {area}: {reasons}. Outdoor conditions are suitable.",
        "close": "Close {windows} in {area}: {reasons}.",
        "title_open": "Air quality - open windows",
        "title_close": "Air quality - close windows",
        "inside": "{name} is high ({value})",
        "outside": "outdoor {name} is high ({value})",
        "no_outdoor_data": "no outdoor air-quality sensor is available",
        "unavailable_outdoor": "outdoor reading unavailable: {name}",
        "no_weather_data": "no weather entity is available",
        "unavailable_weather": "weather information is unavailable",
        "weather_condition": "weather conditions: {value}",
        "inside_passive_cooling": "outdoor air could cool the room ({value} cooler)",
        "title_climate_window": "Window airing may reduce mechanical conditioning",
        "climate_window_cool": "outside air is {value} cooler; briefly opening a window could reduce mechanical cooling",
        "climate_window_heat": "outside air is {value} warmer and can approach the heating target; briefly opening a window could help",
        "climate_window_dry": "outdoor air carries {value} less water vapour per kilogram of dry air; briefly opening a window could reduce humidity",
        "weather_cold": "low outside temperature ({value})",
        "weather_hot": "high outside temperature ({value})",
        "weather_humid": "very humid outside ({value})",
        "weather_wind": "strong wind outside ({value})",
        "active_warning": "active weather warning: {name}",
        "unavailable_warning": "weather warning status unavailable: {name}",
    },
    "de": {
        "open": "Öffne {windows} in {area}: {reasons}. Die Außenbedingungen sind geeignet.",
        "close": "Schließe {windows} in {area}: {reasons}.",
        "title_open": "Luftqualität - Fenster öffnen",
        "title_close": "Luftqualität - Fenster schließen",
        "inside": "{name} ist erhöht ({value})",
        "outside": "{name} draußen ist erhöht ({value})",
        "no_outdoor_data": "kein Außenluftsensor verfügbar",
        "unavailable_outdoor": "Außenmesswert nicht verfügbar: {name}",
        "no_weather_data": "keine Wetterentität verfügbar",
        "unavailable_weather": "Wetterdaten nicht verfügbar",
        "weather_condition": "Wetterbedingungen: {value}",
        "inside_passive_cooling": "Außenluft könnte den Raum kühlen ({value} kühler)",
        "title_climate_window": "Fensterlüftung könnte die Klimatisierung entlasten",
        "climate_window_cool": "die Außenluft ist {value} kühler; kurzes Fensterlüften könnte die Kühlung entlasten",
        "climate_window_heat": "die Außenluft ist {value} wärmer und kann dem Heizsollwert nahekommen; kurzes Lüften könnte helfen",
        "climate_window_dry": "die Außenluft enthält {value} weniger Wasserdampf je Kilogramm trockener Luft; kurzes Lüften könnte Feuchtigkeit abführen",
        "weather_cold": "niedrige Außentemperatur ({value})",
        "weather_hot": "hohe Außentemperatur ({value})",
        "weather_humid": "hohe Luftfeuchte draußen ({value})",
        "weather_wind": "starker Wind draußen ({value})",
        "active_warning": "aktive Wetterwarnung: {name}",
        "unavailable_warning": "Status der Wetterwarnung unbekannt: {name}",
    },
    "el": {
        "open": "Άνοιξε {windows} στο {area}: {reasons}. Οι εξωτερικές συνθήκες είναι κατάλληλες.",
        "close": "Κλείσε {windows} στο {area}: {reasons}.",
        "title_open": "Ποιότητα αέρα - άνοιγμα παραθύρων",
        "title_close": "Ποιότητα αέρα - κλείσιμο παραθύρων",
        "inside": "Αυξημένο {name} ({value})",
        "outside": "Αυξημένο {name} έξω ({value})",
        "no_outdoor_data": "δεν υπάρχει διαθέσιμος αισθητήρας εξωτερικού αέρα",
        "unavailable_outdoor": "μη διαθέσιμη εξωτερική μέτρηση: {name}",
        "no_weather_data": "δεν υπάρχουν διαθέσιμα δεδομένα καιρού",
        "unavailable_weather": "μη διαθέσιμα δεδομένα καιρού",
        "weather_condition": "καιρικές συνθήκες: {value}",
        "inside_passive_cooling": "ο εξωτερικός αέρας μπορεί να δροσίσει ({value} ψυχρότερος)",
        "title_climate_window": "Το άνοιγμα παραθύρου μπορεί να μειώσει τη χρήση κλιματισμού",
        "climate_window_cool": "ο εξωτερικός αέρας είναι {value} ψυχρότερος· ο σύντομος αερισμός μπορεί να βοηθήσει",
        "climate_window_heat": "ο εξωτερικός αέρας είναι {value} θερμότερος και πλησιάζει τον επιθυμητό στόχο· ο σύντομος αερισμός μπορεί να βοηθήσει",
        "climate_window_dry": "ο εξωτερικός αέρας έχει {value} λιγότερους υδρατμούς ανά κιλό ξηρού αέρα· ο σύντομος αερισμός μπορεί να απομακρύνει υγρασία",
        "weather_cold": "χαμηλή εξωτερική θερμοκρασία ({value})",
        "weather_hot": "υψηλή εξωτερική θερμοκρασία ({value})",
        "weather_humid": "υψηλή εξωτερική υγρασία ({value})",
        "weather_wind": "ισχυρός εξωτερικός άνεμος ({value})",
        "active_warning": "ενεργή προειδοποίηση καιρού: {name}",
        "unavailable_warning": "άγνωστη κατάσταση προειδοποίησης καιρού: {name}",
    },
    "fr": {
        "open": "Ouvrez {windows} dans {area} : {reasons}. Les conditions extérieures conviennent.",
        "close": "Fermez {windows} dans {area} : {reasons}.",
        "title_open": "Qualité de l'air - ouvrir les fenêtres",
        "title_close": "Qualité de l'air - fermer les fenêtres",
        "inside": "{name} intérieur est élevé ({value})",
        "outside": "{name} extérieur est élevé ({value})",
        "no_outdoor_data": "aucune mesure de la qualité de l'air extérieur",
        "unavailable_outdoor": "mesure extérieure indisponible : {name}",
        "no_weather_data": "aucune entité météo disponible",
        "unavailable_weather": "données météo indisponibles",
        "weather_condition": "conditions météo : {value}",
        "weather_cold": "température extérieure basse ({value})",
        "weather_hot": "température extérieure élevée ({value})",
        "weather_humid": "humidité extérieure élevée ({value})",
        "weather_wind": "vent fort ({value})",
        "active_warning": "alerte météo active : {name}",
        "unavailable_warning": "alerte météo indisponible : {name}",
    },
    "es": {
        "open": "Abre {windows} en {area}: {reasons}. Las condiciones exteriores son adecuadas.",
        "close": "Cierra {windows} en {area}: {reasons}.",
        "title_open": "Calidad del aire - abrir ventanas",
        "title_close": "Calidad del aire - cerrar ventanas",
        "inside": "{name} interior elevado ({value})",
        "outside": "{name} exterior elevado ({value})",
        "no_outdoor_data": "no hay sensores de aire exterior disponibles",
        "unavailable_outdoor": "medición exterior no disponible: {name}",
        "no_weather_data": "no hay entidad meteorológica disponible",
        "unavailable_weather": "datos meteorológicos no disponibles",
        "weather_condition": "condiciones meteorológicas: {value}",
        "weather_cold": "baja temperatura exterior ({value})",
        "weather_hot": "alta temperatura exterior ({value})",
        "weather_humid": "humedad exterior alta ({value})",
        "weather_wind": "viento fuerte ({value})",
        "active_warning": "alerta meteorológica activa: {name}",
        "unavailable_warning": "estado de alerta meteorológica desconocido: {name}",
    },
}


def _extra_messages(entry: dict) -> dict[str, str]:
    ui = entry["ui"]
    say = entry["speech"]
    missing = entry["card"][5]
    return {
        "open": say[0],
        "close": say[1],
        "title_open": f"{ui[7]} - {ui[14]} {ui[12]}",
        "title_close": f"{ui[7]} - {ui[15]} {ui[12]}",
        "inside": say[2],
        "outside": say[3],
        "no_outdoor_data": f"{ui[3]} - {missing}",
        "unavailable_outdoor": f"{ui[3]} - {missing}: {{name}}",
        "no_weather_data": f"{ui[4]} - {missing}",
        "unavailable_weather": f"{ui[4]} - {missing}",
        "weather_condition": f"{ui[4]}: {{value}}",
        "weather_cold": f"{ui[18]} - {{value}}",
        "weather_hot": f"{ui[18]} - {{value}}",
        "weather_humid": f"{ui[18]} - {{value}}",
        "weather_wind": f"{ui[4]} - {{value}}",
        "active_warning": f"{ui[4]}: {{name}}",
        "unavailable_warning": f"{ui[4]} - {missing}: {{name}}",
    }


TEXT.update({tag: _extra_messages(locale) for tag, locale in EXTRA_LOCALES.items()})
# These older patterns added a window noun around a contact-name placeholder.
# Opening now uses a translated generic noun, not any selected contact name.
TEXT["tr"]["open"] = "{area} içindeki {windows} açın: {reasons}. Dış koşullar havalandırma için uygun."
TEXT["hu"]["open"] = "Nyisd ki {windows} itt: {area}. Ok: {reasons}. A kinti körülmények megfelelőek."
TEXT["fa"]["open"] = "{windows} را در {area} باز کنید: {reasons}. شرایط بیرون برای تهویه مناسب است."
TEXT["ko"]["open"] = "{area}의 {windows}을 여세요. 이유: {reasons}. 실외 환경이 환기에 적합합니다."
for _language, _templates in CLIMATE_WINDOW_TEXT.items():
    TEXT[_language].update(_templates)
for _language, _templates in WINDOW_OPEN_TEXT.items():
    TEXT[_language].update(zip(WEATHER_CAUTION_CODES, _templates["weather"]))
    TEXT[_language]["weather_heat_loss"] = _templates["heat_loss"]
    TEXT[_language]["outside_conditions_not_verified"] = _templates["unverified"]
    for _code in ("outside_more_moisture", "aqi_scale_unconfigured", "outside_pollen",
                  "climate_window_humidify", "climate_window_filtration"):
        TEXT[_language][_code] = _templates[_code]
    TEXT[_language]["inside_passive_cooling"] = TEXT[_language]["climate_window_cool"]


ROOM_VENTILATION_TEXT = {
    "en": {
        "refresh_title": "Fresh-air reminder",
        "wake": "After waking in {area}, consider airing the room briefly. Indoor air quality is not measured here, so this is a timing reminder, not a pollution alert. Outdoor conditions currently allow ventilation.",
        "return": "After returning to {area} following a long vacancy, consider airing the room briefly. There is no indoor air-quality measurement; this reminder is based on occupancy timing. Outdoor conditions currently allow ventilation.",
        "heat_title": "Close window · heating",
        "cool_title": "Close window · cooling",
        "heat": "Please close {windows} in {area} to avoid unnecessary heating. With the window open, the room is cooling toward its heating setpoint ({value}).",
        "cool": "Please close {windows} in {area} to avoid unnecessary cooling. With the window open, the room is warming toward its cooling setpoint ({value}).",
        "reason_heat": "Room cooling toward the heating setpoint ({value})",
        "reason_cool": "Room warming toward the cooling setpoint ({value})",
    },
    "de": {
        "refresh_title": "Frischluft-Erinnerung",
        "wake": "Nach dem Aufwachen in {area}: Lüfte den Raum bei Gelegenheit kurz. Da dort kein Luftqualitätssensor vorhanden ist, ist dies eine zeitbasierte Erinnerung und keine Schadstoffwarnung. Die Außenbedingungen lassen Lüften derzeit zu.",
        "return": "Nach längerer Abwesenheit aus {area}: Lüfte den Raum bei Gelegenheit kurz. Ohne Luftqualitätssensor ist dies nur eine zeitbasierte Erinnerung. Die Außenbedingungen lassen Lüften derzeit zu.",
        "heat_title": "Fenster schließen · Heizen",
        "cool_title": "Fenster schließen · Kühlen",
        "heat": "Bitte schließe {windows} in {area}, um Heizenergie zu sparen. Bei offenem Fenster sinkt die Raumtemperatur in Richtung Heizsollwert ({value}).",
        "cool": "Bitte schließe {windows} in {area}, um Kühlenergie zu sparen. Bei offenem Fenster steigt die Raumtemperatur in Richtung Kühlsollwert ({value}).",
        "reason_heat": "Raumtemperatur sinkt zum Heizsollwert ({value})",
        "reason_cool": "Raumtemperatur steigt zum Kühlsollwert ({value})",
    },
    "el": {
        "refresh_title": "Υπενθύμιση αερισμού",
        "wake": "Μετά το ξύπνημα στο {area}, σκέψου να αερίσεις για λίγο το δωμάτιο. Δεν υπάρχει αισθητήρας ποιότητας αέρα στον χώρο, επομένως πρόκειται για υπενθύμιση βάσει χρόνου και όχι για ένδειξη ρύπανσης. Οι εξωτερικές συνθήκες επιτρέπουν τον αερισμό.",
        "return": "Μετά από μεγάλη απουσία από το {area}, σκέψου να αερίσεις για λίγο το δωμάτιο. Χωρίς αισθητήρα ποιότητας αέρα, η υπενθύμιση βασίζεται στην παρουσία και όχι σε μετρημένους ρύπους. Οι εξωτερικές συνθήκες επιτρέπουν τον αερισμό.",
        "heat_title": "Κλείσιμο παραθύρου · Θέρμανση",
        "cool_title": "Κλείσιμο παραθύρου · Ψύξη",
        "heat": "Κλείσε {windows} στο {area} για εξοικονόμηση ενέργειας. Με ανοιχτό παράθυρο η θερμοκρασία πέφτει κοντά στον στόχο θέρμανσης ({value}).",
        "cool": "Κλείσε {windows} στο {area} για εξοικονόμηση ενέργειας. Με ανοιχτό παράθυρο η θερμοκρασία ανεβαίνει κοντά στον στόχο ψύξης ({value}).",
        "reason_heat": "Πτώση θερμοκρασίας προς τον στόχο θέρμανσης ({value})",
        "reason_cool": "Άνοδος θερμοκρασίας προς τον στόχο ψύξης ({value})",
    },
}
ROOM_VENTILATION_TEXT.update(EXTRA_ROOM_VENTILATION_TEXT)
ROOM_VENTILATION_CODES = frozenset((
    "air_refresh_wake", "air_refresh_return",
    "window_heat_loss", "window_cooling_loss",
))


def language_code(language: str | None) -> str:
    return resolve_language(language)


RH_FALLBACK_REASON_NAMES = {
    "en": "average room relative humidity (RH fallback)",
    "de": "mittlere relative Raumfeuchte (RH-Ersatzwert)",
    "el": "μέση σχετική υγρασία χώρου (εφεδρική μέτρηση)",
    "fr": "humidité relative moyenne (valeur de secours)",
    "es": "humedad relativa media (valor de respaldo)",
}
RH_FALLBACK_SOURCE_LABEL = "Average room relative humidity (fallback)"


def explain(reason: Reason, language: str) -> str:
    if reason.code in ("window_heat_loss", "window_cooling_loss"):
        t = ROOM_VENTILATION_TEXT.get(language_code(language),
                                      ROOM_VENTILATION_TEXT["en"])
        return t["reason_heat" if reason.code=="window_heat_loss"
                 else "reason_cool"].format(value=reason.value)
    if reason.code in ("air_refresh_wake", "air_refresh_return"):
        return ROOM_VENTILATION_TEXT.get(language_code(language),
                                          ROOM_VENTILATION_TEXT["en"])["refresh_title"]
    if reason.code == "inside_mold":
        return f"{MOLD_NAMES.get(language_code(language), MOLD_NAMES['en'])}: {reason.value}"
    dictionary = TEXT[language_code(language)]
    if (reason.code == "inside_humidity"
            and reason.label == RH_FALLBACK_SOURCE_LABEL):
        return dictionary["inside"].format(
            name=RH_FALLBACK_REASON_NAMES.get(language_code(language), "RH"),
            value=reason.value,
        )
    template = dictionary.get(reason.code)
    if template is None:
        if reason.code.startswith("climate_window_"):
            template = TEXT["en"].get(reason.code, "{name}: {value}")
        elif reason.code.startswith("inside_"):
            template = dictionary["inside"]
        elif reason.code.startswith("outside_"):
            template = dictionary["outside"]
        else:
            template = reason.code.replace("_", " ")
    return template.format(name=reason.label, value=reason.value)


def _with_window_wait(rec: Recommendation, message: str, language: str) -> str:
    """Describe a bounded opportunity without claiming that output stopped."""
    if rec.action != "open":
        return message
    translated = WINDOW_OPEN_TEXT[language_code(language)]
    device_lines = []
    seen = set()
    waiting_devices = getattr(rec, "wait_devices", ()) or ()
    for device in waiting_devices:
        if not isinstance(device, Mapping):
            continue
        remaining = device.get("remaining_seconds")
        name = device.get("friendly_name")
        entity = device.get("entity_id")
        if (not isinstance(name, str) or not name.strip()
                or isinstance(remaining, bool) or not isinstance(remaining, (int, float))
                or not isfinite(remaining) or not 0 < remaining <= 30 * 60):
            continue
        key = (entity, name, remaining)
        if key in seen:
            continue
        seen.add(key)
        minutes = ceil(remaining / 60)
        template = (translated.get("device_wait_one", translated["device_wait"])
                    if minutes == 1 else translated["device_wait"])
        device_lines.append(template.format(
            device=name, area=rec.area_name, minutes=minutes,
        ))
    if device_lines:
        return " ".join((message, *device_lines))
    if waiting_devices:
        return message
    # Retain the legacy room-level wording only when no per-device deadline
    # was supplied. Native device waits always list the exact eligible device.
    seconds = getattr(rec, "wait_seconds", 0)
    if (isinstance(seconds, bool)
            or not isinstance(seconds, (int, float)) or not isfinite(seconds)
            or not 0 < seconds <= 30 * 60):
        return message
    minutes = ceil(seconds / 60)
    suffix = translated.get("wait_one", translated["wait"]).format(minutes=minutes) if minutes == 1 else (
        translated["wait"].format(minutes=minutes)
    )
    return f"{message} {suffix}"


def announcement(rec: Recommendation, language: str) -> tuple[str, str]:
    generic_windows = ROOM_WINDOW_NAMES[language_code(language)]
    windows = (", ".join(w.name for w in rec.windows if w.opened is True)
               or generic_windows) if rec.action == "close" else generic_windows
    cautions = getattr(rec, "cautions", ())
    if (rec.reasons and rec.reasons[0].code in ROOM_VENTILATION_CODES
            and not (rec.action == "open" and cautions)):
        code = rec.reasons[0].code
        translated = ROOM_VENTILATION_TEXT.get(language_code(language),
                                                ROOM_VENTILATION_TEXT["en"])
        if code.startswith("air_refresh_"):
            title = translated["refresh_title"]
            content = translated["wake" if code=="air_refresh_wake" else "return"]
            message = content.format(area=rec.area_name)
            if len(rec.reasons) > 1:
                message += " " + "; ".join(explain(reason, language) for reason in rec.reasons[1:]) + "."
            return title, _with_window_wait(rec, message, language)
        kind = "heat" if code=="window_heat_loss" else "cool"
        message = translated[kind].format(
            windows=windows, area=rec.area_name,
            value=rec.reasons[0].value,
        )
        if len(rec.reasons) > 1:
            message += " " + "; ".join(explain(reason, language) for reason in rec.reasons[1:]) + "."
        return translated[kind+"_title"], message
    t = TEXT[language_code(language)]
    # Every requested action explains its actual measured causes, including
    # a fourth pollutant or an additional weather reason that affects safety.
    reasons = "; ".join(explain(reason, language) for reason in rec.reasons)
    title = t[f"title_{rec.action}"]
    if rec.action=="open" and any(
        item.code.startswith("climate_window_") for item in rec.reasons
    ):
        title = t.get("title_climate_window", TEXT["en"]["title_climate_window"])
    if rec.action == "open" and cautions:
        # Never truncate the outdoor caution list or retain the ordinary
        # OPEN template's claim that outside conditions are suitable.
        message = WINDOW_OPEN_TEXT[language_code(language)]["conditional_open"].format(
            windows=windows, area=rec.area_name, reasons=reasons,
            cautions="; ".join(explain(reason, language) for reason in cautions),
        )
    else:
        message = t[rec.action].format(
            windows=windows, area=rec.area_name, reasons=reasons,
        )
    return title, _with_window_wait(rec, message, language)
