"""Plain-language, option-by-option HEM selector explanations.

Only existing, code-verified select option IDs appear here. No I/O, active
device reads, control changes or translated option-name guessing at runtime.
Static catalogs cover all supported languages. Entity metadata keeps English
and the configured presentation languages for the card's local translation lookup.
"""
from __future__ import annotations

if __package__:
    from .backend_text import translated_text, presentation_languages, SUPPORTED_LANGUAGE_TAGS
else:
    from pathlib import Path
    from runpy import run_path
    _text_helpers = run_path(str(Path(__file__).with_name("backend_text.py")))
    translated_text = _text_helpers["translated_text"]
    presentation_languages = _text_helpers["presentation_languages"]
    SUPPORTED_LANGUAGE_TAGS = _text_helpers["SUPPORTED_LANGUAGE_TAGS"]


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
      "Assess the same measurements used by PID during normal operation, including short cycles and continuous output. Keep gains when control is good; propose a small simulated improvement only when the observations justify it. You approve or discard the proposal.",
      "Αξιολογεί τις ίδιες μετρήσεις που χρησιμοποιεί το PID στη φυσιολογική λειτουργία, σε σύντομους κύκλους ή συνεχή έξοδο. Διατηρεί τις τιμές όταν η ρύθμιση είναι καλή και προτείνει μικρή, ελεγμένη σε προσομοίωση βελτίωση μόνο με επαρκή στοιχεία. Εγκρίνεις ή απορρίπτεις την πρόταση.",
      "Bewertet die normalen PID-Messungen auch bei kurzen Zyklen und kontinuierlicher Ausgabe. Gute Reglerwerte bleiben erhalten. Nur ausreichende Beobachtungen führen zu einem kleinen, simulierten Verbesserungsvorschlag, den Sie annehmen oder verwerfen."
    ],
    "adaptive_auto": [
      "Allow validated adjustments of at most 10% per gain change when normal observations show a useful improvement. Check the result before another adjustment and restore previous gains if comparable observations confirm worse control. No fixed daily wait or forced test cycle; existing device protections still apply.",
      "Επιτρέπει ελεγμένες προσαρμογές έως 10% ανά συντελεστή όταν οι φυσιολογικές μετρήσεις τεκμηριώνουν χρήσιμη βελτίωση. Ελέγχει το αποτέλεσμα πριν από νέα αλλαγή και επαναφέρει τις προηγούμενες τιμές αν συγκρίσιμες μετρήσεις επιβεβαιώσουν χειρότερη ρύθμιση. Χωρίς σταθερή ημερήσια αναμονή ή επιβεβλημένο δοκιμαστικό κύκλο. Οι προστασίες της συσκευής ισχύουν.",
      "Erlaubt geprüfte Änderungen von höchstens 10 % je Reglerwert, wenn normale Beobachtungen eine sinnvolle Verbesserung belegen. Vor der nächsten Änderung wird das Ergebnis geprüft; bestätigte Verschlechterung unter vergleichbaren Bedingungen führt zur Wiederherstellung. Keine feste Tageswartezeit und kein erzwungener Testzyklus; Geräteschutz bleibt aktiv."
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

# Source and room selectors use the same IDs as the corresponding entity values.
OPTION_TEXT.update({
  "area_manual_profile": {
    "auto": [
      "Return to HEM's normal profile selection based on home/room presence, sleep and the configured priorities.",
      "Επιστρέφει στην αυτόματη επιλογή προφίλ από το HEM, με βάση παρουσία, ύπνο και τις προτεραιότητες που έχουν ρυθμιστεί.",
      "Zur normalen HEM-Profilwahl anhand von Anwesenheit, Schlaf und eingestellten Prioritäten zurückkehren."
    ],
    "home": [
      "Use this room's Home targets, rather than following the automatically selected profile.",
      "Χρησιμοποιεί τους στόχους «Σπίτι» του δωματίου αντί για το προφίλ που θα επέλεγε αυτόματα το HEM.",
      "Die Zuhause-Sollwerte dieses Raums statt des automatisch gewählten Profils verwenden."
    ],
    "comfort": [
      "Use this room's configured Comfort targets.",
      "Χρησιμοποιεί τους στόχους «Άνεση» που έχεις ορίσει για το δωμάτιο.",
      "Die festgelegten Komfort-Sollwerte dieses Raums verwenden."
    ],
    "away": [
      "Use the room's Away targets, independently of the currently detected home-presence profile.",
      "Χρησιμοποιεί τους στόχους «Απουσία» του δωματίου, ανεξάρτητα από το αυτόματα αναγνωρισμένο προφίλ παρουσίας.",
      "Die Abwesenheits-Sollwerte des Raums verwenden, unabhängig vom automatisch ermittelten Anwesenheitsprofil."
    ],
    "sleep": [
      "Use the room's configured Sleep targets.",
      "Χρησιμοποιεί τους στόχους «Ύπνος» του δωματίου.",
      "Die festgelegten Schlaf-Sollwerte des Raums verwenden."
    ],
    "eco": [
      "Use the room's configured Eco targets for lower consumption when allowed by safety rules.",
      "Χρησιμοποιεί τους στόχους «Eco» του δωματίου για οικονομικότερη λειτουργία, όπου το επιτρέπουν οι προστασίες.",
      "Die Eco-Sollwerte des Raums für sparsameren Betrieb verwenden, soweit die Schutzregeln dies erlauben."
    ]
  },
  "area_pid_gain_source": {
    "defaults": [
      "Use HEM's predefined PID tuning values for this room supervisor; manually entered gains are not selected.",
      "Χρησιμοποιεί τους προεπιλεγμένους συντελεστές PID για τον ελεγκτή του χώρου· δεν επιλέγει τις χειροκίνητες τιμές.",
      "Verwendet die HEM-Standardwerte für den Raum-PID; manuell eingegebene Reglerwerte werden nicht ausgewählt."
    ],
    "manual": [
      "Use the Kp, Ki and Kd values manually entered for this room, subject to the existing PID limits.",
      "Χρησιμοποιεί τα Kp, Ki και Kd που έχεις συμπληρώσει για αυτόν τον χώρο, με τα ίδια όρια προστασίας PID.",
      "Verwendet die für diesen Raum eingegebenen Kp-, Ki- und Kd-Werte unter den bisherigen PID-Grenzen."
    ]
  },
  "home_global_policy_home_policy": {
    "any_home": [
      "If any selected person/tracker is verified at home, the household is Home. Away needs verified absence from all relevant sources.",
      "Αν έστω ένα επιλεγμένο άτομο ή tracker επιβεβαιώνεται στο σπίτι, το σπίτι θεωρείται Home. Για Away πρέπει να έχει επιβεβαιωθεί η απουσία από όλες τις σχετικές πηγές.",
      "Ist mindestens eine ausgewählte Person oder ein Tracker nachweislich zu Hause, gilt Home. Away erfordert bestätigte Abwesenheit aller maßgeblichen Quellen."
    ],
    "all_home": [
      "Legacy compatibility choice. It currently follows the same conservative Home/Away rule as «Any home»; it does not require everybody to be home.",
      "Επιλογή συμβατότητας παλαιών ρυθμίσεων. Σήμερα ακολουθεί τον ίδιο ασφαλή κανόνα Home/Away με το «Έστω ένας στο σπίτι»· ΔΕΝ απαιτεί να είναι όλοι μέσα.",
      "Kompatibilitätsoption für ältere Einstellungen. Derzeit gilt dieselbe vorsichtige Home/Away-Regel wie bei »Mindestens eine Person da«; es müssen NICHT alle zu Hause sein."
    ]
  },
  "area_climate_policy_unknown_occupancy": {
    "occupied": [
      "Legacy fallback: when local room occupancy is unknown, treat the room conservatively as occupied for the old room-level profile policy. This does not prove anyone is present.",
      "Παλιά εφεδρική συμπεριφορά: όταν η παρουσία χώρου είναι άγνωστη, ο παλιός κανόνας προφίλ τον αντιμετωπίζει συντηρητικά ως κατειλημμένο. Δεν αποδεικνύει ότι βρίσκεται κάποιος εκεί.",
      "Älterer Ersatzmodus: Bei unbekannter Raumbelegung behandelt die frühere Raumprofilregel den Raum vorsichtshalber als belegt. Dies beweist keine Anwesenheit."
    ],
    "hold": [
      "Legacy fallback: when local occupancy is unknown, suspend that old room-profile decision instead of assuming someone is inside.",
      "Παλιά εφεδρική συμπεριφορά: με άγνωστη παρουσία, αναστέλλει την παλιά απόφαση προφίλ χώρου αντί να υποθέτει ότι υπάρχει άτομο.",
      "Älterer Ersatzmodus: Bei unbekannter Raumbelegung wird die frühere Raumprofilentscheidung ausgesetzt, statt Anwesenheit anzunehmen."
    ]
  },
  "area_climate_policy_target_source": {
    "temperature": [
      "Use the configured fixed profile temperature targets without extra humidity/comfort adaptation.",
      "Χρησιμοποιεί τις σταθερές θερμοκρασίες των προφίλ όπως έχουν οριστεί, χωρίς πρόσθετη προσαρμογή άνεσης βάσει υγρασίας.",
      "Verwendet die festgelegten Temperatur-Sollwerte der Profile ohne zusätzliche Feuchte-/Komfortanpassung."
    ],
    "auto_comfort": [
      "Adjust the comfort temperature band within configured limits using valid temperature and humidity evidence.",
      "Προσαρμόζει τη ζώνη θερμικής άνεσης μέσα στα καθορισμένα όρια, με έγκυρες μετρήσεις θερμοκρασίας και υγρασίας.",
      "Passt den Temperatur-Komfortbereich innerhalb der eingestellten Grenzen anhand gültiger Temperatur- und Feuchtemesswerte an."
    ],
    "pmv": [
      "Use the advanced PMV comfort assessment only with all required valid inputs. Insufficient evidence cannot authorize a fabricated comfort target.",
      "Χρησιμοποιεί την προηγμένη εκτίμηση PMV μόνο όταν υπάρχουν όλα τα απαιτούμενα έγκυρα δεδομένα. Ελλιπείς μετρήσεις δεν επιτρέπουν αυθαίρετο στόχο άνεσης.",
      "Verwendet die erweiterte PMV-Komfortbewertung nur mit allen erforderlichen gültigen Daten. Fehlende Nachweise erlauben keine erfundenen Komfort-Sollwerte."
    ]
  },
  "home_aqi_scale": {
    "auto": [
      "Recognize the AQI scale only when the source provider identifies it reliably; otherwise no unsupported numerical comparison is made.",
      "Αναγνωρίζει την κλίμακα AQI μόνο όταν η πηγή προσφέρει αξιόπιστη αναγνώριση· διαφορετικά δεν γίνεται αυθαίρετη αριθμητική σύγκριση.",
      "Erkennt die AQI-Skala nur, wenn der Anbieter sie verlässlich ausweist; sonst erfolgt kein unbelegter Zahlenvergleich."
    ],
    "not_configured": [
      "Do not interpret this AQI source until its scale is identified. Other valid air-quality sources remain available.",
      "Δεν ερμηνεύει αυτή την πηγή AQI μέχρι να αναγνωριστεί η κλίμακά της. Οι άλλες έγκυρες πηγές ποιότητας αέρα συνεχίζουν να χρησιμοποιούνται.",
      "Interpretiert diese AQI-Quelle nicht, bis ihre Skala feststeht. Andere gültige Luftqualitätsquellen bleiben nutzbar."
    ],
    "us_epa": [
      "Interpret this source as US EPA AQI only when you know the provider actually uses that scale.",
      "Ερμηνεύει την πηγή ως αμερικανικό δείκτη US EPA AQI μόνο αν ξέρεις ότι ο πάροχος χρησιμοποιεί αυτή την κλίμακα.",
      "Interpretiert die Quelle als US-EPA-AQI, nur wenn der Anbieter tatsächlich diese Skala verwendet."
    ],
    "eea_category": [
      "Interpret this source using the European EEA category scale, only if the provider uses it.",
      "Ερμηνεύει την πηγή με την ευρωπαϊκή κατηγορική κλίμακα EEA, μόνο αν ο πάροχος την χρησιμοποιεί.",
      "Interpretiert diese Quelle nach der europäischen EEA-Kategorieskala, sofern der Anbieter sie verwendet."
    ],
    "custom": [
      "Compare this source only against the custom source-specific AQI limit that you configure separately. Do not reuse a threshold from another scale.",
      "Συγκρίνει την πηγή μόνο με το ειδικό όριο AQI που ορίζεις ξεχωριστά γι’ αυτή. Μην χρησιμοποιείς όριο άλλης κλίμακας.",
      "Vergleicht die Quelle nur mit ihrem separat eingestellten individuellen AQI-Grenzwert. Keine Grenzen anderer Skalen übernehmen."
    ]
  },
  "global_threshold_mode_max_age_mode": {
    "auto": [
      "Apply HEM's type-based freshness limits to numeric environmental/weather readings. Change-driven window/door contacts are not expired merely because they stay unchanged.",
      "Εφαρμόζει τα προεπιλεγμένα χρονικά όρια στις αριθμητικές μετρήσεις περιβάλλοντος/καιρού. Οι επαφές θυρών/παραθύρων δεν λήγουν επειδή παραμένουν αμετάβλητες.",
      "Verwendet typabhängige Aktualitätsgrenzen für Messwerte und Wetter. Tür-/Fensterkontakte verfallen nicht, nur weil sie lange unverändert bleiben."
    ],
    "custom": [
      "Use your configured maximum reading age (minutes) for sampled environmental sources; unavailable/restored measurements remain invalid.",
      "Χρησιμοποιεί το μέγιστο χρονικό όριο (σε λεπτά) που έχεις ορίσει για δειγματοληπτικές περιβαλλοντικές πηγές. Μη διαθέσιμες/επαναφερμένες μετρήσεις παραμένουν άκυρες.",
      "Verwendet das festgelegte Höchstalter (Minuten) für abgetastete Umweltdaten. Nicht verfügbare/wiederhergestellte Messwerte bleiben ungültig."
    ]
  },
  "home_global_policy_source_freshness_mode": {
    "auto": [
      "Use the conservative automatic age policy for sampled home-presence counters and tracker reports. Valid unchanged Home evidence is handled separately.",
      "Χρησιμοποιεί τα συντηρητικά αυτόματα όρια παλαιότητας για μετρητές ατόμων και αναφορές παρουσίας. Η έγκυρη αμετάβλητη κατάσταση Home αντιμετωπίζεται ξεχωριστά.",
      "Verwendet die vorsichtigen automatischen Aktualitätsgrenzen für Anwesenheitszähler und Tracker-Meldungen. Gültige unveränderte Home-Nachweise werden getrennt behandelt."
    ],
    "custom": [
      "Use the configured maximum age for sampled home-presence reports, never treating missing or stale reports as proof that everyone left.",
      "Χρησιμοποιεί το δικό σου χρονικό όριο στις δειγματοληπτικές αναφορές παρουσίας· άγνωστες ή παλιές αναφορές δεν αποδεικνύουν ότι έφυγαν όλοι.",
      "Verwendet die eingestellte Gültigkeitsdauer für gemeldete Anwesenheitswerte; fehlende oder alte Meldungen beweisen niemals, dass alle abwesend sind."
    ]
  },
  "area_climate_policy_occupancy_freshness_mode": {
    "auto": [
      "Use automatic freshness limits for numeric room occupancy counts. Valid binary room-presence states remain change-driven.",
      "Χρησιμοποιεί αυτόματα όρια παλαιότητας για αριθμητικούς μετρητές παρουσίας. Οι έγκυρες δυαδικές καταστάσεις παρουσίας βασίζονται στις αλλαγές τους.",
      "Verwendet automatische Grenzen für numerische Raumbelegungszähler. Gültige binäre Raumpräsenzzustände bleiben ereignisgesteuert."
    ],
    "custom": [
      "Use your configured maximum reading age for numeric room occupancy counts. Unknown values cannot prove the room is empty.",
      "Χρησιμοποιεί το χρονικό όριο που όρισες για αριθμητικούς μετρητές παρουσίας. Οι άγνωστες ενδείξεις δεν αποδεικνύουν ότι ο χώρος είναι άδειος.",
      "Verwendet das eingestellte Höchstalter für numerische Raumbelegungszähler. Unbekannte Werte beweisen nicht, dass der Raum leer ist."
    ]
  }
})

OPTION_TEXT["door_kind"] = {
    "interior": [
        "A normal interior doorway connecting rooms. Only this class can be used for optional cross-room coordination when explicitly linked.",
        "Κανονική εσωτερική πόρτα μεταξύ δωματίων. Μόνο αυτός ο τύπος μπορεί να χρησιμοποιηθεί για προαιρετικό συντονισμό συσκευών ανάμεσα σε συνδεδεμένους χώρους.",
        "Normale Innentür zwischen Räumen. Nur diese Art darf für die optionale Koordinierung zwischen ausdrücklich verbundenen Räumen genutzt werden.",
    ],
    "fire": [
        "Fire or safety door. HEM never recommends holding it open or uses it for cross-room airflow/start coordination.",
        "Πυράντοχη πόρτα ή πόρτα ασφαλείας. Το HEM δεν προτείνει να μείνει ανοιχτή ούτε τη χρησιμοποιεί για συντονισμό μεταξύ χώρων.",
        "Brand- oder Sicherheitstür. HEM empfiehlt nicht, sie offen zu halten, und verwendet sie nicht zur Raum-übergreifenden Koordinierung.",
    ],
    "exterior": [
        "Door to outdoors. It is not a connection between two HEM rooms and is excluded from cross-room coordination.",
        "Εξωτερική πόρτα. Δεν συνδέει δύο δωμάτια του HEM και δεν χρησιμοποιείται για συντονισμό μεταξύ χώρων.",
        "Außentür. Sie verbindet nicht zwei HEM-Räume und bleibt von der Raum-übergreifenden Koordinierung ausgeschlossen.",
    ],
}
OPTION_TEXT["door_coordination"] = {
    option: OPTION_TEXT["equipment_door_start_coordination"][option]
    for option in ("observe", "conflicts", "shared")
}

def option_help_locales(key: str, language: str | None = None) -> dict[str, dict[str, str]]:
    """Return safe, static explanations keyed by native select option values."""
    options = OPTION_TEXT.get(OPTION_ALIASES.get(key, key), {})
    if not options:
        return {}
    locales = presentation_languages(language) if language is not None else SUPPORTED_LANGUAGE_TAGS
    result = {}
    for locale in locales:
        index = {"en": 0, "el": 1, "de": 2}.get(locale)
        result[locale] = {
            option: values[index] if index is not None else translated_text(values[0], locale)
            for option, values in options.items()
        }
    return result

OPTION_ALIASES = {
    "area_climate_policy_away_policy": "home_global_policy_home_policy",
}
