<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Hjem Miljødirektør - smartere luftkvalitet, komfort, ventilasjon og klimakontroll" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Støtte til Chreece Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <strong>Norsk bokmål</strong> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Hjem miljøleder

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Hele hjemmet ditt miljø, i en Home Assistant kortet.</strong></p>

**HEM hjelper hjemmet ditt til å forstå omgivelsene og reagere på hva hvert rom faktisk trenger.** Det bringer din Home Assistant sensorer, værdata, besetningsopplysninger og kompatible klimaparater sammen slik at du kan overvåke luftkvaliteten, få nyttig ventilasjonsrådgivning, administrere komfort og automatisere utstyret du velger.

For eksempel: HEM kan redusere oppvarming mens alle er borte, forberede utvalgte rom før du kommer tilbake, bruke et annet luftfuktighetsmål mens du sover, eller be deg åpne et vindu før du kjører en avfukter. **overvåke og anbefale**, uten å kontrollere noen enhet.

**Du holder ansvaret.** Hvert rom har sine egne innstillinger. Hver støttet apparat har sin egen kontroller, driftsmodus, mål og sikkerhetsgrenser. HEM aldri antager at valg av en enhet gir den tillatelse til å bruke den enheten.

[Utforsk funksjonene](#what-can-hem-do) · [Se grensesnittet](#see-hem-in-action) · [Install HEM](#installation) · [Sett opp ditt hjem](#getting-started) · [Detaljerte veiledning](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Hva kan HEM gjør du?

| Din situasjon | Hvordan? HEM kan hjelpe |
| --- | --- |
| **Huset er tomt.** | Skifte til Away mål, respektere hver rom tilstedeværelse regler og unngå å kjøre utvalgt utstyr unødvendig. |
| **Du er på vei hjem.** | Trykk **Forbered deg på ankomst.** å midlertidig bruke hjemmekomfortmål for kvalifiserte automatiske kontroller, selv om alle fortsatt er borte. |
| **Noen sover.** | Bruk søvnmål, redusere støy fra ventilatoren, eller hold utvalgte enheter av mens alle de ansatte sover. |
| **Et rom er fuktig** | Sammenlign fuktighets- og støpeindikasjonen med mål, foreslå nyttig lufting eller bruk en godkjent avfukter med automatisk eller PID kontroll. |
| **Det er varmt og solfylt** | Evaluere romtemperatur, sollys, vær og tilkoblede vinduer før du flytter innvalgene. |
| **Utendørs luft ser bedre ut.** | Det anbefales å ventilere med innendørs etterspørsel, utendørs forurensning, temperatur, fuktighet, vind og tilgjengelige pollen- eller værvarn. |
| **En oppvarming eller TRV slutter å reagere** | Vis ikke-tilgjengelig eller ventende tilstand, beholde den konfigurerte kontrolleren og rapportere støttet enhet feilsaker uten å anta at et batteri eller relé har gjenopprettet. |

Dette er eksempler, ikke handlinger som HEM Resultatene avhenger av de valgte sensorene, hver enhet faktisk er i stand til å bruke den. Home Assistant Evne og innstillinger.

<a id="explore-the-features"></a>
## Utforsk funksjonene

<a id="a-complete-home-dashboard"></a>
### Et komplett hjemme-dashboard

De HEM kort gir deg et nyttig overblikk uten å åpne flere integrasjoner.

- Se utendørsforhold, luftkvalitet og om det anbefales å ventilere.
- Sammenlign alle overvåkede rom på ett blikk: temperatur, relativ fuktighet, AQI, PM2.5, mold indikasjon, lys og andre støttede målinger.
- Utvide ethvert rom for detaljerte målinger, informasjon om vinduer og dører, klimastatus, aktive kontrollører, årsaker til ventetid og bygningsfysikkskønninger.
- Se historier og trender, se hvilke sensorer som bidro til et gjennomsnitt og skille manglende lesninger fra målede verdier.
- Gruppenrom etter faktiske Home Assistant eller bruk en enkel romliste når du ikke har et gulv.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Forskjellige innstillinger for hjemmet, hvert rom og hver enhet

HEM De deler de felles politikkene og de lokale beslutningene.

| Innstillingsnivå | Hva du kan konfigurere |
| --- | --- |
| **Hjem** | Utendørs vær og forurensningskilder, overvåkede rom, globale ventilasjonsgrenser, husholdningstilstedeværelse, ankomstberedskap og melding. |
| **Rom** | Innendørs temperatur- og fuktighetskilder, luftkvalitetsgrenser, kontakt med vinduer og dører, søvn- og besettingshemming, romspesifikke komfortmål, ventilasjons- og skyggevalg. |
| **Individuell enhet** | Den tilgjengelige styringstilstandene, automatisk/manuell/PID Metode, profilmål, sensorer, stille ventilatorsettinger, minimumsbetjeningstid, strømbeskyttelse, vinduer og meldinger om feil på enheten. |

Alle tre nivåene er tilgjengelige gjennom grupperte, søkbare innstillinger i kortet. Home Assistant installasjonsendringer.

<a id="climate-control-and-pid-device-by-device"></a>
### Klimakontroll og PID, enhet etter enhet

HEM kan fungere med kompatible Home Assistant **klima**, **luftfukter** og **Venner** utstyr, inkludert oppvarming, kjøling, dehumidering, fuktiggjøring og støttet luftcirkulasjons- eller luftrensingsanordning.

For hver **støttet fysisk driftstilstand**, velger kontrollmetoden uavhengig:

| Metode | Hva det betyr |
| --- | --- |
| **Eksisterende** | La drift være med den eksisterende styringsveien. |
| **Automatisk** | Følg HEMmålt etterspørsel, situasjonsbaserte mål og tillatelser. |
| **PID** | Bruk tilbakemeldingsbasert proporsjonell, integral og derivatkontroll når enheten og målingen støtter den. |
| **Manual** | Kontroll gjennom eksplisitt støttet forespørsel og mål. |
| **Avgang** | Hold den kontrolleren av, underlagt fysiske beskyttelse og tilbakemeldingskrav. |

For eksempel kan en klimaanlegg bruke **PID for oppvarming** og **Automatisk for kjøling**En avfukter kan ha sin egen PID For å sikre at det er mulig å bruke en PID når passende tilbakemeldinger og formålsspecifikk kontroll er tilgjengelig.

PID er **ikke** en universell override: HEM De nye alternativene inkluderer per-modus tuning og kalibrering, foreslåtte/adaptive justeringer, stille drift og støttede stadierte faninnstillinger. Du godkjenner foreslåtte endringer med mindre du uttrykkelig velger begrenset automatisk tilpasning.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Komfortabel når du er hjemme, økonomisk når du er borte

HEM kan velge mellom **Komfort, hjemme, borte, søvn og miljø** mål basert på husholdningssituasjonen, rombevisene og dine eksplisitte valg.

- **Hemme og borte:** Bruk forskjellige oppvarmings-, kjølemål og fuktighetsmål avhengig av verifisert tilstedeværelse i hjemmet.
- **Romstilværelse:** Bruk en kvalifisert enhet alltid når det er etterspørsel, bare mens rommet er opptatt, eller bare mens rommet er tomt.
- **Søvn:** Bruk overnattende mål og stille ventilatøradferd.
- **Øko:** Bruk økonomiske mål der det er konfigurert. En lukket interiørdør kan delta i en beskyttet miljøpolitikk når rommet verifiseres tomt og andre betingelser er oppfylt; en lukket dør alene beviser ikke at rommet er isolert.
- **Oppvakningskreds:** Bruk en konfigurert nestelarmkilde for å la automatisk søvn være før larmen og gi kvalifiserte enheter tid til å svare.

Hvis bruk, tilgjengelighet av enheten eller andre nødvendige bevis er usikre, HEM ikke bare anta at det er trygt å starte en automatisk enhet.

<a id="prepare-your-environment-before-you-arrive"></a>
### Forbered omgivelsene dine før du ankommer

**Forbered deg på ankomst.** Det er en tidsbestemt handling for et bekreftet Away-hjem. Start det fra kortheader eller HEMDet er hjemmeapparatet.

HEM midlertidig gjelder konfigurert **Hjemmål** til støtteberettigede Automatic/PID kontrollører slik at rommene kan begynne å varme, kjøle eller justere fuktighet før du kommer tilbake. Dette kan også midlertidig tillate en kontrollør som normalt er begrenset til beliggende rom, **bare når den allerede har den nødvendige fysiske kontrolltillatelse**.

Forberedelse er ikke et kommando for å slå på alt. Enheter trenger fortsatt ekte etterspørsel, gyldige sensorer og autorisasjoner, og må respektere vinduer, minimum ON/OFF-tid og deres egen beskyttelse. Handlingen slutter når noen ankommer, du kansellerer den, eller den konfigurerte timeren utløper. Home Assistant gjenstart starter ikke full timer over.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Ventilasjonsrådgivning, vinduer, dører og skygge

HEM sammenligner **hva et rom trenger** med **om utendørs luft kan hjelpe**.

- Det anbefales å åpne eller lukke vinduer ved hjelp av gjeldende innendørs målinger, luftfuktighet, forurensning, temperatur, vind, værvarsler og valgfri pollen kontekst.
- Bruk utvalgte vindu- og dørkontakter for å forklare romforholdene og unngå å behandle en ukjent kontakt som stengt.
- Vennligst spør deg om du skal prøve å åpne et vindu før du starter et støttet automatisk apparat, og deretter fortsette normal kontroll etter at den konfigurerte responsen venter om nødvendig.
- Bruk døropplysningene for romgrensbevissthet, ventilasjonsvarsel og valgfri miljøvern.
- Forvalte opt-in lukker, blinder og skyer ved hjelp av passende vinduer, temperatur, vær, solopphøyde og valgfritt belysningsbevis.

HEM Den kan gi ventilasjonsråd uten noen kontrollerbare vinduer. Den åpner ikke et vindu av seg selv bare fordi lufting ville hjelpe.

<a id="humidity-mold-indication-and-air-quality"></a>
### Luftfuktighet, skimmelindikator og luftkvalitet

HEM kombinerer støttede avlesninger som **temperatur, fuktighet, CO2, partikler, VOC, AQI og lysstyrke** Tilgjengelige målinger avhenger av hva Home Assistant installasjon gir.

Det er **skimmelindikator** beregner fuktighetsforhold på en kaldt overflate fra rom- og utendørs temperaturer og en kalibreringsmåling. Når den er riktig konfigurert, kan den påvirke en støttet automatisk fuktighetsregler effektiv mål.

**Skimmering er et estimat, ikke en sjammer eller spordetektor.** Fraværende eller forældede sensordata kan ikke rettferdiggjøre et nytt mønsterbasert enhetskommando.

<a id="announcements-diagnostics-and-protection"></a>
### Annonser, diagnostikk og beskyttelse

Du kan sende relevante anbefalinger og varsler gjennom konfigurert Home Assistant meldinger, TTS/mediaspillere eller **Annonseringshub**, med valgfri AI formulering. AI kan endre hvordan en melding er formulert; HEMDe fysiske kontrollbeslutningene forblir deterministiske.

HEM omfatter også enhetsspecifikke beskyttelser og diagnostikk:

- Minimum på- og avaktiveringstid, maksimalt driftstidsinnstillinger og støttet ekstern håndtering av strømforbryter.
- Vindu- og besetningsbegrensninger, manuell override håndtering og native kommandokontroller.
- Fejl- og ikke-tilgjengelig-enhetsrapportering, med valg av meldingsadferd for hver enhet.
- En valgfri overvåkingshund etter nedlukning for mistenkt fortsatt oppvarming etter en OFF-kommando, med overvåket overvåking og begrenset gjenopprettingsforsøk.
- Klare ventetidsmål, nåværende driftsstatus og kildetilgjengelighet, slik at du kan undersøke før du aktiverer mer kontroll.

**Sikkerhetsgrensene er fortsatt i kraft selv når en varsling er inaktivert.** HEM aldri behandler en vellykket kommandodissendelse som bevis på at en enhet fysisk reagerte.

<a id="see-hem-in-action"></a>
## Ser du HEM i aksjon

Disse engelskspråklige illustrasjonene bruker prøverommer og målinger. De viser grensesnittet i stedet for å vise levende data fra et bestemt hus.

<a id="home-at-a-glance"></a>
### Hjem på et øyeblikk

Få råd om ventilasjon, værforhold og status for hvert overvåket rom i et enkelt kort.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM Home dashboard med ventilasjonsrådgivning og miljølesninger i fem rom" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Utvide et rom for detaljer

Kontroller luftkvaliteten, støpeindikasjonen, tilstedeværelsen, vinduets tilstand, klimakontroller og forklaringer for hver beslutning.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Utvidret badehandler dashboard med lesninger og uavhengige enhetskontroller" width="760">
</p>

<a id="home-settings"></a>
### Hjeminnstilling

Forvalte utendørs kilder, tilstedeværelse i hele huset, overvåkede rom, ventilasjonsgrenser, forberedelse og varsler.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Hjeminnstilling med søkbare grupper og kilde- og romstyring" width="900">
</p>

<a id="room-settings"></a>
### Romsinnstillinger

Velg hva som er viktig for hvert rom: sine egne sensorer, mål, innkvartering, dører, vinduer, ventilasjon, skygge og sikkerhetstiltak.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Grupperte HEM rominnstilling for sensorer, enhetskontroll, søvn, vinduer og beskyttelse" width="760">
</p>

<a id="device-settings"></a>
### Innstillinger på enheten

Finjustering av en enhet uten å endre de andre, inkludert støttet kontrollmetoder, PID, stille drift, timing og feilmelding.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Grupperte HEM innstillinger på enheten med kontroll, PID, strømbeskyttelse og meldinger" width="900">
</p>

<a id="getting-started"></a>
## Å begynne

1. **Ordne rommene dine.** I Home Assistant, opprette eller sjekke områdene dine og tildele passende sensorer og enheter til hver.
2. **Velg hva du skal overvåke.** Legg til HEM, velg rommene du bryr deg om og gjennomgå de foreslåtte temperaturene, fuktigheten, vinduet, luftkvaliteten og enhetens kilder.
3. **Konfigurere delt informasjon.** Velg tilgjengelige utendørs vær/luftkvalitetskilder, evidens for husholdningsbesettelse og eventuelle annonseringsdestinasjoner du vil.
4. **Legg til kortet.** Åpne et instrumentbrett i redigering og legge til **Hjem miljøansvarlig** Begynn med overvåking av rommet, avlesninger og ventilasjonsrådgivning.
5. **Aktiver styring bare der det er nyttig.** Åpne et rom, velg et støttet apparat, se gjennom kontrolløren og uttrykkelig velg PID for de modene du ønsker HEM å operere.

Det gjør du. **ikke** Start med sensorer du har, og innfør automatisk kontroll en enhet i gangen.

<a id="add-the-card-manually"></a>
### Legg med kortet manuelt

Integrasjonen registrerer normalt sitt eget Lovelace-kort.

~~~yaml
type: custom:home-environment-manager-card
~~~

Hvis din Home Assistant installasjon har mer enn en HEM anbefaling sensor, kan du trenge å sette riktig **Entitet** uttrykkelig:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

For stegvis instruksjoner om romkilder, profiler, PID settinger, vinduer politikk, forberedelse, støpe kalibrering, solskygge og annonsering levering, bruke [detaljerte konfigurasjonsguide](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installering

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant EU-butikk

1. Åpne **HACS** i Home Assistant.
2. Legg til **HTTPS://github.com/Chreece/HA-Home-Environment-Manager** som en **Custom repositori** i den **Integrasjon** kategori hvis den ikke allerede er oppført.
3. Finn **Hjem miljøansvarlig** og installere den.
4. Å starte på nytt **Home Assistant** for å laste inn integrasjonen.
5. Gå til **Innstillinger → Enheter & tjenester → Legg til integrasjon**, søk etter **Hjem miljøansvarlig** og fullføre innstillingen.

<a id="manual-installation"></a>
### Manuell installasjon

Kopier av arkivets **custom_components/environment_manager** mappe inn i matching **custom_components** katalog i din Home Assistant konfigurasjon, beholder katalognavnet **environment_manager**Start på nytt. Home Assistant og legge til integrasjonen gjennom **Innstillinger → Enheter og tjenester**.

For senere installasjonsendringer, beholde eksisterende HEM integreringselementer og innstillinger. Overlast dashbordet i nettleseren hvis kortets utseende ikke oppdateres umiddelbart.

<a id="common-questions"></a>
## Vanlige spørsmål

**Kan jeg bruke HEM uten å gi det kontroll over mine enheter?**

Ja, overvåking, målinger, ventilasjonsrådgivning, historie og mange miljøindikatorer fungerer uten at enheten aktiveres.

**Will. HEM automatisk styre hver enhet den oppdager?**

Nei. Du velger de fysiske enhetene du vil administrere og velger eksplisitt styringsmetoden for støttede modi. Sensorens kvalifisering og native enhetens muligheter bestemmer fortsatt hva som er mulig.

**Støtter alle apparater PID?**

- Nei, ikke. HEM Støtter PID for **støtteberettigede** oppvarming, kjøling, luftfuktighet eller ventilatørstyringsveier når apparatet og de valgte målingene gir de nødvendige mulighetene og tilbakemeldingen. PID kontroll.

**Kan jeg gi hvert rom forskjellige regler?**

Ja. Besettelsesforhold, søvnadferd, kilder, mål og visse sikkerhetsprøver kan variere etter rom, mens hver fysisk enhet har sine egne drifts- og beskyttelsesinnstillinger.

**Kan HEM Forberede mitt hjem mens jeg er borte?**

- Ja, det er det. **Forbered deg på ankomst.** Det gir midlertidig mulighet til at kvalifiserte, allerede autoriserte automatiske kontroller bruker hjemmål i en begrenset periode.

**Åpner en anbefaling om ventilasjon vinduene mine?**

Det forklarer når lufting kan hjelpe. Automatisk bevegelse er en separat, opt-in funksjon for kvalifiserte støttet skaker eller dekker, underlagt egne sikkerhetskontroller.

**Hva om en sensor eller en enhet blir utilgjengelig?**

HEM Det er viktig å sikre at det er mulig å identifisere og analysere data som ikke er kjent fra virkelige data, å beholde konfigurert data om kontrolløren, og å utdype venteregenskaper og diagnostikk.

<a id="help-and-troubleshooting"></a>
## Hjelp og feilsøking

Hvis noe synes å være galt, sjekk det relevante rommet eller kontrolløren **Begrunnelse**, **Diagnostikk**, kildetilgjengelighet og strømkontrollmetode. [detaljerte konfigurasjonsguide](../../docs/advanced-configuration.md) dekker felles ventestater, tilstedeværelsepolitikk, PID kvalifisering, vinduer og feilsøking av enhetens respons.

For et reprodusert problem, [åpne en GitHub utstedelse](https://github.com/Chreece/HA-Home-Environment-Manager/issues) med forventet atferd, faktisk atferd, relevante rom/enheten innstillinger og trinn å reprodusere.

Bidrag og forbedringer er velkommen. [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Støtte og lisens

Hvis HEM er nyttig for deg, kan du [Støtte til Chreece på Ko-fi](https://ko-fi.com/chreece).

Utstedt under [MIT-lisens](../../LICENSE).
