<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Hjem Miljøchef - smartere luftkvalitet, komfort, ventilation og klimakontrol" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Støtte til krisen Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <strong>Dansk</strong> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Hjemmiljøleder

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Hele dit hjems miljø, i en Home Assistant Kortet.</strong></p>

**HEM hjælper dit hjem med at forstå omgivelserne og reagere på hvad hvert værelse rent faktisk har brug for.** Det bringer din Home Assistant Det er vigtigt, at der tages højde for, at det er muligt at få en bedre ventilationstilpasning, at det er muligt at kontrollere luftkvaliteten, at få nyttige ventilationsrådgivning, at styre komforten og at automatisere det udstyr, du vælger.

For eksempel: HEM kan reducere opvarmningen, mens alle er væk, forberede udvalgte værelser, før du kommer tilbage, bruge et andet luftfugtsmål, mens du sover, eller bede dig åbne et vindue, før du kører en affukter. **overvåge og anbefale**, uden at kontrollere nogen enhed.

**Du holder styret.** Hvert værelse har sine egne indstillinger, og hvert støttet apparat har sin egen kontroller, driftstilstande, mål og sikkerhedsgrænser. HEM aldrig antager, at det ved at vælge en enhed giver den tilladelse til at betjene den enhed.

[Udforsk de særlige træk](#what-can-hem-do) · [Se grænsefladen](#see-hem-in-action) · [Installer HEM](#installation) · [Få et hjem til dig.](#getting-started) · [Detaljeret vejledning](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Hvad kan HEM - Det gør du?

| Din situation | Hvordan? HEM kan hjælpe |
| --- | --- |
| **Huset er tomt.** | Skift til "Fjern" mål, respektere de enkelte værelses tilstedeværelseregler og undgå unødvendigt at køre udvalgt udstyr. |
| **Du er på vej hjem.** | Tryk **Forbered dig på ankomst.** at midlertidigt anvende hjemmekomfortmål for godkendte automatiske kontroller, selv om alle stadig er væk. |
| **Nogen sover.** | Brug søvnmål, mindske støj fra ventilatoren eller hold de valgte enheder slukket, mens alle de besatte værelser sover. |
| **Et værelse er fugtigt.** | Sammenlign dens luftfugtighed og støbe indikation med mål, foreslå nyttig lufting, eller drive en godkendt dehumidifier ved hjælp af automatisk eller PID kontrol. |
| **Det er varmt og solrigt.** | Evaluer værelsetemperatur, sollys, vejr og tilkoblede vindueskontakter, før du flytter opt-in skaker. |
| **Udendørs luft ser bedre ud.** | Det anbefales at ventilere med indendørs efterspørgsel, udendørs forurening, temperatur, fugtighed, vind og tilgængelige pollen- eller vejrvarsler. |
| **En opvarmning eller TRV stopper med at reagere** | Vis dens utilgængelige eller ventende tilstand, bevar dens konfigurerede kontroller og rapportere fejl i den understøttede enhed, uden at antage, at et batteri eller en relé er blevet genoprettet. |

Dette er eksempler, ikke handlinger, der HEM Resultaterne afhænger af de valgte sensorer. Home Assistant muligheder og dine opt-in-indstillinger.

<a id="explore-the-features"></a>
## Udforsk de særlige træk

<a id="a-complete-home-dashboard"></a>
### Et komplet home dashboard

Den HEM kort giver dig et nyttigt overblik uden at åbne flere integrationer.

- Se udendørsforhold, luftkvalitet og om det er tilrådeligt at ventilere.
- Sammenlign alle overvågede værelser med et kig: temperatur, relativ luftfugtighed, AQI, PM2.5, skimmelindikator, lys og andre støttede målinger.
- Udvide ethvert rum til detaljerede målinger, oplysninger om vinduer og døre, klimastatus, aktive kontrolledere, årsager til ventetid og bygnings-fysisk skøn.
- Se historier og tendenser, se hvilke sensorer der bidrog til et gennemsnit og skelne mellem mangler og målede værdier.
- Gruppenværelser efter faktiske Home Assistant eller bruge en simpel værelsesliste, når du ikke har gulv.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Forskellige indstillinger for hjemmet, hvert værelse og hver enhed

HEM De fælles politikker holdes adskilt fra de lokale beslutninger.

| Indstillingerniveau | Hvad du kan konfigurere |
| --- | --- |
| **Hjem** | Udendørs vejr og forureningskilder, overvågede værelser, globale ventilationsgrænser, husholdningstilstedeværelse, ankomstberedskab og meddelelser. |
| **Værelse** | Indendørs temperatur- og fugtkilder, luftkvalitetsgrænser, vindues- og dørkontakter, søvn- og indkvarteringsadfærd, rumsspecifikke komfortmål, ventilation og skyggevalg. |
| **Individuelt udstyr** | Den tilgængelige kontrolmodus, automatisk/manuel/PID metode, mål per profil, sensorer, stille ventilatorindstillinger, minimumsbetjeningstider, strømbeskyttelse, vinduesadfærd og meddelelser om fejl på enheden. |

Alle tre niveauer er tilgængelige via grupperede, søgbare indstillinger i kortet. Home Assistant ændringer i indstillingen.

<a id="climate-control-and-pid-device-by-device"></a>
### Klimakontrollen og PID, enhed efter enhed

HEM kan arbejde med kompatible Home Assistant **klima**, **Humidifier** og **Ventilator** udstyr, herunder varme, køling, dehumidering, luftvækkelse og støtte til luftcirkulation eller luftrensning.

For hver **understøttet fysisk driftstilstand**, vælge kontrolmetoden uafhængigt:

| Metode | Hvad betyder det? |
| --- | --- |
| **Eksisterende** | Læg drift med den eksisterende kontrolledningsvej. |
| **Automatisk** | Følg HEMDen målede efterspørgsel, situationbaserede mål og tilladelser. |
| **PID** | Anvend feedbackbaseret proportional, integral og derivativ kontrol, hvor udstyret og målingen understøtter det. |
| **Manual** | Kontrol gennem udtrykkeligt støttede anmodninger og mål. |
| **Afslip** | Behold den kontroller slukket, under forudsætning af fysisk beskyttelse og feedback krav. |

For eksempel kan en airconditioner **PID til opvarmning** og **Automatisk til afkøling**En affukter kan have sin egen. PID Tiltrædelsesberettigede fans kan bruge PID når der er mulighed for passende feedback og formålsspecifik kontrol.

PID er **Det er ikke** en universel overriding: HEM De avancerede muligheder omfatter per-modus tuning og kalibrering, foreslåede/adaptive justeringer, stille drift og støttede indstagede ventilatorindstillinger. Du godkender foreslåede ændringer, medmindre du udtrykkeligt vælger begrænset automatisk tilpasning.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Komfortabelt når man er hjemme, økonomisk når man er væk

HEM kan vælge mellem **Komfort, hjem, væk, søvn og miljø** mål baseret på husholdningssituationen, værelsesbevis og dine eksplisite valg.

- **Hjem og væk:** Brug forskellige mål for opvarmning, køling og luftfugtighed afhængigt af, om der er verificeret tilstedeværelse i hjemmet.
- **Værelse tilstedeværelse:** Brug en kvalificeret enhed altid, når der er efterspørgsel, kun, mens værelset er besat, eller kun, når værelset er tomt.
- **Sove:** Hvis du bruger en ventilator til at slå mål over natten, kan du holde den slukket, når alle værelser sover.
- **Øko:** En lukket indendørs dør kan deltage i en beskyttet miljøpolitik, når rummet er verificeret tomt og andre betingelser er opfyldt; en lukket dør alene beviser ikke, at rummet er isoleret.
- **Forberedelse til vågen op:** Brug en konfigureret næste alarmkilde til at lade automatisk søvn være før alarmen og give de godkendte enheder tid til at reagere.

Hvis det er usikkert, om udstyret er tilgængeligt eller om det er nødvendigt med andre beviser HEM ikke blot antager, at det er sikkert at starte en automatisk enhed.

<a id="prepare-your-environment-before-you-arrive"></a>
### Forbered dit miljø før du ankommer

**Forbered dig på ankomst.** Det er en tidsbestemt handling for et bekræftet Away hjem. HEMDet er hjemmeapparatet.

HEM midlertidigt anvender den konfigurerede **Hjemmål** til støtteberettigede Automatic/PID Det kan også tillade en kontroller, der normalt er begrænset til beliggende værelser, midlertidigt at opvarme, afkøle eller justere fugtigheden, før du kommer tilbage. **kun, når den allerede har den nødvendige fysiske kontroltilladelse**.

Forberedelse er ikke en kommando om at slå alt på. Enhederne har stadig brug for ægte efterspørgsel, gyldige sensorer og godkendelse, og skal respektere vinduer, minimum Tænd/Sluk timer og deres egen beskyttelse. Handlingen slutter, når nogen ankommer, du afbestilles det, eller den konfigurerede timer udløber. Home Assistant genstart ikke starter den fulde timer igen.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Udluftningsrådgivning, vinduer, døre og skygge

HEM sammenligner **hvad et værelse behøver** med **om udendørs luft kan hjælpe**.

- Det anbefales at åbne eller lukke vinduer ved hjælp af de aktuelle indendørs målinger, luftfugtighed, forurening, temperatur, vind, vejrvarsler og valgfri pollenkontext.
- Brug udvalgte vindues- og dørkontakter til at forklare værelsesforholdene og undgå at behandle en ukendt kontakt som lukket.
- Hvis det er muligt, skal du prøve at åbne et vindue, før du starter et støttet automatisk apparat, og derefter fortsætte den normale kontrol efter det konfigurerede svar venter, hvis det er nødvendigt.
- Brug døroplysningerne til bevidsthed om rumgrænser, ventilationsforsigtigheder og valgfri miljøbeskyttelse.
- Administrere opt-in lukker, blinds og skygger ved hjælp af passende vinduer, temperatur, vejr, solopgang og valgfri belysningsbevis.

HEM Den kan give vejrledningsråd uden nogen kontrollerbare vinduer.

<a id="humidity-mold-indication-and-air-quality"></a>
### Luftfugtighed, skimmelindkling og luftkvalitet

HEM kombinerer støttede aflæsninger som **temperatur, fugtighed, CO2, partikler, VOC, AQI og belysning** Tilgængelige målinger afhænger af, hvad dit Home Assistant - Det er ikke muligt.

Det er **Formuldsbetegnelse** Hvis den er korrekt konfigureret, kan den påvirke et støttet automatisk luftfugtsregulators effektive mål.

**Muldindkning er et skøn, ikke en muld- eller spordetektor.** Fraværende eller forældede sensordata kan ikke retfærdiggøre et nyt mønsterbaseret enhedskommando.

<a id="announcements-diagnostics-and-protection"></a>
### Annoncer, diagnostik og beskyttelse

Du kan sende relevante anbefalinger og advarsler via konfigurerede Home Assistant meddelelser, TTS/mediaplayer eller **Annonceringshub**, med valgfri AI formulering. AI kan ændre, hvordan en besked er formuleret; HEMDe fysiske kontrolbeslutninger forbliver deterministiske.

HEM omfatter også udstyrsspecifikke beskyttelsesforanstaltninger og diagnostik:

- Minimum på- og udstødningstider, maksimal driftstidsinstilling og støttet håndtering af eksterne strømslutter.
- Vindu- og besættelsesbegrænsninger, manuel override håndtering og native kommandokontrol.
- Fejl- og ikke-tilgængelig-anordning rapportering, med valg af anmeldelsesadfærd for hver enhed.
- En valgfri overvågningshund efter nedbrydning for mistænkt fortsat opvarmning efter en OFF-kommando, med bevaret overvågning og begrænsede genoprettelsesforsøg.
- Klare årsager til at vente, den aktuelle driftsstatus og kildetilgængelighed, så du kan undersøge, før du aktiverer mere kontrol.

**Sikkerhedsgrænser er gældende, selv når alarmen er udeladt.** HEM aldrig behandler en vellykket kommandodistribution som bevis for, at en apparat har reageret fysisk.

<a id="see-hem-in-action"></a>
## Se her. HEM i aktion

Disse engelsksprogede illustrationer bruger prøveværelser og målinger. De viser grænsen i stedet for at vise levende data fra et bestemt hus.

<a id="home-at-a-glance"></a>
### Hjem på et øjeblik

Få vejrledningsrådgivning, vejrforhold og status for hvert overvåget rum på et enkelt kort.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM Home dashboard med ventilationsrådgivning og miljølæsninger i fem værelser" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Udvide rummet for detaljer

Kontroller luftkvaliteten, støbens indikation, tilstedeværelse, vinduestilstand, klimakontroller og forklaringer for hver beslutning.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Udvidet badeværelset dashboard med aflæsninger og uafhængige enhedskontrollere" width="760">
</p>

<a id="home-settings"></a>
### Hjem indstillinger

Administrere udendørs kilder, tilstedeværelse i hele huset, overvågede rum, ventilationsgrænser, forberedelse og meddelelser.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Hjem indstillinger med søgegrupper og kilde- og værelsesstyring" width="900">
</p>

<a id="room-settings"></a>
### Værelsesindstillinger

Vælg, hvad der betyder noget for hvert rum: dets egne sensorer, mål, indkvartering, døre, vinduer, ventilation, skygge og beskyttelsesforanstaltninger.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Grupperede HEM rum indstillinger til sensorer, enhedskontroller, søvn, vinduer og beskyttelse" width="760">
</p>

<a id="device-settings"></a>
### Indstillinger af apparatet

Fintjustere en enhed uden at ændre de andre, herunder støttede kontrolmetoder PID, stille drift, timing og fejlrapportering.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Grupperede HEM indstillinger af udstyret med styring PID, strømbeskyttelse og meddelelser" width="900">
</p>

<a id="getting-started"></a>
## Jeg er ved at komme i gang.

1. **Ordne jeres værelser.** Ind i Home Assistant, oprette eller kontrollere dine Areas og tildele de relevante sensorer og enheder til hver.
2. **Vælg, hvad du skal overvåge.** Tilføj HEM, udvælge de værelser, du er interesseret i og gennemgå de foreslåede temperaturer, fugtighed, vindue, luftkvalitet og udstyrskilder.
3. **Konfigurere fælles information.** Vælg tilgængelige udendørs vejr/luftkvalitetskilder, evidencer for husholdningsbesættelse og eventuelle annoncementsdestinationer, som du ønsker.
4. **Læg kortet til.** Åben et instrumentpaneel i redigering og tilføj **Hjemmiljøleder** Start med overvågning af rummet, aflæsninger og ventilationsrådgivning.
5. **Kun aktivere kontrol, når det er nyttigt.** Åbn et rum, vælg et understøttet apparat, gennemgå dets kontroller og udtrykkeligt vælg Automatic eller PID til de modus, du ønsker HEM at operere.

Det gør du. **Det er ikke** Start med de sensorer, du har, og indfør automatisk styring en enhed ad gangen.

<a id="add-the-card-manually"></a>
### Tilføj kortet manuelt

Integrationen registrerer normalt sit eget Lovelace-kort.

~~~yaml
type: custom:home-environment-manager-card
~~~

Hvis din Home Assistant installation har mere end én HEM anbefaling sensor, du kan være nødt til at indstille passende **enhed** udtrykkeligt:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

For trinvis vejledning om rumkilder, profiler, PID Indstillingerne, vinduespolitikken, forberedelsen, skimmel kalibrering, solskygge og meddelelse levering, brug af [detaljeret konfigurationsvejledning](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant EU-butik

1. Åben **HACS** i Home Assistant.
2. Tilføj **HTTPS://github.com/Chreece/HA-Home-Environment-Manager** som en **brugerdefineret arkiv** i den **Integration** kategori, hvis den ikke allerede er opført.
3. Find **Hjemmiljøleder** og installere den.
4. Genopstart **Home Assistant** til at indlæse integrationen.
5. Gå til **Indstillinger → Enheder & tjenester → Tilføj integration**, søge efter **Hjemmiljøleder** og fuldføre indstillingen.

<a id="manual-installation"></a>
### Manuel installation

Kopiere arkivet **custom_components/environment_manager** mappe i matching **custom_components** i din katalog Home Assistant konfiguration og bevarelse af katalognavnet **environment_manager**Start igen. Home Assistant og tilføje integrationen gennem **Indstillinger → Enheder og tjenester**.

For efterfølgende installationsændringer skal du beholde din eksisterende HEM integrering og indstillinger. omlædner instrumentpanelet i din browser, hvis kortets udseende ikke opdateres med det samme.

<a id="common-questions"></a>
## Vanlige spørgsmål

**Kan jeg bruge det? HEM uden at give det kontrol over mine enheder?**

Ja, overvågning, måling, ventilationsrådgivning, historie og mange miljømæssige indikationer virker uden at aktiverer enheden.

**- Vil. HEM Kontrollerer den automatisk alle enheder?**

Nej, du vælger de fysiske enheder, du vil administrere, og du vælger udtrykkeligt kontrolmetoden for støttede modus.

**Støtter alle apparater PID?**

- Nej, jeg er ikke. HEM støtte PID for **støtteberettigede** opvarmning, køling, fugtighed eller ventilationskontrol, når apparatet og de valgte målinger giver de nødvendige muligheder og feedback. PID kontrol.

**Kan jeg give hvert værelse forskellige regler?**

Ja, beboelsesforhold, søvnadfærd, kilder, mål og visse sikkerhedspræferencer kan variere efter værelse, mens hver fysisk enhed har sine egne drifts- og beskyttelsesindstillinger.

**Kan HEM Forbered mit hjem, mens jeg er væk?**

- Ja, det er det. **Forbered dig på ankomst.** Det giver midlertidigt mulighed for, at kvalificerede, allerede autoriserede automatiske kontroller bruger hjemmål i en begrænset periode.

**Åbner en  ⁇ godt for ventilation  ⁇  anbefaling mine vinduer?**

Det forklarer, hvornår luftning kan hjælpe. Automatisk bevægelse er en separat, opt-in-funktion for støtteberettigede skygge eller dække, der er underlagt deres egne sikkerhedskontroller.

**Hvad hvis en sensor eller en enhed ikke er tilgængelig?**

HEM Det er vigtigt at sikre, at det er muligt at skelne mellem ukendte data og reelle aflæsninger, beholde konfigurerede kontrolleroplysninger, hvor det er muligt, og afsløre årsager til vente og diagnostik.

<a id="help-and-troubleshooting"></a>
## Hjælp og fejlfinding

Hvis noget synes at være galt, så tjek det relevante rum eller kontrollederen **Begrundelse**, **Diagnostik**, kildets tilgængelighed og den aktuelle kontrolmetode. [detaljeret konfigurationsvejledning](../../docs/advanced-configuration.md) dækker fælles ventestater, tilstedeværelsepolitikker, PID støtteberettigelse, vinduer og fejlfinding i forbindelse med enhedsrespons.

For et reproducerbart problem, [åbne en GitHub Udgangspunktet](https://github.com/Chreece/HA-Home-Environment-Manager/issues) med den forventede adfærd, den faktiske adfærd, relevante rum/enhedsindstillinger og trin til at reproducere.

Der er velkomne bidrag og forbedringer. [Contributing.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Støtte og licens

Hvis HEM er nyttigt for dig, du kan [støtte til Grækenland i Ko-fi](https://ko-fi.com/chreece).

Distribueret under [MIT licens](../../LICENSE).
