"""Setting-specific purpose text for HEM configuration entities.

All static settings have native English, Greek and German explanations. Other
UI locales use deterministic English help while keeping localized entity names.
No file access, services, settings writes or registry edits occur at runtime.
"""
from __future__ import annotations

from .settings_name_catalog import (
    localized_setting_name, localized_setting_group, setting_locale,
)

SETTING_HELP = {'area_area_environment_air_speed_m_s': {'de': 'Gemessene Luftgeschwindigkeit im Raum in m/s für PMV/PPD, '
                                               'wenn keine Live-Quelle gewählt ist. Eine repräsentative '
                                               'Messung verwenden, nicht die prozentuale Ventilatorstellung.',
                                         'el': 'Μετρημένη ταχύτητα αέρα χώρου σε m/s για υπολογισμούς '
                                               'PMV/PPD όταν δεν έχει επιλεγεί ζωντανή πηγή ταχύτητας. '
                                               'Χρησιμοποίησε αντιπροσωπευτική μέτρηση, όχι ποσοστό '
                                               'ανεμιστήρα.',
                                         'en': 'Measured room air speed in m/s used by advanced PMV/PPD '
                                               'comfort calculations when no live air-speed source is '
                                               'selected. Enter a representative measurement, not a fan’s '
                                               'percentage setting.'},
 'area_area_environment_clo': {'de': 'Repräsentative Bekleidungsisolation in clo für PMV/PPD. Bei geänderter '
                                     'üblicher Kleidung anpassen. Beeinflusst die Komfortschätzung, setzt '
                                     'nicht direkt eine Temperatur.',
                               'el': 'Αντιπροσωπευτική μόνωση ενδυμάτων σε clo για υπολογισμούς PMV/PPD. '
                                     'Αλλάζει μαζί με τη συνήθη ένδυση· επηρεάζει την εκτίμηση άνεσης, όχι '
                                     'άμεσα τη θερμοκρασία.',
                               'en': 'Representative clothing insulation in clo for advanced PMV/PPD comfort '
                                     'calculations. Update it when typical clothing changes; it influences '
                                     'the comfort estimate rather than directly setting a temperature.'},
 'area_area_environment_co2_target_ppm': {'de': 'CO₂-Raumziel in ppm zum Erlernen der '
                                                'Fensterlüftungswirkung aus geeigneten NDIR-Verläufen '
                                                'und für Abluftempfehlungen. Gemessenes CO₂ ab diesem '
                                                'Ziel + 200 ppm gilt dabei als erhöht; Außenluft- und '
                                                'Quellenprüfungen bleiben erforderlich. Die separate '
                                                'allgemeine CO₂-Schwelle für Fensteröffnungsempfehlungen '
                                                'wird dadurch nicht geändert.',
                                          'el': 'Στόχος CO₂ χώρου σε ppm για εκμάθηση '
                                                'αποτελεσματικότητας αερισμού από κατάλληλο ιστορικό '
                                                'NDIR και για συμβουλές απαγωγής. Για την απαγωγή, '
                                                'μετρημένο CO₂ από τον στόχο + 200 ppm θεωρείται '
                                                'αυξημένο· εξακολουθούν να ισχύουν οι έλεγχοι εξωτερικού '
                                                'αέρα και πηγών. Δεν αλλάζει το ξεχωριστό γενικό όριο '
                                                'CO₂ για πρόταση ανοίγματος παραθύρων.',
                                          'en': 'Room CO₂ target in ppm for learning window-ventilation '
                                                'effectiveness from qualified NDIR history and for '
                                                'extraction advice. Extraction advice treats measured '
                                                'CO₂ at or above this target + 200 ppm as elevated; '
                                                'outdoor-air and source checks still apply. This does '
                                                'not change the separate general CO₂ window-opening '
                                                'threshold.'},
 'area_area_environment_enable_pmv': {'de': 'Aktiviert die erweiterte ISO-7730-PMV/PPD-Bewertung. Gemessene '
                                            'Strahlungstemperatur, Luftgeschwindigkeit sowie Aktivität und '
                                            'Kleidung sind erforderlich. Die Bewertung allein gibt keine '
                                            'Klimasteuerung frei und wählt PMV nicht als Regelziel.',
                                      'el': 'Ενεργοποιεί προηγμένη αξιολόγηση ISO 7730 PMV/PPD. Απαιτούνται '
                                            'μετρημένη ακτινοβολούμενη θερμοκρασία, ταχύτητα αέρα, '
                                            'δραστηριότητα και ένδυση. Η ενεργοποίηση δεν επιτρέπει από μόνη '
                                            'της εντολές ούτε επιλέγει PMV ως στόχο ελέγχου.',
                                      'en': 'Enables advanced ISO 7730 PMV/PPD assessment for this room. '
                                            'Measured radiant temperature, air speed, activity and clothing '
                                            'inputs are required. Enabling assessment alone does not '
                                            'authorize climate actuation or select PMV as the control '
                                            'target.'},
 'area_area_environment_met': {'de': 'Repräsentative Stoffwechselaktivität in met als Eingabe für PMV/PPD. '
                                     'Aktivität beeinflusst den thermischen Komfort; kein Schwellwert für '
                                     'einen Bewegungssensor.',
                               'el': 'Αντιπροσωπευτική μεταβολική δραστηριότητα σε met για προηγμένο '
                                     'υπολογισμό PMV/PPD. Η δραστηριότητα επηρεάζει τη θερμική άνεση· είναι '
                                     'είσοδος μοντέλου, όχι όριο αισθητήρα κίνησης.',
                               'en': 'Representative occupant metabolic activity in met for advanced PMV/PPD '
                                     'comfort calculations. Activity changes perceived thermal comfort; this '
                                     'is a model input, not an activity-sensor threshold.'},
 'area_area_environment_particle_cadr_m3h': {'de': 'Alter Raum-Partikel-CADR als Ersatz, bis ein Wert je '
                                                   'Luftreiniger eingerichtet ist. Dient mit dem Raumvolumen '
                                                   'zur nominalen Reinluftwechsel-Schätzung, nicht zur '
                                                   'Gasentfernung.',
                                             'el': 'Παλαιά τιμή CADR σωματιδίων χώρου, ως εφεδρική μέχρι να '
                                                   'ρυθμιστεί CADR ανά καθαριστή. Με τον όγκο χώρου εκτιμά '
                                                   'ονομαστικές ανανεώσεις καθαρού αέρα, όχι αφαίρεση '
                                                   'αερίων.',
                                             'en': 'Legacy room particle-CADR value retained as a fallback '
                                                   'until a per-device purifier CADR is configured. Used '
                                                   'with measured room volume to estimate nominal clean-air '
                                                   'changes, not gas removal.'},
 'area_area_environment_radon_reference_bq_m3': {'de': 'Referenz in Bq/m³ für die jährliche '
                                                       'Radonbeurteilung. HEM vergleicht sie mit ausreichend '
                                                       'abgedeckten Langzeitdaten. Kurze Messungen oder eine '
                                                       'Grenzwertänderung belegen keine sichere '
                                                       'Jahresexposition.',
                                                 'el': 'Τιμή αναφοράς σε Bq/m³ για ετήσια αξιολόγηση '
                                                       'ραδονίου. Συγκρίνεται με επαρκώς καλυμμένο '
                                                       'μακροχρόνιο ιστορικό· σύντομη μέτρηση ή αλλαγή ορίου '
                                                       'δεν τεκμηριώνει ασφαλή ετήσια έκθεση.',
                                                 'en': 'Reference in Bq/m³ for the annual radon screening '
                                                       'assessment. HEM compares qualified long-term '
                                                       'coverage with it; a short measurement or changing '
                                                       'this value cannot establish a safe annual exposure.'},
 'area_area_environment_room_volume_m3': {'de': 'Gemessenes nutzbares Raumluftvolumen in m³, meist '
                                                'Grundfläche mal Deckenhöhe. Dient mit dem Partikel-CADR '
                                                'eines Reinigers zur nominalen Reinluftwechsel-Schätzung; '
                                                'keine gemessene Lüftungsrate.',
                                          'el': 'Μετρημένος ωφέλιμος όγκος αέρα σε m³, συνήθως εμβαδόν επί '
                                                'ύψος οροφής. Με το CADR καθαριστή εκτιμά ονομαστικές '
                                                'ανανεώσεις καθαρού αέρα ανά ώρα· δεν μετρά πραγματικό '
                                                'αερισμό.',
                                          'en': 'Measured usable room air volume in m³, usually floor area '
                                                'multiplied by ceiling height. Used with a purifier’s '
                                                'particle CADR to estimate nominal clean-air changes per '
                                                'hour; it is not a measured ventilation rate.'},
 'area_area_environment_sleep_room': {'de': 'Kennzeichnet den Raum als Schlafraum NUR für die kalibrierte '
                                            'Lärmauswertung des letzten abgeschlossenen lokalen Zeitfensters '
                                            '22:00–07:00. Ohne konfigurierte kalibrierte Lärmquelle ohne '
                                            'Wirkung. Aktiviert kein Schlaf-Klimaprofil und meldet keinen '
                                            'aktuellen Schlaf.',
                                      'el': 'Χαρακτηρίζει τον χώρο ως χώρο ύπνου ΜΟΝΟ για αξιολόγηση '
                                            'βαθμονομημένου θορύβου στο τελευταίο ολοκληρωμένο τοπικό '
                                            'διάστημα 22:00–07:00. Χωρίς αντίστοιχη πηγή δεν έχει επίδραση. '
                                            'Δεν ενεργοποιεί προφίλ Ύπνου ούτε δηλώνει ότι κάποιος κοιμάται '
                                            'τώρα.',
                                      'en': 'Classifies this room as used for sleeping ONLY for the last '
                                            'completed local 22:00–07:00 calibrated-noise assessment. It has '
                                            'no effect without a configured calibrated noise source and does '
                                            'not activate a climate Sleep profile or indicate someone is '
                                            'asleep now.'},
 'area_area_science_air_speed_entity': {'de': 'Live-Messquelle der Raumluftgeschwindigkeit für PMV/PPD. Ein '
                                              'aktueller gültiger Wert ersetzt die feste '
                                              'Luftgeschwindigkeit. Ein Ventilatorprozentsatz ist keine '
                                              'Luftgeschwindigkeitsmessung.',
                                        'el': 'Ζωντανή μετρημένη ταχύτητα αέρα χώρου για PMV/PPD. Η τρέχουσα '
                                              'έγκυρη τιμή χρησιμοποιείται αντί της σταθερής εισόδου. Το '
                                              'ποσοστό ανεμιστήρα δεν είναι μέτρηση ταχύτητας αέρα.',
                                        'en': 'Live measured room air-speed source for advanced PMV/PPD '
                                              'comfort. Its current valid value is used in place of the '
                                              'fixed air-speed input. A fan percentage is not an air-speed '
                                              'measurement.'},
 'area_area_science_radiant_temperature_entity': {'de': 'Tatsächlich gemessene mittlere Strahlungstemperatur '
                                                        'für PMV/PPD. Sie beschreibt die umgebenden '
                                                        'Oberflächen und darf nicht durch eine beliebige '
                                                        'Außen- oder Lufttemperatur ersetzt werden.',
                                                  'el': 'Πραγματική πηγή μετρημένης μέσης ακτινοβολούμενης '
                                                        'θερμοκρασίας για PMV/PPD. Περιγράφει την '
                                                        'ακτινοβολία γύρω επιφανειών· δεν αντικαθίσταται με '
                                                        'τυχαία εξωτερική ή θερμοκρασία αέρα.',
                                                  'en': 'Actual measured mean radiant-temperature source for '
                                                        'advanced PMV/PPD comfort. It describes surrounding '
                                                        'surface radiation and must not be substituted with '
                                                        'an arbitrary outdoor or room-air temperature.'},
 'area_climate_operating_comfort_adjustment_max_c': {'de': 'Größte erlaubte Temperaturabweichung vom aktiven '
                                                           'Profil bei feuchteabhängiger Komfort- oder '
                                                           'qualifizierter PMV-Anpassung. Die feste '
                                                           'Temperaturregelung verwendet diese Anpassung '
                                                           'nicht.',
                                                     'el': 'Μέγιστη επιτρεπτή μετατόπιση θερμοκρασίας από το '
                                                           'ενεργό προφίλ με αυτόματη άνεση βάσει υγρασίας ή '
                                                           'κατάλληλο PMV. Η ρύθμιση σταθερής θερμοκρασίας '
                                                           'δεν τη χρησιμοποιεί.',
                                                     'en': 'Largest allowed temperature offset from the '
                                                           'active profile when automatic humidity-aware '
                                                           'comfort or qualified PMV adjustment is selected. '
                                                           'Fixed-temperature control does not use this '
                                                           'adjustment.'},
 'area_climate_operating_cooling_dry_deferral_rh_points': {'de': 'Zusätzliche Prozentpunkte relativer '
                                                                 'Feuchte, die bei bereits kühlender '
                                                                 'Klimaanlage für separate Entfeuchtung '
                                                                 'erforderlich sind. Die einheitlichen '
                                                                 'Gerätekontroller vergleichen mit dem '
                                                                 'Feuchteziel des aktiven Profils plus '
                                                                 'dieser Marge; die ältere '
                                                                 'Raumkoordination nutzt die obere '
                                                                 'Raumfeuchteschwelle plus Marge. Null '
                                                                 'entfernt die zusätzliche Marge; '
                                                                 'weitere Bedarfsprüfungen gelten '
                                                                 'weiterhin.',
                                                           'el': 'Πρόσθετες ποσοστιαίες μονάδες σχετικής '
                                                                 'υγρασίας που απαιτούνται για ξεχωριστή '
                                                                 'αφύγρανση ενώ το κλιματιστικό ήδη '
                                                                 'ψύχει. Οι ενιαίοι ελεγκτές συσκευών '
                                                                 'συγκρίνουν με τον στόχο υγρασίας του '
                                                                 'ενεργού προφίλ συν αυτό το περιθώριο· '
                                                                 'ο παλαιός συντονισμός χώρου '
                                                                 'χρησιμοποιεί το ανώτερο όριο υγρασίας '
                                                                 'χώρου συν το περιθώριο. Το μηδέν '
                                                                 'αφαιρεί το πρόσθετο περιθώριο· ισχύουν '
                                                                 'οι υπόλοιποι έλεγχοι ζήτησης.',
                                                           'en': 'Extra relative-humidity percentage '
                                                                 'points required while AC is already '
                                                                 'cooling before separate '
                                                                 'dehumidification may run. Unified '
                                                                 'device controllers compare against the '
                                                                 'active profile humidity target plus '
                                                                 'this margin; legacy room coordination '
                                                                 'uses the upper room-humidity threshold '
                                                                 'plus the margin. Zero removes the '
                                                                 'extra margin; other demand checks '
                                                                 'still apply.'},
 'area_climate_operating_extraction_speed_percent': {'de': 'Höchste Solldrehzahl eines bereits laufenden '
                                                           'unterstützten Abluftventilators bei bestätigtem '
                                                           'Frischluftbedarf. Diese Einstellung schaltet ihn '
                                                           'nicht selbst ein und belegt keine geeignete '
                                                           'Außenluft.',
                                                     'el': 'Μέγιστη επιθυμητή ταχύτητα υποστηριζόμενου '
                                                           'εξαεριστήρα που ήδη λειτουργεί, όταν '
                                                           'επιβεβαιωμένη ζήτηση ποιότητας αέρα απαιτεί '
                                                           'εξωτερική ανανέωση. Δεν ενεργοποιεί από μόνη της '
                                                           'τον ανεμιστήρα ούτε αποδεικνύει κατάλληλο '
                                                           'εξωτερικό αέρα.',
                                                     'en': 'Highest target speed for a supported extraction '
                                                           'fan that is already on when verified air-quality '
                                                           'demand calls for outside-air exchange. This '
                                                           'speed setting does not itself switch the fan on '
                                                           'or establish that outdoor air is suitable.'},
 'area_climate_operating_humidity_high_rh': {'de': 'Obere Raumfeuchteschwelle für Entfeuchtungsbedarf und '
                                                   'Gerätekoordination. Sie ist vom gespeicherten '
                                                   'Feuchteziel jedes Profils getrennt. Kühlaufschub und '
                                                   'Hysterese können eine separate Entfeuchtung verzögern.',
                                             'el': 'Ανώτερο όριο σχετικής υγρασίας για αίτημα '
                                                   'ξήρανσης/αφύγρανσης και συντονισμό συσκευών. Διαφέρει '
                                                   'από τον στόχο υγρασίας κάθε προφίλ. Αναβολή κατά την '
                                                   'ψύξη και υστέρηση μπορούν να καθυστερήσουν ξεχωριστή '
                                                   'αφύγρανση.',
                                             'en': 'Upper room relative-humidity threshold used to request '
                                                   'drying/dehumidification and coordinate devices. It is '
                                                   'separate from the saved humidity target of each profile. '
                                                   'Cooling deferral and hysteresis can delay a separate '
                                                   'drying action.'},
 'area_climate_operating_humidity_hysteresis_rh': {'de': 'Feuchtemarge in Prozentpunkten um die '
                                                         'Entscheidungsschwellen. Verringert wiederholte '
                                                         'Wechsel zwischen Befeuchten und Trocknen nahe '
                                                         'einer Grenze; kein Feuchtesollwert.',
                                                   'el': 'Περιθώριο σχετικής υγρασίας σε ποσοστιαίες μονάδες '
                                                         'γύρω από τα όρια αποφάσεων. Περιορίζει '
                                                         'επαναλαμβανόμενες αλλαγές ύγρανσης/αφύγρανσης '
                                                         'κοντά στο όριο· δεν είναι στόχος υγρασίας.',
                                                   'en': 'Relative-humidity margin in percentage points '
                                                         'around the humidity decision thresholds. It '
                                                         'reduces repeated humidify/dry changes near a '
                                                         'boundary; it is a margin, not a target relative '
                                                         'humidity.'},
 'area_climate_operating_humidity_low_rh': {'de': 'Untere Raumfeuchteschwelle für Befeuchtungsbedarf in der '
                                                  'Feuchtekoordination. Profilziel und Raum-/Gerätegrenzen '
                                                  'sind getrennte Einstellungen; Hysterese vermeidet '
                                                  'schnelle Wechsel.',
                                            'el': 'Κατώτερο όριο σχετικής υγρασίας για αίτημα ύγρανσης στον '
                                                  'συντονισμό υγρασίας. Ο στόχος προφίλ και τα όρια '
                                                  'χώρου/συσκευής είναι χωριστές ρυθμίσεις· η υστέρηση '
                                                  'αποτρέπει συχνές εναλλαγές.',
                                            'en': 'Lower room relative-humidity threshold used by humidity '
                                                  'demand/arbitration to request humidification. The '
                                                  'selected profile target and room/device limits are '
                                                  'separate settings; hysteresis prevents rapid decisions '
                                                  'around the band.'},
 'area_climate_operating_occupancy_stale_minutes': {'de': 'Maximales Alter der Meldungen ausgewählter '
                                                          'lokaler Raumanwesenheitssensoren in Minuten. '
                                                          'Ältere oder fehlende Meldungen gelten als '
                                                          'unbekannt und belegen weder Anwesenheit noch '
                                                          'Abwesenheit. Gemeinsame Raumlisten haben eine '
                                                          'eigene Altersgrenze; diese Einstellung wählt '
                                                          'kein Ersatz-Klimaprofil.',
                                                    'el': 'Μέγιστη ηλικία, σε λεπτά, αναφορών από τους '
                                                          'επιλεγμένους τοπικούς αισθητήρες παρουσίας '
                                                          'χώρου. Παλιές ή ελλιπείς αναφορές θεωρούνται '
                                                          'άγνωστες και δεν αποδεικνύουν παρουσία ή '
                                                          'απουσία. Οι κοινές λίστες δωματίων έχουν '
                                                          'ξεχωριστό όριο ηλικίας· αυτή η ρύθμιση δεν '
                                                          'επιλέγει εφεδρικό κλιματικό προφίλ.',
                                                    'en': 'Maximum age in minutes of selected local '
                                                          'room-presence sensor reports. Older or '
                                                          'missing reports count as unknown and cannot '
                                                          'establish occupancy or absence. Shared '
                                                          'room-list sources have a separate age limit; '
                                                          'this setting does not choose a fallback '
                                                          'climate profile.'},
 'area_climate_operating_pm25_action_ug_m3': {'de': 'Momentane PM2.5-Raumschwelle in µg/m³ für '
                                                    'Luftreinigerbedarf. Betriebsschwelle, kein '
                                                    'Tagesexpositionsgrenzwert. Die Regelung benötigt '
                                                    'zusätzlich den passenden Gerätemodus und Freigaben.',
                                              'el': 'Στιγμιαίο όριο PM2.5 χώρου σε µg/m³ για ζήτηση '
                                                    'λειτουργίας καθαριστή. Είναι λειτουργικό όριο ελέγχου, '
                                                    'όχι ημερήσιο όριο έκθεσης. Απαιτούνται και η κατάλληλη '
                                                    'λειτουργία και άδειες συσκευής.',
                                              'en': 'Instantaneous room PM2.5 threshold in µg/m³ used for '
                                                    'purifier-fan demand. It is an operational control '
                                                    'threshold, not a daily exposure limit. Fan control also '
                                                    'requires the device’s configured mode and permissions.'},
 'area_climate_operating_purifier_speed_percent': {'de': 'Höchste Solldrehzahl eines bereits laufenden '
                                                         'unterstützten Luftreinigers bei Partikelbedarf. '
                                                         'Ändert den Luftstrombedarf, nicht den Nenn-CADR '
                                                         'oder die gemessene Filterwirkung.',
                                                   'el': 'Μέγιστη επιθυμητή ταχύτητα υποστηριζόμενου '
                                                         'καθαριστή που ήδη λειτουργεί όταν υπάρχει ζήτηση '
                                                         'λόγω σωματιδίων. Αλλάζει τη ζήτηση ροής, όχι το '
                                                         'ονομαστικό CADR ή τη μετρημένη απόδοση φίλτρου.',
                                                   'en': 'Highest target speed for a supported purifier fan '
                                                         'already on when particle demand is present. It '
                                                         'changes airflow demand, not the purifier’s rated '
                                                         'CADR or measured filtration efficiency.'},
 'area_climate_operating_sleep_active': {'de': 'Kennzeichnet manuell aktuellen Schlaf für automatische '
                                               'Schlafprofile und konfigurierte Ruhe-/Pausenregeln. Aus '
                                               'erzwingt kein Wachsein: Zeitplan oder gewählte '
                                               'Schlafraumquelle können weiterhin Schlaf melden. Explizite '
                                               'Profile und bestätigte Abwesenheit behalten Vorrang.',
                                         'el': 'Δηλώνει χειροκίνητα ύπνο τώρα για αυτόματο προφίλ Ύπνου και '
                                               'ρυθμισμένη ήσυχη λειτουργία ή παύση. Το Off δεν επιβάλλει '
                                               'εγρήγορση: ωράριο ή επιλεγμένη πηγή ύπνου μπορεί ακόμη να '
                                               'δηλώνει ύπνο. Ρητά προφίλ και επιβεβαιωμένη Απουσία '
                                               'υπερισχύουν.',
                                         'en': 'Manually marks this room as sleeping now for automatic '
                                               'sleep/profile and configured quiet or pause behavior. Off '
                                               'does not force awake: an enabled schedule or selected '
                                               'sleeping-room source can still indicate sleep. Explicit '
                                               'profile overrides and verified Away keep their precedence.'},
 'area_climate_operating_sleep_schedule_enabled': {'de': 'Verwendet Beginn und Ende des Raumschlafzeitplans '
                                                         'in der lokalen Home-Assistant-Zeitzone als '
                                                         'Schlafnachweis. Vorgabe 22:00–07:00. Manuelle '
                                                         'Angabe und Schlafraumquelle wirken zusätzlich; die '
                                                         'statische Lärmraum-Einstufung bleibt unverändert.',
                                                   'el': 'Χρησιμοποιεί ώρες έναρξης/λήξης ύπνου στην τοπική '
                                                         'ζώνη ώρας Home Assistant ως ένδειξη τρέχοντος '
                                                         'ύπνου. Προεπιλογή 22:00–07:00. Συνυπολογίζονται η '
                                                         'χειροκίνητη ένδειξη και η πηγή χώρων ύπνου· δεν '
                                                         'αλλάζει η ταξινόμηση χώρου για θόρυβο.',
                                                   'en': 'Uses the room sleep start/end times in the Home '
                                                         'Assistant local time zone as sleeping-now '
                                                         'evidence. The default interval is 22:00–07:00. '
                                                         'Manual sleep and the selected sleeping-room source '
                                                         'also contribute; enabling a schedule does not '
                                                         'change the static noise-room classification.'},
 'area_climate_operating_unoccupied_delay_minutes': {'de': 'Verzögerung für durchgehend gemeldete '
                                                           'Abwesenheit lokaler Raumanwesenheitssensoren '
                                                           'vor einem automatischen Raumprofilwechsel. '
                                                           'Eine gültige gemeinsame Liste belegter '
                                                           'Räume, die diesen Raum auslässt, oder '
                                                           'bestätigte Abwesenheit im gesamten Zuhause '
                                                           'gilt sofort und umgeht diese Verzögerung.',
                                                     'el': 'Καθυστέρηση για συνεχή ένδειξη απουσίας από '
                                                           'τοπικούς αισθητήρες παρουσίας πριν αλλάξουν '
                                                           'τα αυτόματα προφίλ χώρου. Έγκυρη κοινή λίστα '
                                                           'κατειλημμένων δωματίων που δεν περιλαμβάνει '
                                                           'αυτόν τον χώρο, ή επιβεβαιωμένη απουσία από '
                                                           'ολόκληρο το σπίτι, εφαρμόζεται αμέσως χωρίς '
                                                           'αυτή την καθυστέρηση.',
                                                     'en': 'Delay applied to continuous absence reported '
                                                           'by local room-presence sensors before '
                                                           'changing automatic room profiles. A valid '
                                                           'shared occupied-room list that omits this '
                                                           'room, or verified whole-home Away, applies '
                                                           'immediately and bypasses this delay.'},
 'area_climate_operating_window_efficiency_notify': {'de': 'Erlaubt Hinweise zum Öffnen geschlossener '
                                                           'Fenster, wenn bestätigte Außenbedingungen '
                                                           'aktives Heizen, Kühlen oder Entfeuchten '
                                                           'unterstützen könnten. Reiner Hinweis; keine '
                                                           'Fenster- oder Geräteschaltung.',
                                                     'el': 'Επιτρέπει προτάσεις ανοίγματος κλειστού '
                                                           'παραθύρου όταν επιβεβαιωμένες εξωτερικές '
                                                           'συνθήκες μπορούν να βοηθήσουν αντί ενεργής '
                                                           'θέρμανσης, ψύξης ή αφύγρανσης. Είναι '
                                                           'συμβουλευτική ειδοποίηση· δεν κινεί παράθυρα ή '
                                                           'συσκευές.',
                                                     'en': 'Allows suggestions to open a closed window when '
                                                           'verified outdoor conditions could help replace '
                                                           'active heating, cooling or dehumidification. '
                                                           'This is an advisory notification; it does not '
                                                           'open the window or switch appliances.'},
 'area_climate_policy_away_policy': {'de': 'Eine bestätigte Person zu Hause hält das Zuhause immer auf '
                                           'anwesend. Alle zu Hause bleibt für bestehende Konfigurationen '
                                           'erhalten und verwendet dieselbe Regel. Abwesenheit muss '
                                           'bestätigt sein; ein unbekannter Tracker beweist nicht, dass alle '
                                           'gegangen sind.',
                                     'el': 'Επιβεβαιωμένο άτομο στο σπίτι διατηρεί πάντα την κατάσταση '
                                           'παρουσίας. Η επιλογή «Όλοι στο σπίτι» διατηρείται για παλαιές '
                                           'ρυθμίσεις και χρησιμοποιεί τον ίδιο κανόνα. Απαιτείται '
                                           'επιβεβαιωμένη απουσία· άγνωστος ανιχνευτής δεν αποδεικνύει ότι '
                                           'έφυγαν όλοι.',
                                     'en': 'A verified person at home always keeps the home occupied. All '
                                           'home is retained for existing configurations and uses this same '
                                           'rule. Away requires verified absence; an unknown selected '
                                           'tracker cannot prove everyone has left.'},
 'area_climate_policy_target_source': {'de': 'Wählt feste Profiltemperaturen, automatische Anpassung nach '
                                             'Temperatur/Luftfeuchte oder qualifizierte PMV-Anpassung. PMV '
                                             'benötigt vollständige gültige Eingaben. Maximale Anpassung und '
                                             'Gerätegrenzen gelten weiterhin.',
                                       'el': 'Επιλέγει σταθερές θερμοκρασίες προφίλ, αυτόματη προσαρμογή '
                                             'άνεσης από θερμοκρασία/υγρασία ή κατάλληλη εκτίμηση PMV. Το '
                                             'PMV χρειάζεται πλήρη έγκυρα δεδομένα. Ισχύουν μέγιστη '
                                             'προσαρμογή και όρια συσκευών.',
                                       'en': 'Selects fixed profile temperatures, automatic '
                                             'temperature/humidity comfort adjustment, or qualified '
                                             'PMV-based adjustment. Advanced PMV requires complete valid '
                                             'inputs. All methods respect the configured maximum adjustment '
                                             'and device limits.'},
 'area_climate_policy_unknown_occupancy': {'de': 'Ältere Raumprofil-Ersatzregel ohne konfigurierte '
                                                 'gemeinsame Anwesenheit: Belegt-Annahme setzt Belegung '
                                                 'voraus; Aussetzen lässt das Profil unbekannt. Mit '
                                                 'gemeinsamer Anwesenheit bleiben unbekannte Nachweise '
                                                 'unbekannt. Einheitliche Regler nutzen dann Home, '
                                                 'sofern Away, Sleep oder ein explizites Profil nicht '
                                                 'vorrangig ist; gerätespezifische '
                                                 'Belegt-/Leer-Anforderungen benötigen weiterhin '
                                                 'bestätigte Nachweise.',
                                           'el': 'Παλαιός κανόνας εφεδρικού προφίλ όταν δεν έχει '
                                                 'ρυθμιστεί κοινή παρουσία: η θεώρηση ως κατειλημμένου '
                                                 'υποκαθιστά ένδειξη παρουσίας, ενώ η αναμονή αφήνει το '
                                                 'προφίλ άγνωστο. Με κοινή παρουσία, άγνωστα στοιχεία '
                                                 'παραμένουν άγνωστα. Οι ενιαίοι ελεγκτές χρησιμοποιούν '
                                                 'το προφίλ Σπίτι για άγνωστη παρουσία χώρου, εκτός αν '
                                                 'προηγείται Απουσία, Ύπνος ή ρητό προφίλ· οι απαιτήσεις '
                                                 'παρουσίας/απουσίας κάθε συσκευής εξακολουθούν να '
                                                 'χρειάζονται επιβεβαιωμένα στοιχεία.',
                                           'en': 'Legacy room-profile fallback when shared presence is '
                                                 'not configured: assume occupied substitutes occupied '
                                                 'evidence; hold leaves the profile unknown. With shared '
                                                 'presence, unknown evidence stays unknown. Unified '
                                                 'controllers use Home for unknown room occupancy unless '
                                                 'Away, Sleep or an explicit preset takes priority, and '
                                                 'device-specific occupied/absent requirements still '
                                                 'need verified evidence.'},
 'area_climate_profile_away_cool': {'de': 'Raumsollwert für Kühltemperatur (°C) bei aktivem Profil Abwesend. '
                                          'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                          'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                    'el': 'Στόχος χώρου για θερμοκρασία ψύξης (°C) όταν είναι ενεργό το '
                                          'προφίλ Απουσία. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                          'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                    'en': 'Room cooling temperature target (°C) while the Away profile is '
                                          'active. This saved target is applied within the room/device '
                                          'limits by permitted controllers; editing it does not grant '
                                          'control permission.'},
 'area_climate_profile_away_heat': {'de': 'Raumsollwert für Heiztemperatur (°C) bei aktivem Profil Abwesend. '
                                          'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                          'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                    'el': 'Στόχος χώρου για θερμοκρασία θέρμανσης (°C) όταν είναι ενεργό το '
                                          'προφίλ Απουσία. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                          'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                    'en': 'Room heating temperature target (°C) while the Away profile is '
                                          'active. This saved target is applied within the room/device '
                                          'limits by permitted controllers; editing it does not grant '
                                          'control permission.'},
 'area_climate_profile_away_humidity': {'de': 'Raumsollwert für relative Luftfeuchte (%) bei aktivem Profil '
                                              'Abwesend. Freigegebene Regler wenden ihn innerhalb der '
                                              'Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                              'Steuerfreigabe.',
                                        'el': 'Στόχος χώρου για σχετική υγρασία (%) όταν είναι ενεργό το '
                                              'προφίλ Απουσία. Εφαρμόζεται εντός ορίων χώρου/συσκευής από '
                                              'ήδη εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια '
                                              'ελέγχου.',
                                        'en': 'Room relative humidity target (%) while the Away profile is '
                                              'active. This saved target is applied within the room/device '
                                              'limits by permitted controllers; editing it does not grant '
                                              'control permission.'},
 'area_climate_profile_comfort_cool': {'de': 'Raumsollwert für Kühltemperatur (°C) bei aktivem Profil '
                                             'Komfort (Raum belegt). Freigegebene Regler wenden ihn '
                                             'innerhalb der Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                             'Steuerfreigabe.',
                                       'el': 'Στόχος χώρου για θερμοκρασία ψύξης (°C) όταν είναι ενεργό το '
                                             'προφίλ Άνεση (κατειλημμένος χώρος). Εφαρμόζεται εντός ορίων '
                                             'χώρου/συσκευής από ήδη εξουσιοδοτημένους ελεγκτές· η αλλαγή '
                                             'δεν χορηγεί άδεια ελέγχου.',
                                       'en': 'Room cooling temperature target (°C) while the Comfort (room '
                                             'occupied) profile is active. This saved target is applied '
                                             'within the room/device limits by permitted controllers; '
                                             'editing it does not grant control permission.'},
 'area_climate_profile_comfort_heat': {'de': 'Raumsollwert für Heiztemperatur (°C) bei aktivem Profil '
                                             'Komfort (Raum belegt). Freigegebene Regler wenden ihn '
                                             'innerhalb der Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                             'Steuerfreigabe.',
                                       'el': 'Στόχος χώρου για θερμοκρασία θέρμανσης (°C) όταν είναι ενεργό '
                                             'το προφίλ Άνεση (κατειλημμένος χώρος). Εφαρμόζεται εντός ορίων '
                                             'χώρου/συσκευής από ήδη εξουσιοδοτημένους ελεγκτές· η αλλαγή '
                                             'δεν χορηγεί άδεια ελέγχου.',
                                       'en': 'Room heating temperature target (°C) while the Comfort (room '
                                             'occupied) profile is active. This saved target is applied '
                                             'within the room/device limits by permitted controllers; '
                                             'editing it does not grant control permission.'},
 'area_climate_profile_comfort_humidity': {'de': 'Raumsollwert für relative Luftfeuchte (%) bei aktivem '
                                                 'Profil Komfort (Raum belegt). Freigegebene Regler wenden '
                                                 'ihn innerhalb der Raum-/Gerätegrenzen an; Bearbeiten '
                                                 'erteilt keine Steuerfreigabe.',
                                           'el': 'Στόχος χώρου για σχετική υγρασία (%) όταν είναι ενεργό το '
                                                 'προφίλ Άνεση (κατειλημμένος χώρος). Εφαρμόζεται εντός '
                                                 'ορίων χώρου/συσκευής από ήδη εξουσιοδοτημένους ελεγκτές· η '
                                                 'αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                           'en': 'Room relative humidity target (%) while the Comfort (room '
                                                 'occupied) profile is active. This saved target is applied '
                                                 'within the room/device limits by permitted controllers; '
                                                 'editing it does not grant control permission.'},
 'area_climate_profile_eco_cool': {'de': 'Raumsollwert für Kühltemperatur (°C) bei aktivem Profil Eco. '
                                         'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                         'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                   'el': 'Στόχος χώρου για θερμοκρασία ψύξης (°C) όταν είναι ενεργό το '
                                         'προφίλ Eco. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                         'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                   'en': 'Room cooling temperature target (°C) while the Eco profile is '
                                         'active. This saved target is applied within the room/device limits '
                                         'by permitted controllers; editing it does not grant control '
                                         'permission.'},
 'area_climate_profile_eco_heat': {'de': 'Raumsollwert für Heiztemperatur (°C) bei aktivem Profil Eco. '
                                         'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                         'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                   'el': 'Στόχος χώρου για θερμοκρασία θέρμανσης (°C) όταν είναι ενεργό το '
                                         'προφίλ Eco. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                         'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                   'en': 'Room heating temperature target (°C) while the Eco profile is '
                                         'active. This saved target is applied within the room/device limits '
                                         'by permitted controllers; editing it does not grant control '
                                         'permission.'},
 'area_climate_profile_eco_humidity': {'de': 'Raumsollwert für relative Luftfeuchte (%) bei aktivem Profil '
                                             'Eco. Freigegebene Regler wenden ihn innerhalb der '
                                             'Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                             'Steuerfreigabe.',
                                       'el': 'Στόχος χώρου για σχετική υγρασία (%) όταν είναι ενεργό το '
                                             'προφίλ Eco. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                             'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια '
                                             'ελέγχου.',
                                       'en': 'Room relative humidity target (%) while the Eco profile is '
                                             'active. This saved target is applied within the room/device '
                                             'limits by permitted controllers; editing it does not grant '
                                             'control permission.'},
 'area_climate_profile_home_cool': {'de': 'Raumsollwert für Kühltemperatur (°C) bei aktivem Profil Zu Hause. '
                                          'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                          'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                    'el': 'Στόχος χώρου για θερμοκρασία ψύξης (°C) όταν είναι ενεργό το '
                                          'προφίλ Σπίτι. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                          'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                    'en': 'Room cooling temperature target (°C) while the Home profile is '
                                          'active. This saved target is applied within the room/device '
                                          'limits by permitted controllers; editing it does not grant '
                                          'control permission.'},
 'area_climate_profile_home_heat': {'de': 'Raumsollwert für Heiztemperatur (°C) bei aktivem Profil Zu Hause. '
                                          'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                          'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                    'el': 'Στόχος χώρου για θερμοκρασία θέρμανσης (°C) όταν είναι ενεργό το '
                                          'προφίλ Σπίτι. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                          'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                    'en': 'Room heating temperature target (°C) while the Home profile is '
                                          'active. This saved target is applied within the room/device '
                                          'limits by permitted controllers; editing it does not grant '
                                          'control permission.'},
 'area_climate_profile_home_humidity': {'de': 'Raumsollwert für relative Luftfeuchte (%) bei aktivem Profil '
                                              'Zu Hause. Freigegebene Regler wenden ihn innerhalb der '
                                              'Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                              'Steuerfreigabe.',
                                        'el': 'Στόχος χώρου για σχετική υγρασία (%) όταν είναι ενεργό το '
                                              'προφίλ Σπίτι. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                              'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια '
                                              'ελέγχου.',
                                        'en': 'Room relative humidity target (%) while the Home profile is '
                                              'active. This saved target is applied within the room/device '
                                              'limits by permitted controllers; editing it does not grant '
                                              'control permission.'},
 'area_climate_profile_sleep_cool': {'de': 'Raumsollwert für Kühltemperatur (°C) bei aktivem Profil Schlaf. '
                                           'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                           'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                     'el': 'Στόχος χώρου για θερμοκρασία ψύξης (°C) όταν είναι ενεργό το '
                                           'προφίλ Ύπνος. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                           'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                     'en': 'Room cooling temperature target (°C) while the Sleep profile is '
                                           'active. This saved target is applied within the room/device '
                                           'limits by permitted controllers; editing it does not grant '
                                           'control permission.'},
 'area_climate_profile_sleep_heat': {'de': 'Raumsollwert für Heiztemperatur (°C) bei aktivem Profil Schlaf. '
                                           'Freigegebene Regler wenden ihn innerhalb der Raum-/Gerätegrenzen '
                                           'an; Bearbeiten erteilt keine Steuerfreigabe.',
                                     'el': 'Στόχος χώρου για θερμοκρασία θέρμανσης (°C) όταν είναι ενεργό το '
                                           'προφίλ Ύπνος. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                           'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια ελέγχου.',
                                     'en': 'Room heating temperature target (°C) while the Sleep profile is '
                                           'active. This saved target is applied within the room/device '
                                           'limits by permitted controllers; editing it does not grant '
                                           'control permission.'},
 'area_climate_profile_sleep_humidity': {'de': 'Raumsollwert für relative Luftfeuchte (%) bei aktivem Profil '
                                               'Schlaf. Freigegebene Regler wenden ihn innerhalb der '
                                               'Raum-/Gerätegrenzen an; Bearbeiten erteilt keine '
                                               'Steuerfreigabe.',
                                         'el': 'Στόχος χώρου για σχετική υγρασία (%) όταν είναι ενεργό το '
                                               'προφίλ Ύπνος. Εφαρμόζεται εντός ορίων χώρου/συσκευής από ήδη '
                                               'εξουσιοδοτημένους ελεγκτές· η αλλαγή δεν χορηγεί άδεια '
                                               'ελέγχου.',
                                         'en': 'Room relative humidity target (%) while the Sleep profile is '
                                               'active. This saved target is applied within the room/device '
                                               'limits by permitted controllers; editing it does not grant '
                                               'control permission.'},
 'area_climate_sleep_end': {'de': 'Lokale Endzeit des Schlafintervalls, wirksam nur bei aktiviertem '
                                  'Zeitplan. Das Ende hebt Schlafmeldungen des manuellen Schalters oder '
                                  'einer anderen gewählten Quelle nicht auf.',
                            'el': 'Τοπική ώρα λήξης του διαστήματος ύπνου, μόνο με ενεργή «Χρήση ωραρίου». Η '
                                  'λήξη δεν αναιρεί ύπνο που δηλώνεται από τον χειροκίνητο διακόπτη ή άλλη '
                                  'επιλεγμένη πηγή.',
                            'en': 'Local end time of this room’s sleep interval. It contributes only when '
                                  'Use schedule is enabled. Reaching the end does not cancel sleep indicated '
                                  'by the manual switch or another selected sleep source.'},
 'area_climate_sleep_start': {'de': 'Lokale Beginnzeit des Schlafintervalls. Sie trägt nur bei aktiviertem '
                                    'Zeitplan zum Schlafnachweis bei. Das Intervall kann über Mitternacht '
                                    'reichen, etwa 22:00–07:00.',
                              'el': 'Τοπική ώρα έναρξης του διαστήματος ύπνου. Χρησιμοποιείται μόνο όταν '
                                    'είναι ενεργή η «Χρήση ωραρίου». Το διάστημα μπορεί να περνά τα '
                                    'μεσάνυχτα, π.χ. 22:00–07:00.',
                              'en': 'Local start time of this room’s sleep interval. It contributes to '
                                    'sleeping-now evidence only when Use schedule is enabled. An interval '
                                    'may cross midnight, such as 22:00–07:00.'},
 'area_device_target_fan_speed_percent': {'de': 'Gewünschte Drehzahl für die konfigurierte Abluft- oder '
                                                'Filterrolle des gewählten Ventilators. Die vorhandene '
                                                'Strategie wendet Grenzen und Prüfungen an; Bearbeiten gibt '
                                                'keinen zuvor gesperrten Regler frei.',
                                          'el': 'Επιθυμητή ταχύτητα για τον ρυθμισμένο ρόλο εξαερισμού ή '
                                                'φίλτρανσης του επιλεγμένου ανεμιστήρα. Η υπάρχουσα '
                                                'στρατηγική εφαρμόζει όρια και ελέγχους· η αλλαγή δεν '
                                                'εξουσιοδοτεί απενεργοποιημένο ελεγκτή.',
                                          'en': 'Requested speed for the selected fan’s configured '
                                                'extraction or filtration role. The existing native-fan '
                                                'strategy applies its limits and eligibility checks; editing '
                                                'this value does not authorize a previously disabled '
                                                'controller.'},
 'area_direct_tuning_kd': {'de': 'Differentialverstärkung: Korrektur anhand der Temperaturänderungsrate. '
                                 'Kann dämpfen, verstärkt aber Messrauschen; null deaktiviert diesen Anteil.',
                           'el': 'Διαφορικό κέρδος: διόρθωση βάσει του ρυθμού αλλαγής θερμοκρασίας. Μπορεί '
                                 'να αποσβένει την απόκριση αλλά ενισχύει θορυβώδεις μετρήσεις· το μηδέν '
                                 'απενεργοποιεί τη συνιστώσα.',
                           'en': 'Derivative gain: correction based on how quickly temperature changes. It '
                                 'can damp a response but amplifies noisy measurements; zero disables the '
                                 'derivative contribution.'},
 'area_direct_tuning_ki': {'de': 'Integralverstärkung: über die Zeit angesammelte Fehlerkorrektur. Gegen '
                                 'bleibende Abweichung; hohe Werte können Überschwingen verursachen. Es '
                                 'gelten die angezeigten Zeiteinheiten.',
                           'el': 'Ολοκληρωτικό κέρδος: συσσωρευμένη διόρθωση από το σφάλμα θερμοκρασίας στον '
                                 'χρόνο. Αντιμετωπίζει μόνιμη απόκλιση· υψηλές τιμές μπορεί να προκαλέσουν '
                                 'υπερύψωση. Ισχύουν οι εμφανιζόμενες μονάδες.',
                           'en': 'Integral gain: correction accumulated from temperature error over time. It '
                                 'addresses persistent offset; high values can cause overshoot. Time units '
                                 'follow the displayed gain unit.'},
 'area_direct_tuning_kp': {'de': 'Proportionalverstärkung: unmittelbare Korrektur je Grad '
                                 'Temperaturabweichung. Höhere Werte reagieren stärker. Gilt entsprechend '
                                 'der gewählten PID-Verstärkungsquelle.',
                           'el': 'Αναλογικό κέρδος: άμεση διόρθωση ανά βαθμό σφάλματος θερμοκρασίας. '
                                 'Υψηλότερες τιμές αντιδρούν εντονότερα. Χρησιμοποιείται σύμφωνα με την '
                                 'επιλεγμένη πηγή κερδών PID.',
                           'en': 'Proportional gain: immediate correction per degree of temperature error. '
                                 'Higher values react more strongly to the current error. Used with the '
                                 'selected PID gain source.'},
 'area_direct_tuning_max_demand_change': {'de': 'Größte Ausgangsänderung in Prozentpunkten je direktem '
                                                'Proportionalzyklus. Begrenzt abrupte Bedarfsänderungen, '
                                                'nicht den maximalen Gesamtausgang.',
                                          'el': 'Μέγιστη αλλαγή εξόδου σε ποσοστιαίες μονάδες ανά κύκλο '
                                                'άμεσου αναλογικού ελέγχου. Περιορίζει απότομες αλλαγές '
                                                'ζήτησης· δεν είναι μέγιστη συνολική έξοδος.',
                                          'en': 'Largest output change in percentage points per direct '
                                                'proportional-control cycle. It limits abrupt demand '
                                                'changes; it does not set the maximum total output.'},
 'area_direct_tuning_min_demand_change': {'de': 'Kleinste Ausgangsänderung in Prozentpunkten, die an einen '
                                                'direkten Proportionalaktor gesendet wird. Kleinere '
                                                'Änderungen werden zur Befehlsreduzierung ignoriert.',
                                          'el': 'Μικρότερη αλλαγή εξόδου σε ποσοστιαίες μονάδες που '
                                                'στέλνεται σε άμεσο αναλογικό ενεργοποιητή. Μικρότερες '
                                                'προτάσεις αγνοούνται για μείωση περιττών εντολών.',
                                          'en': 'Smallest output change in percentage points sent to a '
                                                'direct proportional actuator. Smaller proposed changes are '
                                                'ignored to reduce needless commands.'},
 'area_direct_tuning_sample_seconds': {'de': 'Mindestabstand in Sekunden zwischen PID-Regelberechnungen. '
                                             'Steuert die Rechenfolge, nicht das Meldeintervall des '
                                             'Temperatursensors.',
                                       'el': 'Ελάχιστο διάστημα σε δευτερόλεπτα μεταξύ υπολογισμών PID. '
                                             'Ρυθμίζει τη συχνότητα υπολογισμού, όχι τη συχνότητα αναφορών '
                                             'του αισθητήρα θερμοκρασίας.',
                                       'en': 'Minimum interval in seconds between PID control calculations. '
                                             'It governs calculation cadence, not the reporting interval of '
                                             'the physical temperature sensor.'},
 'area_manual_profile': {'de': 'Überschreibt das automatisch gewählte Raumklimaprofil. Automatik kehrt zur '
                               'Auswahl nach Anwesenheit/Schlaf zurück; die übrigen Profile verwenden ihre '
                               'jeweiligen Sollwerte. Die Auswahl erteilt keine Gerätefreigabe.',
                         'el': 'Παρακάμπτει την αυτόματη επιλογή κλιματικού προφίλ χώρου. Το Αυτόματο '
                               'επαναφέρει επιλογή με βάση παρουσία/ύπνο· τα άλλα προφίλ χρησιμοποιούν τους '
                               'δικούς τους στόχους. Η επιλογή δεν χορηγεί άδεια ελέγχου συσκευών.',
                         'en': 'Overrides the automatically selected climate profile for this room. '
                               'Automatic resumes presence/sleep-based selection; Comfort, Home, Away, Sleep '
                               'or Eco use their configured targets. A profile selection does not grant '
                               'device-control permission.'},
 'area_mold_surface_critical_temperature_c': {'de': 'Ihre gemessene Temperatur der repräsentativen kältesten '
                                                    'Raumoberfläche in °C. Speichern versucht den '
                                                    'Schimmelkalibrierungsfaktor mit aktuellen gewählten '
                                                    'Innen-/Außentemperaturen neu zu berechnen. Praktisch '
                                                    'nach eingependeltem Heizen und mindestens 10°C wärmer '
                                                    'innen messen; HEM prüft die Stabilität nicht.',
                                              'el': 'Η μετρημένη θερμοκρασία αντιπροσωπευτικής ψυχρότερης '
                                                    'επιφάνειας του χώρου σε °C. Η αποθήκευση επιχειρεί '
                                                    'επανυπολογισμό συντελεστή μούχλας με τρέχουσες '
                                                    'επιλεγμένες θερμοκρασίες. Πρακτικά μέτρησε μετά από '
                                                    'σταθερή θέρμανση, με μέσα τουλάχιστον 10°C θερμότερο· η '
                                                    'σταθερότητα δεν επαληθεύεται από HEM.',
                                              'en': 'Your measured temperature of this room’s coldest '
                                                    'representative surface, in °C. Saving it attempts to '
                                                    'recalculate the mold calibration factor using current '
                                                    'selected room/outdoor temperatures. Measure after '
                                                    'settled heating with at least 10°C warmer indoors as '
                                                    'practical guidance; HEM does not verify stability.'},
 'area_pid_gain_source': {'de': 'Wählt die Raum-PID-Verstärkungen: Standard nutzt die Integrationsvorgaben; '
                                'Manuell die bearbeiteten Kp-, Ki- und Kd-Werte. Andere PID-Grenzen gelten '
                                'weiterhin.',
                          'el': 'Επιλέγει κέρδη PID επόπτη χώρου: Προεπιλογές χρησιμοποιεί τα αρχικά κέρδη, '
                                'Χειροκίνητα τα επεξεργασμένα Kp, Ki, Kd του χώρου. Τα υπόλοιπα όρια PID '
                                'εξακολουθούν να ισχύουν.',
                          'en': 'Chooses the PID gains used by the room supervisor: Defaults uses the '
                                'integration’s default gains; Manual uses the room’s edited Kp, Ki and Kd. '
                                'Other PID limits remain in effect.'},
 'area_pid_kd': {'de': 'Differentialverstärkung: Korrektur anhand der Temperaturänderungsrate. Kann dämpfen, '
                       'verstärkt aber Messrauschen; null deaktiviert diesen Anteil.',
                 'el': 'Διαφορικό κέρδος: διόρθωση βάσει του ρυθμού αλλαγής θερμοκρασίας. Μπορεί να '
                       'αποσβένει την απόκριση αλλά ενισχύει θορυβώδεις μετρήσεις· το μηδέν απενεργοποιεί τη '
                       'συνιστώσα.',
                 'en': 'Derivative gain: correction based on how quickly temperature changes. It can damp a '
                       'response but amplifies noisy measurements; zero disables the derivative '
                       'contribution.'},
 'area_pid_ki': {'de': 'Integralverstärkung: über die Zeit angesammelte Fehlerkorrektur. Gegen bleibende '
                       'Abweichung; hohe Werte können Überschwingen verursachen. Es gelten die angezeigten '
                       'Zeiteinheiten.',
                 'el': 'Ολοκληρωτικό κέρδος: συσσωρευμένη διόρθωση από το σφάλμα θερμοκρασίας στον χρόνο. '
                       'Αντιμετωπίζει μόνιμη απόκλιση· υψηλές τιμές μπορεί να προκαλέσουν υπερύψωση. Ισχύουν '
                       'οι εμφανιζόμενες μονάδες.',
                 'en': 'Integral gain: correction accumulated from temperature error over time. It addresses '
                       'persistent offset; high values can cause overshoot. Time units follow the displayed '
                       'gain unit.'},
 'area_pid_kp': {'de': 'Proportionalverstärkung: unmittelbare Korrektur je Grad Temperaturabweichung. Höhere '
                       'Werte reagieren stärker. Gilt entsprechend der gewählten PID-Verstärkungsquelle.',
                 'el': 'Αναλογικό κέρδος: άμεση διόρθωση ανά βαθμό σφάλματος θερμοκρασίας. Υψηλότερες τιμές '
                       'αντιδρούν εντονότερα. Χρησιμοποιείται σύμφωνα με την επιλεγμένη πηγή κερδών PID.',
                 'en': 'Proportional gain: immediate correction per degree of temperature error. Higher '
                       'values react more strongly to the current error. Used with the selected PID gain '
                       'source.'},
 'area_pid_max_change_c': {'de': 'Größte Thermostatsollwertänderung pro PID-Zyklus. Begrenzt abrupte '
                                 'Änderungen auch bei großer Temperaturabweichung.',
                           'el': 'Μέγιστη αλλαγή στόχου θερμοστάτη σε έναν κύκλο PID. Περιορίζει απότομες '
                                 'αλλαγές ακόμη και με μεγάλο σφάλμα θερμοκρασίας.',
                           'en': 'Largest thermostat-setpoint change allowed in one PID cycle. Limits how '
                                 'abruptly the supervisor can move the setpoint even when the temperature '
                                 'error is large.'},
 'area_pid_max_setpoint_c': {'de': 'Höchster Thermostatsollwert, den der Raum-PID senden darf. Ausgangswerte '
                                   'werden daran und an den Gerätefähigkeiten begrenzt.',
                             'el': 'Μέγιστος στόχος θερμοστάτη που επιτρέπεται να στείλει ο PID. Οι στόχοι '
                                   'περιορίζονται από αυτό το όριο και τα υποστηριζόμενα όρια της συσκευής.',
                             'en': 'Highest thermostat setpoint the room PID supervisor may send. Its '
                                   'generated setpoints are clamped to this upper bound and the native '
                                   'device’s supported limits.'},
 'area_pid_min_change_c': {'de': 'Kleinste sinnvolle Thermostatsollwertänderung. Kleinere Differenzen werden '
                                 'übersprungen, um unnötige Befehle und Quantisierungsrauschen zu vermeiden.',
                           'el': 'Μικρότερη προτεινόμενη αλλαγή στόχου που αξίζει να σταλεί. Μικρότερες '
                                 'διαφορές παραλείπονται για αποφυγή περιττών εντολών.',
                           'en': 'Smallest proposed thermostat-setpoint change worth sending. Smaller '
                                 'differences are skipped to avoid unnecessary commands and device '
                                 'quantization noise.'},
 'area_pid_min_setpoint_c': {'de': 'Niedrigster Thermostatsollwert, den der Raum-PID senden darf. '
                                   'Ausgangswerte werden daran und an den Gerätefähigkeiten begrenzt.',
                             'el': 'Ελάχιστος στόχος θερμοστάτη που επιτρέπεται να στείλει ο PID. Οι στόχοι '
                                   'περιορίζονται από αυτό το όριο και τα υποστηριζόμενα όρια της συσκευής.',
                             'en': 'Lowest thermostat setpoint the room PID supervisor may send. Its '
                                   'generated setpoints are clamped to this lower bound and the native '
                                   'device’s supported limits.'},
 'area_pid_offset_c': {'de': 'Maximale Thermostatsollwert-Korrektur des PID gegenüber seiner Basis. Begrenzt '
                             'den Einfluss in °C, ohne die gewünschte Raumtemperatur zu ändern.',
                       'el': 'Μέγιστη διόρθωση στόχου θερμοστάτη από τον PID σε σχέση με τη βάση του. '
                             'Περιορίζει την επίδραση σε °C χωρίς να αλλάζει την επιθυμητή θερμοκρασία '
                             'χώρου.',
                       'en': 'Maximum thermostat-setpoint trim the PID supervisor may apply relative to its '
                             'baseline. Limits PID influence in °C without changing the room’s desired '
                             'temperature.'},
 'area_pid_sample_seconds': {'de': 'Mindestabstand in Sekunden zwischen PID-Regelberechnungen. Steuert die '
                                   'Rechenfolge, nicht das Meldeintervall des Temperatursensors.',
                             'el': 'Ελάχιστο διάστημα σε δευτερόλεπτα μεταξύ υπολογισμών PID. Ρυθμίζει τη '
                                   'συχνότητα υπολογισμού, όχι τη συχνότητα αναφορών του αισθητήρα '
                                   'θερμοκρασίας.',
                             'en': 'Minimum interval in seconds between PID control calculations. It governs '
                                   'calculation cadence, not the reporting interval of the physical '
                                   'temperature sensor.'},
 'area_pid_target_c': {'de': 'Gewünschte Raumtemperatur für den Raum-PID. Sein Ausgang korrigiert den '
                             'erlaubten Thermostatsollwert; keine aktuelle Thermostatmessung.',
                       'el': 'Επιθυμητή θερμοκρασία χώρου για τον επόπτη PID. Η έξοδος διορθώνει τον '
                             'επιτρεπόμενο στόχο θερμοστάτη· δεν είναι η τρέχουσα μέτρηση του θερμοστάτη.',
                       'en': 'Desired room temperature used by the room PID supervisor. Its output trims the '
                             'permitted thermostat setpoint; this is not the native thermostat’s current '
                             'reading.'},
 'area_recalculate_mold': {'de': 'Berechnet und speichert den SCHIMMEL-KALIBRIERUNGSFAKTOR aus der '
                                 'gespeicherten kalten Oberflächentemperatur und aktuellen gewählten '
                                 'Innen-/Außenwerten. Misst die Oberfläche nicht neu. Die Differenz ≥10°C '
                                 'ist Messhinweis, keine neue Gültigkeitsregel; thermische Stabilität wird '
                                 'nicht geprüft.',
                           'el': 'Επανυπολογίζει και αποθηκεύει τον ΣΥΝΤΕΛΕΣΤΗ ΒΑΘΜΟΝΟΜΗΣΗΣ ΜΟΥΧΛΑΣ από την '
                                 'αποθηκευμένη μέτρηση ψυχρής επιφάνειας και τις τρέχουσες επιλεγμένες '
                                 'εσωτερικές/εξωτερικές θερμοκρασίες. Δεν ξαναμετρά την επιφάνεια. Η διαφορά '
                                 '≥10°C είναι πρακτική οδηγία, όχι νέος κανόνας εγκυρότητας· η θερμική '
                                 'σταθερότητα δεν επαληθεύεται.',
                           'en': 'Recalculates and saves this room’s MOLD CALIBRATION FACTOR using the saved '
                                 'measured cold-surface temperature and current selected indoor/outdoor '
                                 'temperatures. It does not remeasure the surface. The ≥10°C indoor–outdoor '
                                 'difference is measurement guidance, not a new validity rule; thermal '
                                 'stability is not verified.'},
 'area_room_equipment_limit_fan_max_percentage': {'de': 'Alte obere Raumventilatordrehzahlgrenze. Aktuelle '
                                                        'Grenzen gehören zum jeweiligen physischen Regler '
                                                        'und beachten dessen Drehzahlbereich.',
                                                  'el': 'Παλαιό ανώτερο όριο ταχύτητας ανεμιστήρων χώρου. Τα '
                                                        'τρέχοντα όρια ανήκουν στον ελεγκτή κάθε φυσικής '
                                                        'συσκευής και τηρούν τις δυνατότητές της.',
                                                  'en': 'Legacy room fan-speed upper bound. Current fan '
                                                        'limits belong to each physical controller and '
                                                        'respect its native speed range.'},
 'area_room_equipment_limit_fan_min_percentage': {'de': 'Alte untere Raumventilatordrehzahlgrenze. Aktuelle '
                                                        'Grenzen gehören zum jeweiligen physischen Regler '
                                                        'und beachten dessen Drehzahlbereich.',
                                                  'el': 'Παλαιό κατώτερο όριο ταχύτητας ανεμιστήρων χώρου. '
                                                        'Τα τρέχοντα όρια ανήκουν στον ελεγκτή κάθε φυσικής '
                                                        'συσκευής και τηρούν τις δυνατότητές της.',
                                                  'en': 'Legacy room fan-speed lower bound. Current fan '
                                                        'limits belong to each physical controller and '
                                                        'respect its native speed range.'},
 'area_room_equipment_limit_humidity_max_limit': {'de': 'Höchster erlaubter Feuchtesollwert (% rF) innerhalb '
                                                        'des Gerätebereichs. Begrenzt Sollwerte, getrennt '
                                                        'von der Entfeuchtungsbedarfsschwelle.',
                                                  'el': 'Μέγιστος επιτρεπτός στόχος υγρασίας (% RH), εντός '
                                                        'δυνατοτήτων συσκευής. Περιορίζει στόχους και '
                                                        'διαφέρει από το όριο ζήτησης αφύγρανσης.',
                                                  'en': 'Highest permitted room humidity target (% RH), '
                                                        'within the supported device range. This bounds '
                                                        'targets and is separate from the dehumidification '
                                                        'demand threshold.'},
 'area_room_equipment_limit_humidity_min_limit': {'de': 'Niedrigster erlaubter Feuchtesollwert (% rF) '
                                                        'innerhalb des Gerätebereichs. Begrenzt Sollwerte, '
                                                        'getrennt von der Befeuchtungsbedarfsschwelle.',
                                                  'el': 'Ελάχιστος επιτρεπτός στόχος υγρασίας (% RH), εντός '
                                                        'δυνατοτήτων συσκευής. Περιορίζει στόχους και '
                                                        'διαφέρει από το όριο ζήτησης ύγρανσης.',
                                                  'en': 'Lowest permitted room humidity target (% RH), '
                                                        'within the supported device range. This bounds '
                                                        'targets and is separate from the humidification '
                                                        'demand threshold.'},
 'area_room_equipment_limit_temperature_max_limit': {'de': 'Höchster erlaubter Raumtemperatursollwert (°C). '
                                                           'Begrenzt Raum-/Profilziele auf unterstützte '
                                                           'Gerätefähigkeiten.',
                                                     'el': 'Μέγιστος επιτρεπτός στόχος θερμοκρασίας (°C). '
                                                           'Περιορίζει στόχους χώρου/προφίλ εντός '
                                                           'δυνατοτήτων συσκευών.',
                                                     'en': 'Highest permitted room temperature target (°C). '
                                                           'Bounds room/profile targets within supported '
                                                           'equipment capabilities.'},
 'area_room_equipment_limit_temperature_min_limit': {'de': 'Niedrigster erlaubter Raumtemperatursollwert '
                                                           '(°C). Begrenzt Raum-/Profilziele auf die '
                                                           'gemeinsam unterstützten Gerätefähigkeiten.',
                                                     'el': 'Ελάχιστος επιτρεπτός στόχος θερμοκρασίας (°C). '
                                                           'Περιορίζει στόχους χώρου/προφίλ εντός κοινών '
                                                           'δυνατοτήτων συσκευών.',
                                                     'en': 'Lowest permitted room temperature target (°C). '
                                                           'Bounds room/profile targets within the '
                                                           'intersection of supported equipment '
                                                           'capabilities.'},
 'area_shading_close_above_c': {'de': 'Vorgabe der Raumtemperaturschwelle zum Beschatten. Jede Beschattung '
                                      'kann eine eigene Schwelle setzen. Zusätzlich sind Sonnenhöhe, '
                                      'gegebenenfalls Lux-Nachweise, Freigaben und geeignete '
                                      'Geräte-/Fensterzustände nötig.',
                                'el': 'Προεπιλεγμένο όριο θερμοκρασίας χώρου για κλείσιμο σκίασης. Κάθε '
                                      'κάλυμμα μπορεί να έχει δικό του όριο. Χρειάζονται επίσης κατάλληλο '
                                      'ύψος ήλιου, τυχόν στοιχεία lux, άδειες και κατάλληλη κατάσταση '
                                      'καλύμματος/παραθύρου.',
                                'en': 'Default room-temperature threshold for solar-shading closure. A cover '
                                      'may override it with its own threshold. Automatic closure '
                                      'additionally requires sufficient sun elevation, applicable lux '
                                      'evidence, permissions and an eligible cover/window state.'},
 'area_shading_enabled': {'de': 'Raumfreigabe für automatische Sonnenbeschattung. Jede ausgewählte '
                                'Beschattung braucht zusätzlich ihre eigene Aktivierung und gültige '
                                'Bewegungsbedingungen. Auswahl allein erlaubt keine Bewegung. HEM öffnet nur '
                                'zuvor selbst geschlossene, weiterhin verwaltete Beschattung nach '
                                'bestandenen Prüfungen.',
                          'el': 'Άδεια αυτόματης ηλιακής σκίασης χώρου. Κάθε επιλεγμένο κάλυμμα χρειάζεται '
                                'και δική του ενεργοποίηση και έγκυρες συνθήκες κίνησης. Η επιλογή μόνο δεν '
                                'επιτρέπει κίνηση. Ανοίγει ξανά μόνο κάλυμμα που έκλεισε το HEM και '
                                'εξακολουθεί να ελέγχει, μετά τους ελέγχους ανοίγματος.',
                          'en': 'Room-level permission for automatic solar shading. Each selected cover also '
                                'needs its own enabled setting and valid movement conditions. Selection '
                                'alone does not grant movement. HEM reopens only a shade it previously '
                                'closed and still owns, when the reopening checks pass.'},
 'area_shading_min_sun_elevation': {'de': 'Mindesthöhe der Sonne über dem Horizont in Grad, bevor '
                                          'automatisch geschlossen werden darf. Eine Prüfung neben '
                                          'Raumtemperatur und gegebenenfalls aktivierter Lux-Anforderung.',
                                    'el': 'Ελάχιστο ύψος ήλιου πάνω από τον ορίζοντα σε μοίρες για να '
                                          'επιτρέπεται αυτόματο κλείσιμο σκίασης. Είναι ένας έλεγχος μαζί με '
                                          'τη θερμοκρασία και την τυχόν ενεργή απαίτηση lux.',
                                    'en': 'Minimum sun elevation above the horizon, in degrees, before '
                                          'automatic solar-shading closure is allowed. It is one eligibility '
                                          'check alongside room temperature and any enabled lux '
                                          'requirement.'},
 'global_environment_pollen_high_from': {'de': 'Erster Wert, der auf der Pollenskala des Anbieters als hoch '
                                               'gilt. Er dient der Einstufung und verhindert bei aktivierter '
                                               'Vermeidung Lüftungsvorschläge. An die tatsächliche '
                                               'Anbieterskala anpassen.',
                                         'el': 'Πρώτη τιμή που θεωρείται υψηλή στην κλίμακα του επιλεγμένου '
                                               'παρόχου γύρης. Ταξινομεί τη γύρη και, όταν ενεργοποιείται η '
                                               'αποφυγή, αποκλείει προτάσεις αερισμού. Προσαρμόζεται στην '
                                               'πραγματική κλίμακα παρόχου.',
                                         'en': 'First value treated as high on the selected pollen provider '
                                               'scale. Used to classify pollen and, when avoidance is '
                                               'enabled, block window-ventilation suggestions. Set it for '
                                               'the actual provider scale.'},
 'global_environment_pollen_max_scale': {'de': 'Höchster Wert der Pollenskala des ausgewählten Anbieters zur '
                                               'Prüfung und Interpretation der Messungen. Dies definiert die '
                                               'Skala; die Schwelle für hohe Pollen wird separat gesetzt.',
                                         'el': 'Μέγιστη τιμή της κλίμακας του επιλεγμένου παρόχου γύρης, για '
                                               'έλεγχο και ερμηνεία μετρήσεων. Ορίζει την κλίμακα, όχι το '
                                               'όριο υψηλής γύρης, που ρυθμίζεται χωριστά.',
                                         'en': 'Highest value in the selected pollen provider scale, used to '
                                               'validate and interpret its readings. It is a scale '
                                               'definition, not the threshold for high pollen; set that '
                                               'separately.'},
 'global_occupancy_away_cooldown_minutes': {'de': 'Verzögerung in Minuten, bevor aus Raumdaten auf ein '
                                                  'leeres Zuhause geschlossen wird; gilt nur ohne direkte '
                                                  'Zuhause-Tracker. Bestätigte Abwesenheit aller direkten '
                                                  'Tracker gilt sofort. Eine bestätigte Person zu Hause hat '
                                                  'immer Vorrang.',
                                            'el': 'Καθυστέρηση σε λεπτά πριν τα στοιχεία χώρων επιβεβαιώσουν '
                                                  'άδειο σπίτι, μόνο χωρίς άμεσους ανιχνευτές παρουσίας '
                                                  'σπιτιού. Η επιβεβαιωμένη απουσία όλων από άμεσους '
                                                  'ανιχνευτές ισχύει αμέσως. Επιβεβαιωμένο άτομο στο σπίτι '
                                                  'πάντα υπερισχύει.',
                                            'en': 'Delay in minutes before room-derived evidence confirms '
                                                  'the home is empty, used only when no direct home trackers '
                                                  'are configured. Direct verified trackers reporting '
                                                  'everyone away take effect immediately. A verified person '
                                                  'at home always takes precedence.'},
 'global_occupancy_source_stale_minutes': {'de': 'Höchstalter der Meldung für konfigurierte Listen belegter '
                                                 'Räume und Schlafräume. Veraltete oder ungültige Listen '
                                                 'gelten als unbekannt. Direkte Personen-/Geräte-Tracker '
                                                 'folgen ihren eigenen Nachweisregeln.',
                                           'el': 'Μέγιστη ηλικία αναφοράς για τις λίστες κατειλημμένων χώρων '
                                                 'και χώρων όπου κάποιος κοιμάται. Παλιές ή άκυρες λίστες '
                                                 'θεωρούνται άγνωστες. Οι άμεσοι ανιχνευτές '
                                                 'προσώπων/συσκευών ακολουθούν τους δικούς τους κανόνες.',
                                           'en': 'Maximum report age for the configured occupied-room and '
                                                 'sleeping-room list sources. Older or invalid lists become '
                                                 'unknown and cannot establish that a room is empty or '
                                                 'asleep. Direct person/device trackers follow their own '
                                                 'evidence rules.'},
 'global_setting_announcement_repeat_minutes': {'de': 'Minuten zwischen wiederholten Ansagen, solange '
                                                      'dieselbe Empfehlung gilt und automatische '
                                                      'Benachrichtigung oder Sprache aktiviert ist. HEM '
                                                      'prüft die Lage vor jeder Wiederholung. 0 deaktiviert '
                                                      'Wiederholungen, nicht die erste Ansage.',
                                                'el': 'Λεπτά ανάμεσα σε επαναλήψεις όσο παραμένει η ίδια '
                                                      'σύσταση και είναι ενεργές οι αυτόματες ειδοποιήσεις ή '
                                                      'εκφωνήσεις. Οι συνθήκες ελέγχονται ξανά πριν από κάθε '
                                                      'επανάληψη. Το 0 απενεργοποιεί τις επαναλήψεις, όχι '
                                                      'την πρώτη ανακοίνωση.',
                                                'en': 'Minutes between repeat announcements while the same '
                                                      'recommendation remains active and automatic '
                                                      'notification or speech is enabled. HEM rechecks '
                                                      'conditions before repeating. Set 0 to disable '
                                                      'repeats; the first announcement can still occur.'},
 'global_threshold_indoor_aqi': {'de': 'Innenwert für AQI, der eine Lüftungsempfehlung auslösen kann. HEM '
                                       'empfiehlt das Öffnen nur bei geeigneten Außenbedingungen. Dies ist '
                                       'eine Entscheidungsschwelle, kein Gerätesollwert.',
                                 'el': 'Επίπεδο εσωτερικού AQI που μπορεί να προκαλέσει πρόταση αερισμού από '
                                       'παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το επιτρέπουν και οι '
                                       'εξωτερικές συνθήκες. Είναι όριο απόφασης, όχι στόχος συσκευής.',
                                 'en': 'Indoor AQI level that can trigger a window-ventilation '
                                       'recommendation. HEM recommends opening only when outdoor conditions '
                                       'also permit it. This is a decision threshold, not a device target.'},
 'global_threshold_indoor_co2': {'de': 'Innenwert für CO₂ (ppm), der eine Lüftungsempfehlung auslösen kann. '
                                       'HEM empfiehlt das Öffnen nur bei geeigneten Außenbedingungen. Dies '
                                       'ist eine Entscheidungsschwelle, kein Gerätesollwert.',
                                 'el': 'Επίπεδο εσωτερικού CO₂ (ppm) που μπορεί να προκαλέσει πρόταση '
                                       'αερισμού από παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το '
                                       'επιτρέπουν και οι εξωτερικές συνθήκες. Είναι όριο απόφασης, όχι '
                                       'στόχος συσκευής.',
                                 'en': 'Indoor CO₂ (ppm) level that can trigger a window-ventilation '
                                       'recommendation. HEM recommends opening only when outdoor conditions '
                                       'also permit it. This is a decision threshold, not a device target.'},
 'global_threshold_indoor_humidity': {'de': 'Ersatzschwelle der Raumluftfeuchte für Lüftungsempfehlungen, '
                                            'wenn keine nutzbare kalibrierte Schimmelabschätzung vorliegt. '
                                            'Außenprüfungen gelten weiterhin. Sie legt keinen '
                                            'Gerätefeuchtesollwert fest.',
                                      'el': 'Εφεδρικό όριο σχετικής υγρασίας για προτάσεις αερισμού όταν δεν '
                                            'υπάρχει αξιοποιήσιμη βαθμονομημένη εκτίμηση μούχλας επιφάνειας. '
                                            'Ισχύουν και οι εξωτερικοί έλεγχοι. Δεν ορίζει στόχο υγραντήρα ή '
                                            'αφυγραντήρα.',
                                      'en': 'Fallback indoor relative-humidity threshold for ventilation '
                                            'advice when a usable calibrated surface-mold estimate is '
                                            'unavailable. Outdoor checks still apply. This does not set a '
                                            'humidifier or dehumidifier target.'},
 'global_threshold_indoor_mold': {'de': 'Geschätzte relative Feuchte an der kalibrierten kalten Oberfläche, '
                                        'ab der eine schimmelbezogene Lüftungsempfehlung möglich ist. '
                                        'Gemeint ist die Oberflächenfeuchte, nicht die Raumluftfeuchte; '
                                        'Schimmelwachstum wird nicht gemessen.',
                                  'el': 'Εκτιμώμενη σχετική υγρασία στη βαθμονομημένη ψυχρή επιφάνεια που '
                                        'μπορεί να προκαλέσει πρόταση αερισμού λόγω κινδύνου μούχλας. Αφορά '
                                        'την επιφάνεια, όχι την υγρασία αέρα, και δεν ανιχνεύει πραγματική '
                                        'ανάπτυξη μούχλας.',
                                  'en': 'Estimated relative humidity at the calibrated cold surface that can '
                                        'trigger mold-related ventilation advice. It uses surface RH, not '
                                        'room RH, and indicates conditions favorable to mold rather than '
                                        'detecting mold growth.'},
 'global_threshold_indoor_pm10': {'de': 'Innenwert für PM10 (µg/m³), der eine Lüftungsempfehlung auslösen '
                                        'kann. HEM empfiehlt das Öffnen nur bei geeigneten Außenbedingungen. '
                                        'Dies ist eine Entscheidungsschwelle, kein Gerätesollwert.',
                                  'el': 'Επίπεδο εσωτερικού PM10 (µg/m³) που μπορεί να προκαλέσει πρόταση '
                                        'αερισμού από παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το '
                                        'επιτρέπουν και οι εξωτερικές συνθήκες. Είναι όριο απόφασης, όχι '
                                        'στόχος συσκευής.',
                                  'en': 'Indoor PM10 (µg/m³) level that can trigger a window-ventilation '
                                        'recommendation. HEM recommends opening only when outdoor conditions '
                                        'also permit it. This is a decision threshold, not a device target.'},
 'global_threshold_indoor_pm25': {'de': 'Innenwert für PM2.5 (µg/m³), der eine Lüftungsempfehlung auslösen '
                                        'kann. HEM empfiehlt das Öffnen nur bei geeigneten Außenbedingungen. '
                                        'Dies ist eine Entscheidungsschwelle, kein Gerätesollwert.',
                                  'el': 'Επίπεδο εσωτερικού PM2.5 (µg/m³) που μπορεί να προκαλέσει πρόταση '
                                        'αερισμού από παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το '
                                        'επιτρέπουν και οι εξωτερικές συνθήκες. Είναι όριο απόφασης, όχι '
                                        'στόχος συσκευής.',
                                  'en': 'Indoor PM2.5 (µg/m³) level that can trigger a window-ventilation '
                                        'recommendation. HEM recommends opening only when outdoor conditions '
                                        'also permit it. This is a decision threshold, not a device target.'},
 'global_threshold_indoor_voc': {'de': 'Innenwert für VOC (µg/m³), der eine Lüftungsempfehlung auslösen '
                                       'kann. HEM empfiehlt das Öffnen nur bei geeigneten Außenbedingungen. '
                                       'Dies ist eine Entscheidungsschwelle, kein Gerätesollwert.',
                                 'el': 'Επίπεδο εσωτερικού VOC (µg/m³) που μπορεί να προκαλέσει πρόταση '
                                       'αερισμού από παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το '
                                       'επιτρέπουν και οι εξωτερικές συνθήκες. Είναι όριο απόφασης, όχι '
                                       'στόχος συσκευής.',
                                 'en': 'Indoor VOC (µg/m³) level that can trigger a window-ventilation '
                                       'recommendation. HEM recommends opening only when outdoor conditions '
                                       'also permit it. This is a decision threshold, not a device target.'},
 'global_threshold_indoor_voc_parts': {'de': 'Innenwert für VOC (ppb), der eine Lüftungsempfehlung auslösen '
                                             'kann. HEM empfiehlt das Öffnen nur bei geeigneten '
                                             'Außenbedingungen. Dies ist eine Entscheidungsschwelle, kein '
                                             'Gerätesollwert.',
                                       'el': 'Επίπεδο εσωτερικού VOC (ppb) που μπορεί να προκαλέσει πρόταση '
                                             'αερισμού από παράθυρα. Το άνοιγμα προτείνεται μόνο όταν το '
                                             'επιτρέπουν και οι εξωτερικές συνθήκες. Είναι όριο απόφασης, '
                                             'όχι στόχος συσκευής.',
                                       'en': 'Indoor VOC (ppb) level that can trigger a window-ventilation '
                                             'recommendation. HEM recommends opening only when outdoor '
                                             'conditions also permit it. This is a decision threshold, not a '
                                             'device target.'},
 'global_threshold_max_age_minutes': {'de': 'Höchstalter der verwendeten Umweltmesswerte in Minuten, '
                                            'einschließlich Außen-/Wetterdaten und Raummessungen. Ältere '
                                            'Werte gelten als veraltet und belegen weder sichere Lüftung '
                                            'noch gültige Temperaturen für die Schimmelkalibrierung.',
                                      'el': 'Μέγιστη ηλικία περιβαλλοντικών μετρήσεων σε λεπτά, μαζί με '
                                            'επιλεγμένα εξωτερικά/καιρικά δεδομένα και μετρήσεις χώρου. '
                                            'Παλιότερες τιμές δεν τεκμηριώνουν ασφαλή αερισμό ή έγκυρες '
                                            'θερμοκρασίες βαθμονόμησης μούχλας.',
                                      'en': 'Maximum age in minutes for environmental readings used by HEM, '
                                            'including selected outdoor/weather data and room measurements. '
                                            'Older readings become stale and cannot establish safe '
                                            'ventilation or valid mold-calibration temperatures.'},
 'global_threshold_max_outdoor_humidity': {'de': 'Obergrenze der relativen Außenfeuchte bei den '
                                                 'Lüftungsprüfungen. Höhere Werte verhindern '
                                                 'Öffnungsempfehlungen; Trocknungshinweise vergleichen '
                                                 'zusätzlich den Feuchtegehalt innen und außen.',
                                           'el': 'Ανώτατη εξωτερική σχετική υγρασία για τους ελέγχους '
                                                 'αερισμού. Τιμές πάνω από το όριο αποκλείουν πρόταση '
                                                 'ανοίγματος· οι προτάσεις ξήρανσης συγκρίνουν επίσης το '
                                                 'περιεχόμενο υγρασίας μέσα και έξω.',
                                           'en': 'Outdoor relative-humidity ceiling used with the other '
                                                 'window-ventilation checks. Readings above it block opening '
                                                 'advice; drying recommendations also compare indoor and '
                                                 'outdoor moisture content.'},
 'global_threshold_max_outdoor_temp': {'de': 'Verhindert Empfehlungen zum Fensteröffnen über dieser '
                                             'Außentemperatur, damit keine zu heiße Luft hereinkommt. Der '
                                             'Klimagerätesollwert bleibt davon unabhängig.',
                                       'el': 'Αποκλείει προτάσεις ανοίγματος πάνω από αυτή την εξωτερική '
                                             'θερμοκρασία ώστε να μην εισέρχεται πολύ θερμός αέρας. Δεν '
                                             'ορίζει τον στόχο του κλιματιστικού.',
                                       'en': 'Blocks window-opening advice above this outdoor temperature so '
                                             'ventilation does not bring in excessively hot air. It does not '
                                             'set the air-conditioner target.'},
 'global_threshold_max_wind_kmh': {'de': 'Höchste Außenwindgeschwindigkeit für Lüftungsempfehlungen in km/h. '
                                         'Meldet die ausgewählte Wetterquelle stärkeren Wind, verhindert HEM '
                                         'Öffnungsempfehlungen und kann das Schließen offener Fenster '
                                         'empfehlen. Dies ist keine Ventilatordrehzahl.',
                                   'el': 'Μέγιστη εξωτερική ταχύτητα ανέμου για προτάσεις αερισμού, σε km/h. '
                                         'Αν τα επιλεγμένα δεδομένα καιρού δείχνουν ισχυρότερο άνεμο, '
                                         'αποκλείεται το άνοιγμα και μπορεί να προταθεί κλείσιμο ανοιχτών '
                                         'παραθύρων. Δεν είναι ταχύτητα ανεμιστήρα.',
                                   'en': 'Maximum outdoor wind speed for window-ventilation advice, in km/h. '
                                         'If the selected weather data reports stronger wind, HEM blocks '
                                         'opening recommendations and can recommend closing open windows. '
                                         'This is not a fan-speed setting.'},
 'global_threshold_min_outdoor_temp': {'de': 'Verhindert Empfehlungen zum Fensteröffnen unter dieser '
                                             'Außentemperatur, um Kaltluft und Wärmeverluste zu begrenzen. '
                                             'Es ist eine Lüftungsgrenze, kein Heizsollwert.',
                                       'el': 'Αποκλείει προτάσεις ανοίγματος κάτω από αυτή την εξωτερική '
                                             'θερμοκρασία, περιορίζοντας κρύο αέρα και απώλειες θέρμανσης. '
                                             'Είναι έλεγχος αερισμού, όχι στόχος θέρμανσης.',
                                       'en': 'Blocks window-opening advice below this outdoor temperature to '
                                             'limit cold-air discomfort and heating losses. It is a '
                                             'ventilation guard, not a heating setpoint.'},
 'global_threshold_outdoor_aqi': {'de': 'AQI-Obergrenze im Freien für Lüftungsempfehlungen. Die '
                                        'Anbieterskala im AQI-Wähler prüfen; benutzerdefinierte '
                                        'Quellengrenzen haben Vorrang. Ein vergleichbarer aktueller Wert '
                                        'über der jeweiligen Grenze verhindert eine Öffnungsempfehlung.',
                                  'el': 'Ανώτατο όριο εξωτερικού AQI για τον αερισμό. Επιβεβαίωσε την '
                                        'κλίμακα παρόχου στον επιλογέα AQI· προσαρμοσμένα όρια ανά πηγή '
                                        'υπερισχύουν του γενικού. Συγκρίσιμη τρέχουσα τιμή πάνω από το '
                                        'αντίστοιχο όριο αποκλείει πρόταση ανοίγματος.',
                                  'en': 'Outdoor AQI ceiling used for ventilation. Confirm the provider '
                                        'scale with the AQI selector; per-source custom limits override this '
                                        'general ceiling. A comparable current value above its applicable '
                                        'limit blocks opening advice.'},
 'global_threshold_outdoor_co2': {'de': 'Obergrenze für CO₂ (ppm) im Freien bei Lüftungsempfehlungen. Ein '
                                        'aktueller Wert darüber verhindert eine Empfehlung zum '
                                        'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                        'müssen ebenfalls erfüllt sein.',
                                  'el': 'Ανώτατο όριο εξωτερικού CO₂ (ppm) για συμβουλές αερισμού από '
                                        'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                        'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                        'ποιότητας αέρα και καιρού.',
                                  'en': 'Outdoor CO₂ (ppm) ceiling for window-ventilation advice. A current '
                                        'reading above this value blocks an opening recommendation. Other '
                                        'air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_no2': {'de': 'Obergrenze für NO₂ (µg/m³) im Freien bei Lüftungsempfehlungen. Ein '
                                        'aktueller Wert darüber verhindert eine Empfehlung zum '
                                        'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                        'müssen ebenfalls erfüllt sein.',
                                  'el': 'Ανώτατο όριο εξωτερικού NO₂ (µg/m³) για συμβουλές αερισμού από '
                                        'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                        'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                        'ποιότητας αέρα και καιρού.',
                                  'en': 'Outdoor NO₂ (µg/m³) ceiling for window-ventilation advice. A '
                                        'current reading above this value blocks an opening recommendation. '
                                        'Other air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_o3': {'de': 'Obergrenze für O₃ (µg/m³) im Freien bei Lüftungsempfehlungen. Ein '
                                       'aktueller Wert darüber verhindert eine Empfehlung zum Fensteröffnen. '
                                       'Die übrigen Luftqualitäts- und Wetterprüfungen müssen ebenfalls '
                                       'erfüllt sein.',
                                 'el': 'Ανώτατο όριο εξωτερικού O₃ (µg/m³) για συμβουλές αερισμού από '
                                       'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                       'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                       'ποιότητας αέρα και καιρού.',
                                 'en': 'Outdoor O₃ (µg/m³) ceiling for window-ventilation advice. A current '
                                       'reading above this value blocks an opening recommendation. Other '
                                       'air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_pm10': {'de': 'Obergrenze für PM10 (µg/m³) im Freien bei Lüftungsempfehlungen. '
                                         'Ein aktueller Wert darüber verhindert eine Empfehlung zum '
                                         'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                         'müssen ebenfalls erfüllt sein.',
                                   'el': 'Ανώτατο όριο εξωτερικού PM10 (µg/m³) για συμβουλές αερισμού από '
                                         'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                         'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                         'ποιότητας αέρα και καιρού.',
                                   'en': 'Outdoor PM10 (µg/m³) ceiling for window-ventilation advice. A '
                                         'current reading above this value blocks an opening recommendation. '
                                         'Other air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_pm25': {'de': 'Obergrenze für PM2.5 (µg/m³) im Freien bei Lüftungsempfehlungen. '
                                         'Ein aktueller Wert darüber verhindert eine Empfehlung zum '
                                         'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                         'müssen ebenfalls erfüllt sein.',
                                   'el': 'Ανώτατο όριο εξωτερικού PM2.5 (µg/m³) για συμβουλές αερισμού από '
                                         'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                         'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                         'ποιότητας αέρα και καιρού.',
                                   'en': 'Outdoor PM2.5 (µg/m³) ceiling for window-ventilation advice. A '
                                         'current reading above this value blocks an opening recommendation. '
                                         'Other air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_so2': {'de': 'Obergrenze für SO₂ (µg/m³) im Freien bei Lüftungsempfehlungen. Ein '
                                        'aktueller Wert darüber verhindert eine Empfehlung zum '
                                        'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                        'müssen ebenfalls erfüllt sein.',
                                  'el': 'Ανώτατο όριο εξωτερικού SO₂ (µg/m³) για συμβουλές αερισμού από '
                                        'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                        'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                        'ποιότητας αέρα και καιρού.',
                                  'en': 'Outdoor SO₂ (µg/m³) ceiling for window-ventilation advice. A '
                                        'current reading above this value blocks an opening recommendation. '
                                        'Other air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_voc': {'de': 'Obergrenze für VOC (µg/m³) im Freien bei Lüftungsempfehlungen. Ein '
                                        'aktueller Wert darüber verhindert eine Empfehlung zum '
                                        'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                        'müssen ebenfalls erfüllt sein.',
                                  'el': 'Ανώτατο όριο εξωτερικού VOC (µg/m³) για συμβουλές αερισμού από '
                                        'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει πρόταση '
                                        'ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι έλεγχοι '
                                        'ποιότητας αέρα και καιρού.',
                                  'en': 'Outdoor VOC (µg/m³) ceiling for window-ventilation advice. A '
                                        'current reading above this value blocks an opening recommendation. '
                                        'Other air-quality and weather checks must also pass.'},
 'global_threshold_outdoor_voc_parts': {'de': 'Obergrenze für VOC (ppb) im Freien bei Lüftungsempfehlungen. '
                                              'Ein aktueller Wert darüber verhindert eine Empfehlung zum '
                                              'Fensteröffnen. Die übrigen Luftqualitäts- und Wetterprüfungen '
                                              'müssen ebenfalls erfüllt sein.',
                                        'el': 'Ανώτατο όριο εξωτερικού VOC (ppb) για συμβουλές αερισμού από '
                                              'παράθυρα. Τρέχουσα μέτρηση πάνω από την τιμή αποκλείει '
                                              'πρόταση ανοίγματος. Πρέπει επίσης να ικανοποιούνται οι άλλοι '
                                              'έλεγχοι ποιότητας αέρα και καιρού.',
                                        'en': 'Outdoor VOC (ppb) ceiling for window-ventilation advice. A '
                                              'current reading above this value blocks an opening '
                                              'recommendation. Other air-quality and weather checks must '
                                              'also pass.'},
 'home_ai_rewrite_announcements': {'de': 'Erlaubt dem eingerichteten Konversationsagenten, Ansagen '
                                         'umzuformulieren. Empfehlung und Handlungsentscheidung bleiben bei '
                                         'HEM; der Agent ändert nur den Wortlaut.',
                                   'el': 'Επιτρέπει στον επιλεγμένο πράκτορα συνομιλίας να αναδιατυπώνει τις '
                                         'ανακοινώσεις. Η σύσταση και η απόφαση ενέργειας παραμένουν του '
                                         'HEM· αλλάζει μόνο η διατύπωση.',
                                   'en': 'Allows the configured conversation agent to rewrite announcement '
                                         'wording. HEM keeps the underlying recommendation and action '
                                         'decision; the agent only changes phrasing.'},
 'home_aqi_custom_limit': {'de': 'Quellenspezifische Obergrenze auf der gewählten AQI-Skala. Wird bei '
                                 'benutzerdefinierter Skala für Lüftungsvergleiche genutzt. Ändern '
                                 'konvertiert die Quelle nicht in eine andere AQI-Skala.',
                           'el': 'Ανώτατο όριο ειδικά για αυτή την πηγή στην επιλεγμένη κλίμακα AQI. '
                                 'Χρησιμοποιείται σε συγκρίσεις αερισμού με προσαρμοσμένη κλίμακα. Η αλλαγή '
                                 'δεν μετατρέπει την πηγή σε άλλη κλίμακα AQI.',
                           'en': 'Source-specific upper limit on the selected AQI provider scale. Used for '
                                 'ventilation comparisons when this source uses a custom scale. Changing it '
                                 'does not convert the source to a different AQI scale.'},
 'home_aqi_scale': {'de': 'Anbieterskala dieser tatsächlichen AQI-Quelle. Automatik nutzt erkannte '
                          'Metadaten; Unbekannt deaktiviert den Vergleich einer nicht erkannten Skala. '
                          'Benutzerdefiniert benötigt einen sinnvollen Quellengrenzwert. Zahlen '
                          'verschiedener AQI-Skalen sind nicht austauschbar.',
                    'el': 'Κλίμακα παρόχου αυτής της πηγής AQI. Το Αυτόματο χρησιμοποιεί αναγνωρισμένα '
                          'μεταδεδομένα· το Άγνωστο απενεργοποιεί τη σύγκριση μη αναγνωρισμένης κλίμακας. Η '
                          'Προσαρμοσμένη χρειάζεται ουσιαστικό όριο ανά πηγή. Διαφορετικές κλίμακες δεν '
                          'συγκρίνονται άμεσα.',
                    'en': 'Provider scale of this actual AQI source. Automatic uses recognized provider '
                          'metadata; Unknown disables AQI comparison for an unidentified scale. Choose '
                          'Custom only with a meaningful source-specific custom limit. Raw AQI numbers from '
                          'different scales are not interchangeable.'},
 'home_automatic_notifications': {'de': 'Versendet neue HEM-Empfehlungen automatisch über den eingerichteten '
                                        'Benachrichtigungsweg. Das Wiederholungsintervall steuert '
                                        'Erinnerungen. Separat aktivierte Sprachausgabe bleibt beim '
                                        'Ausschalten bestehen.',
                                  'el': 'Στέλνει αυτόματες ειδοποιήσεις για νέες συστάσεις HEM μέσω της '
                                        'επιλεγμένης διαδρομής ειδοποίησης. Το διάστημα επανάληψης ρυθμίζει '
                                        'τις υπενθυμίσεις. Η απενεργοποίηση δεν απενεργοποιεί την ξεχωριστά '
                                        'ενεργοποιημένη εκφώνηση.',
                                  'en': 'Sends automatic notifications for new HEM recommendations using the '
                                        'configured notification path. The repeat interval controls '
                                        'reminders while a recommendation persists. Turning this off does '
                                        'not turn off separately enabled speech.'},
 'home_automatic_tts': {'de': 'Spricht neue HEM-Empfehlungen automatisch über die eingerichtete '
                              'Sprachausgabe. Das Wiederholungsintervall gilt auch für fortbestehende '
                              'Empfehlungen. Textbenachrichtigungen haben einen eigenen Schalter.',
                        'el': 'Εκφωνεί αυτόματα νέες συστάσεις HEM από την επιλεγμένη έξοδο ομιλίας. Το '
                              'διάστημα επανάληψης ρυθμίζει τις επαναλαμβανόμενες εκφωνήσεις. Οι γραπτές '
                              'ειδοποιήσεις έχουν ξεχωριστό διακόπτη.',
                        'en': 'Speaks new HEM recommendations automatically through the configured speech '
                              'output. The repeat interval controls repeated speech while the recommendation '
                              'persists. Notification messages have a separate switch.'},
 'home_away_open_window_alert': {'de': 'Meldet offene ausgewählte Raumfenster, wenn bestätigte '
                                       'Anwesenheitsdaten zeigen, dass niemand zu Hause ist. Unbekannte '
                                       'Anwesenheit beweist keine Abwesenheit. Die Meldung schließt keine '
                                       'Fenster.',
                                 'el': 'Ανακοινώνει ότι παραμένουν ανοιχτά επιλεγμένα παράθυρα όταν '
                                       'επιβεβαιωμένα στοιχεία παρουσίας δείχνουν ότι όλοι απουσιάζουν. '
                                       'Άγνωστη παρουσία δεν αποδεικνύει απουσία. Η ειδοποίηση δεν κλείνει '
                                       'παράθυρα.',
                                 'en': 'Announces when verified home-presence evidence says everyone is away '
                                       'while selected room windows remain open. Unknown presence does not '
                                       'prove absence. This alert does not close windows.'},
 'home_global_environment_pollen_avoid_ventilation': {'de': 'Nimmt hohe Pollenbelastung in die Bedingungen '
                                                            'auf, die Fensterlüftungsempfehlungen '
                                                            'verhindern. Quelle, Hochschwelle und '
                                                            'Skalenmaximum bestimmen die Einstufung.',
                                                      'el': 'Προσθέτει την υψηλή γύρη στις συνθήκες που '
                                                            'αποκλείουν πρόταση αερισμού από παράθυρα. Η '
                                                            'επιλεγμένη πηγή, το όριο υψηλής γύρης και το '
                                                            'μέγιστο της κλίμακας καθορίζουν την ταξινόμηση.',
                                                      'en': 'Adds high pollen to the conditions that block '
                                                            'window-ventilation advice. The selected pollen '
                                                            'source, high threshold and provider maximum '
                                                            'define what counts as high.'},
 'home_global_occupancy_away_cooldown_minutes': {'de': 'Verzögerung in Minuten, bevor aus Raumdaten auf ein '
                                                       'leeres Zuhause geschlossen wird; gilt nur ohne '
                                                       'direkte Zuhause-Tracker. Bestätigte Abwesenheit '
                                                       'aller direkten Tracker gilt sofort. Eine bestätigte '
                                                       'Person zu Hause hat immer Vorrang.',
                                                 'el': 'Καθυστέρηση σε λεπτά πριν τα στοιχεία χώρων '
                                                       'επιβεβαιώσουν άδειο σπίτι, μόνο χωρίς άμεσους '
                                                       'ανιχνευτές παρουσίας σπιτιού. Η επιβεβαιωμένη '
                                                       'απουσία όλων από άμεσους ανιχνευτές ισχύει αμέσως. '
                                                       'Επιβεβαιωμένο άτομο στο σπίτι πάντα υπερισχύει.',
                                                 'en': 'Delay in minutes before room-derived evidence '
                                                       'confirms the home is empty, used only when no direct '
                                                       'home trackers are configured. Direct verified '
                                                       'trackers reporting everyone away take effect '
                                                       'immediately. A verified person at home always takes '
                                                       'precedence.'},
 'home_global_policy_home_policy': {'de': 'Eine bestätigte Person zu Hause hält das Zuhause immer auf '
                                          'anwesend. Alle zu Hause bleibt für bestehende Konfigurationen '
                                          'erhalten und verwendet dieselbe Regel. Abwesenheit muss bestätigt '
                                          'sein; ein unbekannter Tracker beweist nicht, dass alle gegangen '
                                          'sind.',
                                    'el': 'Επιβεβαιωμένο άτομο στο σπίτι διατηρεί πάντα την κατάσταση '
                                          'παρουσίας. Η επιλογή «Όλοι στο σπίτι» διατηρείται για παλαιές '
                                          'ρυθμίσεις και χρησιμοποιεί τον ίδιο κανόνα. Απαιτείται '
                                          'επιβεβαιωμένη απουσία· άγνωστος ανιχνευτής δεν αποδεικνύει ότι '
                                          'έφυγαν όλοι.',
                                    'en': 'A verified person at home always keeps the home occupied. All '
                                          'home is retained for existing configurations and uses this same '
                                          'rule. Away requires verified absence; an unknown selected tracker '
                                          'cannot prove everyone has left.'},
 'home_language': {'de': 'Sprache für HEM-Ansagen. Die automatische Auswahl folgt der '
                         'Home-Assistant-Sprache. Die Oberflächensprache anderer Benutzer wird dadurch nicht '
                         'geändert.',
                   'el': 'Γλώσσα ανακοινώσεων HEM. Η αυτόματη επιλογή ακολουθεί τη γλώσσα Home Assistant. '
                         'Δεν αλλάζει τη γλώσσα διεπαφής Home Assistant για άλλους χρήστες.',
                   'en': 'Language used for HEM announcements. The automatic choice follows the Home '
                         'Assistant language. This does not change the Home Assistant interface language for '
                         'other users.'},
 'home_shade_announce_before_movement': {'de': 'Steuert die Ansage vor automatischer Beschattungsbewegung. '
                                               'Die Einstellung je Beschattung gilt für dieses Gerät, die '
                                               'globale Einstellung als Vorgabe. Sie erlaubt allein keine '
                                               'Bewegung; Freigaben und Bewegungsprüfungen gelten weiterhin.',
                                         'el': 'Ελέγχει την ανακοίνωση πριν από αυτόματη κίνηση σκιάστρων. Η '
                                               'ρύθμιση ανά σκίαστρο αφορά αυτό το σκίαστρο, ενώ η γενική '
                                               'είναι προεπιλογή. Δεν επιτρέπει από μόνη της κίνηση· ισχύουν '
                                               'οι άδειες και οι έλεγχοι κίνησης.',
                                         'en': 'Controls the announcement before automatic shade movement. A '
                                               'per-shade setting applies to that shade; the global setting '
                                               'is the default. It does not enable movement: room and shade '
                                               'automation permissions and movement checks still apply.'},
 'home_use_announcement_hub': {'de': 'Leitet HEM-Ansagen über die eingerichtete Integration Announcement '
                                     'Hub. Hub und Empfänger werden separat konfiguriert. Dieser Schalter '
                                     'wählt den Übertragungsweg; automatische Benachrichtigungen und Sprache '
                                     'werden weiterhin separat aktiviert.',
                               'el': 'Δρομολογεί τις ανακοινώσεις HEM μέσω της ενσωμάτωσης Announcement Hub. '
                                     'Ο κόμβος και οι προορισμοί του ρυθμίζονται ξεχωριστά. Ο διακόπτης '
                                     'επιλέγει διαδρομή αποστολής· οι αυτόματες ειδοποιήσεις και εκφωνήσεις '
                                     'ελέγχονται χωριστά.',
                               'en': 'Routes HEM announcements through the configured Announcement Hub '
                                     'integration. Configure the hub and its destinations separately. This '
                                     'switch chooses the delivery route; automatic notification and speech '
                                     'switches still govern automatic announcements.'},
 'shade_announce': {'de': 'Steuert die Ansage vor automatischer Beschattungsbewegung. Die Einstellung je '
                          'Beschattung gilt für dieses Gerät, die globale Einstellung als Vorgabe. Sie '
                          'erlaubt allein keine Bewegung; Freigaben und Bewegungsprüfungen gelten weiterhin.',
                    'el': 'Ελέγχει την ανακοίνωση πριν από αυτόματη κίνηση σκιάστρων. Η ρύθμιση ανά σκίαστρο '
                          'αφορά αυτό το σκίαστρο, ενώ η γενική είναι προεπιλογή. Δεν επιτρέπει από μόνη της '
                          'κίνηση· ισχύουν οι άδειες και οι έλεγχοι κίνησης.',
                    'en': 'Controls the announcement before automatic shade movement. A per-shade setting '
                          'applies to that shade; the global setting is the default. It does not enable '
                          'movement: room and shade automation permissions and movement checks still apply.'},
 'shade_auto_control': {'de': 'Erlaubt automatische Sonnenbeschattung dieses Geräts bei Raumfreigabe und '
                              'bestandenen Bewegungsprüfungen. Einschalten erteilt die Steuerfreigabe; bloße '
                              'Auswahl tut dies nicht. Manueller Eingriff beendet die HEM-Zuständigkeit.',
                        'el': 'Επιτρέπει αυτόματη ηλιακή σκίαση αυτού του καλύμματος όταν ισχύει η άδεια '
                              'χώρου και οι έλεγχοι κίνησης. Η ενεργοποίηση είναι ρητή άδεια ελέγχου· η απλή '
                              'επιλογή καλύμματος δεν την παρέχει. Χειροκίνητη παρέμβαση διακόπτει την '
                              'κατοχή ελέγχου HEM.',
                        'en': 'Allows automatic solar-shading control for this cover when the room '
                              'permission and all movement checks pass. Turning it on is a control opt-in; '
                              'merely selecting a cover does not enable it. Manual intervention releases '
                              'HEM’s ownership.'},
 'shade_close_above_c': {'de': 'Raumtemperaturschwelle zum automatischen Schließen dieser Beschattung gegen '
                               'Sonnenerwärmung. Verwendet die Raum-, nicht die Außentemperatur. Lux allein '
                               'löst kein Schließen aus; alle übrigen Bedingungen gelten.',
                         'el': 'Όριο θερμοκρασίας χώρου για αυτόματο κλείσιμο αυτού του καλύμματος λόγω '
                               'ηλιακής θέρμανσης. Χρησιμοποιεί εσωτερική, όχι εξωτερική θερμοκρασία. Τα lux '
                               'μόνα τους δεν προκαλούν κλείσιμο· ισχύουν όλοι οι άλλοι έλεγχοι σκίασης.',
                         'en': 'Room-temperature threshold for automatically closing this cover against '
                               'solar heating. Uses current room temperature, not outdoor temperature. Lux '
                               'cannot trigger closure by itself; all other shading conditions must pass.'},
 'shade_lux_enabled': {'de': 'Verlangt gemessene Beleuchtungsstärke mindestens auf der Lux-Schwelle dieser '
                             'Beschattung vor dem automatischen Schließen. Zusätzlich eine gültige Quelle '
                             'wählen. Niedrige, veraltete oder unbekannte Lux sperren neues Schließen, lösen '
                             'aber allein kein Öffnen aus.',
                       'el': 'Απαιτεί μετρημένη φωτεινότητα τουλάχιστον ίση με το όριο lux αυτού του '
                             'καλύμματος πριν από αυτόματο κλείσιμο. Επίλεξε και έγκυρη πηγή lux. Χαμηλά, '
                             'παλιά ή άγνωστα lux αποκλείουν νέο κλείσιμο· δεν προκαλούν αυτόνομα άνοιγμα.',
                       'en': 'Requires measured illuminance at or above this cover’s minimum lux before it '
                             'may automatically close. Select a valid lux source as well. Low, stale or '
                             'unknown lux blocks new closure; it does not independently command reopening.'},
 'shade_lux_entity': {'de': 'Gemessene Lux-Quelle für die optionale Beschattungsprüfung dieses Geräts; ein '
                            'unterstützter Mittelwert ausgewählter Raumsensoren ist ebenfalls möglich. '
                            'Unabhängig von der Quelle des Lichtverlaufs und aktiviert allein keine '
                            'Lux-Regelung.',
                      'el': 'Πηγή μετρημένων lux για τον προαιρετικό έλεγχο σκίασης αυτού του καλύμματος. '
                            'Μπορεί να χρησιμοποιηθεί και υποστηριζόμενος μέσος επιλεγμένων αισθητήρων '
                            'χώρου. Διαφέρει από την πηγή ιστορικού φωτισμού και δεν ενεργοποιεί μόνη της '
                            'έλεγχο lux.',
                      'en': 'Measured lux source used by this cover’s optional solar-shading lux check. A '
                            'supported selected room-sensor mean can also be used. This association is '
                            'separate from the room illuminance-history source and does not enable lux '
                            'control by itself.'},
 'shade_min_lux': {'de': 'Mindestbeleuchtungsstärke in Lux für automatisches Schließen bei aktiviertem '
                         'Lux-Schalter. Zusätzlicher Nachweis zu Temperatur und Sonne; keine eigenständige '
                         'Lichtautomation und kein Raumbeleuchtungssollwert.',
                   'el': 'Ελάχιστη μετρημένη φωτεινότητα σε lux για αυτόματο κλείσιμο με ενεργό τον διακόπτη '
                         'lux. Είναι πρόσθετο στοιχείο μαζί με θερμοκρασία και ήλιο, όχι ανεξάρτητος '
                         'αυτοματισμός φωτεινότητας ή στόχος φωτισμού χώρου.',
                   'en': 'Minimum measured illuminance in lux required for this cover’s automatic closure '
                         'when its lux switch is on. It is extra evidence alongside temperature and sun '
                         'checks, not a standalone light-level automation or a room-lighting target.'},
 'shade_window_entity': {'de': 'Echter Kontakt der Geräteklasse Window für diese Beschattung. Die Bewegung '
                               'verwendet seinen bekannten Offen-/Geschlossen-Zustand und lehnt ungeeignete '
                               'oder unbekannte Nachweise ab. Auswahl aktiviert keine Automatikfreigabe.',
                         'el': 'Πραγματική επαφή κατηγορίας Window που αντιστοιχεί στο κάλυμμα. Η αυτόματη '
                               'κίνηση χρησιμοποιεί γνωστή κατάσταση ανοίγματος/κλεισίματος και απορρίπτει '
                               'ασύμβατα ή άγνωστα στοιχεία. Η επιλογή δεν ενεργοποιεί άδεια αυτοματισμού.',
                         'en': 'Actual Window-class contact associated with this cover. Automatic movement '
                               'uses its known open/closed state and rejects incompatible or unknown window '
                               'evidence. Selecting a contact does not enable the cover’s automation '
                               'permission.'}}

def configuration_help(key: str, locale: str = "en") -> str | None:
    """One current setting explanation; never the complete help catalog."""
    translations = SETTING_HELP.get(key)
    if translations is None:
        return None
    return translations.get(setting_locale(locale), translations["en"])


def metadata_key(entity) -> str | None:
    """Resolve existing translation identities, including dynamic sources."""
    kind = getattr(entity, "_kind", None)
    if kind == "aqi_limit":
        return "home_aqi_custom_limit"
    if kind == "device_target":
        return "area_device_target_" + entity._key
    return getattr(entity, "_attr_translation_key", None)


class SettingsMetadata:
    """Localized full names and concise help, with no entity-registry writes.

    Full names put the functional category first instead of the device prefix.
    Existing unique IDs, entity IDs and registry user-name overrides are intact.
    Translation keys remain available to Home Assistant for select-state names.
    """

    @property
    def name(self):
        key = metadata_key(self)
        locale = getattr(getattr(self._manager.hass, "config", None), "language", "en")
        name = localized_setting_name(key, locale) if key else None
        source_id = (getattr(self, "_entity_id", None)
                     if getattr(self, "_kind", None) == "device_target"
                     else getattr(self, "_cover", None))
        if name and source_id:
            source = self._manager.hass.states.get(source_id)
            source_name = getattr(source, "name", None) or source_id
            group, _, label = name.partition(" · ")
            return f"{group} · {source_name} · {label}"
        return name if name else super().name

    @property
    def extra_state_attributes(self):
        key = metadata_key(self)
        locale = getattr(getattr(self._manager.hass, "config", None), "language", "en")
        text = configuration_help(key, locale) if key else None
        attributes = dict(getattr(super(), "extra_state_attributes", None) or {})
        if text:
            attributes.update({"configuration_help": text, "setting_key": key,
                               "setting_group": localized_setting_group(key, locale)})
        return attributes
