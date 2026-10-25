"""Localized rooms-first setup, applied after all existing translation passes."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path

# Room selector title; windows; air/environment; pressure; room help; general help.
TEXT = {
'en': ('Rooms to monitor', 'Windows', 'Air quality and environmental sensors', 'Pressure sensors', 'Select inputs for this room. Each choice shows device name - entity name (state), omitting empty parts. Empty groups stay unused; they never enable automatic discovery or equipment control.', 'Select shared input sources and notification outputs. Save finishes setup. Operating settings remain on the Home and room devices.'),
'el': ('Χώροι για παρακολούθηση', 'Παράθυρα', 'Αισθητήρες ποιότητας αέρα και περιβάλλοντος', 'Αισθητήρες πίεσης', 'Επίλεξε τις εισόδους του χώρου. Κάθε επιλογή δείχνει όνομα συσκευής - όνομα οντότητας (κατάσταση), χωρίς κενά τμήματα. Οι κενές ομάδες δεν χρησιμοποιούνται και δεν ενεργοποιούν αυτόματη ανακάλυψη ή έλεγχο εξοπλισμού.', 'Επίλεξε κοινές πηγές δεδομένων και εξόδους ειδοποιήσεων. Η αποθήκευση ολοκληρώνει τη ρύθμιση. Οι παράμετροι λειτουργίας βρίσκονται στις συσκευές του σπιτιού και των χώρων.'),
'de': ('Zu überwachende Räume', 'Fenster', 'Luftqualitäts- und Umgebungssensoren', 'Drucksensoren', 'Eingänge für diesen Raum auswählen. Jede Auswahl zeigt Gerätename - Entitätsname (Zustand), ohne leere Bestandteile. Leere Gruppen bleiben ungenutzt; sie aktivieren weder automatische Erkennung noch Gerätesteuerung.', 'Gemeinsame Datenquellen und Benachrichtigungsausgänge auswählen. Speichern beendet die Einrichtung. Betriebsparameter bleiben auf den Haus- und Raumgeräten.'),
'fr': ('Pièces à surveiller', 'Fenêtres', 'Capteurs de qualité de l’air et d’environnement', 'Capteurs de pression', 'Sélectionnez les entrées de cette pièce : nom de l’appareil - nom de l’entité. Les groupes vides restent inutilisés et n’activent ni découverte automatique ni commande.', 'Sélectionnez les sources communes et les sorties de notification. Enregistrer termine la configuration. Les réglages de fonctionnement restent sur les appareils de la maison et des pièces.'),
'es': ('Estancias que supervisar', 'Ventanas', 'Sensores de calidad del aire y del entorno', 'Sensores de presión', 'Selecciona las entradas de esta estancia: nombre del dispositivo - nombre de la entidad. Los grupos vacíos no se usan ni activan descubrimiento o control automático.', 'Selecciona fuentes compartidas y salidas de notificación. Guardar termina la configuración. Los ajustes de funcionamiento quedan en los dispositivos de la casa y las estancias.'),
'it': ('Stanze da monitorare', 'Finestre', 'Sensori della qualità dell’aria e ambientali', 'Sensori di pressione', 'Seleziona gli ingressi della stanza: nome dispositivo - nome entità. I gruppi vuoti non vengono usati e non attivano rilevamento o controllo automatico.', 'Seleziona fonti condivise e uscite di notifica. Salva completa la configurazione. Le impostazioni operative restano sui dispositivi della casa e delle stanze.'),
'nl': ('Te bewaken kamers', 'Ramen', 'Luchtkwaliteits- en omgevingssensoren', 'Druksensoren', 'Selecteer ingangen voor deze kamer: apparaatnaam - entiteitsnaam. Lege groepen blijven ongebruikt en activeren geen automatische detectie of bediening.', 'Selecteer gedeelde bronnen en meldingsuitgangen. Opslaan voltooit de installatie. Bedrijfsinstellingen blijven op de huis- en kamerapparaten.'),
'pt': ('Divisões a monitorizar', 'Janelas', 'Sensores de qualidade do ar e do ambiente', 'Sensores de pressão', 'Selecione entradas da divisão: nome do dispositivo - nome da entidade. Grupos vazios não são usados e não ativam descoberta nem controlo automático.', 'Selecione fontes partilhadas e saídas de notificação. Guardar conclui a configuração. Os parâmetros de operação ficam nos dispositivos da casa e das divisões.'),
'pt-BR': ('Ambientes para monitorar', 'Janelas', 'Sensores de qualidade do ar e do ambiente', 'Sensores de pressão', 'Selecione entradas do ambiente: nome do dispositivo - nome da entidade. Grupos vazios não são usados e não ativam descoberta nem controle automático.', 'Selecione fontes compartilhadas e saídas de notificação. Salvar conclui a configuração. Os parâmetros de operação ficam nos dispositivos da casa e dos ambientes.'),
'pl': ('Pomieszczenia do monitorowania', 'Okna', 'Czujniki jakości powietrza i otoczenia', 'Czujniki ciśnienia', 'Wybierz wejścia pomieszczenia: nazwa urządzenia - nazwa encji. Puste grupy pozostają nieużywane i nie włączają automatycznego wykrywania ani sterowania.', 'Wybierz wspólne źródła i wyjścia powiadomień. Zapis kończy konfigurację. Ustawienia pracy pozostają na urządzeniach domu i pomieszczeń.'),
'cs': ('Sledované místnosti', 'Okna', 'Snímače kvality vzduchu a prostředí', 'Snímače tlaku', 'Vyberte vstupy místnosti: název zařízení - název entity. Prázdné skupiny se nepoužívají a nezapínají automatické vyhledávání ani řízení.', 'Vyberte společné zdroje a výstupy oznámení. Uložení dokončí nastavení. Provozní nastavení zůstává na zařízeních domu a místností.'),
'sk': ('Monitorované miestnosti', 'Okná', 'Snímače kvality vzduchu a prostredia', 'Snímače tlaku', 'Vyberte vstupy miestnosti: názov zariadenia - názov entity. Prázdne skupiny sa nepoužívajú a nezapínajú automatické vyhľadávanie ani riadenie.', 'Vyberte spoločné zdroje a výstupy oznámení. Uloženie dokončí nastavenie. Prevádzkové nastavenia zostávajú na zariadeniach domu a miestností.'),
'sv': ('Rum att övervaka', 'Fönster', 'Luftkvalitets- och miljösensorer', 'Trycksensorer', 'Välj rummets ingångar: enhetsnamn - entitetsnamn. Tomma grupper används inte och aktiverar varken automatisk upptäckt eller styrning.', 'Välj gemensamma källor och aviseringsutgångar. Spara slutför inställningen. Driftinställningarna finns kvar på husets och rummens enheter.'),
'da': ('Rum der skal overvåges', 'Vinduer', 'Luftkvalitets- og miljøsensorer', 'Tryksensorer', 'Vælg rummets indgange: enhedsnavn - entitetsnavn. Tomme grupper bruges ikke og aktiverer ikke automatisk registrering eller styring.', 'Vælg fælles kilder og notifikationsudgange. Gem afslutter opsætningen. Driftsindstillinger forbliver på husets og rummenes enheder.'),
'nb': ('Rom som skal overvåkes', 'Vinduer', 'Luftkvalitets- og miljøsensorer', 'Trykksensorer', 'Velg rommets innganger: enhetsnavn - entitetsnavn. Tomme grupper brukes ikke og aktiverer ikke automatisk oppdagelse eller styring.', 'Velg felles kilder og varslingsutganger. Lagre fullfører oppsettet. Driftsinnstillingene blir på husets og rommenes enheter.'),
'fi': ('Valvottavat huoneet', 'Ikkunat', 'Ilmanlaatu- ja ympäristöanturit', 'Paineanturit', 'Valitse huoneen tulot: laitteen nimi - entiteetin nimi. Tyhjät ryhmät jäävät käyttämättä eivätkä käynnistä automaattista tunnistusta tai ohjausta.', 'Valitse yhteiset lähteet ja ilmoitusten lähdöt. Tallennus päättää määrityksen. Käyttöasetukset jäävät kodin ja huoneiden laitteisiin.'),
'hu': ('Figyelendő helyiségek', 'Ablakok', 'Levegőminőség- és környezeti érzékelők', 'Nyomásérzékelők', 'Válaszd ki a helyiség bemeneteit: eszköznév - entitásnév. Az üres csoportok nem használtak, és nem indítanak automatikus felismerést vagy vezérlést.', 'Válassz közös forrásokat és értesítési kimeneteket. A mentés befejezi a beállítást. Az üzemi beállítások a ház és a helyiségek eszközein maradnak.'),
'ro': ('Camere de monitorizat', 'Ferestre', 'Senzori de calitate a aerului și de mediu', 'Senzori de presiune', 'Selectează intrările camerei: numele dispozitivului - numele entității. Grupurile goale rămân neutilizate și nu activează descoperirea sau controlul automat.', 'Selectează sursele comune și ieșirile de notificare. Salvarea încheie configurarea. Setările de funcționare rămân pe dispozitivele casei și camerelor.'),
'bg': ('Стаи за наблюдение', 'Прозорци', 'Датчици за качество на въздуха и средата', 'Датчици за налягане', 'Изберете входовете на стаята: име на устройство - име на обект. Празните групи не се използват и не включват автоматично откриване или управление.', 'Изберете общи източници и изходи за известия. Записването завършва настройката. Работните настройки остават на устройствата на дома и стаите.'),
'hr': ('Sobe za praćenje', 'Prozori', 'Senzori kvalitete zraka i okoliša', 'Senzori tlaka', 'Odaberite ulaze sobe: naziv uređaja - naziv entiteta. Prazne se grupe ne koriste i ne uključuju automatsko otkrivanje ni upravljanje.', 'Odaberite zajedničke izvore i izlaze obavijesti. Spremanje završava postavljanje. Radne postavke ostaju na uređajima doma i soba.'),
'sr': ('Собе за праћење', 'Прозори', 'Сензори квалитета ваздуха и околине', 'Сензори притиска', 'Изаберите улазе собе: назив уређаја - назив ентитета. Празне групе се не користе и не укључују аутоматско откривање ни управљање.', 'Изаберите заједничке изворе и излазе обавештења. Чување завршава подешавање. Радна подешавања остају на уређајима дома и соба.'),
'ru': ('Комнаты для наблюдения', 'Окна', 'Датчики качества воздуха и среды', 'Датчики давления', 'Выберите входы комнаты: имя устройства - имя сущности. Пустые группы не используются и не включают автоматическое обнаружение или управление.', 'Выберите общие источники и выходы уведомлений. Сохранение завершает настройку. Рабочие параметры остаются на устройствах дома и комнат.'),
'uk': ('Кімнати для спостереження', 'Вікна', 'Датчики якості повітря й середовища', 'Датчики тиску', 'Виберіть входи кімнати: назва пристрою - назва сутності. Порожні групи не використовуються і не вмикають автоматичне виявлення або керування.', 'Виберіть спільні джерела й виходи сповіщень. Збереження завершує налаштування. Робочі параметри залишаються на пристроях дому й кімнат.'),
 'tr': ('İzlenecek odalar', 'Pencereler', 'Hava kalitesi ve çevre sensörleri', 'Basınç sensörleri', 'Odanın girişlerini seçin: cihaz adı - varlık adı. Boş gruplar kullanılmaz ve otomatik keşif veya kontrolü etkinleştirmez.', 'Ortak kaynakları ve bildirim çıkışlarını seçin. Kaydet kurulumu tamamlar. Çalışma ayarları ev ve oda cihazlarında kalır.'),
'ar': ('الغرف المراد مراقبتها', 'النوافذ', 'مستشعرات جودة الهواء والبيئة', 'مستشعرات الضغط', 'اختر مدخلات الغرفة: اسم الجهاز - اسم الكيان. المجموعات الفارغة لا تستخدم ولا تفعّل الاكتشاف أو التحكم التلقائي.', 'اختر المصادر المشتركة ومخرجات الإشعارات. الحفظ ينهي الإعداد. تبقى إعدادات التشغيل على أجهزة المنزل والغرف.'),
'he': ('חדרים למעקב', 'חלונות', 'חיישני איכות אוויר וסביבה', 'חיישני לחץ', 'בחר את קלטי החדר: שם המכשיר - שם הישות. קבוצות ריקות אינן בשימוש ולא מפעילות גילוי או בקרה אוטומטיים.', 'בחר מקורות משותפים ופלטי התראות. שמירה מסיימת את ההגדרה. הגדרות התפעול נשארות במכשירי הבית והחדרים.'),
'fa': ('اتاق‌های مورد پایش', 'پنجره‌ها', 'حسگرهای کیفیت هوا و محیط', 'حسگرهای فشار', 'ورودی‌های اتاق را انتخاب کنید: نام دستگاه - نام موجودیت. گروه‌های خالی استفاده نمی‌شوند و کشف یا کنترل خودکار را فعال نمی‌کنند.', 'منابع مشترک و خروجی‌های اعلان را انتخاب کنید. ذخیره، راه‌اندازی را تمام می‌کند. تنظیمات کارکرد روی دستگاه‌های خانه و اتاق‌ها می‌مانند.'),
'hi': ('निगरानी के कमरे', 'खिड़कियाँ', 'वायु गुणवत्ता और पर्यावरण सेंसर', 'दबाव सेंसर', 'कमरे के इनपुट चुनें: उपकरण का नाम - एंटिटी का नाम। खाली समूह उपयोग नहीं होते और स्वचालित खोज या नियंत्रण चालू नहीं करते।', 'साझा स्रोत और सूचना आउटपुट चुनें। सहेजना सेटअप पूरा करता है। संचालन सेटिंग घर और कमरे के उपकरणों पर रहती हैं।'),
'bn': ('পর্যবেক্ষণের ঘর', 'জানালা', 'বায়ুর গুণমান ও পরিবেশের সেন্সর', 'চাপের সেন্সর', 'ঘরের ইনপুট বেছে নিন: ডিভাইসের নাম - এনটিটির নাম। খালি গোষ্ঠী ব্যবহার হয় না এবং স্বয়ংক্রিয় খোঁজ বা নিয়ন্ত্রণ চালু করে না।', 'যৌথ উৎস ও বিজ্ঞপ্তির আউটপুট বেছে নিন। সংরক্ষণ করলে সেটআপ শেষ হয়। চালনার সেটিং বাড়ি ও ঘরের ডিভাইসে থাকে।'),
 'ta': ('கண்காணிக்க வேண்டிய அறைகள்', 'சாளரங்கள்', 'காற்றுத் தரம் மற்றும் சுற்றுச்சூழல் உணரிகள்', 'அழுத்த உணரிகள்', 'அறையின் உள்ளீடுகளைத் தேர்ந்தெடுக்கவும்: சாதனப் பெயர் - உருப்படிப் பெயர். காலிக் குழுக்கள் பயன்படுத்தப்படாது; தானியங்கிக் கண்டறிதலையோ கட்டுப்பாட்டையோ இயக்காது.', 'பொதுவான மூலங்களையும் அறிவிப்பு வெளியீடுகளையும் தேர்ந்தெடுக்கவும். சேமித்தல் அமைப்பை முடிக்கிறது. இயக்க அமைப்புகள் வீடு மற்றும் அறைச் சாதனங்களில் இருக்கும்.'),
'ur': ('نگرانی کے کمرے', 'کھڑکیاں', 'ہوا کے معیار اور ماحول کے سینسر', 'دباؤ کے سینسر', 'کمرے کے ان پٹ منتخب کریں: آلے کا نام - اینٹیٹی کا نام۔ خالی گروپ استعمال نہیں ہوتے اور خودکار تلاش یا کنٹرول فعال نہیں کرتے۔', 'مشترکہ ذرائع اور اطلاع کے آؤٹ پٹ منتخب کریں۔ محفوظ کرنے سے سیٹ اپ مکمل ہوتا ہے۔ عملی ترتیبات گھر اور کمرے کے آلات پر رہتی ہیں۔'),
'id': ('Ruangan untuk dipantau', 'Jendela', 'Sensor kualitas udara dan lingkungan', 'Sensor tekanan', 'Pilih masukan ruangan: nama perangkat - nama entitas. Kelompok kosong tidak digunakan dan tidak mengaktifkan penemuan atau kendali otomatis.', 'Pilih sumber bersama dan keluaran notifikasi. Simpan menyelesaikan penyiapan. Pengaturan operasi tetap berada pada perangkat rumah dan ruangan.'),
'vi': ('Phòng cần giám sát', 'Cửa sổ', 'Cảm biến chất lượng không khí và môi trường', 'Cảm biến áp suất', 'Chọn đầu vào của phòng: tên thiết bị - tên thực thể. Nhóm trống không được dùng và không bật khám phá hoặc điều khiển tự động.', 'Chọn nguồn chung và đầu ra thông báo. Lưu hoàn tất thiết lập. Cài đặt vận hành nằm trên thiết bị của nhà và phòng.'),
'ko': ('모니터링할 방', '창문', '공기질 및 환경 센서', '압력 센서', '방의 입력을 선택하세요. 기기 이름 - 엔티티 이름으로 표시됩니다. 빈 그룹은 사용하지 않으며 자동 검색이나 제어를 켜지 않습니다.', '공유 소스와 알림 출력을 선택하세요. 저장하면 설정이 끝납니다. 운전 설정은 집과 방의 기기에 남습니다.'),
'ja': ('監視する部屋', '窓', '空気質・環境センサー', '気圧センサー', '部屋の入力を選択します。機器名 - エンティティ名で表示されます。空のグループは使用されず、自動検出や自動制御を有効にしません。', '共通の入力源と通知出力を選択します。保存すると設定が完了します。運転設定は家と部屋のデバイスに残ります。'),
'zh-Hans': ('要监测的房间', '窗户', '空气质量与环境传感器', '压力传感器', '选择房间的输入，显示为设备名称 - 实体名称。空组不使用，也不会启用自动发现或控制。', '选择共享输入源和通知输出。保存即完成设置。运行参数保留在家庭和房间设备上。'),
'zh-Hant': ('要監測的房間', '窗戶', '空氣品質與環境感測器', '壓力感測器', '選擇房間的輸入，顯示為裝置名稱 - 實體名稱。空群組不使用，也不會啟用自動探索或控制。', '選擇共用輸入源和通知輸出。儲存即完成設定。運作參數保留在家庭和房間裝置上。'),
 'th': ('ห้องที่จะตรวจสอบ', 'หน้าต่าง', 'เซ็นเซอร์คุณภาพอากาศและสิ่งแวดล้อม', 'เซ็นเซอร์ความดัน', 'เลือกอินพุตของห้อง โดยแสดงชื่ออุปกรณ์ - ชื่อเอนทิตี กลุ่มว่างจะไม่ใช้และไม่เปิดการค้นหาหรือควบคุมอัตโนมัติ', 'เลือกแหล่งข้อมูลร่วมและเอาต์พุตการแจ้งเตือน บันทึกเพื่อจบการตั้งค่า การตั้งค่าการทำงานยังอยู่บนอุปกรณ์ของบ้านและห้อง'),
}


SHADE_NAMES = {
    'en':'Window blinds, shades and shutters',
    'el':'Σκίαστρα, περσίδες και ρολά παραθύρων',
    'de':'Fensterrollos, Jalousien und Rollläden',
    'fr':'Stores, rideaux et volets de fenêtre',
    'es':'Persianas, estores y cortinas de ventana',
    'it':'Tende, persiane e tapparelle',
    'nl':'Raamzonwering, jaloezieën en rolluiken',
    'pt':'Estores, persianas e cortinas de janela',
    'pt-BR':'Persianas, cortinas e venezianas de janela',
    'pl':'Rolety, żaluzje i zasłony okienne',
    'cs':'Okenní rolety, žaluzie a závěsy',
    'sk':'Okenné rolety, žalúzie a závesy',
    'sv':'Persienner, rullgardiner och fönsterluckor',
    'da':'Persienner, rullegardiner og skodder',
    'nb':'Persienner, rullegardiner og skodder',
    'fi':'Ikkunaverhot, kaihtimet ja luukut',
    'hu':'Ablakredőnyök, reluxák és függönyök',
    'ro':'Jaluzele, rulouri și obloane',
    'bg':'Щори, завеси и капаци за прозорци',
    'hr':'Prozorske rolete, sjenila i žaluzine',
    'sr':'Прозорске ролетне, завесе и жалузине',
    'ru':'Оконные жалюзи, шторы и ставни',
    'uk':'Віконні жалюзі, штори та ролети',
    'tr':'Pencere perdeleri, panjurlar ve jaluziler',
    'ar':'ستائر النوافذ والمصاريع والستائر الدوارة',
    'he':'תריסים, וילונות וצלונים לחלונות',
    'fa':'پرده‌ها، کرکره‌ها و سایه‌بان‌های پنجره',
    'hi':'खिड़की के परदे, ब्लाइंड और शटर',
    'bn':'জানালার পর্দা, ব্লাইন্ড ও শাটার',
    'ta':'சாளரத் திரைகள், பிளைண்டுகள் மற்றும் ஷட்டர்கள்',
    'ur':'کھڑکیوں کے پردے، بلائنڈز اور شٹر',
    'id':'Tirai, gorden, dan penutup jendela',
    'vi':'Rèm, mành và cửa chớp',
    'ko':'창문 블라인드, 차양 및 셔터',
    'ja':'窓のブラインド・シェード・シャッター',
    'zh-Hans':'窗帘、百叶帘及卷帘',
    'zh-Hant':'窗簾、百葉簾及捲簾',
    'th':'ม่าน มู่ลี่ และบานเกล็ดหน้าต่าง',
}


DEVICE_SHADE_HELP = {
  "en": [
    "Select only physical climate.*, humidifier.* and fan.* entities assigned to this room. Their native capabilities determine which heating, cooling, drying, humidity, fan-speed or setpoint controls the Manager can offer. Automatic control and power changes remain off until expressly enabled on each managed device; selecting it here does not operate hardware. Switches and proportional actuators are configured separately.",
    "Select native cover.* window blinds, shutters, shades or curtains in this room. Generic covers without device_class are also supported when their native CLOSE feature is advertised; check that they really are window shades. Garages, gates, doors, actual windows, dampers and awnings are excluded. Selection never moves a cover: its own room child device requires a linked window contact, an automatic-control switch, optional advance announcement and a temperature threshold. Unknown/unavailable covers can be selected but never moved until verified available."
  ],
  "el": [
    "Επίλεξε μόνο φυσικές οντότητες climate.*, humidifier.* και fan.* αυτού του χώρου. Οι πραγματικές δυνατότητες κάθε συσκευής καθορίζουν αν θα χρησιμοποιούνται θέρμανση, ψύξη, αφύγρανση, στόχοι θερμοκρασίας/υγρασίας, ταχύτητα ανεμιστήρα ή on/off. Η επιλογή δεν ενεργοποιεί τον εξοπλισμό: ο αυτόματος έλεγχος ρυθμίζεται ξεχωριστά στη συσκευή-ελεγκτή, με τις αντίστοιχες δικλίδες ασφαλείας. Διακόπτες και αναλογικοί ενεργοποιητές ρυθμίζονται χωριστά.",
    "Επίλεξε ρολά, περσίδες, σκίαστρα ή κουρτίνες τύπου cover.* αυτού του χώρου. Δεκτά είναι και γενικά cover χωρίς device_class, εφόσον υποστηρίζουν την εντολή CLOSE· βεβαιώσου ότι πρόκειται πράγματι για σκίαση παραθύρου. Γκαραζόπορτες, πόρτες, πύλες, πραγματικά παράθυρα, αεραγωγοί και εξωτερικές τέντες εξαιρούνται. Η επιλογή δεν κινεί το ρολό: στη δική του συσκευή-ελεγκτή αντιστοιχίζεις επαφή παραθύρου, αυτόματο έλεγχο, προαιρετική ανακοίνωση και όριο θερμοκρασίας. Αν η κατάσταση είναι unknown/unavailable, επιτρέπεται η επιλογή αλλά όχι η κίνηση."
  ],
  "de": [
    "Nur die physischen climate.*, humidifier.* und fan.*-Entitäten dieses Raums auswählen. Die tatsächlichen Funktionen bestimmen, ob Heizen, Kühlen, Entfeuchten, Sollwerte für Temperatur/Feuchte, Lüfterstufen und Ein/Aus genutzt werden können. Die Auswahl steuert noch nichts; Automatik und Freigaben werden für jedes Controller-Gerät separat aktiviert. Schalter und proportionale Stellantriebe werden gesondert konfiguriert.",
    "Fensterrollos, Jalousien, Rollläden und Vorhänge als cover.* dieses Raums auswählen. Auch generische Covers ohne device_class sind bei unterstützter CLOSE-Funktion zulässig; bitte prüfen, dass es wirklich Fensterbeschattung ist. Garagentore, Türen, Tore, Fenster, Luftklappen und Außenmarkisen sind ausgeschlossen. Die Auswahl bewegt nichts: Auf dem eigenen Controller-Gerät werden Fensterkontakt, Automatik, optionale Vorankündigung und Schließtemperatur eingestellt. Unbekannter/nicht verfügbarer Status verhindert jede Bewegung."
  ],
  "fr": [
    "Sélectionnez uniquement les entités physiques climate.*, humidifier.* et fan.* de cette pièce. Les fonctions natives déterminent les modes chauffage, refroidissement, déshumidification, consignes et vitesse du ventilateur. La sélection n'actionne rien : l'automatisation est activée séparément sur chaque contrôleur.",
    "Sélectionnez les stores, volets et rideaux cover.* de cette pièce. Les covers sans device_class sont acceptés s'ils prennent en charge CLOSE, après vérification qu'il s'agit d'une protection de fenêtre. Portes, garages, portails, fenêtres et auvents sont exclus. La sélection ne déplace rien : associez un contact de fenêtre, activez l'automatisation et réglez annonce et température sur le contrôleur. État inconnu : aucun mouvement."
  ],
  "es": [
    "Selecciona solo las entidades físicas climate.*, humidifier.* y fan.* de esta habitación. Sus capacidades nativas determinan calefacción, refrigeración, secado, consignas y velocidades. Seleccionarlas no acciona nada: habilita el control automático por separado en cada dispositivo.",
    "Selecciona persianas, contraventanas, estores y cortinas cover.* de esta habitación. También se admiten covers sin device_class con función CLOSE, tras comprobar que son protecciones de ventana. Puertas, garajes, portones, ventanas y toldos quedan excluidos. Seleccionar no mueve nada: configura contacto de ventana, automatización, aviso y temperatura en su controlador. Estado desconocido: no se mueve."
  ],
  "it": [
    "Seleziona solo entità fisiche climate.*, humidifier.* e fan.* di questa stanza. Le capacità native definiscono riscaldamento, raffrescamento, deumidificazione, setpoint e velocità. La selezione non comanda nulla: abilita l'automazione nel singolo controller.",
    "Seleziona tapparelle, tende, veneziane e persiane cover.* della stanza. Sono ammessi cover senza device_class se supportano CLOSE, dopo aver verificato che siano schermature di finestre. Porte, garage, cancelli, finestre e tende da sole esterne sono esclusi. La selezione non provoca movimenti: associa il contatto finestra e configura automazione, avviso e temperatura nel controller. Stato sconosciuto: nessun movimento."
  ],
  "nl": [
    "Selecteer alleen fysieke climate.*, humidifier.* en fan.*-entiteiten van deze kamer. De eigen mogelijkheden bepalen verwarmen, koelen, drogen, setpoints en ventilatorsnelheden. Selecteren bedient niets; schakel automatische besturing per apparaat apart in.",
    "Selecteer rolluiken, jaloezieën en gordijnen als cover.* in deze kamer. Covers zonder device_class zijn toegestaan met CLOSE-ondersteuning; controleer dat het echte raamzonwering is. Deuren, garages, poorten, ramen en luifels zijn uitgesloten. Selecteren beweegt niets; koppel raamcontact en stel automatisering, aankondiging en temperatuur in op het controllerapparaat. Onbekende status blokkeert beweging."
  ],
  "pt": [
    "Seleciona apenas entidades físicas climate.*, humidifier.* e fan.* desta divisão. As funções nativas determinam aquecimento, arrefecimento, secagem, temperaturas, humidade e velocidades. A seleção não aciona equipamentos; ativa o controlo automático individualmente.",
    "Seleciona estores, persianas e cortinas cover.* desta divisão. Covers sem device_class são aceites com CLOSE, após verificar que são proteção de janela. Portas, garagens, portões, janelas e toldos exteriores são excluídos. A seleção não move nada: associa o sensor da janela e configura automação, aviso e temperatura no controlador. Estado desconhecido impede o movimento."
  ],
  "pt-BR": [
    "Selecione apenas entidades físicas climate.*, humidifier.* e fan.* deste ambiente. Os recursos nativos determinam aquecimento, resfriamento, secagem, temperaturas, umidade e velocidades. Selecionar não aciona o equipamento; ative o controle automático individualmente.",
    "Selecione persianas, venezianas e cortinas cover.* deste ambiente. Covers sem device_class são aceitos com CLOSE, após confirmar que realmente protegem janelas. Portas, garagens, portões, janelas e toldos são excluídos. Selecionar não movimenta nada: vincule o sensor da janela e configure automação, aviso e temperatura no controlador. Estado desconhecido impede o movimento."
  ],
  "pl": [
    "Wybierz tylko fizyczne encje climate.*, humidifier.* i fan.* tego pokoju. Dostępne funkcje określają ogrzewanie, chłodzenie, osuszanie, nastawy i prędkość wentylatora. Sam wybór niczego nie uruchamia; automatykę włącza się osobno dla urządzenia.",
    "Wybierz rolety, żaluzje i zasłony cover.* tego pokoju. Covers bez device_class są dozwolone z funkcją CLOSE, jeśli naprawdę osłaniają okno. Bramy garażowe, drzwi, furtki, okna i markizy są wykluczone. Wybór niczego nie porusza: przypisz czujnik okna oraz ustaw automatykę, zapowiedź i temperaturę w kontrolerze. Nieznany stan blokuje ruch."
  ],
  "cs": [
    "Vyberte pouze fyzické entity climate.*, humidifier.* a fan.* této místnosti. Nativní možnosti určují vytápění, chlazení, odvlhčování, požadované hodnoty i rychlosti ventilátoru. Výběr nic nespustí; automatiku povolte zvlášť pro každé zařízení.",
    "Vyberte rolety, žaluzie a závěsy cover.* této místnosti. Cover bez device_class lze použít s funkcí CLOSE, pokud skutečně stíní okno. Garáže, vrata, dveře, okna a markýzy jsou vyloučené. Výběr ničím nepohybuje: přiřaďte okenní kontakt a nastavte automatiku, oznámení a teplotu na ovladači. Neznámý stav pohyb blokuje."
  ],
  "sk": [
    "Vyberte iba fyzické entity climate.*, humidifier.* a fan.* tejto miestnosti. Natívne možnosti určujú kúrenie, chladenie, odvlhčovanie, cieľové hodnoty a rýchlosti ventilátora. Výber nič nespustí; automatiku povoľte zvlášť pre každé zariadenie.",
    "Vyberte rolety, žalúzie a závesy cover.* tejto miestnosti. Cover bez device_class je možné použiť s funkciou CLOSE, ak naozaj tieni okno. Garáže, brány, dvere, okná a markízy sú vylúčené. Výber ničím nepohybuje: priraďte okenný kontakt a nastavte automatiku, oznámenie a teplotu na ovládači. Neznámy stav blokuje pohyb."
  ],
  "sv": [
    "Välj bara fysiska climate.*, humidifier.* och fan.* i rummet. Enhetens funktioner styr värme, kyla, avfuktning, börvärden och fläkthastighet. Valet startar inget; automatiken aktiveras separat på varje styrdon.",
    "Välj persienner, rullgardiner och fönsterluckor som cover.* i rummet. Även covers utan device_class stöds med CLOSE om de verkligen skuggar ett fönster. Garage, grindar, dörrar, fönster och markiser utesluts. Valet flyttar inget: tilldela fönsterkontakt och ställ in automatik, avisering och temperatur på styrdonet. Okänd status stoppar rörelse."
  ],
  "da": [
    "Vælg kun fysiske climate.*, humidifier.* og fan.* i rummet. De indbyggede funktioner afgør varme, køling, affugtning, temperaturmål og blæserhastighed. Valget betjener intet; aktiver automatik særskilt på hver enhed.",
    "Vælg rullegardiner, persienner og skodder som cover.* i rummet. Covers uden device_class er tilladt med CLOSE, hvis de reelt skygger vinduer. Garager, porte, døre, vinduer og markiser er udelukket. Valget flytter intet: tilknyt vindueskontakt og indstil automatik, annoncering og temperatur på controlleren. Ukendt status forhindrer bevægelse."
  ],
  "nb": [
    "Velg bare fysiske climate.*, humidifier.* og fan.* i rommet. Enhetens egne funksjoner bestemmer varme, kjøling, avfukting, målverdier og viftehastighet. Valget betjener ingenting; automatikken aktiveres separat på hver enhet.",
    "Velg rullegardiner, persienner og skodder som cover.* i rommet. Covers uten device_class støttes med CLOSE hvis de faktisk skjermer vinduer. Garasjer, porter, dører, vinduer og markiser er utelukket. Valget beveger ingenting: koble vinduskontakt og konfigurer automatikk, kunngjøring og temperatur i kontrolleren. Ukjent status hindrer bevegelse."
  ],
  "fi": [
    "Valitse vain huoneen fyysiset climate.*, humidifier.* ja fan.* -entiteetit. Laitteen omat ominaisuudet määrittävät lämmityksen, jäähdytyksen, kuivauksen, tavoitearvot ja puhallinnopeuden. Valinta ei ohjaa laitetta; ota automatiikka erikseen käyttöön laiteohjaimessa.",
    "Valitse huoneen ikkunaverhot, kaihtimet ja rullaverhot cover.*. Myös ilman device_class-tietoa olevat cover-entiteetit käyvät, jos CLOSE on tuettu ja kyse on ikkunavarjostimesta. Autotallit, portit, ovet, ikkunat ja markiisit on suljettu pois. Valinta ei liikuta mitään: määritä ikkunakosketin sekä automatiikka, ilmoitus ja lämpötilaraja ohjaimessa. Tuntematon tila estää liikkeen."
  ],
  "hu": [
    "Csak a szoba valódi climate.*, humidifier.* és fan.* entitásait válaszd. A natív képességek határozzák meg a fűtést, hűtést, párátlanítást, célértékeket és ventilátorsebességet. A kiválasztás nem kapcsol be semmit; az automatika eszközönként engedélyezhető.",
    "Válaszd ki a szoba cover.* redőnyeit, reluxáit és függönyeit. A device_class nélküli cover is megengedett CLOSE funkcióval, ha valóban ablakot árnyékol. Garázskapuk, ajtók, kapuk, ablakok és napellenzők kizárva. A kiválasztás nem mozgat semmit: rendelj hozzá ablakérzékelőt, majd állítsd be az automatikát, értesítést és hőmérsékletet. Ismeretlen állapotban nincs mozgás."
  ],
  "ro": [
    "Selectează doar entitățile fizice climate.*, humidifier.* și fan.* ale camerei. Funcțiile native determină încălzirea, răcirea, dezumidificarea, valorile-țintă și viteza ventilatorului. Selectarea nu acționează nimic; activează separat controlul automat pe dispozitiv.",
    "Selectează jaluzele, rulouri și perdele cover.* ale camerei. Covers fără device_class sunt acceptate cu funcția CLOSE dacă umbresc cu adevărat ferestre. Garaje, porți, uși, ferestre și copertine sunt excluse. Selectarea nu mișcă nimic: asociază senzorul ferestrei și setează automatizarea, anunțul și temperatura pe controller. Starea necunoscută blochează mișcarea."
  ],
  "bg": [
    "Избери само физическите climate.*, humidifier.* и fan.* в стаята. Вградените им функции определят отопление, охлаждане, изсушаване, целеви стойности и скорост на вентилатора. Изборът не включва нищо; автоматиката се разрешава за всяко устройство поотделно.",
    "Избери щори, ролетни щори и завеси cover.* в стаята. Covers без device_class се приемат при функция CLOSE, ако действително засенчват прозорец. Гаражи, порти, врати, прозорци и тенти се изключват. Изборът не движи нищо: посочи датчик за прозорец и настрой автоматиката, известието и температурата в контролера. Неизвестното състояние блокира движение."
  ],
  "hr": [
    "Odaberi samo fizičke entitete climate.*, humidifier.* i fan.* ove sobe. Izvorne funkcije određuju grijanje, hlađenje, odvlaživanje, zadane vrijednosti i brzinu ventilatora. Sam odabir ništa ne pokreće; automatiku uključi zasebno za uređaj.",
    "Odaberi rolete, žaluzine i zavjese cover.* ove sobe. Covers bez device_class prihvaćaju se uz CLOSE ako su stvarno zasjenjivači prozora. Garaže, vrata, kapije, prozori i tende su isključeni. Odabir ništa ne pomiče: dodijeli senzor prozora i postavi automatiku, najavu i temperaturu na kontroleru. Nepoznato stanje blokira pokret."
  ],
  "sr": [
    "Изабери само физичке ентитете climate.*, humidifier.* и fan.* ове собе. Изворне могућности одређују грејање, хлађење, одвлаживање, циљеве и брзину вентилатора. Сам избор ништа не покреће; аутоматику укључи за сваки уређај посебно.",
    "Изабери ролетне, жалузине и завесе cover.* ове собе. Covers без device_class су дозвољени уз CLOSE ако заиста заклањају прозор. Гараже, капије, врата, прозори и тенде су искључени. Избор ништа не покреће: повежи сензор прозора и подеси аутоматику, најаву и температуру на контролеру. Непознато стање блокира кретање."
  ],
  "ru": [
    "Выберите только физические climate.*, humidifier.* и fan.* этой комнаты. Поддерживаемые устройством функции определяют отопление, охлаждение, осушение, уставки и скорость вентилятора. Сам выбор ничего не включает; автоматическое управление включается отдельно для каждого устройства.",
    "Выберите рольставни, жалюзи и шторы cover.* этой комнаты. Covers без device_class допускаются при наличии CLOSE, если это действительно оконная защита. Гаражи, ворота, двери, окна и маркизы исключены. Выбор ничего не двигает: привяжите датчик окна и настройте автоматику, оповещение и температуру в контроллере. Неизвестное состояние блокирует движение."
  ],
  "uk": [
    "Виберіть лише фізичні climate.*, humidifier.* і fan.* цієї кімнати. Можливості пристрою визначають опалення, охолодження, осушення, цільові значення й швидкість вентилятора. Вибір нічого не вмикає; автоматичне керування дозволяється окремо для кожного пристрою.",
    "Виберіть ролети, жалюзі та штори cover.* цієї кімнати. Covers без device_class дозволені за наявності CLOSE, якщо вони справді затінюють вікно. Гаражі, ворота, двері, вікна та маркізи виключені. Вибір нічого не рухає: прив’яжіть датчик вікна й налаштуйте автоматику, оголошення та температуру на контролері. Невідомий стан блокує рух."
  ],
  "tr": [
    "Yalnızca odadaki fiziksel climate.*, humidifier.* ve fan.* varlıklarını seçin. Cihazın yerel özellikleri ısıtma, soğutma, nem alma, hedefler ve fan hızını belirler. Seçim cihazı çalıştırmaz; otomatik kontrolü her cihazda ayrıca etkinleştirin.",
    "Odadaki cover.* panjur, stor ve perdeleri seçin. device_class olmayan covers, CLOSE destekliyorsa ve gerçekten pencere gölgeliyorsa kabul edilir. Garajlar, kapılar, geçitler, pencereler ve tenteler hariçtir. Seçim hareket ettirmez: pencere sensörünü bağlayın, otomatik kontrolü, duyuruyu ve sıcaklığı ayarlayın. Bilinmeyen durum hareketi engeller."
  ],
  "ar": [
    "اختر فقط كيانات climate.* و humidifier.* و fan.* الفعلية في الغرفة. تحدد قدرات الجهاز أوضاع التدفئة والتبريد وإزالة الرطوبة والقيم المستهدفة وسرعات المروحة. الاختيار لا يشغّل أي جهاز؛ فعّل التحكم الآلي لكل جهاز بشكل مستقل.",
    "اختر ستائر ونوافذ التظليل من نوع cover.* في الغرفة. تُقبل covers دون device_class إذا دعمت CLOSE وكانت فعلًا لتظليل النافذة. تُستبعد أبواب المرآب والبوابات والأبواب والنوافذ والمظلات الخارجية. الاختيار لا يحرك شيئًا: اربط مستشعر النافذة واضبط التحكم والإعلان ودرجة الحرارة في وحدة التحكم. الحالة غير المعروفة تمنع الحركة."
  ],
  "he": [
    "בחר רק ישויות פיזיות climate.*, humidifier.* ו־fan.* בחדר. יכולות המכשיר קובעות חימום, קירור, ייבוש, ערכי יעד ומהירות מאוורר. הבחירה אינה מפעילה דבר; יש לאפשר שליטה אוטומטית לכל מכשיר בנפרד.",
    "בחר תריסים, וילונות והצללות cover.* בחדר. Covers ללא device_class מותרים אם CLOSE נתמך והם אכן הצללת חלון. דלתות, שערים, חניות, חלונות וסוככים מוחרגים. הבחירה אינה מזיזה דבר: שייך חיישן חלון והגדר אוטומציה, הודעה וטמפרטורה בבקר. מצב לא ידוע חוסם תנועה."
  ],
  "fa": [
    "فقط موجودیت‌های فیزیکی climate.*، humidifier.* و fan.* اتاق را انتخاب کنید. توانایی دستگاه نوع گرمایش، سرمایش، خشک‌سازی، هدف‌ها و سرعت فن را تعیین می‌کند. انتخاب دستگاه را روشن نمی‌کند؛ کنترل خودکار را جداگانه برای هر دستگاه فعال کنید.",
    "پرده، کرکره و سایه‌بان پنجره از نوع cover.* این اتاق را انتخاب کنید. Covers بدون device_class با قابلیت CLOSE و پس از تأیید کاربرد پنجره پذیرفته می‌شوند. درها، دروازه‌ها، گاراژ، پنجره و سایبان بیرونی مجاز نیستند. انتخاب حرکتی ایجاد نمی‌کند: حسگر پنجره، کنترل خودکار، اعلان و دما را در کنترل‌کننده تنظیم کنید. وضعیت نامعلوم مانع حرکت است."
  ],
  "hi": [
    "इस कमरे के वास्तविक climate.*, humidifier.* और fan.* उपकरण चुनें। उनकी मूल क्षमताएँ हीटिंग, कूलिंग, नमी हटाने, लक्ष्य मान और पंखे की गति तय करती हैं। चुनने से उपकरण नहीं चलता; प्रत्येक नियंत्रक पर स्वचालन अलग से सक्षम करें।",
    "कमरे की cover.* खिड़की की ब्लाइंड, रोलर शटर और पर्दे चुनें। device_class के बिना covers भी CLOSE समर्थन पर मान्य हैं, यदि वे सचमुच खिड़की पर लगे हों। गैराज, गेट, दरवाज़े, खिड़कियाँ और बाहरी शामियाने मान्य नहीं हैं। चयन कुछ नहीं हिलाता; विंडो सेंसर, ऑटो नियंत्रण, घोषणा और ताप सीमा नियंत्रक पर सेट करें। अज्ञात स्थिति में गति निषिद्ध है।"
  ],
  "bn": [
    "এই ঘরের প্রকৃত climate.*, humidifier.* এবং fan.* সত্তা নির্বাচন করুন। ডিভাইসের নিজস্ব ক্ষমতা গরম, ঠান্ডা, আর্দ্রতা কমানো, লক্ষ্য মান ও ফ্যানের গতি নির্ধারণ করে। নির্বাচন করলে কিছু চালু হয় না; প্রতিটি নিয়ন্ত্রকে স্বয়ংক্রিয় নিয়ন্ত্রণ আলাদাভাবে চালু করুন।",
    "এই ঘরের cover.* জানালার ব্লাইন্ড, রোলার শাটার ও পর্দা নির্বাচন করুন। device_class না থাকলেও CLOSE সমর্থিত এবং এটি সত্যিকারের জানালার ছায়া হলে গ্রহণযোগ্য। গ্যারেজ, গেট, দরজা, জানালা ও বাইরের ছাউনি বাদ। নির্বাচন কিছু নড়ায় না; জানালার সেন্সর যুক্ত করে স্বয়ংক্রিয় নিয়ন্ত্রণ, ঘোষণা ও তাপমাত্রা নির্ধারণ করুন। অজানা অবস্থায় চলাচল বন্ধ।"
  ],
  "ta": [
    "இந்த அறையின் உண்மையான climate.*, humidifier.* மற்றும் fan.* சாதனங்களைத் தேர்ந்தெடுக்கவும். சாதனத்தின் திறன்களைப் பொறுத்து வெப்பம், குளிர்ச்சி, ஈரநீக்கம், இலக்குகள் மற்றும் விசிறி வேகம் பயன்படுத்தப்படும். தேர்வு மட்டும் எந்தச் சாதனத்தையும் இயக்காது; ஒவ்வொரு கட்டுப்பாட்டிலும் தானியங்கியைத் தனியாக இயக்கு.",
    "அறையின் cover.* ஜன்னல் திரைகள், ரோலர் ஷட்டர்கள் மற்றும் குருட்டுத் திரைகளைத் தேர்ந்தெடுக்கவும். device_class இல்லாவிட்டாலும் CLOSE ஆதரவு இருந்தால், அது உண்மையான ஜன்னல் நிழலாக இருப்பதை உறுதிசெய்க. கேரேஜ், வாயில், கதவு, ஜன்னல் மற்றும் வெளிப்புற கூடாரங்கள் தவிர்க்கப்படும். தேர்வு இயக்காது; ஜன்னல் உணரி, தானியங்கி, அறிவிப்பு மற்றும் வெப்ப எல்லையை கட்டுப்பாட்டில் அமைக்கவும். அறியாத நிலையில் இயக்கம் தடுக்கப்படும்."
  ],
  "ur": [
    "صرف کمرے کے حقیقی climate.*, humidifier.* اور fan.* آلات منتخب کریں۔ آلے کی اپنی صلاحیتیں گرم/ٹھنڈا کرنا، نمی کم کرنا، مطلوبہ قدریں اور پنکھے کی رفتار طے کرتی ہیں۔ انتخاب سے آلہ نہیں چلتا؛ ہر کنٹرولر میں خودکار کنٹرول الگ فعال کریں۔",
    "کمرے کے cover.* رولر شٹر، بلائنڈ اور پردے منتخب کریں۔ device_class کے بغیر covers بھی CLOSE کی مدد سے منظور ہیں بشرطیکہ وہ واقعی کھڑکی کے پردے ہوں۔ گیراج، گیٹ، دروازے، کھڑکیاں اور بیرونی سائبان خارج ہیں۔ انتخاب حرکت نہیں کرتا؛ کھڑکی سینسر، خودکار کنٹرول، اعلان اور درجہ حرارت کنٹرولر پر مقرر کریں۔ نامعلوم حالت میں حرکت نہیں ہوگی۔"
  ],
  "id": [
    "Pilih hanya entitas fisik climate.*, humidifier.* dan fan.* di ruangan ini. Kemampuan asli perangkat menentukan pemanasan, pendinginan, pengeringan, target suhu/kelembapan dan kecepatan kipas. Memilih tidak menggerakkan perangkat; aktifkan kontrol otomatis terpisah.",
    "Pilih tirai, kerai dan penutup jendela cover.* di ruangan ini. Covers tanpa device_class diterima bila mendukung CLOSE dan benar-benar peneduh jendela. Garasi, gerbang, pintu, jendela dan awning dikecualikan. Pemilihan tidak menggerakkan apa pun: pasangkan sensor jendela dan atur otomatisasi, pengumuman dan batas suhu di pengontrol. Status tak diketahui mencegah gerakan."
  ],
  "vi": [
    "Chỉ chọn các thực thể vật lý climate.*, humidifier.* và fan.* trong phòng. Tính năng gốc quyết định sưởi, làm mát, hút ẩm, mức đặt và tốc độ quạt. Việc chọn không điều khiển thiết bị; hãy bật tự động riêng trên mỗi bộ điều khiển.",
    "Chọn rèm cuốn, mành và cửa chớp cover.* của phòng. Covers không có device_class vẫn được chấp nhận nếu hỗ trợ CLOSE và thực sự che nắng cửa sổ. Gara, cổng, cửa ra vào, cửa sổ và mái che ngoài trời bị loại. Chọn không di chuyển gì: gán cảm biến cửa sổ rồi cấu hình tự động, thông báo và ngưỡng nhiệt độ. Trạng thái không rõ ngăn mọi chuyển động."
  ],
  "ko": [
    "방에 속한 실제 climate.*, humidifier.*, fan.* 엔티티만 선택하세요. 기기의 기본 기능에 따라 난방, 냉방, 제습, 목표값, 팬 속도를 제어할 수 있습니다. 선택만으로 기기는 동작하지 않으며 각 컨트롤러에서 자동 제어를 별도로 켜야 합니다.",
    "이 방의 cover.* 블라인드, 롤러 셔터, 커튼을 선택하세요. device_class가 없어도 CLOSE를 지원하고 실제 창문 차양이라면 선택할 수 있습니다. 차고문, 대문, 출입문, 창문 및 외부 차양은 제외합니다. 선택만으로 움직이지 않으며 컨트롤러에서 창문 센서, 자동 제어, 사전 알림 및 온도 기준을 설정하세요. 알 수 없는 상태에서는 작동하지 않습니다."
  ],
  "ja": [
    "この部屋の実機 climate.*、humidifier.*、fan.* のエンティティだけを選択します。対応する暖房・冷房・除湿、設定温湿度、ファン速度は機器の機能に依存します。選択だけでは動作せず、各コントローラーで自動制御を個別に有効にします。",
    "部屋の cover.* ブラインド、ローラーシャッター、カーテンを選択します。device_class がなくても CLOSE に対応し、実際の窓の日除けなら選択できます。ガレージ、門、ドア、窓、屋外オーニングは除外します。選択だけでは動かず、コントローラーで窓センサー、自動制御、事前通知、温度しきい値を設定します。状態不明時は動作しません。"
  ],
  "zh-Hans": [
    "只选择本房间实际的 climate.*、humidifier.* 和 fan.* 实体。设备自身的能力决定供暖、制冷、除湿、温湿度目标和风扇速度。选择不会立即控制设备；须在每台设备控制器中分别启用自动控制。",
    "选择本房间的 cover.* 百叶帘、卷帘、卷闸和窗帘。没有 device_class 的 covers 只要支持 CLOSE 且确实用于窗户遮阳，也可以选择。车库门、门、闸门、窗户及室外遮阳棚均排除。仅选择不会移动：请在控制器中指定窗户传感器、自动控制、提前通知和温度阈值。状态未知时禁止移动。"
  ],
  "zh-Hant": [
    "只選擇本房間實際的 climate.*、humidifier.* 和 fan.* 實體。裝置本身的能力決定暖氣、冷房、除濕、溫濕度目標與風扇速度。選取不會立即控制裝置；須在各裝置控制器內分別啟用自動控制。",
    "選擇本房間的 cover.* 百葉簾、捲簾、捲閘與窗簾。沒有 device_class 的 covers 只要支援 CLOSE 且確實用於窗戶遮陽，也可選擇。車庫門、門、閘門、窗戶與室外遮陽棚均排除。僅選取不會移動：請在控制器中指定窗戶感測器、自動控制、提前通知及溫度門檻。狀態未知時禁止移動。"
  ],
  "th": [
    "เลือกเฉพาะเอนทิตีอุปกรณ์จริง climate.*, humidifier.* และ fan.* ในห้องนี้ ความสามารถของอุปกรณ์กำหนดการทำความร้อน ความเย็น ลดความชื้น ค่าเป้าหมาย และความเร็วพัดลม การเลือกยังไม่สั่งงาน ต้องเปิดระบบอัตโนมัติแยกในแต่ละตัวควบคุม",
    "เลือกม่าน มู่ลี่ และบานเกล็ดหน้าต่าง cover.* ของห้อง Covers ที่ไม่มี device_class ใช้ได้เมื่อรองรับ CLOSE และเป็นอุปกรณ์บังแดดหน้าต่างจริง โรงรถ ประตู รั้ว หน้าต่างและกันสาดภายนอกถูกยกเว้น การเลือกไม่ทำให้เคลื่อนที่: เชื่อมเซ็นเซอร์หน้าต่างแล้วตั้งค่าอัตโนมัติ การแจ้งล่วงหน้า และอุณหภูมิที่ตัวควบคุม สถานะไม่ทราบห้ามเคลื่อนไหว"
  ]
}

def apply_document(doc: dict, lang: str, words: dict) -> None:
    rooms, windows, air, pressure, help_text, general_help = TEXT[lang]
    labels = {"windows": windows, "air_quality": air, "temperature": words['temperature'],
              "humidity": words['humidity'], "pressure": pressure, "climate_devices": words['devices'],
              "shades": SHADE_NAMES[lang]}
    for scope in ('config', 'options'):
        target = doc.setdefault(scope, {})
        steps = target.setdefault('step', {})
        # All general source labels/help already have independently maintained
        # native translations. Reuse them without a second divergent vocabulary.
        general_data, general_details = {}, {}
        for name in ('weather', 'outdoor', 'general_settings', 'pollen', 'delivery', 'areas'):
            block = doc.get('options', {}).get('step', {}).get(name, {})
            block = {**block, **steps.get(name, {})}
            general_data.update(block.get('data', {}))
            general_details.update(block.get('data_description', {}))
        keys = ('weather_entities', 'outdoor_sensors', 'weather_warnings', 'general_room_occupancy_sensors',
                'general_home_trackers', 'general_occupied_rooms_entity', 'general_occupied_rooms_attribute',
                'general_sleep_rooms_entity', 'general_sleep_rooms_attribute', 'pollen_entity', 'notify_entities',
                'media_players', 'tts_engine', 'ai_conversation_agent', 'language', 'use_mold_indicator')
        steps['setup_rooms'] = {'title': rooms, 'description': f"{rooms} → {words['source']} → {words['general']} {words['settings']}",
            'data': {'areas': rooms}, 'data_description': {'areas': rooms + '. ' + help_text}}
        steps['setup_room_sources'] = {'title': words['room'] + ' · {area_name} · {room_index}/{room_count}',
            'description': help_text, 'data': labels,
            'data_description': {
                k: f"{v}. " + (
                    DEVICE_SHADE_HELP[lang][0] if k == "climate_devices" else
                    DEVICE_SHADE_HELP[lang][1] if k == "shades" else help_text)
                for k, v in labels.items()}}
        steps['setup_general'] = {'title': f"{words['general']} {words['settings']}", 'description': general_help,
            'data': {k: general_data[k] for k in keys},
            'data_description': {k: general_details.get(k, general_help) for k in keys}}
        target.setdefault('error', {}).update(
            invalid_setup_rooms=f"{words['invalid']}: {rooms}",
            invalid_room_source=f"{words['invalid']}: {words['room']} · {words['source']}")
        target.setdefault('abort', {}).update(
            setup_area_removed=f"{words['invalid']}: {rooms}",
            setup_changed=f"{words['settings']} ↻ {rooms}")


def apply_room_setup_i18n(root: Path) -> None:
    vocab = json.loads((root / 'compact_locales.json').read_text(encoding='utf-8'))
    files = sorted((root / 'translations').glob('*.json'))
    if (set(TEXT) != set(vocab) or set(TEXT) != {p.stem for p in files}
            or set(SHADE_NAMES) != set(TEXT)
            or set(DEVICE_SHADE_HELP) != set(TEXT)):
        raise ValueError('Every supported setup language must be supplied')
    for path in [root / 'strings.json', *files]:
        lang = 'en' if path.name == 'strings.json' else path.stem
        doc = json.loads(path.read_text(encoding='utf-8'))
        apply_document(doc, lang, vocab[lang])
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
