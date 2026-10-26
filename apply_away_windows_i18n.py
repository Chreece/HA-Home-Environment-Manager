"""Complete 38-language Home away-window alert controls and helpful setup fields.

Run only after the existing room-setup and PID translation passes so a catalog
regeneration retains these new settings and all older localized labels.
"""
from __future__ import annotations

import json
from pathlib import Path

# Locale: alert, selected people, channels, phone, watch, tablet, other,
# written notification, companion speech. All selector values remain stable.
TEXT = {
 "en": ("Alert when windows remain open after everyone leaves", "People to notify after leaving", "Delivery channels for open-window alerts", "Phone", "Watch", "Tablet", "Other device", "Notification", "TTS speech"),
 "el": ("Ειδοποίηση για ανοιχτά παράθυρα όταν φύγουν όλοι", "Άτομα που θα ειδοποιούνται", "Τρόποι παράδοσης ειδοποίησης", "Κινητό", "Ρολόι", "Tablet", "Άλλη συσκευή", "Γραπτή ειδοποίηση", "Ομιλία TTS"),
 "de": ("Bei offenen Fenstern nach Verlassen des Hauses warnen", "Zu benachrichtigende Personen", "Zustellwege für offene Fenster", "Handy", "Uhr", "Tablet", "Anderes Gerät", "Benachrichtigung", "Sprachausgabe TTS"),
 "fr": ("Alerter si des fenêtres restent ouvertes après le départ", "Personnes à prévenir", "Canaux d'alerte des fenêtres", "Téléphone", "Montre", "Tablette", "Autre appareil", "Notification", "Voix TTS"),
 "es": ("Avisar de ventanas abiertas cuando todos salgan", "Personas destinatarias", "Canales del aviso de ventanas", "Teléfono", "Reloj", "Tableta", "Otro dispositivo", "Notificación", "Voz TTS"),
 "it": ("Avvisa se le finestre restano aperte dopo l'uscita", "Persone da avvisare", "Canali di avviso finestre", "Telefono", "Orologio", "Tablet", "Altro dispositivo", "Notifica", "Voce TTS"),
 "nl": ("Waarschuw voor open ramen wanneer iedereen weg is", "Personen voor waarschuwingen", "Meldingskanalen voor open ramen", "Telefoon", "Horloge", "Tablet", "Ander apparaat", "Melding", "TTS-spraak"),
 "pt": ("Avisar sobre janelas abertas depois de todos saírem", "Pessoas a avisar", "Canais de aviso de janelas abertas", "Telemóvel", "Relógio", "Tablet", "Outro dispositivo", "Notificação", "Voz TTS"),
 "pt-BR": ("Avisar sobre janelas abertas depois que todos saírem", "Pessoas a avisar", "Canais de aviso de janelas abertas", "Celular", "Relógio", "Tablet", "Outro dispositivo", "Notificação", "Voz TTS"),
 "pl": ("Ostrzegaj o otwartych oknach po wyjściu wszystkich", "Osoby do powiadomienia", "Kanały powiadomień o oknach", "Telefon", "Zegarek", "Tablet", "Inne urządzenie", "Powiadomienie", "Mowa TTS"),
 "cs": ("Upozornit na otevřená okna po odchodu všech", "Příjemci upozornění", "Kanály upozornění na okna", "Telefon", "Hodinky", "Tablet", "Jiné zařízení", "Oznámení", "Hlas TTS"),
 "sk": ("Upozorniť na otvorené okná po odchode všetkých", "Osoby na upozornenie", "Kanály upozornení na okná", "Telefón", "Hodinky", "Tablet", "Iné zariadenie", "Oznámenie", "Hlas TTS"),
 "sv": ("Varna för öppna fönster när alla har gått", "Personer som ska varnas", "Kanaler för fönstervarningar", "Telefon", "Klocka", "Surfplatta", "Annan enhet", "Avisering", "TTS-tal"),
 "da": ("Advar om åbne vinduer når alle er gået", "Personer der skal advares", "Kanaler til vinduesadvarsler", "Telefon", "Ur", "Tablet", "Anden enhed", "Notifikation", "TTS-tale"),
 "nb": ("Varsle om åpne vinduer når alle har gått", "Personer som skal varsles", "Kanaler for vindusvarsler", "Telefon", "Klokke", "Nettbrett", "Annen enhet", "Varsel", "TTS-tale"),
 "fi": ("Varoita avoimista ikkunoista kaikkien lähdettyä", "Ilmoituksen saavat henkilöt", "Ikkunavaroituksen kanavat", "Puhelin", "Kello", "Tabletti", "Muu laite", "Ilmoitus", "TTS-puhe"),
 "hu": ("Figyelmeztessen a nyitott ablakokra távozáskor", "Értesítendő személyek", "Ablakriasztás csatornái", "Telefon", "Óra", "Táblagép", "Más eszköz", "Értesítés", "TTS beszéd"),
 "ro": ("Avertizează pentru ferestre deschise după plecare", "Persoane de anunțat", "Canale pentru alerta ferestrelor", "Telefon", "Ceas", "Tabletă", "Alt dispozitiv", "Notificare", "Voce TTS"),
 "bg": ("Известявай за отворени прозорци след напускане", "Хора за известяване", "Канали за известяване за прозорци", "Телефон", "Часовник", "Таблет", "Друго устройство", "Известие", "Глас TTS"),
 "hr": ("Upozori na otvorene prozore kada svi odu", "Osobe za obavijest", "Kanali obavijesti o prozorima", "Telefon", "Sat", "Tablet", "Drugi uređaj", "Obavijest", "TTS govor"),
 "sr": ("Обавести о отвореним прозорима кад сви оду", "Особе за обавештавање", "Канали за обавештења о прозорима", "Телефон", "Сат", "Таблет", "Други уређај", "Обавештење", "TTS говор"),
 "ru": ("Предупреждать об открытых окнах после ухода всех", "Получатели уведомления", "Каналы уведомления об окнах", "Телефон", "Часы", "Планшет", "Другое устройство", "Уведомление", "Голос TTS"),
 "uk": ("Сповіщати про відкриті вікна після виходу всіх", "Особи для сповіщення", "Канали сповіщень про вікна", "Телефон", "Годинник", "Планшет", "Інший пристрій", "Сповіщення", "Голос TTS"),
 "tr": ("Herkes çıktıktan sonra açık pencereleri bildir", "Bildirim gönderilecek kişiler", "Pencere bildirim kanalları", "Telefon", "Saat", "Tablet", "Diğer cihaz", "Bildirim", "TTS ses"),
 "ar": ("تنبيه عند بقاء النوافذ مفتوحة بعد مغادرة الجميع", "الأشخاص المطلوب تنبيههم", "قنوات تنبيه النوافذ المفتوحة", "الهاتف", "الساعة", "الجهاز اللوحي", "جهاز آخر", "إشعار", "صوت TTS"),
 "he": ("התרעה על חלונות פתוחים לאחר שכולם יצאו", "אנשים לקבלת התראה", "ערוצי התרעה על חלונות", "טלפון", "שעון", "טאבלט", "מכשיר אחר", "התראה", "דיבור TTS"),
 "fa": ("هشدار پنجره باز پس از خروج همه از خانه", "افراد دریافت کننده هشدار", "کانال های هشدار پنجره", "تلفن", "ساعت", "تبلت", "دستگاه دیگر", "اعلان", "گفتار TTS"),
 "hi": ("सबके जाने पर खुली खिड़कियों की सूचना दें", "सूचना पाने वाले व्यक्ति", "खिड़की सूचना के माध्यम", "फ़ोन", "घड़ी", "टैबलेट", "अन्य उपकरण", "सूचना", "TTS आवाज़"),
 "bn": ("সবাই বের হলে খোলা জানালার সতর্কতা দিন", "বিজ্ঞপ্তি পাবেন যাঁরা", "জানালার সতর্কতার মাধ্যম", "ফোন", "ঘড়ি", "ট্যাবলেট", "অন্য ডিভাইস", "বিজ্ঞপ্তি", "TTS কথা"),
 "ta": ("அனைவரும் வெளியேறியபின் திறந்த சாளர எச்சரிக்கை", "அறிவிப்பு பெறும் நபர்கள்", "சாளர எச்சரிக்கை வழிகள்", "தொலைபேசி", "கடிகாரம்", "டேப்லெட்", "மற்ற சாதனம்", "அறிவிப்பு", "TTS பேச்சு"),
 "ur": ("سب کے جانے پر کھلی کھڑکیوں کی اطلاع", "اطلاع پانے والے افراد", "کھڑکی اطلاع کے ذرائع", "فون", "گھڑی", "ٹیبلٹ", "دوسرا آلہ", "اطلاع", "TTS آواز"),
 "id": ("Beri tahu jendela terbuka setelah semua pergi", "Orang yang diberi tahu", "Saluran peringatan jendela", "Ponsel", "Jam tangan", "Tablet", "Perangkat lain", "Notifikasi", "Suara TTS"),
 "vi": ("Cảnh báo cửa sổ mở khi mọi người đã rời nhà", "Người nhận thông báo", "Kênh cảnh báo cửa sổ", "Điện thoại", "Đồng hồ", "Máy tính bảng", "Thiết bị khác", "Thông báo", "Giọng TTS"),
 "ko": ("모두 외출한 뒤 열린 창문 알림", "알림을 받을 사람", "창문 알림 전송 채널", "휴대폰", "시계", "태블릿", "기타 기기", "알림", "TTS 음성"),
 "ja": ("全員の外出後に開いた窓を通知", "通知する人物", "窓の通知先と方法", "スマートフォン", "腕時計", "タブレット", "その他の端末", "通知", "TTS 音声"),
 "zh-Hans": ("所有人离家后提醒未关窗户", "接收提醒的人员", "窗户提醒发送渠道", "手机", "手表", "平板", "其他设备", "通知", "TTS 语音"),
 "zh-Hant": ("所有人離家後提醒未關窗戶", "接收提醒的人員", "窗戶提醒發送管道", "手機", "手錶", "平板", "其他裝置", "通知", "TTS 語音"),
 "th": ("แจ้งเตือนหน้าต่างเปิดหลังทุกคนออกจากบ้าน", "บุคคลที่จะรับการแจ้งเตือน", "ช่องทางแจ้งเตือนหน้าต่าง", "โทรศัพท์", "นาฬิกา", "แท็บเล็ต", "อุปกรณ์อื่น", "การแจ้งเตือน", "เสียง TTS"),
}

HELP = {
    "en": (
        "Off by default. After every known resident is confirmed away for 60 seconds, report still-open selected physical window contacts. No announcement at startup while already away. Report once per departure and again only for newly opened windows.",
        "Select exactly which Home Assistant person.* identities receive this message. Each person must have the selected phone/watch/tablet destination configured in Announcement Hub. Missing destinations are never replaced by room-wide broadcasts.",
        "Choose multiple phone, watch, tablet or other device delivery modes. Notification is written push; TTS uses Companion App speech only. Each selected channel routes to its exact person's assigned output, even while away, not to room speakers.",
        "Select at least one person and one delivery channel for the open-window departure alert.",
    ),
    "el": (
        "Αρχικά ανενεργό. Μόνο όταν επιβεβαιωθεί ότι όλοι απουσιάζουν επί 60 δευτερόλεπτα, ειδοποιεί για πραγματικές ανοιχτές επαφές παραθύρων. Δεν ειδοποιεί ξανά μετά από επανεκκίνηση ενώ λείπουν όλοι. Νέα παράθυρα μπορούν να προκαλέσουν νέα ειδοποίηση.",
        "Επίλεξε συγκεκριμένα άτομα person.*. Κάθε άτομο πρέπει να έχει αντιστοιχισμένο κινητό, ρολόι ή άλλη συσκευή στο Announcement Hub. Δεν γίνεται μετάδοση σε δωμάτια ή άσχετους παραλήπτες.",
        "Πολλαπλή επιλογή γραπτής ειδοποίησης κινητού/ρολογιού ή ομιλίας Companion TTS. Κάθε συνδυασμός αποστέλλεται μόνο στη συσκευή του επιλεγμένου ατόμου, ακόμη και όταν απουσιάζει.",
        "Επίλεξε τουλάχιστον ένα άτομο και έναν τρόπο παράδοσης ειδοποίησης για τα ανοιχτά παράθυρα.",
    ),
    "de": (
        "Standardmäßig aus. Erst wenn alle bekannten Bewohner 60 Sekunden nachweislich abwesend sind, werden echte noch offene Fensterkontakte gemeldet. Kein erneutes Senden beim Neustart während Abwesenheit; neue Fenster können erneut gemeldet werden.",
        "Wähle konkrete person.*-Einträge in Home Assistant. Für jede Person muss das passende Handy/Uhr-Ziel in Announcement Hub zugeordnet sein. Eine fehlende Zuordnung führt niemals zu einem Raum-Rundruf.",
        "Mehrfachauswahl von Handy/Uhr/Tablet-Push oder Companion-App-Sprachausgabe. Jeder gewählte Kanal wird nur an die zugeordneten Geräte dieser Personen gesendet, nicht an Lautsprecher zu Hause.",
        "Mindestens eine Person und einen Zustellweg für die Fensterwarnung auswählen.",
    ),
    "fr": (
        "Désactivé par défaut. Après 60 secondes d'absence confirmée de tous les occupants, signale les contacts de fenêtres encore ouverts. Pas d'alerte lors d'un redémarrage en absence; les nouvelles ouvertures peuvent être signalées.",
        "Choisissez les personnes person.* concernées, dont les appareils doivent être configurés dans Announcement Hub. Aucun envoi général dans les pièces en cas de destination manquante.",
        "Sélection multiple des notifications ou de la voix TTS sur téléphone, montre et tablette. Chaque canal est limité aux appareils attribués aux personnes choisies.",
        "Choisissez au moins une personne et un canal de livraison pour cet avertissement.",
    ),
    "es": (
        "Desactivado inicialmente. Tras confirmar que todos están fuera durante 60 segundos, avisa de los contactos de ventanas aún abiertos. No reenvía al reiniciar en ausencia y solo repite si se abren otras ventanas.",
        "Selecciona personas person.* explícitas con sus dispositivos configurados en Announcement Hub. Nunca se envía un aviso general a habitaciones por destinos ausentes.",
        "Permite varios canales: avisos escritos y voz Companion TTS en teléfono, reloj o tableta. Solo se usan los dispositivos asignados a cada persona elegida.",
        "Selecciona al menos una persona y un canal para recibir el aviso de ventanas.",
    ),
}
# Other language labels and choices are native; the helper falls back to a
# concrete, nonempty multilingual explanation rather than a blank tool tip.
def help_text(lang: str) -> tuple[str, str, str, str]:
    if lang in HELP:
        return HELP[lang]
    enabled, people, channels, phone, watch, tablet, other, notify, speech = TEXT[lang]
    return (
        f"{enabled}. {people} (person.*). 60 s. Announcement Hub. "
        f"{phone}, {watch}, {tablet}.",
        f"{people} (person.*) - Announcement Hub: {phone}, {watch}, {tablet}, {other}. "
        "Only explicitly assigned personal endpoints.",
        f"{channels}: {phone} {notify} / {speech}, {watch} {notify} / {speech}, "
        f"{tablet} {notify} / {speech}. Person-specific, not room speakers.",
        f"{people}; {channels}. Announcement Hub (person.*).",
    )


def apply_away_windows_i18n(root: Path) -> None:
    locale_dir = root / "translations"
    files = [root / "strings.json", *sorted(locale_dir.glob("*.json"))]
    if set(TEXT) != {f.stem for f in files if f.name != "strings.json"}:
        raise ValueError("All 38 current Home Assistant locales must have away-window labels")
    for path in files:
        lang = "en" if path.name == "strings.json" else path.stem
        doc = json.loads(path.read_text(encoding="utf-8"))
        title, people, channels, phone, watch, tablet, other, notice, voice = TEXT[lang]
        desc_enable, desc_people, desc_channels, error = help_text(lang)
        for scope in ("config", "options"):
            step = doc[scope]["step"]["setup_general"]
            step.setdefault("data", {}).update({
                "away_open_window_alert": title,
                "away_windows_target_people": people,
                "away_windows_delivery_channels": channels,
            })
            step.setdefault("data_description", {}).update({
                "away_open_window_alert": desc_enable,
                "away_windows_target_people": desc_people,
                "away_windows_delivery_channels": desc_channels,
            })
            doc[scope].setdefault("error", {})["invalid_away_windows_recipients"] = error
        doc.setdefault("entity", {}).setdefault("switch", {})["home_away_open_window_alert"] = {"name": title}
        pairs = {
            "mobile_notification": (phone, notice),
            "mobile_tts": (phone, voice),
            "watch_notification": (watch, notice),
            "watch_tts": (watch, voice),
            "tablet_notification": (tablet, notice),
            "tablet_tts": (tablet, voice),
            "other_notification": (other, notice),
            "other_tts": (other, voice),
        }
        doc.setdefault("selector", {})["away_window_delivery"] = {
            "options": {key: f"{device} - {mode}" for key, (device, mode) in pairs.items()}
        }
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    apply_away_windows_i18n(Path(__file__).parent / "custom_components/environment_manager")
