<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Domov Ředitel životního prostředí - inteligentnější kvalita ovzduší, komfort, větrání a klimatická kontrola" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Podpora Řecka Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <strong>Čeština</strong> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Domovní manažer životního prostředí

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Celé prostředí vašeho domu, v jednom Home Assistant Kartou.</strong></p>

**HEM pomáhá vášmu domu pochopit jeho okolí a reagovat na to, co každý pokoj vlastně potřebuje.** Přináší vám Home Assistant snímače, údaje o počasí, informace o obsazení a kompatibilní klimatické zařízení společně, abyste mohli sledovat kvalitu vzduchu, získat užitečné poradenství v oblasti větrání, řídit pohodlí a automatizovat vybrané zařízení.

Například: HEM může snížit vytápění, zatímco všichni jsou pryč, připravit vybrané místnosti, než se vrátíte, použít jiný cíl vlhkosti, zatímco spíte, nebo požádat, abyste otevřeli okno před spuštěním dehumidifikátoru. **monitorovat a doporučovat**, bez ovládání žádného zařízení.

**Zůstaň na čele.** Každá místnost má své nastavení, každý podporovaný přístroj má svůj vlastní ovladač, provozní režimy, cíle a bezpečnostní limity. HEM nikdy nepředpokládá, že výběr zařízení mu dává povolení k provozu tohoto zařízení.

[Prozkoumejte charakteristiky](#what-can-hem-do) · [Podívejte se na rozhraní](#see-hem-in-action) · [Nainstalovat HEM](#installation) · [Vytvořte si domov.](#getting-started) · [Detailní průvodce](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Co může HEM - Ano? - Ano.

| Vaše situace | Jak? HEM může pomoci |
| --- | --- |
| **Dům je prázdný.** | Přepněte na cíle pryč, respektujte pravidla přítomnosti každé místnosti a vyhněte se zbytečnému provozu vybraného zařízení. |
| **Jsi na cestě domů.** | Tisk **Připravte se na příjezd.** pro oprávněné automatické ovladače dočasně používat cíle pro domácí pohodlí, i když všichni jsou stále pryč. |
| **Někdo spí.** | Použijte cíle spánku, snižujte hluk ventilátorů nebo vybrané zařízení vypněte, zatímco každý obsazený pokoj spí. |
| **Jedna místnost je vlhká.** | Porovnávejte jeho indikátor vlhkosti a formy s cíli, navrhujte užitečné vylučování nebo provozujte autorizovaný dehumidifikátor pomocí automatického nebo PID Kontroly. |
| **Je to horké a slunečné.** | Vyhodnoťte místnostní teplotu, sluneční světlo, počasí a připojené kontaktní okna, než se přesunete do vybraných odstínů. |
| **Venkovní vzduch vypadá lépe.** | Doporučí se ventilace pomocí poptávky v interiéru, znečištění venku, teploty, vlhkosti, větru a dostupných varování před pollenem nebo počasím. |
| **Hřátel nebo TRV přestávají reagovat** | Zobrazit jeho nedostupný nebo čekající stav, zachovat jeho konfigurovaný ovladač a hlásit chyby podporovaného zařízení, aniž by se předpokládalo, že se baterie nebo relé obnovily. |

To jsou příklady, ne akce, které HEM Výsledky závisí na vybraných senzorech, skutečnosti každého zařízení, Home Assistant možnosti a nastavení přístupu.

<a id="explore-the-features"></a>
## Prozkoumejte charakteristiky

<a id="a-complete-home-dashboard"></a>
### Kompletní domácí palubní deska

Členové HEM karta vám poskytne užitečný přehled bez otevření několika integrací.

- Podívejte se na podmínky venku, kvalitu ovzduší a doporučuje se větrání.
- Porovnávejte všechny monitorované místnosti na jeden pohled: teplotu, relativní vlhkost, AQI, PM2.5, indikátor formy, světlo a další podporované údaje.
- Rozšiřte prostor pro podrobné měření, informace o oknech a dveřích, klimatickém stavu, aktivních kontrolérů, důvodu čekání a odhady budovy-fyziky.
- Podívejte se na historii a trendy, zjistěte, které senzory přispěly k průměru a rozeznáváte chybějící hodnoty od měřených hodnot.
- Skupinné místnosti podle skutečných Home Assistant nebo použít jednoduchý seznam místností, když nemáte podlahu.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Rozdílné nastavení pro dům, každý pokoj a každé zařízení

HEM udržuje sdílené politiky oddělené od místních rozhodnutí.

| Úroveň nastavení | Co můžete konfigurovat |
| --- | --- |
| **Domů** | Vnější počasí a zdroje znečištění, monitorované místnosti, globální limity větrání, přítomnost domácností, příjezdová příprava a doručení oznámení. |
| **Pokoj** | Zdroje vnitřní teploty a vlhkosti, prahové hodnoty kvality ovzduší, kontakty oken a dveří, chování spánku a obsazení, komfortní cíle pro místnost, možnosti větrání a stínování. |
| **Jednotlivé zařízení** | Jeho dostupné režimy ovládání, automatické/manuální/PID metoda, cíle pro profil, senzory, nastavení tichého ventilátoru, minimální provozní doby, ochranná energie, chování oken a upozornění na chybu zařízení. |

Všechny tři úrovně jsou přístupné prostřednictvím skupinových, vyhledatelných nastavení v kartou. Home Assistant změny nastavení.

<a id="climate-control-and-pid-device-by-device"></a>
### Kontrola klimatu a PID, zařízení za zařízení

HEM může fungovat s kompatibilním Home Assistant **klima**, **humidifikátor** a **ventilátor** zařízení, včetně zařízení pro vytápění, chlazení, vyvlhčování, vlhčování a podpůrné zařízení pro oběh vzduchu nebo čištění vzduchu.

Za každý **podporovaný fyzický provozní režim**, zvolit kontrolu nezávisle:

| Metodě | Co to znamená? |
| --- | --- |
| **Existující** | Zastavte provoz s stávající kontrolní dráhou. |
| **Automatické** | Následujte HEMměřená poptávka, cíle založené na situaci a povolení. |
| **PID** | Použijte proporční, integrální a derivativní ovládání založené na zpětné vazbě, pokud je zařízení a měření podporují. |
| **Příruční** | Kontroly prostřednictvím výslovně podporovaných žádostí a cílů. |
| **Zmizte.** | Udržujte ten ovladač vypnutý, s výhradou fyzické ochrany a požadavků na zpětnou vazbu. |

Například jedna klimatizace může použít **PID pro vytápění** a **Automatické chlazení**V dehumidifikátoru může být vlastní PID kalibrace, cílů a cyklu. PID jsou k dispozici vhodné zpětné vazby a specifické kontroly.

PID je **Ne, ne** univerzální předepis: HEM nabízí pouze ty metody, které může určitý zařízení, provozní režim a zdroj zpětné vazby podporovat. Pokročilé možnosti zahrnují nastavení a kalibraci na jednotlivé režimy, navrhované/adaptivní úpravy, tichý provoz a podporované nastavení stadiónového ventilátoru. Souhlasíte s navrhovanými změnami, pokud se výslovně nepostavíte na omezenou automatickou adaptaci.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### V pohodě, když jste doma, ekonomicky, když jste pryč.

HEM může si vybrat **Pohodl, domov, vzdálenost, spánek a životní prostředí** cíle založené na situaci v domácnosti, důkazech o místnosti a vašich výslovných výběrech.

- **Domov a odjezd:** V závislosti na ověřené domácí přítomnosti použijte různé cíle v oblasti vytápění, chlazení a vlhkosti.
- **Přítomnost v místnosti:** Použijte oprávněné zařízení vždy, když je potřeba, pouze když je místnost obsazena nebo pouze když je místnost prázdná.
- **Spánek:** Využijte cíle přes noc a klidnější chování ventilátorů.
- **Ekologické:** Zamčené vnitřní dveře se mohou podílet na ochraně ekologické politiky, pokud je místnost ověřena jako prázdná a jsou splněny jiné podmínky; samotné uzavřené dveře nedokazují, že je místnost izolovaná.
- **Příprava na probuzení:** Použijte nastavený zdroj příštího alarmu, který automaticky opustí spánek před alarmem a poskytne oprávněným zařízenímu čas na odpověď.

Pokud je obsazení, dostupnost zařízení nebo jiné požadované důkazy nejisté, HEM není jednoduše předpokládáno, že je bezpečné spustit automatické zařízení.

<a id="prepare-your-environment-before-you-arrive"></a>
### Připravte své prostředí před příjezdem

**Připravte se na příjezd.** Je to časová akce pro potvrzený odjezd. HEMJe to domácí zařízení.

HEM dočasně použije nastavenou **Domácí cíle** k způsobilému automatickému/PID ovladače, aby místnosti mohly začít vytápět, ochladovat nebo upravovat vlhkost před návratem. **pouze tehdy, pokud již má nezbytné povolení k fyzickému ovládání**.

Příprava není příkaz k tomu, abyste všechno zapnul. Přístroje stále potřebují skutečnou poptávku, platné senzory a oprávnění a musí respektovat okna, minimální dobu zapnutí a vypnutí a vlastní ochranu. Akce končí, když někdo přijde, zrušíte ji nebo skončí nastavený časový řád. Home Assistant restart nezačne plný timer znovu.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Poradenství v oblasti ventilace, oken, dveří a stínování

HEM srovnává **co pokoj potřebuje** s **jestli může pomoci vzduch venku**.

- Doporučujeme otevřít nebo zavřít okna pomocí aktuálních měření vnitřních prostor, vlhkosti venku, znečištění, teploty, větru, varování počasí a volitelného kontextu pylu.
- Použijte vybrané kontaktní okna a dveře k vysvětlení podmínek v místnosti a vyhněte se tomu, aby neznámý kontakt byl považován za uzavřený.
- Pokud je to nutné, požádejte vás, abyste se pokusili otevřít okno před spuštěním podporovaného automatického zařízení, a pak pokračujte v běžném ovládání po skonfiguraci odpovědi.
- Použijte informace o dveřích pro poznání hranic místnosti, varování proti větrání a volitelné ochranné ekologické chování.
- Správte opcionální závěsy, závěsy a odstíny pomocí vhodných oken, teploty, počasí, slunečního vzestupu a volitelného světelného důkazu.

HEM Neotvírá okno samo o sobě jen proto, že by pomohlo ventilace.

<a id="humidity-mold-indication-and-air-quality"></a>
### Vlhkost, označení formy a kvalita vzduchu

HEM kombinuje podporované čtení, jako je **teplota, vlhkost, CO2, částice, VOC, AQI a osvětlení** Dostupné měření závisí na tom, co vaše Home Assistant - Vytvoření.

Je to **označení formy** při správné konfiguraci může ovlivnit účinný cíl podporovaného automatického regulátora vlhkosti.

**Indikace plísní je odhad, ne detektor plísní nebo sporů.** Nedostatek nebo zastaralé údaje senzorů nemohou ospravedlnit nové příkazové zařízení založené na tvaru.

<a id="announcements-diagnostics-and-protection"></a>
### Oznámení, diagnostika a ochrana

Můžete poslat příslušné doporučení a upozornění prostřednictvím konfigurovaných Home Assistant oznámení, TTS/mediální přehrávače nebo **Oznámení**AI může změnit způsob, jak je zpráva formulována; HEMFyzická kontrola zůstává deterministická.

HEM zahrnuje také ochranné prostředky a diagnostiku specifické pro zařízení:

- Minimální doba ON a OFF, maximální nastavení provozního času a podporované ovládání vnějšího přepínače výkonu.
- Omezení oken a obsazení, manuální ovládání a ověření potvrzení vnitřního příkazu.
- Zprávy o chybách a nedostupných zařízeních, s výběrem chování oznámení pro každé zařízení.
- Po ukončení provozu je možný sledovací pes pro podezření na pokračující vytápění po příkazu OFF, s stráženým monitorováním a omezenými pokusy o obnovení.
- Jasné důvody čekání, současný provozní stav a dostupnost zdroje, takže můžete vyšetřit, než umožníte větší kontrolu.

**Bezpečnostní hranice zůstávají v platnosti i v případě, že je výstraha vypnuta.** HEM nikdy nejedná o úspěšnou vysílání jako o důkaz, že zařízení fyzicky reagovalo.

<a id="see-hem-in-action"></a>
## Vidíš ? HEM v akci

V těchto anglicky řečených ilustracích se používají vzorové místnosti a měření, které zobrazují rozhraní místo zobrazení živých dat z konkrétního domu.

<a id="home-at-a-glance"></a>
### Domov na první pohled.

Získejte poradenství o větrání, počasí a stavu každé monitorované místnosti v jedné karte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM domácí palubní deska s poradenstvím ventilace a environmentálními hodnotami v pěti místnostech" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Rozšiřte prostor pro plné detaily

Kontrolovat kvalitu ovzduší, označení formy, přítomnost, stav oken, klimatické regulátory a vysvětlení pro každé rozhodnutí.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Rozšířená palubní deska v koupelně se čtením a nezávislými ovládači zařízení" width="760">
</p>

<a id="home-settings"></a>
### Domácí nastavení

Řídit venkovní zdroje, přítomnost v celém domě, monitorované místnosti, limity větrání, přípravu a oznámení.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Domácí nastavení s vyhledávacími skupinami a správou zdrojů a místností" width="900">
</p>

<a id="room-settings"></a>
### Nastavení místnosti

Vyberte si to, co je pro každý pokoj důležité: vlastní senzory, cíle, obsazení, dveře, okna, větrání, stín a ochranné prostředky.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Skupiny HEM nastavení místnosti pro senzory, ovládání zařízení, spánek, okna a ochranu" width="760">
</p>

<a id="device-settings"></a>
### Nastavení zařízení

Pečlivá nastavení jednoho zařízení bez změny ostatních, včetně podporovaných kontrolních metod, PID, tichý provoz, načasování a hlášení chyb.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Skupiny HEM nastavení zařízení s ovládáním, PID, ochrana elektřiny a oznámení" width="900">
</p>

<a id="getting-started"></a>
## Začínám.

1. **Udělejte si pokoje.** V Home Assistant, vytvořit nebo zkontrolovat své oblasti a přidělit příslušné senzory a zařízení na každý z nich.
2. **Vyberte si, co budete sledovat.** Přidání HEMVyberte si místnosti, které vám záleží, a zkontrolujte navrhované teploty, vlhkost, okna, kvalitu vzduchu a zdroje zařízení.
3. **Konfigurovat sdílené informace.** Vyberte si dostupné zdroje mimozemského počasí/kvalitního ovzduší, důkazy o domácnosti a jakékoliv cíle oznámení, které chcete.
4. **Přidejte kartu.** Otevřete palubní desku v režimu úpravy a přidejte **Domácí manažer životního prostředí** Začněte s monitorováním místnosti, s odhalením a s poradenstvím o ventilaci.
5. **Umožněte kontrolu pouze tam, kde je to užitečné.** Otevřete místnost, vyberte podporovaný přístroj, zkontrolujte jeho ovladač a výslovně vyberte Automatický nebo PID pro režimy, které chcete HEM k operaci.

Ty ano. **Ne, ne** Začněte s senzory, které máte, a zavedte automatické ovládání jeden přístroj najednou.

<a id="add-the-card-manually"></a>
### Přidejte kartu ručně

Pokud preferujete YAML, použijte:

~~~yaml
type: custom:home-environment-manager-card
~~~

Pokud vaše Home Assistant instalace má více než jednu HEM doporučení snímače, můžete potřebovat nastavit vhodný **subjekt** výslovně:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Pro krok za krokem pokyny o zdrojích místností, profilech, PID nastavení, pravidla pro okna, příprava, kalibrace tvaru, sluneční stínování a doručení oznámení, používat [podrobné příručky pro konfiguraci](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Instalace

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Obchod Společenství

1. Otevřeno **HACS** v Home Assistant.
2. Přidání **Hospodářský plán** jako **individuální úložiště** v rámci **Integrace** kategorie, pokud již není uveden.
3. Najděte **Domácí manažer životního prostředí** a nainstalovat ho.
4. Zpětovný start **Home Assistant** Vytáhnout integraci.
5. Běžte. **Nastavení → Přístroje a služby → Přidání integrace**, vyhledávání **Domácí manažer životního prostředí** a dokončit nastavení.

<a id="manual-installation"></a>
### Ruční instalace

Kopírovat databáze. **custom_components/environment_manager** složka do odpovídající **custom_components** adresář ve vašem Home Assistant konfigurace, zachování názvu adresáře **environment_manager**- Znovu zažít . Home Assistant a doplnit integraci prostřednictvím **Nastavení → Přístroje a služby**.

Pro následné změny instalace uchovejte stávající HEM integrační položka a nastavení. V případě, že se vzhled karty neobjeví okamžitě, znovu načtejte palubní desku ve vašem prohlížeči.

<a id="common-questions"></a>
## Časté otázky

**Můžu použít HEM bez toho, aby jí dal kontrolu nad mými zařízeními?**

Ano, monitorování, měření, poradenství v oblasti větrání, historie a mnohé okolní indikace fungují bez umožnění aktivace zařízení.

**- Will. HEM automaticky ovládá každé zařízení, které objeví?**

Ne. Vyberte si fyzické zařízení, které chcete spravovat, a výslovně si vyberete řídící metodu pro podporované režimy.

**Podporuje každé zařízení PID?**

- Ne, ne, ne, ne. HEM podpora PID pro **způsobilé** ohřívací, chlazení, vlhkosti nebo ovládací dráhy ventilátorů, pokud zařízení a vybrané měření poskytují potřebné schopnosti a zpětnou vazbu. PID Kontroly.

**Můžu dát každému pokoji různá pravidla?**

Ano, podmínky pobytu, chování spánku, zdroje, cíle a některé bezpečnostní preference se mohou lišit podle místnosti, zatímco každý fyzický zařízení má své vlastní operační a ochranné nastavení.

**Může HEM Připravit můj domov, zatímco jsem pryč?**

- Ano, to je pravda. **Připravte se na příjezd.** V případě, že se jedná o zařízení, které jsou v souladu s právními předpisy a které jsou již oprávněny, může být automatický kontrolor dočasně používán na omezenou dobu, neohlíží se fyzická ochrana ani nezaručuje dosažení cíle.

**Otvírá se mé okna doporučení pro ventilaci?**

Automatické pohyby jsou samostatnou funkcí pro způsobilé podporované odstíny nebo krytí, které podléhají vlastní bezpečnostní kontrole.

**Co když se snímač nebo zařízení stane nedostupným?**

HEM automatické ovládání stále vyžaduje platnou současnou autoritu a důkazy.

<a id="help-and-troubleshooting"></a>
## Pomoc a řešení problémů

Pokud se něco zdá být špatně, zkontrolujte příslušnou místnost nebo kontrolor **Důvod**, **Diagnostika**, dostupnost zdroje a současná kontrola. [podrobné příručky pro konfiguraci](../../docs/advanced-configuration.md) zahrnuje společné čekovací podmínky, politiku přítomnosti, PID způsobilost, okna a řešení problémů při odpovědi zařízení.

Pro reprodukovatelný problém, [otevřít GitHub Vydání](https://github.com/Chreece/HA-Home-Environment-Manager/issues) s očekávaným chováním, skutečným chováním, příslušnými nastavením místnosti/stroje a krokmi k reprodukci.

Příspěvky a zlepšení jsou vítány. [Příspěvek.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Podpora a licence

Pokud HEM Je vám užitečné, můžete [Podpora ČR na Ko-fi](https://ko-fi.com/chreece).

Rozdělené v rámci [Licence MIT](../../LICENSE).
