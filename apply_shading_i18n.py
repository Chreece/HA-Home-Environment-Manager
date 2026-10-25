"""Translated native room shade cooling controls in all 38 supported locales."""
from __future__ import annotations

import json
from pathlib import Path
from apply_room_setup_i18n import SHADE_NAMES

# Per-locale: room switch / indoor threshold / minimum sun elevation.
LABELS = {
 "en": ("Automatic solar shade cooling", "Close shades above room temperature", "Minimum sun elevation for shading"),
 "el": ("Αυτόματο κλείσιμο σκιάστρων για ψύξη", "Κλείσιμο σκιάστρων πάνω από θερμοκρασία χώρου", "Ελάχιστο ύψος ήλιου για σκίαση"),
 "de": ("Automatische Fensterbeschattung zur Kühlung", "Rollos schließen ab Raumtemperatur", "Minimale Sonnenhöhe für Beschattung"),
 "fr": ("Fermeture solaire automatique des stores", "Fermer les stores au-dessus de cette température", "Élévation minimale du soleil"),
 "es": ("Cierre automático de persianas para enfriar", "Cerrar persianas por encima de la temperatura", "Elevación solar mínima"),
 "it": ("Chiusura automatica tende contro il caldo", "Chiudi tende sopra questa temperatura", "Altezza minima del sole"),
 "nl": ("Automatisch zonwering sluiten tegen hitte", "Zonwering sluiten boven kamertemperatuur", "Minimale zonnestand voor zonwering"),
 "pt": ("Fecho automático de estores para arrefecer", "Fechar estores acima desta temperatura", "Elevação solar mínima"),
 "pt-BR": ("Fechamento automático das persianas para resfriar", "Fechar persianas acima da temperatura", "Elevação solar mínima"),
 "pl": ("Automatyczne zamykanie rolet dla chłodzenia", "Zamknij rolety powyżej temperatury", "Minimalna wysokość słońca"),
 "cs": ("Automatické zavírání rolet proti přehřívání", "Zavřít rolety nad pokojovou teplotou", "Minimální výška slunce"),
 "sk": ("Automatické zatváranie roliet proti prehriatiu", "Zatvoriť rolety nad izbovou teplotou", "Minimálna výška slnka"),
 "sv": ("Automatisk stängning av solskydd vid värme", "Stäng solskydd över rumstemperaturen", "Minsta solhöjd"),
 "da": ("Automatisk lukning af solafskærmning", "Luk persienner over rumtemperaturen", "Mindste solhøjde"),
 "nb": ("Automatisk lukking av solskjerming", "Lukk solskjerming over romtemperatur", "Minste solhøyde"),
 "fi": ("Automaattinen aurinkosuojaus viilennykseen", "Sulje kaihtimet yli huonelämpötilan", "Auringon vähimmäiskorkeus"),
 "hu": ("Automatikus árnyékolás a hűtéshez", "Redőnyök zárása e hőmérséklet felett", "Minimális napmagasság"),
 "ro": ("Închidere automată a jaluzelelor pentru răcire", "Închide jaluzelele peste temperatura camerei", "Înălțimea minimă a soarelui"),
 "bg": ("Автоматично затваряне на щори за охлаждане", "Затваряне над стайна температура", "Минимална височина на слънцето"),
 "hr": ("Automatsko zatvaranje roleta za hlađenje", "Zatvori rolete iznad sobne temperature", "Minimalna visina sunca"),
 "sr": ("Аутоматско затварање ролетни ради хлађења", "Затвори ролетне изнад собне температуре", "Минимална висина сунца"),
 "ru": ("Автоматическое закрытие жалюзи для охлаждения", "Закрывать жалюзи выше температуры комнаты", "Минимальная высота солнца"),
 "uk": ("Автоматичне закриття ролет для охолодження", "Закривати ролети вище температури кімнати", "Мінімальна висота сонця"),
 "tr": ("Serinletmek için otomatik panjur kapatma", "Oda sıcaklığı eşiğinde panjurları kapat", "Asgari güneş yüksekliği"),
 "ar": ("الإغلاق التلقائي للستائر لتبريد الغرفة", "إغلاق الستائر فوق درجة حرارة الغرفة", "الارتفاع الأدنى للشمس"),
 "he": ("סגירת תריסים אוטומטית לקירור", "סגירת תריסים מעל טמפרטורת החדר", "גובה שמש מינימלי"),
 "fa": ("بستن خودکار پرده برای خنک‌سازی", "بستن پرده بالای دمای اتاق", "کمینه ارتفاع خورشید"),
 "hi": ("कमरा ठंडा रखने हेतु ब्लाइंड स्वतः बंद करें", "कमरे के तापमान से ऊपर ब्लाइंड बंद करें", "सूर्य की न्यूनतम ऊँचाई"),
 "bn": ("ঘর ঠান্ডা রাখতে ব্লাইন্ড স্বয়ংক্রিয় বন্ধ", "ঘরের তাপমাত্রার উপরে ব্লাইন্ড বন্ধ", "সূর্যের ন্যূনতম উচ্চতা"),
 "ta": ("அறையைக் குளிர்விக்க திரைகளைத் தானாக மூடு", "அறை வெப்பநிலைக்கு மேல் திரைகளை மூடு", "சூரியனின் குறைந்தபட்ச உயரம்"),
 "ur": ("کمرہ ٹھنڈا رکھنے کے لیے پردے خودکار بند", "کمرے کے درجہ حرارت پر پردے بند کریں", "سورج کی کم از کم بلندی"),
 "id": ("Tutup tirai otomatis untuk mendinginkan", "Tutup tirai di atas suhu ruangan", "Elevasi matahari minimum"),
 "vi": ("Tự động đóng rèm để làm mát", "Đóng rèm khi nhiệt độ phòng vượt ngưỡng", "Độ cao tối thiểu của mặt trời"),
 "ko": ("실내 냉방을 위한 블라인드 자동 닫기", "실내 온도가 이 값을 넘으면 블라인드 닫기", "최소 태양 고도"),
 "ja": ("室内を涼しく保つため自動でブラインドを閉じる", "この室温を超えたらブラインドを閉じる", "日射を遮る最低太陽高度"),
 "zh-Hans": ("自动关闭窗帘帮助降温", "室温超过此值时关闭窗帘", "最小太阳高度角"),
 "zh-Hant": ("自動關閉窗簾以協助降溫", "室溫高於此值時關閉窗簾", "最小太陽高度角"),
 "th": ("ปิดม่านอัตโนมัติเพื่อให้ห้องเย็น", "ปิดม่านเมื่ออุณหภูมิห้องสูงกว่าค่า", "มุมเงยดวงอาทิตย์ขั้นต่ำ"),
}
ANNOUNCE_NAMES = {
 "en":"Announce before moving window shades",
 "el":"Ανακοίνωση πριν από το άνοιγμα ή κλείσιμο σκιάστρων",
 "de":"Vor dem Öffnen oder Schließen der Rollos ankündigen",
 "fr":"Annoncer avant d’ouvrir ou fermer les stores",
 "es":"Anunciar antes de abrir o cerrar persianas",
 "it":"Annuncia prima di aprire o chiudere le tende",
 "nl":"Aankondigen voordat zonwering opent of sluit",
 "pt":"Anunciar antes de abrir ou fechar os estores",
 "pt-BR":"Anunciar antes de abrir ou fechar as persianas",
 "pl":"Zapowiadaj przed otwarciem lub zamknięciem rolet",
 "cs":"Oznámit před otevřením nebo zavřením rolet",
 "sk":"Oznámiť pred otvorením alebo zatvorením roliet",
 "sv":"Meddela innan solskydd öppnas eller stängs",
 "da":"Giv besked før solafskærmning åbnes eller lukkes",
 "nb":"Varsle før solskjerming åpnes eller lukkes",
 "fi":"Ilmoita ennen kaihtimien avaamista tai sulkemista",
 "hu":"Értesítés a redőnyök nyitása vagy zárása előtt",
 "ro":"Anunță înainte de deschiderea sau închiderea jaluzelelor",
 "bg":"Извести преди отваряне или затваряне на щорите",
 "hr":"Najavi prije otvaranja ili zatvaranja roleta",
 "sr":"Најави пре отварања или затварања ролетни",
 "ru":"Сообщать перед открытием или закрытием жалюзи",
 "uk":"Сповіщати перед відкриттям або закриттям ролет",
 "tr":"Panjurlar açılmadan veya kapanmadan önce duyur",
 "ar":"الإعلان قبل فتح أو إغلاق ستائر النوافذ",
 "he":"להודיע לפני פתיחה או סגירה של התריסים",
 "fa":"اعلام پیش از باز یا بسته شدن پرده‌ها",
 "hi":"ब्लाइंड खोलने या बंद करने से पहले घोषणा करें",
 "bn":"ব্লাইন্ড খোলা বা বন্ধের আগে ঘোষণা করুন",
 "ta":"திரைகளைத் திறப்பதற்கு அல்லது மூடுவதற்கு முன் அறிவி",
 "ur":"پردے کھولنے یا بند کرنے سے پہلے اطلاع دیں",
 "id":"Umumkan sebelum tirai dibuka atau ditutup",
 "vi":"Thông báo trước khi mở hoặc đóng rèm cửa",
 "ko":"블라인드를 열거나 닫기 전에 알림",
 "ja":"ブラインドを開閉する前に通知",
 "zh-Hans":"开合窗帘前发送通知",
 "zh-Hant":"開合窗簾前發送通知",
 "th":"แจ้งเตือนก่อนเปิดหรือปิดม่าน",
}


DETAIL = {
 "en": "Only selected room window shades can CLOSE when a fresh room thermometer is above the threshold, sun.sun is above the configured angle, and every selected window contact is confirmed closed. Never automatically opens. Disabled by default; repeated close attempts are held for two hours.",
 "el": "Κλείνει μόνο τα επιλεγμένα σκίαστρα του χώρου όταν η πραγματική θερμοκρασία ξεπερνά το όριο, ο ήλιος είναι αρκετά ψηλά και όλες οι επαφές παραθύρων είναι κλειστές. Δεν ανοίγει αυτόματα. Αρχικά ανενεργό· αποφεύγει νέες εντολές για δύο ώρες.",
 "de": "Schließt nur ausgewählte Raumrollos bei bestätigter hoher Raumtemperatur, ausreichender Sonnenhöhe und geschlossenen Fensterkontakten. Öffnet nie automatisch. Standardmäßig aus; verhindert wiederholtes Schließen für zwei Stunden.",
}


WINDOW_CONTACT_NAMES = {
 "en": "Associated window contact",
 "el": "Συνδεδεμένος αισθητήρας παραθύρου",
 "de": "Zugeordneter Fensterkontakt",
 "fr": "Contact de fenêtre associé",
 "es": "Sensor de ventana asociado",
 "it": "Contatto finestra associato",
 "nl": "Gekoppeld raamcontact",
 "pt": "Contacto da janela associado",
 "pt-BR": "Sensor de janela associado",
 "pl": "Powiązany czujnik okna",
 "cs": "Přiřazený okenní kontakt",
 "sk": "Priradený okenný kontakt",
 "sv": "Kopplad fönsterkontakt",
 "da": "Tilknyttet vindueskontakt",
 "nb": "Tilknyttet vinduskontakt",
 "fi": "Liitetty ikkunakosketin",
 "hu": "Hozzárendelt ablakérzékelő",
 "ro": "Contact de fereastră asociat",
 "bg": "Свързан сензор за прозорец",
 "hr": "Povezani senzor prozora",
 "sr": "Повезани сензор прозора",
 "ru": "Связанный датчик окна",
 "uk": "Пов’язаний датчик вікна",
 "tr": "İlişkili pencere sensörü",
 "ar": "مستشعر النافذة المرتبط",
 "he": "חיישן חלון משויך",
 "fa": "حسگر پنجره مرتبط",
 "hi": "संबंधित खिड़की सेंसर",
 "bn": "সংযুক্ত জানালার সেন্সর",
 "ta": "தொடர்புடைய சன்னல் உணரி",
 "ur": "متعلقہ کھڑکی کا سینسر",
 "id": "Sensor jendela terkait",
 "vi": "Cảm biến cửa sổ được liên kết",
 "ko": "연결된 창문 센서",
 "ja": "対応する窓の開閉センサー",
 "zh-Hans": "关联的窗户传感器",
 "zh-Hant": "關聯的窗戶感測器",
 "th": "เซ็นเซอร์หน้าต่างที่เชื่อมโยง"
}

def apply_shading_i18n(root: Path) -> None:
    files = [root/"strings.json", *sorted((root/"translations").glob("*.json"))]
    if (len(files) != 39 or set(LABELS) != set(SHADE_NAMES)
            or set(ANNOUNCE_NAMES) != set(SHADE_NAMES)
            or set(WINDOW_CONTACT_NAMES) != set(SHADE_NAMES)):
        raise ValueError("All 38 Home Assistant languages require shade controls")
    for path in files:
        lang = "en" if path.name == "strings.json" else path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        name, temperature, solar = LABELS[lang]
        entities = data.setdefault("entity", {})
        entities.setdefault("switch", {})["area_shading_enabled"] = {
            "name": name,
        }
        entities["switch"]["home_shade_announce_before_movement"] = {
            "name": ANNOUNCE_NAMES[lang],
        }
        nums = entities.setdefault("number", {})
        nums["area_shading_close_above_c"] = {"name": temperature + " (°C)"}
        nums["area_shading_min_sun_elevation"] = {"name": solar + " (°)"}
        # Per-cover controller entities live on each cover's own child device.
        entities["switch"]["shade_auto_control"] = {"name": name}
        entities["switch"]["shade_announce"] = {"name": ANNOUNCE_NAMES[lang]}
        nums["shade_close_above_c"] = {"name": temperature + " (°C)"}
        entities.setdefault("select", {})["shade_window_entity"] = {
            "name": WINDOW_CONTACT_NAMES[lang],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
