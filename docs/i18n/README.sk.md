<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Domov manažér životného prostredia - inteligentnejšia kvalita ovzdušia, komfort, ventilácia a kontrola klímy" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Podpora Chreece na Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <strong>Slovenčina</strong> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Domáci manažér životného prostredia

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Celé prostredie vášho domova, v jednom Home Assistant Karta.</strong></p>

**HEM pomáha vášmu domu pochopiť okolie a reagovať na to, čo každá izba skutočne potrebuje.** Prinesie vám Home Assistant snímače, údaje o počasí, informácie o obsadení a kompatibilné klimatické zariadenia spolu, aby ste mohli monitorovať kvalitu ovzdušia, získať užitočné poradenstvo v oblasti vetrenia, riadiť pohodlie a automatizovať vybrané zariadenie.

Napríklad: HEM môže znížiť vykurovanie, kým sú všetci preč, pripraviť vybrané miestnosti pred návratom, použiť iný cieľ vlhkosti počas spánku alebo požiadať o otvorenie okna pred spustením dehumidifikátoru. **monitorovať a odporúčať**, bez ovládania žiadneho zariadenia.

**Zostaň na čele.** Každá izba má svoje nastavenia, každý podporovaný prístroj má svoj vlastný ovládač, prevádzkové režimy, ciele a bezpečnostné limity. HEM nikdy nepredpokladá, že výber zariadenia mu dáva povolenie na prevádzku tohto zariadenia.

[Prečítajte si jeho charakteristiky](#what-can-hem-do) · [Pozrite rozhranie](#see-hem-in-action) · [Vložte HEM](#installation) · [Ustanovte si domov](#getting-started) · [Podrobné vedenie](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Čo môže HEM - Áno?

| Vaša situácia | Ako sa to stalo? HEM môže pomôcť |
| --- | --- |
| **Dom je prázdny .** | Prejdite na cieľy preč, rešpektujte pravidlá prítomnosti každej miestnosti a vyhýbajte sa zbytočnému prevádzkovaniu vybraného vybavenia. |
| **Si na ceste domov.** | Tlač **Pripravte sa na príchod** na dočasné používanie cieľov pohodlia pre oprávnené automatické ovládače, aj keď všetci sú stále preč. |
| **Niekto spí.** | Používajte spánkové ciele, znížte hluk ventilátorov alebo vypnite vybrané zariadenia, zatiaľ čo každá obsadená izba spí. |
| **Jedna izba je vlhká.** | Porovnávajte jeho indikáciu vlhkosti a formy s cieľmi, navrhujte užitočné ovzdušnenie alebo prevádzkovať autorizovaný dehumidifikátor pomocou automatického alebo PID riadenie. |
| **Je horúce a slnečné.** | Vyhodnoťte miestnostnú teplotu, slnečné svetlo, počasie a pripojené kontaktné okná pred presunom zvolených odtieňov. |
| **Vzduch vonku vyzerá lepšie.** | Odporúča sa ventilácia pomocou dopytu v interiéri, znečisťovania vonku, teploty, vlhkosti, vetra a dostupných varovaní o pôde alebo počasí. |
| **Ohrievač alebo TRV prestane reagovať** | Predstaviť jeho nedostupný alebo čakajúci stav, zachovať konfigurovaný ovládač a hlásiť chyby podporovaného zariadenia bez predpokladu, že batéria alebo relé sa obnovili. |

Toto sú príklady, nie akcie, ktoré HEM Výsledky závisia od vybraných senzorov, Home Assistant možnosti a nastavenia opt-in.

<a id="explore-the-features"></a>
## Prečítajte si jeho charakteristiky

<a id="a-complete-home-dashboard"></a>
### Kompletná domáca prístrojová doska

V prípade HEM karta vám poskytuje užitočný prehľad bez toho, aby ste otvorili niekoľko integrácií.

- Pozrite sa na vonkajšie podmienky, kvalitu ovzdušia a na to, či je vhodné ventiláciu.
- Porovnávajte všetky monitorované miestnosti na jedno pohľad: teplotu, relatívnu vlhkosť, AQI, PM2.5, indikáciu formy, svetlo a iné podporované údaje.
- Rozšírte priestor pre podrobné merania, informácie o oknoch a dverách, klimatický stav, aktívne riadiace zariadenia, dôvody čakania a odhady fyziky budovy.
- Pozrite si históriu a trendy, pozrite, ktoré senzory prispievali k priemerovi a rozoznajte chýbajúce odčítania od meraných hodnôt.
- Skupinné izby podľa skutočných Home Assistant podlahy, alebo použite jednoduchý zoznam miestností, keď nemáte podlahy.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Rôzne nastavenia pre domov, pre každý izbu a pre každé zariadenie

HEM zachováva zdieľané politiky oddelené od miestnych rozhodnutí.

| Úroveň nastavení | Čo môžete nastaviť |
| --- | --- |
| **Domov** | Počasie vonku a zdroje znečisťovania, monitorované miestnosti, globálne limity vetrania, prítomnosť domácností, príprava na príchod a doručenie oznámenia. |
| **Izba** | Zdroje vnútornej teploty a vlhkosti, prahové hodnoty kvality ovzdušia, kontakty s oknami a dverami, správanie sa v spánku a v obytných priestoroch, komfortné ciele pre miestnosť, možnosti ventilácie a stíhania. |
| **Jednotlivé zariadenie** | Jeho dostupné režimy ovládania, automatické/ručné/PID metóda, ciele na profil, senzory, nastavenia tichého ventilátoru, minimálne prevádzkové časy, ochranu výkonu, správanie okna a upozornenia na chybu zariadenia. |

Všetky tri úrovne sú prístupné prostredníctvom zoskupených, vyhľadateľných nastavení v karte. Home Assistant zmeny nastavenia.

<a id="climate-control-and-pid-device-by-device"></a>
### Kontrola klímy a PID, zariadenie za zariadením

HEM môže pracovať s kompatibilnými Home Assistant **podnebie**, **vlhčovač** a **ventilátor** zariadenia, vrátane vykurovania, chladenia, vyvlhčovania, vlhčovania a podporovaných zariadení na obeh vzduchu alebo čistenie vzduchu.

Za každú **podporovaný fyzický prevádzkový režim**, zvoľte nezávisle metódu kontroly:

| Metóda | Čo to znamená |
| --- | --- |
| **Existujúce** | Opustiť prevádzku s existujúcim smerom ovládača. |
| **Automatické** | Sledujte HEMmerané dopyt, ciele a povolenia založené na situácii. |
| **PID** | Používajte na základe spätnej väzby proporcionálnu, integrálnu a derivátovú reguláciu, ak ju zariadenie a meranie podporujú. |
| **Príručka** | Kontrola prostredníctvom výslovne podporovaných požiadaviek a cieľov. |
| **Zmiznite .** | Udržujte ten ovládač vypnutý, podliehajúc požiadavkám fyzickej ochrany a spätnej väzby. |

Napríklad jeden klimatizátor môže používať **PID na vykurovanie** a **Automatické chladenie**Odvlhčovač môže mať svoj vlastný PID kalibrácia, ciele a časovanie cyklu. PID ak sú k dispozícii vhodné spätné väzby a špecifické kontroly.

PID je **nie** univerzálna prekážka: HEM Ponúka len metódy, ktoré môže podporovať konkrétne zariadenie, prevádzkový režim a zdroj spätnej väzby. Pokročilé možnosti zahŕňajú nastavenie a kalibráciu na jednotný režim, navrhované/adaptívne úpravy, tiché prevádzky a podporované nastavenia fanúšikov.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Komfortný, keď ste doma, ekonomický, keď ste preč.

HEM môže si vybrať medzi **Komfort, dom, vzdialenosť, spánok a životné prostredie** ciele založené na situácii domácnosti, dôkazoch miestnosti a vašich výslovných výberov.

- **Domov a odchod:** Používajte rôzne ciele vykurovania, chladenia a vlhkosti v závislosti od overenej prítomnosti doma.
- **Prítomnosť v miestnosti:** Používajte oprávnené zariadenie vždy, keď existuje dopyt, iba vtedy, keď je miestnosť obsadená alebo len vtedy, keď je miestnosť prázdna.
- **Spanie:** Používajte cez noc ciele a tichšie správanie ventilátorov. Vybrané zariadenie môže zostať vypnuté, keď všetky obsadené izby spajú.
- **Ekologické:** Zamknuté vnútorné dvere sa môžu zapojiť do ochrany životného prostredia, keď je miestnosť overená ako prázdna a splnené sú iné podmienky; samotné zatvorené dvere neprikladú, že je miestnosť izolovaná.
- **Príprava na prebudenie:** Použite nastavený zdroj ďalšieho výstrahu, aby ste automaticky opustili spánok pred výstrahom a umožnili oprávneným zariadeniam čas na reakciu.

Ak je obsadenie, dostupnosť zariadenia alebo iné požadované dôkazy neisté, HEM nie je jednoducho predpokladané, že je bezpečné spustiť automatické zariadenie.

<a id="prepare-your-environment-before-you-arrive"></a>
### Pripravte svoje prostredie pred príchodom

**Pripravte sa na príchod** Je to časová akcia pre potvrdený domov. HEMJe to domáce zariadenie.

HEM dočasne uplatňuje konfigurované **Domáce ciele** k oprávnenému automatickému/PID regulátory, aby miestnosti mohli začať vykurovať, chladiť alebo upraviť vlhkosť pred návratom. **len vtedy, ak má už potrebné povolenie na fyzický kontrolu**.

Príprava nie je príkaz, aby sa všetko zapájalo. Zariadenia stále potrebujú skutočnú dopyt, platné senzory a povolenie, a musia rešpektovať okná, minimálne načasy ON/OFF a ich vlastné ochrany. Akcia končí, keď príde niekto, zrušíte ju, alebo skonfigúrovaný timer vyprší. Home Assistant Restart nezačne plný timer.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Poradenstvo v oblasti ventilácie, okien, dverí a zastenia

HEM porovnáva **Čo potrebuje izba** s **či môže pomôcť vonkajší vzduch**.

- Odporúča sa otvárať alebo zatvárať okná s použitím súčasných meraní vnútorných priestorov, vlhkosti vonku, znečistenia, teploty, vetra, varovných informácií o počasí a možnosti kontextu pylov.
- Použite vybrané kontaktné okná a dvere, aby ste vysvetlili podmienky v miestnosti a vyhnite sa neznámu kontaktu, aby ste ho považovali za zatvoreného.
- Ak chcete, môžete sa pokúsiť otvoriť okno pred spustením podporovaného automatického zariadenia, potom pokračujte v normálnej kontrole po skonfigurovanej reakcii čakať, ak je to potrebné.
- Používajte informácie o dverách na informáciu o hraniciach miestnosti, varovanie pred vetraním a voliteľné ochranné správanie Eco.
- Správte nastavené závesy, závesy a odtiene pomocou vhodných oknov, teploty, počasia, výšky slnka a optických dôkazov o osvetlení.

HEM V tomto prípade je potrebné stanoviť, či je možné, aby sa pri ventilácii bez kontrolovateľných okien neotvorilo okno samo o sebe len preto, že by to pomohlo s ventiláciou.

<a id="humidity-mold-indication-and-air-quality"></a>
### Vlhkosť, indikácia formy a kvalita ovzdušia

HEM kombinuje podporované odčítania, ako sú **teplota, vlhkosť, CO2, častice, VOC, AQI a osvetlenie** Z dostupných meraní závisí na tom, čo sa deje v každej izbe. Home Assistant nastavenie zabezpečuje.

Je to **indikácia formy** odhadne podmienky vlhkosti na studenom povrchu z miestnosti a vonkajšej teploty a kalibračného merania.

**Indikácia plesní je odhad, nie detektor plesní alebo sporov.** Chýbajúce alebo zastaralé údaje snímača nemôžu ospravedlniť nové príkazové zariadenie založené na plesni.

<a id="announcements-diagnostics-and-protection"></a>
### Oznámenia, diagnostika a ochrana

Môžete poslať príslušné odporúčania a upozornenia prostredníctvom konfigurovaných Home Assistant oznámenia, TTS/media player alebo **Oznámenie centrum**AI môže zmeniť spôsob, akým sa správa formuluje; HEMFyzická kontrola rozhodnutia zostávajú deterministické.

HEM zahŕňa aj ochranu a diagnostiky špecifické pre zariadenie:

- Minimálne doby zapnutia a vypnutia, maximálne nastavenia prevádzkových hodín a podporované ovládanie exteriérnych prepínačov napájania.
- Obmedzenia okna a obývania, ručné ovládanie a kontroly potvrdenia príkazov.
- Správa o chybe a nedostupnosti zariadenia s výberom správania oznamovania pre každé zariadenie.
- Voliteľný sledovací pes po vypnutí pre podozrenie na pokračovanie vykurovania po príkazu OFF, s stráženým monitorovaním a obmedzenými pokusmi o obnovu.
- Jasné dôvody čakania, aktuálny prevádzkový stav a dostupnosť zdroje, takže môžete prešetriť pred umožnením väčšej kontroly.

**Bezpečnostné hranice zostávajú v platnosti aj vtedy, keď je výstraha vypnutá.** HEM nikdy neberie úspešnú príkazovú vyslanie ako dôkaz, že zariadenie fyzicky reagovalo.

<a id="see-hem-in-action"></a>
## Pozri . HEM v akcii

Tieto anglicky vysvetlené obrázky používajú vzorové miestnosti a merania, ktoré preukazujú rozhranie namiesto zobrazovania živých údajov z konkrétneho domu.

<a id="home-at-a-glance"></a>
### Domov na pohľad

Získajte poradenstvo o ventilácii, počasie a stav každej monitorovanej miestnosti v jednej karte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM domáca prístrojová doska s poradenstvom o vetrane a environmentálnych odčítaniach v piatich miestnostiach" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Rozširovať priestor pre plné detaily

Kontrolovať kvalitu ovzdušia, indikáciu pleti, prítomnosť, stav okna, klimatické regulátory a vysvetlenie každého rozhodnutia.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Rozšírená prístrojová doska v kúpeľni s čitateľmi a nezávislými riadiacimi zariadeniami" width="760">
</p>

<a id="home-settings"></a>
### Nastavenie domova

Správa vonkajších zdrojov, prítomnosti v celom dome, monitorovaných miestností, limitov ventilácie, prípravy a oznámení.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Nastavenia domova s vyhľadateľnými skupinami a riadením zdrojov a miestností" width="900">
</p>

<a id="room-settings"></a>
### Nastavenia miestnosti

Vyberte si to, čo je pre každú miestnosť dôležité: vlastné senzory, ciele, obývanie, dvere, okná, ventilácia, stíhanie a ochranné prostriedky.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Vyrobené HEM nastavenia miestnosti pre senzory, ovládacie zariadenia, spánok, okná a ochranu" width="760">
</p>

<a id="device-settings"></a>
### Nastavenia zariadenia

Pevné nastavenie jedného zariadenia bez zmeny ostatných vrátane podporovaných ovládacích metód, PID, tichá prevádzka, načasovanie a hlásenie chyb.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Vyrobené HEM nastavenia zariadenia s ovládaním, PID, ochrana elektrickej energie a oznámenia" width="900">
</p>

<a id="getting-started"></a>
## Začínam

1. **Uistite sa, že vaše izby sú organizované.** V Home Assistant, vytvorte alebo skontrolujte svoje oblasti a priradite každému vhodné senzory a zariadenia.
2. **Vyberte si, čo sledovať.** Pridať HEMVyberte si miestnosti, ktoré vás zaujímajú, a preskúmajte navrhovanú teplotu, vlhkosť, okná, kvalitu vzduchu a zdroje zariadenia.
3. **Konfigurovať zdieľané informácie.** Vyberte dostupné zdroje počasia/kvalitu ovzdušia, dôkazy o obývaní domácností a akékoľvek reklamné destinácie, ktoré chcete.
4. **Pridajte kartu.** Otvorte paneli v režime úpravy a pridajte **Domáce manažér životného prostredia** Začnite s monitorovaním miestnosti, odčítaním a poradenstvom o ventilácii.
5. **Umožniť ovládanie len tam, kde je užitočné.** Otvorte miestnosť, vyberte podporované zariadenie, preskúmajte jeho ovládač a výslovne vyberte Automatické alebo PID pre režimy, ktoré chcete HEM operovať.

Ty áno. **nie** Začnite s senzormi, ktoré máte, a začnite automaticky ovládať jedno zariadenie naraz.

<a id="add-the-card-manually"></a>
### Pridajte kartu ručne

Integrácia zvyčajne zaregistruje vlastnú kartu Lovelace.

~~~yaml
type: custom:home-environment-manager-card
~~~

Ak váš Home Assistant inštalácia má viac ako jednu HEM odporúčané snímače, možno budete musieť nastaviť vhodný **subjekt** výslovne:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Pre postupné pokyny o zdrojoch miestnosti, profiloch, PID nastavenia, politiky okien, príprava, kalibrácia plesní, slnečné zastreľovanie a doručovanie oznámení, používať [podrobné príručné konfigurácie](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Instalácia

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Občanský obchod

1. Otvorené **HACS** v Home Assistant.
2. Pridať **Hospodárska spolupráca v oblasti životného prostredia** ako **vlastný repository** v **Integrácia** kategória, ak nie je už uvedená na zozname.
3. Nájsť **Domáce manažér životného prostredia** a nainštalovať ho.
4. Opätovné spustenie **Home Assistant** na zaťaženie integrácie.
5. Choď na **Nastavenia → Zariadenia a služby → Pridanie integrácie**, vyhľadávanie **Domáce manažér životného prostredia** a dokončiť nastavenie.

<a id="manual-installation"></a>
### Ručná inštalácia

Kopírovanie skladov **custom_components/environment_manager** Do súboru zhody **custom_components** adresár vo vašom Home Assistant konfigurácia, zachovanie názvu adresára **environment_manager**Opätovné spustenie . Home Assistant a pridať integráciu prostredníctvom **Nastavenia → Zariadenia a služby**.

Na následné zmeny inštalácie uchovávajte existujúce HEM integrácia a nastavenia. V prípade, že vzhľad karty sa okamžite neobnoví, preberte kontrolnú dosku vo vašom prehliadači.

<a id="common-questions"></a>
## Časté otázky

**Môžem použiť HEM bez toho, aby som mu dal kontrolu nad mojimi zariadeniami?**

Áno, monitorovanie, meranie, poradenstvo o ventilácii, dejiny a mnohé environmentálne indikácie fungujú bez toho, aby zariadenie mohlo byť aktivované.

**Will . HEM automaticky ovládať každé zariadenie, ktoré objaví?**

Nie. Vyberte fyzické zariadenia, ktoré chcete spravovať a výslovne si vyberte ovládaciu metódu podporovaných režimov.

**Podporuje každé zariadenie PID?**

- Nie, nie, nie. HEM podpory PID pre **oprávnené** Hrievanie, chladenie, vlhkosť alebo ovládanie ventilátorov, keď zariadenie a vybrané merania poskytujú potrebné schopnosti a spätnú väzbu. PID riadenie.

**Môžem dať každému izbe rôzne pravidlá?**

Áno. Podmienky obývania, správanie sa pri spánku, zdroje, ciele a niektoré bezpečnostné preferencie sa môžu líšiť podľa miestnosti, pričom každé fyzické zariadenie má svoje vlastné nastavenia prevádzky a ochrany.

**Môžeš HEM Pripraviť môj dom, kým som preč?**

- Áno, áno. **Pripravte sa na príchod** dočasne umožňuje oprávneným, už autorizovaným automatickým riadiacim orgánom využívať domáce ciele na obmedzený čas. Neobchádza s fyzickou ochranou ani zaručuje dosiahnutie cieľa.

**Otvorí mi odporúčanie na ventiláciu okná?**

Automatické pohyby sú samostatnou funkciou pre oprávnené podporované odtieňové alebo krytie, ktoré podliehajú vlastným bezpečnostným kontrolám.

**Čo ak sa snímač alebo zariadenie stane nedostupným?**

HEM automatická kontrola stále vyžaduje platnú platnosť a dôkazy.

<a id="help-and-troubleshooting"></a>
## Pomoc a riešenie problémov

Ak sa niečo zdá byť v poriadku, skontrolujte príslušnú miestnosť alebo kontrolér **Dôvody**, **Diagnostika**, dostupnosť zdroja a súčasná metóda kontroly. [podrobné príručné konfigurácie](../../docs/advanced-configuration.md) zahŕňa spoločné čakané štáty, politiky prítomnosti, PID oprávnenosť, okná a riešenie problémov pri odpovedi zariadenia.

Pre reprodukovateľný problém, [otvoriť GitHub Vydanie](https://github.com/Chreece/HA-Home-Environment-Manager/issues) s očakávaným správaním, skutočným správaním, relevantnými nastavením miestnosti/ zariadenia a kroky na reprodukciu.

Príspevky a zlepšenia sú vítané. [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Podpora a povolenie

Ak HEM je užitočné pre vás, môžete [Podpora Grécka na Ko-fi](https://ko-fi.com/chreece).

Rozdeľované v rámci [Licencia MIT](../../LICENSE).
