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
    'sleep_behavior': ("Normal continues HEM control; Pause requests this device off during its room's Sleep condition, "
     'respecting minimum runtime and native protections; Sleep targets selects the Sleep target set. Automatic '
     'profile selection can also select Sleep under Normal. The configured wake alarm ends automatic Sleep '
     'early.\n'
     '\n'
     'The separate Keep device off when all asleep switch adds a household OFF rule for Automatic/PID. Normal '
     "or Sleep targets here does not cancel that rule. With the household option off, the room's own sleep "
     'behavior remains active.',
     'Η κανονική λειτουργία συνεχίζει τον έλεγχο HEM. Η Παύση ζητά κλείσιμο κατά τη συνθήκη Ύπνου του '
     'δωματίου, με τήρηση ελάχιστου χρόνου και φυσικών προστασιών. Οι Στόχοι ύπνου επιλέγουν το αντίστοιχο '
     'προφίλ. Η αυτόματη επιλογή μπορεί να επιλέξει Ύπνο και στην κανονική λειτουργία. Το ρυθμισμένο ξυπνητήρι '
     'τερματίζει νωρίτερα τον αυτόματο Ύπνο.\n'
     '\n'
     'Ο ξεχωριστός διακόπτης διατήρησης της συσκευής κλειστής όταν όλοι κοιμούνται προσθέτει κανόνα OFF για '
     'όλο το σπίτι στο Αυτόματα/PID. Η Κανονική λειτουργία ή οι Στόχοι ύπνου εδώ δεν ακυρώνουν αυτόν τον '
     'κανόνα. Με την επιλογή όλου του σπιτιού κλειστή, η συμπεριφορά ύπνου του ίδιου του δωματίου παραμένει '
     'ενεργή.',
     'Normal setzt die HEM-Regelung fort; Pause fordert während der Schlafbedingung des eigenen Raums Aus an '
     'und beachtet Mindestlaufzeit und Geräteschutz; Schlaf-Sollwerte wählt das Schlafprofil. Auch bei Normal '
     'kann die automatische Profilwahl Schlaf wählen. Der konfigurierte Wecker beendet den automatischen '
     'Schlafmodus früher.\n'
     '\n'
     'Der separate Schalter zum Ausschalten des Geräts, wenn alle schlafen, ergänzt eine '
     'Haushalts-Abschaltregel für Automatik/PID. Normal oder Schlaf-Sollwerte hier hebt diese Regel nicht auf. '
     'Bei deaktivierter Haushaltsoption bleibt das Schlafverhalten des eigenen Raums aktiv.'),
    'sleep_when_everyone_asleep': ('On: in Automatic or PID, keep this device off when household evidence confirms that at least one room is '
     'occupied and every occupied room is in the selected sleeping-room list, including rooms without HEM '
     'devices. If HEM is already running this device, request OFF after its minimum ON time and other stop '
     'protections permit it; require actual OFF feedback and prevent a new start while the condition holds.\n'
     '\n'
     'This household OFF rule also applies with an explicit Home or Comfort preset. An empty home, confirmed '
     'Away or unknown occupancy/sleep evidence does not mean everyone is asleep. The configured wake-alarm '
     'lead releases this household hold so normal control can resume if demand and the remaining rules allow '
     'it.\n'
     '\n'
     "Off (default): remove only this device's extra household sleep hold. Its own room's sleep behavior, "
     'presence rules, quiet limits and physical protections remain independently configured. This setting does '
     'not mark its room occupied or grant permission to start.',
     'Ενεργό: στο Αυτόματα ή PID, κρατά αυτή τη συσκευή κλειστή όταν τα δεδομένα σπιτιού επιβεβαιώνουν ότι '
     'υπάρχει τουλάχιστον ένα κατειλημμένο δωμάτιο και ότι όλα τα κατειλημμένα δωμάτια βρίσκονται στην '
     'επιλεγμένη λίστα ύπνου, μαζί με δωμάτια χωρίς συσκευές HEM. Αν το HEM λειτουργεί ήδη τη συσκευή, ζητά '
     'OFF μόλις το επιτρέψουν ο ελάχιστος χρόνος ON και οι προστασίες διακοπής· απαιτεί πραγματική ένδειξη OFF '
     'και αποτρέπει νέα εκκίνηση όσο ισχύει η συνθήκη.\n'
     '\n'
     'Ο κανόνας κλεισίματος ισχύει και με ρητά επιλεγμένο προφίλ Σπίτι ή Άνεση. Άδειο σπίτι, επιβεβαιωμένη '
     'Απουσία ή άγνωστα δεδομένα παρουσίας/ύπνου δεν σημαίνουν ότι όλοι κοιμούνται. Η ρυθμισμένη προετοιμασία '
     'πριν από το ξυπνητήρι αίρει αυτή την παύση ώστε να συνεχιστεί ο κανονικός έλεγχος, αν το επιτρέπουν η '
     'ζήτηση και οι υπόλοιποι κανόνες.\n'
     '\n'
     'Ανενεργό (προεπιλογή): αφαιρεί μόνο την πρόσθετη παύση αυτής της συσκευής λόγω ύπνου όλου του σπιτιού. Η '
     'συμπεριφορά ύπνου του δικού της δωματίου, οι κανόνες παρουσίας, τα όρια ησυχίας και οι φυσικές '
     'προστασίες παραμένουν ανεξάρτητες ρυθμίσεις. Δεν δηλώνει παρουσία στο δωμάτιο ούτε δίνει άδεια '
     'εκκίνησης.',
     'Eingeschaltet: Bei Automatik oder PID bleibt dieses Gerät aus, wenn die Hausdaten bestätigen, dass '
     'mindestens ein Raum belegt ist und alle belegten Räume in der ausgewählten Schlafraumliste stehen, '
     'einschließlich Räumen ohne HEM-Geräte. Läuft das Gerät bereits unter HEM, wird Aus angefordert, sobald '
     'Mindestlaufzeit und Abschaltschutz es erlauben; die tatsächliche Aus-Rückmeldung bleibt erforderlich und '
     'ein Neustart wird solange verhindert.\n'
     '\n'
     'Diese Haushalts-Abschaltregel gilt auch bei ausdrücklich gewähltem Zuhause- oder Komfortprofil. Ein '
     'leeres Zuhause, bestätigte Abwesenheit oder unbekannte Anwesenheits-/Schlafdaten bedeuten nicht, dass '
     'alle schlafen. Der konfigurierte Wecker-Vorlauf hebt diese Haushaltspause auf, damit die normale '
     'Regelung bei Bedarf und erfüllten übrigen Bedingungen fortgesetzt wird.\n'
     '\n'
     'Ausgeschaltet (Standard): Nur die zusätzliche Haushaltsschlaf-Pause dieses Geräts entfällt. '
     'Schlafverhalten des eigenen Raums, Anwesenheitsregeln, Ruhegrenzen und Geräteschutz bleiben separat '
     'eingestellt. Die Option erklärt den Raum nicht als belegt und erteilt keine Startfreigabe.'),
    'quiet_sleep': ("On: apply this device's configured quiet fan mode or percentage limit while its applicable sleep "
     'condition is active. For advertised Low/Medium/High stages, quiet is a speed ceiling: HEM lowers a '
     'higher stage and keeps an already lower normal stage. The configured wake alarm can end automatic '
     'quiet-sleep behavior early.\n'
     '\n'
     'Off (default): sleep alone no longer applies this fan limit. An enabled occupied-room quiet rule can '
     'still limit speed. With this switch on and uncertain sleep evidence, HEM conservatively retains the '
     'quiet ceiling until the evidence is known.\n'
     '\n'
     "This changes fan speed, not the room target or the device's ON/OFF timing. Presence, window "
     'protection and the separate keep-off-when-all-asleep rule still apply. Only native fan controls '
     'advertised by this device are used.',
     'Ενεργό: εφαρμόζει την επιλεγμένη αθόρυβη λειτουργία ή το όριο ποσοστού ανεμιστήρα όταν ισχύει η συνθήκη '
     'ύπνου της συσκευής. Στις διαθέσιμες βαθμίδες Χαμηλή/Μεσαία/Υψηλή, η ησυχία είναι ανώτατο όριο: το HEM '
     'μειώνει μια υψηλότερη βαθμίδα και διατηρεί μια ήδη χαμηλότερη κανονική βαθμίδα. Το ρυθμισμένο ξυπνητήρι '
     'μπορεί να τερματίσει νωρίτερα την αυτόματη αθόρυβη λειτουργία ύπνου.\n'
     '\n'
     'Ανενεργό (προεπιλογή): ο ύπνος από μόνος του δεν εφαρμόζει αυτό το όριο. Η ενεργή αθόρυβη ρύθμιση με '
     'παρουσία μπορεί ακόμη να περιορίζει την ταχύτητα. Όταν ο διακόπτης είναι ενεργός και τα δεδομένα ύπνου '
     'αβέβαια, το HEM διατηρεί συντηρητικά το αθόρυβο όριο ώσπου να επιβεβαιωθούν.\n'
     '\n'
     'Αλλάζει την ταχύτητα ανεμιστήρα, όχι τον στόχο δωματίου ή τους χρόνους ON/OFF της συσκευής. Παρουσία, '
     'προστασία παραθύρων και ο ξεχωριστός κανόνας κλεισίματος όταν όλοι κοιμούνται εξακολουθούν να ισχύουν. '
     'Χρησιμοποιούνται μόνο χειρισμοί ανεμιστήρα που δηλώνει η συσκευή.',
     'Eingeschaltet: Bei der geltenden Schlafbedingung werden die konfigurierte leise Lüfterstufe oder '
     'Prozentgrenze angewendet. Bei angebotenen Stufen Niedrig/Mittel/Hoch ist die Ruhevorgabe eine '
     'Obergrenze: HEM senkt eine höhere Stufe und behält eine bereits niedrigere normale Stufe bei. Der '
     'konfigurierte Wecker kann die automatische leise Schlafeinstellung früher beenden.\n'
     '\n'
     'Ausgeschaltet (Standard): Schlaf allein aktiviert diese Lüftergrenze nicht mehr. Die aktivierte '
     'Ruheregel bei Raumbelegung kann die Drehzahl weiterhin begrenzen. Ist dieser Schalter eingeschaltet und '
     'die Schlafinformation unsicher, hält HEM vorsorglich die Ruhegrenze ein, bis die Information bekannt '
     'ist.\n'
     '\n'
     'Geändert wird die Lüfterdrehzahl, weder der Raumsollwert noch die Ein/Aus-Zeit des Geräts. '
     'Anwesenheit, Fensterschutz und die separate Abschaltregel beim Schlaf aller Bewohner gelten weiterhin. '
     'Verwendet werden nur die vom Gerät angebotenen nativen Lüfterfunktionen.'),
    'quiet_occupied': ("On: apply this device's configured quiet fan mode or percentage ceiling while its own room is occupied. "
     'For discrete native fan stages, the quiet choice caps the normal requested stage; it does not raise a '
     'lower stage merely to reach the quiet limit. Unknown presence evidence conservatively keeps the quiet '
     'ceiling when this option is enabled.\n'
     '\n'
     'Off (default): room occupancy alone no longer applies this fan limit. The separate quiet-sleep option '
     'can still limit the fan. Normal fan demand and mode settings determine the remaining speed choice.\n'
     '\n'
     "This affects only this device's available native fan controls. Room targets, device ON/OFF timing, "
     'permission to run and physical protections remain independent.',
     'Ενεργό: εφαρμόζει την επιλεγμένη αθόρυβη λειτουργία ή το ανώτατο ποσοστό ανεμιστήρα όταν το δικό της '
     'δωμάτιο έχει παρουσία. Στις διακριτές βαθμίδες, η αθόρυβη επιλογή περιορίζει την κανονικά ζητούμενη '
     'ταχύτητα· δεν αυξάνει μια χαμηλότερη βαθμίδα μόνο για να φτάσει το όριο. Με ενεργή την επιλογή, άγνωστη '
     'παρουσία διατηρεί συντηρητικά το αθόρυβο όριο.\n'
     '\n'
     'Ανενεργό (προεπιλογή): η παρουσία στο δωμάτιο από μόνη της δεν εφαρμόζει αυτό το όριο. Η ξεχωριστή '
     'αθόρυβη επιλογή ύπνου μπορεί ακόμη να περιορίζει τον ανεμιστήρα. Η κανονική ζήτηση και οι ρυθμίσεις '
     'λειτουργίας καθορίζουν την υπόλοιπη επιλογή ταχύτητας.\n'
     '\n'
     'Αφορά μόνο τους διαθέσιμους πραγματικούς χειρισμούς ανεμιστήρα αυτής της συσκευής. Οι στόχοι δωματίου, '
     'οι χρόνοι ON/OFF της συσκευής, η άδεια λειτουργίας και οι φυσικές προστασίες παραμένουν ανεξάρτητα.',
     'Eingeschaltet: Im belegten eigenen Raum gelten die konfigurierte leise Lüfterstufe oder '
     'Prozentobergrenze dieses Geräts. Bei diskreten nativen Stufen begrenzt die Ruhevorgabe die normal '
     'angeforderte Stufe; eine niedrigere Stufe wird nicht eigens auf die Ruhegrenze angehoben. Bei '
     'unbekannter Raumbelegung bleibt die Ruhegrenze vorsorglich wirksam, solange diese Option aktiviert ist.\n'
     '\n'
     'Ausgeschaltet (Standard): Raumbelegung allein aktiviert diese Lüftergrenze nicht mehr. Die separate '
     'leise Schlafeinstellung kann den Lüfter weiterhin begrenzen. Normaler Bedarf und Moduseinstellungen '
     'bestimmen ansonsten die Drehzahl.\n'
     '\n'
     'Betrifft nur die verfügbaren nativen Lüfterfunktionen dieses Geräts. Raumsollwerte, Ein/Aus-Zeiten des '
     'Geräts, Betriebsfreigabe und Geräteschutz bleiben unabhängig davon.'),
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
    'sensor_verified': ("On: confirm that this device's selected PM2.5 measurement is suitable for automatic particle filtration. "
     "HEM still requires current valid readings and the device's normal control and power permissions.\n"
     '\n'
     "Off (default): remove this device-level confirmation. A separate confirmation on the room's PM2.5 source "
     'may still satisfy the requirement; otherwise automatic filtration remains blocked until the source is '
     'verified.\n'
     '\n'
     'This is source verification for particle filtration, not a measurement or calibration. It does not make '
     "a particle filter a remedy for CO₂, VOCs or other gases and does not change another device's "
     'verification.',
     'Ενεργό: επιβεβαιώνει ότι η επιλεγμένη μέτρηση PM2.5 είναι κατάλληλη για την αυτόματη φίλτρανση '
     'σωματιδίων αυτής της συσκευής. Το HEM εξακολουθεί να απαιτεί πρόσφατες έγκυρες μετρήσεις και τις '
     'κανονικές άδειες ελέγχου και ισχύος.\n'
     '\n'
     'Ανενεργό (προεπιλογή): αφαιρεί αυτή την επιβεβαίωση σε επίπεδο συσκευής. Ξεχωριστή επιβεβαίωση της πηγής '
     'PM2.5 του δωματίου μπορεί ακόμη να καλύπτει την απαίτηση· διαφορετικά η αυτόματη φίλτρανση μένει σε '
     'αναμονή μέχρι να επιβεβαιωθεί η πηγή.\n'
     '\n'
     'Είναι επιβεβαίωση πηγής για σωματίδια, όχι μέτρηση ή βαθμονόμηση. Δεν μετατρέπει ένα φίλτρο σωματιδίων '
     'σε λύση για CO₂, VOC ή άλλα αέρια και δεν αλλάζει την επιβεβαίωση άλλης συσκευής.',
     'Eingeschaltet: Bestätigt, dass die ausgewählte PM2.5-Messung dieses Geräts für automatische '
     'Partikelfilterung geeignet ist. HEM benötigt weiterhin aktuelle gültige Messwerte sowie die normalen '
     'Regelungs- und Schaltfreigaben.\n'
     '\n'
     'Ausgeschaltet (Standard): Diese Bestätigung auf Geräteebene entfällt. Eine separate Bestätigung der '
     'PM2.5-Quelle des Raums kann die Voraussetzung weiterhin erfüllen; andernfalls bleibt die automatische '
     'Filterung bis zur Quellenbestätigung gesperrt.\n'
     '\n'
     'Dies bestätigt eine Quelle für Partikelfilterung und ist keine Messung oder Kalibrierung. Ein '
     'Partikelfilter wird dadurch nicht zur Abhilfe für CO₂, VOC oder andere Gase; die Bestätigung anderer '
     'Geräte bleibt unverändert.'),
    "particle_cadr_m3h": (
        "Enter the purifier's rated clean-air delivery for particles at the relevant fan speed, in m³/h. HEM combines it with room volume for filtration estimates. Zero means unconfigured; CADR does not measure fresh-air ventilation or CO₂ removal.",
        "Δώσε την ονομαστική παροχή καθαρού αέρα για σωματίδια στη σχετική ταχύτητα, σε m³/h. Συνδυάζεται με τον όγκο δωματίου για εκτιμήσεις φίλτρανσης. Το μηδέν σημαίνει μη ρυθμισμένο· το CADR δεν μετρά αερισμό ή απομάκρυνση CO₂.",
        "Tragen Sie die angegebene Partikel-Reinluftleistung bei der betreffenden Lüfterstufe in m³/h ein. HEM nutzt sie mit dem Raumvolumen für Filterungsabschätzungen. Null bedeutet unkonfiguriert; CADR beschreibt weder Frischluft noch CO₂-Abfuhr.",
    ),
    'pause_on_window_open': ("On (default): when a selected window in this device's own room is confirmed open, HEM requests a guarded "
     "stop and prevents an automatic restart. It respects the device's minimum ON time and requires native OFF "
     'feedback. Missing or unknown window evidence holds new starts; it is not treated as a confirmed '
     'opening.\n'
     '\n'
     "After the room's windows close, automatic evaluation resumes once they have remained verified closed for "
     'one minute and the other operating conditions permit it. Windows in another room do not trigger this '
     "device's window policy.\n"
     '\n'
     "Off: remove this device's window-open pause and closure delay. Its normal demand, presence, sleep and "
     'physical protections still apply. The separate opening-request option controls whether to ask for airing '
     'before a start.',
     'Ενεργό (προεπιλογή): όταν επιβεβαιωθεί ότι άνοιξε επιλεγμένο παράθυρο του ίδιου δωματίου, το HEM ζητά '
     'ασφαλή διακοπή και αποτρέπει την αυτόματη επανεκκίνηση. Τηρεί τον ελάχιστο χρόνο ON της συσκευής και '
     'απαιτεί πραγματική ένδειξη OFF. Ελλιπή ή άγνωστα δεδομένα παραθύρων κρατούν σε αναμονή νέες εκκινήσεις· '
     'δεν θεωρούνται επιβεβαιωμένο άνοιγμα.\n'
     '\n'
     'Μετά το κλείσιμο των παραθύρων, η αυτόματη αξιολόγηση συνεχίζεται όταν παραμείνουν επιβεβαιωμένα κλειστά '
     'για ένα λεπτό και το επιτρέψουν οι υπόλοιπες συνθήκες. Παράθυρα άλλου δωματίου δεν ενεργοποιούν αυτή την '
     'προστασία.\n'
     '\n'
     'Ανενεργό: αφαιρεί την παύση λόγω παραθύρου και την αναμονή μετά το κλείσιμο για αυτή τη συσκευή. Η '
     'ζήτηση, η παρουσία, ο ύπνος και οι φυσικές προστασίες εξακολουθούν να ισχύουν. Η ξεχωριστή επιλογή '
     'αιτήματος ανοίγματος ελέγχει αν θα ζητηθεί αερισμός πριν από εκκίνηση.',
     'Eingeschaltet (Standard): Wird ein ausgewähltes Fenster im eigenen Raum als offen bestätigt, fordert HEM '
     'ein geschütztes Abschalten an und verhindert einen automatischen Neustart. Mindestlaufzeit und native '
     'Aus-Rückmeldung bleiben erforderlich. Fehlende oder unbekannte Fensterdaten halten neue Starts zurück '
     'und gelten nicht als bestätigte Öffnung.\n'
     '\n'
     'Nach dem Schließen wird automatisch neu bewertet, sobald alle betreffenden Fenster eine Minute '
     'durchgehend als geschlossen bestätigt sind und die übrigen Betriebsbedingungen erfüllt sind. Fenster '
     'anderer Räume lösen diese Gerätefunktion nicht aus.\n'
     '\n'
     'Ausgeschaltet: Fensterpause und Wiederanlaufverzögerung für dieses Gerät entfallen. Bedarf, Anwesenheit, '
     'Schlafregeln und Geräteschutz bleiben wirksam. Die separate Lüftungsaufforderung bestimmt, ob vor einem '
     'Start zum Öffnen aufgefordert wird.'),
    'announce_before_start': ('On: before this device starts automatically, HEM may ask for useful airing when verified room and '
     'outdoor conditions show that it can reduce the current need. The announcement names the room, reason, '
     "device and this device's waiting time. Its countdown starts only after accepted delivery.\n"
     '\n'
     "If the windows remain closed, the added wait ends at this device's timeout and normal control continues "
     "when demand and protections permit. If a window opens, the device's separate window-protection setting "
     'determines its window hold.\n'
     '\n'
     'Off (default): this device adds no opening request or airing wait. When it is an eligible remedy for the '
     'current cause, HEM also omits that covered cause from automatic opening announcements. A dehumidifier '
     'can cover humidity or mold; it cannot remove an unrelated CO₂ reason. Another waiting device does not '
     'recreate an opening request for the same covered cause.\n'
     '\n'
     "Applies only to this device's qualified automatic start. Turning this on does not authorize power, "
     "guarantee immediate operation or change another device's preference.",
     'Ενεργό: πριν από αυτόματη εκκίνηση, το HEM μπορεί να ζητήσει χρήσιμο αερισμό όταν επιβεβαιωμένα δεδομένα '
     'δωματίου και εξωτερικού χώρου δείχνουν ότι μειώνει την τρέχουσα ανάγκη. Η ανακοίνωση αναφέρει δωμάτιο, '
     'αιτία, συσκευή και τον χρόνο αναμονής της. Η αντίστροφη μέτρηση αρχίζει μόνο μετά την αποδοχή της '
     'ανακοίνωσης.\n'
     '\n'
     'Αν τα παράθυρα μείνουν κλειστά, η πρόσθετη αναμονή λήγει στον χρόνο της συσκευής και ο κανονικός έλεγχος '
     'συνεχίζεται όταν το επιτρέπουν η ζήτηση και οι προστασίες. Αν ανοίξει παράθυρο, η ξεχωριστή προστασία '
     'παραθύρων της συσκευής καθορίζει την παύση της.\n'
     '\n'
     'Ανενεργό (προεπιλογή): η συσκευή δεν προσθέτει αίτημα ανοίγματος ή αναμονή αερισμού. Όταν αποτελεί '
     'επιτρεπόμενη λύση για την τρέχουσα αιτία, το HEM αφαιρεί και αυτή την καλυμμένη αιτία από τις αυτόματες '
     'ανακοινώσεις ανοίγματος. Ένας αφυγραντήρας μπορεί να καλύπτει υγρασία ή μούχλα, αλλά όχι μια ανεξάρτητη '
     'ανάγκη λόγω CO₂. Άλλη συσκευή που περιμένει δεν επαναφέρει αίτημα για την ίδια καλυμμένη αιτία.\n'
     '\n'
     'Αφορά μόνο την κατάλληλη αυτόματη εκκίνηση αυτής της συσκευής. Δεν δίνει άδεια ισχύος, δεν εγγυάται '
     'άμεση λειτουργία και δεν αλλάζει τις επιλογές άλλων συσκευών.',
     'Eingeschaltet: Vor dem automatischen Start dieses Geräts kann HEM zum Lüften auffordern, wenn bestätigte '
     'Raum- und Außenbedingungen eine Verringerung des aktuellen Bedarfs erwarten lassen. Genannt werden Raum, '
     'Grund, Gerät und dessen Wartezeit. Die Frist beginnt erst nach angenommener Zustellung.\n'
     '\n'
     'Bleiben die Fenster geschlossen, endet die zusätzliche Wartezeit mit dem Geräte-Timeout; die normale '
     'Regelung läuft weiter, sobald Bedarf und Schutzbedingungen es erlauben. Bei geöffnetem Fenster bestimmt '
     'der separate Fensterschutz dieses Geräts die Pause.\n'
     '\n'
     'Ausgeschaltet (Standard): Dieses Gerät erzeugt keine Öffnungsaufforderung und keine Lüftungswartezeit. '
     'Kann es die aktuelle Ursache zulässig beheben, entfernt HEM diese abgedeckte Ursache auch aus '
     'automatischen Öffnungsansagen. Ein Entfeuchter kann Feuchtigkeit oder Schimmelbedarf abdecken, aber '
     'keinen unabhängigen CO₂-Grund. Ein weiteres wartendes Gerät erzeugt für dieselbe abgedeckte Ursache '
     'keine neue Aufforderung.\n'
     '\n'
     'Gilt nur für den zulässigen automatischen Start dieses Geräts. Die Option erteilt keine Schaltfreigabe, '
     'garantiert keinen sofortigen Betrieb und ändert keine Einstellung anderer Geräte.'),
    "window_open_timeout_minutes": (
        "This device's waiting time after an accepted opening request, in minutes (0–30, default 5). Used only when its opening announcement is enabled. Zero adds no delay. Other devices have their own deadlines, and repeated announcements never restart this countdown. Turning the announcement off releases an existing wait; changing the time does not extend an active deadline.",
        "Χρόνος αναμονής αυτής της συσκευής μετά την αποδοχή αιτήματος ανοίγματος, σε λεπτά (0–30, προεπιλογή 5). Ισχύει μόνο όταν είναι ενεργή η ανακοίνωσή της. Το μηδέν δεν προσθέτει καθυστέρηση. Κάθε συσκευή έχει δική της προθεσμία και οι επαναλήψεις δεν επανεκκινούν τη μέτρηση. Η απενεργοποίηση της ανακοίνωσης λήγει την αναμονή· η αλλαγή χρόνου δεν παρατείνει ενεργή προθεσμία.",
        "Wartezeit dieses Geräts nach Annahme einer Aufforderung zum Fensteröffnen, in Minuten (0–30, Standard 5). Gilt nur bei aktivierter Geräteansage. Null fügt keine Verzögerung hinzu. Andere Geräte haben eigene Fristen; Wiederholungen starten die Frist nicht neu. Ausschalten der Ansage beendet eine laufende Wartezeit; eine Zeitänderung verlängert keine aktive Frist.",
    ),
    'announce_device_errors': ('On (default): allow HEM to announce new faults and eligible command-nonresponse notices for this '
     "physical device through its configured announcement channels. Fault details come from the device's "
     'existing Home Assistant error entities or attributes; command notices describe actual unconfirmed '
     'requests.\n'
     '\n'
     'Off: silence these announcements for this device. Its reported errors, actual state and command '
     'diagnostics remain visible. Other devices keep their own announcement preferences.\n'
     '\n'
     'This is a notification preference. It does not change the control method, operate the device, clear a '
     'fault or acknowledge a pending command. Delivery also requires the relevant HEM announcement channel to '
     'be enabled.',
     'Ενεργό (προεπιλογή): επιτρέπει στο HEM να ανακοινώνει νέα σφάλματα και τις προβλεπόμενες ειδοποιήσεις μη '
     'απόκρισης εντολών για αυτή την πραγματική συσκευή, από τα ρυθμισμένα κανάλια ανακοινώσεων. Οι '
     'λεπτομέρειες σφάλματος προέρχονται από τις υπάρχουσες οντότητες ή ιδιότητες της συσκευής στο Home '
     'Assistant· οι ειδοποιήσεις εντολών περιγράφουν πραγματικά αιτήματα που δεν επιβεβαιώθηκαν.\n'
     '\n'
     'Ανενεργό: σταματά αυτές τις ανακοινώσεις μόνο για αυτή τη συσκευή. Τα δηλωμένα σφάλματα, η πραγματική '
     'κατάσταση και τα διαγνωστικά εντολών παραμένουν ορατά. Οι άλλες συσκευές διατηρούν τη δική τους '
     'επιλογή.\n'
     '\n'
     'Είναι προτίμηση ειδοποιήσεων. Δεν αλλάζει τη μέθοδο ελέγχου, δεν ενεργοποιεί τη συσκευή, δεν διαγράφει '
     'σφάλματα και δεν επιβεβαιώνει εκκρεμείς εντολές. Η αποστολή απαιτεί επίσης ενεργό το αντίστοιχο κανάλι '
     'ανακοινώσεων του HEM.',
     'Eingeschaltet (Standard): HEM darf neue Fehler und vorgesehene Hinweise auf unbestätigte Befehle dieses '
     'physischen Geräts über die konfigurierten Ausgabekanäle melden. Fehlerdetails stammen aus den '
     'vorhandenen Home-Assistant-Fehlerentitäten oder Attributen des Geräts; Befehlshinweise beschreiben '
     'tatsächlich unbestätigte Anforderungen.\n'
     '\n'
     'Ausgeschaltet: diese Meldungen für dieses Gerät unterdrücken. Gemeldete Fehler, tatsächlicher '
     'Gerätezustand und Befehlsdiagnosen bleiben sichtbar. Andere Geräte behalten ihre eigenen '
     'Meldeeinstellungen.\n'
     '\n'
     'Diese Option betrifft Benachrichtigungen. Sie ändert weder die Regelungsart noch den Gerätezustand, '
     'löscht keine Fehler und bestätigt keine ausstehenden Befehle. Für die Zustellung muss auch der '
     'entsprechende HEM-Ausgabekanal aktiviert sein.'),
    'native_full_output': ('On (default): during a confirmed ON period, HEM requests the native target that asks for maximum output '
     "in the active supported mode. This option is for this device's authorized Automatic/PID ON/OFF control. "
     'HEM uses only limits actually reported by the device.\n'
     '\n'
     "Off: leave the device's native target unchanged. HEM's room target still determines demand and ON/OFF "
     'timing. This preference does not change the room target or force continuous running. Available fan-speed '
     'controls continue to follow their mode settings and quiet limits.\n'
     '\n'
     'With PID, the same full-demand target gets at most three total dispatch attempts, including the first, '
     'while the device is available. Each attempt has one minute for feedback. If the third remains '
     'unconfirmed after that interval, HEM stops retrying that target and continues guarded ON/OFF control. '
     'The attempt count survives ordinary cycles and restarts; offline checks do not spend attempts.\n'
     '\n'
     'Requested and actually reported targets remain separately visible, with the unconfirmed result when '
     'applicable. Native ON/OFF commands still require real device feedback and obey operating limits. '
     'Automatic retains its existing retry policy; the three-attempt limit is for PID.',
     'Ενεργό (προεπιλογή): κατά το επιβεβαιωμένο διάστημα ON, το HEM ζητά τον πραγματικό στόχο που αντιστοιχεί '
     'στη μέγιστη απόδοση της ενεργής υποστηριζόμενης λειτουργίας. Η επιλογή αφορά τον εγκεκριμένο έλεγχο '
     'ON/OFF αυτής της συσκευής με Αυτόματα/PID. Χρησιμοποιούνται μόνο όρια που δηλώνει η ίδια η συσκευή.\n'
     '\n'
     'Ανενεργό: αφήνει αμετάβλητο τον στόχο της συσκευής. Ο στόχος δωματίου του HEM συνεχίζει να καθορίζει τη '
     'ζήτηση και τους χρόνους ON/OFF. Η επιλογή δεν αλλάζει τον στόχο δωματίου ούτε επιβάλλει συνεχή '
     'λειτουργία. Οι διαθέσιμες ταχύτητες ανεμιστήρα ακολουθούν τις ρυθμίσεις λειτουργίας και τα όρια ησυχίας '
     'τους.\n'
     '\n'
     'Στο PID, ο ίδιος στόχος μέγιστης απόδοσης έχει έως τρεις συνολικές απόπειρες αποστολής, μαζί με την '
     'πρώτη, όσο η συσκευή είναι διαθέσιμη. Κάθε απόπειρα έχει ένα λεπτό για επιβεβαίωση. Αν και η τρίτη '
     'παραμείνει ανεπιβεβαίωτη μετά από αυτό το διάστημα, το HEM σταματά τις επαναλήψεις του ίδιου στόχου και '
     'συνεχίζει τον προστατευμένο έλεγχο ON/OFF. Το πλήθος διατηρείται στους κανονικούς κύκλους και στις '
     'επανεκκινήσεις· οι έλεγχοι μη διαθεσιμότητας δεν καταναλώνουν απόπειρες.\n'
     '\n'
     'Ο ζητούμενος και ο πραγματικά δηλωμένος στόχος εμφανίζονται χωριστά, μαζί με το ανεπιβεβαίωτο αποτέλεσμα '
     'όπου ισχύει. Οι εντολές ON/OFF απαιτούν πραγματική ανάδραση και τηρούν τα όρια λειτουργίας. Η μέθοδος '
     'Αυτόματα διατηρεί την υπάρχουσα πολιτική επανάληψης· το όριο τριών αποπειρών αφορά το PID.',
     'Eingeschaltet (Standard): Während einer bestätigten Einschaltphase fordert HEM den nativen Sollwert für '
     'maximale Leistung in der aktiven unterstützten Betriebsart an. Die Option gilt für die freigegebene '
     'Ein/Aus-Regelung dieses Geräts mit Automatik/PID. Verwendet werden ausschließlich vom Gerät tatsächlich '
     'gemeldete Grenzen.\n'
     '\n'
     'Ausgeschaltet: Den nativen Gerätesollwert unverändert lassen. HEMs Raumsollwert bestimmt weiterhin '
     'Bedarf und Ein/Aus-Zeiten. Die Option ändert weder den Raumsollwert noch erzwingt sie Dauerbetrieb. '
     'Verfügbare Lüfterstufen folgen weiterhin ihren Moduseinstellungen und Ruhegrenzen.\n'
     '\n'
     'Bei PID gibt es für denselben Sollwert für volle Leistung insgesamt höchstens drei Sendeversuche '
     'einschließlich des ersten, solange das Gerät verfügbar ist. Nach jedem Versuch bleibt eine Minute für '
     'die Rückmeldung. Bleibt auch der dritte danach unbestätigt, endet die Wiederholung dieses Sollwerts und '
     'die geschützte Ein/Aus-Regelung läuft weiter. Der Zähler bleibt über normale Betriebszyklen und '
     'Neustarts erhalten; Offline-Prüfungen verbrauchen keine Versuche.\n'
     '\n'
     'Angeforderter und tatsächlich gemeldeter Sollwert bleiben getrennt sichtbar, gegebenenfalls mit dem '
     'unbestätigten Ergebnis. Ein/Aus-Befehle benötigen weiterhin echte Geräterückmeldung und beachten '
     'Betriebsgrenzen. Automatik behält ihre bisherige Wiederholungsregel; die Begrenzung auf drei Versuche '
     'gilt für PID.'),
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


_NATIVE_MODE_TARGET_HELP = {
    "heat": (
        "{mode}: request the highest temperature actually reported as supported by this device.",
        "{mode}: ζητά τη μέγιστη θερμοκρασία που δηλώνει ότι υποστηρίζει η συσκευή.",
        "{mode}: die höchste vom Gerät tatsächlich als unterstützt gemeldete Temperatur anfordern.",
    ),
    "cool": (
        "{mode}: request the lowest temperature actually reported as supported by this device.",
        "{mode}: ζητά την ελάχιστη θερμοκρασία που δηλώνει ότι υποστηρίζει η συσκευή.",
        "{mode}: die niedrigste vom Gerät tatsächlich als unterstützt gemeldete Temperatur anfordern.",
    ),
    "dry": (
        "{mode}: request the lowest relative-humidity target actually reported as supported by this device.",
        "{mode}: ζητά τον ελάχιστο στόχο σχετικής υγρασίας που δηλώνει ότι υποστηρίζει η συσκευή.",
        "{mode}: den niedrigsten vom Gerät tatsächlich als unterstützt gemeldeten Sollwert der relativen Luftfeuchtigkeit anfordern.",
    ),
    "humidify": (
        "{mode}: request the highest relative-humidity target actually reported as supported by this device.",
        "{mode}: ζητά τον μέγιστο στόχο σχετικής υγρασίας που δηλώνει ότι υποστηρίζει η συσκευή.",
        "{mode}: den höchsten vom Gerät tatsächlich als unterstützt gemeldeten Sollwert der relativen Luftfeuchtigkeit anfordern.",
    ),
}


def equipment_configuration_help(key: str, locale: str = "en", *, modes=None) -> str:
    """Describe one setting, using only supplied device modes when applicable."""
    language = str(locale or "en").replace("_", "-").casefold().split("-")[0]
    index = {"el": 1, "de": 2}.get(language, 0)
    description = HELP.get(key, HELP["climate"])[index]
    if key != "native_full_output" or modes is None:
        return description
    if __package__:
        from .equipment_name_catalog import _native_target_modes
        from .operating_mode_catalog import operating_mode_label
    else:
        # Standalone catalog tests have no package or Home Assistant imports.
        from pathlib import Path
        from runpy import run_path
        catalog = run_path(str(Path(__file__).with_name("equipment_name_catalog.py")))
        _native_target_modes = catalog["_native_target_modes"]
        operating_mode_label = catalog["operating_mode_label"]
    applicable = _native_target_modes(modes)
    if not applicable:
        return (
            "This device currently has no verified operating mode that supports this optional native target.",
            "Η συσκευή δεν έχει αυτή τη στιγμή επιβεβαιωμένη λειτουργία που να υποστηρίζει αυτόν τον προαιρετικό στόχο.",
            "Für dieses Gerät ist derzeit keine Betriebsart bestätigt, die diesen optionalen nativen Sollwert unterstützt.",
        )[index]
    paragraphs = description.split("\n\n")
    paragraphs[1:1] = [_NATIVE_MODE_TARGET_HELP[mode][index].format(
        mode=operating_mode_label(mode, locale)) for mode in applicable]
    return "\n\n".join(paragraphs)
