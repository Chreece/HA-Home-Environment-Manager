"""Reviewed labels and help for the room-local window-closure advice delay."""

WINDOW_CLOSE_COOLDOWN_TEXT = {
    "en": {
        "label": "Wait before suggesting window closure (min)",
        "help": "After a window opens following HEM opening advice, wait this many minutes before suggesting that it be closed, even when outside conditions are unsuitable. Applies independently to each room. 0–60 minutes, default 5; 0 disables the delay. Device pause and protection rules remain active.",
    },
    "el": {
        "label": "Αναμονή πριν από πρόταση κλεισίματος παραθύρου (λεπτά)",
        "help": "Όταν ανοίγει παράθυρο μετά από πρόταση αερισμού του HEM, περιμένει τόσα λεπτά πριν προτείνει να κλείσει, ακόμη κι αν οι εξωτερικές συνθήκες δεν είναι κατάλληλες. Η αναμονή ισχύει ανεξάρτητα για κάθε χώρο. 0–60 λεπτά, προεπιλογή 5· το 0 απενεργοποιεί την αναμονή. Οι κανόνες παύσης και προστασίας των συσκευών παραμένουν ενεργοί.",
    },
    "de": {
        "label": "Wartezeit vor dem Hinweis zum Fensterschließen (min)",
        "help": "Wird ein Fenster nach einem Lüftungshinweis von HEM geöffnet, wartet HEM so viele Minuten, bevor es zum Schließen auffordert, auch bei ungeeigneten Außenbedingungen. Die Wartezeit gilt für jeden Raum unabhängig. 0–60 Minuten, Standard 5; 0 deaktiviert die Wartezeit. Die Regeln zum Pausieren und Schützen der Geräte bleiben aktiv.",
    },
    "fr": {
        "label": "Délai avant de suggérer de fermer une fenêtre (min)",
        "help": "Lorsqu’une fenêtre est ouverte après un conseil d’aération de HEM, attendre ce nombre de minutes avant de suggérer de la fermer, même si les conditions extérieures sont défavorables. Le délai s’applique indépendamment à chaque pièce. 0–60 minutes, 5 par défaut ; 0 désactive le délai. Les règles de mise en pause et de protection des appareils restent actives.",
    },
    "es": {
        "label": "Espera antes de sugerir cerrar una ventana (min)",
        "help": "Cuando se abre una ventana siguiendo una sugerencia de HEM, espera estos minutos antes de sugerir que se cierre, incluso si las condiciones exteriores no son adecuadas. La espera se aplica de forma independiente a cada habitación. 0–60 minutos, 5 por defecto; 0 desactiva la espera. Las reglas de pausa y protección de los equipos siguen activas.",
    },
    "it": {
        "label": "Attesa prima di suggerire la chiusura della finestra (min)",
        "help": "Quando una finestra viene aperta dopo un suggerimento di aerazione di HEM, attende questo numero di minuti prima di suggerire di chiuderla, anche se le condizioni esterne non sono adatte. L’attesa si applica indipendentemente a ogni stanza. 0–60 minuti, valore predefinito 5; 0 disattiva l’attesa. Le regole di pausa e protezione dei dispositivi restano attive.",
    },
    "nl": {
        "label": "Wachttijd voordat sluiten van het raam wordt voorgesteld (min)",
        "help": "Wanneer een raam wordt geopend na een ventilatieadvies van HEM, wacht HEM dit aantal minuten voordat het voorstelt het raam te sluiten, ook als de buitenomstandigheden ongeschikt zijn. De wachttijd geldt afzonderlijk voor elke kamer. 0–60 minuten, standaard 5; 0 schakelt de wachttijd uit. De regels voor het pauzeren en beschermen van apparaten blijven actief.",
    },
    "pt": {
        "label": "Espera antes de sugerir fechar a janela (min)",
        "help": "Quando uma janela é aberta após uma sugestão de arejamento do HEM, aguarda este número de minutos antes de sugerir que seja fechada, mesmo que as condições exteriores não sejam adequadas. A espera aplica-se de forma independente a cada divisão. 0–60 minutos, valor predefinido 5; 0 desativa a espera. As regras de pausa e proteção dos aparelhos mantêm-se ativas.",
    },
    "pt-BR": {
        "label": "Espera antes de sugerir fechar a janela (min)",
        "help": "Quando uma janela é aberta após uma sugestão de ventilação do HEM, aguarda este número de minutos antes de sugerir que ela seja fechada, mesmo que as condições externas não sejam adequadas. A espera se aplica de forma independente a cada cômodo. 0–60 minutos, padrão 5; 0 desativa a espera. As regras de pausa e proteção dos aparelhos continuam ativas.",
    },
    "pl": {
        "label": "Czas oczekiwania przed sugestią zamknięcia okna (min)",
        "help": "Po otwarciu okna zgodnie z sugestią HEM odczekuje tyle minut, zanim zasugeruje jego zamknięcie, nawet jeśli warunki na zewnątrz są nieodpowiednie. Czas oczekiwania jest liczony niezależnie dla każdego pomieszczenia. 0–60 minut, domyślnie 5; 0 wyłącza opóźnienie. Zasady wstrzymywania pracy i ochrony urządzeń pozostają aktywne.",
    },
    "ru": {
        "label": "Задержка перед советом закрыть окно (мин)",
        "help": "После открытия окна по совету HEM выжидает указанное число минут, прежде чем предложить закрыть его, даже если условия снаружи неподходящие. Задержка отсчитывается независимо для каждой комнаты. 0–60 минут, по умолчанию 5; 0 отключает задержку. Правила приостановки работы и защиты устройств остаются активными.",
    },
    "uk": {
        "label": "Затримка перед порадою зачинити вікно (хв)",
        "help": "Після відчинення вікна за порадою HEM очікує вказану кількість хвилин, перш ніж запропонувати зачинити його, навіть якщо умови надворі несприятливі. Затримка відлічується незалежно для кожної кімнати. 0–60 хвилин, типово 5; 0 вимикає затримку. Правила призупинення роботи та захисту пристроїв залишаються активними.",
    },
    "tr": {
        "label": "Pencereyi kapatmayı önermeden önce bekleme (dk)",
        "help": "HEM’in havalandırma önerisinin ardından bir pencere açıldığında, dış koşullar uygun olmasa bile kapatılmasını önermeden önce bu kadar dakika bekler. Bekleme süresi her oda için ayrı hesaplanır. 0–60 dakika, varsayılan 5; 0 beklemeyi devre dışı bırakır. Cihazları duraklatma ve koruma kuralları etkin kalır.",
    },
    "cs": {
        "label": "Čekání před doporučením zavřít okno (min)",
        "help": "Po otevření okna na základě doporučení HEM vyčká tento počet minut, než doporučí jeho zavření, i když jsou venkovní podmínky nevhodné. Doba čekání se počítá pro každou místnost samostatně. 0–60 minut, výchozí hodnota 5; 0 čekání vypne. Pravidla pro pozastavení provozu a ochranu zařízení zůstávají aktivní.",
    },
    "sk": {
        "label": "Čakanie pred odporúčaním zatvoriť okno (min)",
        "help": "Po otvorení okna na základe odporúčania HEM počká tento počet minút, kým odporučí jeho zatvorenie, aj keď sú vonkajšie podmienky nevhodné. Čas čakania sa počíta pre každú miestnosť samostatne. 0–60 minút, predvolená hodnota 5; 0 čakanie vypne. Pravidlá pozastavenia prevádzky a ochrany zariadení zostávajú aktívne.",
    },
    "hu": {
        "label": "Várakozás az ablak bezárására vonatkozó javaslat előtt (perc)",
        "help": "Ha a HEM szellőztetési javaslata után kinyitnak egy ablakot, ennyi percet vár, mielőtt annak bezárását javasolná, akkor is, ha a kinti körülmények nem megfelelőek. A várakozási időt helyiségenként külön számítja. 0–60 perc, alapérték 5; a 0 kikapcsolja a várakozást. Az eszközök szüneteltetési és védelmi szabályai továbbra is érvényesek.",
    },
    "ro": {
        "label": "Așteptare înainte de a sugera închiderea ferestrei (min)",
        "help": "După deschiderea unei ferestre în urma unei sugestii HEM, așteaptă acest număr de minute înainte de a sugera închiderea ei, chiar dacă condițiile de afară sunt nepotrivite. Timpul de așteptare se aplică independent fiecărei camere. 0–60 de minute, implicit 5; 0 dezactivează așteptarea. Regulile de pauză și protecție ale dispozitivelor rămân active.",
    },
    "bg": {
        "label": "Изчакване преди предложение за затваряне на прозореца (мин)",
        "help": "Когато прозорец бъде отворен след съвет от HEM за проветряване, изчаква толкова минути, преди да предложи затварянето му, дори ако външните условия са неподходящи. Времето за изчакване се отчита независимо за всяка стая. 0–60 минути, по подразбиране 5; 0 изключва изчакването. Правилата за пауза и защита на устройствата остават активни.",
    },
    "hr": {
        "label": "Čekanje prije prijedloga za zatvaranje prozora (min)",
        "help": "Nakon što se prozor otvori na preporuku HEM-a, čeka ovoliko minuta prije nego što predloži zatvaranje, čak i ako vanjski uvjeti nisu prikladni. Vrijeme čekanja računa se zasebno za svaku prostoriju. 0–60 minuta, zadano 5; 0 isključuje čekanje. Pravila pauziranja rada i zaštite uređaja ostaju aktivna.",
    },
    "sr": {
        "label": "Чекање пре предлога за затварање прозора (мин)",
        "help": "Када се прозор отвори по препоруци HEM-а, чека оволико минута пре него што предложи затварање, чак и ако спољни услови нису одговарајући. Време чекања рачуна се засебно за сваку просторију. 0–60 минута, подразумевано 5; 0 искључује чекање. Правила паузирања рада и заштите уређаја остају активна.",
    },
    "sv": {
        "label": "Väntetid innan fönsterstängning föreslås (min)",
        "help": "När ett fönster öppnas efter ett vädringsförslag från HEM väntar HEM så här många minuter innan det föreslår att fönstret stängs, även om förhållandena utomhus är olämpliga. Väntetiden räknas separat för varje rum. 0–60 minuter, standard 5; 0 stänger av väntetiden. Reglerna för att pausa och skydda enheter gäller fortfarande.",
    },
    "nb": {
        "label": "Ventetid før lukking av vinduet foreslås (min)",
        "help": "Når et vindu åpnes etter et lufteforslag fra HEM, venter HEM så mange minutter før det foreslår å lukke vinduet, selv om forholdene ute er uegnede. Ventetiden beregnes separat for hvert rom. 0–60 minutter, standard 5; 0 slår av ventetiden. Reglene for å sette enheter på pause og beskytte dem gjelder fortsatt.",
    },
    "da": {
        "label": "Ventetid før lukning af vinduet foreslås (min)",
        "help": "Når et vindue åbnes efter et udluftningsforslag fra HEM, venter HEM så mange minutter, før det foreslår at lukke vinduet, selv hvis forholdene udenfor er uegnede. Ventetiden beregnes separat for hvert rum. 0–60 minutter, standard 5; 0 slår ventetiden fra. Reglerne for at sætte enheder på pause og beskytte dem gælder fortsat.",
    },
    "fi": {
        "label": "Odotusaika ennen ikkunan sulkemisehdotusta (min)",
        "help": "Kun ikkuna avataan HEMin tuuletusehdotuksen jälkeen, HEM odottaa näin monta minuuttia ennen kuin ehdottaa sen sulkemista, vaikka ulko-olosuhteet olisivat epäsuotuisat. Odotusaika lasketaan erikseen kullekin huoneelle. 0–60 minuuttia, oletus 5; 0 poistaa odotusajan käytöstä. Laitteiden tauko- ja suojaussäännöt pysyvät voimassa.",
    },
    "id": {
        "label": "Jeda sebelum menyarankan penutupan jendela (menit)",
        "help": "Setelah jendela dibuka mengikuti saran HEM, tunggu selama jumlah menit ini sebelum menyarankan agar jendela ditutup, meskipun kondisi di luar tidak sesuai. Jeda dihitung secara terpisah untuk setiap ruangan. 0–60 menit, bawaan 5; 0 menonaktifkan jeda. Aturan jeda operasi dan perlindungan perangkat tetap aktif.",
    },
    "vi": {
        "label": "Thời gian chờ trước khi đề nghị đóng cửa sổ (phút)",
        "help": "Sau khi cửa sổ được mở theo đề nghị của HEM, chờ số phút này trước khi đề nghị đóng lại, ngay cả khi điều kiện bên ngoài không phù hợp. Thời gian chờ được tính riêng cho từng phòng. 0–60 phút, mặc định 5; 0 tắt thời gian chờ. Các quy tắc tạm dừng và bảo vệ thiết bị vẫn có hiệu lực.",
    },
    "th": {
        "label": "ระยะเวลารอก่อนแนะนำให้ปิดหน้าต่าง (นาที)",
        "help": "เมื่อเปิดหน้าต่างตามคำแนะนำของ HEM ให้รอตามจำนวนนาทีนี้ก่อนแนะนำให้ปิด แม้ว่าสภาพภายนอกจะไม่เหมาะสมก็ตาม ระยะเวลารอจะนับแยกกันสำหรับแต่ละห้อง ตั้งได้ 0–60 นาที ค่าเริ่มต้น 5; ค่า 0 ปิดการรอ กฎการพักการทำงานและการป้องกันอุปกรณ์ยังคงมีผลอยู่",
    },
    "hi": {
        "label": "खिड़की बंद करने का सुझाव देने से पहले प्रतीक्षा (मिनट)",
        "help": "HEM के सुझाव पर खिड़की खोलने के बाद, उसे बंद करने का सुझाव देने से पहले इतने मिनट प्रतीक्षा करें, भले ही बाहर की स्थितियाँ उपयुक्त न हों। प्रतीक्षा समय हर कमरे के लिए अलग गिना जाता है। 0–60 मिनट, डिफ़ॉल्ट 5; 0 प्रतीक्षा बंद करता है। उपकरणों को रोकने और उनकी सुरक्षा के नियम सक्रिय रहते हैं।",
    },
    "zh-Hans": {
        "label": "建议关窗前的等待时间（分钟）",
        "help": "按照 HEM 的开窗建议打开窗户后，等待设定的分钟数，再建议关窗，即使室外条件不适宜也会等待。各房间的等待时间独立计算。范围 0–60 分钟，默认 5；设为 0 可关闭等待。设备暂停和保护规则仍然有效。",
    },
    "zh-Hant": {
        "label": "建議關窗前的等待時間（分鐘）",
        "help": "依照 HEM 的開窗建議打開窗戶後，等待設定的分鐘數，再建議關窗，即使室外條件不適宜也會等待。各房間的等待時間獨立計算。範圍 0–60 分鐘，預設 5；設為 0 可關閉等待。裝置暫停和保護規則仍然有效。",
    },
    "ja": {
        "label": "窓を閉める提案までの待ち時間（分）",
        "help": "HEMの提案に従って窓が開けられた後、ここで設定した分数が経過してから窓を閉めるよう提案します。屋外の条件が適していない場合も同様です。待ち時間は部屋ごとに計測します。0–60分、初期値は5。0にすると待ち時間が無効になります。機器の一時停止と保護のルールは引き続き適用されます。",
    },
    "ko": {
        "label": "창문 닫기 권고 전 대기 시간(분)",
        "help": "HEM의 창문 열기 권고에 따라 창문이 열리면, 설정한 시간만큼 기다린 후 닫기를 권고합니다. 실외 조건이 적합하지 않아도 대기하며, 대기 시간은 방마다 따로 계산합니다. 0–60분, 기본값 5; 0으로 설정하면 대기하지 않습니다. 기기 일시 중지 및 보호 규칙은 계속 적용됩니다.",
    },
    "ar": {
        "label": "مدة الانتظار قبل اقتراح إغلاق النافذة (دقيقة)",
        "help": "بعد فتح نافذة استجابةً لاقتراح HEM بالتهوية، ينتظر هذا العدد من الدقائق قبل اقتراح إغلاقها، حتى لو كانت الظروف الخارجية غير مناسبة. تُحسب مدة الانتظار لكل غرفة على حدة. من 0–60 دقيقة، والقيمة الافتراضية 5؛ تعطل القيمة 0 الانتظار. تظل قواعد الإيقاف المؤقت وحماية الأجهزة سارية.",
    },
    "he": {
        "label": "המתנה לפני הצעה לסגור חלון (דקות)",
        "help": "לאחר פתיחת חלון בעקבות המלצת HEM לאוורור, יש להמתין מספר דקות זה לפני הצעה לסגור אותו, גם כשהתנאים בחוץ אינם מתאימים. זמן ההמתנה מחושב בנפרד לכל חדר. 0–60 דקות, ברירת המחדל 5; הערך 0 מבטל את ההמתנה. כללי ההשהיה וההגנה של המכשירים נשארים בתוקף.",
    },
    "fa": {
        "label": "زمان انتظار پیش از پیشنهاد بستن پنجره (دقیقه)",
        "help": "پس از باز شدن پنجره طبق پیشنهاد تهویهٔ HEM، این تعداد دقیقه صبر می‌کند و سپس بستن پنجره را پیشنهاد می‌دهد، حتی اگر شرایط بیرون مناسب نباشد. زمان انتظار برای هر اتاق جداگانه محاسبه می‌شود. 0–60 دقیقه، پیش‌فرض 5؛ مقدار 0 انتظار را غیرفعال می‌کند. قواعد توقف موقت و حفاظت از دستگاه‌ها همچنان فعال می‌مانند.",
    },
    "bn": {
        "label": "জানালা বন্ধ করার পরামর্শের আগে অপেক্ষা (মিনিট)",
        "help": "HEM-এর পরামর্শে জানালা খোলার পর, সেটি বন্ধ করার পরামর্শ দেওয়ার আগে এই সংখ্যক মিনিট অপেক্ষা করে, বাইরের পরিবেশ অনুকূল না হলেও। প্রতিটি ঘরের জন্য অপেক্ষার সময় আলাদাভাবে গণনা করা হয়। 0–60 মিনিট, ডিফল্ট 5; 0 দিলে অপেক্ষা বন্ধ হয়। যন্ত্রের কাজ সাময়িক বন্ধ রাখা ও সুরক্ষার নিয়ম চালু থাকে।",
    },
    "ur": {
        "label": "کھڑکی بند کرنے کا مشورہ دینے سے پہلے انتظار (منٹ)",
        "help": "HEM کے ہوا کی آمدورفت کے مشورے پر کھڑکی کھلنے کے بعد، اسے بند کرنے کا مشورہ دینے سے پہلے اتنے منٹ انتظار کرتا ہے، چاہے باہر کے حالات موزوں نہ ہوں۔ ہر کمرے کا انتظار الگ شمار کیا جاتا ہے۔ 0–60 منٹ، طے شدہ قدر 5؛ قدر 0 انتظار بند کرتی ہے۔ آلات کو عارضی طور پر روکنے اور ان کی حفاظت کے قواعد فعال رہتے ہیں۔",
    },
    "ta": {
        "label": "சாளரத்தை மூடப் பரிந்துரைக்கும் முன் காத்திருக்கும் நேரம் (நிமிடம்)",
        "help": "HEM பரிந்துரையின்படி சாளரம் திறக்கப்பட்ட பிறகு, அதை மூடப் பரிந்துரைக்கும் முன் இத்தனை நிமிடங்கள் காத்திருக்கும்; வெளிப்புறச் சூழல் ஏற்றதாக இல்லாவிட்டாலும் காத்திருக்கும். ஒவ்வொரு அறைக்கும் காத்திருப்பு நேரம் தனித்தனியாகக் கணக்கிடப்படும். 0–60 நிமிடங்கள், இயல்புநிலை 5; 0 என அமைத்தால் காத்திருப்பு முடக்கப்படும். சாதனங்களை இடைநிறுத்தும் மற்றும் பாதுகாக்கும் விதிகள் தொடர்ந்து செயல்படும்.",
    },
}
