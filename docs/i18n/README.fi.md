<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Kotimainen ympäristöjohtaja - älykkäämpi ilmanlaatu, mukavuus, tuuletus ja ilmasto" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Toiminta Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <strong>Suomi</strong> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Kotiympäristöjohtaja

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Koko kotiympäristösi yhdessä Home Assistant Kortti.</strong></p>

**HEM auttaa talosi ymmärtämään ympäristönsä ja reagoimaan siihen, mitä jokainen huone todella tarvitsee.** Se tuo sinut Home Assistant Sensorit, säätiedot, käyttötiedot ja yhteensopivat ilmastolaitteet yhdessä, jotta voit seurata ilmanlaatua, saada hyödyllisiä ilmanvaihto-ohjeita, hallita mukavuutta ja automatisoida valitsemasi laitteet.

Esimerkiksi: HEM voi vähentää lämmitystä, kun kaikki ovat poissa, valmistaa tiettyjä huoneita ennen palaamista, käyttää erilaista kosteuden kohdentaa nukkumisen aikana tai pyytää sinua avaamaan ikkunan ennen kuin käytät nesteenpoistoa. **seurata ja suositella**, ilman laitteen hallintaa.

**Pysy johdossa.** Jokaisella huoneella on omat asetukset, jokaisella laitteella on omat ohjaimet, toimintatapa, tavoitteet ja turvallisuusrajoitukset. HEM ei koskaan oletta, että laitteen valinta antaa sille luvan käyttää sitä laitteen.

[Tutki ominaisuudet](#what-can-hem-do) • [Näytä käyttöliittymä](#see-hem-in-action) • [Asennetaan HEM](#installation) • [Aseta kotisi](#getting-started) • [Yksityiskohtainen opas](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Mikä voi HEM - Onko se totta?

| Sinun tilanteesi | Miten? HEM voi auttaa |
| --- | --- |
| **Talo on tyhjä .** | Vaihda kohteet pois, kunnioita jokaisen huoneen läsnäolon sääntöjä ja vältä valikoitujen laitteiden käyttöä tarpeettomasti. |
| **Olet matkalla kotiin.** | Paina **Valmistautukaa saapumiselle.** Toimittajien on käytettävä automaattisia ohjaimia, vaikka kaikki ovat vielä poissa. |
| **Joku nukkuu.** | Käytä nukkumistavoitteita, vähentä ventilattorin melua tai pidä valinnut laitteet poissa, kun kaikki huoneet nukkuvat. |
| **Yksi huone on kosteaa .** | Vertaile sen kosteuden ja muodon merkitystä kohteiden kanssa, ehdottele hyödyllistä ilmastointia tai käytä hyväksytty deshumidifioija käyttämällä automaattista tai PID Valvonta. |
| **Se on kuuma ja aurinkoinen.** | Arvioida huoneen lämpötila, auringonvalo, sää ja liitetty ikkunan yhteys ennen kuin siirretään valitut sävyet. |
| **Ulkopuolinen ilma näyttää paremmalta .** | Suosittelemme ilmanvaihtoa, jossa käytetään sisätilojen kysyntää, ulkona olevaa pilaantumista, lämpötilaa, kosteutta, tuulta ja käytettävissä olevaa pölyä tai säävaroituksia. |
| **Kylämmitti tai TRV pysähtyy** | Näytä sen käytettävissä oleva tai odottava tila, säilytä sen konfiguroitu ohjain ja ilmoita tuettujen laitteiden virheistä oletamatta, että akku tai rele on toipunut. |

Nämä ovat esimerkkejä, eivätkä toimia, jotka HEM Tulokset riippuvat valittuista antureista. Home Assistant mahdollisuudet ja opt-in-asetuksesi.

<a id="explore-the-features"></a>
## Tutki ominaisuudet

<a id="a-complete-home-dashboard"></a>
### Kokonainen kotimatka

Euroopan parlamentin ja neuvoston HEM kortti antaa hyödyllisen yleiskuvan avaamatta useita integraatioita.

- Katso ulkona olevat olosuhteet, ilmanlaatu ja onko ilmanvaihto suositeltavaa.
- Vertaile kaikki tarkkailtuja huoneita silmäyksellä: lämpötila, suhteellinen kosteus, AQI, PM2.5, muova-indikaatio, valo ja muut tukevat lukemat.
- Täydellisten mittausten, ikkunan ja oven tietojen, ilmastotilannan, aktiivisten ohjainten, odottamisperusteiden ja rakennusfysiikan arvioiden tilaa laajennetaan.
- Katso historiaa ja trendejä, katso, mitkä anturit vaikuttivat keskimäärään ja erota puuttuvat lukemukset mitattuista arvoista.
- ryhmähuoneet todellinen Home Assistant tai käyttää yksinkertaista huoneen luetteloa, kun sinulla ei ole lattia.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Eri asetukset kotonaan, huoneeseen ja laitteeseen

HEM Se pitää yhteiset politiikat erillään paikallisista päätöksistä.

| Asetusten taso | Mitä voit säätää |
| --- | --- |
| **Koti** | Ulkona oleva sää ja saastumisen lähteet, valvontahuoneet, maailmanlaajuiset ilmanvaihdon rajoitukset, kotitalouksien läsnäolo, saapumisvalmistautuminen ja ilmoituksen toimittaminen. |
| **Huone** | Sisätilojen lämpötila- ja kosteuslähteet, ilmanlaatujen kynnykset, ikkunan ja oven yhteydet, nukkumisen ja asennuksen käyttäytyminen, huoneen erityiset mukavuuden tavoitteet, tuuletus- ja varjostusvaihtoehdot. |
| **Yksittäinen laite** | Sen käytettävissä olevat ohjauslaitteet: automaattinen/käsikirjainen/PID menetelmä, profiilikohtaiset kohteet, anturit, hiljaiset ventilaattoriasetukset, vähimmäis käyttöajat, sähkön suojat, ikkunan käyttäytyminen ja laitteen virheilmoitukset. |

Kaikki kolme tasoa on käytettävissä kortin ryhmitettyihin, etsimiseen käytettävissä oleviin asetuksiin. Home Assistant asennusmuutokset.

<a id="climate-control-and-pid-device-by-device"></a>
### Ilmastonhallinta ja PID, laite laite

HEM voi toimia yhteensopivilla Home Assistant **ilmasto**, **Hämmittäjä** ja **tuulilaite** laitteet, mukaan lukien lämmitys, jäähdytys, kosteuttaminen, kosteuttaminen ja ilmankierto tai ilmanpuhdistuslaitteet.

Jokaiselle **tuettu fyysinen käyttötapa**, valitsee valvontametodista itsenäisesti:

| Menetelmä | Mitä se tarkoittaa |
| --- | --- |
| **Käytännössä** | Jätä käyttöä olemassa olevalla ohjaimen polulla. |
| **Automaattinen** | Seuraa HEMSääntöjen mukaiset tavoitteet ja luvat. |
| **PID** | Käytä palautuspohjaista suhteellista, integraalista ja johdannaista valvonta, jos laite ja mittaus tukevat sitä. |
| **Käsikirja** | Valvonta nimenomaisesti tuketuilla pyynnöillä ja tavoitteilla. |
| **Päästä irti.** | Pidä ohjauslaite pois päältä, jos vaaditaan fyysistä suojaa ja palautetta. |

Esimerkiksi yksi ilmastointi voi käyttää **PID lämmitykseen** ja **Automaattinen jäähdytys**-Häpäsyttimet voivat olla omia PID Valmistajat voivat käyttää: PID kun on saatavilla asianmukaista palautetta ja käyttötarkoitusta koskevaa valvontaa.

PID on **ei ole** yleismaailmallinen ylittäminen: HEM Edistyneitä vaihtoehtoja ovat muun muassa per-mode-tuning ja kalibrointi, ehdotetut/adaptiiviset säätelyet, hiljainen toiminta ja tuettuja vaiheittaisia ventilaattoriasetuksia. Hyväksyt ehdotetut muutokset, ellet nimenomaan valitse rajoitettua automaattista mukauttamista.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Mukava kotona, taloudellinen poissa ollessasi.

HEM voi valita **Mukavuus, koti, matka, uni ja ympäristö** Tavoitteet perustuvat kotitalouksien tilanteeseen, huoneen todisteisiin ja nimenomaisiin valintasi.

- **Kotona ja pois:** Käytä erilaisia lämmitys-, jäähdytys- ja kosteusmääräyksiä, jotka riippuvat todistetusta kotitalouksien läsnäolosta.
- **Huoneen läsnäolo:** Käytä hyväksyttävää laitetta aina, kun on kysyntää, vain, kun huone on täynnä tai vain, kun huone on tyhjä.
- **Nuku:** Valittu laite voi pysyä sammutettuna, kun kaikki huoneet nukkuvat.
- **Ympäristö:** Suljettu sisäoven voi osallistua suojattuun ympäristöpolitiikkaan, kun huoneessa todetaan olevan tyhjä ja täyttyvät muut edellytykset; suljettu ovi yksin ei todista, että huone on eristetty.
- **Herätysvalmiste:** Käytä konfiguroitua seuraavaa hälytyslähdettä, jotta automaattinen nukkuminen jättää hälytyksen edeltävän ajan ja antaa oikeutettujen laitteiden aikaa vastata.

Jos käyttö, laitteen saatavuus tai muut vaaditut todisteet ovat epävarmoja, HEM ei yksinkertaisesti oleteta, että automaattisen laitteen käynnistäminen on turvallista.

<a id="prepare-your-environment-before-you-arrive"></a>
### Valmista ympäristösi ennen saapumista

**Valmistautukaa saapumiselle.** Se alkaa kortin otsikosta. HEMSe on kotilaite.

HEM soveltaa väliaikaisesti määritettyä **Kotimaiset tavoitteet** tukikelpoiseen automaattiin/PID valvontalaitteet, jotta huoneet voivat aloittaa lämmityksen, jäähdytyksen tai kosteuden säätelyä ennen palaamista. Tämä voi myös antaa tilapäisesti mahdollisuuden valvontalaitteen, joka on yleensä rajoitettu käytettyihin huoneisiin, **vain, jos sillä on jo tarvittava fyysinen valvontalupa**.

Valmistelu ei ole käsky käynnistää kaikkea. Laitteet tarvitsevat edelleen todellista kysyntää, päteviä antureita ja valtuutuksia, ja niiden on kunnioitettava ikkunoita, vähimmäislähtöisiä ON/OFF-aikoja ja omaa suojaa. Home Assistant Jos käynnistys ei käynnisty täysillä timerillä.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Tuuletusohjeet, ikkunat, ovet ja varjoitus

HEM vertailut **mitä huone tarvitsee** ja **Voiko ulkona oleva ilma auttaa?**.

- Suosittelemme, että ikkunat avautuvat tai suljetaan käyttämällä nykyisiä sisätilojen mittauksia, ulkona olevaa kosteutta, saastumista, lämpötilaa, tuulta, sääilmoituksia ja valinnaista siipikarjan kontekstia.
- Käytä valittuja ikkunan ja oven yhteyksiä, jotta voit selittää huoneen olosuhteet ja välttää tuntemattoman yhteyden käsittelyn suljetuksi.
- Valitettavasti pyydetään avaamaan ikkunan, ennen kuin käynnistetään tukematon automaattinen laitteen, ja jatketaan normaalia ohjausta, kun konfiguroitu vastaus odottaa tarvittaessa.
- Käytä oven tietoja huoneen rajojen tiedostamiseksi, ilmanvaihdon varoituksille ja valinnaisesti vartioituun ympäristökäyttäytymiseen.
- Käsittele valinnut lukit, persiinit ja varjoja käyttämällä asianmukaisia ikkunoita, lämpötilaa, säätä, auringonnousua ja valinnaista valaistusta.

HEM Se ei avaa ikkunaa yksinään vain siksi, että ilmastointi auttaisi.

<a id="humidity-mold-indication-and-air-quality"></a>
### Korkkuus, muovin merkintä ja ilmanlaatu

HEM yhdistää tukevat lukemat, kuten **lämpötila, kosteus, hiilidioksidipäästö, hiukkaset, VOC, AQI ja valaistus** Käytettävissä olevat mittaukset riippuvat siitä, mitä huoneesi on. Home Assistant Seuraavaksi.

Se on **muurahaisen merkintä** Kun se on asianmukaisesti konfiguroitu, se voi vaikuttaa autettuun automaattiseen kosteudenvalvontalaitteen tehokkaan kohteeseen.

**Muurahaisen merkintä on arvio, ei muurahaisen tai sporin detektori.** Puuttuvat tai vanhentuneet antureiden tiedot eivät voi oikeuttaa uutta muottipohjaista laitteen käskyä.

<a id="announcements-diagnostics-and-protection"></a>
### Ilmoitukset, diagnoosi ja suoja

Voit lähettää asiaankuuluvia suosituksia ja varoituksia Home Assistant ilmoitukset, TTS/media-pelaajat tai **Ilmoituskeskus**AI voi muuttaa viestin ilmaisemista. HEMFyysisen valvonnan päätökset ovat edelleen deterministisia.

HEM sisältää myös laitteen erityisiä suojauksia ja diagnoosia:

- Vähimmäislähtö- ja pääsykausi, enimmäislähtöaikaasetukset ja tukitut ulkoiset toimitusvaihteiden käsittely.
- Ikkunan ja käytön rajoitukset, manuaalinen ohjaus ja alkuperäisen käskyn vahvistus.
- Virheiden ja käytettävissä olevien laitteiden raportointi, jossa on valinta ilmoituksen käyttäytymisestä kunkin laitteen osalta.
- Valinnainen valvontatoiminta sulkemisen jälkeen epäiltyjen jatkuvien lämmitysten vuoksi, jossa on vartioitu seuranta ja rajoitetut palautusyrityt.
- Selkeät odottamisperusteet, nykyinen käyttötilanne ja lähteen saatavuus, jotta voit tutkia ennen kuin voit antaa lisää valvontaa.

**Turvallisuusrajat pysyvät voimassa myös silloin, kun varoitus on pois käytöstä.** HEM ei koskaan käsittele onnistuneesta komennon lähetyksestä todisteena siitä, että laite on fyysisesti vastannut.

<a id="see-hem-in-action"></a>
## Katso . HEM toiminnassa

Nämä englanninkieliset kuvat käyttävät näytteitä ja mittauksia, jotka osoittavat käyttöliittymän sen sijaan, että ne näyttäisivät tietyn talon eläviä tietoja.

<a id="home-at-a-glance"></a>
### Kotona silmäyksellä

Ota ilmanvaihtoohjeet, sääolosuhteet ja jokaisen seurannatun huoneen tila yhdellä korttilla.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM kotimainen ohjauslauta, jossa on tuuletusohjeita ja ympäristöluokituksia viidessä huoneessa" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Laajennetaan tilaa yksityiskohtia varten.

Tarkista ilmanlaatu, muurahaisindikaatio, läsnäolo, ikkunan tila, ilmasto- ja ilmastovalvontat sekä jokaisen päätöksen selitys.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Laajennettu kylpyhuoneen ohjauslauta, jossa on lukemat ja riippumattomat laitteiden ohjaimet" width="760">
</p>

<a id="home-settings"></a>
### Kotiasetukset

Hallitse ulkoiset lähteet, koko talon läsnäolo, valvontahuoneet, ilmanvaihdon rajoitukset, valmistelu ja ilmoitukset.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Kotiasetukset, joissa on etsimistäviä ryhmiä ja lähde- ja huoneenhallinta" width="900">
</p>

<a id="room-settings"></a>
### Huoneen asetukset

Valitse, mitä jokaiselle huoneelle on merkitystä: sen omat anturit, kohteet, asukkaat, ovet, ikkunat, tuuletus, varjoitus ja suoja.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Ryhmitetty HEM huoneen asetukset antureille, laitteen ohjauksille, nukkumaan, ikkunoille ja suojaan" width="760">
</p>

<a id="device-settings"></a>
### Laitteen asetukset

yhden laitteen hienostuneisuus ilman muiden vaihtamista, mukaan lukien tukemat ohjausmenetelmät, PID, hiljainen toiminta, ajoitus ja virheiden ilmoittaminen.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Ryhmitetty HEM laitteen asetukset ohjauslaitteella, PID, sähkösuojelu ja ilmoitukset" width="900">
</p>

<a id="getting-started"></a>
## Aloitetaan.

1. **Järjestäkää huoneenne.** Sisällä Home Assistant, luoda tai tarkistaa alueesi ja määrätä jokaiselle asianmukaiset anturit ja laitteet.
2. **Valitse, mitä tarkkailla.** Lisää HEMValitse huoneet, joista välität, ja tarkista ehdotetut lämpötilat, kosteus, ikkunat, ilmanlaatu ja laitteen lähteet.
3. **Säännön yhteistä tietoa.** Valitse käytettävissä olevat ulkona olevat sää-/ilmalaatuiset lähteet, kotitalouden väliaikaiset tiedot ja haluamasi ilmoituksen kohteet.
4. **Lisää kortti.** Avaa painiketta muokkaustilaan ja lisää **Kotiympäristöjohtaja** Aloita huoneen seurannalla, lukemalla ja tuuletuksella.
5. **Käytännössä vain silloin, kun se on hyödyllistä.** Avaa huone, valitse tukematon laitteen, tarkista sen ohjaaja ja valitse nimenomaisesti automaattinen tai PID haluamasi muodoista HEM Toiminta.

- Kyllä sinä tiedät. **ei ole** Aloita käyttämäsi antureilla ja ota käyttöön automaattinen ohjaus yksi laitteen kerrallaan.

<a id="add-the-card-manually"></a>
### Lisää kortti käsin

YAML-kortti on yleensä omalla nimellä.

~~~yaml
type: custom:home-environment-manager-card
~~~

Jos Home Assistant asennus on useampi kuin yksi HEM suosituksen anturi, saatat joutua asettamaan asianmukaisen **yksikkö** selkeästi:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Huoneen lähteistä, profiileista, PID Käytetään myös sähköisiä laitteita, jotka ovat tarkoitettuja sähköisten laitteiden käyttöönottoon. [yksityiskohtainen konfiguraatiohje](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Asennus

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Yhteisön kauppa

1. Avaa . **HACS** Vihreillä Home Assistant.
2. Lisää **Euroopan parlamentin ja neuvoston asetus (EU) N:o 1303/2013, annettu 10 päivänä marraskuuta 2014, Euroopan parlamentin ja neuvoston asetuksen (EU) N:o 1303/2013, Euroopan parlamentin ja neuvoston asetuksen (EU) N:o 1303/2013, (EU) N:o 1303/2013 ja Euroopan parlamentin ja neuvoston asetuksen (EU) N:o 1303/2013, (EU) N:o 1303/2013, (EU) N:o 1303/2013, (EU) N:o 1303/2013 ja (EU) N:o 1303/2013, (EU) N:o 1303/2013, (EU) N:o 1303/2013 ja (EU) N:o 1303/2013, (EU) N:o 1303/2013, (EU) N:o 1303/2013 ja (EU) N:o 1303/2013, (EU) N:o 1303/2013** Vihreä **Säännöllinen säilytys** Se on **Yhteenliittymä** luokka, jos se ei ole jo lueteltu.
3. Etsi **Kotiympäristöjohtaja** ja asentaa se.
4. Aloittakaa uudelleen **Home Assistant** Täytyy ladata integrointi.
5. Menkää . **Asetukset → Laitteet & palvelut → Lisää integrointia**, etsiä **Kotiympäristöjohtaja** Ja lopeta järjestely.

<a id="manual-installation"></a>
### Käsikirjoitus

Kopioida varasto **custom_components/environment_manager** Pöydän mukaan **custom_components** luettelo Home Assistant konfiguraatio, jossa säilytetään luettelon nimi **ympäristö_hallinta**Aloita uudelleen . Home Assistant ja lisätä integrointi **Asetukset → Laitteet & palvelut**.

Jälkimmäisiä asennusmuutoksia varten säilytetään olemassa olevia HEM integrointi- ja -asetukset. Jos kortin ulkonäkö ei uudistu välittömästi, ladata selaimesi ohjauslauta.

<a id="common-questions"></a>
## Yleiset kysymykset

**Saanko käyttää HEM -En antanut sille valvontaa laitteistani?**

Valvonta, mittaukset, tuuletusohjeet, historia ja monet ympäristöindikaatiot toimivat ilman laitteen käynnistämistä.

**Will , minä ... HEM Valvoiko se automaattisesti kaikki laitteet?**

Valitse fyysiset laitteet, joita haluat hallita, ja valitse nimenomaisesti hallintomenetelmä tuketuille toimintatapoille.

**Kannattaako jokainen laite PID?**

- En minä. HEM tuet PID Vähintään: **tukikelpoiset** lämmitys-, jäähdytys-, kosteus- tai ventilaattoriohjausmatka, kun laitteen ja valitut mittaukset tarjoavat tarvittavat valmiudet ja palautetta. PID Valvonta.

**Voinko antaa jokaiselle huoneelle erilaisia sääntöjä?**

Kyllä. Asunnon olosuhteet, nukkumisen käyttäytyminen, lähteet, kohteet ja tietyt turvallisuusehdotukset voivat vaihdella huoneen mukaan, kun taas jokaisella fyysisellä laitteella on omat käyttö- ja suojausasetukset.

**Voisin HEM Valmistatko kotini poissa ollessani?**

- Kyllä, minä olen. **Valmistautukaa saapumiselle.** Se ei ohjaa fyysisiä suojauksia eikä takaa, että kohde saavutetaan.

**Avaako  ⁇ hyvä ilmanvaihto ⁇  suositus ikkunani?**

Se selittää, milloin ilmastointi voi auttaa. Automaattinen liikkuvuus on erillinen, opt-in-ominaisuus hyväksyttäville tuettuille varjoille tai kattoille, jotka ovat riippuvaisia omasta turvallisuustarkastuksesta.

**Entä jos anturi tai laite ei ole käytettävissä?**

HEM Automaattinen valvonta edellyttää edelleen voimassa olevaa valtaa ja todisteita.

<a id="help-and-troubleshooting"></a>
## Avun ja ongelmanratkaisu

Jos jokin vaikuttaa väärältä, tarkista asiaa koskeva huone tai valvonta **Syynä**, **Diagnostiset tiedot**, lähteen saatavuus ja nykyinen valvontamenetelmä. [yksityiskohtainen konfiguraatiohje](../../docs/advanced-configuration.md) kattaa yhteisiä odotusolosuhteita, läsnäolon politiikkaa, PID hyväksyttävyys, ikkunat ja laitteen vastauksen häiriöiden ratkaiseminen.

Toistuvan ongelman vuoksi [avaa a GitHub Ehdotus](https://github.com/Chreece/HA-Home-Environment-Manager/issues) Se sisältää odotettavaa käyttäytymistä, todellista käyttäytymistä, asiaankuuluvia huoneen/laitteen asetuksia ja toistettavia askeleita.

Lisätietoja ja parannuksia on tervetulleita. [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Tukea ja lisenssiä

Jos HEM Se on sinulle hyödyllistä. [tuki Kreikalle Ko-fi-ohjelmassa](https://ko-fi.com/chreece).

Julkaistu [MIT:n lisenssi](../../LICENSE).
