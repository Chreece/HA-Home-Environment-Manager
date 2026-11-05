"""Purpose-specific controller help, resolved in memory for entity details.

These descriptions follow the actual settings in equipment_model and their
runtime consumers. They do not change control, targets, or entity identity.
"""
from __future__ import annotations


# English, Greek and German are kept together so a setting cannot accidentally
# reuse the description of a neighbouring field. Other UI locales use English
# for these explanations while keeping their existing translated entity names.
HELP = {
    "control_mode": (
        "Choose who controls this device: its existing integration, HEM automatic rules, manual requests, Off, or PID demand control. Available choices depend on the device's supported functions.",
        "Επίλεξε ποιος ελέγχει τη συσκευή: η υπάρχουσα ενσωμάτωση, οι αυτόματοι κανόνες του HEM, οι χειροκίνητες εντολές, η απενεργοποίηση ή ο έλεγχος ζήτησης PID. Οι διαθέσιμες επιλογές εξαρτώνται από τις δυνατότητες της συσκευής.",
        "Legt fest, wer das Gerät steuert: seine bisherige Integration, HEM-Automatik, manuelle Vorgaben, Aus oder PID-Regelung. Die Auswahl richtet sich nach den unterstützten Gerätefunktionen.",
    ),
    "power_switch_entity": (
        "Select the switch that supplies power to this particular device. HEM powers it before starting the device and can switch it off after the device is confirmed idle and the supply cooldown has elapsed.",
        "Επίλεξε τον διακόπτη που τροφοδοτεί αυτή τη συσκευή. Το HEM δίνει πρώτα ρεύμα και μπορεί να το διακόψει όταν επιβεβαιωθεί ότι η συσκευή είναι αδρανής και ολοκληρωθεί η καθυστέρηση διακοπής τροφοδοσίας.",
        "Wählt den Versorgungsschalter dieses Geräts. HEM schaltet zuerst die Versorgung ein und kann sie nach bestätigtem Leerlauf und Ablauf der Abschaltverzögerung wieder ausschalten.",
    ),
    "presence_requirement": (
        "Restrict automatic operation to an occupied room, an empty room, or allow either. HEM uses the configured room presence evidence and gives confirmed whole-home absence priority over room activity.",
        "Περιορίζει την αυτόματη λειτουργία σε κατειλημμένο ή άδειο δωμάτιο, ή επιτρέπει και τα δύο. Το HEM χρησιμοποιεί τις επιλεγμένες πηγές παρουσίας και δίνει προτεραιότητα στην επιβεβαιωμένη απουσία από ολόκληρο το σπίτι.",
        "Erlaubt den Automatikbetrieb nur bei belegtem Raum, nur bei leerem Raum oder unabhängig davon. Bestätigte Abwesenheit im gesamten Zuhause hat Vorrang vor Raumsignalen.",
    ),
    "sleep_behavior": (
        "Normal continues HEM control; Pause requests this device off while the room is sleeping, respecting minimum runtime and native protections; Sleep targets requests the Sleep target set. Automatic profile selection can also select Sleep under Normal. Away and explicit presets retain their priority.",
        "Η κανονική λειτουργία συνεχίζει τον έλεγχο HEM. Η Παύση ζητά κλείσιμο κατά τον ύπνο, με τήρηση ελάχιστου χρόνου και προστασιών συσκευής. Οι Στόχοι ύπνου ζητούν το αντίστοιχο προφίλ. Η αυτόματη επιλογή μπορεί να επιλέξει Ύπνο και στην κανονική λειτουργία· το Away και τα ρητά προφίλ διατηρούν την προτεραιότητά τους.",
        "Normal setzt die HEM-Steuerung fort; Pause fordert bei Schlafstatus Aus an und beachtet Mindestlaufzeit und Geräteschutz; Schlaf-Sollwerte fordert das Schlafprofil an. Auch bei Normal kann die automatische Profilwahl Schlaf wählen. Abwesenheit und ausdrücklich gewählte Profile behalten Vorrang.",
    ),
    "quiet_sleep": (
        "Use this device's configured quiet fan setting while its room is sleeping. This changes the fan setting; the active target profile and separate sleep/presence policies remain in effect.",
        "Χρησιμοποιεί την επιλεγμένη αθόρυβη ρύθμιση ανεμιστήρα όταν το δωμάτιο είναι σε ύπνο. Αλλάζει τη ρύθμιση ανεμιστήρα· το ενεργό προφίλ στόχων και οι ξεχωριστοί κανόνες ύπνου και παρουσίας εξακολουθούν να ισχύουν.",
        "Verwendet die konfigurierte leise Lüftereinstellung, solange der Raum schläft. Geändert wird die Lüftereinstellung; aktives Sollwertprofil und separate Schlaf-/Anwesenheitsregeln bleiben wirksam.",
    ),
    "quiet_occupied": (
        "Use this device's configured quiet fan setting while the room is occupied. Automatic demand remains subject to the device's normal operating rules and available quiet output.",
        "Χρησιμοποιεί την επιλεγμένη αθόρυβη ρύθμιση ανεμιστήρα όταν το δωμάτιο είναι κατειλημμένο. Η ζήτηση εξακολουθεί να ακολουθεί τους κανόνες λειτουργίας και τη διαθέσιμη απόδοση στην αθόρυβη ρύθμιση.",
        "Verwendet die konfigurierte leise Lüftereinstellung bei belegtem Raum. Die automatische Anforderung bleibt durch Betriebsregeln und verfügbare leise Leistung begrenzt.",
    ),
    "quiet_fan_mode": (
        "Choose the device's native fan mode to use when an enabled quiet condition applies, such as sleeping or an occupied room.",
        "Επίλεξε την πραγματική λειτουργία ανεμιστήρα της συσκευής για τις ενεργοποιημένες συνθήκες ησυχίας, όπως ύπνος ή παρουσία στο δωμάτιο.",
        "Wählt die native Lüfterstufe für aktivierte Ruhebedingungen, etwa Schlaf oder Raumbelegung.",
    ),
    "quiet_percentage": (
        "Fan-speed limit used when this device has an active quiet condition. The value is a percentage of the native controllable fan speed, not a noise level or heating/cooling capacity.",
        "Όριο ταχύτητας ανεμιστήρα όταν ισχύει συνθήκη ησυχίας για τη συσκευή. Είναι ποσοστό της πραγματικής ταχύτητας, όχι στάθμη θορύβου ή θερμική απόδοση.",
        "Begrenzt die Lüfterdrehzahl bei aktiver Ruhebedingung. Der Prozentwert beschreibt die native Drehzahl, nicht den Schallpegel oder die Heiz-/Kühlleistung.",
    ),
    "fan_min_percentage": (
        "Lowest nonzero fan speed HEM may request from this device while it is running. Zero demand can still turn the output off; native speed steps are respected.",
        "Η χαμηλότερη μη μηδενική ταχύτητα που μπορεί να ζητήσει το HEM όταν ο ανεμιστήρας λειτουργεί. Η μηδενική ζήτηση μπορεί να τον σταματήσει και τηρούνται τα πραγματικά βήματα ταχύτητας.",
        "Niedrigste Drehzahl oberhalb null, die HEM im Betrieb anfordern darf. Bei fehlender Anforderung bleibt Abschalten möglich; native Drehzahlstufen werden berücksichtigt.",
    ),
    "fan_max_percentage": (
        "Highest fan speed HEM may request from this device. Quiet conditions can impose a lower limit; the device's native speed steps are respected.",
        "Η υψηλότερη ταχύτητα ανεμιστήρα που επιτρέπεται να ζητήσει το HEM. Οι συνθήκες ησυχίας μπορούν να επιβάλουν χαμηλότερο όριο και τηρούνται τα πραγματικά βήματα ταχύτητας.",
        "Höchste von HEM erlaubte Lüfterdrehzahl. Ruhebedingungen können sie weiter begrenzen; native Drehzahlstufen werden berücksichtigt.",
    ),
    "fan_purpose": (
        "Extraction uses CO₂ demand to replace room air; filtration uses PM2.5 demand to remove particles. Auto uses a saved role or infers it from CO₂-only or PM2.5-only room sources. Choose the role explicitly when the sources cannot distinguish it.",
        "Η απαγωγή ακολουθεί το CO₂ για ανανέωση αέρα, ενώ η φίλτρανση ακολουθεί τα PM2.5 για απομάκρυνση σωματιδίων. Το Αυτόματα χρησιμοποιεί αποθηκευμένο ρόλο ή τον συμπεραίνει από αποκλειστικά CO₂ ή PM2.5 πηγές. Επίλεξε ρητά τον ρόλο όταν οι πηγές δεν τον προσδιορίζουν.",
        "Abluft erneuert Raumluft anhand des CO₂-Bedarfs; Filterung entfernt Partikel anhand von PM2.5. Automatisch verwendet eine gespeicherte Rolle oder leitet sie aus ausschließlich CO₂- bzw. PM2.5-Quellen ab. Bei uneindeutigen Quellen ist eine ausdrückliche Auswahl nötig.",
    ),
    "sensor_verified": (
        "Confirm that the selected PM2.5 measurement is suitable for automatic particle filtration. Verification on the room's PM2.5 source can also satisfy this requirement. This switch does not calibrate the sensor.",
        "Επιβεβαιώνει ότι η επιλεγμένη μέτρηση PM2.5 είναι κατάλληλη για αυτόματη φίλτρανση σωματιδίων. Η επιβεβαίωση της πηγής PM2.5 του δωματίου καλύπτει επίσης αυτή την απαίτηση. Ο διακόπτης δεν βαθμονομεί τον αισθητήρα.",
        "Bestätigt die Eignung der ausgewählten PM2.5-Messung für automatische Partikelfilterung. Auch die Bestätigung der PM2.5-Quelle des Raums erfüllt diese Voraussetzung. Der Schalter kalibriert den Sensor nicht.",
    ),
    "particle_cadr_m3h": (
        "Enter the purifier's rated clean-air delivery for particles at the relevant fan speed, in m³/h. HEM combines it with room volume for filtration estimates. Zero means unconfigured; CADR does not measure fresh-air ventilation or CO₂ removal.",
        "Δώσε την ονομαστική παροχή καθαρού αέρα για σωματίδια στη σχετική ταχύτητα, σε m³/h. Συνδυάζεται με τον όγκο δωματίου για εκτιμήσεις φίλτρανσης. Το μηδέν σημαίνει μη ρυθμισμένο· το CADR δεν μετρά αερισμό ή απομάκρυνση CO₂.",
        "Tragen Sie die angegebene Partikel-Reinluftleistung bei der betreffenden Lüfterstufe in m³/h ein. HEM nutzt sie mit dem Raumvolumen für Filterungsabschätzungen. Null bedeutet unkonfiguriert; CADR beschreibt weder Frischluft noch CO₂-Abfuhr.",
    ),
    "pause_on_window_open": (
        "Pause this device's automatic output when a configured window in its own room is open or its state cannot be verified. Automatic evaluation resumes after that room's windows close and the existing recovery delay completes.",
        "Παύει την αυτόματη λειτουργία όταν επιλεγμένο παράθυρο του ίδιου δωματίου είναι ανοιχτό ή δεν επιβεβαιώνεται η κατάστασή του. Η αυτόματη αξιολόγηση συνεχίζεται όταν κλείσουν τα παράθυρα και ολοκληρωθεί η καθυστέρηση επαναφοράς.",
        "Pausiert die automatische Ausgabe, wenn ein konfiguriertes Fenster im eigenen Raum offen oder nicht verifizierbar ist. Nach dem Schließen und der bestehenden Wiederanlaufzeit wird automatisch neu bewertet.",
    ),
    "announce_device_errors": (
        "Announce new faults reported by this physical device's existing Home Assistant error entities or attributes. The announcement includes the reported fault details and uses HEM's configured announcement delivery.",
        "Ανακοινώνει νέα σφάλματα από τις υπάρχουσες οντότητες ή ιδιότητες σφαλμάτων της πραγματικής συσκευής. Περιλαμβάνει τις λεπτομέρειες του σφάλματος και χρησιμοποιεί τη ρυθμισμένη αποστολή ανακοινώσεων του HEM.",
        "Meldet neue Fehler aus den bestehenden Fehlerentitäten oder Attributen des physischen Geräts. Die Meldung enthält die Fehlerdetails und nutzt die konfigurierte HEM-Ausgabe.",
    ),
    "timed_setpoint_sequence": (
        "Wait 30 seconds after confirmed native ON before writing supported temperature or humidity targets. For heating/cooling shutdown, send the native minimum temperature in Heat or maximum in Cool, then wait 30 seconds before Off. Disabled removes this added timing and reverse shutdown target.",
        "Περιμένει 30 δευτερόλεπτα μετά την επιβεβαιωμένη ενεργοποίηση πριν γράψει στόχους θερμοκρασίας ή υγρασίας. Στο κλείσιμο θέρμανσης στέλνει την ελάχιστη θερμοκρασία της συσκευής, στην ψύξη τη μέγιστη, και μετά από 30 δευτερόλεπτα το Off. Κλειστή αφαιρεί τον πρόσθετο χρονισμό και τον αντίθετο στόχο κλεισίματος.",
        "Wartet nach bestätigtem nativem Ein 30 Sekunden vor Temperatur- oder Feuchtesollwerten. Vor dem Abschalten bei Heizen wird die native Mindesttemperatur, bei Kühlen die Höchsttemperatur gesendet; nach 30 Sekunden folgt Aus. Deaktiviert entfallen diese Zusatzzeiten und der entgegengesetzte Abschalt-Sollwert.",
    ),
    "kp": (
        "PID proportional response: determines how strongly output demand reacts to the current difference from the target. Higher values produce a stronger immediate response.",
        "Αναλογική απόκριση PID: καθορίζει πόσο έντονα αντιδρά η ζήτηση στην τρέχουσα απόκλιση από τον στόχο. Μεγαλύτερη τιμή δίνει εντονότερη άμεση απόκριση.",
        "Proportionalanteil des PID: bestimmt die unmittelbare Reaktion auf die aktuelle Sollwertabweichung. Höhere Werte bewirken eine stärkere Reaktion.",
    ),
    "ki": (
        "PID accumulated-error correction: adjusts demand when a difference from the target persists over time. Zero disables the integral contribution.",
        "Διόρθωση συσσωρευμένου σφάλματος PID: προσαρμόζει τη ζήτηση όταν η απόκλιση από τον στόχο επιμένει. Το μηδέν απενεργοποιεί την ολοκληρωτική συνιστώσα.",
        "Integralanteil des PID: korrigiert über die Zeit anhaltende Sollwertabweichungen. Null deaktiviert diesen Anteil.",
    ),
    "kd": (
        "PID trend response: adjusts demand using the rate at which the measurement changes, helping moderate rapid approaches to the target. Zero disables the derivative contribution.",
        "Απόκριση PID στην τάση: προσαρμόζει τη ζήτηση βάσει του ρυθμού μεταβολής της μέτρησης, περιορίζοντας την απότομη προσέγγιση του στόχου. Το μηδέν απενεργοποιεί τη διαφορική συνιστώσα.",
        "Differentialanteil des PID: berücksichtigt die Änderungsgeschwindigkeit der Messung, um schnelle Annäherungen an den Sollwert abzufangen. Null deaktiviert diesen Anteil.",
    ),
    "sample_seconds": (
        "Minimum interval between normal PID updates or repeated target adjustments for this controller. Urgent stop conditions and physical-device safeguards are checked separately.",
        "Ελάχιστο διάστημα μεταξύ κανονικών ενημερώσεων PID ή επαναλαμβανόμενων προσαρμογών στόχου. Οι άμεσες συνθήκες διακοπής και οι έλεγχοι της συσκευής εξετάζονται ξεχωριστά.",
        "Mindestabstand zwischen regulären PID-Berechnungen bzw. wiederholten Sollwertanpassungen. Sofortige Stoppbedingungen und Geräteprüfungen werden separat geprüft.",
    ),
    "cycle_seconds": (
        "Time window used to turn a PID demand percentage into on/off running time. A 50% demand aims for half of the window running, while minimum on/off times and low-demand cycle extension remain in effect.",
        "Χρονικό παράθυρο που μετατρέπει το ποσοστό ζήτησης PID σε χρόνο λειτουργίας on/off. Ζήτηση 50% αντιστοιχεί περίπου στο μισό παράθυρο λειτουργίας, με τήρηση ελάχιστων χρόνων και παράταση κύκλου σε χαμηλή ζήτηση.",
        "Zeitfenster zur Umsetzung des PID-Bedarfs in Ein-/Aus-Zeit. Bei 50% wird ungefähr die Hälfte des Fensters angefordert; Mindestzeiten und Zyklusverlängerung bei geringer Last bleiben wirksam.",
    ),
    "min_on_seconds": (
        "Minimum running time for a supervised on/off output to reduce rapid cycling. Sleep, window and target stop requests still respect the applicable minimum runtime and native protections. A separate supply switch also observes its minimum-on timing.",
        "Ελάχιστος χρόνος λειτουργίας επιτηρούμενης εξόδου on/off για περιορισμό συχνών εκκινήσεων. Αιτήματα διακοπής λόγω ύπνου, παραθύρου ή επίτευξης στόχου τηρούν τον ελάχιστο χρόνο και τις προστασίες συσκευής. Ο ξεχωριστός διακόπτης τροφοδοσίας τηρεί επίσης τον ελάχιστο χρόνο ενεργοποίησης.",
        "Mindestlaufzeit für überwachte Ein-/Aus-Ausgänge gegen häufige Starts. Stoppanforderungen durch Schlaf, Fenster oder erreichte Sollwerte beachten weiterhin Mindestlaufzeit und Geräteschutz. Ein separater Versorgungsschalter beachtet ebenfalls seine Mindest-Ein-Zeit.",
    ),
    "min_off_seconds": (
        "Minimum stopped time before HEM may restart a supervised output or its separate power supply. This prevents rapid restarts; restoring demand does not erase the remaining delay.",
        "Ελάχιστος χρόνος διακοπής πριν το HEM επανεκκινήσει την έξοδο ή την ξεχωριστή τροφοδοσία της. Αποτρέπει γρήγορες επανεκκινήσεις· νέα ζήτηση δεν μηδενίζει την υπολειπόμενη αναμονή.",
        "Mindeststillstandszeit vor einem Neustart des Ausgangs oder seiner separaten Versorgung. Neue Anforderung hebt die verbleibende Wiederanlaufverzögerung nicht auf.",
    ),
    "max_on_seconds": (
        "Maximum continuous running period for an output started under HEM's supervision. Reaching it requests a stop through the normal verified shutdown sequence; device feedback, minimum runtime and defrost protection can delay completion.",
        "Μέγιστη συνεχής διάρκεια εξόδου που ξεκίνησε υπό τον έλεγχο HEM. Στο όριο ζητείται διακοπή μέσω της κανονικής επιβεβαιωμένης διαδικασίας· η ανάδραση, ο ελάχιστος χρόνος και η απόψυξη μπορούν να καθυστερήσουν την ολοκλήρωση.",
        "Maximale durchgehende Laufzeit eines unter HEM gestarteten Ausgangs. Danach wird ein Stopp über die normale bestätigte Abschaltfolge angefordert; Rückmeldung, Mindestlaufzeit und Abtauschutz können den Abschluss verzögern.",
    ),
    "power_switch_cooldown_seconds": (
        "Continuous confirmed idle time required before HEM turns off this device's selected supply switch. Activity or uncertain device feedback prevents the supply from being switched off.",
        "Συνεχής επιβεβαιωμένος χρόνος αδράνειας πριν το HEM κλείσει τον επιλεγμένο διακόπτη τροφοδοσίας. Ενεργή λειτουργία ή αβέβαιη ανάδραση εμποδίζει τη διακοπή ρεύματος.",
        "Erforderliche durchgehend bestätigte Leerlaufzeit vor dem Ausschalten des Versorgungsschalters. Aktivität oder unklare Rückmeldung verhindert das Abschalten der Versorgung.",
    ),
    "pid_calibration_method": (
        "Choose how PID gains are obtained: manual values; a measured-response IMC/Lambda or Cohen–Coon calculation; adaptive suggestions requiring approval; or explicitly enabled bounded automatic adaptation during normal operation.",
        "Επίλεξε πώς προκύπτουν οι συντελεστές PID: χειροκίνητα, υπολογισμός IMC/Lambda ή Cohen–Coon από μετρημένη απόκριση, προσαρμοστικές προτάσεις με έγκριση ή ρητά επιλεγμένη περιορισμένη αυτόματη προσαρμογή κατά την κανονική λειτουργία.",
        "Wählt die Herkunft der PID-Werte: manuell, IMC/Lambda oder Cohen–Coon aus gemessener Reaktion, adaptive Vorschläge mit Freigabe oder ausdrücklich aktivierte begrenzte automatische Anpassung im Normalbetrieb.",
    ),
    "pid_process_gain": (
        "Measured total change in room temperature or humidity caused by a full output step. Used with the measured response time and delay to calculate this device's PID gains; zero means not measured.",
        "Μετρημένη συνολική μεταβολή θερμοκρασίας ή υγρασίας από πλήρες βήμα εξόδου. Μαζί με τον χρόνο απόκρισης και την καθυστέρηση χρησιμοποιείται για τους συντελεστές PID. Το μηδέν σημαίνει ότι δεν έχει μετρηθεί.",
        "Gemessene gesamte Temperatur- oder Feuchteänderung durch einen vollständigen Leistungssprung. Dient mit Zeitkonstante und Totzeit zur PID-Berechnung; null bedeutet noch nicht gemessen.",
    ),
    "pid_time_constant_minutes": (
        "Measured time for the room's response to reach about 63% of its eventual change after the initial delay. This describes the device/room response used for PID calibration.",
        "Μετρημένος χρόνος μέχρι η απόκριση του δωματίου να φτάσει περίπου το 63% της τελικής μεταβολής, μετά την αρχική καθυστέρηση. Περιγράφει την απόκριση για τη βαθμονόμηση PID.",
        "Gemessene Zeit bis ungefähr 63% der späteren Gesamtänderung nach der anfänglichen Verzögerung. Beschreibt die Geräte-/Raumreaktion für die PID-Berechnung.",
    ),
    "pid_dead_time_minutes": (
        "Measured delay between a change in device output and the first observable room temperature or humidity response. Used by the selected mathematical PID calibration method.",
        "Μετρημένη καθυστέρηση από την αλλαγή εξόδου μέχρι την πρώτη παρατηρήσιμη απόκριση θερμοκρασίας ή υγρασίας. Χρησιμοποιείται από την επιλεγμένη μαθηματική μέθοδο βαθμονόμησης PID.",
        "Gemessene Verzögerung zwischen einer Leistungsänderung und der ersten erkennbaren Temperatur- oder Feuchtereaktion. Wird von der gewählten PID-Berechnung verwendet.",
    ),
    "pid_lambda_minutes": (
        "Desired response time for IMC/Lambda tuning. A larger value requests a gentler, slower correction. This field is used only by IMC/Lambda, together with the measured response model.",
        "Επιθυμητός χρόνος απόκρισης για τη μέθοδο IMC/Lambda. Μεγαλύτερη τιμή ζητά πιο ήπια και αργή διόρθωση. Χρησιμοποιείται μόνο από αυτή τη μέθοδο μαζί με το μετρημένο μοντέλο απόκρισης.",
        "Gewünschte Reaktionszeit für IMC/Lambda. Größere Werte ergeben eine ruhigere, langsamere Korrektur. Wird nur bei IMC/Lambda zusammen mit dem gemessenen Modell verwendet.",
    ),
    "pid_apply_calibration": (
        "Calculate and save this device's Kp, Ki and Kd from the selected IMC/Lambda or Cohen–Coon method and the entered measured response. The device must be reconciled and physically off; this button does not perform a live measurement experiment.",
        "Υπολογίζει και αποθηκεύει Kp, Ki και Kd από τη μέθοδο IMC/Lambda ή Cohen–Coon και τη μετρημένη απόκριση που έδωσες. Η συσκευή πρέπει να είναι επιβεβαιωμένα κλειστή· το κουμπί δεν εκτελεί πείραμα μέτρησης.",
        "Berechnet und speichert Kp, Ki und Kd aus IMC/Lambda oder Cohen–Coon und der eingegebenen gemessenen Reaktion. Das Gerät muss abgeglichen und physisch ausgeschaltet sein; die Taste führt keinen Messversuch aus.",
    ),
    "pid_review_approve": (
        "Apply the pending adaptive PID proposal shown for this device. The proposal is checked again against the current controller context before its gains are saved.",
        "Εφαρμόζει την εκκρεμή προσαρμοστική πρόταση PID για αυτή τη συσκευή. Η πρόταση ελέγχεται ξανά με τις τρέχουσες συνθήκες ελέγχου πριν αποθηκευτούν οι συντελεστές.",
        "Übernimmt den angezeigten ausstehenden adaptiven PID-Vorschlag. Vor dem Speichern werden Vorschlag und aktueller Regelungskontext erneut geprüft.",
    ),
    "pid_review_discard": (
        "Discard the current adaptive PID proposal and keep the controller's existing gains. Later normal operation can produce a new proposal.",
        "Απορρίπτει την τρέχουσα πρόταση PID και κρατά τους υπάρχοντες συντελεστές. Η επόμενη κανονική λειτουργία μπορεί να δημιουργήσει νέα πρόταση.",
        "Verwirft den aktuellen PID-Vorschlag und behält die bisherigen Werte. Im weiteren Normalbetrieb kann ein neuer Vorschlag entstehen.",
    ),
    "pid_fan_capacity_mode": (
        "Choose the original fan allocation or use a saved measured output-versus-fan-speed model. The measured option adjusts on/off duty for actual relative capacity at each fan speed.",
        "Επίλεξε την αρχική κατανομή ανεμιστήρα ή αποθηκευμένο μοντέλο μετρημένης απόδοσης ανά ταχύτητα. Το μετρημένο μοντέλο προσαρμόζει τον χρόνο on/off στη σχετική απόδοση κάθε ταχύτητας.",
        "Wählt die bisherige Lüfterzuordnung oder ein gespeichertes Modell der gemessenen Leistung je Drehzahl. Das Messmodell passt die Ein-/Aus-Dauer an die relative Leistung an.",
    ),
    "pid_fan_capacity_for_mode": (
        "Select which operating direction the entered fan-capacity measurements describe: heating, cooling, drying or fan-only. Each direction needs its own matching model.",
        "Επίλεξε τη λειτουργία που αφορούν οι μετρήσεις απόδοσης ανεμιστήρα: θέρμανση, ψύξη, αφύγρανση ή μόνο ανεμιστήρας. Κάθε λειτουργία χρειάζεται το αντίστοιχο μοντέλο.",
        "Wählt die Betriebsrichtung der Lüfter-Leistungsmessungen: Heizen, Kühlen, Entfeuchten oder nur Lüfter. Jede Richtung benötigt ein passendes eigenes Modell.",
    ),
    "pid_apply_fan_capacity": (
        "Validate and save the entered relative fan-output measurements for the selected operating direction. The fastest stage is the 100% output reference. Applying requires the physical device to be off and does not measure capacity automatically.",
        "Ελέγχει και αποθηκεύει τις μετρημένες σχετικές αποδόσεις για την επιλεγμένη λειτουργία. Η ταχύτερη βαθμίδα είναι η αναφορά απόδοσης 100%. Η συσκευή πρέπει να είναι κλειστή· η απόδοση δεν μετριέται αυτόματα.",
        "Prüft und speichert die gemessenen relativen Leistungen für die gewählte Betriebsrichtung. Die höchste Stufe bildet die 100%-Referenz. Das Gerät muss ausgeschaltet sein; die Leistung wird nicht automatisch gemessen.",
    ),
    "resume": (
        "Return this controller to automatic operation and clear its manual pause. HEM continues pending device checks in the background and applies demand when the configured operating conditions permit it.",
        "Επαναφέρει τον ελεγκτή στην αυτόματη λειτουργία και αίρει τη χειροκίνητη παύση. Το HEM συνεχίζει τους εκκρεμείς ελέγχους στο παρασκήνιο και εφαρμόζει τη ζήτηση όταν το επιτρέπουν οι συνθήκες λειτουργίας.",
        "Setzt den Regler wieder auf Automatik und hebt die manuelle Pause auf. Ausstehende Geräteprüfungen laufen im Hintergrund weiter; Anforderungen werden bei passenden Betriebsbedingungen umgesetzt.",
    ),
    "climate": (
        "HEM's controller for this physical device. Room profiles supply its targets; the chosen control method, presence, sleep and window settings determine when it may act.",
        "Ο ελεγκτής HEM αυτής της πραγματικής συσκευής. Τα προφίλ δωματίου δίνουν τους στόχους και η μέθοδος ελέγχου, η παρουσία, ο ύπνος και τα παράθυρα καθορίζουν πότε λειτουργεί.",
        "HEM-Regler für dieses physische Gerät. Raumprofile liefern die Sollwerte; Regelungsart, Anwesenheit, Schlaf- und Fenstereinstellungen bestimmen den Betrieb.",
    ),
    "control_status": (
        "Current result of HEM's control evaluation for this device, including demand, pauses, pending feedback and recovery. Physical activity is reported separately by the device's own Home Assistant state.",
        "Τρέχον αποτέλεσμα ελέγχου HEM: ζήτηση, παύσεις, εκκρεμής ανάδραση και επαναφορά. Η πραγματική δραστηριότητα εμφανίζεται ξεχωριστά από την κατάσταση της ίδιας της συσκευής στο Home Assistant.",
        "Aktuelles Ergebnis der HEM-Regelung: Bedarf, Pausen, ausstehende Rückmeldung und Wiederherstellung. Die tatsächliche Aktivität stammt separat aus dem Home-Assistant-Zustand des Geräts.",
    ),
}

_CAPACITY_HELP = {
    "stage": (
        "Measured relative output at fan stage {index}, as a percentage of the fastest stage's output. Enter actual heating, cooling or drying output for the selected direction; fan-speed percentages alone are not capacity measurements.",
        "Μετρημένη σχετική απόδοση στη βαθμίδα ανεμιστήρα {index}, ως ποσοστό της ταχύτερης βαθμίδας. Δώσε πραγματική απόδοση θέρμανσης, ψύξης ή αφύγρανσης· το ποσοστό ταχύτητας δεν αποτελεί μέτρηση απόδοσης.",
        "Gemessene relative Leistung der Lüfterstufe {index}, bezogen auf die höchste Stufe. Benötigt wird die tatsächliche Heiz-, Kühl- oder Entfeuchtungsleistung; Drehzahlprozente allein sind keine Leistungsmessung.",
    ),
    "speed": (
        "Native fan-speed percentage for measurement point {index}. Enter its measured relative output in the matching output field. At least two complete points are required for a percentage-speed model.",
        "Πραγματικό ποσοστό ταχύτητας για το σημείο μέτρησης {index}. Συμπλήρωσε τη μετρημένη σχετική απόδοση στο αντίστοιχο πεδίο. Το μοντέλο ποσοστιαίας ταχύτητας απαιτεί τουλάχιστον δύο πλήρη σημεία.",
        "Native Lüfterdrehzahl in Prozent für Messpunkt {index}. Die gemessene relative Leistung gehört ins zugehörige Leistungsfeld. Für ein Prozentdrehzahl-Modell werden mindestens zwei vollständige Punkte benötigt.",
    ),
    "output": (
        "Measured relative output at the matching fan-speed point {index}, compared with output at full speed. This value lets PID compensate running time when a lower fan speed delivers less capacity.",
        "Μετρημένη σχετική απόδοση για το αντίστοιχο σημείο ταχύτητας {index}, σε σύγκριση με την πλήρη ταχύτητα. Επιτρέπει στο PID να προσαρμόζει τον χρόνο λειτουργίας όταν η χαμηλότερη ταχύτητα αποδίδει λιγότερο.",
        "Gemessene relative Leistung beim zugehörigen Drehzahlpunkt {index}, verglichen mit voller Drehzahl. Damit gleicht PID die Laufzeit an die geringere Leistung niedriger Drehzahlen an.",
    ),
}

for _kind, _count in (("stage", 4), ("speed", 3), ("output", 3)):
    for _index in range(1, _count + 1):
        HELP[f"pid_capacity_{_kind}_{_index}"] = tuple(
            text.format(index=_index) for text in _CAPACITY_HELP[_kind]
        )


def equipment_configuration_help(key: str, locale: str = "en") -> str:
    """Return one setting's purpose with a deterministic language fallback."""
    language = str(locale or "en").replace("_", "-").casefold().split("-")[0]
    index = {"el": 1, "de": 2}.get(language, 0)
    return HELP.get(key, HELP["climate"])[index]
