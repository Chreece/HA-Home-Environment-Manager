<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Home Környezetvédelmi igazgató - intelligensebb levegőminőség, kényelmesség, légzés és éghajlat-ellenőrzés" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="A Bizottság támogatja a Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <strong>Magyar</strong> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Otthoni környezetkezelő

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logó" width="420">
</p>

<p align="center"><strong>Az egész otthoni környezet egy Home Assistant Kártyát.</strong></p>

**HEM segít megérteni a ház körülményeit, és reagálni arra, amire minden szobának szüksége van.** - Ez hozza el a Home Assistant a szenzorok, az időjárási adatok, az elhelyezkedési adatok és a kompatibilis klímaeszközök együtt, így a levegő minőségét figyelemmel kísérheti, hasznos szellőztetési tanácsokat kaphat, a kényelmet kezelheti és automatizálja a kiválasztott berendezést.

Például: HEM a többiek távolságában csökkentheti a fűtést, előkészíti a kiválasztott szobákat, mielőtt visszatér, más nedvességcélot használ, amikor alszik, vagy kér, hogy kinyissák az ablakot, mielőtt a nedvességbontót futtatják. **megfigyelés és ajánlás**, anélkül, hogy irányítaná a készüléket.

**Te maradj a főnök.** Minden szobának saját beállításai vannak, minden támogatott készüléknek saját vezérlője, működési módja, célpontja és biztonsági korlátai vannak. HEM soha nem feltételezi, hogy a készülék kiválasztása engedélyt ad annak a készüléknek a használatára.

[Fedezze fel a jellemzőket](#what-can-hem-do) · [Lásd a felületet](#see-hem-in-action) · [HEM telepítés](#installation) · [Szépítsd ki a házad](#getting-started) · [Fontos útmutató](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Mi lehet? HEM - Nem?

| A helyzeted | Hogyan? HEM Segíthet. |
| --- | --- |
| **A ház üres.** | Átálljon a távol célpontokra, tiszteletben tartsa a szobák jelenlétének szabályait, és elkerülje a kiválasztott berendezés szükségtelen futását. |
| **Hazautazol.** | Nyomás **Készülj fel a megérkezésre!** a jogosult automatikus vezérlők számára ideiglenesen a hazai kényelmes célpontokat használni, még akkor is, ha mindenki még távol van. |
| **Valaki alszik.** | Használjon alvó célpontokat, csökkentse a ventilátor zaját, vagy zárja ki a kiválasztott készüléket, miközben minden elfoglalt szoba alszik. |
| **Az egyik szoba nedves.** | Összehasonlítjuk a nedvesség- és formanyomtatványt a célpontokkal, javasoljuk a hasznos légzést, vagy működtetjük egy engedélyezett dehumidifiert automatikus vagy PID irányítás. |
| **Meleg és napfény.** | Értékelje a szobatemperatúrát, a napfényt, az időjárást és a csatlakoztatott ablakkontaktokat, mielőtt a kiválasztott árnyékokat költöztetné. |
| **A külső levegő jobban néz ki.** | A ventiláció javasolása a belső igény, a külső szennyezés, a hőmérséklet, a páratartalom, a szél és a rendelkezésre álló pollén vagy az időjárási figyelmeztetések alkalmazásával. |
| **A fűtő vagy a TRV nem reagál** | A készülék nem elérhető vagy várakozó állapotának megjelenítése, a konfigurált vezérlő megtartása és a támogatott készülék hibájának bejelentése anélkül, hogy feltételeznénk, hogy a akkumulátor vagy a relais felépült. |

Ezek példák, nem olyan cselekmények, amelyek HEM Az eredmények a kiválasztott érzékelőktől függnek. Home Assistant a funkciók és a beállítások.

<a id="explore-the-features"></a>
## Fedezze fel a jellemzőket

<a id="a-complete-home-dashboard"></a>
### Teljes otthoni panela

Az Európai Parlament HEM a kártya hasznos áttekintést nyújt több integráció kinyitása nélkül.

- Lásd a külső körülmények, a levegőminőség és a szellőztetés javasolt-e.
- Összehasonlítsa az összes ellenőrzött szobát egy pillantásra: hőmérséklet, relatív nedvesség, AQI, PM2.5, formanyomtatás, fény és egyéb támogatott mutatók.
- A részletes mérések, az ablak- és ajtóinformáció, az éghajlatállás, az aktív vezérlő, a várakozás okainak és az épület-fizikai becslések részére bővítsék a teret.
- Tekintse meg a történelmet és a tendenciákat, lássa, hogy mely érzékelők hozzájárultak az átlaghoz, és különböztesse el a hiányzó értékeket a mérett értékektől.
- Csoportszobák tényleges Home Assistant a padlókat, vagy használjon egy egyszerű szobalistát, ha nincs padlója.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### A ház, a szobák és a készülékek különböző beállításai

HEM a közös politikákat a helyi döntésektől elkülönítve tartja.

| A beállítások szintje | Mit konfigurálhatsz? |
| --- | --- |
| **Otthon** | A kültéri időjárás és a szennyezés forrásai, az ellenőrzött helyiségek, a globális szellőztetési határértékek, a háztartások jelenléte, a megérkezésre való felkészülés és a bejelentések eljuttatása. |
| **Szobában.** | A belső hőmérséklet és nedvesség forrásai, a levegőminőség küszöbértékek, az ablak- és ajtókontaktumok, az alvás és a lakóhely viselkedése, a szobás kényelmes célpontok, a szellőztetés és az árnyékolás lehetőségei. |
| **Egyéni berendezés** | A rendelkezésre álló vezérelési módok: Automatikus/Manuális/PID módszer, profilonkénti célpontok, érzékelők, csendes ventilátor beállítása, minimális működési idő, áramvédelem, ablak viselkedés és készülék hibás értesítése. |

Mindhárom szintet csoportosított, kereshető beállításokon keresztül lehet elérni a kártyában. Home Assistant A beállítási változások.

<a id="climate-control-and-pid-device-by-device"></a>
### Az éghajlat-ellenőrzés PID, készülékről készülékre

HEM kompatibilis Home Assistant **éghajlat**, **szűkítő** és **szellőző** berendezések, beleértve a fűtési, hűtő, nedvesítő, nedvesítő és támogatott levegőforgalom vagy levegőtisztító berendezéseket.

Minden egyes esetében **támogatott fizikai működési mód**, függetlenül válasszák ki a ellenőrzési módszert:

| Mód | Mit jelent ez? |
| --- | --- |
| **Meglévő** | A meglévő vezérlő útvonalon hagyja el az üzemeltetést. |
| **Automatikus** | Követni. HEMa mérett kereslet, a helyzetre alapuló célok és engedélyek. |
| **PID** | A készülék és a mérés által támogatott visszajelzés alapú arányos, integrális és származékos vezérlés alkalmazása. |
| **Kézikönyv** | Az ellenőrzés kifejezetten támogatott kérelmek és célpontok révén történik. |
| **- Le!** | Tartsd ki a vezérlőt, a fizikai védelmet és a visszajelzést. |

Például egy légkondicionáló használhatja **PID fűtésre** és **Automatikus hűtés**Egy nedvítőtárkának is lehet sajátja. PID a kalibrálás, a célpontok és a ciklus időzítése. PID a megfelelő visszajelzések és a célspecifikus ellenőrzések rendelkezésre állnak.

PID az **Nem** egyetemes felülírás: HEM A javasolt funkció csak olyan módszereket kínál, amelyeket egy adott eszköz, a működési mód és a visszajelzési forrás támogathat. A fejlett lehetőségek közé tartozik a per-modus behangolás és kalibrálás, a javasolt/adaptív módosítások, a csendes működés és a támogatott felépített ventilátor beállításai. Ön jóváhagyja a javasolt módosításokat, kivéve, ha kifejezetten a korlátozott automatikus adaptációt választja.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Kényelmes otthon, gazdaságos távol.

HEM választhatnak **Kényelmet, otthon, távol, alvás és környezetbarát** a háztartási helyzet, a szobás bizonyítékok és az Ön kifejezett választásai alapján.

- **Otthon és távol:** Használjon különböző fűtési, hűtő és nedvességet célzott célokat a hitelesített otthon jelenlététől függően.
- **A szobás jelenlét:** A jogosult készüléket mindig futtassa el, ha szükség van rá, csak akkor, ha a szobája elfoglalt, vagy csak akkor, ha a szoba üres.
- **Alvás:** A kiválasztott készülék kikapcsolva maradhat, amikor az összes elfoglalt szoba alszik.
- **Öko:** A zárott belső ajtó részt vehet egy védett környezetvédelmi politikában, ha a szobát üresnek ellenőrzik, és más feltételek teljesülnek; a zárott ajtó önmagában nem bizonyítja, hogy a szobát elszigetelve.
- **Ébredés előkészítése:** A következő riasztási forrás konfigurálása esetén hagyja el az automatikus alvást a riasztó előtt, és adjon idő a jogosult eszközökre, hogy reagáljanak.

Ha a beosztás, a készülék rendelkezésre állása vagy más szükséges bizonyítékok bizonytalanak, HEM nem feltételezi egyszerűen, hogy biztonságos az automatikus készülék elindítása.

<a id="prepare-your-environment-before-you-arrive"></a>
### Készítse fel a környezetét, mielőtt megérkezik.

**Készülj fel a megérkezésre!** Ez egy időzített akció egy megerősített távol otthon. HEMA háztartási eszköz.

HEM ideiglenesen alkalmazza a konfigurált **Otthoni célpontok** a jogosult Automatic/PID a vezérlő, hogy a szobák a visszatérés előtt kezdődjenek felmelegedni, hűteni vagy a nedvesség-szabályozásra. Ez ideiglenesen lehetővé teszi a rendszerint a megszállott szobákra korlátozott vezérlő, **csak akkor, ha már rendelkezik a szükséges fizikai ellenőrzési engedéllyel**.

A készülékeknek még mindig valódi igényre, érvényes érzékelőkre és engedélyre van szükségük, és tiszteletben kell tartania az ablakokat, a minimális bekapcsolási/kimaradási időket és a saját védelmüket. Home Assistant Ha újraindítjuk, nem indítjuk újra a teljes időzítést.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Szellőztetés, ablakok, ajtók és árnyékolás

HEM összehasonlít **A szobának mit kell?** az **A külső levegő segíthet-e**.

- Az ablakok megnyitását vagy bezárását a jelenlegi belső mérések, a külső páratartalom, a szennyezés, a hőmérséklet, a szél, az időjárási figyelmeztetések és az önkéntes pollénkontextus alkalmazásával ajánlják.
- Használja a kiválasztott ablak- és ajtókontaktusokat, hogy megmagyarázza a szobás körülményeket, és ne kezelje a ismeretlen kontaktust zárva.
- Választhatóan kérjük, hogy próbáljon kinyitni egy ablakot, mielőtt elindítaná a támogatott automatikus készüléket, majd folytatja a normál vezérléset, miután a konfigurált válasz vár, ha szükséges.
- Használja az ajtók adatait a szoba határérzékeléséhez, a szellőztetési figyelmeztetésekhez és az önkéntes védett környezetvédelmi viselkedéshez.
- A beállított zárokat, függönyöket és árnyékokat megfelelő ablak, hőmérséklet, időjárás, napfelkeltés és a választható világítási bizonyítékok segítségével kezeljük.

HEM Ha a levegőzés segítene, nem nyithatná meg az ablakot önmagában.

<a id="humidity-mold-indication-and-air-quality"></a>
### Sűrűség, formanyomtatás és levegőminőség

HEM támogatott olvasatokat kombinál, mint például: **hőmérséklet, nedvesség, CO2, részecskék, VOC, AQI és világosság** A rendelkezésre álló mérések attól függnek, Home Assistant a telepítés biztosítása.

Az **formanyomtatvány** a hideg felszínen lévő nedvességet a szoba- és a külső hőmérséklet alapján és a kalibrációs mérés alapján becsüli. Ha megfelelően konfigurált, befolyásolhatja a támogatott automatikus nedvességszabályozó hatékony célpontját.

**A moldajelzés egy becslés, nem egy molda- vagy spórátérzékelő.** A hiányzó vagy elavult érzékelőadatok nem indokolhatják az új, formátumokon alapuló eszközirányítást.

<a id="announcements-diagnostics-and-protection"></a>
### Jelentések, diagnosztikák és védelem

A megfelelő ajánlásokat és figyelmeztetéseket a konfigurált Home Assistant értesítések, TTS/médiajátszók vagy **Hírközpont**Az AI megváltoztathatja az üzenet kifejezését. HEMA fizikai ellenőrzési döntések továbbra is meghatározóak.

HEM a készülék-specifikus védelmet és diagnosztikát is magában foglalja:

- Minimális bekapcsolási és kikapcsolási időtartam, maximális működési idő beállítása és támogatott külső áramkapcsoló kezelése.
- Az ablakok és az elhelyezkedés korlátozásai, a kézi átállás kezelése és a helyi parancsellenőrzés.
- Hibák és nem rendelkezésre álló eszközök bejelentése, a bejelentési magatartás kiválasztásával az egyes eszközök esetében.
- A kikapcsolás utáni felügyeleti kutya, amely a kikapcsolási parancsot követően továbbra is fűtésre gyanúsított, a megfigyeléssel és korlátozott helyreállítási kísérletekkel rendelkezik.
- Nyilvánvaló várakozási okok, a jelenlegi működési állapot és a forrás rendelkezésre állása, így meg tud vizsgálni, mielőtt lehetővé tenné a további ellenőrzést.

**A biztonsági határok még akkor is érvényben maradnak, ha a figyelmeztető jelzés kikapcsolva van.** HEM soha nem tekintik a sikeres parancs küldést bizonyítéknak arra, hogy egy készülék fizikai reagált.

<a id="see-hem-in-action"></a>
## Látod? HEM akcióban

Ezek az angol nyelvű illusztrációk minták szobákat és méréseket használnak.

<a id="home-at-a-glance"></a>
### Otthon egy pillantásra

Szerezd meg a szellőztetést, az időjárási feltételeket és a megfigyelett szobák állapotát egyetlen kártyával.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM háztartási képernyő, ahol öt szobában van szellőztetés és környezetértékelés" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Folyamatos részletekre bővítse a szobát.

Ellenőrizze a levegőminőséget, a formanyomtatványt, a jelenlétet, az ablak állapotát, az éghajlat-ellenőrzőket és minden döntés magyarázatait.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="A fürdőszobában kiterjesztett, olvasatokkal és független készülék vezérlőkkel ellátott mérőpult" width="760">
</p>

<a id="home-settings"></a>
### Otthoni beállítások

Kezelje a szabadtéri forrásokat, az egész házban való jelenlétet, a felügyelet alatt álló szobákat, a szellőztetés határértékét, a felkészülést és a értesítéseket.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Otthoni beállítások a kereshető csoportokkal és a forrás- és szoba-kezeléssel" width="900">
</p>

<a id="room-settings"></a>
### A szobák beállításai

Válassza ki, mi számít a szobának: saját érzékelők, célpontok, lakhatóság, ajtók, ablakok, szellőztetés, árnyékolás és biztonsági eszközök.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Csoportok HEM a szenzorok, az eszközvezérlő rendszerek, az alvás, az ablakok és a védelem szobájának beállításai" width="760">
</p>

<a id="device-settings"></a>
### A készülék beállítása

Az egyik készülék finom kiigazítása a többiek megváltoztatása nélkül, beleértve a támogatott vezérlő módszereket is, PID, csendes üzemeltetés, időzítés és hibás bejelentés.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Csoportok HEM a vezérléssel rendelkező berendezés beállításai, PID, energiavédelem és értesítések" width="900">
</p>

<a id="getting-started"></a>
## Kezdődik.

1. **Rendelkezzétek a szobáitokat.** A Home Assistant, létrehozza vagy ellenőrizze a területét, és minden egyes területre a megfelelő érzékelőket és berendezéseket adja.
2. **Válassza ki, mit figyeljen.** Hozzáadás HEMVálasszon ki a szobákat, melyeket érdekli, és nézze át a javasolt hőmérsékletet, nedvességet, ablakokat, levegőminőséget és készülékforrásokat.
3. **A megosztott információk konfigurálása.** Válassza ki a szabadtéri időjárás/ levegőminőségi forrásokat, a háztartási lakosságra vonatkozó bizonyítékokat és a kívánt hirdetési célpontokat.
4. **Adja hozzá a kártyát.** Nyissa ki a panelit a szerkesztési módban, és adja hozzá a **Otthoni környezetkezelő** Kezdje a szobás megfigyelést, az olvasást és a szellőztetést.
5. **Csak akkor engedélyezze a vezérléset, ha hasznos.** Nyisd ki egy szobát, válaszd ki egy támogatott készüléket, nézd át a vezérlőjét, és kifejezetten válaszd ki Automatic vagy PID a kívánt módokhoz HEM operálni.

Te igen. **Nem** Minden szobában kell egy okos készülék. Kezdjük az érzékelőkkel, és vezéreljük be az automatikus vezérlő eszközt egyszerre.

<a id="add-the-card-manually"></a>
### Kezdőlap

Az integráció általában saját Lovelace kártyát regisztrál.

~~~yaml
type: custom:home-environment-manager-card
~~~

Ha a Home Assistant a telepítés több, mint egy HEM ajánlás érzékelő, akkor szükség lehet a megfelelő **Cég** kifejezetten:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

A szobák forrásai, profiljai, PID a beállítások, ablakpolitikák, előkészítés, formák kalibrálása, napfényölítés és bejelentés [részletes konfigurációs útmutató](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Feltöltés

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Közösségi áruház

1. Nyitva **HACS** a Home Assistant.
2. Hozzáadás **Az Európai Parlament és a Tanács (HL L 347., 2011.12., 1. o.).** a) **Személyes tároló** a **Integráció** kategória, ha még nem szerepel a listán.
3. Találd meg **Otthoni környezetkezelő** és telepítem.
4. Újraindítás **Home Assistant** hogy feltöltse az integrációt.
5. Menj! **Beállítások → Felszerelések & szolgáltatások → Integráció hozzáadása**, keresés **Otthoni környezetkezelő** és befejezzük a beépítést.

<a id="manual-installation"></a>
### Kézi telepítés

A tároló másolatai **custom_components/environment_manager** A tároló a megfelelő **custom_components** az Önben található Home Assistant konfiguráció, a címke nevet megtartva **környezet_kezelő**- Újra indítsuk. Home Assistant és az integrációt a **Beállítások → Felszerelések & szolgáltatások**.

A későbbi telepítési módosításokhoz a meglévő HEM integrációs bejegyzés és beállítások. Újra töltsd be a böngésződben lévő műszerpultot, ha a kártya megjelenése nem frissül meg azonnal.

<a id="common-questions"></a>
## Gyakori kérdések

**Használhatom? HEM anélkül, hogy a készülékeim irányítását adná neki?**

Igen, a megfigyelés, a mérés, a szellőztetés, a történelem és számos környezeti jelzés működik anélkül, hogy a készülék aktiválódása lehetővé válna.

**Will. HEM Automatikusan vezérli minden eszközt, amit felfedeznek?**

Nem. Választhatja a kezelni kívánt fizikai eszközöket, és kifejezetten kiválasztja az irányítási módját a támogatott módokhoz.

**Minden készülék támogatja PID?**

- Nem, nem, nem. HEM támogatások PID a **támogatható** fűtési, hűtési, nedvesség- vagy ventilátor-vezérlő útvonalak, ha a készülék és a kiválasztott mérések a szükséges képességeket és visszajelzést biztosítják. PID irányítás.

**Adhatok egy szobának más szabályokat?**

Igen, a lakóhelyek, az alvó viselkedés, a források, a célpontok és a biztonsági preferenciák a szobák szerint eltérhetnek, míg minden fizikai eszköznek saját működési és védelmi beállításai vannak.

**Megtehetem. HEM Ha nem vagyok itt, készítsd fel a házat!**

- Igen, igen, igen. **Készülj fel a megérkezésre!** a jogosult, már felhatalmazott automatikus vezérlők ideiglenesen használhatják az otthoni célpontokat egy meghatározott időtartamra.

**Nyitja-e az ablakok egy  ⁇  jó szellőztető  ⁇  ajánlás?**

Nem. Megmagyarázza, hogy mikor segíthet a légzés. Az automatikus mozgás egy külön, opt-in funkció a támogatható árnyalatok vagy fedélzetek számára, a saját biztonsági ellenőrzések hatálya alá.

**Mi van, ha egy érzékelő vagy eszköz nem áll rendelkezésre?**

HEM a nem ismert adatok és a valós adatok közötti különbséget tesz, ha lehetséges, megőrzi a konfigurált adatkezelő információkat, és felfedheti a várakozási okok és a diagnosztikákat.

<a id="help-and-troubleshooting"></a>
## Segítség és hibaelhárítás

Ha valami rossznak tűnik, ellenőrizze a megfelelő szobát vagy az ellenőrzőt. **Az ok**, **Diagnostika**A következők: [részletes konfigurációs útmutató](../../docs/advanced-configuration.md) a közös várakozási állapotokat, a jelenlétpolitikákat, PID a jogosultság, az ablakok és a készülék-válasz hibaelhárítása.

Egy reprodukálható probléma esetén, [nyitva GitHub kiadás](https://github.com/Chreece/HA-Home-Environment-Manager/issues) a várható viselkedés, a tényleges viselkedés, a megfelelő szobás/eszköz beállításai és a reprodukálandó lépések.

A hozzájárulás és a fejlesztések üdvözölhetők. [COMPRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Támogatás és engedély

Ha HEM Ha hasznos lenne, akkor... [támogatása a Ko-fi-n Chreece számára](https://ko-fi.com/chreece).

Az alábbiakban: [MIT licenc](../../LICENSE).
