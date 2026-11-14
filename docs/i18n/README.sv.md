<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Hem Miljöchef - smartare luftkvalitet, bekvämlighet, ventilation och klimatkontroll" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Stöd till Grekland Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <strong>Svenska</strong> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Hemmiljöchef

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logotyp" width="420">
</p>

<p align="center"><strong>Hela ditt hems miljö, i en Home Assistant Kortet.</strong></p>

**HEM hjälper ditt hem att förstå omgivningen och att reagera på vad varje rum egentligen behöver.** Det ger dig Home Assistant Sensorer, väderuppgifter, information om upptagning och kompatibla klimatutrustning tillsammans så att du kan övervaka luftkvaliteten, få användbara ventilationsråd, hantera komfort och automatisera den utrustning du väljer.

Till exempel: HEM kan minska uppvärmningen medan alla är borta, förbereda utvalda rum innan du återvänder, använda ett annat luftfuktighetsmål medan du sover eller be dig öppna ett fönster innan du kör en avfuktar. **övervaka och rekommendera**, utan att kontrollera någon enhet.

**Du ska fortsätta att styra.** Varje rum har sina egna inställningar. Varje stödjande apparat har sin egen kontrollör, driftläge, mål och säkerhetsgränser. HEM aldrig antar att det när man väljer en enhet får tillstånd att använda den.

[Utforska egenskaperna](#what-can-hem-do) • Förberedelser [Se gränssnittet](#see-hem-in-action) • Förberedelser [Installa HEM](#installation) • Förberedelser [Gör ditt hem](#getting-started) • Förberedelser [Detaljerad vägledning](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Vad kan HEM - Är det?

| Din situation | Hur? HEM kan hjälpa |
| --- | --- |
| **Huset är tomt.** | Övergå till avlägsna mål, respektera varje rums närvaroregler och undvik att använda utvalda utrustning onödigt. |
| **Du är på väg hem.** | Tryck **Förbered dig för ankomsten.** Tillfälligt använda hemkomfortmål för kvalificerade automatstyrare, även om alla fortfarande är borta. |
| **Någon sover.** | Använd sömnmål, minska ljudet från ventilatorn eller håll utvalda apparater borta medan alla rum som är upptagna sover. |
| **Ett rum är fuktigt.** | Jämför dess luftfuktighet och mögel indikation med mål, föreslå användbar luftning eller använda en auktoriserad avfuktar med hjälp av automatiska eller PID kontroll. |
| **Det är varmt och soligt.** | Evaluera rumstemperatur, solljus, väder och anslutna fönsterkontakter innan du flyttar intagna nyanser. |
| **Utomhusluften ser bättre ut.** | Rekommenderas ventilation med användning av inomhusbehov, utomhusföroreningar, temperatur, luftfuktighet, vind och tillgängliga pollen- eller vädervarningar. |
| **En värme eller TRV slutar svara** | Visa det otillgängliga eller väntande tillståndet, behålla den konfigurerade kontrolleren och rapportera fel på den stödda enheten utan att anta att batteriet eller reläet har återhämtat sig. |

Detta är exempel, inte åtgärder som HEM Resultaten beror på de valda sensorerna. Home Assistant Fungerar och inställningar för att välja in.

<a id="explore-the-features"></a>
## Utforska egenskaperna

<a id="a-complete-home-dashboard"></a>
### Ett komplett hembord

Den HEM kort ger dig en användbar översikt utan att öppna flera integrationer.

- Se utomhusförhållanden, luftkvaliteten och om det är lämpligt att ventilera.
- Jämför alla övervakade rum på ett ögonblick: temperatur, relativa luftfuktighet, AQI, PM2.5, mögel indikation, ljus och andra stödda mätningar.
- Utöka alla utrymmen för detaljerade mätningar, information om fönster och dörrar, klimatstatus, aktiva kontrollörer, skäl till väntan och byggnadsfysics uppskattningar.
- Se historier och trender, se vilka sensorer som bidrog till ett genomsnitt och skilja mellan saknade mätningar och mätda värden.
- Gruppenrum efter verkliga Home Assistant eller använda en enkel rumlista när du inte har golv.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Olika inställningar för hemmet, varje rum och varje enhet

HEM Den gemensamma politiken ska hållas oberoende av lokala beslut.

| Inställningsnivå | Vad du kan konfigurera |
| --- | --- |
| **Hem** | Utomhus väder och föroreningskällor, övervakade rum, globala ventilationsgränser, hushållets närvaro, ankomstförberedelser och meddelandeleverans. |
| **Rummet** | Inomhustemperatur- och luftfuktighetskällor, luftkvalitetströskelvärden, fönster- och dörrkontakter, sömn- och upptagningsbeteende, rumsspecifika komfortmål, ventilation och skuggning. |
| **En enskild enhet** | Dess tillgängliga styrläge, automatiska/manuella/PID Metod, mål per profil, sensorer, lugna ventilatörsinställningar, minsta driftstider, strömskydd, fönsterbeteende och meddelanden om fel på enheten. |

Alla tre nivåer är tillgängliga genom grupperade, sökbara inställningar i kortet. Home Assistant Anpassningar i inställningen.

<a id="climate-control-and-pid-device-by-device"></a>
### Klimatkontroll och PID, enhet för enhet

HEM kan fungera med kompatibla Home Assistant **klimat**, **förfuktar** och **Väntar** Anordningar, inklusive uppvärmning, kylning, avfuktande, fuktiggörande och stödjande luftcirkulation- eller luftreningsutrustning.

För varje **Stödda fysiska driftsläge**, välja kontrollmetoden självständigt:

| Metod | Vad det betyder |
| --- | --- |
| **Existerande** | Lämna drift med den befintliga kontrollvägen. |
| **Automatik** | Följ HEMMålda efterfrågan, situationbaserade mål och tillstånd. |
| **PID** | Använd proportionell, integrell och derivatstyrning baserad på återkoppling, om den stöds av anordningen och mätningen. |
| **Handbok** | Kontroll genom uttryckligen stödda förfrågningar och mål. |
| **Avstängd.** | Håll den kontrollerna avstängda, med förbehåll för fysisk skydd och återkopplingskrav. |

Till exempel kan en luftkonditionering använda **PID för uppvärmning** och **Automatik för kylning**En avfuktar kan ha sin egen PID För att kunna få tillgång till dessa produkter kan du använda PID När lämplig återkoppling och ändamålsspecifik kontroll finns tillgängliga.

PID är **Det är inte så.** en universell överskjutning: HEM Det finns en annan metod som endast erbjuder de metoder som en viss enhet, operativläge och återkopplingskälla kan stödja. Avancerade alternativ inkluderar per-modus tuning och kalibrering, föreslagna/adaptiva justeringar, lugn drift och stödda invecklade ventilatorinställningar. Du godkänner föreslagna ändringar om du inte uttryckligen väljer begränsad automatisk anpassning.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Bekvämt när man är hemma, ekonomiskt när man är borta

HEM kan välja mellan **Komfort, hem, bort, sömn och miljö** mål baserat på hushållssituationen, rumprov och dina uttryckliga val.

- **Hem och bort:** Använd olika värme-, kyl- och luftfuktighetsmål beroende på verifierad närvaro i hemmet.
- **Rum närvaro:** Använd en lämplig enhet alltid när det finns efterfrågan, endast när rummet är upptaget eller endast när rummet är tomt.
- **Sömn:** Använd övernattningsmål och tystare ventilatorbeteende.
- **Öko:** En stängd inre dörr kan delta i en skyddad miljöpolicy när rummet kontrolleras tomt och andra villkor är uppfyllda.
- **Förberedelse för vakning:** Använd en konfigurerad nästa larmkälla för att lämna automatisk sömn före larmet och ge kvalificerade enheter tid att svara.

Om upptagning, tillgänglighet av enheten eller andra nödvändiga bevis är osäkra, HEM inte helt enkelt anta att det är säkert att starta en automatisk enhet.

<a id="prepare-your-environment-before-you-arrive"></a>
### Förbereda din miljö innan du anländer

**Förbered dig för ankomsten.** Det är en tidig åtgärd för ett bekräftat Away hem. HEMDet är hemapparatet.

HEM tillfälligt tillämpar den konfigurerade **Hemmål** till stödberättigande Automatic/PID kontrollörer så att rummen kan börja värma, kyla eller justera luftfuktigheten innan du återvänder. **endast om den redan har behörig fysisk kontrolltillstånd**.

Förberedelse är inte ett kommando för att slå på allt. Enheter behöver fortfarande genuin efterfrågan, giltiga sensorer och auktorisation, och måste respektera fönster, minimimängder på/ut och sina egna skydd. Handlingen slutar när någon anländer, du avbryter den, eller den konfigurerade timern löper ut. Home Assistant omstart inte startar timern helt över.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Ventilationsrådgivning, fönster, dörrar och skuggning

HEM jämförelser **vad ett rum behöver** med **om utomhusluft kan hjälpa**.

- Rekommenderas att öppna eller stänga fönster med hjälp av aktuella inomhusmätningar, utomhusfuktighet, föroreningar, temperatur, vind, vädervarningar och valfri pollenkontext.
- Använd utvalda fönster- och dörrkontakter för att förklara rumförhållandena och undvik att behandla en okänd kontakt som stängd.
- Alternativt kan du be om att försöka öppna ett fönster innan du startar en automatisk apparat som stöds, och sedan fortsätta normal kontroll efter att det konfigurerade svaret har väntat om det behövs.
- Använd dörrinformation för att vara medveten om rumgränserna, ventilationsförsiktighet och valfritt skyddat miljöbeteende.
- Hantera valda luktar, blindar och skuggor med lämpliga fönster, temperatur, väder, soluppgång och valbara belysningsbevis.

HEM Den kan ge ventilationsråd utan några kontrollerbara fönster. Den öppnar inte ett fönster av sig själv bara för att luftning skulle hjälpa.

<a id="humidity-mold-indication-and-air-quality"></a>
### Luftfuktighet, mögel indikation och luftkvalitet

HEM kombinerar stödda avläsningar som **temperatur, luftfuktighet, CO2, partiklar, VOC, AQI och belysning** Tillgängliga mätningar beror på vad du behöver för att Home Assistant - Det finns en uppsättning.

Det är **Muld indikation** Den beräknar fuktighet på en kall yta utifrån rum- och utomhustemperaturer och en kalibreringsmätning.

**Muld indikation är en uppskattning, inte en muld eller spordetektor.** Missande eller föråldrade sensordata kan inte rättfärdiga ett nytt mjukbaserat enhetskommando.

<a id="announcements-diagnostics-and-protection"></a>
### Anmälningar, diagnostik och skydd

Du kan skicka relevanta rekommendationer och varningar via konfigurerade Home Assistant anmälningar, TTS/media-spelare eller **Anmälningscentrum**AI kan ändra hur ett meddelande uttrycks. HEMDe fysiska kontrollbesluten är fortfarande deterministiska.

HEM Inkluderar även enhetsspecifika skydd och diagnostik:

- Minimal på- och avstängningsperiod, maximala driftstider och stödjande extern effektbrytarehantering.
- Fönster- och upptagningsbegränsningar, manuell överreddhantering och native kommandokontroller.
- Rapportering av fel och otillgängliga enheter, med ett val av meddelandebeteende för varje enhet.
- En valfri vakthund efter stängning för misstänkt fortsatt uppvärmning efter ett OFF-kommando, med vaktad övervakning och begränsade återhämtningsförsök.
- Klara väntetillstånd, aktuell driftsstatus och tillgång till källor, så att du kan undersöka innan du aktiverar mer kontroll.

**Säkerhetsgränserna gäller även när en varning är inaktiverad.** HEM behandlar aldrig ett framgångsrikt befallningssändande som bevis på att en apparat fysiskt svarade.

<a id="see-hem-in-action"></a>
## Se här. HEM i aktion

I dessa engelska illustrationer används provrum och mätningar som visar gränssnittet i stället för att visa data från ett visst hus.

<a id="home-at-a-glance"></a>
### Hem på en gång.

Få råd om ventilation, väderförhållanden och status för varje övervakad rum i ett enda kort.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM Hemsidan med ventilationsrådgivning och miljöläsningar i fem rum" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Utöka rummet för detaljer

Kontrollera luftkvaliteten, mögelindikator, närvaro, fönstertillstånd, klimatkontroll och förklaringar för varje beslut.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Utökad badrumskontroller med mätningar och oberoende enhetskontroll" width="760">
</p>

<a id="home-settings"></a>
### Hem inställningar

Hantera utomhuskällor, närvaro i hela huset, övervakade rum, ventilationsgränser, förberedelser och meddelanden.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Hem inställningar med sökbara grupper och käll- och rumhantering" width="900">
</p>

<a id="room-settings"></a>
### Rumsinställningar

Välj vad som är viktigt för varje rum: sina egna sensorer, mål, upptagning, dörrar, fönster, ventilation, skuggning och skydd.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Grupperade HEM rumsinställningar för sensorer, enhetskontroll, sömn, fönster och skydd" width="760">
</p>

<a id="device-settings"></a>
### Anordningsinställningar

Finjustering av en enhet utan att ändra de andra, inklusive stödda kontrollmetoder, PID, lugn drift, timing och felrapportering.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Grupperade HEM Anordningens inställningar med styrning, PID, strömskydd och anmälningar" width="900">
</p>

<a id="getting-started"></a>
## - Jag börjar.

1. **Ordna era rum.** I Home Assistant, skapa eller kontrollera era områden och tilldela lämpliga sensorer och enheter till var och en.
2. **Välj vad du ska övervaka.** Lägg till HEMVälj de rum du bryr dig om och se över den föreslagna temperaturen, luftfuktigheten, fönstret, luftkvaliteten och utrustningens källor.
3. **Konfigurera delad information.** Välj tillgängliga väder/luftkvalitetskällor, bevis på hushållsinnehållning och eventuella annonsdestinationer som du vill.
4. **Lägg till kortet.** Öppna en instrumentpanel i redigeringsläge och lägg till **Hemmiljöchef** Börja med övervakning, mätningar och ventilationsrådgivning.
5. **Kontroll endast när det är användbart.** Öppna ett rum, välj en stödd apparat, se över dess kontrollör och uttryckligen välj PID för de lägen du vill ha HEM att operera.

Det gör du. **Det är inte så.** Börja med de sensorer du har, och införa automatisk kontroll en enhet i taget.

<a id="add-the-card-manually"></a>
### Lägg till kortet manuellt

Integrationen registrerar normalt sitt eget Lovelace-kort.

~~~yaml
type: custom:home-environment-manager-card
~~~

Om din Home Assistant Installationen har mer än en HEM rekommendationssensorn, kan du behöva ange lämpliga **Företag** uttryckligen:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

För stegvis instruktioner om rumkällor, profiler, PID Inställningar, fönsterregler, förberedelse, mögel kalibrering, solskärm och meddelande leverans, använda [detaljerad konfigurationsguide](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Gemenskapsbutik

1. Öppna **HACS** i Home Assistant.
2. Lägg till **Högsta nivån för att kunna uppnå en fullständig och effektiv utveckling** som en **Anpassade arkiv** i den **Integration** Kategori om den inte redan är förtecknad.
3. Hitta **Hemmiljöchef** och installera den.
4. Återstart **Home Assistant** för att ladda integrationen.
5. Gå till **Inställningar → Enheter & tjänster → Lägg till integration**, söka efter **Hemmiljöchef** och slutföra installationen.

<a id="manual-installation"></a>
### Manuell installation

Kopiera arkivet. **custom_components/environment_manager** mapp i matching **custom_components** Förteckning i din Home Assistant konfiguration, vilket bevarar katalognamnet **miljö_manager**- Återstarta. Home Assistant och lägga till integrationen genom **Inställningar → Enheter & tjänster**.

För efterföljande installationsändringar behåll dina befintliga HEM Integrationsinmatning och inställningar. Ladda om instrumentpanelen i din webbläsare om kortets utseende inte uppdateras omedelbart.

<a id="common-questions"></a>
## Vanliga frågor

**Kan jag använda den? HEM utan att ge den kontroll över mina enheter?**

Ja, övervakning, mätningar, ventilationsrådgivning, historia och många miljöindikatorer fungerar utan att enheten aktiveras.

**- Will. HEM automatiskt styra varje enhet den upptäcker?**

Du väljer de fysiska enheter du vill hantera och väljer uttryckligen kontrollmetoden för stödda lägen.

**Stöttar alla apparater PID?**

- Nej, det gör jag inte. HEM Stöd PID för **stödberättigade** uppvärmning, kylning, luftfuktighet eller ventilatorkontrollvägar när apparaten och de valda mätningarna ger de nödvändiga förmågorna och återkopplingen. PID kontroll.

**Kan jag ge varje rum olika regler?**

Ja, arbetsvillkor, sömnbeteende, källor, mål och vissa säkerhetsinställningar kan variera beroende på rum, medan varje fysisk enhet har sina egna drifts- och skyddsinställningar.

**Kan HEM Förbereda mitt hem medan jag är borta?**

- Ja, det är jag. **Förbered dig för ankomsten.** Det innebär inte att man omdirigerar fysiska skydd eller garanterar att ett mål kommer att nås.

**Öppnar en rekommendation om ventilation mina fönster?**

Det förklarar när luftning kan hjälpa. Automatisk rörelse är en separat, opt-in funktion för stödberättigande skugga eller täckningar, föremål för egna säkerhetskontroller.

**Tänk om en sensor eller en enhet inte är tillgänglig?**

HEM Det är viktigt att säkerställa att det är möjligt att kontroll av data som används för att kunna identifiera de aktuella uppgifterna och att kontroll av data som används för att kunna identifiera de aktuella uppgifterna.

<a id="help-and-troubleshooting"></a>
## Hjälp och felsökning

Om något verkar vara fel, kolla i det relevanta rummet eller kontrollörens **Anledningen**, **Diagnostik**, källatillgänglighet och aktuell kontrollmetod [detaljerad konfigurationsguide](../../docs/advanced-configuration.md) omfattar gemensamma väntetillstånd, närvaropolitik, PID Förmåga, fönster och felsökning av enhetens svar.

För ett återskapbart problem, [öppna en GitHub Utgåva](https://github.com/Chreece/HA-Home-Environment-Manager/issues) med det förväntade beteendet, det faktiska beteendet, relevanta rum/enhetsinställningar och steg att reproducera.

Bidrag och förbättringar är välkomna. [Att bidra.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Stöd och licens

Om HEM Det är bra för dig, du kan [Stöd till Grekland på Ko-fi](https://ko-fi.com/chreece).

Fördelade under [MIT-licens](../../LICENSE).
