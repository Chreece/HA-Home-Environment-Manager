<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Home Umweltmanager - intelligenter Luftqualität, Komfort, Lüftung und Klimakontrolle" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Unterstützung von Chreece Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <strong>Deutsch</strong> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Umweltmanager

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM Logo" width="420">
</p>

<p align="center"><strong>Die ganze Umgebung Ihres Hauses, in einem Home Assistant Das ist eine Karte.</strong></p>

**HEM hilft Ihrem Zuhause, die Umgebung zu verstehen und auf das zu reagieren, was jedes Zimmer wirklich braucht.** Es bringt deine Home Assistant Sensoren, Wetterdaten, Besatzungsinformationen und kompatible Klimaanlagen zusammen, damit Sie die Luftqualität überwachen, nützliche Lüftungsberatungen erhalten, Komfortmanagement und die von Ihnen gewählte Ausrüstung automatisieren können.

Zum Beispiel: HEM Sie können die Heizung reduzieren, während alle weg sind, ausgewählte Räume vorbereiten, bevor Sie zurückkehren, während Sie schlafen ein anderes Luftfeuchtigkeitsziel verwenden oder Sie bitten, ein Fenster zu öffnen, bevor Sie einen Entfeuchter ausführen. **Überwachung und Empfehlung**, ohne die Kontrolle von Geräten.

**Du bleibst an der Spitze.** Jeder Raum hat seine eigenen Einstellungen, jedes unterstützte Gerät hat seine eigene Steuerung, Betriebsweise, Ziele und Sicherheitsgrenzen. HEM niemals davon ausgeht, dass die Auswahl eines Geräts ihm die Erlaubnis gibt, dieses Gerät zu bedienen.

[Erkunden Sie die Merkmale](#what-can-hem-do) · [Siehe die Schnittstelle](#see-hem-in-action) · [Installieren](#installation) · [Machen Sie Ihr Zuhause](#getting-started) · [Detaillierte Anleitung](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Was kann HEM - Das tun wir?

| Ihre Situation | Wie? HEM kann helfen |
| --- | --- |
| **Das Haus ist leer.** | Schalten Sie die Zielsetzungen auf Weg, respektieren Sie die Präsenzregeln in jedem Raum und vermeiden Sie, ausgewählte Geräte unnötig zu betreiben. |
| **Du bist auf dem Weg nach Hause.** | Drücken Sie **Bereiten Sie sich auf die Ankunft vor.** die vorübergehende Nutzung von Wohnkomfortzielen für qualifizierte automatische Steuerungen, auch wenn alle noch weg sind. |
| **Jemand schläft.** | Nutzen Sie Schlafziele, reduzieren Sie das Fanlärm oder halten Sie die gewählten Geräte aus, während jedes besetzte Zimmer schläft. |
| **Ein Zimmer ist feucht.** | Vergleichen Sie seine Feuchtigkeits- und Schimmelanzeige mit Zielen, schlagen Sie eine nützliche Belüftung vor oder bedienen Sie einen autorisierten Entfeuchter mit Hilfe von Automatischen oder PID Die Kontrolle. |
| **Es ist heiß und sonnig.** | Bewertet die Raumtemperatur, das Sonnenlicht, das Wetter und die angeschlossenen Fensterkontakte, bevor Sie die gewählten Farbtöne wechseln. |
| **Die Außenluft sieht besser aus.** | Es wird empfohlen, eine Lüftung zu ermöglichen, wobei die Nachfrage nach Innenräumen, die Umweltverschmutzung im Freien, die Temperatur, die Luftfeuchtigkeit, der Wind und die verfügbaren Pollen- oder Wetterwarnungen zu berücksichtigen sind. |
| **Ein Heizgerät oder TRV hört auf zu reagieren** | Anzeigen Sie den nicht verfügbaren oder wartenden Zustand, behalten Sie den konfigurierten Controller und melden Sie Fehler des unterstützten Geräts, ohne davon auszugehen, dass sich eine Batterie oder eine Relay wiederhergestellt hat. |

Dies sind Beispiele, nicht Maßnahmen, die HEM Die Ergebnisse hängen von den ausgewählten Sensoren ab. Home Assistant Fähigkeiten und Ihre Eintrittsinstellungen.

<a id="explore-the-features"></a>
## Erkunden Sie die Merkmale

<a id="a-complete-home-dashboard"></a>
### Ein komplettes Heim-Dashboard

Die HEM Die Karte gibt Ihnen einen nützlichen Überblick, ohne mehrere Integrationen zu öffnen.

- Sehen Sie sich die Außenbedingungen, die Luftqualität an und ob eine Lüftung ratsam ist.
- Vergleichen Sie alle überwachten Räume auf einen Blick: Temperatur, relative Luftfeuchtigkeit, AQI, PM2,5, Schimmelindizierung, Licht und andere unterstützte Messwerte.
- Erweitern Sie alle Räume für detaillierte Messungen, Fenster- und Türinformationen, Klimastatus, aktive Steuerungen, Wartegründe und Gebäudephysik-Schätzungen.
- Schauen Sie sich Geschichten und Trends an, sehen Sie, welche Sensoren zu einem Durchschnitt beigetragen haben und unterscheiden Sie fehlende Messwerte von gemessenen Werten.
- Gruppenräume nach tatsächlichen Home Assistant oder eine einfache Zimmerliste verwenden, wenn Sie keine Böden haben.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Verschiedene Einstellungen für das Haus, jedes Zimmer und jedes Gerät

HEM die gemeinsame Politik von lokalen Entscheidungen getrennt hält.

| Einstellungsstufe | Was Sie einrichten können |
| --- | --- |
| **Zuhause** | Außenwetter und Verschmutzungsquellen, überwachte Räume, globale Lüftungsgrenzen, Haushaltsaufenthalt, Ankunftsvorbereitung und Ankündigungen. |
| **Zimmer** | Innenraumtemperatur- und Luftfeuchtigkeitsquellen, Luftqualitätsschwellen, Fenster- und Türkontakte, Schlaf- und Bewohnerverhalten, Raumspezifische Komfortziele, Lüftungs- und Schattierungsmöglichkeiten. |
| **Ein einzelnes Gerät** | Die verfügbaren Steuerungsarten, automatisch/handlich/PID Methode, Profilziele, Sensoren, stille Ventilatorinstellungen, Mindestbetriebszeiten, Stromschutz, Fensterverhalten und Fehlermeldungen des Geräts. |

Alle drei Ebenen sind über gruppierte, durchsuchbare Einstellungen in der Karte zugänglich. Home Assistant Änderungen an der Einrichtung.

<a id="climate-control-and-pid-device-by-device"></a>
### Klimabewältigung PID, Gerät für Gerät

HEM kann mit kompatiblen Home Assistant **Klima**, **Luftbefeuchter** und **Ventilator** Geräte, einschließlich Heizung, Kühlung, Entfeuchtung, Befeuchtung und Luftkreislauf- oder Luftreinigungsgeräte.

Für jeden **unterstützter physischer Betriebsmodus**, die Kontrollmethode unabhängig auswählen:

| Methode | Was es bedeutet |
| --- | --- |
| **Bestehende** | Lassen Sie den Betrieb mit dem vorhandenen Steuerungsweg. |
| **Automatisiert** | Folgen Sie mir HEMDie Messen der Nachfrage, die auf der Situation basierenden Ziele und Genehmigungen. |
| **PID** | Verwenden Sie proportionale, integrale und abgeleitete Rückkopplungssteuerung, wenn das Gerät und die Messung sie unterstützen. |
| **Handbuch** | Kontrolle durch ausdrücklich unterstützte Anfragen und Ziele. |
| **Wir sind weg .** | Halten Sie den Steuergerät aus, unter Berücksichtigung des physischen Schutzes und der Rückkopplungsanforderungen. |

Zum Beispiel kann eine Klimaanlage **PID für Heizung** und **Automatische Kühlung**Ein Entfeuchter kann seine eigene PID die Kalibrierung, die Ziele und die Zykluszeit. PID wenn geeignete Rückmeldungen und zwecksspezifische Kontrollen zur Verfügung stehen.

PID ist **nicht** eine allgemeine Überschreitung: HEM Sie unterstützen die vorgeschlagenen Änderungen, es sei denn, Sie entscheiden sich ausdrücklich für eine begrenzte automatische Anpassung.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Komfortabel, wenn man zu Hause ist, wirtschaftlich, wenn man weg ist.

HEM kann zwischen **Komfort, Zuhause, Weg, Schlaf und Öko** Ziele basierend auf der Situation des Haushaltes, den Zimmernachweisen und Ihren ausdrücklichen Auswahlen.

- **Zuhause und Weg:** Verwenden Sie unterschiedliche Ziele für Heizung, Kühlung und Luftfeuchtigkeit, abhängig von der geprüften Anwesenheit des Hauses.
- **Anwesenheit im Raum:** Führen Sie ein berechtigtes Gerät immer aus, wenn es Nachfrage gibt, nur wenn sein Zimmer besetzt ist oder nur wenn der Raum leer ist.
- **Schlaf:** Ein ausgewähltes Gerät kann abgeschaltet bleiben, wenn alle besetzten Räume schlafen.
- **Öko:** Eine geschlossene Innentür kann an einer geschützten Öko-Politik teilnehmen, wenn der Raum geprüft wird, dass er leer ist und andere Bedingungen erfüllt sind; eine geschlossene Tür allein beweist nicht, dass der Raum isoliert ist.
- **Aufwachenvorbereitung:** Verwenden Sie eine konfigurierte nächste Alarmquelle, um automatischen Schlaf vor dem Alarm zu lassen und den berechtigten Geräten Zeit zu geben, zu reagieren.

Ist die Besetzung, die Verfügbarkeit des Geräts oder andere erforderliche Beweise unsicher, HEM ist nicht einfach davon auszugehen, dass es sicher ist, ein automatisches Gerät zu starten.

<a id="prepare-your-environment-before-you-arrive"></a>
### Bereiten Sie Ihre Umgebung vor

**Bereiten Sie sich auf die Ankunft vor.** ist eine zeitgemäße Aktion für ein bestätigtes Away-Haus. HEMDas ist das Heimgerät.

HEM wird vorübergehend die konfigurierte **Zuhauseziele** zu berechtigtem Automatic/PID Ein Kontrollgerät, das normalerweise nur in besetzten Räumen eingesetzt wird, kann vor der Rückkehr mit der Erwärmung, Kühlung oder Anpassung der Luftfeuchtigkeit beginnen. **nur, wenn sie bereits die erforderliche körperliche Kontrollgenehmigung hat**.

Vorbereitung ist kein Befehl, um alles einzuschalten. Geräte benötigen immer noch echte Nachfrage, gültige Sensoren und Genehmigungen, und müssen Fenster, minimale ON/OFF-Zeiten und ihren eigenen Schutz respektieren. Home Assistant Neustart nicht den vollständigen Timer wieder auf.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Rat zur Lüftung, Fenster, Türen und Schattierung

HEM Vergleiche **was ein Zimmer braucht** mit **ob die Außenluft helfen kann**.

- Es wird empfohlen, Fenster zu öffnen oder zu schließen, wobei die aktuellen Innenmessungen, die Luftfeuchtigkeit, die Umweltverschmutzung, die Temperatur, der Wind, die Wetterwarnungen und der optionalen Pollenkontext verwendet werden.
- Verwenden Sie ausgewählte Fenster- und Türkontakte, um die Raumbedingungen zu erklären und vermeiden Sie, einen unbekannten Kontakt als geschlossen zu behandeln.
- Erfordern Sie optional, ein Fenster zu öffnen, bevor Sie ein unterstütztes automatisches Gerät starten, und setzen Sie dann die normale Steuerung fort, nachdem die konfigurierte Antwort warten muss, falls erforderlich.
- Verwenden Sie Türinformationen für Raumgrenzbewusstsein, Lüftungsvorkehrungen und optionales geschütztes Umweltverhalten.
- Verwalten Sie die eingeschlossenen Fenster, Verhütungen und Schattierungen mit geeigneten Fenster-, Temperatur-, Wetter-, Sonneneinstufungs- und optionalen Beleuchtungsnachweisen.

HEM Sie kann ohne steuerbare Fenster eine Lüftungsberatung geben, sie öffnet kein Fenster allein, nur weil eine Belüftung hilft.

<a id="humidity-mold-indication-and-air-quality"></a>
### Feuchtigkeit, Schimmelanzeige und Luftqualität

HEM kombiniert unterstützte Messwerte wie **Temperatur, Luftfeuchtigkeit, CO2, Partikel, VOC, AQI und Beleuchtung** Die verfügbaren Messungen hängen davon ab, was Ihre Home Assistant Einheitliche Einrichtung.

Die **Schimmelanzeige** Es kann die Luftfeuchtigkeit eines unterstützten automatischen Luftfeuchtigkeitssteuerers beeinflussen, wenn sie ordnungsgemäß konfiguriert ist.

**Die Schimmel-Anzeige ist eine Schätzung, nicht ein Schimmel- oder Sporentmelder.** Fehlende oder veraltete Sensordaten können keinen neuen Schimmel-basierten Gerätebefehl rechtfertigen.

<a id="announcements-diagnostics-and-protection"></a>
### Ankündigungen, Diagnose und Schutz

Sie können relevante Empfehlungen und Benachrichtigungen über konfigurierte Home Assistant Mitteilungen, TTS/Medien-Player oder **Ankündigungshub**, mit optionaler KI-Formulierung. KI kann die Ausdrückung einer Nachricht ändern; HEMDie Entscheidungen der physischen Kontrolle bleiben deterministisch.

HEM umfasst auch ein bestimmtes Gerät für den Schutz und die Diagnose:

- Mindestzeit der Ein- und Auslösung, Höchstbetriebszeit-Einstellungen und unterstützte externe Leistungsschalter.
- Fenster- und Besatzungsbeschränkungen, manuelle Überschreitung und Native-Kommando-Bestätigungskontrollen.
- Fehler- und nicht verfügbare Geräteberichterstattung mit einer Wahl des Benachrichtigungsverhaltens für jedes Gerät.
- Eine optionale Überwachung nach dem Schalten für vermutete Weiterwärmung nach einem OFF-Befehl, mit bewachter Überwachung und begrenzten Wiederherstellungsversuchen.
- Klarer Wartegründe, aktueller Betriebszustand und Quelleverfügbarkeit, damit Sie untersuchen können, bevor Sie mehr Kontrolle ermöglichen.

**Die Sicherheitsgrenzen bleiben auch dann in Kraft, wenn eine Alarmmeldung ausgeschaltet ist.** HEM eine erfolgreiche Kommandoversendung niemals als Beweis für die physische Reaktion eines Geräts betrachtet.

<a id="see-hem-in-action"></a>
## Siehst du ? HEM in Aktion

Diese englischsprachigen Illustrationen verwenden Probenräume und Messungen, um die Schnittstelle zu demonstrieren, anstatt Live-Daten aus einem bestimmten Haus zu zeigen.

<a id="home-at-a-glance"></a>
### Zuhause auf einen Blick

Erhalten Sie Rat zur Lüftung, Wetterbedingungen und den Status jedes überwachten Raumes in einer einzigen Karte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM Home-Dashboard mit Lüftungsberatung und Umweltmessungen in fünf Räumen" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Erweitern Sie den Raum für alle Details

Überprüfen Sie die Luftqualität, die Schimmelanzeige, die Anwesenheit, den Fensterzustand, die Klimakontrollen und die Erläuterungen für jede Entscheidung.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Erweiterte Badezimmer-Dashboard mit Messungen und unabhängigen Gerätecontrollern" width="760">
</p>

<a id="home-settings"></a>
### Home-Einstellungen

Verwalten Sie Außenquellen, die Anwesenheit im ganzen Haus, überwachte Räume, Lüftungsgrenzen, Vorbereitung und Benachrichtigungen.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Home-Einstellungen mit Suchgruppen und Quell- und Raummanagement" width="900">
</p>

<a id="room-settings"></a>
### Raum Einstellungen

Wählen Sie, was für jedes Zimmer wichtig ist: seine eigenen Sensoren, Ziele, Platz, Türen, Fenster, Lüftung, Schatten und Sicherheitsvorkehrungen.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Gruppe HEM Raum Einstellungen für Sensoren, Gerätebedienungen, Schlaf, Fenster und Schutz" width="760">
</p>

<a id="device-settings"></a>
### Geräteinstellungen

Ein Gerät ohne Änderung der anderen, einschließlich unterstützter Steuerungsmethoden, fein abgestimmt PID, ruhiger Betrieb, Timing und Fehlermeldung.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Gruppe HEM Einstellungen des Geräts mit Steuerung, PID, Stromschutz und Mitteilungen" width="900">
</p>

<a id="getting-started"></a>
## Ich beginne

1. **Organisieren Sie Ihre Zimmer.** In Home AssistantSie können Ihre Bereiche erstellen oder überprüfen und jedem die entsprechenden Sensoren und Geräte zuweisen.
2. **Wählen Sie aus, was Sie überwachen sollen.** Hinzufügen HEMSie können die unbenutzten Gruppen leer lassen.
3. **Konfiguration der gemeinsamen Informationen.** Wählen Sie verfügbare Wetter-/Luftqualitätsquellen im Freien, Nachweise für den Haushalt und die gewünschten Ankündigungszielen aus.
4. **Fügen Sie die Karte hinzu.** Öffnen Sie ein Dashboard im Bearbeitungsmodus und fügen Sie die **Home Umweltmanager** Beginnen Sie mit Raumüberwachung, Messungen und Lüftungsberatung.
5. **Steuerung nur dann aktivieren, wenn sie nützlich ist.** Öffnen Sie einen Raum, wählen Sie ein unterstütztes Gerät, überprüfen Sie seinen Controller und wählen Sie ausdrücklich PID für die gewünschten Modi HEM - Ich kann nicht arbeiten.

Du weißt es . **nicht** Beginnen Sie mit den Sensoren, die Sie haben, und führen Sie automatische Steuerung ein Gerät nach dem anderen ein.

<a id="add-the-card-manually"></a>
### Fügen Sie die Karte manuell hinzu

Wenn Sie YAML bevorzugen, verwenden Sie:

~~~yaml
type: custom:home-environment-manager-card
~~~

Wenn Ihre Home Assistant die Installation hat mehr als eine HEM Empfehlungssensor, müssen Sie möglicherweise die geeignete **Einheit** ausdrücklich:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Für Schritt-für-Schritt-Anweisungen zu den Quellen, Profilen, PID Einheitliche Veröffentlichungen, Ankündigungen und Ankündigungen [Detailliertes Konfigurationsleitfaden](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Gemeinschaftsgeschäft

1. Öffnen **HACS** in Home Assistant.
2. Hinzufügen **Die Kommission hat die Kommission mit dem Vorschlag für eine Verordnung (EG) Nr. 1333/2008 zur Verfügung gestellt.** als eine **benutzerdefiniertes Repository** in der **Integration** Kategorie, wenn sie nicht bereits aufgelistet ist.
3. Finden Sie **Home Umweltmanager** Und installieren Sie es.
4. Neustart **Home Assistant** Die Integration ist zu laden.
5. Geht zu **Einstellungen → Geräte & Dienstleistungen → Integration hinzufügen**, Suche nach **Home Umweltmanager** und die Einrichtung abschließen.

<a id="manual-installation"></a>
### Manuelle Installation

Kopieren Sie das Repository **custom_components/environment_manager** Ordner in die Passform **custom_components** Verzeichnis in Ihrem Home Assistant Konfiguration und Aufbewahrung des Verzeichnisnamen **Umwelt_manager**- Neustart Home Assistant und die Integration durch **Einstellungen → Geräte & Dienstleistungen**.

Für spätere Installationsänderungen halten Sie Ihre vorhandenen HEM Integrations-Eingabe und -Einstellungen. Laden Sie das Dashboard in Ihrem Browser neu, wenn sich das Aussehen der Karte nicht sofort erfrischt.

<a id="common-questions"></a>
## Häufige Fragen

**Kann ich es benutzen? HEM ohne ihm die Kontrolle über meine Geräte zu geben?**

Ja, Überwachung, Messung, Lüftungsberatung, Vergangenheit und viele Umweltangaben funktionieren, ohne das Gerät zu aktivieren.

**- Will . HEM Sie kontrollieren automatisch jedes Gerät, das sie entdeckt?**

Sie wählen die physischen Geräte aus, die Sie verwalten möchten, und wählen explizit die Steuerungsmethode für unterstützte Modi.

**Unterstützt jedes Gerät PID?**

- Nein, ich weiß nicht. HEM Unterstützungen PID für **in Betracht kommen** Wärme-, Kühl-, Luftfeuchtigkeits- oder Lüftersteuerungswege, wenn das Gerät und die gewählten Messungen die erforderlichen Fähigkeiten und Rückmeldungen bieten. PID Die Kontrolle.

**Kann ich jedem Zimmer unterschiedliche Regeln geben?**

Ja, die Bedingungen des Einsatzes, das Schlafverhalten, die Quellen, die Ziele und einige Sicherheitsvorlieben können sich je nach Raum unterscheiden, während jedes physische Gerät seine eigenen Betriebs- und Schutzabstellungen hat.

**Kann HEM Bereiten Sie mein Zuhause vor, während ich weg bin?**

- Ja, ich weiß. **Bereiten Sie sich auf die Ankunft vor.** Sie erlaubt den berechtigten, bereits autorisierten automatischen Controllern vorübergehend, Heimziele für einen begrenzten Zeitraum zu nutzen.

**Öffnet eine Empfehlung für eine gute Lüftung meine Fenster?**

Automatische Bewegung ist eine separate, opt-in-Funktion für berechtigte unterstützte Farbtöne oder -deckungen, die ihren eigenen Sicherheitsprüfungen unterliegen.

**Was ist, wenn ein Sensor oder ein Gerät nicht verfügbar ist?**

HEM die unbekannte Daten von realen Messungen unterscheidet, die konfigurierten Controllerinformationen soweit möglich speichert und Wartegründe und Diagnostik aufdeckt.

<a id="help-and-troubleshooting"></a>
## Hilfe und Fehlerbehebung

Wenn etwas falsch erscheint, überprüfen Sie den entsprechenden Raum oder die Kontrollstelle **Der Grund**, **Diagnostik**, Quelleverfügbarkeit und aktuelle Kontrollmethode. [Detailliertes Konfigurationsleitfaden](../../docs/advanced-configuration.md) umfasst gemeinsame Wartezustände, Präsenzpolitik, PID Anspruchsberechtigung, Fenster und Fehlerbehebung der Geräteantworten.

Für ein reproduzierbares Problem [öffnen GitHub Ausgabe](https://github.com/Chreece/HA-Home-Environment-Manager/issues) mit dem erwarteten Verhalten, dem tatsächlichen Verhalten, den relevanten Raum-/Geräte-Einstellungen und den Reproduktionsschritten.

Beiträge und Verbesserungen sind zu begrüßen. [Contributions.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Unterstützung und Lizenz

Wenn HEM ist für Sie nützlich, können Sie [Unterstützung von Griechenland bei Ko-fi](https://ko-fi.com/chreece).

Verteilt unter der [MIT-Lizenz](../../LICENSE).
