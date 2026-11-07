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
        "Applies to Automatic and PID; this chooses when the device may operate.\n"
        "No room-presence restriction: meet demand whether the room is occupied or empty; this does not mean continuously ON.\n"
        "Only while room is occupied: require confirmed presence in this room.\n"
        "Only while room is empty: require confirmed absence from this room, even if someone is elsewhere at home.\n"
        "Unknown room presence pauses the two restricted choices. Confirmed whole-home Away counts every room as empty.\n"
        "When the condition stops matching, HEM requests OFF for an output it controls after its minimum ON time, retaining command confirmation and native protections. Target demand, sleep and window rules still apply.",
        "Ισχύει για Αυτόματα και PID· ορίζει πότε επιτρέπεται να λειτουργεί η συσκευή.\n"
        "Χωρίς περιορισμό παρουσίας: καλύπτει τη ζήτηση είτε το δωμάτιο έχει κόσμο είτε είναι άδειο· δεν σημαίνει συνεχή λειτουργία.\n"
        "Μόνο με παρουσία στο δωμάτιο: απαιτεί επιβεβαιωμένη παρουσία σε αυτό το δωμάτιο.\n"
        "Μόνο σε άδειο δωμάτιο: απαιτεί επιβεβαιωμένη απουσία από αυτό το δωμάτιο, ακόμη κι αν υπάρχει κάποιος αλλού στο σπίτι.\n"
        "Η άγνωστη παρουσία παύει τις δύο επιλογές με περιορισμό. Η επιβεβαιωμένη Απουσία από το σπίτι θεωρεί όλα τα δωμάτια άδεια.\n"
        "Όταν η συνθήκη πάψει να ισχύει, το HEM ζητά κλείσιμο της εξόδου που ελέγχει μετά τον ελάχιστο χρόνο ON, τηρώντας την επιβεβαίωση εντολών και τις προστασίες της συσκευής. Η ζήτηση, οι κανόνες ύπνου και τα παράθυρα εξακολουθούν να ισχύουν.",
        "Gilt für Automatik und PID und legt fest, wann das Gerät arbeiten darf.\n"
        "Unabhängig von der Raumbelegung: deckt den Bedarf bei belegtem oder leerem Raum; bedeutet keinen Dauerbetrieb.\n"
        "Nur bei belegtem Raum: erfordert bestätigte Anwesenheit in diesem Raum.\n"
        "Nur bei leerem Raum: erfordert bestätigte Abwesenheit in diesem Raum, auch wenn jemand anderswo zu Hause ist.\n"
        "Unbekannte Raumbelegung pausiert die beiden eingeschränkten Optionen. Bei bestätigter Abwesenheit im gesamten Zuhause gelten alle Räume als leer.\n"
        "Wenn die Bedingung nicht mehr zutrifft, fordert HEM für einen von ihm gesteuerten Ausgang nach dessen Mindestlaufzeit Aus an; Befehlsbestätigung und Geräteschutz bleiben wirksam. Bedarf, Schlaf- und Fensterregeln gelten weiterhin.",
    ),
    "sleep_behavior": (
        "Normal continues HEM control; Pause requests this device off during Sleep, respecting minimum runtime and native protections; Sleep targets requests the Sleep target set. Sleep comes from this room or, when enabled on this device, from everyone sleeping. Automatic profile selection can also select Sleep under Normal. The configured wake alarm ends automatic Sleep early. Away and explicit presets retain their priority.",
        "Η κανονική λειτουργία συνεχίζει τον έλεγχο HEM. Η Παύση ζητά κλείσιμο κατά τον ύπνο, με τήρηση ελάχιστου χρόνου και προστασιών συσκευής. Οι Στόχοι ύπνου ζητούν το αντίστοιχο προφίλ. Ο Ύπνος προκύπτει από το δωμάτιο ή, αν ενεργοποιηθεί στη συσκευή, όταν όλοι κοιμούνται. Η αυτόματη επιλογή μπορεί να επιλέξει Ύπνο και στην κανονική λειτουργία. Το ρυθμισμένο ξυπνητήρι τερματίζει νωρίτερα τον αυτόματο Ύπνο. Η Απουσία και τα ρητά προφίλ διατηρούν την προτεραιότητά τους.",
        "Normal setzt die HEM-Steuerung fort; Pause fordert im Schlafmodus Aus an und beachtet Mindestlaufzeit und Geräteschutz; Schlaf-Sollwerte fordert das Schlafprofil an. Schlaf folgt dem eigenen Raum oder, bei aktivierter Geräteoption, dem Schlaf aller Bewohner. Auch bei Normal kann die automatische Profilwahl Schlaf wählen. Der konfigurierte Wecker beendet den automatischen Schlafmodus früher. Abwesenheit und ausdrücklich gewählte Profile behalten Vorrang.",
    ),
    "sleep_when_everyone_asleep": (
        "Off by default. In Automatic or PID, also apply this device's sleep behavior, Sleep targets and enabled quiet-sleep setting when at least one room is occupied and every occupied room is in the selected sleeping-room list, including rooms without HEM devices. An empty home does not mean everyone is sleeping; unknown evidence does not confirm it. This does not mark this device's room occupied or bypass its presence requirement. The configured wake alarm ends this automatic Sleep early so normal control can resume. Away, manual control, explicit presets and device protections retain their priority.",
        "Ανενεργό από προεπιλογή. Στο Αυτόματα ή PID, εφαρμόζει και σε αυτή τη συσκευή τη συμπεριφορά ύπνου, τους στόχους Ύπνου και την ενεργή αθόρυβη ρύθμιση ύπνου, όταν υπάρχει τουλάχιστον ένα κατειλημμένο δωμάτιο και όλα τα κατειλημμένα δωμάτια περιλαμβάνονται στη λίστα ύπνου, ακόμη και δωμάτια χωρίς συσκευές HEM. Άδειο σπίτι δεν σημαίνει ότι όλοι κοιμούνται· άγνωστα δεδομένα δεν το επιβεβαιώνουν. Δεν δηλώνει παρουσία στο δωμάτιο της συσκευής ούτε παρακάμπτει το κριτήριο παρουσίας της. Το ρυθμισμένο ξυπνητήρι τερματίζει νωρίτερα τον αυτόματο Ύπνο για επαναφορά του κανονικού ελέγχου. Η Απουσία, ο χειροκίνητος έλεγχος, τα ρητά προφίλ και οι προστασίες διατηρούν την προτεραιότητά τους.",
        "Standardmäßig aus. Bei Automatik oder PID gelten Schlafverhalten, Schlaf-Sollwerte und aktivierte leise Schlafeinstellung dieses Geräts auch dann, wenn mindestens ein Raum belegt ist und alle belegten Räume in der gewählten Schlafraumliste stehen, einschließlich Räumen ohne HEM-Geräte. Ein leeres Zuhause bedeutet nicht, dass alle schlafen; unbekannte Daten bestätigen dies nicht. Die Option macht den eigenen Raum nicht belegt und umgeht keine Anwesenheitsvoraussetzung. Der konfigurierte Wecker beendet diesen automatischen Schlafmodus früher, damit die normale Regelung fortgesetzt wird. Abwesenheit, manuelle Steuerung, ausdrückliche Profile und Geräteschutz behalten Vorrang.",
    ),
    "quiet_sleep": (
        "Use this device's configured quiet fan setting while its room is sleeping, or when its enabled everyone-sleeping option applies. The configured wake alarm ends automatic quiet-sleep behavior early. This changes the fan setting; the active target profile and separate sleep/presence policies remain in effect.",
        "Χρησιμοποιεί την επιλεγμένη αθόρυβη ρύθμιση ανεμιστήρα όταν το δωμάτιο είναι σε ύπνο ή ισχύει η ενεργή επιλογή της συσκευής «Όταν όλοι κοιμούνται». Το ρυθμισμένο ξυπνητήρι τερματίζει νωρίτερα την αυτόματη αθόρυβη λειτουργία ύπνου. Αλλάζει τη ρύθμιση ανεμιστήρα· το ενεργό προφίλ στόχων και οι ξεχωριστοί κανόνες ύπνου και παρουσίας εξακολουθούν να ισχύουν.",
        "Verwendet die konfigurierte leise Lüftereinstellung, solange der Raum schläft oder die aktivierte Option für den Schlaf aller Bewohner gilt. Der konfigurierte Wecker beendet die automatische leise Schlafeinstellung früher. Geändert wird die Lüftereinstellung; aktives Sollwertprofil und separate Schlaf-/Anwesenheitsregeln bleiben wirksam.",
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
    "announce_before_start": (
        "Off by default. When useful airing can reduce this device's current demand, announce the room, reason, device name and its waiting time before starting. The countdown starts after accepted delivery. If the windows stay closed, normal demand-based operation resumes when this device's timeout expires. Disabled means no airing request or added wait for this device. Existing window protection, operating minimums and other device rules still apply.",
        "Ανενεργό από προεπιλογή. Όταν ο αερισμός μπορεί να μειώσει την τρέχουσα ανάγκη, ανακοινώνει το δωμάτιο, την αιτία, το όνομα της συσκευής και τον χρόνο αναμονής πριν την εκκίνηση. Η αντίστροφη μέτρηση αρχίζει μετά την αποδοχή της ανακοίνωσης. Αν τα παράθυρα παραμείνουν κλειστά, η κανονική λειτουργία βάσει ζήτησης συνεχίζεται στη λήξη του χρόνου της συσκευής. Ανενεργό σημαίνει χωρίς αίτημα αερισμού ή πρόσθετη αναμονή γι’ αυτή τη συσκευή. Οι προστασίες παραθύρων και οι ελάχιστοι χρόνοι λειτουργίας εξακολουθούν να ισχύουν.",
        "Standardmäßig aus. Wenn Lüften den aktuellen Bedarf dieses Geräts verringern kann, werden Raum, Grund, Gerätename und Wartezeit vor dem Start angesagt. Die Frist beginnt nach Annahme der Ansage. Bleiben die Fenster geschlossen, wird nach Ablauf der Gerätefrist bedarfsgerecht weitergeregelt. Deaktiviert gibt es für dieses Gerät keine Lüftungsaufforderung oder zusätzliche Wartezeit. Fensterschutz, Mindestlaufzeiten und andere Gerätevorgaben gelten weiter.",
    ),
    "window_open_timeout_minutes": (
        "This device's waiting time after an accepted opening request, in minutes (0–30, default 5). Used only when its opening announcement is enabled. Zero adds no delay. Other devices have their own deadlines, and repeated announcements never restart this countdown. Turning the announcement off releases an existing wait; changing the time does not extend an active deadline.",
        "Χρόνος αναμονής αυτής της συσκευής μετά την αποδοχή αιτήματος ανοίγματος, σε λεπτά (0–30, προεπιλογή 5). Ισχύει μόνο όταν είναι ενεργή η ανακοίνωσή της. Το μηδέν δεν προσθέτει καθυστέρηση. Κάθε συσκευή έχει δική της προθεσμία και οι επαναλήψεις δεν επανεκκινούν τη μέτρηση. Η απενεργοποίηση της ανακοίνωσης λήγει την αναμονή· η αλλαγή χρόνου δεν παρατείνει ενεργή προθεσμία.",
        "Wartezeit dieses Geräts nach Annahme einer Aufforderung zum Fensteröffnen, in Minuten (0–30, Standard 5). Gilt nur bei aktivierter Geräteansage. Null fügt keine Verzögerung hinzu. Andere Geräte haben eigene Fristen; Wiederholungen starten die Frist nicht neu. Ausschalten der Ansage beendet eine laufende Wartezeit; eine Zeitänderung verlängert keine aktive Frist.",
    ),
    "announce_device_errors": (
        "Announce new faults reported by this physical device's existing Home Assistant error entities or attributes. The announcement includes the reported fault details and uses HEM's configured announcement delivery.",
        "Ανακοινώνει νέα σφάλματα από τις υπάρχουσες οντότητες ή ιδιότητες σφαλμάτων της πραγματικής συσκευής. Περιλαμβάνει τις λεπτομέρειες του σφάλματος και χρησιμοποιεί τη ρυθμισμένη αποστολή ανακοινώσεων του HEM.",
        "Meldet neue Fehler aus den bestehenden Fehlerentitäten oder Attributen des physischen Geräts. Die Meldung enthält die Fehlerdetails und nutzt die konfigurierte HEM-Ausgabe.",
    ),
    "native_full_output": (
        "For authorized Automatic/PID ON/OFF control. When on, request the physical device's reported maximum temperature for heating or maximum humidity for humidifying, and its reported minimum temperature for cooling or minimum humidity for dehumidifying. HEM's room target still determines demand and operating time. When off, leave the native setpoint unchanged and continue controlling operation from HEM's target. Fan speeds follow the mode settings and room quiet rules.\n"
        "For PID control, an unconfirmed full-output target receives at most three actual attempts while the device is available. If it still does not match, stop retrying that request and continue automatic ON/OFF control, keeping the reported target and diagnostic result visible. Power commands still require native feedback. Disabling this option also disables new timed-setpoint transitions; an already committed shutdown can finish safely.",
        "Για εγκεκριμένο έλεγχο ON/OFF με Αυτόματα/PID. Όταν είναι ανοικτή, ζητά τη μέγιστη θερμοκρασία που δηλώνει η πραγματική συσκευή για θέρμανση ή τη μέγιστη υγρασία για ύγρανση, και την ελάχιστη θερμοκρασία για ψύξη ή την ελάχιστη υγρασία για αφύγρανση. Ο στόχος δωματίου του HEM εξακολουθεί να καθορίζει τη ζήτηση και τον χρόνο λειτουργίας. Όταν είναι κλειστή, αφήνει τον στόχο της συσκευής αμετάβλητο και συνεχίζει τον έλεγχο λειτουργίας με βάση τον στόχο του HEM. Οι ταχύτητες ανεμιστήρα ακολουθούν τις ρυθμίσεις λειτουργίας και τους κανόνες ησυχίας του δωματίου.\n"
        "Στον έλεγχο PID, ένας μη επιβεβαιωμένος στόχος πλήρους απόδοσης δοκιμάζεται το πολύ τρεις φορές όταν η συσκευή είναι διαθέσιμη. Αν εξακολουθεί να διαφέρει, σταματούν οι επαναλήψεις του ίδιου αιτήματος και συνεχίζεται ο αυτόματος έλεγχος ON/OFF, με ορατό τον πραγματικό στόχο και το διαγνωστικό αποτέλεσμα. Οι εντολές ισχύος εξακολουθούν να απαιτούν επιβεβαίωση από τη συσκευή. Η απενεργοποίηση αυτής της επιλογής απενεργοποιεί και νέες μεταβάσεις χρονισμού στόχων· μια ήδη δεσμευμένη απενεργοποίηση μπορεί να ολοκληρωθεί με ασφάλεια.",
        "Für freigegebene Ein/Aus-Regelung mit Automatik/PID. Eingeschaltet wird die vom Gerät gemeldete Höchsttemperatur beim Heizen bzw. höchste Luftfeuchtigkeit beim Befeuchten angefordert, beim Kühlen die Mindesttemperatur und beim Entfeuchten die niedrigste Luftfeuchtigkeit. HEMs Raumsollwert bestimmt weiterhin Bedarf und Laufzeit. Ausgeschaltet bleibt der native Sollwert unverändert; HEM regelt den Betrieb weiterhin nach seinem Sollwert. Lüfterstufen folgen den Moduseinstellungen und den Ruheeinstellungen des Raums.\n"
        "Bei PID erhält ein unbestätigter Sollwert für volle Leistung höchstens drei tatsächliche Versuche, während das Gerät verfügbar ist. Bleibt die Rückmeldung abweichend, endet die Wiederholung dieses Auftrags und die automatische Ein/Aus-Regelung läuft weiter; gemeldeter Sollwert und Diagnose bleiben sichtbar. Schaltbefehle benötigen weiterhin die native Rückmeldung. Ausschalten dieser Option deaktiviert auch neue zeitgesteuerte Sollwertübergänge; eine bereits begonnene Abschaltung kann sicher abgeschlossen werden.",
    ),
    "timed_setpoint_sequence": (
        "For authorized Automatic/PID ON/OFF heating and cooling. During the authorized ON period, HEM requests full output using the physical device's reported maximum temperature in Heat or minimum temperature in Cool; the room target still determines demand. The separate Full-output setpoint option must be enabled; this timing option controls only the transitions.\n"
        "When on: wait 30 seconds after confirmed native ON before applying that setpoint. Before OFF, after minimum ON time and device protections permit a stop, send the opposite limit (minimum in Heat, maximum in Cool), then wait 30 seconds after sending it before requesting native OFF. The 30 seconds apply to these transitions; running time follows demand and operating limits. When off: omit these added waits and the opposite shutdown setpoint. Only native OFF feedback confirms that the device has stopped.",
        "Για εγκεκριμένο έλεγχο ON/OFF θέρμανσης και ψύξης με Αυτόματα/PID. Κατά το εγκεκριμένο διάστημα ON, το HEM ζητά πλήρη απόδοση με τη μέγιστη θερμοκρασία που δηλώνει η πραγματική συσκευή στη Θέρμανση ή την ελάχιστη στην Ψύξη· ο στόχος δωματίου εξακολουθεί να καθορίζει τη ζήτηση. Πρέπει να είναι ανοικτή η ξεχωριστή επιλογή Στόχος πλήρους απόδοσης· η επιλογή χρονισμού ελέγχει μόνο τις μεταβάσεις.\n"
        "Με την επιλογή ανοικτή: περιμένει 30 δευτερόλεπτα μετά την επιβεβαιωμένη ενεργοποίηση της συσκευής πριν εφαρμόσει αυτόν τον στόχο. Πριν από το OFF, αφού το επιτρέψουν ο ελάχιστος χρόνος ON και οι προστασίες, στέλνει το αντίθετο όριο (ελάχιστο στη Θέρμανση, μέγιστο στην Ψύξη) και περιμένει 30 δευτερόλεπτα από την αποστολή πριν ζητήσει OFF. Τα 30 δευτερόλεπτα αφορούν αυτές τις μεταβάσεις· η διάρκεια λειτουργίας ακολουθεί τη ζήτηση και τα όρια λειτουργίας. Με την επιλογή κλειστή, παραλείπει αυτές τις πρόσθετες αναμονές και τον αντίθετο στόχο κλεισίματος. Μόνο η πραγματική ένδειξη OFF επιβεβαιώνει τη διακοπή.",
        "Für freigegebene Ein/Aus-Regelung von Heizen und Kühlen mit Automatik/PID. Während der freigegebenen Einschaltphase fordert HEM volle Leistung an: beim Heizen mit der vom Gerät gemeldeten Höchsttemperatur, beim Kühlen mit dessen Mindesttemperatur. Der Raumsollwert bestimmt weiterhin den Bedarf. Die separate Option Sollwert für volle Leistung muss eingeschaltet sein; diese Zeitsteuerung betrifft nur die Übergänge.\n"
        "Eingeschaltet: Nach bestätigtem nativem Ein 30 Sekunden warten, bevor dieser Sollwert gesetzt wird. Vor Aus, sobald Mindestlaufzeit und Geräteschutz einen Stopp erlauben, das entgegengesetzte Limit senden (Minimum beim Heizen, Maximum beim Kühlen); 30 Sekunden nach dem Senden natives Aus anfordern. Die 30 Sekunden gelten für diese Übergänge; die Laufzeit folgt Bedarf und Betriebsgrenzen. Ausgeschaltet entfallen diese zusätzlichen Wartezeiten und der entgegengesetzte Abschalt-Sollwert. Erst die native Aus-Rückmeldung bestätigt den Stillstand.",
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
        "Minimum seconds the device must remain operating after confirmed ON before HEM may stop it. Set 0 to disable this forced hold for future operating cycles, for example on a radiator valve that needs no minimum run time. An ON minimum already recorded for the current cycle completes first. HEM still uses observed device transitions and waits for command confirmation; this does not change the external power-switch timing. Choose any required compressor interval from the device manufacturer's guidance.",
        "Ελάχιστα δευτερόλεπτα που πρέπει να λειτουργεί η συσκευή μετά την επιβεβαιωμένη ενεργοποίηση, πριν το HEM ζητήσει διακοπή. Όρισε 0 για να αφαιρέσεις αυτή την υποχρεωτική διάρκεια στους επόμενους κύκλους, για παράδειγμα σε βαλβίδα καλοριφέρ χωρίς απαίτηση ελάχιστου χρόνου. Ο ελάχιστος χρόνος που έχει ήδη καταγραφεί για τον τρέχοντα κύκλο ολοκληρώνεται πρώτα. Το HEM εξακολουθεί να χρησιμοποιεί τις παρατηρημένες αλλαγές κατάστασης και να περιμένει επιβεβαίωση εντολών· ο χρονισμός του εξωτερικού διακόπτη τροφοδοσίας δεν αλλάζει. Για συσκευές με συμπιεστή επίλεξε το απαιτούμενο διάστημα σύμφωνα με τον κατασκευαστή.",
        "Mindestlaufzeit des Geräts in Sekunden nach bestätigtem Ein, bevor HEM es stoppen darf. Mit 0 deaktivierst du diese erzwungene Laufzeit für künftige Betriebszyklen, etwa bei einem Heizkörperventil ohne erforderliche Mindestlaufzeit. Eine bereits für den aktuellen Zyklus gespeicherte Mindestlaufzeit wird zuerst abgeschlossen. HEM verwendet weiterhin beobachtete Zustandswechsel und wartet auf die Befehlsbestätigung; die Zeitvorgaben des externen Versorgungsschalters ändern sich nicht. Wähle ein erforderliches Kompressorintervall nach den Herstellerangaben.",
    ),
    "min_off_seconds": (
        "Minimum seconds the device must remain stopped after confirmed OFF before HEM may start it again. 0 disables this forced operating hold, which can suit a radiator valve that needs no minimum rest time. HEM keeps the observed OFF time and still waits for command confirmation; this does not change the external power-switch timing. Choose any required compressor restart interval from the device manufacturer's guidance.",
        "Ελάχιστα δευτερόλεπτα που πρέπει να παραμείνει εκτός λειτουργίας η συσκευή μετά την επιβεβαιωμένη διακοπή, πριν το HEM την εκκινήσει ξανά. Το 0 απενεργοποιεί αυτή την υποχρεωτική αναμονή και μπορεί να ταιριάζει σε βαλβίδα καλοριφέρ χωρίς απαίτηση ελάχιστου χρόνου διακοπής. Το HEM διατηρεί τον παρατηρημένο χρόνο διακοπής και εξακολουθεί να περιμένει επιβεβαίωση εντολών· ο χρονισμός του εξωτερικού διακόπτη τροφοδοσίας δεν αλλάζει. Για συμπιεστή επίλεξε το διάστημα επανεκκίνησης που ορίζει ο κατασκευαστής.",
        "Mindeststillstandszeit des Geräts in Sekunden nach bestätigtem Aus, bevor HEM es erneut starten darf. 0 deaktiviert diese erzwungene Wartezeit und kann für ein Heizkörperventil ohne erforderliche Ruhezeit passen. HEM behält den beobachteten Ausschaltzeitpunkt bei und wartet weiterhin auf die Befehlsbestätigung; die Zeitvorgaben des externen Versorgungsschalters ändern sich nicht. Wähle ein erforderliches Kompressor-Wiederanlaufintervall nach den Herstellerangaben.",
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
