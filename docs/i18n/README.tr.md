<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Ev Çevre Yöneticisi - Akıllı hava kalitesi, konfor, havalandırma ve iklim kontrolü" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Chreece'ı desteklemek Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <strong>Türkçe</strong> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Ev Çevre Müdürü

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Tüm evin çevresini, tek bir Home Assistant Kart.</strong></p>

**HEM evinizin çevresini anlamasına ve her odanın aslında neye ihtiyacı olduğunu anlamasına yardımcı olur.** Senin için Home Assistant Havanın kalitesini izlemek, faydalı havalandırma tavsiyelerini almak, konforu yönetmek ve seçtiğiniz ekipmanları otomatikleştirmek için sensörler, hava durumu verileri, işlev bilgisi ve uyumlu iklim cihazları bir araya getirilmiştir.

Örneğin, HEM Herkes yokken ısıyı azaltabilir, geri dönmeden önce seçilmiş odaları hazırlayabilir, uyurken farklı bir nem hedefi kullanabilir veya bir dehumidifier çalıştırmadan önce pencerenizi açmanızı isteyebilir. **izleme ve tavsiye**, herhangi bir cihazı kontrol etmeden.

**Sen sorumlu kal.** Her odanın kendi ayarları vardır. Her desteklenen cihazın kendi kontrolörü, çalışma modları, hedefleri ve güvenlik sınırları vardır. HEM bir cihaz seçmenin, bu cihazı kullanma izni verdiğini asla varsaymaz.

[Özellikleri keşfedin](#what-can-hem-do) · [Bağlantıyı görün](#see-hem-in-action) · [HEM kur](#installation) · [Evinizi hazırlayın .](#getting-started) · [Detaylı rehber](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Ne yapabilir? HEM - Evet.

| Durumunuz | Nasıl ? HEM yardımcı olabilir. |
| --- | --- |
| **Ev boş.** | Uzak hedeflere geçin, her odanın varlık kurallarına saygı gösterin ve seçilmiş ekipmanları gereksiz yere çalıştırmaktan kaçının. |
| **Eve gidiyorsun.** | Basın **Gelmeye hazırlanın.** Herkes hala uzakta olsa da uygun otomatik denetleyiciler için geçici olarak ev konfor hedeflerini kullanmak. |
| **Biri uyuyor.** | Uyku hedeflerini kullanın, havalandırıcı gürültüsünü azaltın ya da seçtiğiniz cihazları her yerleşik odada uyurken kapatın. |
| **Bir oda nemlidir.** | Nem ve kalınlık göstergesini hedeflerle karşılaştırın, faydalı havalandırma önerin veya Otomatik veya PID Kontrol. |
| **Sıcak ve güneşli.** | Seçili renklerini değiştirmeden önce oda sıcaklığı, güneş ışığı, hava durumu ve bağlantılı pencerelerle bağlantı değerlendirin. |
| **Dış hava daha iyi görünüyor.** | Ev içi talebi, dış mekan kirliliği, sıcaklık, nem, rüzgar ve mevcut polen veya hava uyarılarını kullanarak havalandırma önerilmelidir. |
| **Bir ısıtıcı veya TRV tepki göstermeyi durdurur.** | Batarya veya relayın iyileşmiş olduğunu varsaymadan, mevcut olmayan veya bekleyen durumunu göster, yapılandırılmış denetleyicisini tut ve desteklenen cihazın hatalarını bildir. |

Bunlar örnekler, eylemler değil HEM Sonuçlar seçtiğiniz sensörlere, her cihazın gerçek Home Assistant yetenekleri ve seçme ayarlarınız.

<a id="explore-the-features"></a>
## Özellikleri keşfedin

<a id="a-complete-home-dashboard"></a>
### Tam bir ev tablosu

Bu HEM kartı, birkaç entegrasyon açmadan size yararlı bir genel bakış sağlar.

- Dışarıdaki koşulları, hava kalitesini ve havalandırmanın uygun olup olmadığını görün.
- Tüm izlenen odaları bir bakışta karşılaştırın: sıcaklık, nispet nemlilik, AQI, PM2.5, kalıp göstergesi, ışık ve diğer desteklenen değerler.
- Detaylı ölçümler, pencere ve kapı bilgileri, iklim durumu, aktif denetleyiciler, bekleme nedenleri ve bina fiziği tahminleri için herhangi bir odayı genişletin.
- Tarih ve eğilimleri görün, hangi sensörlerin ortalama değerlere katkıda bulunduğunu görün ve kayıp okumaları ölçülen değerlerden ayırt edin.
- Grup odaları gerçek Home Assistant Yeri yokken basit bir oda listesini kullanın.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Ev, her oda ve her cihaz için farklı ayarlar

HEM paylaşılan politikaları yerel kararlardan ayrı tutar.

| Ayarlar seviyesi | Yapılandırılabilecekleri |
| --- | --- |
| **Ev** | Dış hava durumu ve kir kaynakları, izlenen odalar, küresel havalandırma sınırları, evlerin varlığı, geliş hazırlığı ve duyuru teslimatı. |
| **Oda** | Ev içi sıcaklık ve nem kaynakları, hava kalitesi eşiği, pencere ve kapı kontaktları, uyku ve işlev davranışları, oda özel konfor hedefleri, havalandırma ve gölgelik seçenekleri. |
| **Bireysel cihaz** | Kullanılabilir kontrol modları, Otomatik/Elçi/PID yöntem, profil başına hedefler, sensörler, sessiz fan ayarları, minimum çalışma süreleri, güç koruması, pencere davranışları ve cihaz hata bildirimleri. |

Tüm üç seviyede de karttaki gruplanmış, arama yapılabilir ayarlar aracılığıyla erişilebilir. Gerektiğinde, günlük ayarları sıkıştırmadan gelişmiş kontroller mevcuttur. Home Assistant Yapılandırma değişiklikleri.

<a id="climate-control-and-pid-device-by-device"></a>
### İklim kontrolü ve PID, cihazla cihaz

HEM uyumlu ile çalışabilir Home Assistant **iklim**, **ısıtıcı** ve **Fan** Sıcaklık, soğutma, nemsizleştirme, nemlendirme ve desteklenen hava dolaşımı veya hava temizleme ekipmanları dahil olmak üzere cihazlar.

Her biri için **Desteklenen fiziksel çalışma modu**, kontrol yöntemini bağımsız olarak seçin:

| Metod | Ne anlama geliyor? |
| --- | --- |
| **Mevcut** | Mevcut kontrol yolu ile çalışmayı bırakın. |
| **Otomatik** | Takip edin . HEMÖlçülen talep, durum tabanlı hedefler ve izinler. |
| **PID** | Cihaz ve ölçüm desteklediği yerlerde geri bildirim tabanlı oranlı, bütünlü ve türevli kontrol kullanın. |
| **Kılavuz** | Açıkça desteklenen istekler ve hedefler yoluyla kontrol. |
| **Çıkar .** | Bu kontrol cihazını kapat, fiziksel koruma ve geri bildirim gereksinimlerine tabi tut. |

Örneğin, bir klima kullanılabilir. **PID Sıcaklık için** ve **Soğutma için otomatik**Bir dehumidifier kendi olabilir . PID Kalibrasyon, hedefler ve döngü zamanlaması. PID uygun geri bildirim ve amaç-özel kontrol mevcut olduğunda.

PID Bu **Hayır.** Evrensel bir önleme: HEM Tek seçenek, belirli bir cihazın destekleyebileceği yöntemleri, işletim modu ve geri bildirim kaynağı sunar. Gelişmiş seçenekler arasında per-mod ayarlama ve kalibrasyon, önerilen / adaptatif ayarlamalar, sessiz çalışma ve desteklenen aşamalı fan ayarları bulunur.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Evdeyken rahat, uzaktayken ekonomik

HEM arasında seçim yapabilir. **Rahatlık, Ev, Uyku ve Ekoloji** Ev ortamına, oda kanıtlarına ve açık seçeneğinize dayanan hedefler.

- **Evde ve Dışarıda:** Evde doğrulanmış varlıklara bağlı olarak farklı ısıtma, soğutma ve nem hedeflerini kullanın.
- **Oda varlığı:** İhtiyacın olduğu her zaman uygun bir cihazı kullanın, sadece odası işgal edildiği ya da odası boş olduğu sürece.
- **Uyku:** Gecelik hedefler uygulayın ve seyirci davranışlarını daha sessiz hale getirin.
- **Ekoloji:** Yapılandırıldığında ekonomik hedefler kullanın. Kapalı bir iç kapı, odanın boş olduğu ve diğer koşullar yerine getirildiği doğrulanırsa korunan bir Ekoloji politikasına katılabilir; kapalı kapı tek başına odanın izole edildiğini kanıtlamaz.
- **Uyandırma hazırlığı:** Alarmdan önce otomatik uykuyu bırakmak ve uygun cihazların cevap vermesi için ayarlanmış bir sonraki alarm kaynağı kullanın.

İşlem, cihazın kullanılabilirliği veya diğer gerekli kanıtlar belirsizse, HEM otomatik bir cihazı başlatmanın güvenli olduğunu düşünmez.

<a id="prepare-your-environment-before-you-arrive"></a>
### Gelmeden önce çevreyi hazırlayın

**Gelmeye hazırlanın.** Bu, onaylanmış bir evden uzaklaşmak için zamanlı bir eylemdir. HEMEv cihazı.

HEM geçici olarak yapılandırılmış **Ev hedefleri** Eğitilebilir OtomatikPID kontrol cihazları, böylece odalar geri dönmeden önce ısıtmaya, soğutmaya veya nem ayarlamaya başlayabilir. **Sadece gerekli fiziksel kontrol izni varsa**.

Hazırlık, her şeyi çalıştırmak için bir komut değildir. Cihazların hala gerçek bir talebe, geçerli sensörlere ve yetkiye ihtiyaçları vardır ve pencerelere, en az ON/OFF zamanlarına ve kendi korumalarına saygı duymalıdır. Eylem birileri geldiğinde sona erer, onu iptal edersiniz veya yapılandırılmış zamanlayıcı sona erer. Home Assistant Yeniden başlatma tam zamanlayıcıyı yeniden başlatmaz.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Havalandırma tavsiyesi, pencereler, kapılar ve gölgelik

HEM karşılaştırır **bir odanın neye ihtiyacı var** ile **Dış hava yardım edebilir mi?**.

- Ev içindeki mevcut ölçümleri, dış mekan nemini, kirliliği, sıcaklığı, rüzgarı, hava uyarıları ve seçmeli polen bağlamını kullanarak pencerelerin açılmasını veya kapatılmasını önerin.
- Oda koşullarını açıklamak için seçilmiş pencere ve kapı bağlantılarını kullanın ve bilinmeyen bir temasın kapalı olarak görmemek için kullanın.
- Seçenek olarak, desteklenen otomatik cihazı başlatmadan önce bir pencereyi açmaya çalışmanıza izin verin. Gerekirse yapılandırılmış yanıt bekledikten sonra normal kontrolü sürdürün.
- Oda sınırları farkındalığı, havalandırma uyarıları ve seçmeli olarak korunmuş Eco davranış için kapı bilgileri kullanın.
- Seçilen pencereleri, perdeleri ve gölgeleri uygun pencere, sıcaklık, hava durumu, güneş yüksekliği ve seçmeli aydınlatma kanıtlarını kullanarak yönetin.

HEM Havacılık konusunda herhangi bir kontrol edilebilir pencere olmadan tavsiyede bulunabilir.

<a id="humidity-mold-indication-and-air-quality"></a>
### Nem, kalıp göstergesi ve hava kalitesi

HEM desteklenen okumaları birleştirir, örneğin: **sıcaklık, nem, CO2, parçacıklar, VOC, AQI ve aydınlatma** Her odayı anlamanıza yardımcı olmak için. Home Assistant kurulum sağlıyor.

Bu ... **kalıp belirtisi** Bu sistem, soğuk bir yüzeyde nem koşullarını oda ve dış sıcaklıklardan ve kalibrasyon ölçümlerinden hesaplar.

**Çamur gösterisi bir tahmin, bir çamur ya da spor algılayıcısı değil.** Kayıp ya da eski sensör verileri, yeni bir kalıp tabanlı cihaz komutunu haklı çıkaramaz.

<a id="announcements-diagnostics-and-protection"></a>
### İlanlar, teşhis ve koruma

Uygun tavsiyeler ve uyarıları yapılandırılmış Home Assistant bildirimler, TTS/medya oynatıcıları veya **İlan Merkezi**Yapay zeka bir mesajın nasıl ifade edildiğini değiştirebilir; HEMFiziksel kontrol kararları belirleyici kalır.

HEM Ayrıca cihazlara özgü koruma ve teşhisler de içerir:

- En az ON ve OFF süreleri, maksimum çalışma süresi ayarları ve desteklenen dış güç anahtarı yönetimi.
- Pencere ve işleme kısıtlamaları, manuel geçiş işlemleri ve yerel komut onay kontrolleri.
- Her cihaz için bildirim davranışı seçeneği ile hata ve kullanılamaz cihaz raporlama.
- Bir OFF komutundan sonra şüpheli bir ısıtmanın devam etmesi için kapatma sonrası bir gözleme köpeği, korunan izleme ve sınırlı kurtarma girişimleri ile.
- Bekleme nedenleri, mevcut işletim durumu ve kaynak kullanılabilirliği, böylece daha fazla kontrol sağlamadan önce araştırma yapabilirsiniz.

**Güvenlik sınırları uyarı devre dışı bırakıldığında bile geçerli kalır.** HEM Başarılı bir komut gönderisini bir cihazın fiziksel olarak yanıtladığına dair kanıt olarak asla değerlendirmemiştir.

<a id="see-hem-in-action"></a>
## Gördün mü ? HEM eylemde

Bu İngilizce resimlerde örnek odalar ve ölçümler kullanılarak, belirli bir evin canlı verilerini göstermek yerine arayüzü gösterirler.

<a id="home-at-a-glance"></a>
### Bir bakışta ev

Havalandırma tavsiyesi, hava koşulları ve her izlenen odanın durumunu tek bir kartla alın.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM 5 odada havalandırma tavsiyesi ve çevresel değerlendirmeler ile birlikte ev ekran tablosu" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Tam ayrıntılar için bir oda genişlet

Her karar için hava kalitesini, kalıp göstergesini, varlığını, pencere durumunu, iklim kontrollerini ve açıklamalarını kontrol edin.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Okuyucular ve bağımsız cihaz denetleyicileri olan genişletilmiş banyo tablosu" width="760">
</p>

<a id="home-settings"></a>
### Ev ayarları

Dış kaynakları, ev genelinde varlık, izlenen odalar, havalandırma sınırları, hazırlık ve bildirimleri yönetmek.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Aranabilir gruplar ve kaynak ve oda yönetimi ile ev ayarları" width="900">
</p>

<a id="room-settings"></a>
### Oda ayarları

Her oda için önemli olanları seçin: kendi sensörleri, hedefleri, yerleşimi, kapılar, pencereler, havalandırma, gölgelik ve güvenlik önlemleri.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Gruplandırılmış HEM Sensörler, cihaz kontrolü, uyku, pencere ve koruma için oda ayarları" width="760">
</p>

<a id="device-settings"></a>
### Cihaz Ayarları

Desteklenen kontrol yöntemleri de dahil olmak üzere diğerlerini değiştirmeden bir cihazı ince ayarlamak, PID... sessiz çalışmalar, zamanlama ve hata raporları.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Gruplandırılmış HEM Kontrollü cihaz ayarları, PID, güç koruma ve bildirimler" width="900">
</p>

<a id="getting-started"></a>
## Başlamak

1. **Odalarınızı düzenleyin.** İçeride Home AssistantBölgeleri oluşturmak veya kontrol etmek ve her birine uygun sensörler ve cihazlar atamak.
2. **Neyi izleyeceğinizi seçin.** Ekle HEM, değer verdiğiniz odaları seçin ve önerilen sıcaklık, nem, pencere, hava kalitesi ve cihaz kaynaklarını gözden geçirin.
3. **Paylaşılan bilgileri yapılandır.** Açık hava/hava kalitesi kaynaklarını, evin işgalinin kanıtlarını ve istediğiniz ilan destinasyonlarını seçin.
4. **Kartı ekle.** Düzenleme modunda bir tabloyu açın ve **Ev Çevre Yöneticisi** Oda izleme, okuma ve havalandırma tavsiyesi ile başlayın.
5. **Sadece yararlı olduğunda kontrolü etkinleştir.** Bir odayı açın, desteklenen bir cihaz seçin, kontrolörünü gözden geçirin ve açıkça Otomatik veya PID İstediğiniz modlar için HEM İşlem için.

Sen de öyle. **Hayır.** Her odada akıllı bir cihaz lazım. Sahip olduğunuz sensörlerle başlayın ve otomatik kontrolü bir seferde bir cihazla başlatın.

<a id="add-the-card-manually"></a>
### Kartı elle ekle

Birleştirme normalde kendi Lovelace kartını kaydeder.

~~~yaml
type: custom:home-environment-manager-card
~~~

Eğer Home Assistant kurulum birden fazla HEM tavsiye sensörü, uygun ayarlama yapmanız gerekebilir **kurum** Açıkça:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Oda kaynakları, profilleri hakkında adım adım talimatlar, PID Ayarlar, pencere politikaları, hazırlık, kalıp kalibrasyonu, güneş ışınlama ve duyuru teslimatı, [detaylı yapılandırma kılavuzu](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Kurulum

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Topluluk Mağazası

1. Açık **HACS** İçinde Home Assistant.
2. Ekle **https://github.com/Chreece/HA-Home-Environment-Manager** bir olarak **özel deposu** Bu arada **Entegrelik** Kategori, henüz listelenmemişse.
3. Bul **Ev Çevre Yöneticisi** ve yükle.
4. Yeniden başlat **Home Assistant** Birleştirmeyi yüklemek için.
5. Git . **Ayarlar → Cihazlar & Hizmetler → Entegreliği Ekle**, arama **Ev Çevre Yöneticisi** Ve ayarlamaları tamamla.

<a id="manual-installation"></a>
### Elsel kurulum

Depo'nun kopyası **custom_components/environment_manager** eşleşme klasörüne **custom_components** Dizininizde Home Assistant Dizin adını koruyan yapılandırma **environment_manager**Yeniden başlat . Home Assistant ve entegrasyonu **Ayarlar → Cihazlar & Hizmetler**.

Sonraki kurulum değişiklikleri için mevcut HEM Kartın görünümü hemen yenilmezse tarayıcınızdaki araç tablosunu yeniden yükleyin.

<a id="common-questions"></a>
## Genel sorular

**Kullanırım mı? HEM Cihazlarımı kontrol etmeden mi?**

Evet, izleme, ölçüm, havalandırma tavsiyesi, tarih ve birçok çevre göstergesi cihazın çalıştırılmasını sağlamadan çalışır.

**Will. HEM Bulduğu her cihazı otomatik olarak kontrol ediyor mu?**

Hayır. Yönetmek istediğiniz fiziksel cihazları seçersiniz ve açıkça desteklenen modlar için kontrol yöntemini seçersiniz. Sensör uygunluğu ve yerel cihaz yetenekleri hala neyin mümkün olduğunu belirler.

**Her cihaz destekliyor mu? PID?**

- Hayır, hayır. HEM Destekler PID için **Eğitimi** Aygıt ve seçilen ölçümler gerekli kapasite ve geri bildirim sağladığında ısıtma, soğutma, nem veya fan kontrol yolları. Desteklenmeyen modlar yapay olarak verilmez. PID Kontrol.

**Her odaya farklı kurallar verebilir miyim?**

Evet, yerleşim koşulları, uyku davranışları, kaynaklar, hedefler ve bazı güvenlik tercihleri odaya göre değişebilir, her fiziksel cihazın kendi çalışma ve koruma ayarları vardır.

**- Evet . HEM Ben yokken evimi hazırlamam mı?**

- Evet. - Evet. **Gelmeye hazırlanın.** Bu, uygun, zaten yetkili otomatik denetleyicilerin sınırlı bir süre için Ev hedeflerini kullanmasına izin verir.

**Havalandırma için iyi bir tavsiye pencerelerimi açıyor mu?**

Otomatik hareket, uygun desteklenen gölgeler veya kapaklar için kendi güvenlik kontrollerine tabi olmak üzere ayrı bir opt-in özelliğidir.

**Ya bir sensör veya cihaz kullanılamazsa?**

HEM Bilinmeyen verileri gerçek okumalardan ayırır, mümkünse yapılandırılmış denetleyiciler bilgileri saklar ve bekleme nedenlerini ve teşhislerini ortaya çıkarır. Otomatik kontrol hala geçerli geçerli yetki ve kanıt gerektirir.

<a id="help-and-troubleshooting"></a>
## Yardım ve sorun çözme

Eğer bir şey yanlış görünüyorsa, ilgili odaya veya kontrolörün **Sebep**, **Diagnostikler**, kaynak kullanılabilirliği ve mevcut kontrol yöntemi. [detaylı yapılandırma kılavuzu](../../docs/advanced-configuration.md) Genel bekleme durumları, varlık politikaları, PID uygunluk, pencereler ve cihaz yanıt sorun çözümü.

Tekrarlanabilir bir sorun için, [Açın GitHub Sorumluluk](https://github.com/Chreece/HA-Home-Environment-Manager/issues) Beklenen davranış, gerçek davranış, ilgili oda/cihaz ayarları ve yeniden üretilme adımları ile.

Katkı ve iyileştirmeler hoş karşılanmaktadır. [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Destek ve lisans

Eğer HEM Sana yararlı olur, yapabilirsin [Ko-fi'de Türkiye'ye destek](https://ko-fi.com/chreece).

Bölüm: [MIT Lisansı](../../LICENSE).
