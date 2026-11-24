<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="HEM - intelligente Steuerung von Raumklima, Luftqualität, Lüftung und Komfort" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Chreece auf Ko-fi unterstützen" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <strong>Deutsch</strong> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Environment Manager

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM-Logo" width="420">
</p>

<p align="center"><strong>Das gesamte Raumklima Ihres Zuhauses auf einer einzigen Home-Assistant-Karte.</strong></p>

**HEM hilft Ihrem Zuhause, Umgebungsbedingungen zu erfassen und auf die Bedürfnisse jedes einzelnen Raums zu reagieren.** Dazu führt die Integration Sensoren aus Home Assistant, Wetterdaten, Anwesenheitsinformationen und kompatible Geräte für Heizung, Kühlung und Luftaufbereitung zusammen. Sie behalten Luftqualität und Raumklima im Blick, erhalten sinnvolle Lüftungsempfehlungen und können ausgewählte Geräte automatisieren.

So kann HEM beispielsweise die Heizung absenken, wenn niemand zu Hause ist, bestimmte Räume vor Ihrer Rückkehr vorbereiten, nachts einen anderen Luftfeuchtigkeitswert anstreben oder zuerst zum Lüften auffordern, bevor ein Luftentfeuchter eingeschaltet wird. Auf Wunsch bleibt es bei **Überwachung und Empfehlungen**, ganz ohne automatische Gerätesteuerung.

**Die Entscheidung liegt bei Ihnen.** Jeder Raum hat eigene Einstellungen. Jedes unterstützte Gerät verfügt über getrennte Betriebsarten, Regelverfahren, Sollwerte und Schutzgrenzen. Dass Sie ein Gerät auswählen, bedeutet nicht automatisch, dass HEM es steuern darf.

[Funktionen entdecken](#what-can-hem-do) · [Oberfläche ansehen](#see-hem-in-action) · [HEM installieren](#installation) · [Erste Schritte](#getting-started) · [Ausführliche Anleitung](../../docs/advanced-configuration.md) · [Alle Einstellungen (Englisch)](../../docs/settings-reference.md)

<a id="what-can-hem-do"></a>
## Was kann HEM?

| Situation | So unterstützt Sie HEM |
| --- | --- |
| **Niemand ist zu Hause** | HEM verwendet die für Abwesenheit festgelegten Sollwerte (Away), beachtet die Anwesenheitsregeln der einzelnen Räume und vermeidet den unnötigen Betrieb ausgewählter Geräte. |
| **Sie sind auf dem Heimweg** | Mit **Ankunft vorbereiten** können berechtigte automatische Regler vorübergehend die Home-Komfortwerte nutzen, obwohl noch niemand zurückgekehrt ist. |
| **Jemand schläft** | HEM kann Schlaf-Sollwerte verwenden, die Lüfterlautstärke reduzieren oder festgelegte Geräte ausgeschaltet lassen, wenn in allen belegten Räumen geschlafen wird. |
| **Ein Raum ist zu feucht** | HEM vergleicht Feuchtigkeit und Schimmelrisiko-Indikator mit Ihren Zielwerten, empfiehlt Lüften oder regelt einen dafür freigegebenen Entfeuchter automatisch beziehungsweise per PID. |
| **Es ist heiß und sonnig** | Vor dem Bewegen ausdrücklich freigegebener Rollläden oder Jalousien berücksichtigt HEM Raumtemperatur, Sonneneinstrahlung, Wetter und vorhandene Fensterkontakte. |
| **Die Außenluft ist günstiger** | Lüftungsempfehlungen berücksichtigen den Bedarf im Raum sowie Schadstoffe, Temperatur, Luftfeuchtigkeit, Wind und gegebenenfalls Pollen- oder Wetterwarnungen. |
| **Ein Heizgerät oder Heizkörperthermostat (TRV) reagiert nicht** | HEM zeigt den Ausfall beziehungsweise Wartezustand an, behält die Gerätekonfiguration bei und meldet geeignete Fehler, ohne fälschlich eine Wiederherstellung der Batterie- oder Relaisfunktion anzunehmen. |

Diese Beispiele sind keine verbindlichen Automatikregeln für jedes Zuhause. Die möglichen Aktionen hängen von Ihren Sensoren, den tatsächlichen Home-Assistant-Funktionen der Geräte und Ihren ausdrücklichen Freigaben ab.

<a id="explore-the-features"></a>
## Funktionen im Überblick

<a id="a-complete-home-dashboard"></a>
### Das ganze Zuhause auf einem Dashboard

Die HEM-Karte verschafft Ihnen einen Überblick, ohne dass Sie zwischen mehreren Integrationen wechseln müssen.

- Sehen Sie Außenbedingungen, Luftqualität und aktuelle Lüftungsempfehlungen.
- Vergleichen Sie alle überwachten Räume auf einen Blick: Temperatur, relative Luftfeuchtigkeit, AQI, PM2.5, Schimmelrisiko-Indikator, Helligkeit und weitere unterstützte Messwerte.
- Klappen Sie einzelne Räume auf, um Messwerte, Fenster und Türen, Klimageräte, aktive Regler, Wartegründe und bauphysikalische Schätzwerte zu sehen.
- Verfolgen Sie Verlauf und Trends, erkennen Sie die Sensoren hinter einem Durchschnitt und unterscheiden Sie fehlende Daten von tatsächlich gemessenen Werten.
- Gruppieren Sie Räume nach den in Home Assistant angelegten Etagen oder nutzen Sie eine einfache Raumliste, wenn keine Etagen vorhanden sind.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Einstellungen für Zuhause, Raum und Gerät getrennt

HEM trennt übergreifende Regeln von den Anforderungen einzelner Räume und Geräte.

| Einstellungsebene | Was Sie festlegen können |
| --- | --- |
| **Zuhause** | Außenwetter- und Luftqualitätssensoren, überwachte Räume, allgemeine Lüftungsgrenzen, Anwesenheit im Haushalt, Ankunftsvorbereitung und Benachrichtigungskanäle. |
| **Raum** | Temperatur- und Feuchtigkeitssensoren, Luftqualitätsgrenzen, Fenster- und Türkontakte, Anwesenheit und Schlafzustand, Komfortziele, Lüftung und Beschattung. |
| **Einzelnes Gerät** | Unterstützte Betriebsarten, Regelverfahren Automatic/Manual/PID, Sollwerte je Profil, Sensoren, leise Lüfterstufen, Mindestlaufzeiten, Stromversorgungsschutz, Verhalten bei offenen Fenstern und Fehlermeldungen. |

Die Einstellungen für Zuhause, Räume und Geräte sind in der Karte übersichtlich gruppiert und durchsuchbar. Wählen Sie **Basis**, **Erweitert** oder **Experten**, um den Umfang der angezeigten Einstellungen festzulegen. Basis enthält die alltäglichen Bedienelemente und die erforderliche Einrichtung. Erweitert ergänzt manuelle PID-Koeffizienten und detaillierte Anpassungen. Experten fügt spezielle Modelle und die Abstimmung der Geräteleistung hinzu. Jede Stufe umfasst auch die vorherigen Stufen. Wenn sich Ihre Home-Assistant-Installation ändert, können Sie die verfügbaren Quellen neu einlesen. <!-- HEM-I18N:levels -->


<a id="climate-control-and-pid-device-by-device"></a>
### Klimaregelung und PID für jedes Gerät

HEM unterstützt kompatible Home-Assistant-Geräte der Typen **climate**, **humidifier** und **fan**. Dazu können Heizungen, Klimaanlagen, Luftbe- und -entfeuchter sowie geeignete Geräte zur Luftzirkulation oder Luftreinigung gehören.

Für **jede tatsächlich unterstützte Betriebsart** legen Sie das Regelverfahren unabhängig fest:

| Verfahren | Bedeutung |
| --- | --- |
| **Existing** | Die bisherige Geräte- beziehungsweise Regelungssteuerung bleibt zuständig. |
| **Automatic** | HEM reagiert auf gemessenen Bedarf, situationsabhängige Sollwerte und die erteilten Freigaben. |
| **PID** | Rückgekoppelte proportional-integral-differenzielle Regelung, sofern Gerät und Messwerte sie unterstützen. |
| **Manual** | Steuerung über ausdrücklich unterstützte manuelle Befehle und Sollwerte. |
| **Off** | Der betreffende Regler bleibt ausgeschaltet, unter Beachtung der erforderlichen Schutz- und Rückmeldebedingungen. |

Beispielsweise kann eine Klimaanlage beim **Heizen PID** und beim **Kühlen Automatic** verwenden. Ein Luftentfeuchter kann eigene PID-Parameter, Zielwerte und Schaltzeiten besitzen. Geeignete Lüfter lassen sich ebenfalls per PID regeln, wenn für ihren Zweck passende Rückmeldungen vorliegen.

**PID ist keine pauschale Umgehung von Schutzregeln.** HEM bietet nur Verfahren an, die das konkrete Gerät, die Betriebsart und die zugehörigen Messungen unterstützen. Zu den erweiterten Optionen zählen Kalibrierung, abgestimmte Parameter je Betriebsart, Vorschläge zur adaptiven Anpassung, leiser Betrieb und unterstützte Lüfterstufen. Vorgeschlagene Änderungen müssen Sie bestätigen, sofern Sie keine ausdrücklich begrenzte automatische Anpassung aktiviert haben.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Komfort bei Anwesenheit, Sparbetrieb bei Abwesenheit

HEM kann zwischen den Sollwertprofilen **Comfort, Home, Away, Sleep und Eco** wählen. Ausschlaggebend sind die bestätigte Situation im Haushalt, die Informationen aus den Räumen und Ihre Einstellungen.

- **Home und Away:** Unterschiedliche Sollwerte für Heizung, Kühlung und Luftfeuchtigkeit bei bestätigter An- oder Abwesenheit.
- **Raumanwesenheit:** Ein geeignetes Gerät kann bei Bedarf immer, nur bei Anwesenheit oder nur bei Abwesenheit im zugehörigen Raum laufen.
- **Sleep:** Nacht-Sollwerte und leisere Lüftereinstellungen. Ein ausgewähltes Gerät kann ausgeschaltet bleiben, solange in allen belegten Räumen geschlafen wird.
- **Eco:** Energieeffizientere Sollwerte, wo Sie diese hinterlegt haben. Eine geschlossene Innentür kann unter zusätzlichen Schutzbedingungen in eine Eco-Regel einfließen, wenn der Raum nachweislich leer ist. Allein eine geschlossene Tür beweist keine vollständige Abtrennung.
- **Aufwachen vorbereiten:** Anhand einer konfigurierten nächsten Weckzeit kann HEM den automatischen Schlafbetrieb rechtzeitig beenden, damit geeignete Geräte reagieren können.

Fehlen verlässliche Angaben zur Anwesenheit, Geräteverfügbarkeit oder anderen erforderlichen Voraussetzungen, schaltet HEM ein automatisches Gerät nicht einfach unter der Annahme ein, dass dies sicher sei.

<a id="prepare-your-environment-before-you-arrive"></a>
### Räume vor der Rückkehr vorbereiten

**Ankunft vorbereiten** ist eine zeitlich begrenzte Aktion für ein nachweislich abwesendes Zuhause (Away). Sie können sie über die Kartenüberschrift oder das HEM-Home-Gerät auslösen.

Dabei verwendet HEM vorübergehend die eingestellten **Home-Sollwerte** für dafür geeignete Automatic-/PID-Regler. So können Räume bereits vor Ihrer Rückkehr aufgeheizt, gekühlt oder hinsichtlich der Feuchtigkeit angepasst werden. Vorübergehend kann auch ein Regler zugelassen werden, der normalerweise nur bei Raumanwesenheit läuft, **allerdings nur, wenn die Erlaubnis zur physischen Gerätesteuerung bereits besteht**.

Die Vorbereitung ist kein Befehl, alle Geräte einzuschalten. Es müssen tatsächlich Regelbedarf, gültige Sensordaten und die nötigen Freigaben vorliegen. Fensterbedingungen, Mindest-Ein- und -Ausschaltzeiten und Schutzfunktionen bleiben gültig. Die Aktion endet bei Ihrer Ankunft, nach Abbruch oder wenn die Zeit abgelaufen ist. Ein Neustart von Home Assistant beginnt die Laufzeit nicht erneut in voller Länge.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Lüftungsempfehlungen, Fenster, Türen und Beschattung

HEM stellt gegenüber, **was ein Raum benötigt** und **ob die Außenluft dabei helfen kann**.

- Empfehlungen zum Öffnen oder Schließen von Fenstern beruhen auf Innenmessungen sowie Außenfeuchte, Schadstoffen, Temperatur, Wind, Wetterwarnungen und optionalen Pollendaten.
- Der AQI-Index ist optional. Eine nicht konfigurierte Anbieterskala wird als unvollständige Datengrundlage angezeigt; sie allein verhindert weder das Lüften noch begründet sie eine Aufforderung zum Fensterschließen. Gültige Schadstoffmessungen und tatsächlich bedenkliche AQI-Werte mit korrekt zugeordneter Skala werden weiterhin berücksichtigt. <!-- HEM-I18N:aqi -->
- Ausgewählte Fenster- und Türkontakte helfen dabei, die Raumsituation einzuschätzen. Ein unbekannter Kontaktzustand wird nicht einfach als „geschlossen“ gewertet.
- Balkon- oder Terrassentüren mit der Home-Assistant-Binärsensorklasse `door` oder `opening` können Sie optional als **Fensterkontakte** einbeziehen. Sie erscheinen in der Fensterauswahl des Raums, werden aber **nie automatisch vorausgewählt**. Die normale Türüberwachung bleibt davon unabhängig. <!-- HEM-I18N:balcony -->
- Auf Wunsch fordert HEM vor dem Start eines unterstützten automatischen Geräts zunächst zum Lüften auf. Nach der eingestellten Wartezeit kann die normale Regelung gegebenenfalls fortgesetzt werden.
- Türinformationen fließen in die Einschätzung von Raumgrenzen, Lüftungshinweisen und optionalen, abgesicherten Eco-Regeln ein.
- Freigegebene Rollläden, Jalousien und andere Beschattungssysteme lassen sich anhand geeigneter Fenster-, Temperatur-, Wetter- und Sonnenstandsdaten sowie optionaler Helligkeitsmessungen steuern.

Für Lüftungsempfehlungen brauchen Sie keine elektrisch steuerbaren Fenster. **HEM öffnet Fenster nicht selbstständig**, nur weil frische Luft hilfreich wäre.

<a id="humidity-mold-indication-and-air-quality"></a>
### Luftfeuchtigkeit, Schimmelrisiko und Luftqualität

HEM führt unterstützte Messwerte wie **Temperatur, Luftfeuchtigkeit, CO₂, Feinstaub, VOC, AQI und Helligkeit** zusammen. Welche davon verfügbar sind, hängt von den Sensoren Ihrer Home-Assistant-Installation ab.

Der **Schimmelrisiko-Indikator** schätzt die Feuchtebedingungen an einer kühlen Oberfläche anhand der Raum- und Außentemperatur sowie einer Kalibrierungsmessung. Bei richtiger Einrichtung kann dieser Wert den wirksamen Sollwert einer geeigneten automatischen Luftfeuchtigkeitsregelung beeinflussen.

**Der Indikator ist eine Schätzung und kein Sensor für Schimmel oder Sporen.** Fehlende oder veraltete Messwerte dürfen keine neuen, auf dieser Schätzung beruhenden Gerätebefehle auslösen.

<a id="announcements-diagnostics-and-protection"></a>
### Benachrichtigungen, Diagnose und Schutz

Empfehlungen und Warnungen können über Home-Assistant-Benachrichtigungen, TTS/Medienwiedergabe oder den **Announcement Hub** ausgegeben werden. Optional kann KI die Formulierung verständlicher gestalten. **Die physische Geräteentscheidung bleibt dabei deterministisch** und wird nicht von der KI getroffen.

Zusätzliche Gerätefunktionen umfassen:

- Mindest-Ein- und -Ausschaltzeiten, maximale Betriebsdauer und die unterstützte Ansteuerung externer Netzschalter.
- Sperren aufgrund von Fenstern oder Anwesenheit, Behandlung manueller Eingriffe sowie Prüfung der Rückmeldung nach Gerätebefehlen.
- Meldung von Gerätefehlern und Nichtverfügbarkeit mit einzeln einstellbarem Benachrichtigungsverhalten.
- Optionale Überwachung nach einem OFF-Befehl, wenn Anzeichen dafür bestehen, dass die Heizung dennoch weiterläuft; mit abgesicherten Prüfungen und begrenzten Wiederholungsversuchen.
- Verständliche Wartegründe, Betriebszustände und Informationen zur Verfügbarkeit der Datenquellen, um Probleme vor dem Aktivieren weiterer Automatiken untersuchen zu können.

**Schutzgrenzen gelten auch bei abgeschalteten Benachrichtigungen.** Eine erfolgreich gesendete Anweisung ist noch kein Beweis dafür, dass das Gerät sie tatsächlich ausgeführt hat.

<a id="see-hem-in-action"></a>
## HEM in der Praxis

Die folgenden englischsprachigen Abbildungen verwenden Beispieldaten und fiktive Räume. Sie zeigen die Bedienoberfläche, nicht die Live-Daten eines bestimmten Haushalts.

<a id="home-at-a-glance"></a>
### Das Zuhause auf einen Blick

Lüftungsempfehlungen, Wetterbedingungen und alle überwachten Räume erscheinen auf einer Karte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.png" alt="HEM-Übersicht mit Lüftungsempfehlungen und Umgebungswerten aus fünf Räumen" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Einen Raum im Detail anzeigen

Sehen Sie Luftqualität, Schimmelrisiko-Indikator, Anwesenheit, Fensterstatus, Klimaregler und die Gründe für deren Entscheidungen.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.png" alt="Aufgeklappte Badansicht mit Messwerten und unabhängigen Gerätesteuerungen" width="760">
</p>

<a id="home-settings"></a>
### Einstellungen für das Zuhause

Konfigurieren Sie Außenquellen, Anwesenheit, überwachte Räume, Lüftungsgrenzen, Ankunftsvorbereitung und Benachrichtigungen.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM-Hauseinstellungen mit durchsuchbaren Gruppen und Quellenverwaltung" width="900">
</p>

<a id="room-settings"></a>
### Raumeinstellungen

Wählen Sie je Raum Sensoren, Sollwerte, Anwesenheitsregeln, Türen, Fenster, Lüftung, Beschattung und Schutzfunktionen.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Gruppierte HEM-Raumeinstellungen für Sensoren, Geräte, Schlafzustand und Fenster" width="760">
</p>

<a id="device-settings"></a>
### Geräteeinstellungen

Passen Sie Regelverfahren, PID, leisen Betrieb, Zeitvorgaben und Fehlermeldungen für jedes Gerät getrennt an.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="HEM-Geräteeinstellungen für Regelung, PID, Stromschutz und Benachrichtigungen" width="900">
</p>

<a id="getting-started"></a>
## Erste Schritte

1. **Räume zuordnen.** Legen Sie in Home Assistant Bereiche (Areas) an oder prüfen Sie die bestehenden und ordnen Sie Sensoren und Geräte korrekt zu.
2. **Überwachung auswählen.** Fügen Sie HEM hinzu, wählen Sie die gewünschten Räume und prüfen Sie vorgeschlagene Temperatur-, Feuchtigkeits-, Fenster-, Luftqualitäts- und Gerätequellen. Nicht benötigte Gruppen können leer bleiben.
3. **Gemeinsame Daten festlegen.** Wählen Sie verfügbare Außenwetter- und Luftqualitätsquellen, Informationen zur Anwesenheit im Haushalt und bei Bedarf Empfänger für Benachrichtigungen.
4. **Karte hinzufügen.** Öffnen Sie ein Dashboard im Bearbeitungsmodus und fügen Sie die Karte **Home Environment Manager** hinzu. Beginnen Sie mit der Überwachung, den Messwerten und den Lüftungsempfehlungen.
5. **Steuerung gezielt freigeben.** Öffnen Sie einen Raum, wählen Sie ein geeignetes Gerät, prüfen Sie dessen Regler und aktivieren Sie Automatic oder PID ausdrücklich nur für die gewünschten Betriebsarten.

**Nicht jeder Raum benötigt ein smartes Gerät.** Nutzen Sie zuerst die vorhandenen Sensoren und aktivieren Sie die automatische Steuerung schrittweise, Gerät für Gerät.

<a id="add-the-card-manually"></a>
### Karte manuell hinzufügen

Normalerweise registriert die Integration ihre Lovelace-Karte selbst. Falls Sie YAML bevorzugen:

~~~yaml
type: custom:home-environment-manager-card
~~~

Wenn Ihre Home-Assistant-Installation mehrere HEM-Empfehlungssensoren besitzt, müssen Sie gegebenenfalls die passende **Entität (entity)** angeben:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Eine ausführliche Anleitung zu Raumquellen, Profilen, PID-Einstellungen, Fensterregeln, Ankunftsvorbereitung, Schimmelkalibrierung, Beschattung und Benachrichtigungen finden Sie im [Konfigurationshandbuch](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### Mit HACS (Home Assistant Community Store)

1. Öffnen Sie **HACS** in Home Assistant.
2. Fügen Sie **https://github.com/Chreece/HA-Home-Environment-Manager** gegebenenfalls als **benutzerdefiniertes Repository (Custom Repository)** in der Kategorie **Integration** hinzu.
3. Suchen Sie nach **Home Environment Manager** und installieren Sie die Integration.
4. Starten Sie **Home Assistant** neu, damit die Integration geladen wird.
5. Öffnen Sie **Einstellungen → Geräte & Dienste → Integration hinzufügen**, suchen Sie nach **Home Environment Manager** und schließen Sie die Einrichtung ab.

<a id="manual-installation"></a>
### Manuelle Installation

Kopieren Sie den Ordner **custom_components/environment_manager** aus dem Repository in das passende Verzeichnis **custom_components** Ihrer Home-Assistant-Konfiguration. Behalten Sie den Ordnernamen **environment_manager** bei. Starten Sie Home Assistant neu und fügen Sie die Integration über **Einstellungen → Geräte & Dienste** hinzu.

Behalten Sie bei späteren Updates Ihren vorhandenen HEM-Eintrag und dessen Einstellungen. Falls die Karte nicht sofort aktualisiert aussieht, laden Sie das Dashboard im Browser neu.

<a id="common-questions"></a>
## Häufige Fragen

**Kann ich HEM nutzen, ohne ihm die Steuerung meiner Geräte zu erlauben?**

Ja. Überwachung, Messwerte, Lüftungsempfehlungen, Verlauf und viele Umgebungsindikatoren funktionieren auch ohne aktive Gerätesteuerung.

**Steuert HEM alle gefundenen Geräte automatisch?**

Nein. Sie wählen die Geräte und die Regelverfahren für die unterstützten Betriebsarten ausdrücklich aus. Welche Funktionen möglich sind, hängt weiterhin von den Gerätefähigkeiten und geeigneten Sensordaten ab.

**Unterstützt jedes Gerät PID?**

Nein. PID steht nur für **geeignete** Heiz-, Kühl-, Feuchtigkeits- und Lüfterregelungen zur Verfügung, wenn passende Fähigkeiten und verlässliche Rückmeldungen vorhanden sind. HEM ergänzt keine künstliche PID-Regelung für nicht unterstützte Betriebsarten.

**Kann ich für jeden Raum eigene Regeln festlegen?**

Ja. Anwesenheit, Schlafzustand, Datenquellen, Sollwerte und manche Sicherheitseinstellungen können je Raum unterschiedlich sein. Auch jedes Gerät besitzt eigene Betriebs- und Schutzoptionen.

**Kann HEM mein Zuhause während meiner Abwesenheit vorbereiten?**

Ja. Mit **Ankunft vorbereiten** können berechtigte, zuvor freigegebene automatische Regler vorübergehend Home-Sollwerte nutzen. Schutzfunktionen werden nicht umgangen, und das Erreichen der Zielwerte ist nicht garantiert.

**Öffnet HEM meine Fenster automatisch, wenn es Lüften empfiehlt?**

Nein. Eine Lüftungsempfehlung erklärt nur, wann Lüften sinnvoll sein kann. Automatische Bewegungen sind eine separate, ausdrücklich freizugebende Funktion für geeignete Beschattungssysteme und unterliegen eigenen Sicherheitsprüfungen.

**Was passiert, wenn ein Sensor oder Gerät nicht verfügbar ist?**

HEM unterscheidet unbekannte Zustände von echten Messwerten, behält Reglerdaten nach Möglichkeit bei und zeigt Wartegründe sowie Diagnoseinformationen. Für automatische Eingriffe sind weiterhin gültige aktuelle Daten und die notwendigen Freigaben erforderlich.

<a id="help-and-troubleshooting"></a>
## Hilfe und Fehlerbehebung

Wenn etwas nicht wie erwartet funktioniert, prüfen Sie beim jeweiligen Raum oder Regler den **Grund (Reason)**, die **Diagnose (Diagnostics)**, die Verfügbarkeit der Quellen und das eingestellte Regelverfahren. Das [Konfigurationshandbuch](../../docs/advanced-configuration.md) erläutert typische Wartezustände, Anwesenheitsregeln, PID-Voraussetzungen, Fensterbedingungen und Probleme mit Geräterückmeldungen.

Bei reproduzierbaren Fehlern [erstellen Sie ein GitHub-Issue](https://github.com/Chreece/HA-Home-Environment-Manager/issues). Beschreiben Sie das erwartete und tatsächliche Verhalten, relevante Raum- und Geräteeinstellungen sowie die Schritte zum Nachstellen. Entfernen Sie persönliche Daten aus Protokollen und Bildern.

Beiträge und Verbesserungen sind willkommen. Weitere Hinweise stehen in [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Unterstützung und Lizenz

Wenn HEM Ihnen hilft, können Sie [Chreece auf Ko-fi unterstützen](https://ko-fi.com/chreece).

Veröffentlicht unter der [MIT-Lizenz](../../LICENSE).
