<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Managerul de mediu - calitate a aerului mai inteligentă, confort, ventilație și control al climei" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Susținerea Chreece Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <strong>Română</strong> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Directorul de mediu

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Întregul mediu al casei, într-un singur Home Assistant Cardul.</strong></p>

**HEM ajută casa ta să înţeleagă împrejurimile şi să reacţioneze la ceea ce fiecare cameră are de fapt nevoie.** Îţi aduce Home Assistant Se folosesc senzori, date meteorologice, informații privind ocuparea și dispozitive climatice compatibile, astfel încât să puteți monitoriza calitatea aerului, să primiți sfaturi utile privind ventilația, să gestionați confortul și să automatizați echipamentul ales.

De exemplu, HEM poate reduce încălzirea în timp ce toată lumea este plecată, poate pregăti camere selectate înainte de întoarcere, poate folosi un alt obiectiv de umiditate în timp ce dormi sau poate cere să deschizi o fereastră înainte de a rula un dehumidificator. **monitorizarea și recomandarea**, fără a controla niciun dispozitiv.

**Rămâi la conducere.** Fiecare cameră are propriile setări. Fiecare dispozitiv suportat are propriul controler, moduri de funcționare, ținte și limite de siguranță. HEM nu presupune niciodată că alegerea unui dispozitiv îi dă permisiunea de a opera dispozitivul.

[Explorează caracteristicile](#what-can-hem-do) · [Vezi interfaţa](#see-hem-in-action) · [Instalarea HEM](#installation) · [Pune-ţi casa.](#getting-started) · [Ghid detaliat](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Ce poate HEM - Da, nu.

| Situaţia ta | Cum ? HEM poate ajuta |
| --- | --- |
| **Casa e goală .** | Treci la ţintele de la distanţă, respectă regulile de prezenţă ale fiecărei camere şi evita să rulaţi echipamente selectate inutil. |
| **Te duci acasă.** | Presă **Pregătiţi-vă pentru sosire.** să utilizeze temporar obiectivele de confort la domiciliu pentru controlatorii automatici eligibili, chiar dacă toată lumea este încă plecată. |
| **Cineva doarme .** | Folositi obiective de somn, reduceti zgomotul ventilatorilor sau lasati dispozitivele selectate in afara in timp ce fiecare camera ocupata doarme. |
| **O cameră este umedă .** | Comparaţi indicaţia de umiditate şi mucegai cu ţintele, sugeraţi aerare utilă sau utilizaţi un dehumidificator autorizat folosind un dispozitiv automat sau PID controlul. |
| **E cald şi soare.** | Evaluarea temperaturii camerei, a luminii solare, a vremii și a contactelor de fereastră conectate înainte de a muta nuanțele optate. |
| **Aerul exterior arată mai bine.** | Se recomandă ventilarea utilizând cererea de interior, poluarea exterioră, temperatura, umiditatea, vântul și avertismentele privind polenul sau vremea disponibile. |
| **Un încălzitor sau un TRV nu mai răspunde** | Prezentarea stării sale de nedesponibilitate sau de aşteptare, păstrarea controlerului său configurat și raportarea defecțiunilor dispozitivului suportat fără a presupune că bateria sau relulul s-au recuperat. |

Acestea sunt exemple, nu acțiuni care HEM Rezultatele depind de senzorii selectaţi. Home Assistant capacităţile şi setările de opt-in.

<a id="explore-the-features"></a>
## Explorează caracteristicile

<a id="a-complete-home-dashboard"></a>
### O tablă de bord completă

În cazul HEM cardul vă oferă o imagine generală utilă fără a deschide mai multe integrări.

- Vezi condiţiile de exterior, calitatea aerului şi dacă este recomandat ventilarea.
- Compară toate camerele monitorizate dintr-o singură dată: temperatură, umiditate relativă, AQI, PM2.5, indiciere a mucegaiului, lumină și alte valori susținute.
- Extinde orice spațiu pentru măsurători detaliate, informații despre ferestre și uși, starea climatică, controlatorii activi, motivele de așteptare și estimările fizice ale clădirilor.
- Priviți istoricul și tendințele, vedeți care senzori au contribuit la o medie și distingeți lecturile lipsite de valorile măsurate.
- Camerele de grupare în număr real Home Assistant de etaje, sau folosiți o listă simplă de camere atunci când nu aveți etaje.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Diferite setări pentru casă, fiecare cameră și fiecare dispozitiv

HEM ține politicile împărțite separate de deciziile locale.

| Nivelul setărilor | Ce puteţi configura |
| --- | --- |
| **Acasă** | Surse de vreme și poluare în aer liber, camere monitorizate, limite globale de ventilație, prezența gospodăriilor, pregătirea sosirii și livrarea anunțurilor. |
| **Camera** | Surse de temperatură și umiditate din interior, praguri de calitate a aerului, contacte cu ferestrele și ușile, comportament de somn și de ocupare, obiective de confort specifice camerei, ventilație și opțiuni de umbră. |
| **Dispozitiv individual** | Modurile sale de control disponibile, automat/manual/PID metoda, țintele pe profil, senzorii, setările de ventilator liniștit, timpul minim de funcționare, protecțiile de alimentare, comportamentul fereastră și notificările de eroare a dispozitivului. |

Toate cele trei niveluri sunt accesibile prin setări grupate, căutabile din card. Home Assistant modificări de setare.

<a id="climate-control-and-pid-device-by-device"></a>
### Controlul climatic și PID, dispozitiv după dispozitiv

HEM poate lucra cu compatibil Home Assistant **climă**, **umidificator** și **ventilator** dispozitive, inclusiv echipamente de încălzire, răcire, dehumidificare, umidificare și suport pentru circulația aerului sau de curățare a aerului.

Pentru fiecare **modul de funcționare fizic suportat**, alege metoda de control independent:

| Metoda | Ce înseamnă |
| --- | --- |
| **Există** | Lasă funcționarea cu drumul de control existent. |
| **Automat** | Urmează HEMCererea măsurată, obiectivele și permisiunile bazate pe situație. |
| **PID** | Utilizați controlul proporțional, integral și derivat pe bază de feedback, în cazul în care dispozitivul și măsurarea îl susțin. |
| **Manual** | Controlul prin solicitări și obiective explicite susținute. |
| **Închide !** | Ţineţi controlerul off, sub rezerva cerinţelor de protecţie fizică şi feedback. |

De exemplu, un aparat de aer condiționat poate utiliza **PID pentru încălzire** și **Automatic pentru răcire**Un dehumidificator poate avea propriul PID calibrarea, obiectivele și cronometrajul ciclului. PID atunci când sunt disponibile feedback-uri adecvate și controluri specifice scopului.

PID este **Nu** o suprapunere universală: HEM Opțiunile avansate includ tuning-ul și calibrarea per-mod, ajustările sugerate/adaptive, funcționarea liniștită și setările de ventilator în etape susținute.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Comod când eşti acasă, economic când eşti plecat.

HEM poate alege între **Confort, acasă, departe, somn şi ecologie** obiective bazate pe situația casei, evidența camerei și selecțiile tale explicite.

- **Acasă şi departe:** Utilizați obiective diferite de încălzire, răcire și umiditate în funcție de prezența verificată a locuinței.
- **Prezența în cameră:** Foloseste un dispozitiv eligibil întotdeauna atunci când există cerere, numai în timp ce camera este ocupată sau numai în timp ce camera este goală.
- **Dorm:** Un dispozitiv selectat poate rămâne oprit atunci când toate camerele ocupate dorm.
- **ECO:** O ușă internă închisă poate participa la o politică ecologică păzită atunci când camera este verificată goală și alte condiții sunt îndeplinite; o ușă închisă singură nu dovedește că camera este izolată.
- **Pregătirea pentru trezire:** Utilizați o sursă de alarmă următoare configurată pentru a lăsa automat somnul înainte de alarmă și pentru a da timp dispozitivelor eligibile pentru a răspunde.

În cazul în care ocuparea, disponibilitatea dispozitivului sau alte dovezi necesare nu sunt sigure, HEM nu presupune pur și simplu că este sigur să pornească un dispozitiv automat.

<a id="prepare-your-environment-before-you-arrive"></a>
### Pregătiţi-vă mediul înainte de a ajunge

**Pregătiţi-vă pentru sosire.** Este o acţiune cronometrată pentru o casă confirmată. HEME dispozitivul de acasă.

HEM aplică temporar configurația **Obiectivele pentru locuințe** în cazul în care este eligibil Automatic/PID controler-uri pentru ca camerele să poată începe încălzirea, răcire sau ajustarea umidității înainte de întoarcere. **numai dacă are deja permisiunea necesară de control fizic**.

Pregatirea nu este o comandă pentru a porni totul. Dispozitivele au nevoie încă de cerere autentică, senzori valabili și autorizații, și trebuie să respecte ferestrele, timpul minim de ON/OFF și protecțiile lor proprii. Home Assistant Restartul nu porneşte complet cu cronometrul.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Sfaturi privind ventilația, ferestrele, ușile și umbrarea

HEM compară **ce are nevoie o cameră** cu **dacă aerul exterior poate ajuta**.

- Recomandă deschiderea sau închiderea ferestrelor folosind măsurătorile actuale de interior, umiditatea exterioră, poluarea, temperatura, vântul, avertismentele meteorologice și contextul opțional al polenului.
- Utilizaţi contacturile selectate pentru ferestre şi uşi pentru a explica condiţiile camerei şi evitaţi să trataţi un contact necunoscut ca fiind închis.
- În opțiune, vă rugăm să încercați să deschideți o fereastră înainte de a porni un aparat automat suportat, apoi să continuați controlul normal după ce răspunsul configurat așteaptă, dacă este necesar.
- Utilizați informațiile de la ușă pentru conștientizarea granițelor camerei, avertismentele de ventilație și comportamentul ecologic protejat opțional.
- Gestionarea obturărilor opționale, a persienilor și a umbrelor folosind ferestrele adecvate, temperatura, vremea, înălțimea soarelui și dovezile opționale de iluminare.

HEM Nu se deschide o fereastră de la sine doar pentru că aerul ar ajuta.

<a id="humidity-mold-indication-and-air-quality"></a>
### Umiditate, indicație a mucegaiului și calitate a aerului

HEM combinați citiri suportate, cum ar fi **temperatura, umiditatea, CO2, particulele, COV, AQI și iluminarea** Măsurările disponibile depind de ceea ce Home Assistant Se asigură instalarea.

- Nu. **indicație de formă** estimă condițiile de umiditate la o suprafață rece, pe baza temperaturii de cameră și de exterior, precum și a unei măsurători de calibrare.

**Indicarea mucegaiului este o estimare, nu un detector de mucegai sau spore.** Datele de senzori lipsite sau învechite nu pot justifica o nouă comandă de dispozitiv bazată pe mucegai.

<a id="announcements-diagnostics-and-protection"></a>
### Anunțuri, diagnostic și protecție

Puteţi trimite recomandări şi avertismente relevante prin intermediul configurării Home Assistant notificări, jucătoare TTS/media sau **Hub de anunţuri**, cu formularea opțională AI. AI poate schimba modul de exprimare a unui mesaj; HEMDeciziile de control fizic rămân deterministe.

HEM include, de asemenea, protecții și diagnostice specifice dispozitivului:

- Durata minimă de ON și OFF, setările maxime de timp de funcționare și manipularea suportată a comutatorului extern de alimentare.
- Restricții de fereastră și ocupare, manipulare manuală și verificări de confirmare a comandelor locale.
- Raportarea erorilor și a dispozitivelor nedisponibile, cu o alegere a comportamentului de notificare pentru fiecare dispozitiv.
- Un câine de supraveghere opțional după închidere pentru încălzirea continuă suspectată după o comandă de oprire, cu monitorizare păzită și încercări limitate de recuperare.
- Motive clare de așteptare, starea actuală de funcționare și disponibilitatea surselor, astfel încât să puteți investiga înainte de a permite mai mult control.

**Limitele de siguranță rămân în vigoare chiar și atunci când se dezactivă alarma.** HEM nu tratează niciodată o expediere de comandă reușită ca dovadă că un dispozitiv a răspuns fizic.

<a id="see-hem-in-action"></a>
## Vezi ? HEM în acțiune

Aceste ilustrații în limba engleză folosesc camere de probă și măsurători.

<a id="home-at-a-glance"></a>
### Acasă la o privire

Obțineți sfaturi de ventilație, condiții meteorologice și starea fiecărei camere monitorizate într-o singură carte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM tabla de bord de la domiciliu cu sfaturi de ventilație și citiri de mediu în cinci camere" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Expandă o cameră pentru detalii complete

Inspectă calitatea aerului, indicația mucegaiului, prezența, starea ferestrei, controlatorii climatici și explicațiile pentru fiecare decizie.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Tabla de bord extinsă pentru baie cu citiri și controale independente ale dispozitivelor" width="760">
</p>

<a id="home-settings"></a>
### Configurații de acasă

Gestionarea surselor de aer liber, prezența în întreaga casă, camerele monitorizate, limitele de ventilație, pregătirea și notificările.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Configurații de domiciliu cu grupuri de căutare și gestionarea surselor și a camerelor" width="900">
</p>

<a id="room-settings"></a>
### Setări ale camerei

Alegeţi ceea ce contează pentru fiecare cameră: propriile senzori, ţinte, ocupare, uşi, ferestre, ventilaţie, umbră şi protecţii.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Grupate HEM setări de cameră pentru senzori, dispozitive de control, somn, ferestre și protecție" width="760">
</p>

<a id="device-settings"></a>
### Setările dispozitivului

Ajustarea fină a unui dispozitiv fără schimbarea celorlalte, inclusiv a metodelor de control suportate, PID, operaţiune liniştită, cronometrare şi raportare de defecte.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Grupate HEM setările dispozitivului cu control, PID, protecția energiei electrice și notificări" width="900">
</p>

<a id="getting-started"></a>
## Începând

1. **Organizează-ţi camerele.** În Home Assistant, creaţi sau verificaţi zonele şi atribuiţi senzorilor şi dispozitivelor corespunzătoare fiecărei.
2. **Alege ce să monitorizezi.** Adăugați HEM, selectaţi camerele care vă interesează şi verificaţi temperatura, umiditatea, fereastra, calitatea aerului şi sursele de dispozitive sugerate.
3. **Configurați informațiile împărțite.** Selectați sursele disponibile pentru condițiile meteorologice/calitatea aerului în aer liber, dovezi privind ocuparea locuințelor și orice destinații de anunțuri doriți.
4. **Adăugaţi cardul.** Deschideţi un tablou în modul de editare şi adăugaţi **Home Manager de mediu** Începe cu monitorizarea camerei, lecturile şi sfaturile de ventilaţie.
5. **Activaţi controlul numai atunci când este util.** Deschideţi o cameră, alegeţi un dispozitiv suportat, verificaţi controlerul său şi selectaţi în mod explicit PID pentru modalităţile pe care le doriţi HEM pentru a opera.

- Da, ştii. **Nu** Începe cu senzorii pe care îi ai, şi introduce controlul automat, un dispozitiv la un moment dat.

<a id="add-the-card-manually"></a>
### Adăugaţi cardul manual

Integrarea înregistrează în mod normal propria carte Lovelace.

~~~yaml
type: custom:home-environment-manager-card
~~~

Dacă Home Assistant instalația are mai mult de una HEM dacă este necesar setarea sensorului de recomandare **entitate** în mod explicit:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Pentru instrucțiuni pas cu pas cu privire la sursele de cameră, profiluri, PID setările, politicile de fereastră, pregătirea, calibrarea mucegaiului, umbrarea solară și livrarea anunțurilor, folosiți [ghid detaliat de configurare](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Instalarea

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Magazin comunitar

1. Deschis **HACS** în Home Assistant.
2. Adăugați **În cazul în care este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar să se asigure că este necesar.** ca o **depozit personalizat** în **Integrare** categoria dacă nu este deja listată.
3. Găsiţi **Home Manager de mediu** şi să-l instalezi.
4. Reluare **Home Assistant** pentru a încărca integrarea.
5. Du-te la **Setări → Dispozitive & servicii → Adăugați integrare**, căutarea pentru **Home Manager de mediu** Şi să terminăm setarea.

<a id="manual-installation"></a>
### Instalarea manuală

Copiează depozitul. **custom_components/environment_manager** carpeta în corespunzătoare **custom_components** directory în Home Assistant configurare, păstrând numele directoriului **environment_manager**Reluare . Home Assistant şi adăuga integrarea prin **Configurații → Dispozitive și servicii**.

Pentru modificările ulterioare ale instalaţiei, păstraţi HEM introducerea și setările de integrare. Reloadă tabla de bord în browserul dvs. dacă aspectul cardului nu se reînnoiește imediat.

<a id="common-questions"></a>
## Întrebări obișnuite

**Pot să folosesc HEM fără să-i dau controlul dispozitivelor mele?**

Monitorizarea, măsurarea, consultarea ventilaţiei, istoricul şi multe indicaţii de mediu funcţionează fără a permite activarea dispozitivului.

**Will , HEM controla automat fiecare dispozitiv descoperit?**

Nu. Selectați dispozitivele fizice pe care doriți să le gestionați și alegeți în mod explicit metoda de control pentru modurile suportate. Eligibilitatea senzorului și capacitățile dispozitivului nativ determină totuși ceea ce este posibil.

**Fiecare dispozitiv suportă PID?**

Nu, nu, nu. HEM sprijinuri PID pentru **eligibile** căile de încălzire, răcire, umiditate sau de control al ventilatorului atunci când aparatul și măsurătorile selectate oferă capacitățile și feedback-ul necesar. PID controlul.

**Pot să dau reguli diferite fiecărei camere?**

Da, condiţiile de ocupare, comportamentul somnului, sursele, obiectivele şi unele preferinţe de siguranţă pot fi diferite în funcţie de cameră, în timp ce fiecare dispozitiv fizic are propriile setări de funcţionare şi protecţie.

**Poate . HEM Să-mi pregătesc casa în timp ce sunt plecată?**

- Da, am fost. **Pregătiţi-vă pentru sosire.** De asemenea, sistemul de control automat permite temporar controlatorilor automatici eligibili, deja autorizați, să utilizeze țintele de domiciliu pentru o perioadă limitată.

**O recomandare bună pentru ventilaţie îmi deschide ferestrele?**

Mișcarea automată este o caracteristică separată, opt-in pentru nuanțele sau acoperisurile eligibile, supuse propriilor controale de siguranță.

**Ce se întâmplă dacă un senzor sau un dispozitiv devine indisponibil?**

HEM controlul automat necesită încă o autoritate validă și dovezi actuale.

<a id="help-and-troubleshooting"></a>
## Ajutor și soluționare a problemelor

Dacă se pare că ceva nu e în regulă, verificaţi camera relevantă sau controlatorul **Motivul**, **Diagnostică**, disponibilitatea sursei şi metoda de control curent. [ghid detaliat de configurare](../../docs/advanced-configuration.md) acoperă statele de așteptare comune, politicile de prezență, PID Eligibilitate, ferestre și soluționarea problemelor cu răspunsul dispozitivului.

Pentru o problemă reproducibilă, [deschide un GitHub Emission](https://github.com/Chreece/HA-Home-Environment-Manager/issues) cu comportamentul așteptat, comportamentul real, setările de cameră/dispozitiv relevante și pașii de reproducere.

Contribuţiile şi îmbunătăţirile sunt binevenite. [Contributarea.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Suport și licență

Dacă HEM este util pentru tine, poti [sprijinul Chreece pe Ko-fi](https://ko-fi.com/chreece).

Distribuit în cadrul [Licenţa MIT](../../LICENSE).
