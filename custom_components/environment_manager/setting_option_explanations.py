"""Plain-language, option-by-option HEM selector explanations.

Only existing, code-verified select option IDs appear here. No I/O, active
device reads, control changes or translated option-name guessing at runtime.
The current HEM card language selects EN, EL or DE; all other languages use EN.
"""
from __future__ import annotations

OPTION_TEXT = {
  "equipment_door_start_coordination": {
    "inherit": [
      "Use the existing coordination policy set on each individual room door. If those doors have no active policy, starts proceed normally.",
      "Χρησιμοποιεί τη ρύθμιση συντονισμού που έχει ήδη οριστεί ξεχωριστά για κάθε πόρτα του χώρου. Αν καμία πόρτα δεν έχει ενεργό κανόνα, η συσκευή ξεκινά κανονικά.",
      "Verwendet die bisherige Koordinierungsregel jeder einzelnen Raumtür. Ohne aktive Türregel startet das Gerät ganz normal."
    ],
    "observe": [
      "Never delay this device's start because of another room. The other device remains independent.",
      "Δεν καθυστερεί ποτέ την εκκίνηση αυτής της συσκευής λόγω άλλου δωματίου. Η άλλη συσκευή λειτουργεί ανεξάρτητα.",
      "Verzögert den Start dieses Geräts nicht wegen eines anderen Raums. Das Nachbargerät bleibt unabhängig."
    ],
    "conflicts": [
      "If an already-running device across a verified open interior door is doing the opposite job (such as cooling versus heating), briefly defer this device's new Automatic start.",
      "Αν στον συνδεδεμένο χώρο λειτουργεί ήδη συσκευή με αντίθετη δράση (π.χ. ψύξη αντί θέρμανσης), καθυστερεί προσωρινά τη νέα αυτόματη εκκίνηση αυτής της συσκευής.",
      "Arbeitet ein Gerät im verbundenen Raum bereits in die entgegengesetzte Richtung (etwa Kühlen statt Heizen), wartet der neue Automatikstart dieses Geräts kurz."
    ],
    "shared": [
      "Also defer a new start when a suitable device in the connected room already performs the same task and measured conditions suggest it might help here. Check improvement after 60 seconds; start normally if evidence is missing.",
      "Μπορεί επίσης να καθυστερήσει νέα εκκίνηση όταν άλλη συσκευή στον συνδεδεμένο χώρο κάνει την ίδια δουλειά και οι μετρήσεις δείχνουν πιθανό όφελος. Ελέγχει τη βελτίωση μετά από 60 δευτερόλεπτα· χωρίς ένδειξη βοήθειας, ξεκινά κανονικά.",
      "Verzögert zusätzlich einen neuen Start, wenn im verbundenen Raum schon ein geeignetes Gerät die gleiche Aufgabe erfüllt und Messwerte auf einen möglichen Nutzen hier hindeuten. Nach 60 Sekunden wird die Verbesserung geprüft; ohne Nachweis startet das Gerät normal."
    ]
  },
  "equipment_off_state_watchdog_mode": {
    "monitor_recover": [
      "After HEM turns this device OFF, monitor suspicious room trends, notify you, and allow at most two safety-checked OFF retries, separated by at least ten minutes.",
      "Μετά από εντολή OFF του HEM, παρακολουθεί ύποπτες μεταβολές του χώρου, σε ειδοποιεί και επιτρέπει έως δύο επιπλέον ελεγμένες εντολές OFF, με απόσταση τουλάχιστον δέκα λεπτών.",
      "Nach einem HEM-AUS werden auffällige Raumverläufe beobachtet, Hinweise gesendet und höchstens zwei geprüfte AUS-Wiederholungen im Abstand von mindestens zehn Minuten erlaubt."
    ],
    "monitor_only": [
      "Observe and report a suspected continued operation, but never send extra OFF commands from this watchdog.",
      "Παρακολουθεί και σε ειδοποιεί για πιθανή συνέχιση λειτουργίας, αλλά δεν στέλνει πρόσθετες εντολές OFF μέσω αυτής της επιτήρησης.",
      "Beobachtet und meldet möglichen Weiterbetrieb, sendet aber keine zusätzlichen AUS-Befehle durch diese Überwachung."
    ],
    "disabled": [
      "Disable this optional post-shutdown check and its notifications/retries. Normal HEM device control and OFF behavior remain active.",
      "Απενεργοποιεί μόνο αυτή την πρόσθετη επιτήρηση μετά το OFF και τις ειδοποιήσεις/επαναλήψεις της. Ο κανονικός έλεγχος και η απενεργοποίηση της συσκευής συνεχίζουν να λειτουργούν.",
      "Schaltet nur die zusätzliche Nach-AUS-Überwachung und ihre Hinweise/Wiederholungen aus. Die normale HEM-Steuerung und Abschaltung bleiben aktiv."
    ]
  },
  "equipment_control_mode": {
    "existing": [
      "Leave operational control to the device's existing Home Assistant integration. HEM does not replace its control logic.",
      "Αφήνει τον λειτουργικό έλεγχο στην υπάρχουσα ενσωμάτωση της συσκευής στο Home Assistant. Το HEM δεν αντικαθιστά τη λογική της.",
      "Überlässt die Betriebssteuerung der vorhandenen Home-Assistant-Integration des Geräts. HEM ersetzt deren Regelung nicht."
    ],
    "automatic": [
      "HEM automatically selects targets and operating demand using the configured room profile, presence, sensors and safety rules.",
      "Το HEM επιλέγει αυτόματα στόχους και πότε χρειάζεται λειτουργία, με βάση το προφίλ χώρου, την παρουσία, τους αισθητήρες και τους κανόνες ασφαλείας.",
      "HEM wählt Sollwerte und Bedarf automatisch anhand von Raumprofil, Anwesenheit, Sensoren und Schutzregeln."
    ],
    "manual": [
      "Use the device's explicitly configured manual HEM targets instead of adapting the automatic profile. Physical and safety limits still apply.",
      "Χρησιμοποιεί τους χειροκίνητους στόχους που όρισες στο HEM αντί για αυτόματη επιλογή προφίλ. Τα φυσικά όρια και οι προστασίες εξακολουθούν να ισχύουν.",
      "Verwendet die ausdrücklich eingestellten manuellen HEM-Sollwerte statt automatisch gewählter Profile. Gerätegrenzen und Schutz bleiben wirksam."
    ],
    "off": [
      "HEM keeps this controller's output OFF when it has authority; native minimum ON/OFF and acknowledgement protections still apply.",
      "Το HEM διατηρεί κλειστή την έξοδο που ελέγχει, με σεβασμό στους ελάχιστους χρόνους ON/OFF και την επιβεβαίωση εντολών.",
      "HEM hält den von ihm gesteuerten Ausgang AUS; Mindestlauf-/Stillstandszeiten und Befehlsbestätigung bleiben gültig."
    ],
    "pid": [
      "HEM uses measured demand and the configured PID gains to regulate output while observing device limits and safety policies.",
      "Το HEM ρυθμίζει την ισχύ με βάση τη μετρημένη ζήτηση και τους συντελεστές PID, τηρώντας τα όρια της συσκευής και τις προστασίες.",
      "HEM regelt anhand des gemessenen Bedarfs und der eingestellten PID-Werte unter Beachtung der Gerätegrenzen und Schutzregeln."
    ]
  },
  "equipment_presence_requirement": {
    "always": [
      "No extra room-occupancy restriction: the device can meet demand whether this room is occupied or empty. It does not mean continuously ON.",
      "Χωρίς πρόσθετο περιορισμό παρουσίας: η συσκευή μπορεί να καλύπτει ζήτηση είτε το δωμάτιο έχει κόσμο είτε όχι. Δεν σημαίνει συνεχή λειτουργία.",
      "Keine zusätzliche Raumanwesenheitsbedingung: Das Gerät kann Bedarf bei belegtem oder leerem Raum decken. Es läuft deshalb nicht dauerhaft."
    ],
    "occupied": [
      "Allow Automatic/PID operation only when presence in this exact room is verified. Unknown presence does not grant permission.",
      "Επιτρέπει Αυτόματο/PID μόνο όταν έχει επιβεβαιωθεί παρουσία στο συγκεκριμένο δωμάτιο. Άγνωστη παρουσία δεν δίνει άδεια.",
      "Erlaubt Automatik/PID nur bei bestätigter Anwesenheit in genau diesem Raum. Unbekannte Anwesenheit genügt nicht."
    ],
    "absent": [
      "Allow Automatic/PID operation only when this room is verified empty, even if people are elsewhere at home.",
      "Επιτρέπει Αυτόματο/PID μόνο όταν το συγκεκριμένο δωμάτιο είναι επιβεβαιωμένα άδειο, ακόμη κι αν υπάρχουν άτομα αλλού στο σπίτι.",
      "Erlaubt Automatik/PID nur bei nachweislich leerem Raum, auch wenn Personen in anderen Räumen zu Hause sind."
    ]
  },
  "equipment_sleep_behavior": {
    "normal": [
      "Keep normal automatic HEM control during room sleep; automatic profile selection may still choose Sleep targets.",
      "Συνεχίζει τον κανονικό αυτόματο έλεγχο του HEM στον ύπνο. Η αυτόματη επιλογή προφίλ μπορεί και πάλι να χρησιμοποιήσει στόχους Ύπνου.",
      "Behält die normale HEM-Automatik während der Schlafbedingung bei. Die Profilwahl kann dennoch Schlaf-Sollwerte verwenden."
    ],
    "pause": [
      "Request this device OFF while the room is in Sleep, subject to its minimum operating times and protections.",
      "Ζητά να κλείσει αυτή η συσκευή όσο ισχύει η συνθήκη Ύπνου του δωματίου, τηρώντας τους ελάχιστους χρόνους λειτουργίας και τις προστασίες.",
      "Fordert AUS für dieses Gerät während der Schlafbedingung des Raums an, unter Beachtung der Mindestlaufzeiten und Schutzregeln."
    ],
    "sleep_targets": [
      "Use the room's configured Sleep targets when Sleep is active, rather than forcing the device OFF.",
      "Όταν ισχύει η συνθήκη Ύπνου, χρησιμοποιεί τους στόχους του προφίλ Ύπνου αντί να κλείνει υποχρεωτικά τη συσκευή.",
      "Verwendet während der Schlafbedingung die festgelegten Schlaf-Sollwerte, statt das Gerät zwingend auszuschalten."
    ]
  },
  "equipment_fan_purpose": {
    "auto": [
      "Try a configured fan role or infer one only from sufficiently distinctive room sources. An ambiguous role does not authorize automatic control.",
      "Χρησιμοποιεί τον αποθηκευμένο ρόλο ή προσπαθεί να τον αναγνωρίσει από ξεκάθαρες πηγές του χώρου. Αν ο ρόλος είναι ασαφής, δεν επιτρέπεται αυθαίρετος αυτόματος έλεγχος.",
      "Nutzt die gespeicherte Lüfterrolle oder leitet sie nur aus eindeutigen Raumsensoren ab. Bei unklarer Rolle erfolgt keine eigenmächtige Automatik."
    ],
    "extraction": [
      "Treat the fan as an exhaust/ventilation device driven by verified CO₂ and outdoor-air conditions; it does not remove fine particles through filtration.",
      "Αντιμετωπίζει τον ανεμιστήρα ως εξαερισμό/απαγωγή με βάση επαληθευμένο CO₂ και κατάλληλο εξωτερικό αέρα· δεν τον θεωρεί φίλτρο μικροσωματιδίων.",
      "Behandelt den Lüfter als Abluftgerät anhand geprüften CO₂-Bedarfs und geeigneter Außenluft; keine Partikelfilterung wird angenommen."
    ],
    "filtration": [
      "Treat the fan as a particle-filtering purifier driven by valid PM2.5 demand. This does not mean fresh-air supply or CO₂ removal.",
      "Αντιμετωπίζει τον ανεμιστήρα ως καθαριστή σωματιδίων βάσει έγκυρων μετρήσεων PM2.5. Δεν σημαίνει παροχή φρέσκου αέρα ή αφαίρεση CO₂.",
      "Behandelt den Lüfter als Partikelfilter auf Basis gültiger PM2.5-Messwerte, nicht als Frischluftzufuhr oder CO₂-Entfernung."
    ]
  },
  "equipment_pid_calibration_method": {
    "manual": [
      "Enter and maintain Kp, Ki and Kd yourself; HEM does not automatically replace these values.",
      "Ορίζεις εσύ τα Kp, Ki και Kd. Το HEM δεν τα αντικαθιστά αυτόματα.",
      "Kp, Ki und Kd selbst eintragen und pflegen; HEM ersetzt sie nicht automatisch."
    ],
    "imc_lambda": [
      "Calculate suggested PID gains from an explicitly measured room/device model using IMC/Lambda; apply them only through the separate approval action.",
      "Υπολογίζει προτεινόμενα κέρδη PID από πραγματικά μετρημένο μοντέλο χώρου/συσκευής με IMC/Lambda. Εφαρμόζονται μόνο με ξεχωριστή εντολή έγκρισης.",
      "Berechnet PID-Vorschläge aus einem gemessenen Raum-/Gerätemodell nach IMC/Lambda; Übernahme nur per ausdrücklicher Freigabe."
    ],
    "cohen_coon": [
      "Calculate suggested gains from a measured response using Cohen–Coon; nothing changes until the calculated values are explicitly applied.",
      "Υπολογίζει προτεινόμενα κέρδη από μετρημένη απόκριση με Cohen–Coon. Τίποτα δεν αλλάζει μέχρι να εφαρμοστούν ρητά οι τιμές.",
      "Berechnet Vorschläge aus einer gemessenen Reaktion nach Cohen–Coon; ohne ausdrückliche Anwendung ändert sich nichts."
    ],
    "adaptive_suggest": [
      "Observe eligible normal operating cycles, then propose bounded tuning changes for you to approve or reject.",
      "Παρακολουθεί κατάλληλους κύκλους κανονικής λειτουργίας και προτείνει περιορισμένες αλλαγές για έγκριση ή απόρριψη.",
      "Beobachtet geeignete normale Betriebszyklen und schlägt begrenzte Änderungen zur Freigabe oder Ablehnung vor."
    ],
    "adaptive_auto": [
      "After enough high-quality cycles, allow bounded automatic PID tuning with the existing safety checks. This mode changes gains, so choose it deliberately.",
      "Μετά από αρκετούς αξιόπιστους κύκλους, επιτρέπει περιορισμένη αυτόματη προσαρμογή PID με τους υπάρχοντες ελέγχους ασφαλείας. Αλλάζει συντελεστές, οπότε επίλεξέ το συνειδητά.",
      "Erlaubt nach genügend hochwertigen Zyklen begrenzte automatische PID-Anpassung mit Schutzprüfungen. Dabei ändern sich Reglerwerte; bewusst wählen."
    ]
  },
  "equipment_pid_fan_capacity_mode": {
    "legacy": [
      "Use the original fan allocation; do not apply a measured fan-capacity curve.",
      "Χρησιμοποιεί την αρχική κατανομή ισχύος ανεμιστήρα χωρίς μετρημένη καμπύλη απόδοσης.",
      "Verwendet die bisherige Lüfterzuordnung ohne gemessene Kapazitätskurve."
    ],
    "measured": [
      "Use the explicitly saved measured output at each fan speed to adjust the controlled duty. Requires valid capacity data for the chosen direction.",
      "Χρησιμοποιεί τις αποθηκευμένες μετρημένες αποδόσεις ανά ταχύτητα για να προσαρμόζει τον χρόνο λειτουργίας. Απαιτούνται έγκυρα δεδομένα για τη συγκεκριμένη λειτουργία.",
      "Berücksichtigt die gespeicherte gemessene Leistung je Lüfterstufe zur Anpassung der Laufzeit. Erfordert gültige Daten für die gewählte Betriebsrichtung."
    ]
  },
  "equipment_pid_fan_capacity_for_mode": {
    "choose": [
      "No operating direction selected for these calibration inputs. Choose one before entering and saving capacity measurements.",
      "Δεν έχει επιλεγεί λειτουργία για τις μετρήσεις βαθμονόμησης. Επίλεξε πρώτα λειτουργία πριν εισαγάγεις και αποθηκεύσεις αποδόσεις.",
      "Keine Betriebsrichtung für diese Messwerte gewählt. Vor Eingabe und Speichern der Kapazität zuerst eine Richtung auswählen."
    ],
    "heat": [
      "The entered fan measurements belong to heating only, not cooling or drying.",
      "Οι μετρήσεις απόδοσης ανεμιστήρα αφορούν μόνο τη θέρμανση, όχι την ψύξη ή την αφύγρανση.",
      "Die eingetragenen Lüftermesswerte gelten nur für Heizen, nicht Kühlen oder Trocknen."
    ],
    "cool": [
      "The entered fan measurements belong to cooling only.",
      "Οι μετρήσεις απόδοσης ανεμιστήρα αφορούν μόνο την ψύξη.",
      "Die eingetragenen Lüftermesswerte gelten nur für Kühlen."
    ],
    "dry": [
      "The entered fan measurements belong to dehumidification only.",
      "Οι μετρήσεις απόδοσης ανεμιστήρα αφορούν μόνο την αφύγρανση.",
      "Die eingetragenen Lüftermesswerte gelten nur für Entfeuchten."
    ],
    "fan_only": [
      "The entered fan measurements belong to fan-only operation, where supported.",
      "Οι μετρήσεις απόδοσης αφορούν τη λειτουργία μόνο ανεμιστήρα, όπου υποστηρίζεται.",
      "Die eingetragenen Messwerte gelten nur für reinen Lüfterbetrieb, soweit unterstützt."
    ]
  }
}

def option_help_locales(key: str) -> dict[str, dict[str, str]]:
    """Return safe, static explanations keyed by native select option values."""
    options = OPTION_TEXT.get(OPTION_ALIASES.get(key, key), {})
    return {
        locale: {option: text[index] for option, text in options.items()}
        for index, locale in enumerate(("en", "el", "de"))
    } if options else {}

OPTION_ALIASES = {
    "area_climate_policy_away_policy": "home_global_policy_home_policy",
}
