<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Home Milieu Manager - slimmere luchtkwaliteit, comfort, ventilatie en klimaatbeheersing" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Ondersteuning van de Commissie Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <strong>Nederlands</strong> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Milieu Manager

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>De hele omgeving van je huis, in één Home Assistant Een kaartje.</strong></p>

**HEM helpt je huis om de omgeving te begrijpen en te reageren op wat elke kamer eigenlijk nodig heeft.** Het brengt je Home Assistant de luchtkwaliteit te controleren, nuttige ventilatieadvies te ontvangen, comfort te beheren en de uitrusting van uw keuze te automatiseren.

Bijvoorbeeld: HEM Het kan de verwarming verminderen terwijl iedereen weg is, geselecteerde kamers voorbereiden voordat je terugkomt, een ander vochttarget gebruiken terwijl je slaapt, of vragen om een raam te openen voordat je een ontvochtmiddel gebruikt. **toezicht houden en aanbevelen**, zonder enige apparatuur te controleren.

**Jij blijft de baas.** Elke kamer heeft zijn eigen instellingen, elk ondersteunde apparaat heeft zijn eigen controller, werkwijze, doelen en veiligheidsgrenzen. HEM neemt nooit aan dat het selecteren van een apparaat hem toestemming geeft om dat apparaat te bedienen.

[Ontdek de kenmerken](#what-can-hem-do) · [Zie de interface](#see-hem-in-action) · [Installeer HEM](#installation) · [Maak je huis klaar.](#getting-started) · [Gedetailleerde gids](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Wat kan HEM - Ja, dat doen we.

| Uw situatie | Hoe? HEM kan helpen |
| --- | --- |
| **Het huis is leeg .** | Schakel naar wegdoelen, respecteer de aanwezigheidsregels van elke kamer en vermijd onnodig gebruik van geselecteerde apparatuur. |
| **Je bent op weg naar huis.** | Druk **Bereid je voor op aankomst.** Het gebruik van thuiscomfortdoelstellingen voor in aanmerking komende automatische controllers is tijdelijk mogelijk, ook al is iedereen nog weg. |
| **Iemand slaapt.** | Gebruik slaapdoelwitten, verminder het geluid van de ventilators of houd de geselecteerde apparaten uitgeschakeld terwijl elke kamer slaapt. |
| **Een kamer is vochtig .** | Vergelijk de vochtigheids- en schimmelindicatie met de doelen, stel een nuttige ventilatie voor of bedien een goedgekeurde ontvochtingsmiddel met behulp van automatische of PID De controle. |
| **Het is heet en zonnig.** | Beoordeel de kamertemperatuur, het zonlicht, het weer en de aangesloten venstercontacten voordat je de gekozen tinten verplaatst. |
| **De buitenlucht ziet er beter uit .** | Aanbeveling van ventilatie met behulp van binnenvraag, buitenvervuiling, temperatuur, vochtigheid, wind en beschikbare stuifmeel- of weerswaarschuwingen. |
| **Een verwarmer of TRV stopt met reageren** | Toon de niet-beschikbare of wachttoestand, bewaren de geconfigureerde controller en melden de gebrekkingen van het ondersteunde apparaat, zonder aan te nemen dat een batterij of relais is hersteld. |

Dit zijn voorbeelden, niet acties die HEM De resultaten zijn afhankelijk van de geselecteerde sensoren. Home Assistant capaciteiten en uw opt-in-instellingen.

<a id="explore-the-features"></a>
## Ontdek de kenmerken

<a id="a-complete-home-dashboard"></a>
### Een compleet thuis dashboard

De HEM de kaart geeft u een nuttig overzicht zonder verschillende integraties te openen.

- Bekijk de buitenomstandigheden, de luchtkwaliteit en of ventilatie wenselijk is.
- Vergelijk alle gemonitorde kamers op één oogopslag: temperatuur, relatieve vochtigheid, AQI, PM2,5, schimmelindicatie, licht en andere ondersteunde metingen.
- Vergroten van de ruimte voor gedetailleerde metingen, informatie over ramen en deuren, klimaatstatus, actieve controllers, redenen voor wachten en bouwfysica-schattingen.
- Bekijk de geschiedenis en de trends, kijk welke sensoren bijgedragen hebben aan een gemiddelde en onderscheid de ontbrekende lezen van gemeten waarden.
- Groepskamers per daadwerkelijke Home Assistant een vloer, of gebruik een eenvoudige kamerlijst wanneer je geen vloeren hebt.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Verschillende instellingen voor het huis, elke kamer en elk apparaat

HEM Het is een belangrijk onderdeel van de Europese Unie.

| Instellingenniveau | Wat u kunt configuren |
| --- | --- |
| **Huis** | Het buitenweer en vervuilingsbronnen, gecontroleerde kamers, wereldwijde ventilatielimieten, de aanwezigheid van huishoudens, de voorbereiding op aankomst en de aflevering van aankondigingen. |
| **Kamer** | Inrichtingstemperatuur en vochtigheidsbronnen, luchtkwaliteitsdrempels, venster- en deurcontacten, slaap- en bezettingsgedrag, kamerspecifieke comfortdoelstellingen, ventilatie- en schaduwkeuzes. |
| **Individueel apparaat** | De beschikbare besturingsmodus, automatisch/handmatig/PID methode, doelwitten per profiel, sensoren, stilte ventilatorinstellingen, minimale werktijden, stroombeschermingen, venstergedrag en berichten over apparaatfouten. |

Alle drie de niveaus zijn toegankelijk via gegroepeerde, zoekbare instellingen in de kaart. Home Assistant instellingswijzigingen.

<a id="climate-control-and-pid-device-by-device"></a>
### Klimaatcontrole en PID, apparaat voor apparaat

HEM kan werken met compatibele Home Assistant **klimaat**, **bevochtigingsmiddel** en **ventilator** apparaten, waaronder verwarming, koeling, ontvochting, vochting en ondersteunende luchtcirculatie- of luchtreinigingsapparatuur.

Voor elk **ondersteunde fysieke bedieningsmodus**, de controlemethode onafhankelijk kiezen:

| Metode | Wat het betekent |
| --- | --- |
| **Bestaande** | Laat de besturing met het bestaande controllerpad. |
| **Automatisch** | Volg . HEMde gemeten vraag, op situatie gebaseerde doelstellingen en vergunningen. |
| **PID** | Gebruik op feedback gebaseerde proportieve, integrale en afgeleide besturing waar het apparaat en de meting het ondersteunen. |
| **Handleiding** | Controle via expliciete ondersteunde verzoeken en doelstellingen. |
| **Af .** | Houd die controller uitgeschakeld, onder voorbehoud van fysieke bescherming en feedback vereisten. |

Een airconditioner kan bijvoorbeeld **PID voor verwarming** en **Automatisch voor koeling**Een ontvochtmiddel kan zijn eigen PID de afmeting, de doelstellingen en de cyclustijd. PID wanneer passende feedback en doel-specifieke controle beschikbaar zijn.

PID is **- Niet** een universele overschrijving: HEM De voorgestelde opties omvatten per-mode afstemming en kalibratie, suggereerde/adaptieve aanpassingen, stille werking en ondersteunde gestage ventilatorinstellingen.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Comfortabel als je thuis bent, economisch als je weg bent

HEM kan kiezen tussen **Comfort, thuis, weg, slapen en milieu** Doelstellingen gebaseerd op de situatie van het huishouden, het bewijs van de kamer en uw expliciete keuzes.

- **Thuis en weg:** Gebruik verschillende doelstellingen voor verwarming, koeling en luchtvochtigheid, afhankelijk van de geverifieerde aanwezigheid in het huis.
- **Kamer aanwezigheid:** Voer een in aanmerking komend apparaat altijd uit wanneer er vraag is, alleen terwijl de kamer is bezet, of alleen terwijl de kamer leeg is.
- **Slaap:** Een geselecteerd apparaat kan uitgeschakeld blijven wanneer alle bezette kamers slapen.
- **ECO:** Een gesloten binnendeur kan deelnemen aan een beschermd ecologisch beleid wanneer de ruimte leeg is gecontroleerd en andere voorwaarden worden voldaan; een gesloten deur alleen bewijst niet dat de kamer geïsoleerd is.
- **Ontwakingsvoorbereiding:** Gebruik een geconfigureerde volgende alarmbron om automatische slaap vóór het alarm te laten vallen en de in aanmerking komende apparaten tijd te geven om te reageren.

Indien het gebruik, de beschikbaarheid van het apparaat of andere vereiste bewijzen onzeker zijn, HEM niet zomaar ervan uitgaat dat het veilig is om een automatisch apparaat te starten.

<a id="prepare-your-environment-before-you-arrive"></a>
### Bereid uw omgeving voor voordat u aankomt

**Bereid je voor op aankomst.** Het is een tijdelijke actie voor een bevestigde weg huis. HEMHet is een thuisapparaat.

HEM tijdelijk de geconfigureerde **Huisdoelstellingen** tot in aanmerking komende Automatic/PID de beheerders, zodat de kamers kunnen beginnen met het verwarmen, afkoelen of instellen van de vochtigheid voordat u terugkeert. **alleen wanneer hij al de nodige fysieke controlevergunning heeft**.

Voorbereiding is geen opdracht om alles aan te zetten. Apparaten hebben nog steeds echte vraag, geldige sensoren en toestemming nodig, en moeten vensters, minimale ON/OFF-tijden en hun eigen bescherming respecteren. De actie eindigt wanneer iemand aankomt, je deze annuleert of de geconfigureerde timer verstrijkt. Home Assistant herstart niet de volledige timer opnieuw opstarten.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Advies voor ventilatie, ramen, deuren en schaduw

HEM vergelijkt **wat een kamer nodig heeft** met **of buitenlucht kan helpen**.

- Aanbeveling van het openen of sluiten van ramen met behulp van de huidige binnenmetingen, luchtvochtigheid, vervuiling, temperatuur, wind, weerwaarschuwingen en de optieve pollencontext.
- Gebruik geselecteerde venster- en deurcontacten om de kameromstandigheden te verklaren en vermijd een onbekend contact als gesloten te behandelen.
- Als optie wordt gevraagd om een venster te proberen te openen voordat een ondersteund automatisch apparaat wordt gestart, en vervolgens de normale besturing voort te zetten nadat de geconfigureerde reactie wacht indien nodig.
- Gebruik deurinformatie voor ruimtegrensbewustzijn, ventilatievoorzorgingen en optioneel beschermd ecologisch gedrag.
- Beheer van de ingeschakelde sluizen, blinds en schaduwen met behulp van geschikt venster, temperatuur, weer, zonsopgang en optionele belichtingsbewijs.

HEM Het is een van de belangrijkste factoren die de Commissie in haar advies over de toepassing van de richtlijn heeft aangetoond.

<a id="humidity-mold-indication-and-air-quality"></a>
### Vochtigheid, schimmelindicatie en luchtkwaliteit

HEM Combineert ondersteunde lezen zoals: **temperatuur, vochtigheid, CO2, deeltjes, VOC, AQI en verlichting** De beschikbare afmetingen zijn afhankelijk van wat uw Home Assistant De installatie is voorzien.

Het is **schimmelindicatie** de vochtomstandigheden op een koud oppervlak op basis van kamertemperatuur en buitentemperatuur en een kalibreringsmeting berekent.

**De vormindicatie is een schatting, geen schimmel- of spore-detector.** Ontbrekende of verouderde sensorgegevens kunnen geen nieuw op vorm gebaseerd apparaatbevel rechtvaardigen.

<a id="announcements-diagnostics-and-protection"></a>
### Aankondigingen, diagnose en bescherming

U kunt relevante aanbevelingen en waarschuwingen sturen via geconfigureerde Home Assistant meldingen, TTS/media-spelers of **Kennisgeving Hub**AI kan de manier waarop een bericht wordt geformuleerd veranderen; HEMDe beslissingen van de fysieke controle blijven deterministisch.

HEM omvat ook beschermings- en diagnostiekprogramma's die specifiek voor het apparaat zijn:

- Minimaal aan- en uit-tijd, maximale werktijdinstellingen en ondersteunde bediening van externe stroomschakelaars.
- Venster- en bezettingsbeperkingen, handmatige overschrijving en controle van het inheemse commando.
- Fouten en niet beschikbare apparaatrapporten, met een keuze van meldingsgedrag voor elk apparaat.
- Een optionele bewakingshond na de sluiting voor vermoedelijke verdere verwarming na een OFF-commando, met bewakend toezicht en beperkte herstelpogingen.
- Klare redenen om te wachten, de huidige exploitatiestatus en de beschikbaarheid van de bron, zodat je kunt onderzoeken voordat je meer controle mogelijk maakt.

**De veiligheidsgrenzen blijven van kracht ook wanneer een waarschuwing uitgeschakeld is.** HEM een succesvolle commando-uitzending nooit als bewijs beschouwt dat een apparaat fysiek heeft gereageerd.

<a id="see-hem-in-action"></a>
## Zie je dat ? HEM in actie

Deze illustraties in het Engels maken gebruik van steekproefkamers en metingen. Ze tonen de interface in plaats van live data van een bepaald huis te tonen.

<a id="home-at-a-glance"></a>
### Thuis in een oogopslag

Ontdek ventilatieadvies, weersomstandigheden en de status van elke gecontroleerde kamer in één kaart.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM Home dashboard met ventilatieadvies en milieulezen in vijf kamers" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Vergroot de ruimte voor alle details

Controleer de luchtkwaliteit, de schimmelindicatie, de aanwezigheid, de toestand van het raam, de klimaatbeheerders en de uitleg voor elke beslissing.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Uitgebreid badkamer dashboard met aflezen en onafhankelijke apparaatcontrollers" width="760">
</p>

<a id="home-settings"></a>
### Home-instellingen

Beheer van buitenbronnen, aanwezigheid in het hele huis, gecontroleerde ruimtes, ventilatiegrenzen, voorbereiding en meldingen.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Huisinstellingen met zoekgroepen en bron- en kamerbeheer" width="900">
</p>

<a id="room-settings"></a>
### Ruimteinstellingen

Kies voor wat voor elke kamer belangrijk is: eigen sensoren, doelen, bezetting, deuren, ramen, ventilatie, schaduw en beveiliging.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Groepen HEM kamerinstellingen voor sensoren, toestellen, slaap, ramen en bescherming" width="760">
</p>

<a id="device-settings"></a>
### Installatie van het apparaat

Een apparaat fijn afstemmen zonder de anderen te wijzigen, met inbegrip van ondersteunde besturingsmethoden, PID, stille werking, timing en foutmelding.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Groepen HEM instellingen van het apparaat met besturing, PID, elektriciteitsbescherming en meldingen" width="900">
</p>

<a id="getting-started"></a>
## Beginnen

1. **Organiseer je kamers.** In Home Assistant, uw gebieden te maken of te controleren en de juiste sensoren en apparaten aan elk toe te wijzen.
2. **Kies wat je moet monitoren.** Voeg toe HEMSelecteer de kamers waar je om geeft en kijk de aanbevolen temperatuur, vochtigheid, raam, luchtkwaliteit en apparaatbronnen.
3. **Configureer gedeelde informatie.** Selecteer beschikbare weer- en luchtkwaliteitbronnen, bewijs van huishoudelijke bezetting en eventuele aankondigingsbestemmingen die u wilt.
4. **Voeg de kaart toe.** Open een dashboard in bewerkingsmodus en voeg de **Home Milieummanager** Begin met kamermonitoring, lezen en ventilatieadvies.
5. **Beheersing alleen als het nuttig is.** Maak een kamer open, kies een ondersteund apparaat, bekijk de controller en selecteer uitdrukkelijk PID voor de modus die je wilt HEM om te opereren.

- Ja, dat weet je. **- Niet** Begin met de sensoren die je hebt, en introduceer automatische besturing één apparaat per keer.

<a id="add-the-card-manually"></a>
### Voeg de kaart handmatig toe

De integratie registreert normaal een eigen Lovelace-kaart.

~~~yaml
type: custom:home-environment-manager-card
~~~

Als uw Home Assistant installatie heeft meer dan één HEM aanbevelingssensor, moet u misschien de juiste **entiteit** uitdrukkelijk:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Voor stapsgewijze instructies over kamerbronnen, profielen, PID de opstelling, het vensterbeleid, de voorbereiding, de schimmelkalibratie, de zonne- [gedetailleerde configuratiegids](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installatie

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Gemeenschapswinkel

1. Open . **HACS** in Home Assistant.
2. Voeg toe **https://github.com/Chreece/HA-Home-Environment-Manager** als een **aangepaste opslagplaats** In de **Integratie** categorie indien deze niet al is vermeld.
3. Zoek **Home Milieummanager** en installeer het.
4. Start opnieuw **Home Assistant** om de integratie op te laden.
5. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen**, zoeken naar **Home Milieummanager** En de installatie afmaken.

<a id="manual-installation"></a>
### Handmatige installatie

Kopieer de gegevens van de bewaarplaats **custom_components/environment_manager** folder in de matching **custom_components** Directory in uw Home Assistant Configuratie, behoud van de directory naam **environment_manager**Start opnieuw . Home Assistant en de integratie toevoegen via **Instellingen → Apparaten & diensten**.

Voor latere installatiewijzigingen, houd uw bestaande HEM integratie-invoer en -instellingen. het dashboard in uw browser opnieuw laden als het uiterlijk van de kaart niet onmiddellijk wordt vernieuwd.

<a id="common-questions"></a>
## Algemene vragen

**Mag ik het gebruiken ? HEM zonder dat ik hem de controle over mijn apparaten geef?**

Ja, monitoring, metingen, ventilatieadvies, geschiedenis en vele milieuaanduidingen werken zonder dat het apparaat geactiveerd wordt.

**Will , HEM Automatisch controleren van elk apparaat dat het ontdekt?**

Je selecteert de fysieke apparaten die je wilt beheren en selecteert expliciet de besturingsmethode voor ondersteunde modus.

**Ondersteunt elk apparaat PID?**

- Nee, dat is niet waar. HEM steun PID voor **in aanmerking komende** verwarming, koeling, luchtvochtigheid of ventilator-controlepaden wanneer het apparaat en de geselecteerde metingen de nodige mogelijkheden en feedback bieden. PID De controle.

**Kan ik elke kamer verschillende regels geven?**

Ja, de bezettingsomstandigheden, het slaapgedrag, de bronnen, de doelen en bepaalde veiligheidsvoorkeuren kunnen per kamer verschillen, terwijl elk fysiek apparaat zijn eigen bedienings- en beschermingsinstellingen heeft.

**Kan HEM Ik moet mijn huis bereiden terwijl ik weg ben.**

- Ja, dat is het. **Bereid je voor op aankomst.** Het is de mogelijkheid om voor een beperkte periode in aanmerking komende, reeds geautoriseerde automatische controllers gebruik te maken van huisdoelstellingen.

**Maak een aanbeveling voor ventilatie mijn ramen open?**

Automatische beweging is een aparte, opt-in functie voor in aanmerking komende ondersteunde tinten of dekens, onderworpen aan hun eigen veiligheidscontroles.

**Wat als een sensor of een apparaat niet beschikbaar wordt?**

HEM het onderscheid maakt tussen onbekende gegevens en werkelijke lezen, waar mogelijk de informatie van de controller bewaart en de redenen voor wachten en de diagnose blootlegt.

<a id="help-and-troubleshooting"></a>
## Hulp en probleemoplossing

Als er iets mis lijkt, controleer de betreffende kamer of de controleur. **De reden**, **Diagnostiek**De Commissie heeft de Commissie de nodige informatie verstrekt over de beschikbaarheid van de [gedetailleerde configuratiegids](../../docs/advanced-configuration.md) de algemene wachttoestanden, het aanwezigheidsbeleid, PID aanmerking komendheid, vensters en probleemoplossing op het apparaat-respons.

Voor een reproduceerbaar probleem, [open een GitHub Uitgifte](https://github.com/Chreece/HA-Home-Environment-Manager/issues) met het verwachte gedrag, het daadwerkelijke gedrag, de relevante ruimte/apparaatinstellingen en de stappen om te reproduceren.

De bijdragen en verbeteringen zijn welkom. [Contributie.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Ondersteuning en vergunning

Indien HEM is nuttig voor je, je kunt [Ondersteuning aan Griekenland op Ko-fi](https://ko-fi.com/chreece).

Verdeel onder de [MIT-licentie](../../LICENSE).
