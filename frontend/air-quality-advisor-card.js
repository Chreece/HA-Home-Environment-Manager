/* Air Quality Advisor for Home Assistant - native Lovelace card, no dependencies.
 * Install with the integration; the integration registers this asset with HA.
 * The card ONLY displays information. It never controls windows or devices.
 */
(() => {
  'use strict';

  const BRAND_TITLE = "Home Environment Manager";
  const LANGUAGE = {
    en: {
      title:'Air quality', subtitle:'Your home at a glance', outside:'Outside',
      goodOutside:'Good for ventilation', badOutside:'Keep windows closed',
      missingOutside:'Outdoor conditions unknown', partialOutside:'Some outdoor data missing',
      roomStatus:'Rooms', safe:'Good', attention:'Needs attention', unknown:'No data',
      readings:'Measurements', windows:'Windows', windowOpen:'Open', windowClosed:'Closed',
      windowUnknown:'Unknown', open:'Open', close:'Close', openAdvice:'Open windows',
      closeAdvice:'Close windows', blocked:'Ventilation not advised',
      ventilating:'Ventilating', noWindows:'No window sensors',
      missingIndoor:'Indoor readings unavailable', noRooms:'No rooms configured',
      missingCard:'Select an Air Quality Advisor recommendation sensor to display this card.',
      more:'More details', less:'Fewer details', weather:'Weather', warnings:'Warnings',
      limits:'Limit', outdoorSensors:'Outdoor air', noReadings:'No measurements',
      missing:'Unavailable', sensor:'sensor', partial:'Partial data', wind:'Wind',
      humidity:'Humidity', unavailableWeather:'Weather information missing',
      noOutdoor:'No outdoor sensors configured', warningActive:'Active alert',
      warningUnknown:'Alert status unavailable', allOkay:'Indoor air within limits',
      indoorHigh:'Indoor air above a threshold', notSafeToOpen:'Outside prevents opening',
      conditions:'Conditions', measured:'measured', activeWindows:'windows open',
      action:'Recommendation', noAttention:'Everything looks good',
      metric_aqi:'AQI', metric_co2:'CO₂', metric_pm25:'PM2.5',metric_pm10:'PM10',
      metric_voc:'TVOC', metric_voc_parts:'VOC', metric_humidity:'Humidity', metric_mold:'Mold indication',
      wx_sunny:'Sunny', wx_clearNight:'Clear night', wx_partlycloudy:'Partly cloudy',
      wx_cloudy:'Cloudy', wx_rainy:'Rainy', wx_pouring:'Heavy rain',
      wx_lightning:'Thunderstorm', wx_fog:'Fog', wx_snowy:'Snow', wx_windy:'Windy',
      sourceData:'Based on configured Home Assistant sensors',
      allSafe:'No rooms currently need attention',
      warningReason:'Weather warning', unsafeReason:'Unsafe outdoor reading',
      cold:'Too cold outside', hot:'Too hot outside', wet:'High outdoor humidity',
      windHigh:'Strong winds', noWeather:'Weather entity not available'
    },
    de: {
      title:'Luftqualität',subtitle:'Dein Zuhause im Überblick',outside:'Draußen',
      goodOutside:'Lüften möglich',badOutside:'Fenster geschlossen halten',
      missingOutside:'Außenbedingungen unbekannt',partialOutside:'Einige Außendaten fehlen',
      roomStatus:'Räume',safe:'Gut',attention:'Handlungsbedarf',unknown:'Keine Daten',
      readings:'Messwerte',windows:'Fenster',windowOpen:'Offen',windowClosed:'Geschlossen',
      windowUnknown:'Unbekannt',open:'Öffnen',close:'Schließen',openAdvice:'Fenster öffnen',
      closeAdvice:'Fenster schließen',blocked:'Lüften derzeit nicht empfohlen',
      ventilating:'Wird gelüftet',noWindows:'Keine Fensterkontakte',
      missingIndoor:'Innenmesswerte nicht verfügbar',noRooms:'Keine Räume eingerichtet',
      missingCard:'Wähle den Empfehlungssensor von Air Quality Advisor aus.',
      more:'Mehr Details',less:'Weniger Details',weather:'Wetter',warnings:'Warnungen',
      limits:'Grenzwert',outdoorSensors:'Außenluft',noReadings:'Keine Messwerte',
      missing:'Nicht verfügbar',sensor:'Sensor',partial:'Unvollständige Daten',wind:'Wind',
      humidity:'Luftfeuchtigkeit',unavailableWeather:'Wetterdaten fehlen',
      noOutdoor:'Keine Außensensoren konfiguriert',warningActive:'Aktive Warnung',
      warningUnknown:'Warnstatus unbekannt',allOkay:'Innenluft im Grenzbereich',
      indoorHigh:'Innenwert über Grenzwert',notSafeToOpen:'Draußen nicht zum Lüften geeignet',
      conditions:'Bedingungen',measured:'gemessen',activeWindows:'Fenster offen',
      action:'Empfehlung',noAttention:'Alles sieht gut aus',
      metric_humidity:'Luftfeuchtigkeit',metric_mold:'Schimmelindikator',wx_sunny:'Sonnig',wx_clearNight:'Klare Nacht',
      wx_partlycloudy:'Teilweise bewölkt',wx_cloudy:'Bewölkt',wx_rainy:'Regnerisch',
      wx_pouring:'Starkregen',wx_lightning:'Gewitter',wx_fog:'Nebel',wx_snowy:'Schnee',
      wx_windy:'Windig',sourceData:'Basierend auf den eingerichteten Home-Assistant-Sensoren',
      allSafe:'Aktuell kein Raum mit Handlungsbedarf',warningReason:'Wetterwarnung',
      unsafeReason:'Schlechte Außenluft',cold:'Draußen zu kalt',hot:'Draußen zu heiß',
      wet:'Hohe Außenluftfeuchtigkeit',windHigh:'Starker Wind',noWeather:'Wetterentität fehlt'
    },
    el: {
      title:'Ποιότητα αέρα',subtitle:'Το σπίτι σου με μια ματιά',outside:'Εξωτερικά',
      goodOutside:'Κατάλληλο για αερισμό',badOutside:'Κράτησε τα παράθυρα κλειστά',
      missingOutside:'Άγνωστες εξωτερικές συνθήκες',partialOutside:'Λείπουν εξωτερικές μετρήσεις',
      roomStatus:'Δωμάτια',safe:'Καλή',attention:'Χρειάζεται προσοχή',unknown:'Χωρίς δεδομένα',
      readings:'Μετρήσεις',windows:'Παράθυρα',windowOpen:'Ανοιχτό',windowClosed:'Κλειστό',
      windowUnknown:'Άγνωστο',open:'Άνοιγμα',close:'Κλείσιμο',openAdvice:'Άνοιξε τα παράθυρα',
      closeAdvice:'Κλείσε τα παράθυρα',blocked:'Ο αερισμός δεν συνιστάται',
      ventilating:'Γίνεται αερισμός',noWindows:'Δεν υπάρχουν αισθητήρες παραθύρων',
      missingIndoor:'Δεν υπάρχουν εσωτερικές μετρήσεις',noRooms:'Δεν έχουν οριστεί δωμάτια',
      missingCard:'Επίλεξε τον αισθητήρα προτάσεων του Air Quality Advisor.',
      more:'Περισσότερα',less:'Λιγότερα',weather:'Καιρός',warnings:'Προειδοποιήσεις',
      limits:'Όριο',outdoorSensors:'Εξωτερικός αέρας',noReadings:'Δεν υπάρχουν μετρήσεις',
      missing:'Μη διαθέσιμο',sensor:'αισθητήρας',partial:'Ελλιπή δεδομένα',wind:'Άνεμος',
      humidity:'Υγρασία',unavailableWeather:'Λείπουν στοιχεία καιρού',
      noOutdoor:'Δεν έχουν οριστεί εξωτερικοί αισθητήρες',warningActive:'Ενεργή προειδοποίηση',
      warningUnknown:'Άγνωστη κατάσταση προειδοποίησης',allOkay:'Ο εσωτερικός αέρας είναι εντός ορίων',
      indoorHigh:'Υπέρβαση ορίου σε εσωτερική μέτρηση',notSafeToOpen:'Οι εξωτερικές συνθήκες δεν επιτρέπουν αερισμό',
      conditions:'Συνθήκες',measured:'μετρήσεις',activeWindows:'ανοιχτά παράθυρα',
      action:'Πρόταση',noAttention:'Όλα φαίνονται καλά',
      metric_humidity:'Υγρασία',metric_mold:'Ένδειξη μούχλας',wx_sunny:'Ηλιοφάνεια',wx_clearNight:'Ξαστεριά',
      wx_partlycloudy:'Λίγες νεφώσεις',wx_cloudy:'Συννεφιά',wx_rainy:'Βροχή',
      wx_pouring:'Ισχυρή βροχή',wx_lightning:'Καταιγίδα',wx_fog:'Ομίχλη',
      wx_snowy:'Χιόνι',wx_windy:'Άνεμος',sourceData:'Βάσει των ρυθμισμένων αισθητήρων Home Assistant',
      allSafe:'Κανένα δωμάτιο δεν χρειάζεται προσοχή',warningReason:'Προειδοποίηση καιρού',
      unsafeReason:'Κακή ποιότητα εξωτερικού αέρα',cold:'Χαμηλή εξωτερική θερμοκρασία',
      hot:'Υψηλή εξωτερική θερμοκρασία',wet:'Υψηλή εξωτερική υγρασία',
      windHigh:'Ισχυροί άνεμοι',noWeather:'Δεν διατίθενται μετρήσεις καιρού'
    },
    fr: {
      title:'Qualité de l’air',subtitle:'Votre maison en un coup d’œil',outside:'Dehors',
      goodOutside:'Aération possible',badOutside:'Gardez les fenêtres fermées',
      missingOutside:'Conditions extérieures inconnues',partialOutside:'Données extérieures manquantes',
      roomStatus:'Pièces',safe:'Bonne',attention:'À surveiller',unknown:'Sans données',
      readings:'Mesures',windows:'Fenêtres',windowOpen:'Ouverte',windowClosed:'Fermée',
      windowUnknown:'Inconnue',open:'Ouvrir',close:'Fermer',openAdvice:'Ouvrir les fenêtres',
      closeAdvice:'Fermer les fenêtres',blocked:'Aération déconseillée',
      ventilating:'Aération en cours',noWindows:'Aucun contact de fenêtre',
      missingIndoor:'Mesures intérieures indisponibles',noRooms:'Aucune pièce configurée',
      missingCard:'Sélectionnez le capteur de recommandations Air Quality Advisor.',
      more:'Plus de détails',less:'Moins de détails',weather:'Météo',warnings:'Alertes',
      limits:'Seuil',outdoorSensors:'Air extérieur',noReadings:'Aucune mesure',
      missing:'Indisponible',partial:'Données partielles',wind:'Vent',humidity:'Humidité',
      unavailableWeather:'Météo indisponible',noOutdoor:'Aucun capteur extérieur',
      warningActive:'Alerte active',warningUnknown:'État d’alerte inconnu',
      allOkay:'Air intérieur sous les seuils',indoorHigh:'Seuil intérieur dépassé',
      notSafeToOpen:'Conditions extérieures défavorables',conditions:'Conditions',
      measured:'mesurés',activeWindows:'fenêtres ouvertes',action:'Conseil',
      noAttention:'Tout semble bon',metric_humidity:'Humidité',metric_mold:'Indicateur de moisissure',wx_sunny:'Ensoleillé',
      wx_clearNight:'Nuit claire',wx_partlycloudy:'Partiellement nuageux',wx_cloudy:'Nuageux',
      wx_rainy:'Pluvieux',wx_pouring:'Fortes pluies',wx_lightning:'Orage',
      wx_fog:'Brouillard',wx_snowy:'Neige',wx_windy:'Venteux',
      sourceData:'Selon les capteurs Home Assistant configurés',allSafe:'Aucune pièce à surveiller',
      warningReason:'Alerte météo',unsafeReason:'Air extérieur dégradé',cold:'Trop froid dehors',
      hot:'Trop chaud dehors',wet:'Humidité extérieure élevée',windHigh:'Vent fort',noWeather:'Météo manquante'
    },
    es: {
      title:'Calidad del aire',subtitle:'Tu hogar de un vistazo',outside:'Exterior',
      goodOutside:'Adecuado para ventilar',badOutside:'Mantén las ventanas cerradas',
      missingOutside:'Condiciones exteriores desconocidas',partialOutside:'Faltan datos exteriores',
      roomStatus:'Habitaciones',safe:'Bien',attention:'Requiere atención',unknown:'Sin datos',
      readings:'Mediciones',windows:'Ventanas',windowOpen:'Abierta',windowClosed:'Cerrada',
      windowUnknown:'Desconocida',open:'Abrir',close:'Cerrar',openAdvice:'Abre las ventanas',
      closeAdvice:'Cierra las ventanas',blocked:'No se recomienda ventilar',
      ventilating:'Ventilando',noWindows:'No hay sensores de ventana',
      missingIndoor:'Sin mediciones interiores',noRooms:'No hay habitaciones configuradas',
      missingCard:'Selecciona el sensor de recomendaciones de Air Quality Advisor.',
      more:'Más detalles',less:'Menos detalles',weather:'Tiempo',warnings:'Alertas',
      limits:'Límite',outdoorSensors:'Aire exterior',noReadings:'Sin mediciones',
      missing:'No disponible',partial:'Datos parciales',wind:'Viento',humidity:'Humedad',
      unavailableWeather:'Datos meteorológicos no disponibles',noOutdoor:'Sin sensores exteriores',
      warningActive:'Alerta activa',warningUnknown:'Estado de alerta desconocido',
      allOkay:'Aire interior dentro de los límites',indoorHigh:'Límite interior superado',
      notSafeToOpen:'Las condiciones exteriores impiden ventilar',conditions:'Condiciones',
      measured:'medidos',activeWindows:'ventanas abiertas',action:'Recomendación',
      noAttention:'Todo parece correcto',metric_humidity:'Humedad',metric_mold:'Indicador de moho',wx_sunny:'Soleado',
      wx_clearNight:'Noche despejada',wx_partlycloudy:'Parcialmente nublado',wx_cloudy:'Nublado',
      wx_rainy:'Lluvioso',wx_pouring:'Lluvia intensa',wx_lightning:'Tormenta',
      wx_fog:'Niebla',wx_snowy:'Nieve',wx_windy:'Ventoso',
      sourceData:'Según los sensores configurados en Home Assistant',
      allSafe:'Ninguna habitación requiere atención',warningReason:'Alerta meteorológica',
      unsafeReason:'Aire exterior contaminado',cold:'Frío exterior',hot:'Calor exterior',
      wet:'Humedad exterior alta',windHigh:'Viento fuerte',noWeather:'No hay datos meteorológicos'
    },
    it: { title:'Qualità dell’aria',subtitle:'La casa a colpo d’occhio',outside:'All’aperto',
      goodOutside:'Puoi arieggiare',badOutside:'Tieni le finestre chiuse',
      missingOutside:'Condizioni esterne sconosciute',partialOutside:'Dati esterni incompleti',
      roomStatus:'Stanze',safe:'Buona',attention:'Richiede attenzione',unknown:'Senza dati',
      readings:'Misurazioni',windows:'Finestre',windowOpen:'Aperta',windowClosed:'Chiusa',
      windowUnknown:'Sconosciuta',openAdvice:'Apri le finestre',closeAdvice:'Chiudi le finestre',
      blocked:'Aerazione sconsigliata',ventilating:'Aerazione in corso',
      missingIndoor:'Misurazioni interne non disponibili',noRooms:'Nessuna stanza configurata',
      more:'Più dettagli',less:'Meno dettagli',weather:'Meteo',warnings:'Avvisi',
      limits:'Limite',outdoorSensors:'Aria esterna',noReadings:'Nessuna misurazione',
      missing:'Non disponibile',partial:'Dati parziali',wind:'Vento',humidity:'Umidità',
      warningActive:'Avviso attivo',allOkay:'Aria interna nei limiti',indoorHigh:'Limite interno superato',
      notSafeToOpen:'Condizioni esterne sfavorevoli',action:'Consiglio',noAttention:'Tutto a posto',
      metric_humidity:'Umidità',sourceData:'Dati dei sensori di Home Assistant',
      allSafe:'Nessuna stanza richiede attenzione' },
    nl: { title:'Luchtkwaliteit',subtitle:'Je huis in één oogopslag',outside:'Buiten',
      goodOutside:'Geschikt om te ventileren',badOutside:'Houd ramen gesloten',
      missingOutside:'Buitenomstandigheden onbekend',partialOutside:'Buitengegevens ontbreken',
      roomStatus:'Kamers',safe:'Goed',attention:'Aandacht nodig',unknown:'Geen gegevens',
      readings:'Metingen',windows:'Ramen',windowOpen:'Open',windowClosed:'Dicht',
      windowUnknown:'Onbekend',openAdvice:'Open de ramen',closeAdvice:'Sluit de ramen',
      blocked:'Ventileren afgeraden',ventilating:'Bezig met ventileren',
      missingIndoor:'Binnenmetingen ontbreken',noRooms:'Geen kamers ingesteld',
      more:'Meer details',less:'Minder details',weather:'Weer',warnings:'Waarschuwingen',
      limits:'Grenswaarde',outdoorSensors:'Buitenlucht',noReadings:'Geen metingen',
      missing:'Niet beschikbaar',partial:'Onvolledige gegevens',wind:'Wind',humidity:'Vochtigheid',
      warningActive:'Actieve waarschuwing',allOkay:'Binnenlucht binnen de grenzen',
      indoorHigh:'Binnenwaarde te hoog',notSafeToOpen:'Buitenlucht niet geschikt',
      action:'Advies',noAttention:'Alles ziet er goed uit',metric_humidity:'Vochtigheid',
      sourceData:'Gebaseerd op Home Assistant-sensoren',allSafe:'Geen kamers met aandacht nodig' },
    pt: { title:'Qualidade do ar',subtitle:'A sua casa num relance',outside:'Exterior',
      goodOutside:'Condições para ventilar',badOutside:'Mantenha as janelas fechadas',
      missingOutside:'Condições exteriores desconhecidas',partialOutside:'Dados exteriores em falta',
      roomStatus:'Divisões',safe:'Boa',attention:'Precisa de atenção',unknown:'Sem dados',
      readings:'Medições',windows:'Janelas',windowOpen:'Aberta',windowClosed:'Fechada',
      windowUnknown:'Desconhecida',openAdvice:'Abra as janelas',closeAdvice:'Feche as janelas',
      blocked:'Ventilação desaconselhada',ventilating:'A ventilar',
      missingIndoor:'Medições interiores indisponíveis',noRooms:'Sem divisões configuradas',
      more:'Mais detalhes',less:'Menos detalhes',weather:'Tempo',warnings:'Alertas',
      limits:'Limite',outdoorSensors:'Ar exterior',noReadings:'Sem medições',
      missing:'Indisponível',partial:'Dados parciais',wind:'Vento',humidity:'Humidade',
      warningActive:'Alerta ativo',allOkay:'Ar interior dentro dos limites',
      indoorHigh:'Limite interior excedido',notSafeToOpen:'Condições exteriores desfavoráveis',
      action:'Recomendação',noAttention:'Tudo parece bem',metric_humidity:'Humidade',
      sourceData:'Com base nos sensores Home Assistant',allSafe:'Nenhuma divisão requer atenção' },
    pl: { title:'Jakość powietrza',subtitle:'Twój dom w skrócie',outside:'Na zewnątrz',
      goodOutside:'Można wietrzyć',badOutside:'Pozostaw okna zamknięte',
      missingOutside:'Nieznane warunki na zewnątrz',partialOutside:'Brak części danych zewnętrznych',
      roomStatus:'Pomieszczenia',safe:'Dobrze',attention:'Wymaga uwagi',unknown:'Brak danych',
      readings:'Pomiary',windows:'Okna',windowOpen:'Otwarte',windowClosed:'Zamknięte',
      windowUnknown:'Nieznane',openAdvice:'Otwórz okna',closeAdvice:'Zamknij okna',
      blocked:'Wietrzenie niewskazane',ventilating:'Trwa wietrzenie',
      missingIndoor:'Brak pomiarów wewnętrznych',noRooms:'Nie skonfigurowano pomieszczeń',
      more:'Więcej',less:'Mniej',weather:'Pogoda',warnings:'Ostrzeżenia',
      limits:'Próg',outdoorSensors:'Powietrze na zewnątrz',noReadings:'Brak pomiarów',
      missing:'Niedostępne',partial:'Niepełne dane',wind:'Wiatr',humidity:'Wilgotność',
      warningActive:'Aktywne ostrzeżenie',allOkay:'Wartości wewnętrzne w normie',
      indoorHigh:'Przekroczony próg',notSafeToOpen:'Niekorzystne warunki na zewnątrz',
      action:'Zalecenie',noAttention:'Wszystko wygląda dobrze',metric_humidity:'Wilgotność',
      sourceData:'Na podstawie czujników Home Assistant',allSafe:'Brak pomieszczeń wymagających uwagi' },
    ru: { title:'Качество воздуха',subtitle:'Состояние дома с первого взгляда',outside:'На улице',
      goodOutside:'Можно проветривать',badOutside:'Оставьте окна закрытыми',
      missingOutside:'Погода снаружи неизвестна',partialOutside:'Часть данных снаружи недоступна',
      roomStatus:'Комнаты',safe:'Хорошо',attention:'Требует внимания',unknown:'Нет данных',
      readings:'Измерения',windows:'Окна',windowOpen:'Открыто',windowClosed:'Закрыто',
      windowUnknown:'Неизвестно',openAdvice:'Откройте окна',closeAdvice:'Закройте окна',
      blocked:'Проветривание не рекомендуется',ventilating:'Проветривание',
      missingIndoor:'Нет данных внутри',noRooms:'Комнаты не настроены',
      more:'Подробнее',less:'Свернуть',weather:'Погода',warnings:'Предупреждения',
      limits:'Порог',outdoorSensors:'Наружный воздух',noReadings:'Нет измерений',
      missing:'Недоступно',partial:'Частичные данные',wind:'Ветер',humidity:'Влажность',
      warningActive:'Активное предупреждение',allOkay:'Воздух внутри в норме',
      indoorHigh:'Превышен внутренний порог',notSafeToOpen:'Снаружи проветривать нельзя',
      action:'Рекомендация',noAttention:'Всё в порядке',metric_humidity:'Влажность',
      sourceData:'Данные датчиков Home Assistant',allSafe:'Нет комнат, требующих внимания' },
    tr: { title:'Hava kalitesi',subtitle:'Evinize genel bakış',outside:'Dışarıda',
      goodOutside:'Havalandırmaya uygun',badOutside:'Pencereleri kapalı tutun',
      missingOutside:'Dış koşullar bilinmiyor',partialOutside:'Bazı dış veriler eksik',
      roomStatus:'Odalar',safe:'İyi',attention:'Dikkat gerekli',unknown:'Veri yok',
      readings:'Ölçümler',windows:'Pencereler',windowOpen:'Açık',windowClosed:'Kapalı',
      windowUnknown:'Bilinmiyor',openAdvice:'Pencereleri açın',closeAdvice:'Pencereleri kapatın',
      blocked:'Havalandırma önerilmiyor',ventilating:'Havalandırılıyor',
      missingIndoor:'İç ortam ölçümleri yok',noRooms:'Oda yapılandırılmadı',
      more:'Daha fazla',less:'Daha az',weather:'Hava durumu',warnings:'Uyarılar',
      limits:'Sınır',outdoorSensors:'Dış hava',noReadings:'Ölçüm yok',
      missing:'Kullanılamıyor',partial:'Eksik veri',wind:'Rüzgâr',humidity:'Nem',
      warningActive:'Aktif uyarı',allOkay:'İç hava normal',indoorHigh:'İç hava sınırı aşıldı',
      notSafeToOpen:'Dış koşullar uygun değil',action:'Öneri',noAttention:'Her şey yolunda',
      metric_humidity:'Nem',sourceData:'Home Assistant sensörlerinden',
      allSafe:'Dikkat gerektiren oda yok' },
  };

  // Generated from locale packs: UI text follows Home Assistant user language.
  const EXTRA_LANGUAGE = {"it":{"title":"Qualità dell'aria","subtitle":"Qualità dell'aria","outside":"Esterno","goodOutside":"Adatto a ventilare","badOutside":"Tieni le finestre chiuse","missingOutside":"Non disponibile","partialOutside":"Non disponibile","roomStatus":"Stanze","safe":"Buona","attention":"Attenzione","unknown":"Dati assenti","readings":"Apri","windows":"Misurazioni","windowOpen":"Aperta","windowClosed":"Chiusa","windowUnknown":"Dati assenti","open":"Chiudi","close":"Notifiche automatiche","openAdvice":"Chiudi · Misurazioni","closeAdvice":"Notifiche automatiche · Misurazioni","blocked":"Tieni le finestre chiuse","ventilating":"Aerazione in corso","noWindows":"0 · Misurazioni","missingIndoor":"Dati assenti","noRooms":"Nessuna stanza configurata","missingCard":"Air Quality Advisor · Apri","more":"Più dettagli","less":"Meno dettagli","weather":"Meteo","warnings":"Avvisi meteo","limits":"Limite","outdoorSensors":"Qualità dell'aria esterna","noReadings":"Dati assenti","missing":"Non disponibile","sensor":"Apri","partial":"Non disponibile","wind":"Meteo","humidity":"RH","unavailableWeather":"Non disponibile","noOutdoor":"0 · Qualità dell'aria esterna","warningActive":"Avvisi meteo","warningUnknown":"Avvisi meteo","allOkay":"Buona","indoorHigh":"Attenzione","notSafeToOpen":"Tieni le finestre chiuse","conditions":"Esterno","measured":"Apri","activeWindows":"Aperta","action":"Annunci (facoltativi)","noAttention":"Buona","metric_humidity":"RH","sourceData":"Home Assistant · Apri","allSafe":"Buona","warningReason":"Avvisi meteo","unsafeReason":"Tieni le finestre chiuse","noWeather":"Non disponibile"},"nl":{"title":"Luchtkwaliteit","subtitle":"Luchtkwaliteit","outside":"Buiten","goodOutside":"Geschikt om te ventileren","badOutside":"Houd ramen gesloten","missingOutside":"Niet beschikbaar","partialOutside":"Niet beschikbaar","roomStatus":"Kamers","safe":"Goed","attention":"Aandacht nodig","unknown":"Geen gegevens","readings":"Open","windows":"Metingen","windowOpen":"Open","windowClosed":"Gesloten","windowUnknown":"Geen gegevens","open":"Sluit","close":"Automatische meldingen","openAdvice":"Sluit · Metingen","closeAdvice":"Automatische meldingen · Metingen","blocked":"Houd ramen gesloten","ventilating":"Ventilatie actief","noWindows":"0 · Metingen","missingIndoor":"Geen gegevens","noRooms":"Geen kamers ingesteld","missingCard":"Air Quality Advisor · Open","more":"Meer details","less":"Minder details","weather":"Weer","warnings":"Weerwaarschuwingen","limits":"Grenswaarde","outdoorSensors":"Buitenluchtkwaliteit","noReadings":"Geen gegevens","missing":"Niet beschikbaar","sensor":"Open","partial":"Niet beschikbaar","wind":"Weer","humidity":"RH","unavailableWeather":"Niet beschikbaar","noOutdoor":"0 · Buitenluchtkwaliteit","warningActive":"Weerwaarschuwingen","warningUnknown":"Weerwaarschuwingen","allOkay":"Goed","indoorHigh":"Aandacht nodig","notSafeToOpen":"Houd ramen gesloten","conditions":"Buiten","measured":"Open","activeWindows":"Open","action":"Meldingen (optioneel)","noAttention":"Goed","metric_humidity":"RH","sourceData":"Home Assistant · Open","allSafe":"Goed","warningReason":"Weerwaarschuwingen","unsafeReason":"Houd ramen gesloten","noWeather":"Niet beschikbaar"},"pt":{"title":"Qualidade do ar","subtitle":"Qualidade do ar","outside":"Exterior","goodOutside":"Bom para ventilar","badOutside":"Mantenha as janelas fechadas","missingOutside":"Indisponível","partialOutside":"Indisponível","roomStatus":"Divisões","safe":"Boa","attention":"Requer atenção","unknown":"Sem dados","readings":"Abra","windows":"Medições","windowOpen":"Aberta","windowClosed":"Fechada","windowUnknown":"Sem dados","open":"Feche","close":"Notificações automáticas","openAdvice":"Feche · Medições","closeAdvice":"Notificações automáticas · Medições","blocked":"Mantenha as janelas fechadas","ventilating":"A ventilar","noWindows":"0 · Medições","missingIndoor":"Sem dados","noRooms":"Sem divisões configuradas","missingCard":"Air Quality Advisor · Abra","more":"Mais detalhes","less":"Menos detalhes","weather":"Tempo","warnings":"Avisos meteorológicos","limits":"Limite","outdoorSensors":"Qualidade do ar exterior","noReadings":"Sem dados","missing":"Indisponível","sensor":"Abra","partial":"Indisponível","wind":"Tempo","humidity":"RH","unavailableWeather":"Indisponível","noOutdoor":"0 · Qualidade do ar exterior","warningActive":"Avisos meteorológicos","warningUnknown":"Avisos meteorológicos","allOkay":"Boa","indoorHigh":"Requer atenção","notSafeToOpen":"Mantenha as janelas fechadas","conditions":"Exterior","measured":"Abra","activeWindows":"Aberta","action":"Anúncios (opcional)","noAttention":"Boa","metric_humidity":"RH","sourceData":"Home Assistant · Abra","allSafe":"Boa","warningReason":"Avisos meteorológicos","unsafeReason":"Mantenha as janelas fechadas","noWeather":"Indisponível"},"pt-br":{"title":"Qualidade do ar","subtitle":"Qualidade do ar","outside":"Área externa","goodOutside":"Bom para ventilar","badOutside":"Mantenha as janelas fechadas","missingOutside":"Indisponível","partialOutside":"Indisponível","roomStatus":"Cômodos","safe":"Boa","attention":"Precisa de atenção","unknown":"Sem dados","readings":"Abra","windows":"Medições","windowOpen":"Aberta","windowClosed":"Fechada","windowUnknown":"Sem dados","open":"Feche","close":"Notificações automáticas","openAdvice":"Feche · Medições","closeAdvice":"Notificações automáticas · Medições","blocked":"Mantenha as janelas fechadas","ventilating":"Ventilando","noWindows":"0 · Medições","missingIndoor":"Sem dados","noRooms":"Nenhum cômodo configurado","missingCard":"Air Quality Advisor · Abra","more":"Mais detalhes","less":"Menos detalhes","weather":"Clima","warnings":"Alertas meteorológicos","limits":"Limite","outdoorSensors":"Qualidade do ar externo","noReadings":"Sem dados","missing":"Indisponível","sensor":"Abra","partial":"Indisponível","wind":"Clima","humidity":"RH","unavailableWeather":"Indisponível","noOutdoor":"0 · Qualidade do ar externo","warningActive":"Alertas meteorológicos","warningUnknown":"Alertas meteorológicos","allOkay":"Boa","indoorHigh":"Precisa de atenção","notSafeToOpen":"Mantenha as janelas fechadas","conditions":"Área externa","measured":"Abra","activeWindows":"Aberta","action":"Avisos (opcional)","noAttention":"Boa","metric_humidity":"RH","sourceData":"Home Assistant · Abra","allSafe":"Boa","warningReason":"Alertas meteorológicos","unsafeReason":"Mantenha as janelas fechadas","noWeather":"Indisponível"},"pl":{"title":"Jakość powietrza","subtitle":"Jakość powietrza","outside":"Na zewnątrz","goodOutside":"Można wietrzyć","badOutside":"Pozostaw okna zamknięte","missingOutside":"Niedostępne","partialOutside":"Niedostępne","roomStatus":"Pomieszczenia","safe":"Dobra","attention":"Wymaga uwagi","unknown":"Brak danych","readings":"Otwórz","windows":"Pomiary","windowOpen":"Otwarte","windowClosed":"Zamknięte","windowUnknown":"Brak danych","open":"Zamknij","close":"Automatyczne powiadomienia","openAdvice":"Zamknij · Pomiary","closeAdvice":"Automatyczne powiadomienia · Pomiary","blocked":"Pozostaw okna zamknięte","ventilating":"Trwa wietrzenie","noWindows":"0 · Pomiary","missingIndoor":"Brak danych","noRooms":"Brak skonfigurowanych pomieszczeń","missingCard":"Air Quality Advisor · Otwórz","more":"Więcej szczegółów","less":"Mniej szczegółów","weather":"Pogoda","warnings":"Ostrzeżenia pogodowe","limits":"Próg","outdoorSensors":"Jakość powietrza na zewnątrz","noReadings":"Brak danych","missing":"Niedostępne","sensor":"Otwórz","partial":"Niedostępne","wind":"Pogoda","humidity":"RH","unavailableWeather":"Niedostępne","noOutdoor":"0 · Jakość powietrza na zewnątrz","warningActive":"Ostrzeżenia pogodowe","warningUnknown":"Ostrzeżenia pogodowe","allOkay":"Dobra","indoorHigh":"Wymaga uwagi","notSafeToOpen":"Pozostaw okna zamknięte","conditions":"Na zewnątrz","measured":"Otwórz","activeWindows":"Otwarte","action":"Komunikaty (opcjonalnie)","noAttention":"Dobra","metric_humidity":"RH","sourceData":"Home Assistant · Otwórz","allSafe":"Dobra","warningReason":"Ostrzeżenia pogodowe","unsafeReason":"Pozostaw okna zamknięte","noWeather":"Niedostępne"},"ru":{"title":"Качество воздуха","subtitle":"Качество воздуха","outside":"Снаружи","goodOutside":"Можно проветривать","badOutside":"Держите окна закрытыми","missingOutside":"Недоступно","partialOutside":"Недоступно","roomStatus":"Комнаты","safe":"Хорошее","attention":"Требует внимания","unknown":"Нет данных","readings":"Откройте","windows":"Измерения","windowOpen":"Открыто","windowClosed":"Закрыто","windowUnknown":"Нет данных","open":"Закройте","close":"Автоматические уведомления","openAdvice":"Закройте · Измерения","closeAdvice":"Автоматические уведомления · Измерения","blocked":"Держите окна закрытыми","ventilating":"Проветривание","noWindows":"0 · Измерения","missingIndoor":"Нет данных","noRooms":"Нет выбранных комнат","missingCard":"Air Quality Advisor · Откройте","more":"Подробнее","less":"Свернуть","weather":"Погода","warnings":"Погодные предупреждения","limits":"Порог","outdoorSensors":"Качество воздуха снаружи","noReadings":"Нет данных","missing":"Недоступно","sensor":"Откройте","partial":"Недоступно","wind":"Погода","humidity":"RH","unavailableWeather":"Недоступно","noOutdoor":"0 · Качество воздуха снаружи","warningActive":"Погодные предупреждения","warningUnknown":"Погодные предупреждения","allOkay":"Хорошее","indoorHigh":"Требует внимания","notSafeToOpen":"Держите окна закрытыми","conditions":"Снаружи","measured":"Откройте","activeWindows":"Открыто","action":"Оповещения (необязательно)","noAttention":"Хорошее","metric_humidity":"RH","sourceData":"Home Assistant · Откройте","allSafe":"Хорошее","warningReason":"Погодные предупреждения","unsafeReason":"Держите окна закрытыми","noWeather":"Недоступно"},"uk":{"title":"Якість повітря","subtitle":"Якість повітря","outside":"Надворі","goodOutside":"Можна провітрювати","badOutside":"Тримайте вікна зачиненими","missingOutside":"Недоступно","partialOutside":"Недоступно","roomStatus":"Кімнати","safe":"Добра","attention":"Потребує уваги","unknown":"Немає даних","readings":"Відкрийте","windows":"Вимірювання","windowOpen":"Відчинене","windowClosed":"Зачинене","windowUnknown":"Немає даних","open":"Зачиніть","close":"Автоматичні сповіщення","openAdvice":"Зачиніть · Вимірювання","closeAdvice":"Автоматичні сповіщення · Вимірювання","blocked":"Тримайте вікна зачиненими","ventilating":"Провітрювання","noWindows":"0 · Вимірювання","missingIndoor":"Немає даних","noRooms":"Немає вибраних кімнат","missingCard":"Air Quality Advisor · Відкрийте","more":"Докладніше","less":"Менше деталей","weather":"Погода","warnings":"Попередження про погоду","limits":"Поріг","outdoorSensors":"Якість повітря надворі","noReadings":"Немає даних","missing":"Недоступно","sensor":"Відкрийте","partial":"Недоступно","wind":"Погода","humidity":"RH","unavailableWeather":"Недоступно","noOutdoor":"0 · Якість повітря надворі","warningActive":"Попередження про погоду","warningUnknown":"Попередження про погоду","allOkay":"Добра","indoorHigh":"Потребує уваги","notSafeToOpen":"Тримайте вікна зачиненими","conditions":"Надворі","measured":"Відкрийте","activeWindows":"Відчинене","action":"Оголошення (необов’язково)","noAttention":"Добра","metric_humidity":"RH","sourceData":"Home Assistant · Відкрийте","allSafe":"Добра","warningReason":"Попередження про погоду","unsafeReason":"Тримайте вікна зачиненими","noWeather":"Недоступно"},"tr":{"title":"Hava kalitesi","subtitle":"Hava kalitesi","outside":"Dışarısı","goodOutside":"Havalandırmaya uygun","badOutside":"Pencereleri kapalı tutun","missingOutside":"Kullanılamıyor","partialOutside":"Kullanılamıyor","roomStatus":"Odalar","safe":"İyi","attention":"İlgi gerekiyor","unknown":"Veri yok","readings":"Açın","windows":"Ölçümler","windowOpen":"Açık","windowClosed":"Kapalı","windowUnknown":"Veri yok","open":"Kapatın","close":"Otomatik bildirimler","openAdvice":"Kapatın · Ölçümler","closeAdvice":"Otomatik bildirimler · Ölçümler","blocked":"Pencereleri kapalı tutun","ventilating":"Havalandırılıyor","noWindows":"0 · Ölçümler","missingIndoor":"Veri yok","noRooms":"Oda yapılandırılmamış","missingCard":"Air Quality Advisor · Açın","more":"Daha fazla ayrıntı","less":"Daha az ayrıntı","weather":"Hava durumu","warnings":"Hava durumu uyarıları","limits":"Eşik","outdoorSensors":"Dış hava kalitesi","noReadings":"Veri yok","missing":"Kullanılamıyor","sensor":"Açın","partial":"Kullanılamıyor","wind":"Hava durumu","humidity":"RH","unavailableWeather":"Kullanılamıyor","noOutdoor":"0 · Dış hava kalitesi","warningActive":"Hava durumu uyarıları","warningUnknown":"Hava durumu uyarıları","allOkay":"İyi","indoorHigh":"İlgi gerekiyor","notSafeToOpen":"Pencereleri kapalı tutun","conditions":"Dışarısı","measured":"Açın","activeWindows":"Açık","action":"Duyurular (isteğe bağlı)","noAttention":"İyi","metric_humidity":"RH","sourceData":"Home Assistant · Açın","allSafe":"İyi","warningReason":"Hava durumu uyarıları","unsafeReason":"Pencereleri kapalı tutun","noWeather":"Kullanılamıyor"},"cs":{"title":"Kvalita vzduchu","subtitle":"Kvalita vzduchu","outside":"Venku","goodOutside":"Vhodné pro větrání","badOutside":"Nechte okna zavřená","missingOutside":"Nedostupné","partialOutside":"Nedostupné","roomStatus":"Místnosti","safe":"Dobrá","attention":"Vyžaduje pozornost","unknown":"Bez dat","readings":"Otevřete","windows":"Měření","windowOpen":"Otevřené","windowClosed":"Zavřené","windowUnknown":"Bez dat","open":"Zavřete","close":"Automatická oznámení","openAdvice":"Zavřete · Měření","closeAdvice":"Automatická oznámení · Měření","blocked":"Nechte okna zavřená","ventilating":"Probíhá větrání","noWindows":"0 · Měření","missingIndoor":"Bez dat","noRooms":"Nejsou vybrány místnosti","missingCard":"Air Quality Advisor · Otevřete","more":"Více informací","less":"Méně informací","weather":"Počasí","warnings":"Výstrahy počasí","limits":"Limit","outdoorSensors":"Kvalita venkovního vzduchu","noReadings":"Bez dat","missing":"Nedostupné","sensor":"Otevřete","partial":"Nedostupné","wind":"Počasí","humidity":"RH","unavailableWeather":"Nedostupné","noOutdoor":"0 · Kvalita venkovního vzduchu","warningActive":"Výstrahy počasí","warningUnknown":"Výstrahy počasí","allOkay":"Dobrá","indoorHigh":"Vyžaduje pozornost","notSafeToOpen":"Nechte okna zavřená","conditions":"Venku","measured":"Otevřete","activeWindows":"Otevřené","action":"Oznámení (volitelně)","noAttention":"Dobrá","metric_humidity":"RH","sourceData":"Home Assistant · Otevřete","allSafe":"Dobrá","warningReason":"Výstrahy počasí","unsafeReason":"Nechte okna zavřená","noWeather":"Nedostupné"},"sk":{"title":"Kvalita vzduchu","subtitle":"Kvalita vzduchu","outside":"Vonku","goodOutside":"Vhodné na vetranie","badOutside":"Nechajte okná zatvorené","missingOutside":"Nedostupné","partialOutside":"Nedostupné","roomStatus":"Miestnosti","safe":"Dobrá","attention":"Vyžaduje pozornosť","unknown":"Bez údajov","readings":"Otvorte","windows":"Merania","windowOpen":"Otvorené","windowClosed":"Zatvorené","windowUnknown":"Bez údajov","open":"Zatvorte","close":"Automatické oznámenia","openAdvice":"Zatvorte · Merania","closeAdvice":"Automatické oznámenia · Merania","blocked":"Nechajte okná zatvorené","ventilating":"Prebieha vetranie","noWindows":"0 · Merania","missingIndoor":"Bez údajov","noRooms":"Žiadne miestnosti","missingCard":"Air Quality Advisor · Otvorte","more":"Viac podrobností","less":"Menej podrobností","weather":"Počasie","warnings":"Výstrahy počasia","limits":"Limit","outdoorSensors":"Kvalita vonkajšieho vzduchu","noReadings":"Bez údajov","missing":"Nedostupné","sensor":"Otvorte","partial":"Nedostupné","wind":"Počasie","humidity":"RH","unavailableWeather":"Nedostupné","noOutdoor":"0 · Kvalita vonkajšieho vzduchu","warningActive":"Výstrahy počasia","warningUnknown":"Výstrahy počasia","allOkay":"Dobrá","indoorHigh":"Vyžaduje pozornosť","notSafeToOpen":"Nechajte okná zatvorené","conditions":"Vonku","measured":"Otvorte","activeWindows":"Otvorené","action":"Oznámenia (voliteľné)","noAttention":"Dobrá","metric_humidity":"RH","sourceData":"Home Assistant · Otvorte","allSafe":"Dobrá","warningReason":"Výstrahy počasia","unsafeReason":"Nechajte okná zatvorené","noWeather":"Nedostupné"},"hu":{"title":"Levegőminőség","subtitle":"Levegőminőség","outside":"Kint","goodOutside":"Szellőztetésre alkalmas","badOutside":"Tartsd csukva az ablakokat","missingOutside":"Nem érhető el","partialOutside":"Nem érhető el","roomStatus":"Helyiségek","safe":"Jó","attention":"Figyelmet igényel","unknown":"Nincs adat","readings":"Nyisd ki","windows":"Mérések","windowOpen":"Nyitva","windowClosed":"Zárva","windowUnknown":"Nincs adat","open":"Csukd be","close":"Automatikus értesítések","openAdvice":"Csukd be · Mérések","closeAdvice":"Automatikus értesítések · Mérések","blocked":"Tartsd csukva az ablakokat","ventilating":"Szellőztetés folyamatban","noWindows":"0 · Mérések","missingIndoor":"Nincs adat","noRooms":"Nincs beállított helyiség","missingCard":"Air Quality Advisor · Nyisd ki","more":"További részletek","less":"Kevesebb részlet","weather":"Időjárás","warnings":"Időjárási figyelmeztetések","limits":"Határérték","outdoorSensors":"Kültéri levegőminőség","noReadings":"Nincs adat","missing":"Nem érhető el","sensor":"Nyisd ki","partial":"Nem érhető el","wind":"Időjárás","humidity":"RH","unavailableWeather":"Nem érhető el","noOutdoor":"0 · Kültéri levegőminőség","warningActive":"Időjárási figyelmeztetések","warningUnknown":"Időjárási figyelmeztetések","allOkay":"Jó","indoorHigh":"Figyelmet igényel","notSafeToOpen":"Tartsd csukva az ablakokat","conditions":"Kint","measured":"Nyisd ki","activeWindows":"Nyitva","action":"Értesítések (opcionális)","noAttention":"Jó","metric_humidity":"RH","sourceData":"Home Assistant · Nyisd ki","allSafe":"Jó","warningReason":"Időjárási figyelmeztetések","unsafeReason":"Tartsd csukva az ablakokat","noWeather":"Nem érhető el"},"ro":{"title":"Calitatea aerului","subtitle":"Calitatea aerului","outside":"Exterior","goodOutside":"Potrivit pentru aerisire","badOutside":"Țineți ferestrele închise","missingOutside":"Indisponibil","partialOutside":"Indisponibil","roomStatus":"Camere","safe":"Bună","attention":"Necesită atenție","unknown":"Fără date","readings":"Deschideți","windows":"Măsurători","windowOpen":"Deschisă","windowClosed":"Închisă","windowUnknown":"Fără date","open":"Închideți","close":"Notificări automate","openAdvice":"Închideți · Măsurători","closeAdvice":"Notificări automate · Măsurători","blocked":"Țineți ferestrele închise","ventilating":"Aerisire în curs","noWindows":"0 · Măsurători","missingIndoor":"Fără date","noRooms":"Nu sunt camere configurate","missingCard":"Air Quality Advisor · Deschideți","more":"Mai multe detalii","less":"Mai puține detalii","weather":"Vreme","warnings":"Avertizări meteo","limits":"Prag","outdoorSensors":"Calitatea aerului exterior","noReadings":"Fără date","missing":"Indisponibil","sensor":"Deschideți","partial":"Indisponibil","wind":"Vreme","humidity":"RH","unavailableWeather":"Indisponibil","noOutdoor":"0 · Calitatea aerului exterior","warningActive":"Avertizări meteo","warningUnknown":"Avertizări meteo","allOkay":"Bună","indoorHigh":"Necesită atenție","notSafeToOpen":"Țineți ferestrele închise","conditions":"Exterior","measured":"Deschideți","activeWindows":"Deschisă","action":"Anunțuri (opțional)","noAttention":"Bună","metric_humidity":"RH","sourceData":"Home Assistant · Deschideți","allSafe":"Bună","warningReason":"Avertizări meteo","unsafeReason":"Țineți ferestrele închise","noWeather":"Indisponibil"},"bg":{"title":"Качество на въздуха","subtitle":"Качество на въздуха","outside":"Навън","goodOutside":"Подходящо за проветряване","badOutside":"Дръжте прозорците затворени","missingOutside":"Недостъпно","partialOutside":"Недостъпно","roomStatus":"Стаи","safe":"Добро","attention":"Изисква внимание","unknown":"Няма данни","readings":"Отворете","windows":"Измервания","windowOpen":"Отворен","windowClosed":"Затворен","windowUnknown":"Няма данни","open":"Затворете","close":"Автоматични известия","openAdvice":"Затворете · Измервания","closeAdvice":"Автоматични известия · Измервания","blocked":"Дръжте прозорците затворени","ventilating":"Проветряване","noWindows":"0 · Измервания","missingIndoor":"Няма данни","noRooms":"Няма настроени стаи","missingCard":"Air Quality Advisor · Отворете","more":"Повече подробности","less":"По-малко подробности","weather":"Време","warnings":"Метеорологични предупреждения","limits":"Праг","outdoorSensors":"Качество на външния въздух","noReadings":"Няма данни","missing":"Недостъпно","sensor":"Отворете","partial":"Недостъпно","wind":"Време","humidity":"RH","unavailableWeather":"Недостъпно","noOutdoor":"0 · Качество на външния въздух","warningActive":"Метеорологични предупреждения","warningUnknown":"Метеорологични предупреждения","allOkay":"Добро","indoorHigh":"Изисква внимание","notSafeToOpen":"Дръжте прозорците затворени","conditions":"Навън","measured":"Отворете","activeWindows":"Отворен","action":"Съобщения (по избор)","noAttention":"Добро","metric_humidity":"RH","sourceData":"Home Assistant · Отворете","allSafe":"Добро","warningReason":"Метеорологични предупреждения","unsafeReason":"Дръжте прозорците затворени","noWeather":"Недостъпно"},"hr":{"title":"Kvaliteta zraka","subtitle":"Kvaliteta zraka","outside":"Vani","goodOutside":"Pogodno za provjetravanje","badOutside":"Držite prozore zatvorenima","missingOutside":"Nedostupno","partialOutside":"Nedostupno","roomStatus":"Prostorije","safe":"Dobra","attention":"Potrebna pažnja","unknown":"Nema podataka","readings":"Otvorite","windows":"Mjerenja","windowOpen":"Otvoren","windowClosed":"Zatvoren","windowUnknown":"Nema podataka","open":"Zatvorite","close":"Automatske obavijesti","openAdvice":"Zatvorite · Mjerenja","closeAdvice":"Automatske obavijesti · Mjerenja","blocked":"Držite prozore zatvorenima","ventilating":"Provjetravanje","noWindows":"0 · Mjerenja","missingIndoor":"Nema podataka","noRooms":"Nema podešenih prostorija","missingCard":"Air Quality Advisor · Otvorite","more":"Više detalja","less":"Manje detalja","weather":"Vrijeme","warnings":"Vremenska upozorenja","limits":"Prag","outdoorSensors":"Kvaliteta vanjskog zraka","noReadings":"Nema podataka","missing":"Nedostupno","sensor":"Otvorite","partial":"Nedostupno","wind":"Vrijeme","humidity":"RH","unavailableWeather":"Nedostupno","noOutdoor":"0 · Kvaliteta vanjskog zraka","warningActive":"Vremenska upozorenja","warningUnknown":"Vremenska upozorenja","allOkay":"Dobra","indoorHigh":"Potrebna pažnja","notSafeToOpen":"Držite prozore zatvorenima","conditions":"Vani","measured":"Otvorite","activeWindows":"Otvoren","action":"Obavijesti (neobavezno)","noAttention":"Dobra","metric_humidity":"RH","sourceData":"Home Assistant · Otvorite","allSafe":"Dobra","warningReason":"Vremenska upozorenja","unsafeReason":"Držite prozore zatvorenima","noWeather":"Nedostupno"},"sr":{"title":"Квалитет ваздуха","subtitle":"Квалитет ваздуха","outside":"Напољу","goodOutside":"Погодно за проветравање","badOutside":"Држите прозоре затвореним","missingOutside":"Недоступно","partialOutside":"Недоступно","roomStatus":"Собе","safe":"Добар","attention":"Потребна пажња","unknown":"Нема података","readings":"Отворите","windows":"Мерења","windowOpen":"Отворен","windowClosed":"Затворен","windowUnknown":"Нема података","open":"Затворите","close":"Аутоматска обавештења","openAdvice":"Затворите · Мерења","closeAdvice":"Аутоматска обавештења · Мерења","blocked":"Држите прозоре затвореним","ventilating":"Проветравање","noWindows":"0 · Мерења","missingIndoor":"Нема података","noRooms":"Нема подешених соба","missingCard":"Air Quality Advisor · Отворите","more":"Више детаља","less":"Мање детаља","weather":"Време","warnings":"Временска упозорења","limits":"Праг","outdoorSensors":"Квалитет спољног ваздуха","noReadings":"Нема података","missing":"Недоступно","sensor":"Отворите","partial":"Недоступно","wind":"Време","humidity":"RH","unavailableWeather":"Недоступно","noOutdoor":"0 · Квалитет спољног ваздуха","warningActive":"Временска упозорења","warningUnknown":"Временска упозорења","allOkay":"Добар","indoorHigh":"Потребна пажња","notSafeToOpen":"Држите прозоре затвореним","conditions":"Напољу","measured":"Отворите","activeWindows":"Отворен","action":"Обавештења (опционо)","noAttention":"Добар","metric_humidity":"RH","sourceData":"Home Assistant · Отворите","allSafe":"Добар","warningReason":"Временска упозорења","unsafeReason":"Држите прозоре затвореним","noWeather":"Недоступно"},"sv":{"title":"Luftkvalitet","subtitle":"Luftkvalitet","outside":"Utomhus","goodOutside":"Bra för vädring","badOutside":"Håll fönstren stängda","missingOutside":"Inte tillgänglig","partialOutside":"Inte tillgänglig","roomStatus":"Rum","safe":"Bra","attention":"Behöver åtgärdas","unknown":"Inga data","readings":"Öppna","windows":"Mätningar","windowOpen":"Öppet","windowClosed":"Stängt","windowUnknown":"Inga data","open":"Stäng","close":"Automatiska aviseringar","openAdvice":"Stäng · Mätningar","closeAdvice":"Automatiska aviseringar · Mätningar","blocked":"Håll fönstren stängda","ventilating":"Vädring pågår","noWindows":"0 · Mätningar","missingIndoor":"Inga data","noRooms":"Inga rum konfigurerade","missingCard":"Air Quality Advisor · Öppna","more":"Fler detaljer","less":"Färre detaljer","weather":"Väder","warnings":"Vädervarningar","limits":"Gränsvärde","outdoorSensors":"Utomhusluftens kvalitet","noReadings":"Inga data","missing":"Inte tillgänglig","sensor":"Öppna","partial":"Inte tillgänglig","wind":"Väder","humidity":"RH","unavailableWeather":"Inte tillgänglig","noOutdoor":"0 · Utomhusluftens kvalitet","warningActive":"Vädervarningar","warningUnknown":"Vädervarningar","allOkay":"Bra","indoorHigh":"Behöver åtgärdas","notSafeToOpen":"Håll fönstren stängda","conditions":"Utomhus","measured":"Öppna","activeWindows":"Öppet","action":"Meddelanden (valfritt)","noAttention":"Bra","metric_humidity":"RH","sourceData":"Home Assistant · Öppna","allSafe":"Bra","warningReason":"Vädervarningar","unsafeReason":"Håll fönstren stängda","noWeather":"Inte tillgänglig"},"nb":{"title":"Luftkvalitet","subtitle":"Luftkvalitet","outside":"Ute","goodOutside":"Egnet for lufting","badOutside":"Hold vinduene lukket","missingOutside":"Ikke tilgjengelig","partialOutside":"Ikke tilgjengelig","roomStatus":"Rom","safe":"God","attention":"Trenger oppmerksomhet","unknown":"Ingen data","readings":"Åpne","windows":"Målinger","windowOpen":"Åpent","windowClosed":"Lukket","windowUnknown":"Ingen data","open":"Lukk","close":"Automatiske varsler","openAdvice":"Lukk · Målinger","closeAdvice":"Automatiske varsler · Målinger","blocked":"Hold vinduene lukket","ventilating":"Lufter nå","noWindows":"0 · Målinger","missingIndoor":"Ingen data","noRooms":"Ingen rom konfigurert","missingCard":"Air Quality Advisor · Åpne","more":"Flere detaljer","less":"Færre detaljer","weather":"Vær","warnings":"Værvarsler","limits":"Grenseverdi","outdoorSensors":"Luftkvalitet ute","noReadings":"Ingen data","missing":"Ikke tilgjengelig","sensor":"Åpne","partial":"Ikke tilgjengelig","wind":"Vær","humidity":"RH","unavailableWeather":"Ikke tilgjengelig","noOutdoor":"0 · Luftkvalitet ute","warningActive":"Værvarsler","warningUnknown":"Værvarsler","allOkay":"God","indoorHigh":"Trenger oppmerksomhet","notSafeToOpen":"Hold vinduene lukket","conditions":"Ute","measured":"Åpne","activeWindows":"Åpent","action":"Kunngjøringer (valgfritt)","noAttention":"God","metric_humidity":"RH","sourceData":"Home Assistant · Åpne","allSafe":"God","warningReason":"Værvarsler","unsafeReason":"Hold vinduene lukket","noWeather":"Ikke tilgjengelig"},"da":{"title":"Luftkvalitet","subtitle":"Luftkvalitet","outside":"Udenfor","goodOutside":"Egnet til udluftning","badOutside":"Hold vinduerne lukkede","missingOutside":"Ikke tilgængelig","partialOutside":"Ikke tilgængelig","roomStatus":"Rum","safe":"God","attention":"Kræver opmærksomhed","unknown":"Ingen data","readings":"Åbn","windows":"Målinger","windowOpen":"Åbent","windowClosed":"Lukket","windowUnknown":"Ingen data","open":"Luk","close":"Automatiske notifikationer","openAdvice":"Luk · Målinger","closeAdvice":"Automatiske notifikationer · Målinger","blocked":"Hold vinduerne lukkede","ventilating":"Udluftning i gang","noWindows":"0 · Målinger","missingIndoor":"Ingen data","noRooms":"Ingen rum konfigureret","missingCard":"Air Quality Advisor · Åbn","more":"Flere detaljer","less":"Færre detaljer","weather":"Vejr","warnings":"Vejradvarsler","limits":"Grænse","outdoorSensors":"Udendørs luftkvalitet","noReadings":"Ingen data","missing":"Ikke tilgængelig","sensor":"Åbn","partial":"Ikke tilgængelig","wind":"Vejr","humidity":"RH","unavailableWeather":"Ikke tilgængelig","noOutdoor":"0 · Udendørs luftkvalitet","warningActive":"Vejradvarsler","warningUnknown":"Vejradvarsler","allOkay":"God","indoorHigh":"Kræver opmærksomhed","notSafeToOpen":"Hold vinduerne lukkede","conditions":"Udenfor","measured":"Åbn","activeWindows":"Åbent","action":"Meddelelser (valgfrit)","noAttention":"God","metric_humidity":"RH","sourceData":"Home Assistant · Åbn","allSafe":"God","warningReason":"Vejradvarsler","unsafeReason":"Hold vinduerne lukkede","noWeather":"Ikke tilgængelig"},"fi":{"title":"Ilmanlaatu","subtitle":"Ilmanlaatu","outside":"Ulkona","goodOutside":"Sopii tuuletukseen","badOutside":"Pidä ikkunat kiinni","missingOutside":"Ei saatavilla","partialOutside":"Ei saatavilla","roomStatus":"Huoneet","safe":"Hyvä","attention":"Vaatii huomiota","unknown":"Ei tietoja","readings":"Avaa","windows":"Mittaukset","windowOpen":"Auki","windowClosed":"Kiinni","windowUnknown":"Ei tietoja","open":"Sulje","close":"Automaattiset ilmoitukset","openAdvice":"Sulje · Mittaukset","closeAdvice":"Automaattiset ilmoitukset · Mittaukset","blocked":"Pidä ikkunat kiinni","ventilating":"Tuuletus käynnissä","noWindows":"0 · Mittaukset","missingIndoor":"Ei tietoja","noRooms":"Huoneita ei ole määritetty","missingCard":"Air Quality Advisor · Avaa","more":"Lisätiedot","less":"Vähemmän tietoja","weather":"Sää","warnings":"Säävaroitukset","limits":"Raja-arvo","outdoorSensors":"Ulkoilman laatu","noReadings":"Ei tietoja","missing":"Ei saatavilla","sensor":"Avaa","partial":"Ei saatavilla","wind":"Sää","humidity":"RH","unavailableWeather":"Ei saatavilla","noOutdoor":"0 · Ulkoilman laatu","warningActive":"Säävaroitukset","warningUnknown":"Säävaroitukset","allOkay":"Hyvä","indoorHigh":"Vaatii huomiota","notSafeToOpen":"Pidä ikkunat kiinni","conditions":"Ulkona","measured":"Avaa","activeWindows":"Auki","action":"Ilmoitukset (valinnainen)","noAttention":"Hyvä","metric_humidity":"RH","sourceData":"Home Assistant · Avaa","allSafe":"Hyvä","warningReason":"Säävaroitukset","unsafeReason":"Pidä ikkunat kiinni","noWeather":"Ei saatavilla"},"id":{"title":"Kualitas udara","subtitle":"Kualitas udara","outside":"Di luar","goodOutside":"Baik untuk ventilasi","badOutside":"Biarkan jendela tertutup","missingOutside":"Tidak tersedia","partialOutside":"Tidak tersedia","roomStatus":"Ruangan","safe":"Baik","attention":"Perlu perhatian","unknown":"Tidak ada data","readings":"Buka","windows":"Pengukuran","windowOpen":"Terbuka","windowClosed":"Tertutup","windowUnknown":"Tidak ada data","open":"Tutup","close":"Notifikasi otomatis","openAdvice":"Tutup · Pengukuran","closeAdvice":"Notifikasi otomatis · Pengukuran","blocked":"Biarkan jendela tertutup","ventilating":"Sedang berventilasi","noWindows":"0 · Pengukuran","missingIndoor":"Tidak ada data","noRooms":"Belum ada ruangan","missingCard":"Air Quality Advisor · Buka","more":"Detail lainnya","less":"Lebih sedikit detail","weather":"Cuaca","warnings":"Peringatan cuaca","limits":"Batas","outdoorSensors":"Kualitas udara luar","noReadings":"Tidak ada data","missing":"Tidak tersedia","sensor":"Buka","partial":"Tidak tersedia","wind":"Cuaca","humidity":"RH","unavailableWeather":"Tidak tersedia","noOutdoor":"0 · Kualitas udara luar","warningActive":"Peringatan cuaca","warningUnknown":"Peringatan cuaca","allOkay":"Baik","indoorHigh":"Perlu perhatian","notSafeToOpen":"Biarkan jendela tertutup","conditions":"Di luar","measured":"Buka","activeWindows":"Terbuka","action":"Pengumuman (opsional)","noAttention":"Baik","metric_humidity":"RH","sourceData":"Home Assistant · Buka","allSafe":"Baik","warningReason":"Peringatan cuaca","unsafeReason":"Biarkan jendela tertutup","noWeather":"Tidak tersedia"},"vi":{"title":"Chất lượng không khí","subtitle":"Chất lượng không khí","outside":"Ngoài trời","goodOutside":"Phù hợp để thông gió","badOutside":"Giữ cửa sổ đóng","missingOutside":"Không khả dụng","partialOutside":"Không khả dụng","roomStatus":"Phòng","safe":"Tốt","attention":"Cần chú ý","unknown":"Không có dữ liệu","readings":"Mở","windows":"Đo lường","windowOpen":"Mở","windowClosed":"Đóng","windowUnknown":"Không có dữ liệu","open":"Đóng","close":"Thông báo tự động","openAdvice":"Đóng · Đo lường","closeAdvice":"Thông báo tự động · Đo lường","blocked":"Giữ cửa sổ đóng","ventilating":"Đang thông gió","noWindows":"0 · Đo lường","missingIndoor":"Không có dữ liệu","noRooms":"Chưa cấu hình phòng","missingCard":"Air Quality Advisor · Mở","more":"Chi tiết thêm","less":"Ít chi tiết hơn","weather":"Thời tiết","warnings":"Cảnh báo thời tiết","limits":"Ngưỡng","outdoorSensors":"Chất lượng không khí ngoài trời","noReadings":"Không có dữ liệu","missing":"Không khả dụng","sensor":"Mở","partial":"Không khả dụng","wind":"Thời tiết","humidity":"RH","unavailableWeather":"Không khả dụng","noOutdoor":"0 · Chất lượng không khí ngoài trời","warningActive":"Cảnh báo thời tiết","warningUnknown":"Cảnh báo thời tiết","allOkay":"Tốt","indoorHigh":"Cần chú ý","notSafeToOpen":"Giữ cửa sổ đóng","conditions":"Ngoài trời","measured":"Mở","activeWindows":"Mở","action":"Thông báo (tùy chọn)","noAttention":"Tốt","metric_humidity":"RH","sourceData":"Home Assistant · Mở","allSafe":"Tốt","warningReason":"Cảnh báo thời tiết","unsafeReason":"Giữ cửa sổ đóng","noWeather":"Không khả dụng"},"th":{"title":"คุณภาพอากาศ","subtitle":"คุณภาพอากาศ","outside":"ภายนอก","goodOutside":"เหมาะสำหรับการระบายอากาศ","badOutside":"ปิดหน้าต่างไว้","missingOutside":"ไม่พร้อมใช้งาน","partialOutside":"ไม่พร้อมใช้งาน","roomStatus":"ห้อง","safe":"ดี","attention":"ต้องตรวจสอบ","unknown":"ไม่มีข้อมูล","readings":"เปิด","windows":"ค่าที่วัด","windowOpen":"เปิด","windowClosed":"ปิด","windowUnknown":"ไม่มีข้อมูล","open":"ปิด","close":"การแจ้งเตือนอัตโนมัติ","openAdvice":"ปิด · ค่าที่วัด","closeAdvice":"การแจ้งเตือนอัตโนมัติ · ค่าที่วัด","blocked":"ปิดหน้าต่างไว้","ventilating":"กำลังระบายอากาศ","noWindows":"0 · ค่าที่วัด","missingIndoor":"ไม่มีข้อมูล","noRooms":"ยังไม่ได้ตั้งค่าห้อง","missingCard":"Air Quality Advisor · เปิด","more":"รายละเอียดเพิ่มเติม","less":"รายละเอียดน้อยลง","weather":"สภาพอากาศ","warnings":"คำเตือนสภาพอากาศ","limits":"ค่าขีดจำกัด","outdoorSensors":"คุณภาพอากาศภายนอก","noReadings":"ไม่มีข้อมูล","missing":"ไม่พร้อมใช้งาน","sensor":"เปิด","partial":"ไม่พร้อมใช้งาน","wind":"สภาพอากาศ","humidity":"RH","unavailableWeather":"ไม่พร้อมใช้งาน","noOutdoor":"0 · คุณภาพอากาศภายนอก","warningActive":"คำเตือนสภาพอากาศ","warningUnknown":"คำเตือนสภาพอากาศ","allOkay":"ดี","indoorHigh":"ต้องตรวจสอบ","notSafeToOpen":"ปิดหน้าต่างไว้","conditions":"ภายนอก","measured":"เปิด","activeWindows":"เปิด","action":"การประกาศ (ไม่บังคับ)","noAttention":"ดี","metric_humidity":"RH","sourceData":"Home Assistant · เปิด","allSafe":"ดี","warningReason":"คำเตือนสภาพอากาศ","unsafeReason":"ปิดหน้าต่างไว้","noWeather":"ไม่พร้อมใช้งาน"},"hi":{"title":"वायु गुणवत्ता","subtitle":"वायु गुणवत्ता","outside":"बाहर","goodOutside":"हवादारी के लिए अनुकूल","badOutside":"खिड़कियाँ बंद रखें","missingOutside":"अनुपलब्ध","partialOutside":"अनुपलब्ध","roomStatus":"कमरे","safe":"अच्छी","attention":"ध्यान आवश्यक","unknown":"कोई डेटा नहीं","readings":"खोलें","windows":"माप","windowOpen":"खुली","windowClosed":"बंद","windowUnknown":"कोई डेटा नहीं","open":"बंद करें","close":"स्वचालित सूचनाएँ","openAdvice":"बंद करें · माप","closeAdvice":"स्वचालित सूचनाएँ · माप","blocked":"खिड़कियाँ बंद रखें","ventilating":"हवादारी जारी","noWindows":"0 · माप","missingIndoor":"कोई डेटा नहीं","noRooms":"कोई कमरा नहीं चुना","missingCard":"Air Quality Advisor · खोलें","more":"और जानकारी","less":"कम जानकारी","weather":"मौसम","warnings":"मौसम चेतावनियाँ","limits":"सीमा","outdoorSensors":"बाहरी वायु गुणवत्ता","noReadings":"कोई डेटा नहीं","missing":"अनुपलब्ध","sensor":"खोलें","partial":"अनुपलब्ध","wind":"मौसम","humidity":"RH","unavailableWeather":"अनुपलब्ध","noOutdoor":"0 · बाहरी वायु गुणवत्ता","warningActive":"मौसम चेतावनियाँ","warningUnknown":"मौसम चेतावनियाँ","allOkay":"अच्छी","indoorHigh":"ध्यान आवश्यक","notSafeToOpen":"खिड़कियाँ बंद रखें","conditions":"बाहर","measured":"खोलें","activeWindows":"खुली","action":"घोषणाएँ (वैकल्पिक)","noAttention":"अच्छी","metric_humidity":"RH","sourceData":"Home Assistant · खोलें","allSafe":"अच्छी","warningReason":"मौसम चेतावनियाँ","unsafeReason":"खिड़कियाँ बंद रखें","noWeather":"अनुपलब्ध"},"zh-hans":{"title":"空气质量","subtitle":"空气质量","outside":"室外","goodOutside":"适合通风","badOutside":"请保持窗户关闭","missingOutside":"不可用","partialOutside":"不可用","roomStatus":"房间","safe":"良好","attention":"需要关注","unknown":"无数据","readings":"打开","windows":"测量值","windowOpen":"已打开","windowClosed":"已关闭","windowUnknown":"无数据","open":"关闭","close":"自动通知","openAdvice":"关闭 · 测量值","closeAdvice":"自动通知 · 测量值","blocked":"请保持窗户关闭","ventilating":"正在通风","noWindows":"0 · 测量值","missingIndoor":"无数据","noRooms":"尚未配置房间","missingCard":"Air Quality Advisor · 打开","more":"更多详情","less":"收起详情","weather":"天气","warnings":"天气预警","limits":"阈值","outdoorSensors":"室外空气质量","noReadings":"无数据","missing":"不可用","sensor":"打开","partial":"不可用","wind":"天气","humidity":"RH","unavailableWeather":"不可用","noOutdoor":"0 · 室外空气质量","warningActive":"天气预警","warningUnknown":"天气预警","allOkay":"良好","indoorHigh":"需要关注","notSafeToOpen":"请保持窗户关闭","conditions":"室外","measured":"打开","activeWindows":"已打开","action":"播报（可选）","noAttention":"良好","metric_humidity":"RH","sourceData":"Home Assistant · 打开","allSafe":"良好","warningReason":"天气预警","unsafeReason":"请保持窗户关闭","noWeather":"不可用"},"zh-hant":{"title":"空氣品質","subtitle":"空氣品質","outside":"室外","goodOutside":"適合通風","badOutside":"請保持窗戶關閉","missingOutside":"無法使用","partialOutside":"無法使用","roomStatus":"房間","safe":"良好","attention":"需要注意","unknown":"無資料","readings":"開啟","windows":"測量值","windowOpen":"已開啟","windowClosed":"已關閉","windowUnknown":"無資料","open":"關閉","close":"自動通知","openAdvice":"關閉 · 測量值","closeAdvice":"自動通知 · 測量值","blocked":"請保持窗戶關閉","ventilating":"正在通風","noWindows":"0 · 測量值","missingIndoor":"無資料","noRooms":"尚未設定房間","missingCard":"Air Quality Advisor · 開啟","more":"更多詳情","less":"收起詳情","weather":"天氣","warnings":"天氣警報","limits":"閾值","outdoorSensors":"室外空氣品質","noReadings":"無資料","missing":"無法使用","sensor":"開啟","partial":"無法使用","wind":"天氣","humidity":"RH","unavailableWeather":"無法使用","noOutdoor":"0 · 室外空氣品質","warningActive":"天氣警報","warningUnknown":"天氣警報","allOkay":"良好","indoorHigh":"需要注意","notSafeToOpen":"請保持窗戶關閉","conditions":"室外","measured":"開啟","activeWindows":"已開啟","action":"播報（選用）","noAttention":"良好","metric_humidity":"RH","sourceData":"Home Assistant · 開啟","allSafe":"良好","warningReason":"天氣警報","unsafeReason":"請保持窗戶關閉","noWeather":"無法使用"},"ja":{"title":"空気質","subtitle":"空気質","outside":"屋外","goodOutside":"換気に適しています","badOutside":"窓を閉めてください","missingOutside":"利用不可","partialOutside":"利用不可","roomStatus":"部屋","safe":"良好","attention":"注意が必要","unknown":"データなし","readings":"開ける","windows":"測定値","windowOpen":"開","windowClosed":"閉","windowUnknown":"データなし","open":"閉める","close":"自動通知","openAdvice":"閉める · 測定値","closeAdvice":"自動通知 · 測定値","blocked":"窓を閉めてください","ventilating":"換気中","noWindows":"0 · 測定値","missingIndoor":"データなし","noRooms":"部屋が設定されていません","missingCard":"Air Quality Advisor · 開ける","more":"詳細を表示","less":"詳細を閉じる","weather":"天気","warnings":"気象警報","limits":"しきい値","outdoorSensors":"屋外の空気質","noReadings":"データなし","missing":"利用不可","sensor":"開ける","partial":"利用不可","wind":"天気","humidity":"RH","unavailableWeather":"利用不可","noOutdoor":"0 · 屋外の空気質","warningActive":"気象警報","warningUnknown":"気象警報","allOkay":"良好","indoorHigh":"注意が必要","notSafeToOpen":"窓を閉めてください","conditions":"屋外","measured":"開ける","activeWindows":"開","action":"通知（任意）","noAttention":"良好","metric_humidity":"RH","sourceData":"Home Assistant · 開ける","allSafe":"良好","warningReason":"気象警報","unsafeReason":"窓を閉めてください","noWeather":"利用不可"},"ko":{"title":"공기질","subtitle":"공기질","outside":"실외","goodOutside":"환기하기 좋음","badOutside":"창문을 닫아 두세요","missingOutside":"사용할 수 없음","partialOutside":"사용할 수 없음","roomStatus":"방","safe":"좋음","attention":"주의 필요","unknown":"데이터 없음","readings":"열기","windows":"측정값","windowOpen":"열림","windowClosed":"닫힘","windowUnknown":"데이터 없음","open":"닫기","close":"자동 알림","openAdvice":"닫기 · 측정값","closeAdvice":"자동 알림 · 측정값","blocked":"창문을 닫아 두세요","ventilating":"환기 중","noWindows":"0 · 측정값","missingIndoor":"데이터 없음","noRooms":"설정된 방 없음","missingCard":"Air Quality Advisor · 열기","more":"자세히 보기","less":"간단히 보기","weather":"날씨","warnings":"기상 경보","limits":"임계값","outdoorSensors":"실외 공기질","noReadings":"데이터 없음","missing":"사용할 수 없음","sensor":"열기","partial":"사용할 수 없음","wind":"날씨","humidity":"RH","unavailableWeather":"사용할 수 없음","noOutdoor":"0 · 실외 공기질","warningActive":"기상 경보","warningUnknown":"기상 경보","allOkay":"좋음","indoorHigh":"주의 필요","notSafeToOpen":"창문을 닫아 두세요","conditions":"실외","measured":"열기","activeWindows":"열림","action":"알림(선택 사항)","noAttention":"좋음","metric_humidity":"RH","sourceData":"Home Assistant · 열기","allSafe":"좋음","warningReason":"기상 경보","unsafeReason":"창문을 닫아 두세요","noWeather":"사용할 수 없음"},"ar":{"title":"جودة الهواء","subtitle":"جودة الهواء","outside":"الخارج","goodOutside":"مناسب للتهوية","badOutside":"أبقِ النوافذ مغلقة","missingOutside":"غير متوفر","partialOutside":"غير متوفر","roomStatus":"الغرف","safe":"جيدة","attention":"تحتاج إلى انتباه","unknown":"لا توجد بيانات","readings":"افتح","windows":"القياسات","windowOpen":"مفتوحة","windowClosed":"مغلقة","windowUnknown":"لا توجد بيانات","open":"أغلق","close":"إشعارات تلقائية","openAdvice":"أغلق · القياسات","closeAdvice":"إشعارات تلقائية · القياسات","blocked":"أبقِ النوافذ مغلقة","ventilating":"التهوية جارية","noWindows":"0 · القياسات","missingIndoor":"لا توجد بيانات","noRooms":"لم تُحدد غرف","missingCard":"Air Quality Advisor · افتح","more":"مزيد من التفاصيل","less":"تفاصيل أقل","weather":"الطقس","warnings":"تحذيرات الطقس","limits":"الحد","outdoorSensors":"جودة الهواء الخارجي","noReadings":"لا توجد بيانات","missing":"غير متوفر","sensor":"افتح","partial":"غير متوفر","wind":"الطقس","humidity":"RH","unavailableWeather":"غير متوفر","noOutdoor":"0 · جودة الهواء الخارجي","warningActive":"تحذيرات الطقس","warningUnknown":"تحذيرات الطقس","allOkay":"جيدة","indoorHigh":"تحتاج إلى انتباه","notSafeToOpen":"أبقِ النوافذ مغلقة","conditions":"الخارج","measured":"افتح","activeWindows":"مفتوحة","action":"الإعلانات (اختياري)","noAttention":"جيدة","metric_humidity":"RH","sourceData":"Home Assistant · افتح","allSafe":"جيدة","warningReason":"تحذيرات الطقس","unsafeReason":"أبقِ النوافذ مغلقة","noWeather":"غير متوفر"},"he":{"title":"איכות האוויר","subtitle":"איכות האוויר","outside":"בחוץ","goodOutside":"מתאים לאוורור","badOutside":"השאירו חלונות סגורים","missingOutside":"לא זמין","partialOutside":"לא זמין","roomStatus":"חדרים","safe":"טובה","attention":"דורשת טיפול","unknown":"אין נתונים","readings":"פתחו","windows":"מדידות","windowOpen":"פתוח","windowClosed":"סגור","windowUnknown":"אין נתונים","open":"סגרו","close":"התראות אוטומטיות","openAdvice":"סגרו · מדידות","closeAdvice":"התראות אוטומטיות · מדידות","blocked":"השאירו חלונות סגורים","ventilating":"מתאוורר","noWindows":"0 · מדידות","missingIndoor":"אין נתונים","noRooms":"לא הוגדרו חדרים","missingCard":"Air Quality Advisor · פתחו","more":"פרטים נוספים","less":"פחות פרטים","weather":"מזג אוויר","warnings":"אזהרות מזג אוויר","limits":"סף","outdoorSensors":"איכות האוויר בחוץ","noReadings":"אין נתונים","missing":"לא זמין","sensor":"פתחו","partial":"לא זמין","wind":"מזג אוויר","humidity":"RH","unavailableWeather":"לא זמין","noOutdoor":"0 · איכות האוויר בחוץ","warningActive":"אזהרות מזג אוויר","warningUnknown":"אזהרות מזג אוויר","allOkay":"טובה","indoorHigh":"דורשת טיפול","notSafeToOpen":"השאירו חלונות סגורים","conditions":"בחוץ","measured":"פתחו","activeWindows":"פתוח","action":"הודעות (אופציונלי)","noAttention":"טובה","metric_humidity":"RH","sourceData":"Home Assistant · פתחו","allSafe":"טובה","warningReason":"אזהרות מזג אוויר","unsafeReason":"השאירו חלונות סגורים","noWeather":"לא זמין"},"fa":{"title":"کیفیت هوا","subtitle":"کیفیت هوا","outside":"بیرون","goodOutside":"مناسب تهویه","badOutside":"پنجره‌ها را بسته نگه دارید","missingOutside":"در دسترس نیست","partialOutside":"در دسترس نیست","roomStatus":"اتاق‌ها","safe":"خوب","attention":"نیازمند توجه","unknown":"بدون داده","readings":"باز کنید","windows":"اندازه‌گیری‌ها","windowOpen":"باز","windowClosed":"بسته","windowUnknown":"بدون داده","open":"ببندید","close":"اعلان‌های خودکار","openAdvice":"ببندید · اندازه‌گیری‌ها","closeAdvice":"اعلان‌های خودکار · اندازه‌گیری‌ها","blocked":"پنجره‌ها را بسته نگه دارید","ventilating":"در حال تهویه","noWindows":"0 · اندازه‌گیری‌ها","missingIndoor":"بدون داده","noRooms":"اتاقی تنظیم نشده است","missingCard":"Air Quality Advisor · باز کنید","more":"جزئیات بیشتر","less":"جزئیات کمتر","weather":"آب‌وهوا","warnings":"هشدارهای آب‌وهوا","limits":"آستانه","outdoorSensors":"کیفیت هوای بیرون","noReadings":"بدون داده","missing":"در دسترس نیست","sensor":"باز کنید","partial":"در دسترس نیست","wind":"آب‌وهوا","humidity":"RH","unavailableWeather":"در دسترس نیست","noOutdoor":"0 · کیفیت هوای بیرون","warningActive":"هشدارهای آب‌وهوا","warningUnknown":"هشدارهای آب‌وهوا","allOkay":"خوب","indoorHigh":"نیازمند توجه","notSafeToOpen":"پنجره‌ها را بسته نگه دارید","conditions":"بیرون","measured":"باز کنید","activeWindows":"باز","action":"اعلان‌ها (اختیاری)","noAttention":"خوب","metric_humidity":"RH","sourceData":"Home Assistant · باز کنید","allSafe":"خوب","warningReason":"هشدارهای آب‌وهوا","unsafeReason":"پنجره‌ها را بسته نگه دارید","noWeather":"در دسترس نیست"},"bn":{"title":"বায়ুর মান","subtitle":"বায়ুর মান","outside":"বাইরে","goodOutside":"বায়ু চলাচলের উপযোগী","badOutside":"জানালা বন্ধ রাখুন","missingOutside":"পাওয়া যাচ্ছে না","partialOutside":"পাওয়া যাচ্ছে না","roomStatus":"কক্ষ","safe":"ভালো","attention":"নজর দেওয়া দরকার","unknown":"তথ্য নেই","readings":"খুলুন","windows":"পরিমাপ","windowOpen":"খোলা","windowClosed":"বন্ধ","windowUnknown":"তথ্য নেই","open":"বন্ধ করুন","close":"স্বয়ংক্রিয় বিজ্ঞপ্তি","openAdvice":"বন্ধ করুন · পরিমাপ","closeAdvice":"স্বয়ংক্রিয় বিজ্ঞপ্তি · পরিমাপ","blocked":"জানালা বন্ধ রাখুন","ventilating":"বায়ু চলাচল করছে","noWindows":"0 · পরিমাপ","missingIndoor":"তথ্য নেই","noRooms":"কোনো কক্ষ সেট করা নেই","missingCard":"Air Quality Advisor · খুলুন","more":"বিস্তারিত","less":"কম বিস্তারিত","weather":"আবহাওয়া","warnings":"আবহাওয়ার সতর্কতা","limits":"সীমা","outdoorSensors":"বাইরের বায়ুর মান","noReadings":"তথ্য নেই","missing":"পাওয়া যাচ্ছে না","sensor":"খুলুন","partial":"পাওয়া যাচ্ছে না","wind":"আবহাওয়া","humidity":"RH","unavailableWeather":"পাওয়া যাচ্ছে না","noOutdoor":"0 · বাইরের বায়ুর মান","warningActive":"আবহাওয়ার সতর্কতা","warningUnknown":"আবহাওয়ার সতর্কতা","allOkay":"ভালো","indoorHigh":"নজর দেওয়া দরকার","notSafeToOpen":"জানালা বন্ধ রাখুন","conditions":"বাইরে","measured":"খুলুন","activeWindows":"খোলা","action":"ঘোষণা (ঐচ্ছিক)","noAttention":"ভালো","metric_humidity":"RH","sourceData":"Home Assistant · খুলুন","allSafe":"ভালো","warningReason":"আবহাওয়ার সতর্কতা","unsafeReason":"জানালা বন্ধ রাখুন","noWeather":"পাওয়া যাচ্ছে না"},"ur":{"title":"ہوا کا معیار","subtitle":"ہوا کا معیار","outside":"باہر","goodOutside":"ہواداری کے لیے مناسب","badOutside":"کھڑکیاں بند رکھیں","missingOutside":"دستیاب نہیں","partialOutside":"دستیاب نہیں","roomStatus":"کمرے","safe":"اچھا","attention":"توجہ درکار","unknown":"کوئی ڈیٹا نہیں","readings":"کھولیں","windows":"پیمائشیں","windowOpen":"کھلی","windowClosed":"بند","windowUnknown":"کوئی ڈیٹا نہیں","open":"بند کریں","close":"خودکار اطلاعات","openAdvice":"بند کریں · پیمائشیں","closeAdvice":"خودکار اطلاعات · پیمائشیں","blocked":"کھڑکیاں بند رکھیں","ventilating":"ہواداری جاری","noWindows":"0 · پیمائشیں","missingIndoor":"کوئی ڈیٹا نہیں","noRooms":"کوئی کمرہ منتخب نہیں","missingCard":"Air Quality Advisor · کھولیں","more":"مزید تفصیلات","less":"کم تفصیلات","weather":"موسم","warnings":"موسم کی تنبیہات","limits":"حد","outdoorSensors":"بیرونی ہوا کا معیار","noReadings":"کوئی ڈیٹا نہیں","missing":"دستیاب نہیں","sensor":"کھولیں","partial":"دستیاب نہیں","wind":"موسم","humidity":"RH","unavailableWeather":"دستیاب نہیں","noOutdoor":"0 · بیرونی ہوا کا معیار","warningActive":"موسم کی تنبیہات","warningUnknown":"موسم کی تنبیہات","allOkay":"اچھا","indoorHigh":"توجہ درکار","notSafeToOpen":"کھڑکیاں بند رکھیں","conditions":"باہر","measured":"کھولیں","activeWindows":"کھلی","action":"اعلانات (اختیاری)","noAttention":"اچھا","metric_humidity":"RH","sourceData":"Home Assistant · کھولیں","allSafe":"اچھا","warningReason":"موسم کی تنبیہات","unsafeReason":"کھڑکیاں بند رکھیں","noWeather":"دستیاب نہیں"},"ta":{"title":"காற்றுத் தரம்","subtitle":"காற்றுத் தரம்","outside":"வெளியே","goodOutside":"காற்றோட்டத்திற்கு ஏற்றது","badOutside":"சாளரங்களை மூடி வைக்கவும்","missingOutside":"கிடைக்கவில்லை","partialOutside":"கிடைக்கவில்லை","roomStatus":"அறைகள்","safe":"நன்று","attention":"கவனம் தேவை","unknown":"தரவு இல்லை","readings":"திறக்கவும்","windows":"அளவீடுகள்","windowOpen":"திறந்தது","windowClosed":"மூடியது","windowUnknown":"தரவு இல்லை","open":"மூடவும்","close":"தானியங்கி அறிவிப்புகள்","openAdvice":"மூடவும் · அளவீடுகள்","closeAdvice":"தானியங்கி அறிவிப்புகள் · அளவீடுகள்","blocked":"சாளரங்களை மூடி வைக்கவும்","ventilating":"காற்றோட்டம் நடைபெறுகிறது","noWindows":"0 · அளவீடுகள்","missingIndoor":"தரவு இல்லை","noRooms":"அறைகள் அமைக்கப்படவில்லை","missingCard":"Air Quality Advisor · திறக்கவும்","more":"மேலும் விவரங்கள்","less":"குறைந்த விவரங்கள்","weather":"வானிலை","warnings":"வானிலை எச்சரிக்கைகள்","limits":"வரம்பு","outdoorSensors":"வெளிப்புறக் காற்றுத் தரம்","noReadings":"தரவு இல்லை","missing":"கிடைக்கவில்லை","sensor":"திறக்கவும்","partial":"கிடைக்கவில்லை","wind":"வானிலை","humidity":"RH","unavailableWeather":"கிடைக்கவில்லை","noOutdoor":"0 · வெளிப்புறக் காற்றுத் தரம்","warningActive":"வானிலை எச்சரிக்கைகள்","warningUnknown":"வானிலை எச்சரிக்கைகள்","allOkay":"நன்று","indoorHigh":"கவனம் தேவை","notSafeToOpen":"சாளரங்களை மூடி வைக்கவும்","conditions":"வெளியே","measured":"திறக்கவும்","activeWindows":"திறந்தது","action":"அறிவிப்புகள் (விருப்பம்)","noAttention":"நன்று","metric_humidity":"RH","sourceData":"Home Assistant · திறக்கவும்","allSafe":"நன்று","warningReason":"வானிலை எச்சரிக்கைகள்","unsafeReason":"சாளரங்களை மூடி வைக்கவும்","noWeather":"கிடைக்கவில்லை"}};
  for (const [locale, translated] of Object.entries(EXTRA_LANGUAGE)) {
    LANGUAGE[locale] = {...translated, ...(LANGUAGE[locale] || {})};
  }
  const MOLD_NAMES = {"en":"Mold indication","de":"Schimmelindikator","el":"Ένδειξη μούχλας","fr":"Indicateur de moisissure","es":"Indicador de moho","ar":"مؤشر العفن","bg":"Индикатор за мухъл","bn":"ছাঁচের সূচক","cs":"Indikátor plísní","da":"Skimmelindikator","fa":"شاخص کپک","fi":"Homeindikaattori","he":"מדד עובש","hi":"फफूंद संकेतक","hr":"Pokazatelj plijesni","hu":"Penészesedési mutató","id":"Indikator jamur","it":"Indicatore muffa","ja":"カビ指標","ko":"곰팡이 지표","nb":"Muggindikator","nl":"Schimmelindicator","pl":"Wskaźnik pleśni","pt":"Indicador de bolor","pt-br":"Indicador de mofo","ro":"Indicator de mucegai","ru":"Индикатор плесени","sk":"Indikátor plesní","sr":"Индикатор буђи","sv":"Mögelindikator","ta":"பூஞ்சை குறியீடு","th":"ตัวชี้วัดเชื้อรา","tr":"Küf göstergesi","uk":"Індикатор цвілі","ur":"پھپھوندی کی نشاندہی","vi":"Chỉ số nấm mốc","zh-hans":"霉菌指标","zh-hant":"黴菌指標"};
  for (const [locale, name] of Object.entries(MOLD_NAMES)) {
    if (LANGUAGE[locale]) LANGUAGE[locale].metric_mold = name;
  }
  // Differentiate a never-calibrated room from temporarily unavailable
  // measurements. Keep these short status labels localized for every card UI.
  const MOLD_STATUS_TEXT = {"en":["Mold indicator not calibrated","Mold indicator data unavailable"],"de":["Schimmelindikator nicht kalibriert","Messdaten für Schimmelindikator fehlen"],"el":["Η ένδειξη μούχλας δεν έχει βαθμονομηθεί","Λείπουν δεδομένα για την ένδειξη μούχλας"],"fr":["Indicateur de moisissure non calibré","Données de moisissure indisponibles"],"es":["Indicador de moho sin calibrar","Faltan datos para el indicador de moho"],"ar":["مؤشر العفن غير معاير","بيانات مؤشر العفن غير متاحة"],"bg":["Индикаторът за мухъл не е калибриран","Липсват данни за индикатора за мухъл"],"bn":["ছাঁচের সূচক ক্যালিব্রেট করা হয়নি","ছাঁচের সূচকের তথ্য অনুপলব্ধ"],"cs":["Indikátor plísně není kalibrován","Chybí údaje pro indikátor plísně"],"da":["Skimmelindikator er ikke kalibreret","Data til skimmelindikator mangler"],"fa":["شاخص کپک کالیبره نشده است","داده‌های شاخص کپک در دسترس نیست"],"fi":["Homeindikaattoria ei ole kalibroitu","Homeindikaattorin tiedot puuttuvat"],"he":["מדד העובש לא כויל","חסרים נתונים למדד העובש"],"hi":["फफूंद संकेतक कैलिब्रेट नहीं है","फफूंद संकेतक का डेटा उपलब्ध नहीं"],"hr":["Pokazatelj plijesni nije kalibriran","Nedostaju podaci za pokazatelj plijesni"],"hu":["A penészmutató nincs kalibrálva","Hiányoznak a penészmutató adatai"],"id":["Indikator jamur belum dikalibrasi","Data indikator jamur tidak tersedia"],"it":["Indicatore muffa non calibrato","Dati dell'indicatore muffa non disponibili"],"ja":["カビ指標は未校正です","カビ指標のデータがありません"],"ko":["곰팡이 지표가 보정되지 않았습니다","곰팡이 지표 데이터가 없습니다"],"nb":["Muggindikator er ikke kalibrert","Data for muggindikatoren mangler"],"nl":["Schimmelindicator niet gekalibreerd","Gegevens voor schimmelindicator ontbreken"],"pl":["Wskaźnik pleśni nie został skalibrowany","Brak danych dla wskaźnika pleśni"],"pt":["Indicador de bolor não calibrado","Dados do indicador de bolor indisponíveis"],"pt-br":["Indicador de mofo não calibrado","Dados do indicador de mofo indisponíveis"],"ro":["Indicatorul de mucegai nu este calibrat","Lipsesc date pentru indicatorul de mucegai"],"ru":["Индикатор плесени не откалиброван","Нет данных для индикатора плесени"],"sk":["Indikátor plesní nie je kalibrovaný","Chýbajú údaje indikátora plesní"],"sr":["Индикатор буђи није калибрисан","Недостају подаци за индикатор буђи"],"sv":["Mögelindikatorn är inte kalibrerad","Data för mögelindikatorn saknas"],"ta":["பூஞ்சை குறியீடு அளவுத்திருத்தம் செய்யப்படவில்லை","பூஞ்சை குறியீட்டிற்கான தரவு இல்லை"],"th":["ยังไม่ได้ปรับเทียบตัวชี้วัดเชื้อรา","ไม่มีข้อมูลสำหรับตัวชี้วัดเชื้อรา"],"tr":["Küf göstergesi kalibre edilmedi","Küf göstergesi verileri eksik"],"uk":["Індикатор цвілі не відкалібровано","Немає даних для індикатора цвілі"],"ur":["پھپھوندی کے اشارے کی کیلیبریشن نہیں ہوئی","پھپھوندی کے اشارے کا ڈیٹا دستیاب نہیں"],"vi":["Chỉ số nấm mốc chưa được hiệu chuẩn","Thiếu dữ liệu chỉ số nấm mốc"],"zh-hans":["霉菌指标尚未校准","霉菌指标缺少数据"],"zh-hant":["黴菌指標尚未校準","黴菌指標缺少資料"]};
  for (const [locale, [needsCalibration, missingInputs]] of Object.entries(MOLD_STATUS_TEXT)) {
    if (LANGUAGE[locale]) {
      LANGUAGE[locale].moldNotCalibrated = needsCalibration;
      LANGUAGE[locale].moldInputsUnavailable = missingInputs;
    }
  }
  // Full guidance in the five main UI languages; other locales retain their
  // localized measurement names and show universally understood sensor units.
  const MOLD_INPUT_WARNING_LABELS = {"en":{"calibration":"Measure and save the coldest-surface temperature in Room settings","indoor_temperature":"Room temperature sensor has no valid reading","outdoor_temperature":"Selected weather entity has no usable outdoor temperature","humidity":"No valid nonzero room humidity readings available","calculation":"Mold estimate cannot be calculated from current values"},"de":{"calibration":"Temperatur der kältesten Oberfläche in den Raumeinstellungen messen und speichern","indoor_temperature":"Raumtemperatursensor liefert keinen gültigen Messwert","outdoor_temperature":"Ausgewählte Wetterentität liefert keine gültige Außentemperatur","humidity":"Keine gültigen Raumfeuchtewerte über 0 % verfügbar","calculation":"Schimmelindikator kann nicht berechnet werden"},"el":{"calibration":"Μέτρησε και αποθήκευσε τη θερμοκρασία της πιο κρύας επιφάνειας στις ρυθμίσεις χώρου","indoor_temperature":"Δεν υπάρχει έγκυρη μέτρηση θερμοκρασίας δωματίου","outdoor_temperature":"Η επιλεγμένη οντότητα καιρού δεν δίνει έγκυρη εξωτερική θερμοκρασία","humidity":"Δεν υπάρχουν έγκυρες μετρήσεις υγρασίας δωματίου πάνω από 0%","calculation":"Δεν είναι δυνατός ο υπολογισμός της ένδειξης μούχλας"},"fr":{"calibration":"Mesurez et enregistrez la température du point le plus froid dans les paramètres de la pièce","indoor_temperature":"Aucune température intérieure valide n'est disponible","outdoor_temperature":"L'entité météo choisie ne fournit pas de température extérieure valide","humidity":"Aucune humidité ambiante valide supérieure à 0 % disponible","calculation":"Impossible de calculer l'indicateur de moisissure"},"es":{"calibration":"Mide y guarda la temperatura de la superficie más fría en la configuración de la habitación","indoor_temperature":"No hay una lectura válida de temperatura interior","outdoor_temperature":"La entidad meteorológica seleccionada no proporciona temperatura exterior válida","humidity":"No hay humedad interior válida superior al 0 % disponible","calculation":"No se puede calcular el indicador de moho"}};

  // Home Assistant translates enum sensor states using the same keys. Keep
  // short independent fallbacks for cards opened before the locale loads.
  // New/unknown codes are still shown as words, never internal snake_case.
  const CONTROLLER_STATUS_FALLBACK = {
    en: {
      startup_warmup:'Waiting for startup checks to finish',
      pid_output_inactive:'PID demand is present, but the output is off',
      within_target_band:'Within the configured target range',
      sleep_room_evidence_unknown:'Cannot verify whether this room is sleeping',
      minimum_off_hold:'Waiting for the minimum safe OFF time',
      minimum_on_hold:'Waiting for the minimum safe ON time',
      paused:'Automatic control is paused',
      controlling:'Automatic control is active',
      unrecognized_status:'Unknown controller state; see status_code',
    },
    de: {
      startup_warmup:'Warte auf Abschluss der Startprüfung',
      pid_output_inactive:'PID-Anforderung vorhanden, Ausgang derzeit ausgeschaltet',
      within_target_band:'Innerhalb des eingestellten Zielbereichs',
      sleep_room_evidence_unknown:'Schlafstatus dieses Raums ist unklar',
      minimum_off_hold:'Warte auf sichere Mindest-Ausschaltzeit',
      minimum_on_hold:'Warte auf sichere Mindestlaufzeit',
      paused:'Automatische Regelung ist pausiert',
      controlling:'Automatische Regelung ist aktiv',
      unrecognized_status:'Unbekannter Reglerzustand; status_code prüfen',
    },
    el: {
      startup_warmup:'Αναμονή ολοκλήρωσης ελέγχων εκκίνησης',
      pid_output_inactive:'Το PID ζητά λειτουργία, αλλά η έξοδος είναι κλειστή',
      within_target_band:'Εντός του καθορισμένου εύρους στόχου',
      sleep_room_evidence_unknown:'Άγνωστη κατάσταση ύπνου δωματίου',
      minimum_off_hold:'Αναμονή ελάχιστου χρόνου εκτός λειτουργίας',
      minimum_on_hold:'Αναμονή ελάχιστου χρόνου λειτουργίας',
      paused:'Η αυτόματη λειτουργία έχει τεθεί σε παύση',
      controlling:'Η αυτόματη ρύθμιση λειτουργεί',
      unrecognized_status:'Άγνωστη κατάσταση ελεγκτή· έλεγξε το status_code',
    },
  };
  const RTL_LANGUAGES = new Set(['ar', 'he', 'fa', 'ur']);
  function cardLanguage(code) {
    const tag = String(code || 'en').replaceAll('_','-').toLowerCase();
    if (LANGUAGE[tag]) return tag;
    if (tag.startsWith('zh')) return /hant|-(tw|hk|mo)/.test(tag) ? 'zh-hant' : 'zh-hans';
    if (tag.startsWith('pt-')) return tag === 'pt-br' ? 'pt-br' : 'pt';
    const root = tag.split('-')[0];
    if (root === 'no') return 'nb';
    return LANGUAGE[root] ? root : 'en';
  }

  const ICON = {
    safe:'mdi:check-circle-outline', attention:'mdi:alert-circle-outline', unknown:'mdi:help-circle-outline',
    partial:'mdi:information-outline', unsafe:'mdi:weather-windy',
    sunny:'mdi:weather-sunny', 'clear-night':'mdi:weather-night',
    partlycloudy:'mdi:weather-partly-cloudy', cloudy:'mdi:weather-cloudy',
    rainy:'mdi:weather-rainy', pouring:'mdi:weather-pouring',
    'lightning-rainy':'mdi:weather-lightning-rainy', lightning:'mdi:weather-lightning',
    fog:'mdi:weather-fog', snowy:'mdi:weather-snowy', windy:'mdi:weather-windy',
    'windy-variant':'mdi:weather-windy-variant', exceptional:'mdi:alert-octagon-outline',
    hail:'mdi:weather-hail', snowyrainy:'mdi:weather-snowy-rainy'
  };
  const METRIC_ICON = { co2:'mdi:molecule-co2', aqi:'mdi:air-filter', pm25:'mdi:blur',
    pm10:'mdi:blur', voc:'mdi:flask-outline', voc_parts:'mdi:flask-outline',
    illuminance:'mdi:brightness-5', humidity:'mdi:water-percent', mold:'mdi:water-alert-outline' };
  const RH_FALLBACK_TEXT = {"en":"RH fallback active","de":"RH-Ersatzwert aktiv","el":"Ενεργή εφεδρική χρήση σχετικής υγρασίας","fr":"Repli sur l’humidité relative actif","es":"Respaldo de humedad relativa activo","ar":"الاعتماد الاحتياطي على الرطوبة النسبية نشط","bg":"Активно заместване с относителна влажност","bn":"আপেক্ষিক আর্দ্রতার বিকল্প সক্রিয়","cs":"Aktivní náhradní relativní vlhkost","da":"RH-reservemåling aktiv","fa":"جایگزین رطوبت نسبی فعال است","fi":"Suhteellisen kosteuden varatila käytössä","he":"גיבוי לחות יחסית פעיל","hi":"सापेक्ष आर्द्रता का बैकअप सक्रिय","hr":"Aktivna zamjena relativnom vlagom","hu":"Relatív páratartalom tartalékmód aktív","id":"Cadangan kelembapan relatif aktif","it":"Fallback umidità relativa attivo","ja":"相対湿度の代替値を使用中","ko":"상대습도 대체값 사용 중","nb":"RH-reservemåling aktiv","nl":"RH-terugval actief","pl":"Aktywna rezerwowa wilgotność względna","pt":"Alternativa por humidade relativa ativa","pt-br":"Fallback de umidade relativa ativo","ro":"Mod de rezervă cu umiditate relativă activ","ru":"Используется резервная относительная влажность","sk":"Aktívna náhradná relatívna vlhkosť","sr":"Активна резервна релативна влажност","sv":"Reservvärde för relativ luftfuktighet aktivt","ta":"ஒப்பீட்டு ஈரப்பத மாற்று செயலில் உள்ளது","th":"ใช้ค่าความชื้นสัมพัทธ์สำรอง","tr":"Bağıl nem yedek ölçümü etkin","uk":"Активна резервна відносна вологість","ur":"نسبتی نمی کی متبادل پیمائش فعال ہے","vi":"Đang dùng độ ẩm tương đối dự phòng","zh-hans":"已启用相对湿度回退","zh-hant":"已啟用相對濕度備援"};
  // Calibration and humidity summary labels in all 38 supported card locales.
  const MOLD_DETAIL_LABELS = {"en":["Average humidity","sensor","sensors","Estimated surface","Calibration factor","Indoor temperature","Outdoor temperature"],"de":["Durchschnittliche Luftfeuchte","Sensor","Sensoren","Geschätzte Oberflächentemperatur","Kalibrierfaktor","Raumtemperatur","Außentemperatur"],"el":["Μέση υγρασία","αισθητήρας","αισθητήρες","Εκτιμώμενη επιφάνεια","Συντελεστής βαθμονόμησης","Εσωτερική θερμοκρασία","Εξωτερική θερμοκρασία"],"fr":["Humidité moyenne","capteur","capteurs","Surface estimée","Facteur de calibration","Température intérieure","Température extérieure"],"es":["Humedad media","sensor","sensores","Superficie estimada","Factor de calibración","Temperatura interior","Temperatura exterior"],"ar":["متوسط الرطوبة","مستشعر","مستشعرات","السطح المقدّر","معامل المعايرة","درجة الحرارة الداخلية","درجة الحرارة الخارجية"],"bg":["Средна влажност","сензор","сензора","Оценена температура на повърхността","Калибрационен коефициент","Вътрешна температура","Външна температура"],"bn":["গড় আর্দ্রতা","সেন্সর","সেন্সর","আনুমানিক পৃষ্ঠের তাপমাত্রা","ক্রমাঙ্কন গুণক","ভেতরের তাপমাত্রা","বাইরের তাপমাত্রা"],"cs":["Průměrná vlhkost","senzor","senzory","Odhadovaná teplota povrchu","Kalibrační faktor","Vnitřní teplota","Venkovní teplota"],"da":["Gennemsnitlig luftfugtighed","sensor","sensorer","Estimeret overfladetemperatur","Kalibreringsfaktor","Indetemperatur","Udetemperatur"],"fa":["میانگین رطوبت","حسگر","حسگر","دمای تخمینی سطح","ضریب کالیبراسیون","دمای داخل","دمای بیرون"],"fi":["Keskimääräinen ilmankosteus","anturi","anturia","Arvioitu pintalämpötila","Kalibrointikerroin","Sisälämpötila","Ulkolämpötila"],"he":["לחות ממוצעת","חיישן","חיישנים","טמפרטורת משטח משוערת","מקדם כיול","טמפרטורה פנימית","טמפרטורה חיצונית"],"hi":["औसत आर्द्रता","सेंसर","सेंसर","अनुमानित सतह तापमान","अंशांकन गुणांक","अंदर का तापमान","बाहर का तापमान"],"hr":["Prosječna vlažnost","senzor","senzora","Procijenjena temperatura površine","Faktor kalibracije","Unutarnja temperatura","Vanjska temperatura"],"hu":["Átlagos páratartalom","érzékelő","érzékelő","Becsült felületi hőmérséklet","Kalibrációs tényező","Beltéri hőmérséklet","Kültéri hőmérséklet"],"id":["Kelembapan rata-rata","sensor","sensor","Perkiraan suhu permukaan","Faktor kalibrasi","Suhu dalam ruangan","Suhu luar ruangan"],"it":["Umidità media","sensore","sensori","Temperatura superficiale stimata","Fattore di calibrazione","Temperatura interna","Temperatura esterna"],"ja":["平均湿度","センサー","センサー","推定表面温度","校正係数","室内温度","屋外温度"],"ko":["평균 습도","센서","센서","예상 표면 온도","보정 계수","실내 온도","실외 온도"],"nb":["Gjennomsnittlig luftfuktighet","sensor","sensorer","Estimert overflatetemperatur","Kalibreringsfaktor","Innetemperatur","Utetemperatur"],"nl":["Gemiddelde luchtvochtigheid","sensor","sensoren","Geschatte oppervlaktetemperatuur","Kalibratiefactor","Binnentemperatuur","Buitentemperatuur"],"pl":["Średnia wilgotność","czujnik","czujniki","Szacowana temperatura powierzchni","Współczynnik kalibracji","Temperatura wewnętrzna","Temperatura zewnętrzna"],"pt":["Humidade média","sensor","sensores","Temperatura estimada da superfície","Fator de calibração","Temperatura interior","Temperatura exterior"],"pt-br":["Umidade média","sensor","sensores","Temperatura estimada da superfície","Fator de calibração","Temperatura interna","Temperatura externa"],"ro":["Umiditate medie","senzor","senzori","Temperatura estimată a suprafeței","Factor de calibrare","Temperatura interioară","Temperatura exterioară"],"ru":["Средняя влажность","датчик","датчика","Оценочная температура поверхности","Калибровочный коэффициент","Температура внутри","Температура снаружи"],"sk":["Priemerná vlhkosť","senzor","senzory","Odhadovaná teplota povrchu","Kalibračný faktor","Vnútorná teplota","Vonkajšia teplota"],"sr":["Просечна влажност","сензор","сензора","Процењена температура површине","Фактор калибрације","Унутрашња температура","Спољашња температура"],"sv":["Genomsnittlig luftfuktighet","sensor","sensorer","Uppskattad yttemperatur","Kalibreringsfaktor","Inomhustemperatur","Utomhustemperatur"],"ta":["சராசரி ஈரப்பதம்","சென்சார்","சென்சார்கள்","மதிப்பிடப்பட்ட மேற்பரப்பு வெப்பநிலை","அளவுத்திருத்த காரணி","உட்புற வெப்பநிலை","வெளிப்புற வெப்பநிலை"],"th":["ความชื้นเฉลี่ย","เซนเซอร์","เซนเซอร์","อุณหภูมิพื้นผิวโดยประมาณ","ค่าปรับเทียบ","อุณหภูมิภายใน","อุณหภูมิภายนอก"],"tr":["Ortalama nem","sensör","sensör","Tahmini yüzey sıcaklığı","Kalibrasyon katsayısı","İç sıcaklık","Dış sıcaklık"],"uk":["Середня вологість","датчик","датчики","Оцінена температура поверхні","Калібрувальний коефіцієнт","Температура всередині","Температура зовні"],"ur":["اوسط نمی","سینسر","سینسر","سطح کا اندازاً درجہ حرارت","کیلیبریشن عامل","اندرونی درجہ حرارت","بیرونی درجہ حرارت"],"vi":["Độ ẩm trung bình","cảm biến","cảm biến","Nhiệt độ bề mặt ước tính","Hệ số hiệu chuẩn","Nhiệt độ trong nhà","Nhiệt độ ngoài trời"],"zh-hans":["平均湿度","传感器","传感器","估算表面温度","校准系数","室内温度","室外温度"],"zh-hant":["平均濕度","感測器","感測器","估算表面溫度","校正係數","室內溫度","室外溫度"]};


  const CLIMATE_LABELS = {
    en:{title:'Climate',heat:'Heating target',cool:'Cooling target',occupied:'Occupied',
      unoccupied:'Unoccupied',away:'Away',sleep:'Sleep',home:'Home',
      holding:'Waiting for safe conditions',active:'Native thermostat control',
      advisory:'Planning only',pause:'Pause climate',resume:'Resume climate',
      mode:'Selected mode',target:'Active target',device:'Device',
      primary:'Primary HVAC',secondary:'Secondary HVAC',humidity:'Humidity control',humidityPower:'Humidity power',environmentActive:'Environment control active',
      selectedDevice:'Selected equipment',moistureAction:'Humidity decision',
      currentHumidity:'Measured RH',sourceStatus:'Sensor evidence',
      fan:'Fan-speed control',fanPower:'Fan power',dryFanAuto:'Commissioned DRY/FAN modes',extraction:'Ventilation/extraction',
      filtration:'Particle filtration',treatment:'Air treatment',
      manualDry:'Manual AC mode suggestion (no automatic switch)',
      windowHelp:'Open-window opportunity (advisory only)',
      priority:'Room priority',heldPurpose:'Held',
      co2Priority:'CO₂ ventilation',particlePriority:'Particle filtration',
      temperaturePriority:'Temperature comfort',humidityPriority:'Humidity',
      safetyPriority:'Safety interlock',noPriority:'No qualifying demand',
      environmentOnly:'Room monitoring; individual device controllers below',
      devices:'Managed climate devices',method:'Control method',
      manual:'Manual',automatic:'Automatic',pid:'PID',off:'Off',existing:'Native control',
      roomTemperature:'Room temperature',temperatureMissing:'No valid room temperature',
      manualTemperature:'Manual temperature target',manualHumidity:'Manual humidity target',
      save:'Save target',openEntity:'Open climate entity',
      invalidTarget:'Target invalid, unsupported or outside device limits.',
      editFailed:'Could not save the device settings.'},
    de:{title:'Klima',heat:'Heizsollwert',cool:'Kühlsollwert',occupied:'Belegt',
      unoccupied:'Unbelegt',away:'Abwesend',sleep:'Schlaf',home:'Zuhause',
      holding:'Wartet auf sichere Bedingungen',active:'Native Thermostatregelung',
      advisory:'Nur Planung',pause:'Klima pausieren',resume:'Klima fortsetzen',
      mode:'Aktueller Modus',target:'Aktives Ziel',device:'Gerät',
      primary:'Hauptthermostat',secondary:'Zweites Klimagerät',humidity:'Luftfeuchteregelung',humidityPower:'Be-/Entfeuchter schalten',environmentActive:'Umweltregelung aktiv',
      selectedDevice:'Ausgewähltes Gerät',moistureAction:'Feuchteentscheidung',
      currentHumidity:'Gemessene rF',sourceStatus:'Sensornachweis',
      fan:'Lüfter-Drehzahlregelung',fanPower:'Lüfter Ein/Aus',dryFanAuto:'Freigegebene DRY/FAN-Modi',extraction:'Lüftung / Abluft',
      filtration:'Partikelfiltration',treatment:'Luftbehandlung',
      manualDry:'Empfohlener Klimamodus (nur manuell, kein Umschalten)',
      windowHelp:'Fensterlüften als Alternative (nur Hinweis)',
      priority:'Raumpriorität',heldPurpose:'Gesperrt',
      co2Priority:'CO₂-Lüftung',particlePriority:'Partikelfiltration',
      temperaturePriority:'Temperaturkomfort',humidityPriority:'Luftfeuchtigkeit',
      safetyPriority:'Sicherheitssperre',noPriority:'Kein qualifizierter Bedarf',
      environmentOnly:'Raumüberwachung; einzelne Gerätesteuerungen unten',
      devices:'Verwaltete Klimageräte',method:'Regelungsart',
      manual:'Manuell',automatic:'Automatisch',pid:'PID',off:'Aus',existing:'Native Steuerung',
      roomTemperature:'Raumtemperatur',temperatureMissing:'Keine gültige Raumtemperatur',
      manualTemperature:'Manueller Temperatursollwert',manualHumidity:'Manueller Feuchtesollwert',
      save:'Ziel speichern',openEntity:'Klima-Entität öffnen',
      invalidTarget:'Sollwert ungültig, nicht unterstützt oder außerhalb der Gerätegrenzen.',
      editFailed:'Änderungen konnten nicht gespeichert werden.'},
    el:{title:'Κλίμα',heat:'Στόχος θέρμανσης',cool:'Στόχος ψύξης',occupied:'Παρουσία',
      unoccupied:'Κενό',away:'Απουσία',sleep:'Ύπνος',home:'Σπίτι',
      holding:'Αναμονή ασφαλών συνθηκών',active:'Έλεγχος θερμοστάτη',
      advisory:'Μόνο σχεδιασμός',pause:'Παύση κλίματος',resume:'Συνέχιση κλίματος',
      mode:'Λειτουργία',target:'Ενεργός στόχος',device:'Συσκευή',
      primary:'Κύριος θερμοστάτης',secondary:'Δεύτερη συσκευή κλίματος',humidity:'Ρύθμιση υγρασίας',humidityPower:'Έλεγχος ισχύος υγρασίας',environmentActive:'Ενεργή διαχείριση περιβάλλοντος',
      selectedDevice:'Επιλεγμένη συσκευή',moistureAction:'Απόφαση υγρασίας',
      currentHumidity:'Μετρημένη υγρασία',sourceStatus:'Ποιότητα μετρήσεων',
      fan:'Ρύθμιση ταχύτητας ανεμιστήρων',fanPower:'Ισχύς ανεμιστήρων',dryFanAuto:'Εγκεκριμένες λειτουργίες DRY/FAN',extraction:'Εξαερισμός / απαγωγή',
      filtration:'Φιλτράρισμα σωματιδίων',treatment:'Διαχείριση αέρα',
      manualDry:'Πρόταση χειροκίνητης λειτουργίας A/C (χωρίς αυτόματη αλλαγή)',
      windowHelp:'Πιθανή εξοικονόμηση με άνοιγμα παραθύρου (μόνο συμβουλή)',
      priority:'Προτεραιότητα δωματίου',heldPurpose:'Σε αναμονή',
      co2Priority:'Εξαερισμός CO₂',particlePriority:'Φιλτράρισμα σωματιδίων',
      temperaturePriority:'Θερμική άνεση',humidityPriority:'Υγρασία',
      safetyPriority:'Ασφάλεια',noPriority:'Καμία έγκυρη ανάγκη',
      environmentOnly:'Παρακολούθηση δωματίου· οι ελεγκτές συσκευών βρίσκονται παρακάτω',
      devices:'Ελεγκτές κλιματικών συσκευών',method:'Μέθοδος ελέγχου',
      manual:'Χειροκίνητος',automatic:'Αυτόματος',pid:'PID',off:'Κλειστό',existing:'Εγγενής έλεγχος',
      roomTemperature:'Θερμοκρασία δωματίου',temperatureMissing:'Δεν υπάρχει έγκυρη θερμοκρασία δωματίου',
      manualTemperature:'Χειροκίνητος στόχος θερμοκρασίας',manualHumidity:'Χειροκίνητος στόχος υγρασίας',
      save:'Αποθήκευση στόχου',openEntity:'Άνοιγμα οντότητας κλίματος',
      invalidTarget:'Μη έγκυρος ή μη υποστηριζόμενος στόχος ή εκτός ορίων συσκευής.',
      editFailed:'Αποτυχία αποθήκευσης ρυθμίσεων.'},
  };

  const PID_LABELS = {
    en:{title:'Climate PID',active:'Setpoint regulation active',paused:'Paused: manual action required',
        pending:'Waiting for safe conditions',effort:'PID effort',target:'Room target',requested:'Requested setpoint',
        pause:'Pause PID',resume:'Resume PID',caution:'Controls setpoint only; does not change HVAC mode.'},
    de:{title:'Klima-PID',active:'Sollwertregelung aktiv',paused:'Pausiert: manueller Eingriff nötig',
        pending:'Wartet auf sichere Bedingungen',effort:'PID-Ausgang',target:'Raumziel',requested:'Thermostat-Sollwert',
        pause:'PID pausieren',resume:'PID fortsetzen',caution:'Ändert nur den Sollwert, nicht den Heiz-/Kühlmodus.'},
    el:{title:'Κλιματικός PID',active:'Ενεργή ρύθμιση θερμοστάτη',paused:'Παύση: απαιτείται ενέργεια',
        pending:'Αναμονή ασφαλών συνθηκών',effort:'Έξοδος PID',target:'Στόχος δωματίου',requested:'Επιθυμητή θερμοκρασία',
        pause:'Παύση PID',resume:'Συνέχιση PID',caution:'Αλλάζει μόνο το setpoint, όχι τη λειτουργία HVAC.'},
    fr:{title:'PID climatique',active:'Réglage de consigne actif',paused:'En pause : action manuelle',
        pending:'En attente de conditions sûres',effort:'Effort PID',target:'Cible',requested:'Consigne demandée',
        pause:'Pause PID',resume:'Reprendre PID',caution:'Ne modifie que la consigne, jamais le mode HVAC.'},
    es:{title:'PID climático',active:'Regulación de consigna activa',paused:'Pausado: intervención manual',
        pending:'Esperando condiciones seguras',effort:'Esfuerzo PID',target:'Objetivo',requested:'Consigna solicitada',
        pause:'Pausar PID',resume:'Reanudar PID',caution:'Solo modifica la consigna; no cambia el modo HVAC.'},
  };

  const SCIENCE_LABELS = {
    en: {title:'Building physics · estimates',drying:'Outdoor air is drier',humidifying:'Outdoor air carries more moisture',
      neutral:'Similar moisture content',predicted:'Outside air, warmed to room temperature',
      band:'Adaptive comfort band',heat:'Above the comfort band',cool:'Below the comfort band',
      normal:'Within the comfort band',unknown:'Needs seven days of outdoor history',
      cooling:'Passive cooling opportunity',surface:'Surface condensation margin',
      exposure:'Surface humidity above 80% (24 h)',pm25:'PM2.5 mean (24 h)',
      pm10:'PM10 mean (24 h)',co2:'CO₂ trend',ach:'Estimated air changes',
      energy:'Heat per complete air exchange (per m³)',unverified:'CO₂ sensor technology must be verified separately',
      estimated:'Estimates depend on sensor accuracy and model assumptions.'},
    de: {title:'Bauphysik · Schätzwerte',drying:'Außenluft ist trockener',humidifying:'Außenluft enthält mehr Feuchtigkeit',
      neutral:'Ähnlicher Feuchtegehalt',predicted:'Außenluft auf Raumtemperatur erwärmt',
      band:'Adaptiver Komfortbereich',heat:'Oberhalb des Komfortbereichs',cool:'Unterhalb des Komfortbereichs',
      normal:'Im Komfortbereich',unknown:'Sieben Tage Außenverlauf erforderlich',
      cooling:'Passive Kühlung möglich',surface:'Abstand zur Kondensation an Oberfläche',
      exposure:'Oberflächenfeuchte über 80 % (24 h)',pm25:'PM2.5-Mittel (24 h)',
      pm10:'PM10-Mittel (24 h)',co2:'CO₂-Trend',ach:'Geschätzter Luftwechsel',
      energy:'Wärme pro vollständigem Luftaustausch (je m³)',unverified:'CO₂-Sensortechnik separat prüfen',
      estimated:'Schätzungen hängen von Sensoren und Modellannahmen ab.'},
    el: {title:'Φυσική κτιρίων · εκτιμήσεις',drying:'Ο εξωτερικός αέρας είναι ξηρότερος',humidifying:'Ο εξωτερικός αέρας έχει περισσότερη υγρασία',
      neutral:'Παρόμοια ποσότητα υγρασίας',predicted:'Εξωτερικός αέρας θερμασμένος στη θερμοκρασία δωματίου',
      band:'Προσαρμοστική ζώνη άνεσης',heat:'Πάνω από τη ζώνη άνεσης',cool:'Κάτω από τη ζώνη άνεσης',
      normal:'Εντός της ζώνης άνεσης',unknown:'Απαιτούνται 7 ημέρες εξωτερικών μετρήσεων',
      cooling:'Δυνατότητα παθητικής ψύξης',surface:'Περιθώριο συμπύκνωσης στην επιφάνεια',
      exposure:'Υγρασία επιφάνειας πάνω από 80% (24 ώρες)',pm25:'Μέσος όρος PM2.5 (24 ώρες)',
      pm10:'Μέσος όρος PM10 (24 ώρες)',co2:'Τάση CO₂',ach:'Εκτίμηση ανανεώσεων αέρα',
      energy:'Θερμότητα ανά πλήρη αλλαγή αέρα (ανά m³)',unverified:'Απαιτείται επαλήθευση του αισθητήρα CO₂',
      estimated:'Οι εκτιμήσεις εξαρτώνται από τους αισθητήρες και τις παραδοχές.'}
  };

  const EXTRA_LABELS = {
    en:{pollen:'Pollen forecast',pollenHigh:'High pollen',purification:'Purifier clean-air changes',
      measuredAch:'Measured ventilation trend',toTarget:'Estimated CO₂ target time',
      sourceMoisture:'Rapid humidity change',hcho:'Verified formaldehyde (30 min)',
      radon:'Radon annual average',noise:'Sound exposure (24 h)',nightNoise:'Nighttime sound',
      light:'Daylight above threshold',melanopic:'Sensor measured melanopic EDI',
      overheated:'Overheating degree-hours',pmv:'Thermal comfort PMV / PPD',
      particle:'Indoor / outdoor PM2.5 ratio',unknown:'History or validated hardware required',
      noActuation:'Informational only · PID climate control is planned, not active.'},
    de:{pollen:'Pollenprognose',pollenHigh:'Hohe Pollenbelastung',purification:'Partikel-Luftwechsel des Luftreinigers',
      measuredAch:'Beobachteter Lüftungstrend',toTarget:'Geschätzte CO₂-Zielzeit',
      sourceMoisture:'Schneller Feuchteanstieg',hcho:'Geprüftes Formaldehyd (30 min)',
      radon:'Radon-Jahresmittel',noise:'Schallbelastung (24 h)',nightNoise:'Schall im Schlafzimmer',
      light:'Tageslicht über Schwellenwert',melanopic:'Gemessene melanopische EDI',
      overheated:'Überhitzungsgradstunden',pmv:'Thermischer Komfort PMV / PPD',
      particle:'PM2.5-Verhältnis innen / außen',unknown:'Messhistorie oder Sensorprüfung fehlt',
      noActuation:'Nur Hinweise · PID-Klimaregelung ist geplant, noch nicht aktiv.'},
    el:{pollen:'Πρόγνωση γύρης',pollenHigh:'Υψηλή γύρη',purification:'Ανανεώσεις καθαρού αέρα φίλτρου',
      measuredAch:'Παρατηρούμενη τάση αερισμού',toTarget:'Εκτίμηση χρόνου στόχου CO₂',
      sourceMoisture:'Απότομη αύξηση υγρασίας',hcho:'Επαληθευμένη φορμαλδεΰδη (30 λεπτά)',
      radon:'Ετήσιος μέσος όρος ραδονίου',noise:'Θόρυβος (24 ώρες)',nightNoise:'Νυχτερινός θόρυβος',
      light:'Φως ημέρας πάνω από όριο',melanopic:'Μετρημένη μελανοπική EDI',
      overheated:'Βαθμοώρες υπερθέρμανσης',pmv:'Θερμική άνεση PMV / PPD',
      particle:'Αναλογία PM2.5 μέσα / έξω',unknown:'Απαιτείται ιστορικό ή επαλήθευση αισθητήρα',
      noActuation:'Μόνο πληροφορίες · Ο έλεγχος κλίματος PID είναι μελλοντική δυνατότητα.'}
  };

  const DEVICE_EDIT_LABELS = {
    en: {room:'Edit room',home:'Home settings'},
    el: {room:'Ρυθμίσεις χώρου',home:'Ρυθμίσεις σπιτιού'},
    de: {room:'Raum bearbeiten',home:'Hauseinstellungen'},
    fr: {room:'Modifier la pièce',home:'Paramètres du logement'},
    es: {room:'Editar habitación',home:'Ajustes de la vivienda'}
  };

  const ESC_MAP = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
  const escape = (s) => String(s ?? '').replace(/[&<>"']/g, (ch) => ESC_MAP[ch]);
  const clamp = (num,min,max) => Math.max(min, Math.min(max,num));
  const safeArray = (x) => Array.isArray(x) ? x : [];

  function detected(hass) {
    return Object.entries(hass?.states || {})
      .filter(([id, state]) => id.startsWith('sensor.') &&
        (state?.attributes?.dashboard?.version === 1 ||
         state?.attributes?.dashboard_api === 'environment_manager/dashboard'))
      .map(([id]) => id);
  }

  class AirQualityAdvisorCard extends HTMLElement {
    static getStubConfig(hass) {
      const matches = detected(hass);
      return matches.length === 1 ? {entity:matches[0]} : {};
    }

    constructor() {
      super();
      this.attachShadow({mode:'open'});
      this._config = {};
      this._expanded = new Set();
      this._calibrationExpanded65 = new Set();
      this.shadowRoot.addEventListener('toggle', (event)=>{
        const id=event.target?.getAttribute?.('data-calibration-id');
        if (!id || !event.target.isConnected) return;
        if (event.target.open) this._calibrationExpanded65.add(id);
        else this._calibrationExpanded65.delete(id);
      }, true);
      this._shownEntity = null;
      this._shownLanguage = null;
      this._shownControllerSignature = null;
      this._dashboardData = null;
      this._dashboardEntity = null;
      this._dashboardLoadedRevision = null;
      this._dashboardFetching = null;
      this._dashboardFailureCount = 0;
      this._dashboardNextAttemptAt = 0;
      this._climateEditError = null;
      this._lastState = null;
      this._lastConfigKey = null;
      this._areaDeviceIds = new Map();
      this._homeDeviceId = null;
      this._deviceRegistryLoading = null;
      this._deviceRegistryUnavailable = false;
      this._deviceRegistryLoaded = false;
      this._deviceRegistryFailureCount = 0;
      this._deviceRegistryNextAttemptAt = 0;
      this._focusedEditor = null;
      this._pendingRender = false;
      this._pendingForceRender = false;
      this._editRenderTimer = null;
      this._lastRenderError = null;
      this._hasValidRender = false;
      // A focused native select/input belongs to the user until they commit
      // or leave it; replacing shadowRoot.innerHTML while it is open closes
      // the browser's picker and discards any unfinished manual edit.
      this.shadowRoot.addEventListener('focusin', (event) => {
        const editor = event.target.closest?.('[data-climate-method],[data-climate-input],[data-pid-calibration-method],[data-pid-model-input],[data-pid-capacity-select],[data-pid-capacity-input]');
        if (!editor) return;
        this._focusedEditor = editor;
        if (this._editRenderTimer !== null) {
          clearTimeout(this._editRenderTimer);
          this._editRenderTimer = null;
        }
      });
      this.shadowRoot.addEventListener('pointerdown', (event) => {
        const editor = event.target.closest?.('[data-climate-method],[data-climate-input],[data-pid-calibration-method],[data-pid-model-input],[data-pid-capacity-select],[data-pid-capacity-input]');
        if (editor) this._focusedEditor = editor;
      });
      this.shadowRoot.addEventListener('focusout', (event) => {
        if (event.target !== this._focusedEditor) return;
        this._focusedEditor = null;
        // A click on Save follows input focusout. Defer the DOM replacement
        // until after click dispatch so its target is not removed beforehand.
        this._flushDeferredRenderSoon();
      });
      this.shadowRoot.addEventListener('click', (event) => {
        const edit = event.target.closest?.('[data-edit-area],[data-edit-home]');
        if (edit) {
          const area = edit.getAttribute('data-edit-area');
          const id = area === null ? this._homeDeviceId : this._areaDeviceIds.get(area);
          if (!id) return;
          const path = '/config/devices/device/' + encodeURIComponent(id);
          // HA's SPA device route; never build a link from the area name.
          if (window.history?.pushState && window.dispatchEvent) {
            window.history.pushState(null, '', path);
            window.dispatchEvent(new Event('location-changed'));
          } else if (window.location) {
            window.location.assign(path);
          }
          return;
        }
        const selectedCover = event.target.closest?.('[data-open-shade]');
        if (selectedCover) {
          const area=selectedCover.getAttribute('data-shade-area');
          const entityId=selectedCover.getAttribute('data-open-shade');
          const inRoom=safeArray(this._shadingEvidence(area)?.selected_covers).includes(entityId);
          if (inRoom && typeof entityId==='string' && entityId.startsWith('cover.')) {
            this.dispatchEvent(new CustomEvent('hass-more-info',{
              detail:{entityId},bubbles:true,composed:true,
            }));
          }
          return;
        }
        const shadeSwitch = event.target.closest?.('[data-shade-switch]');
        if (shadeSwitch && this._hass?.callService) {
          const area=shadeSwitch.getAttribute('data-shade-area');
          const entityId=shadeSwitch.getAttribute('data-shade-switch');
          const found=this._shadingSwitch(area);
          if (found?.id!==entityId) return;
          const service=found.state.state==='on'?'turn_off':'turn_on';
          Promise.resolve(this._hass.callService('switch',service,{
            entity_id:entityId,
          })).catch((error)=>console.warn('Home Environment Manager shade toggle failed',error));
          return;
        }
        const moreInfo = event.target.closest?.('[data-open-climate]');
        if (moreInfo) {
          const entityId = moreInfo.getAttribute('data-open-climate');
          const area = moreInfo.getAttribute('data-controller-area');
          if (this._managedControllers(area).some((item)=>item.entityId===entityId)) {
            this.dispatchEvent(new CustomEvent('hass-more-info', {
              detail:{entityId}, bubbles:true, composed:true
            }));
          }
          return;
        }
        const capacityInputSave = event.target.closest?.('[data-save-pid-capacity]');
        if (capacityInputSave && this._hass?.callService) {
          const area=capacityInputSave.getAttribute('data-controller-area');
          const entityId=capacityInputSave.getAttribute('data-save-pid-capacity');
          const field=capacityInputSave.getAttribute('data-pid-capacity-field');
          const parent=this._managedControllers(area).find((item)=>
            item.capacityNumbers?.some((row)=>
              row.id===entityId && row.field===field) && item.method?.state==='pid');
          const chosen=parent?.capacityNumbers.find((item)=>item.id===entityId);
          const input=capacityInputSave.closest('.climate-target-editor')
            ?.querySelector('input[data-pid-capacity-input]');
          const parsed=input ? Number(String(input.value).replace(',','.')) : NaN;
          const limits=chosen?.state.attributes || {};
          if (!parent || !input || !Number.isFinite(parsed) ||
              !Number.isFinite(Number(limits.min)) ||
              !Number.isFinite(Number(limits.max)) ||
              parsed < Number(limits.min) || parsed > Number(limits.max)) return;
          Promise.resolve(this._hass.callService('number','set_value',{
            entity_id:entityId,value:parsed
          })).catch((error)=>console.warn('PID fan capacity measurement rejected',error));
          return;
        }
        const capacityApply=event.target.closest?.('[data-apply-pid-fan-capacity]');
        if (capacityApply && this._hass?.callService) {
          const area=capacityApply.getAttribute('data-controller-area');
          const entityId=capacityApply.getAttribute('data-apply-pid-fan-capacity');
          const matched=this._managedControllers(area).find((item)=>
            item.capacityButtonId===entityId && item.method?.state==='pid' &&
            item.capacityDirection?.state!=='choose' &&
            item.climate?.attributes?.physical_source_state==='off');
          if (!matched) return;
          Promise.resolve(this._hass.callService('button','press',{
            entity_id:entityId
          })).catch((error)=>console.warn('Measured capacity not applied',error));
          return;
        }
        const pidSave = event.target.closest?.('[data-save-pid-model]');
        if (pidSave && this._hass?.callService) {
          const area=pidSave.getAttribute('data-controller-area');
          const entityId=pidSave.getAttribute('data-save-pid-model');
          const field=pidSave.getAttribute('data-pid-model-field');
          const linked=this._managedControllers(area).find((item)=>
            item.calibrationNumbers?.some((info)=>
              info.id===entityId && info.field===field));
          const input=pidSave.closest('.climate-target-editor')
            ?.querySelector('input[data-pid-model-input]');
          const parsed=input ? Number(String(input.value).replace(',','.')) : NaN;
          const record=linked?.calibrationNumbers?.find((item)=>item.id===entityId);
          const low=Number(record?.state?.attributes?.min);
          const high=Number(record?.state?.attributes?.max);
          if (!linked || !linked.calibrationSelect ||
              linked.method?.state!=='pid' ||
              linked.calibrationSelect.state==='manual' ||
              !Number.isFinite(parsed) || !Number.isFinite(low) ||
              !Number.isFinite(high) || parsed<low || parsed>high) return;
          Promise.resolve(this._hass.callService('number','set_value',{
            entity_id:entityId,value:parsed
          })).catch((error)=>console.warn('PID model input rejected',error));
          return;
        }
        const pidApply = event.target.closest?.('[data-apply-pid-calibration]');
        if (pidApply && this._hass?.callService) {
          const area=pidApply.getAttribute('data-controller-area');
          const entityId=pidApply.getAttribute('data-apply-pid-calibration');
          const linked=this._managedControllers(area).find((item)=>
            item.calibrationButtonId===entityId);
          if (!linked || linked.method?.state!=='pid' ||
              !linked.calibrationSelect ||
              linked.calibrationSelect.state==='manual' ||
              linked.climate?.state==='unavailable') return;
          // The server independently checks model validity and physical OFF;
          // this is a deliberate apply action, never automatic calibration.
          Promise.resolve(this._hass.callService('button','press',{entity_id:entityId}))
            .catch((error)=>console.warn('PID calibration not applied',error));
          return;
        }
        const targetSave = event.target.closest?.('[data-save-climate-target]');
        if (targetSave) {
          const area = targetSave.getAttribute('data-controller-area');
          const entityId = targetSave.getAttribute('data-save-climate-target');
          const metric = targetSave.getAttribute('data-target-metric');
          const controller = this._managedControllers(area).find(
            (entry)=>entry.entityId===entityId);
          const input = targetSave.closest('.climate-target-editor')
            ?.querySelector('input[data-climate-input]');
          const parsed = input ? Number(String(input.value).replace(',', '.')) : NaN;
          const boundaries = controller?.climate?.attributes || {};
          const nativeSupported = Number(boundaries.supported_features) || 0;
          const validMetric = metric==='temperature' ? Boolean(nativeSupported & 1)
            : metric==='humidity' && Boolean(nativeSupported & 4);
          const minimum = metric==='temperature'
            ? Number(boundaries.min_temp ?? 5) : Number(boundaries.min_humidity ?? 20);
          const maximum = metric==='temperature'
            ? Number(boundaries.max_temp ?? 35) : Number(boundaries.max_humidity ?? 80);
          if (!controller || controller.method?.state!=='manual' ||
              controller.climate?.state==='unavailable' || !validMetric ||
              !Number.isFinite(parsed) || !Number.isFinite(minimum) ||
              !Number.isFinite(maximum) || parsed<minimum || parsed>maximum) {
            this._climateEditError = (CLIMATE_LABELS[this._language()] ||
              CLIMATE_LABELS.en).invalidTarget;
            this._render(true);
            return;
          }
          const service = metric==='temperature' ? 'set_temperature' : 'set_humidity';
          this._climateEditError = null;
          Promise.resolve(this._hass.callService('climate',service,{
            entity_id:entityId,[metric]:parsed
          })).catch((error)=>{
            console.error('Home Environment Manager manual target failed',error);
            this._climateEditError = (CLIMATE_LABELS[this._language()] ||
              CLIMATE_LABELS.en).editFailed;
            this._render(true);
          });
          return;
        }
        const climate = event.target.closest?.('[data-climate-action]');
        if (climate) {
          const area = climate.getAttribute('data-climate-area');
          const action = climate.getAttribute('data-climate-action');
          if (area && ['pause','resume'].includes(action) && this._hass?.callService) {
            Promise.resolve(this._hass.callService('environment_manager','climate_control',{area,action}))
              .catch((error)=>console.error('Home Environment Manager climate action failed',error));
          }
          return;
        }
        const pid = event.target.closest?.('[data-pid-action]');
        if (pid) {
          const area = pid.getAttribute('data-pid-area');
          const action = pid.getAttribute('data-pid-action');
          if (area && ['pause','resume'].includes(action) && this._hass?.callService) {
            Promise.resolve(this._hass.callService('environment_manager','pid_control',{area,action}))
              .catch((error)=>console.error('Home Environment Manager PID action failed',error));
          }
          return;
        }
        const button = event.target.closest?.('[data-expand]');
        if (!button) return;
        const area = button.getAttribute('data-expand');
        if (this._expanded.has(area)) this._expanded.delete(area);
        else this._expanded.add(area);
        this._render(true);
      });
      this.shadowRoot.addEventListener('change', (event) => {
        const capacitySelection = event.target.closest?.('[data-pid-capacity-select]');
        const pidSelection = event.target.closest?.('[data-pid-calibration-method]');
        const selector = capacitySelection || pidSelection || event.target.closest?.('[data-climate-method]');
        if (!selector || !this._hass?.callService) return;
        const area = selector.getAttribute('data-controller-area');
        const entityId = selector.getAttribute(capacitySelection ?
          'data-pid-capacity-select' : pidSelection ?
          'data-pid-calibration-method' : 'data-climate-method');
        const current = this._managedControllers(area).find((item)=>
          capacitySelection ? item.method?.state==='pid' &&
            [item.capacityModeId,item.capacityDirectionId].includes(entityId) :
          pidSelection ? item.calibrationSelectId===entityId &&
            item.method?.state==='pid' : item.methodId===entityId);
        const value = selector.value;
        const chosenState=capacitySelection ?
          (entityId===current?.capacityModeId ? current.capacityMode
            : current?.capacityDirection) :
          pidSelection ? current?.calibrationSelect : current?.method;
        const choices = chosenState?.attributes?.options;
        if (!current || current.climate?.state==='unavailable' ||
            !Array.isArray(choices) || !choices.includes(value)) return;
        this._climateEditError = null;
        Promise.resolve(this._hass.callService('select','select_option',{
          entity_id:entityId,option:value
        })).catch((error)=>{
          console.error('Home Environment Manager controller selector failed',error);
          this._climateEditError = (CLIMATE_LABELS[this._language()] ||
            CLIMATE_LABELS.en).editFailed;
          this._render(true);
        });
        // A native change event commits the user's selected option. This is
        // the earliest safe point to let the Manual target editor appear.
        if (this._focusedEditor === selector) {
          this._focusedEditor = null;
          this._pendingRender = true;
          this._flushDeferredRenderSoon();
        }
      });
    }

    _flushDeferredRenderSoon() {
      if (this._editRenderTimer !== null) clearTimeout(this._editRenderTimer);
      this._editRenderTimer = setTimeout(() => {
        this._editRenderTimer = null;
        if (this._focusedEditor || !this._pendingRender) return;
        const forced = this._pendingForceRender;
        this._pendingRender = false;
        this._pendingForceRender = false;
        this._render(forced);
      }, 80);
    }

    disconnectedCallback() {
      if (this._editRenderTimer !== null) {
        clearTimeout(this._editRenderTimer);
        this._editRenderTimer = null;
      }
      this._focusedEditor = null;
      this._pendingRender = false;
      this._pendingForceRender = false;
    }

    setConfig(config) {
      if (config.entity && !/^sensor\.[a-z0-9_]+$/.test(config.entity)) {
        throw new Error('Home Environment Manager: entity must be a sensor.* entity ID');
      }
      this._config = {show_outside:true, show_metrics:true, show_science:true, ...config};
      this._lastConfigKey = null;
      this._loadDashboard();
      this._render(true);
    }

    set hass(hass) {
      this._hass = hass;
      this._loadDashboard();
      this._loadDeviceIds();
      this._render();
    }

    _loadDashboard() {
      // Recorder attributes deliberately contain only an API marker/revision.
      // Fetch the complete scientific and device data over authenticated WS.
      // Old in-memory dashboards remain displayable during a rolling upgrade.
      if (!this._hass?.callWS) return;
      const [entityId, state] = this._state();
      const attrs = state?.attributes || {};
      if (!entityId || attrs.dashboard_api !== 'environment_manager/dashboard' ||
          attrs.dashboard?.version === 1) return;
      const revision = Number(attrs.dashboard_revision) || 0;
      if (this._dashboardEntity === entityId &&
          this._dashboardLoadedRevision === revision && this._dashboardData) return;
      if (this._dashboardFetching ||
          Date.now()<this._dashboardNextAttemptAt) return;
      const capturedEntity = entityId;
      const capturedRevision = revision;
      this._dashboardFetching = Promise.resolve().then(() =>
        this._hass.callWS({
          type:'environment_manager/dashboard', entity_id:capturedEntity
        })
      ).then((snapshot) => {
        if (!snapshot || snapshot.version !== 1 ||
            !Array.isArray(snapshot.rooms)) throw new Error('Invalid dashboard snapshot');
        // A response from a previously selected recommendation must never
        // appear on another entry's card after the user changes the source.
        if (this._state()[0] !== capturedEntity) return;
        this._dashboardData = snapshot;
        this._dashboardEntity = capturedEntity;
        this._dashboardLoadedRevision = capturedRevision;
        this._dashboardFailureCount = 0;
        this._dashboardNextAttemptAt = 0;
        this._render(true);
      }).catch((error) => {
        this._dashboardFailureCount = Math.min(6, this._dashboardFailureCount+1);
        this._dashboardNextAttemptAt = Date.now() +
          Math.min(60000, 1000 * (2 ** this._dashboardFailureCount));
        if (this._dashboardFailureCount<=2) {
          console.warn('Home Environment Manager dashboard will retry',error);
        }
      }).finally(() => {
        this._dashboardFetching = null;
        const [currentEntity, current] = this._state();
        const currentRevision = Number(current?.attributes?.dashboard_revision) || 0;
        if (current?.attributes?.dashboard_api === 'environment_manager/dashboard' &&
            (currentEntity !== capturedEntity ||
             currentRevision !== capturedRevision) &&
            Date.now()>=this._dashboardNextAttemptAt) {
          this._loadDashboard();
        }
      });
    }

    _loadDeviceIds() {
      // Loading/reconnect failures are transient. A permanent "unavailable"
      // latch previously required a browser hard refresh to recover links.
      if (this._deviceRegistryLoading || this._deviceRegistryLoaded ||
          !this._hass?.callWS || Date.now()<this._deviceRegistryNextAttemptAt) return;
      // Defer the call to catch both synchronous WebSocket failures and
      // rejected promises without escaping from Home Assistant's hass setter.
      this._deviceRegistryLoading = Promise.resolve().then(() =>
        this._hass.callWS({type:'config/device_registry/list'})
      ).then((entries) => {
        if (!Array.isArray(entries)) throw new Error('Invalid device registry');
        const belong = (d) => safeArray(d?.identifiers)
          .filter((pair) => Array.isArray(pair) && pair[0]==='environment_manager')
          .map((pair) => pair[1]);
        const home = entries.filter((device) => belong(device).some(
          (identifier) => typeof identifier === 'string' && !identifier.includes('_area_')
        ));
        const stateId = this._state()[0];
        const currentDevice = this._hass?.entities?.[stateId]?.device_id;
        const parent = home.find((device)=>device.id===currentDevice) ||
                       (home.length===1 ? home[0] : null);
        if (!parent) {
          // Multiple integrations or an incomplete HA registry are ambiguous.
          // Do not navigate to a guessed device; retry when HA reconnects.
          throw new Error('Home device registry not yet unambiguous');
        }
        const ids = belong(parent);
        const entryId = ids.find((id) => typeof id==='string' && !id.includes('_area_'));
        if (!entryId) throw new Error('Home device registry is incomplete');
        const roomDevices = new Map();
        for (const device of entries) {
          for (const identifier of belong(device)) {
            const prefix = entryId+'_area_';
            if (typeof identifier === 'string' && identifier.startsWith(prefix)) {
              roomDevices.set(identifier.slice(prefix.length),device.id);
            }
          }
        }
        this._homeDeviceId = parent.id;
        this._areaDeviceIds = roomDevices;
        this._deviceRegistryLoaded = true;
        this._deviceRegistryUnavailable = false;
        this._deviceRegistryFailureCount = 0;
        this._deviceRegistryNextAttemptAt = 0;
        this._render(true);
      }).catch((error) => {
        this._deviceRegistryLoaded = false;
        this._deviceRegistryFailureCount = Math.min(6, this._deviceRegistryFailureCount+1);
        this._deviceRegistryNextAttemptAt = Date.now()+
          Math.min(60000, 1000*(2**this._deviceRegistryFailureCount));
        // A temporary websocket/registry outage must not break card rendering
        // and must not generate a console warning on every hass state update.
        if (this._deviceRegistryFailureCount<=2) {
          console.warn('Home Environment Manager device links will retry', error);
        }
      }).finally(() => { this._deviceRegistryLoading = null; });
    }

    _deviceEditLabel(home = false) {
      const l = DEVICE_EDIT_LABELS[this._language()] || DEVICE_EDIT_LABELS.en;
      return home ? l.home : l.room;
    }

    _editButton(area) {
      const device = this._areaDeviceIds.get(String(area));
      return '<button class="edit-device" type="button" data-edit-area="'+escape(area)+
        '" aria-label="'+escape(this._deviceEditLabel())+'" title="'+escape(
          this._deviceEditLabel())+'" '+(device ? '' : 'disabled')+'>'+
        this._icon('mdi:cog-outline')+'</button>';
    }

    getCardSize() { return 5; }

    _language() {
      return cardLanguage(this._hass?.language);
    }
    _controllerStatusLabel(code) {
      const key=String(code ?? '').trim();
      if (!key) return this._t('missing');
      // Keep canonical internal codes in state/history/automations. Only the
      // displayed text is translated. HA language may differ from integration
      // announcement language; use the viewer's active locale.
      const tr=this._hass?.localize?.(
        'component.environment_manager.entity.sensor.equipment_control_status.state.'+key);
      if (typeof tr==='string' && tr.trim() && tr!==key) return tr;
      const root=this._language();
      const fallback=CONTROLLER_STATUS_FALLBACK[root] || CONTROLLER_STATUS_FALLBACK.en;
      if (fallback[key]) return fallback[key];
      // Future statuses must remain intelligible before adding new strings.
      const readable=key.replaceAll('_',' ').replace(/\b(pid|hvac|co2|rh|pwm|ac)\b/gi,
        (part)=>part.toUpperCase());
      return readable.charAt(0).toUpperCase()+readable.slice(1);
    }

    _t(key) {
      const lang = this._language();
      return key === "title" ? BRAND_TITLE : (LANGUAGE[lang]?.[key] || LANGUAGE.en[key] || key);
    }

    _format(value, digits = 1) {
      if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
      try { return new Intl.NumberFormat(this._hass?.language || 'en', {
        maximumFractionDigits:digits, minimumFractionDigits:0
      }).format(value); } catch { return String(value); }
    }

    _metricName(metric) {
      if (metric === 'mold') {
        const translated = this._t('metric_mold');
        return translated === 'metric_mold' ? 'Mold indication' : translated;
      }
      return this._t(`metric_${metric}`);
    }

    _unknownMetricName(item) {
      // Unavailable/unsupported selected sensors can have no friendly name
      // and their fallback "name" is then the full sensor.entity_id. Never
      // display that identifier as the heading of a narrow metric tile.
      // This is a *label only*, not a claim that the sensor is usable data.
      const entityId = typeof item?.entity_id === 'string' ? item.entity_id : '';
      const native = this._hass?.states?.[entityId];
      const kind = String(native?.attributes?.device_class || '').toLowerCase();
      const slug = entityId.split('.').slice(1).join('.').toLowerCase();
      const dictionary = {
        illumination:{en:'Illumination',de:'Beleuchtung',el:'Φωτισμός',
          fr:'Éclairement',es:'Iluminación'},
        presence:{en:'Presence',de:'Präsenz',el:'Παρουσία',
          fr:'Présence',es:'Presencia'},
        motion:{en:'Motion',de:'Bewegung',el:'Κίνηση',
          fr:'Mouvement',es:'Movimiento'},
        temperature:{en:'Temperature',de:'Temperatur',el:'Θερμοκρασία',
          fr:'Température',es:'Temperatura'},
        humidity:{en:'Humidity',de:'Luftfeuchtigkeit',el:'Υγρασία',
          fr:'Humidité',es:'Humedad'},
        pressure:{en:'Pressure',de:'Luftdruck',el:'Πίεση',
          fr:'Pression',es:'Presión'},
        noise:{en:'Noise',de:'Geräusch',el:'Θόρυβος',
          fr:'Bruit',es:'Ruido'},
      };
      const hints = [
        ['illumination',/(?:^|_)(?:illuminance|illumination|brightness|light_level|lux)$/],
        ['presence',/(?:^|_)(?:presence|occupancy|occupied)$/],
        ['motion',/(?:^|_)(?:motion|movement)$/],
        ['temperature',/(?:^|_)(?:temperature|temp)$/],
        ['humidity',/(?:^|_)(?:humidity|relative_humidity)$/],
        ['pressure',/(?:^|_)(?:pressure|atmospheric_pressure)$/],
        ['noise',/(?:^|_)(?:noise|sound_level|sound_pressure)$/],
      ];
      const identified = hints.find(([id, pattern])=>
        kind===id || (id==='illumination' && kind==='illuminance') ||
        (id==='presence' && kind==='occupancy') ||
        (id==='noise' && kind==='sound_pressure') ||
        pattern.test(slug));
      if (identified) {
        const language=this._language();
        return dictionary[identified[0]][language] ||
          dictionary[identified[0]].en;
      }
      const name=String(native?.attributes?.friendly_name || item?.name || '').trim();
      // Keep actual user-given short names, but not raw entity IDs.
      if (name && !/^(sensor|binary_sensor|input_number)\.[\w.]+$/i.test(name)
          && name.length<=24) return name;
      if (name && !/^(sensor|binary_sensor|input_number)\.[\w.]+$/i.test(name)) {
        const finalPart=name.split(/\s+[·:-]\s+/).at(-1).trim();
        if (finalPart.length<=24) return finalPart;
      }
      const words=slug.split(/[_.]+/).filter(Boolean).slice(-2)
        .map((word)=>word.replace(/^\w/,ch=>ch.toUpperCase()));
      return words.join(' ') || this._t('sensor');
    }

    _weatherName(condition) {
      if (!condition) return this._t('missing');
      const key = { 'clear-night':'wx_clearNight','partlycloudy':'wx_partlycloudy',
        'lightning-rainy':'wx_lightning','snowy-rainy':'wx_snowy','windy-variant':'wx_windy'
      }[condition] || `wx_${condition}`;
      return this._t(key) === key ? condition.replaceAll('-',' ') : this._t(key);
    }

    _state() {
      const id = this._config.entity || (detected(this._hass).length === 1 ? detected(this._hass)[0] : null);
      return [id, id ? this._hass?.states?.[id] : null];
    }

    _managedControllers(area) {
      // Only match Manager-created native climate facades with provenance.
      // An unrelated physical entity must never acquire writable controls.
      const states = Object.entries(this._hass?.states || {});
      const physical = states.filter(([id, item])=>
        id.startsWith('climate.') && item?.attributes?.area_id===area &&
        Array.isArray(item.attributes.source_entity_ids) &&
        item.attributes.source_entity_ids.length>0 &&
        typeof item.attributes.control_mode==='string');
      const selectors = states.filter(([id, item])=> id.startsWith('select.') &&
        item?.attributes?.area_id===area &&
        Array.isArray(item.attributes.source_entity_ids) &&
        Array.isArray(item.attributes.options) &&
        ['automatic','manual','off'].every((mode)=>item.attributes.options.includes(mode)));
      const signature = (item) => JSON.stringify(
        safeArray(item.attributes.source_entity_ids).slice().sort());
      const calibrationSelectors=states.filter(([id,item])=>
        id.startsWith('select.') && item?.attributes?.area_id===area &&
        item.attributes.pid_calibration_role==='method');
      const calibrationButtons=states.filter(([id,item])=>
        id.startsWith('button.') && item?.attributes?.area_id===area &&
        item.attributes.pid_calibration_role==='apply');
      const calibrationInputs=states.filter(([id,item])=>
        id.startsWith('number.') && item?.attributes?.area_id===area &&
        typeof item.attributes.pid_calibration_field==='string');
      const capacitySelectors=states.filter(([id,item])=>
        id.startsWith('select.') && item?.attributes?.area_id===area &&
        ['strategy','direction'].includes(item.attributes.pid_fan_capacity_role));
      const capacityButtons=states.filter(([id,item])=>
        id.startsWith('button.') && item?.attributes?.area_id===area &&
        item.attributes.pid_fan_capacity_role==='apply');
      const capacityFields=states.filter(([id,item])=>
        id.startsWith('number.') && item?.attributes?.area_id===area &&
        typeof item.attributes.pid_fan_capacity_field==='string');
      return physical.map(([entityId, climate])=>{
        const matched = selectors.filter(([,item])=>signature(item)===signature(climate));
        const [methodId, method] = matched.length===1 ? matched[0] : [null,null];
        const found=calibrationSelectors.filter(([,item])=>signature(item)===signature(climate));
        const [calibrationSelectId,calibrationSelect]=found.length===1 ?
          found[0] : [null,null];
        const buttons=calibrationButtons.filter(([,item])=>signature(item)===signature(climate));
        const [calibrationButtonId,calibrationButton]=buttons.length===1 ?
          buttons[0] : [null,null];
        const calibrationNumbers=calibrationInputs.filter(([,item])=>
          signature(item)===signature(climate)).map(([id,state])=>({
            id,state,field:state.attributes.pid_calibration_field,
          }));
        const capacitySelection=capacitySelectors.filter(([,item])=>
          signature(item)===signature(climate));
        const [capacityModeId, capacityMode]=capacitySelection.find(([,item])=>
          item.attributes.pid_fan_capacity_role==='strategy') || [null,null];
        const [capacityDirectionId, capacityDirection]=capacitySelection.find(([,item])=>
          item.attributes.pid_fan_capacity_role==='direction') || [null,null];
        const [capacityButtonId, capacityButton]=capacityButtons.find(([,item])=>
          signature(item)===signature(climate)) || [null,null];
        const capacityNumbers=capacityFields.filter(([,item])=>
          signature(item)===signature(climate)).map(([id,state])=>({
            id,state,field:state.attributes.pid_fan_capacity_field,
          }));
        return {entityId,climate,methodId,method,calibrationSelectId,
                calibrationSelect,calibrationButtonId,calibrationButton,
                calibrationNumbers,capacityModeId,capacityMode,capacityDirectionId,
                capacityDirection,capacityButtonId,capacityButton,capacityNumbers};
      }).sort((a,b)=>a.entityId.localeCompare(b.entityId));
    }

    _controllerSignature() {
      // The main recommendation sensor may be unchanged while a physical
      // controller is switched to Manual/PID/Off in Home Assistant.
      const rows = Object.entries(this._hass?.states || {})
        .filter(([id, state]) =>
          (id.startsWith('select.') || id.startsWith('climate.') || (id.startsWith('sensor.') && state?.attributes?.status_code) ||
           (id.startsWith('button.') && (
             state?.attributes?.pid_calibration_role || state?.attributes?.pid_fan_capacity_role)) ||
           (id.startsWith('number.') && (
             state?.attributes?.pid_calibration_field || state?.attributes?.pid_fan_capacity_field))) &&
          Array.isArray(state?.attributes?.source_entity_ids) &&
          typeof state.attributes.area_id==='string')
        .map(([id,state])=>[
          id,state.state,state.attributes.control_mode,
          state.attributes.temperature,state.attributes.humidity,
          state.attributes.supported_features,
          state.attributes.physical_source_state, state.attributes.status_reason_code, state.attributes.status_code, state.attributes.upstream_idle_since,
          state.attributes.controller_status, state.attributes.measurements, state.attributes.upstream_power_state,
          state.attributes.options,
          state.attributes.source_entity_ids,
          state.attributes.pid_calibration_role,
          state.attributes.pid_calibration_field,
          state.attributes.pid_fan_capacity_role,
          state.attributes.pid_fan_capacity_field,
          state.attributes.calibration_status,
        ]);
      return JSON.stringify(rows);
    }

    _icon(icon, extraClass = '') {
      return `<ha-icon class="${extraClass}" icon="${escape(icon)}" aria-hidden="true"></ha-icon>`;
    }

    _moldInputWarning(code) {
      const localized = MOLD_INPUT_WARNING_LABELS[this._language()]?.[code];
      if (localized) return localized;
      const missing = this._t('missing');
      return {
        calibration: this._t('moldNotCalibrated'),
        indoor_temperature: '🏠 🌡️ °C · ' + missing,
        outdoor_temperature: this._t('weather') + ' · 🌡️ °C · ' + missing,
        humidity: this._t('humidity') + ' RH (%) · ' + missing,
        calculation: this._t('moldInputsUnavailable'),
      }[code] || missing;
    }

    _moldLabels() {
      return MOLD_DETAIL_LABELS[this._language()] || MOLD_DETAIL_LABELS.en;
    }

    _formatCalibration(value) {
      if (typeof value !== 'number' || !Number.isFinite(value)) return '-';
      // Display precision only: this never changes the stored numeric factor.
      try {
        return new Intl.NumberFormat(this._hass?.language || 'en', {
          minimumFractionDigits: 2, maximumFractionDigits: 6, useGrouping: false
        }).format(value);
      } catch { return String(value); }
    }

    _moldCalibrationDetails(moldReading) {
      const details = moldReading?.details;
      if (typeof details?.calibration_factor !== 'number' ||
          !Number.isFinite(details.calibration_factor)) return '';
      const labels = this._moldLabels();
      const temperature = (value) => typeof value === 'number' && Number.isFinite(value)
        ? `${escape(this._format(value))}°C` : '-';
      return `<section class="mold-calibration-details" role="group"
          aria-label="${escape(labels[4])}">
        <div><span>${escape(labels[4])}</span>
          <strong title="${escape(String(details.calibration_factor))}">${escape(this._formatCalibration(details.calibration_factor))}</strong></div>
        <div><span>${escape(labels[5])}</span>
          <strong>${temperature(details.indoor_temperature_c)}</strong></div>
        <div><span>${escape(labels[6])}</span>
          <strong>${temperature(details.outdoor_temperature_c)}</strong></div>
      </section>`;
    }

    _metricHelp(item) {
      const lang = this._language();
      const gr = lang === 'el';
      const de = lang === 'de';
      const texts = {
        co2: ['CO₂ shows how much exhaled air accumulates indoors. Elevated levels suggest insufficient ventilation and may coincide with sleepiness and impaired concentration.', 'Το CO₂ δείχνει πόσος εκπνεόμενος αέρας συσσωρεύεται. Υψηλή συγκέντρωση υποδηλώνει ανεπαρκή αερισμό και μπορεί να συνδέεται με υπνηλία και μειωμένη συγκέντρωση.', 'CO₂ zeigt die Ansammlung ausgeatmeter Luft und kann auf unzureichende Lüftung hinweisen.'],
        pm25: ['PM2.5 particles can penetrate deeply into the lungs. Filtration and avoiding polluted outdoor air may reduce exposure.', 'Τα σωματίδια PM2.5 διεισδύουν βαθιά στους πνεύμονες. Ο καθαρισμός και η αποφυγή ρυπασμένου εξωτερικού αέρα μειώνουν την έκθεση.', 'PM2,5-Partikel können tief in die Lunge eindringen. Filtration kann die Belastung senken.'],
        pm10: ['PM10 is inhalable particulate matter. High exposure can irritate the airways.', 'Τα PM10 είναι εισπνεόμενα αιωρούμενα σωματίδια που μπορούν να ερεθίσουν τους αεραγωγούς.', 'PM10 ist einatembarer Feinstaub, der die Atemwege reizen kann.'],
        humidity: ['Relative humidity depends on temperature. Persistently high RH increases condensation and mold risk; low RH may cause dryness.', 'Η σχετική υγρασία εξαρτάται από τη θερμοκρασία. Η παρατεταμένα υψηλή υγρασία αυξάνει τον κίνδυνο συμπύκνωσης και μούχλας· η χαμηλή προκαλεί ξηρότητα.', 'Relative Luftfeuchte hängt von der Temperatur ab. Dauerhaft hohe Werte fördern Kondenswasser und Schimmel.'],
        mold: ['This is an estimated critical-surface moisture indicator, not a mold detector. Cold surfaces and persistent high RH can raise risk.', 'Πρόκειται για εκτίμηση υγρασίας κρίσιμης επιφάνειας, όχι ανιχνευτή μούχλας. Οι κρύες επιφάνειες και η επίμονη υγρασία αυξάνουν τον κίνδυνο.', 'Dies ist eine Schätzung der Oberflächenfeuchte, kein Schimmeldetektor.'],
        aqi: ['Air Quality Index summarizes pollution according to the selected provider scale. Different national scales are not interchangeable.', 'Ο δείκτης AQI συνοψίζει τη ρύπανση βάσει της κλίμακας του παρόχου. Οι εθνικές κλίμακες δεν είναι ισοδύναμες.', 'Der Luftqualitätsindex verwendet die Skala des Anbieters. Nationale Skalen sind nicht austauschbar.'],
        voc: ['Volatile organic compounds may originate from cleaning agents, paints and furnishings. Sensor accuracy and compound coverage vary.', 'Οι πτητικές οργανικές ενώσεις προέρχονται μεταξύ άλλων από καθαριστικά, βαφές και έπιπλα. Η ακρίβεια του αισθητήρα διαφέρει.', 'Flüchtige organische Stoffe stammen etwa aus Reinigern, Farben und Möbeln.'],
        voc_parts: ['VOC concentration in parts per billion depends on sensor calibration and reference gas; high readings merit source inspection.', 'Οι VOC σε ppb εξαρτώνται από τη βαθμονόμηση και το αέριο αναφοράς. Οι υψηλές τιμές απαιτούν έλεγχο της πηγής.', 'VOC in ppb sind stark von Kalibrierung und Referenzgas abhängig.'],
        no2: ['Nitrogen dioxide can aggravate respiratory symptoms; sources include traffic and combustion.', 'Το διοξείδιο του αζώτου μπορεί να επιδεινώσει αναπνευστικά συμπτώματα· προέρχεται από κυκλοφορία και καύση.', 'Stickstoffdioxid aus Verkehr oder Verbrennung belastet die Atemwege.'],
        o3: ['Ground-level ozone can irritate the lungs and worsen asthma symptoms.', 'Το όζον κοντά στο έδαφος μπορεί να ερεθίσει τους πνεύμονες και να επιδεινώσει το άσθμα.', 'Bodennahes Ozon kann die Atemwege reizen.'],
        so2: ['Sulfur dioxide from combustion can irritate breathing passages.', 'Το διοξείδιο του θείου από καύσεις μπορεί να ερεθίσει το αναπνευστικό.', 'Schwefeldioxid aus Verbrennung kann die Atemwege reizen.']
      };
      const base = texts[item.metric] || [
        'Measured environmental data from the selected Home Assistant sensor. Use the recorded source, units and freshness to interpret it.',
        'Περιβαλλοντική μέτρηση από αισθητήρα Home Assistant. Ελέγξτε την πηγή, τις μονάδες και την ενημέρωση.',
        'Umweltmessung des ausgewählten Home-Assistant-Sensors. Quelle, Einheit und Aktualität beachten.'
      ];
      const limit = typeof item.threshold === 'number' && Number.isFinite(item.threshold)
        ? (gr ? ' Όριο ρύθμισης: ' : de ? ' Konfiguriertes Limit: ' : ' Configured threshold: ') + item.threshold + (item.unit ? ' ' + item.unit : '') + '.'
        : '';
      return (gr ? base[1] : de ? base[2] : base[0]) + limit;
    }

    _metric(item, miniature = false) {
      const metric = item.details?.fallback_for_mold
        ? `${this._t('humidity')} Ø (RH)`
        : item.metric==='unknown' ? this._unknownMetricName(item)
          : this._metricName(item.metric);
      const fullSource=[item.name,item.entity_id].filter(Boolean)
        .filter((value,index,arr)=>arr.indexOf(value)===index).join(' · ');
      const available = item.available && typeof item.value === 'number';
      const limit = item.threshold;
      const hasLimit = typeof limit === 'number' && limit > 0;
      const pct = available && hasLimit ? clamp(item.value / limit * 100, 0, 100) : 0;
      const unit = item.unit || '';
      const level = !available ? 'unknown' : item.exceeded ? 'attention' : 'safe';
      const display = available ? this._format(item.value) : '-';
      const threshold = hasLimit ? `${this._t('limits')} ${this._format(limit)} ${escape(unit)}` : '';
      const details = item.metric === 'mold' && item.details && typeof item.details === 'object'
        ? item.details : null;
      const moldUnavailableReason = item.metric === 'mold' && !available
        ? details?.status === 'needs_calibration' ? this._t('moldNotCalibrated')
          : details?.status === 'inputs_unavailable' ? this._t('moldInputsUnavailable')
            : this._t('missing')
        : this._t('missing');
      // The room can still have valid RH contributors before its coldest
      // surface has been calibrated. Show that average instead of hiding it.
      const moldLabels = this._moldLabels();
      const count = details?.humidity_sensor_count;
      const average = details && typeof details.average_indoor_humidity === 'number'
        && Number.isFinite(details.average_indoor_humidity)
        ? `<div>${escape(moldLabels[0])}: ${escape(this._format(details.average_indoor_humidity))}%
          ${Number.isInteger(count) && count > 0
            ? ` · ${escape(count)} ${escape(count === 1 ? moldLabels[1] : moldLabels[2])}`
            : ''}</div>`
        : '';
      const surface = details && typeof details.estimated_surface_c === 'number'
        && Number.isFinite(details.estimated_surface_c)
        ? `<div>${escape(moldLabels[3])}: ${escape(this._format(details.estimated_surface_c))}°C</div>`
        : '';
      const moldInfo = average || surface
        ? `<div class="mold-summary">${average}${surface}</div>` : '';
      return `<div class="metric ${miniature ? 'tiny' : ''} metric-${level}">
        <div class="metric-line">
          <span class="metric-name">${this._icon(METRIC_ICON[item.metric] || 'mdi:gauge')}<span class="metric-title" title="${escape(fullSource || metric)}">${escape(metric)}</span><details class="metric-help"><summary aria-label="${escape(this._l65('information'))}: ${escape(metric)}" title="${escape(this._metricHelp(item))}">${this._icon('mdi:information-outline')}</summary><div class="metric-help-content" role="note">${escape(this._metricHelp(item))}</div></details></span>
          <span class="metric-number">${escape(display)} <small>${escape(unit)}</small></span>
        </div>
        ${hasLimit ? `<div class="meter" role="progressbar" aria-label="${escape(metric)}"
          aria-valuemin="0" aria-valuemax="${escape(limit)}" aria-valuenow="${available ? escape(item.value) : '0'}">
          <span class="meter-fill" style="width:${pct.toFixed(2)}%"></span><span class="meter-limit"></span>
        </div><div class="metric-limit">${threshold}</div>`
          : `<div class="metric-limit">${available ? '' : escape(moldUnavailableReason)}</div>`}
        ${moldInfo}
      </div>`;
    }

    _window(win) {
      const opened = win.opened;
      const klass = opened === true ? 'opened' : opened === false ? 'closed' : 'unknown';
      const icon = opened === true ? 'mdi:window-open-variant' : opened === false ? 'mdi:window-closed-variant' : 'mdi:window-closed';
      const text = opened === true ? this._t('windowOpen') : opened === false ? this._t('windowClosed') : this._t('windowUnknown');
      return `<span class="window ${klass}" title="${escape(win.entity_id)}">${this._icon(icon)}<span>${escape(win.name)}</span>
        <small>· ${escape(text)}</small></span>`;
    }

    _outsideBlocker(reason) {
      const code = reason.code || '';
      const label = String(reason.label || '');
      const value = String(reason.value || '');
      const prefix = code.startsWith('outside_') ? this._t('unsafeReason') : ({
        weather_condition:this._t('weather'), weather_cold:this._t('cold'),
        weather_hot:this._t('hot'), weather_humid:this._t('wet'),
        weather_wind:this._t('windHigh'), active_warning:this._t('warningReason'),
        unavailable_warning:this._t('warningUnknown'),
        unavailable_weather:this._t('unavailableWeather'),
        no_weather_data:this._t('noWeather'),no_outdoor_data:this._t('noOutdoor')
      }[code] || this._t('conditions'));
      const metric = code.startsWith('outside_') ? this._metricName(code.slice(8)) : '';
      const suffix = code === 'weather_condition' ? this._weatherName(value) : value;
      return `<span class="reason">${this._icon('mdi:alert-circle-outline')}${escape(prefix)}${metric ? `: ${escape(metric)}` : ''}
       ${suffix ? `· ${escape(suffix)}` : (code === 'active_warning' && label ? `· ${escape(label)}` : '')}</span>`;
    }

    _outside(outdoor) {
      if (this._config.show_outside === false) return '';
      const status = ['safe','partial','unsafe','unknown'].includes(outdoor.status) ? outdoor.status : 'unknown';
      const main = status === 'safe' ? this._t('goodOutside') : status === 'partial' ?
        this._t('partialOutside') : status === 'unsafe' ? this._t('badOutside') : this._t('missingOutside');
      const wx = safeArray(outdoor.weather).find((item) => item.condition) || safeArray(outdoor.weather)[0];
      const icon = wx?.condition ? (ICON[wx.condition] || 'mdi:weather-cloudy') : 'mdi:weather-cloudy-alert';
      const temperature = typeof wx?.temperature_c === 'number' ? `${this._format(wx.temperature_c)}°C` : null;
      const extras = [
        ...(typeof wx?.humidity === 'number' ? [this._icon('mdi:water-percent') + escape(this._format(wx.humidity)) + '%'] : []),
        ...(typeof wx?.wind_kmh === 'number' ? [this._icon('mdi:weather-windy') + escape(this._format(wx.wind_kmh)) + ' km/h'] : [])
      ];
      const readings = safeArray(outdoor.readings);
      const blockers = safeArray(outdoor.blockers);
      const warnings = safeArray(outdoor.warnings).filter((item) => item.active === true);
      return `<section class="outside outside-${status}" aria-label="${escape(this._t('outside'))}">
        <div class="outdoor-head"><div class="outdoor-icon">${this._icon(icon)}</div>
          <div class="outdoor-text"><span class="eyebrow">${escape(this._t('outside'))}</span>
            <div class="outside-title">${escape(main)}</div>
            <div class="weather-line">${escape(wx?.condition ? this._weatherName(wx.condition) : this._t('missing'))}
              ${temperature ? `<strong>${escape(temperature)}</strong>` : ''}
              ${extras.length ? `<span>${extras.join('<span class="sep">·</span>')}</span>` : ''}
            </div>
          </div>
          <div class="outdoor-status">${this._icon(status === 'safe' ? 'mdi:check' : status === 'unsafe' ? 'mdi:alert' : 'mdi:information-outline')}</div>
        </div>
        ${readings.length ? `<div class="out-metrics" aria-label="${escape(this._t('outdoorSensors'))}">
          ${readings.map((item) => `<span class="out-chip ${!item.available ? 'dim' : item.exceeded ? 'elevated' : ''}">
            ${escape(this._metricName(item.metric))} <b>${item.available ? escape(this._format(item.value)) : '-'}</b>
            <small>${escape(item.unit)}</small></span>`).join('')}
        </div>` : `<div class="out-empty">${escape(this._t('noOutdoor'))}</div>`}
        ${blockers.length ? `<div class="outside-alerts">${blockers.slice(0,5).map((item) => this._outsideBlocker(item)).join('')}
          ${blockers.length > 5 ? `<span>+${blockers.length - 5}</span>` : ''}</div>` : ''}
        ${warnings.length && !blockers.some((b) => b.code === 'active_warning' || b.code === 'unavailable_warning')
          ? `<div class="outside-alerts">${warnings.map((warning) => `<span class="reason">${escape(warning.name)} · ${escape(warning.active === true ? this._t('warningActive') : this._t('warningUnknown'))}</span>`).join('')}</div>` : ''}
      </section>`;
    }

    _summary(summary) {
      const counts = ['safe','attention','unknown'].map((k) => Math.max(0, Number(summary[k] || 0)));
      const total = counts.reduce((acc, value) => acc + value, 0);
      const first = total ? counts[0] / total * 100 : 0;
      const second = total ? (counts[0] + counts[1]) / total * 100 : 0;
      return `<div class="section-head"><span class="section-title">${this._icon('mdi:home-heart')} ${escape(this._t('roomStatus'))}</span>
        <span class="subdued">${total}</span></div>
        <div class="overview">
          <div class="donut-wrap"><div class="donut" role="img"
            aria-label="${escape(this._t('safe'))}: ${counts[0]}; ${escape(this._t('attention'))}: ${counts[1]}; ${escape(this._t('unknown'))}: ${counts[2]}"
            style="--good-end:${first.toFixed(2)}%;--attention-end:${second.toFixed(2)}%">
            <div class="donut-inner"><strong>${total}</strong><span>${escape(this._t('roomStatus'))}</span></div>
          </div></div>
          <div class="counts">${['safe','attention','unknown'].map((k,i) => `<div class="count count-${k}">
            <span class="count-icon">${this._icon(ICON[k])}</span>
            <strong>${counts[i]}</strong><small>${escape(this._t(k))}</small>
          </div>`).join('')}</div>
        </div>`;
    }


    _scienceHelp(topic) {
      const lang = this._language();
      const explanations = {
        moisture: ['Moisture-ratio difference estimates whether outside air can dry or humidify the room. Relative humidity alone does not show this.', 'Η διαφορά στην ποσότητα υδρατμών δείχνει αν ο εξωτερικός αέρας μπορεί να ξηράνει ή να υγράνει το δωμάτιο. Η σχετική υγρασία μόνη της δεν επαρκεί.'],
        predicted: ['Outdoor relative humidity projected after the air warms indoors; this is a physical estimate, not a humidity forecast.', 'Εκτίμηση σχετικής υγρασίας του εξωτερικού αέρα αφού θερμανθεί μέσα. Δεν αποτελεί πρόγνωση.'],
        band: ['Adaptive comfort band derived from outdoor temperature history. It describes expected comfort, not a mandatory medical limit.', 'Προσαρμοστική ζώνη θερμικής άνεσης βάσει ιστορικού εξωτερικής θερμοκρασίας, όχι ιατρικό όριο.'],
        cooling: ['Positive outdoor cooling advantage suggests a possible window-airing opportunity if outdoor air quality and weather are safe.', 'Πιθανή φυσική ψύξη από τον εξωτερικό αέρα, μόνο εφόσον επιτρέπουν η ρύπανση και ο καιρός.'],
        surface: ['Condensation margin estimates how near a cold surface is to its dew point. A small margin increases moisture risk.', 'Το περιθώριο συμπύκνωσης δείχνει πόσο πλησιάζει μια ψυχρή επιφάνεια στο σημείο δρόσου. Μικρή διαφορά αυξάνει τον κίνδυνο υγρασίας.'],
        exposure: ['Hours with estimated surface RH above the displayed exposure threshold. Persistent moisture raises mold risk; it is not proof of mold.', 'Ώρες με εκτιμώμενη υγρασία επιφάνειας πάνω από το εμφανιζόμενο όριο. Η παρατεταμένη υγρασία ευνοεί τη μούχλα, δεν την αποδεικνύει.'],
        pm: ['Measured 24-hour particulate mean, only shown when history coverage is sufficient. Exposure duration matters, not just one reading.', 'Μέσος όρος σωματιδίων 24 ωρών μόνο με επαρκές ιστορικό. Η διάρκεια έκθεσης έχει σημασία.'],
        co2: ['CO₂ rate of change can help evaluate ventilation or occupancy but does not independently measure air changes.', 'Ο ρυθμός μεταβολής CO₂ βοηθά στην αξιολόγηση αερισμού ή παρουσίας αλλά δεν μετρά απευθείας τις εναλλαγές αέρα.'],
        ach: ['Conditional air-change estimate from a qualified CO₂ decay sequence. It is not a certified ventilation airflow measurement.', 'Εκτίμηση εναλλαγών αέρα από αξιόπιστη πτώση CO₂· δεν αποτελεί πιστοποιημένη μέτρηση παροχής αέρα.'],
        energy: ['Approximate heat required per cubic meter of exchanged air. Mechanical efficiency and actual device power are not included.', 'Εκτιμώμενη θερμική ενέργεια ανά κυβικό μέτρο ανανέωσης αέρα· δεν περιλαμβάνει πραγματική κατανάλωση συσκευών.'],
        purification: ['Nominal clean-air changes from entered room volume and purifier CADR; real performance varies with filters and airflow.', 'Ονομαστικές εναλλαγές καθαρού αέρα από όγκο χώρου και CADR. Η πραγματική απόδοση εξαρτάται από φίλτρα και ροή.'],
        ventilation: ['Indicative minutes to a selected target based on observed improvement. Changes in occupancy or windows can invalidate the estimate.', 'Ενδεικτικά λεπτά μέχρι τον στόχο βάσει μετρήσεων. Αλλαγές παρουσίας και παραθύρων επηρεάζουν την εκτίμηση.'],
        humidity_event: ['Recent relative-humidity increase can indicate moisture generation (showering, cooking or drying), but source attribution is uncertain.', 'Πρόσφατη άνοδος σχετικής υγρασίας μπορεί να οφείλεται σε ντους, μαγείρεμα ή στέγνωμα· η πηγή δεν αποδεικνύεται.'],
        formaldehyde: ['Formaldehyde can irritate the eyes and airways. The short measurement period is not a long-term exposure assessment.', 'Η φορμαλδεΰδη μπορεί να ερεθίσει μάτια και αεραγωγούς. Η σύντομη μέτρηση δεν εκτιμά τη μακροχρόνια έκθεση.'],
        radon: ['Radon is a radioactive gas associated with increased lung cancer risk from long-term exposure. Meaningful assessment requires an adequately long calibrated measurement.', 'Το ραδόνιο είναι ραδιενεργό αέριο και η μακροχρόνια έκθεση αυξάνει τον κίνδυνο καρκίνου πνεύμονα. Χρειάζεται αξιόπιστη μακρά μέτρηση.'],
        noise: ['Sound levels in dB(A) depend on measurement period and calibration. Sustained or nighttime noise may disrupt sleep.', 'Η στάθμη dB(A) εξαρτάται από τη διάρκεια και τη βαθμονόμηση. Επίμονος ή νυχτερινός θόρυβος μπορεί να επηρεάσει τον ύπνο.'],
        light: ['Observed daylight availability can help assess light exposure, but ordinary lux does not determine circadian stimulus.', 'Η διάρκεια φυσικού φωτισμού περιγράφει την έκθεση στο φως, αλλά τα κοινά lux δεν προσδιορίζουν τον κιρκάδιο ερεθισμό.'],
        melanopic: ['Melanopic equivalent daylight illuminance approximates biological light stimulation only from a verified spectral measurement.', 'Τα μελανοπικά lux εκτιμούν τη βιολογική επίδραση φωτός μόνο με κατάλληλη φασματική μέτρηση.'],
        overheating: ['Cumulative degrees above an overheating reference reflect both intensity and duration of indoor heat.', 'Σωρευτικοί βαθμοώρες πάνω από όριο υπερθέρμανσης δείχνουν ένταση και διάρκεια ζέστης.'],
        pmv: ['PMV predicts average thermal sensation and PPD the predicted percentage dissatisfied under declared clothing, activity, airflow and radiation assumptions.', 'Το PMV εκτιμά θερμική αίσθηση και το PPD το ποσοστό δυσαρέσκειας, με υποθέσεις ένδυσης, δραστηριότητας και ροής αέρα.'],
        particle: ['Indoor/outdoor particle ratio compares measured concentrations; differences do not by themselves prove filtration efficiency.', 'Ο λόγος εσωτερικών/εξωτερικών σωματιδίων συγκρίνει μετρήσεις, αλλά δεν αποδεικνύει μόνος του απόδοση φίλτρων.'],
      };
      const record = explanations[topic] || ['Measured environmental estimate; interpret only with its source and units.', 'Περιβαλλοντική εκτίμηση: ελέγξτε πηγή και μονάδες.'];
      return record[lang === 'el' ? 1 : 0];
    }

    _environmentReport(room) {
      const e = room.environment || {};
      const m = e.moisture || {};
      const t = e.thermal_comfort || {};
      const p = e.passive_cooling || {};
      const s = e.condensation || {};
      const h = e.surface_rh_exposure_24h || {};
      const labels = SCIENCE_LABELS[this._language()] || SCIENCE_LABELS.en;
      const fmt = (v, digits = 1) => this._format(v, digits);
      const lines = [];
      const add = (label, value, topic = '') => {
        const help = this._scienceHelp(topic);
        lines.push('<div class="science-line"><span>' + escape(label) +
          ' <details class="metric-help"><summary aria-label="' + escape(label) +
          ' '+escape(this._l65('information'))+'" title="' + escape(help) + '">' +
          this._icon('mdi:information-outline') +
          '</summary><div class="metric-help-content" role="note">' +
          escape(help) + '</div></details></span><strong>' + escape(value) + '</strong></div>');
      };
      if (m.status === 'drying' || m.status === 'humidifying' || m.status === 'neutral') {
        add(m.status === 'drying' ? labels.drying :
            m.status === 'humidifying' ? labels.humidifying : labels.neutral,
          fmt(m.drying_potential_g_kg, 2) + ' g/kg','moisture');
        if (typeof m.outside_air_rh_when_warmed_percent === 'number')
          add(labels.predicted, fmt(m.outside_air_rh_when_warmed_percent) + '% RH','predicted');
      }
      if (t.status === 'within_band' || t.status === 'above_band' || t.status === 'below_band') {
        add(labels.band + ' · ' +
            (t.status === 'above_band' ? labels.heat :
             t.status === 'below_band' ? labels.cool : labels.normal),
          fmt(t.lower_80_c) + '-' + fmt(t.upper_80_c) + ' °C','band');
      }
      if (p.status === 'cooling_opportunity')
        add(labels.cooling, fmt(p.cooling_delta_c) + ' °C','cooling');
      if (s.status && s.status !== 'unavailable')
        add(labels.surface, fmt(s.condensation_margin_c) + ' °C','surface');
      if (h.status === 'ready')
        add(labels.exposure, fmt(h.above_threshold_hours) + ' h','exposure');
      for (const [key, label] of [['pm25_24h', labels.pm25], ['pm10_24h', labels.pm10]]) {
        const value = e[key] || {};
        if (value.status === 'ready') add(label, fmt(value.mean) + ' µg/m³','pm');
      }
      if (e.co2_trend?.status === 'ready')
        add(labels.co2, fmt(e.co2_trend.trend_ppm_per_hour) + ' ppm/h','co2');
      if (e.co2_decay_ach?.status === 'estimate')
        add(labels.ach, fmt(e.co2_decay_ach.ach_per_hour, 2) + ' h⁻¹','ach');
      if (typeof e.heat_per_full_air_exchange_wh_m3 === 'number')
        add(labels.energy, fmt(e.heat_per_full_air_exchange_wh_m3) + ' Wh/m³','energy');
      const extra = e.international || {};
      const eLabels = EXTRA_LABELS[this._language()] || EXTRA_LABELS.en;
      if (extra.air_purification?.nominal_particle_clean_air_changes_h !== undefined)
        add(eLabels.purification,fmt(extra.air_purification.nominal_particle_clean_air_changes_h,2)+' h⁻¹','purification');
      if (extra.ventilation_learning?.status === 'indicative')
        add(eLabels.toTarget,'~'+fmt(extra.ventilation_learning.estimated_minutes_to_target)+' min','ventilation');
      if (extra.moisture_event?.status === 'relative_humidity_rise')
        add(eLabels.sourceMoisture,'+'+fmt(extra.moisture_event.rh_change_percent_points)+' %','humidity_event');
      if (extra.formaldehyde_30min?.status === 'ready')
        add(eLabels.hcho,fmt(extra.formaldehyde_30min.mean)+' µg/m³','formaldehyde');
      if (extra.radon?.status === 'annual_screening')
        add(eLabels.radon,fmt(extra.radon.mean_bq_m3)+' Bq/m³','radon');
      if (extra.sound_24h?.status === 'indicative_laeq')
        add(eLabels.noise,fmt(extra.sound_24h.db_a)+' dB(A)','noise');
      if (extra.sound_last_night?.status === 'indicative_night_laeq')
        add(eLabels.nightNoise,fmt(extra.sound_last_night.db_a)+' dB(A)','noise');
      if (extra.daylight?.status === 'descriptive')
        add(eLabels.light,fmt(extra.daylight.observed_hours_above_threshold)+' h','light');
      if (extra.daylight?.melanopic_edi_status === 'sensor_reported_not_from_photopic_lux')
        add(eLabels.melanopic,fmt(extra.daylight.melanopic_edi_lux)+' lx','melanopic');
      if (extra.overheating_degree_hours?.status === 'ready')
        add(eLabels.overheated,fmt(extra.overheating_degree_hours.degree_hours_over_reference)+' °C·h','overheating');
      if (extra.pmv_ppd?.status === 'estimate')
        add(eLabels.pmv,fmt(extra.pmv_ppd.pmv,2)+' / '+fmt(extra.pmv_ppd.ppd_percent)+'%','pmv');
      if (extra.particle_indoor_outdoor_ratio?.status === 'descriptive_only')
        add(eLabels.particle,fmt(extra.particle_indoor_outdoor_ratio.ratio,2),'particle');
      if (!lines.length) return '';
      return '<section class="science-section" aria-label="' + escape(labels.title) + '">' +
        '<div class="field-label">' + this._icon('mdi:flask-outline') +
        escape(labels.title) + '</div><div class="science-grid">' + lines.join('') + '</div>' +
        '<div class="science-caveat">' + escape(labels.estimated) + '</div></section>';
    }

    _pollenIndicator(outdoor) {
      const p = outdoor?.pollen || {};
      if (p.status !== 'provider_defined') return '';
      const title = (EXTRA_LABELS[this._language()] || EXTRA_LABELS.en);
      return '<div class="pollen-indicator" role="status">' +
        this._icon('mdi:flower-pollen') +
        escape(title.pollen) + ': <strong>' + escape(this._format(p.value)) + ' / ' +
        escape(this._format(p.max_scale)) + (p.high ? ' · ' + escape(title.pollenHigh) : '') +
        '</strong></div>';
    }

    _controllerPanel(room) {
      const devices=this._managedControllers(room.area_id);
      if (!devices.length) return '';
      const l=this._climateLabels65();
      const methods={existing:l.existing,automatic:l.automatic,manual:l.manual,
        pid:l.pid,off:l.off};
      const pidLabels=this._pidLabels65();
      const fanCapacityLabels=this._fanLabels65();
      const sections=devices.map((entry)=>{
        const state=entry.climate;
        const attrs=state.attributes || {};
        const available=state.state!=='unavailable' && state.state!=='unknown';
        const selection=entry.method;
        const options=Array.isArray(selection?.attributes?.options)
          ? selection.attributes.options : [];
        const control=selection?.state || attrs.control_mode || 'existing';
        const name=attrs.friendly_name || entry.entityId;
        const method=entry.methodId && options.length
          ? '<label class="managed-method-label"><span>'+escape(l.method)+'</span>'+
          '<select data-climate-method="'+escape(entry.methodId)+
          '" data-controller-area="'+escape(room.area_id)+
          '" aria-label="'+escape(l.method)+' · '+escape(name)+'" '+
          (available ? '' : 'disabled')+'>'+
          options.map((option)=>'<option value="'+escape(option)+'" '+
            (option===control ? 'selected' : '')+'>'+
            escape(methods[option] || option)+'</option>').join('')+
          '</select></label>' : '';
        const calMethods={manual:pidLabels[1],imc_lambda:pidLabels[2],
          cohen_coon:pidLabels[3]};
        const selectedCalibration=entry.calibrationSelect?.state || 'manual';
        const calibrationOptions=entry.calibrationSelect?.attributes?.options || [];
        const calibrationMethod=control==='pid' && entry.calibrationSelectId &&
          calibrationOptions.length
          ? '<label class="managed-method-label"><span>'+escape(pidLabels[0])+'</span>'+
            '<select data-pid-calibration-method="'+escape(entry.calibrationSelectId)+
            '" data-controller-area="'+escape(room.area_id)+'" '+
            (available ? '' : 'disabled')+'>'+
            calibrationOptions.map((option)=>
              '<option value="'+escape(option)+'" '+
              (option===selectedCalibration ? 'selected' : '')+'>'+
              escape(calMethods[option] || option)+'</option>').join('')+
            '</select></label>' : '';
        const pidModelFields=[
          ['pid_process_gain',pidLabels[4]],
          ['pid_time_constant_minutes',pidLabels[5]],
          ['pid_dead_time_minutes',pidLabels[6]],
          ['pid_lambda_minutes',pidLabels[7]],
        ].filter(([key])=>selectedCalibration==='imc_lambda' ||
          key!=='pid_lambda_minutes');
        const pidInputs=(control==='pid' && selectedCalibration!=='manual')
          ? pidModelFields.map(([key,label])=>{
              const match=entry.calibrationNumbers?.find(item=>item.field===key);
              if (!match) return '';
              const bound=match.state.attributes || {};
              return '<div class="climate-target-editor">'+
                '<label><span>'+escape(label)+'</span>'+
                '<input type="number" data-pid-model-input="'+escape(key)+
                '" min="'+escape(bound.min ?? 0)+'" max="'+escape(bound.max ?? 10000)+
                '" step="'+escape(bound.step ?? 0.1)+'" value="'+
                escape(match.state.state==='unavailable' ? '' : match.state.state)+
                '"></label><button type="button" data-save-pid-model="'+escape(match.id)+
                '" data-pid-model-field="'+escape(key)+'" data-controller-area="'+
                escape(room.area_id)+'">'+escape(pidLabels[8])+'</button></div>';
            }).join('') : '';
        const apply=(control==='pid' && selectedCalibration!=='manual' &&
          entry.calibrationButtonId)
          ? '<div class="managed-status">'+escape(pidLabels[10])+' · '+
             escape(this._controllerStatusLabel(entry.calibrationButton?.attributes?.calibration_status || ''))+
            '</div><button type="button" class="pid-button" '+
            'data-apply-pid-calibration="'+escape(entry.calibrationButtonId)+
            '" data-controller-area="'+escape(room.area_id)+'" '+
            (!available ? 'disabled' : '')+'>'+escape(pidLabels[9])+'</button>' : '';
        const capMethod=entry.capacityMode;
        const capDirection=entry.capacityDirection;
        const capChoices={
          legacy:fanCapacityLabels[1],measured:fanCapacityLabels[2],
          choose:fanCapacityLabels[4],heat:fanCapacityLabels[5],
          cool:fanCapacityLabels[6],dry:fanCapacityLabels[7],
          fan_only:fanCapacityLabels[8],
        };
        const renderCapacitySelect=(id,state,label)=>{
          if (!id || !Array.isArray(state?.attributes?.options)) return '';
          return '<label class="managed-method-label"><span>'+escape(label)+'</span>'+
            '<select data-pid-capacity-select="'+escape(id)+
            '" data-controller-area="'+escape(room.area_id)+'" '+
            (available && control==='pid' ? '' : 'disabled')+'>'+
            state.attributes.options.map(option=>
              '<option value="'+escape(option)+'" '+
              (state.state===option ? 'selected' : '')+'>'+
              escape(capChoices[option] || option)+'</option>').join('')+
            '</select></label>';
        };
        const capVisible=control==='pid' && entry.capacityModeId &&
          entry.capacityDirectionId;
        const capSelectors=capVisible ?
          renderCapacitySelect(entry.capacityModeId,capMethod,fanCapacityLabels[0])+
          renderCapacitySelect(entry.capacityDirectionId,capDirection,fanCapacityLabels[3]) : '';
        const capacityInput=capVisible && capMethod?.state==='measured' && capDirection?.state!=='choose' ?
          (entry.capacityNumbers || []).map((item)=>{
            const name=item.field;
            const number=Number(name.split('_').at(-1));
            const fieldName=name.startsWith('pid_capacity_stage_')
              ? fanCapacityLabels[9]+' '+number
              : name.startsWith('pid_capacity_speed_')
                ? fanCapacityLabels[10]+' '+number+' (%)'
                : fanCapacityLabels[11]+' '+number+' (%)';
            const limits=item.state?.attributes || {};
            return '<div class="climate-target-editor"><label><span>'+
              escape(fieldName)+'</span><input type="number" '+
              'data-pid-capacity-input="'+escape(name)+'" '+
              'min="'+escape(limits.min??0)+'" max="'+escape(limits.max??99)+
              '" step="'+escape(limits.step??1)+'" value="'+
              escape(item.state.state==='unavailable'?'':item.state.state)+'"></label>'+
              '<button type="button" data-save-pid-capacity="'+escape(item.id)+
              '" data-pid-capacity-field="'+escape(name)+'" '+
              'data-controller-area="'+escape(room.area_id)+'">'+
              escape(fanCapacityLabels[12])+'</button></div>';
          }).join('') : '';
        const nativeOff=attrs.physical_source_state==='off';
        const applyCapacity=capVisible && capMethod?.state==='measured' && entry.capacityButtonId ?
          '<small>'+escape(fanCapacityLabels[14])+' · '+
          escape(this._controllerStatusLabel(entry.capacityButton?.attributes?.calibration_status || ''))+
          '</small><button type="button" class="pid-button" '+
          'data-apply-pid-fan-capacity="'+escape(entry.capacityButtonId)+
          '" data-controller-area="'+escape(room.area_id)+'" '+
          (!nativeOff || capDirection?.state==='choose' || !available ?
            'disabled title="'+escape(fanCapacityLabels[18])+'"' : '')+
          '>'+escape(fanCapacityLabels[13])+'</button>' : '';
        const capacityStatus=attrs.controller_status?.pid_fan_capacity;
        const capacitySummary=control==='pid' && capacityStatus ?
          '<small>'+escape(this._controllerStatusLabel(capacityStatus.status))+
          (typeof capacityStatus.compensated_duty_percent==='number'
            ? ' · '+escape(fanCapacityLabels[15])+': '+
              escape(this._format(capacityStatus.compensated_duty_percent))+'%' : '')+
          (typeof capacityStatus.expected_delivered_percent==='number'
            ? ' · '+escape(fanCapacityLabels[16])+': '+
              escape(this._format(capacityStatus.expected_delivered_percent))+'%' : '')+
          (capacityStatus.unmet_demand_percent>0
            ? ' · '+escape(fanCapacityLabels[17])+': '+
              escape(this._format(capacityStatus.unmet_demand_percent))+'%' : '')+
          '</small>' : '';
        const features=Number(attrs.supported_features) || 0;
        const thermalModes=Array.isArray(attrs.hvac_modes) &&
          attrs.hvac_modes.some(mode=>['heat','cool','heat_cool','auto'].includes(mode));
        const editable=available && control==='manual';
        const editors=[];
        for(const [kind,bit,label,minKey,maxKey,fallbackLow,fallbackHigh,step] of [
          ['temperature',1,l.manualTemperature,'min_temp','max_temp',5,35,0.5],
          ['humidity',4,l.manualHumidity,'min_humidity','max_humidity',20,80,1],
        ]) {
          if (!(features & bit) || !editable ||
              (kind==='temperature' && !thermalModes)) continue;
          const minimum=Number(attrs[minKey] ?? fallbackLow);
          const maximum=Number(attrs[maxKey] ?? fallbackHigh);
          const value=attrs[kind];
          if (!Number.isFinite(minimum) || !Number.isFinite(maximum) ||
              !(maximum > minimum)) continue;
          editors.push('<div class="climate-target-editor">'+
            '<label><span>'+escape(label)+'</span>'+
            '<input type="number" data-climate-input="'+escape(kind)+
            '" min="'+escape(minimum)+'" max="'+escape(maximum)+
            '" step="'+escape(step)+'" value="'+
            (Number.isFinite(value) ? escape(value) : '')+'"></label>'+
            '<button type="button" data-save-climate-target="'+escape(entry.entityId)+
            '" data-target-metric="'+escape(kind)+'" data-controller-area="'+
            escape(room.area_id)+'">'+escape(l.save)+'</button></div>');
        }
        const status=attrs.controller_status?.status || '';
        return '<section class="managed-controller">'+
          '<button type="button" class="climate-entity-link" '+
          'data-open-climate="'+escape(entry.entityId)+
          '" data-controller-area="'+escape(room.area_id)+
          '" title="'+escape(l.openEntity)+'">'+
          this._icon('mdi:thermostat')+' <strong>'+escape(name)+
          '</strong> '+this._icon('mdi:open-in-new')+'</button>'+
          this._deviceSummary65(entry)+method+editors.join('')+
          this._calibrationDetails65(entry,control==='pid' ?
            calibrationMethod+pidInputs+apply+capSelectors+capacityInput+applyCapacity+capacitySummary : '')+
          '</section>';
      }).join('');
      return '<div class="managed-controllers">'+
        '<strong>'+escape(l.devices)+'</strong>'+
        (this._climateEditError ? '<small role="alert" class="climate-edit-error">'+
          escape(this._climateEditError)+'</small>' : '')+
        sections+'</div>';
    }

    _climatePanel(room) {
      const p=room?.environment?.climate_plan || {};
      const managed=this._managedControllers(room.area_id);
      if ((!p.status || p.status==='disabled') && !managed.length) return '';
      const l=this._climateLabels65();
      const primary=p.actuation || {};
      const secondary=p.secondary_actuation || {};
      const moisture=p.humidity_actuation || {};
      const power=p.humidity_power_actuation || {};
      const fan=p.fan_actuation || {};
      const fanPower=p.fan_power_actuation || {};
      const dryFan=p.native_air_mode_actuation || {};
      const controllers=[
        {label:l.primary, status:primary.status || 'advisory_only'},
        {label:l.secondary, status:secondary.status || 'advisory_only'},
        {label:l.humidity, status:moisture.status || 'advisory_only'},
        {label:l.humidityPower, status:power.status || 'advisory_only'},
        {label:l.fan, status:fan.status || 'advisory_only'},
        {label:l.fanPower, status:fanPower.status || 'advisory_only'},
        {label:l.dryFanAuto, status:dryFan.status || 'advisory_only'},
      ];
      const working=['setpoint_commanded','native_range_commanded',
        'at_setpoint','native_range_at_setpoint','holding','commanded',
        'modulating','mode_commanded','target_commanded',
        'fan_speed_increased','at_target_speed',
        'native_mode_commanded',
        'power_command_sent','owned_running','power_off_acknowledged',
        'fan_power_commanded','owned_fan_running','fan_power_off_acknowledged',
        'minimum_fan_on_hold',
        'minimum_on_hold_before_safe_off'];
      const active=controllers.some((part)=>working.includes(part.status));
      const enabled=controllers.filter((part)=>part.status!=='advisory_only' &&
        part.status!=='disabled');
      const allPaused=enabled.length>0 && enabled.every((part)=>part.status==='paused');
      const blocked=!active && ['hold','unavailable','unsupported_mode',
        'unsupported_device'].includes(p.status);
      const target=(typeof p.low_target_c==='number' &&
                    typeof p.high_target_c==='number') ?
        this._format(p.low_target_c)+'-'+this._format(p.high_target_c)+' °C' :
        typeof p.temperature_target_c==='number' ?
        this._format(p.temperature_target_c)+' °C' : '-';
      const title=managed.length ? this._l65('overview') : active ? (p.controller==='environment' ? l.environmentActive : l.active)
        : enabled.length ? l.holding : l.advisory;
      const command=allPaused?'resume':'pause';
      const controls=enabled.length===0 ? '' :
        '<button type="button" class="pid-button" data-climate-area="'+escape(room.area_id)+
        '" data-climate-action="'+command+'">'+escape(command==='pause'?l.pause:l.resume)+'</button>';
      const equipment=p.equipment_plan || {};
      const thermal=equipment.thermal || {};
      const wet=equipment.moisture || {};
      const humidity=equipment.humidity || {};
      const sources=[
        thermal.entity_id ? '<span>'+escape(l.selectedDevice)+': <b>'+
          escape(thermal.entity_id)+'</b></span>' : '',
        wet.entity_id ? '<span>'+escape(l.humidity)+': <b>'+
          escape(wet.entity_id)+'</b></span>' : '',
      ].filter(Boolean).join('');
      const controllerDetails=controllers.filter((part)=>
        part.status!=='advisory_only' && part.status!=='disabled').map((part)=>
        '<small>'+escape(part.label)+': '+escape(this._controllerStatusLabel(part.status))+
        '</small>').join('');
      const humidityDetails=humidity.status==='advisory' ?
        '<small>'+escape(l.moistureAction)+': '+escape(this._controllerStatusLabel(humidity.action||'idle'))+
        (typeof humidity.measured_rh==='number' ?
          ' · '+escape(l.currentHumidity)+': '+escape(this._format(humidity.measured_rh))+'%' : '')+
        ' · '+escape(l.sourceStatus)+': '+escape(this._controllerStatusLabel(equipment.humidity_evidence||'unknown'))+
        '</small>' : '';
      const air=p.air_actions || {};
      const extract=air.extraction || {};
      const filter=air.filtration || {};
      const airDetails=[
        extract.status==='recommended' ? l.extraction+': '+
          (extract.entity_id || l.advisory) : '',
        filter.status==='recommended' ? l.filtration+': '+
          (filter.entity_id || l.advisory) : '',
      ].filter(Boolean).map((v)=>'<small>'+escape(v)+'</small>').join('');
      const nativeAir=p.native_air_mode_advice || {};
      const dryAdvice=['manual_mode_transition_suggested',
        'manual_stop_dry_suggested'].includes(nativeAir.status) ?
        '<small>'+escape(l.manualDry)+': '+escape(this._controllerStatusLabel(nativeAir.recommended_mode||''))+
        ' · '+escape(nativeAir.climate_entity||'')+'</small>' : '';
      const windowPlan=p.window_efficiency || {};
      const windowAdvice=windowPlan.status==='opportunity' ?
        '<small>'+escape(l.windowHelp)+': '+
        escape(this._controllerStatusLabel(windowPlan.effect||''))+' · '+
        escape(String(windowPlan.active_device||''))+
        '</small>' : '';
      const coordinator=p.coordination || {};
      const purposes=coordinator.channels || {};
      const priorities={
        measured_co2_ventilation:l.co2Priority,
        measured_particle_filtration:l.particlePriority,
        temperature_comfort:l.temperaturePriority,
        humidity_management:l.humidityPriority,
        safety:l.safetyPriority,
        hold_or_no_demand:l.noPriority,
      };
      const priorityDetail=coordinator.priority ?
        '<small>'+escape(l.priority)+': '+
        escape(priorities[coordinator.priority] || l.noPriority)+'</small>' : '';
      const heldDetails=Object.entries(purposes)
        .filter(([,data])=>data?.status==='held').slice(0,3)
        .map(([kind,data])=>'<small>'+escape(l.heldPurpose)+' · '+
          escape(this._controllerStatusLabel(kind))+': '+escape(this._controllerStatusLabel(data.reason||'unverified'))+
          '</small>').join('');
      const reason=(p.reason==='secondary_thermal_driver_pending' && active)
        ? '' : p.reason==='environment_only_no_hvac' ? l.environmentOnly
          : (p.reason ? this._controllerStatusLabel(p.reason) : '');
      const measuredTemp=typeof p.temperature_c==='number'
        ? '<span>'+escape(l.roomTemperature)+': <b>'+
          escape(this._format(p.temperature_c))+' °C</b></span>'
        : '<span>'+escape(l.temperatureMissing)+'</span>';
      const selected=p.temperature_evidence || {};
      const sourceDiagnostic=p.temperature_c==null && selected.status &&
        selected.status!=='ready' ? '<small>'+escape(this._controllerStatusLabel(selected.status))+
          (selected.entity_ids?.length ? ' · '+
            escape(selected.entity_ids.slice(0,3).join(', ')) : '')+
          '</small>' : '';
      return '<section class="pid-panel" aria-label="'+escape(l.title)+'">'+
        '<div class="pid-title">'+this._icon('mdi:thermostat')+
        '<strong>'+escape(l.title)+'</strong><span>'+escape(title)+'</span></div>'+
        '<div class="pid-metrics">'+
        (p.controller==='environment' ? '' :
          '<span>'+escape(l.target)+': <b>'+escape(target)+'</b></span>'+
          '<span>'+escape(l.mode)+': <b>'+escape(p.mode||'-')+'</b></span>')+
        '<span>'+escape(l[p.profile] || p.profile || 'home')+'</span>'+sources+'</div>'+
        '<div class="hem-room-readings66">'+measuredTemp+this._roomHumidity66(room)+'</div>'+sourceDiagnostic+
        controllerDetails+priorityDetail+heldDetails+
        humidityDetails+airDetails+dryAdvice+windowAdvice+
        (blocked?'<small>'+escape(l.holding)+'</small>':'')+
        (reason?'<small>'+escape(reason)+'</small>':'')+
        controls+this._controllerPanel(room)+'</section>';
    }

    _pidPanel(room) {
      const pid = room?.environment?.climate_pid || {};
      if (!pid.status || pid.status === 'disabled') return '';
      const l = PID_LABELS[this._language()] || PID_LABELS.en;
      const active = ['controlling','at_device_setpoint'].includes(pid.status);
      const paused = pid.status === 'paused';
      const title = paused ? l.paused : active ? l.active : l.pending;
      const metrics = [];
      const show = (title,value)=> metrics.push('<span class="pid-metric">'+escape(title)+
                                              ': <strong>'+escape(value)+'</strong></span>');
      if (typeof pid.target_c === 'number') show(l.target,this._format(pid.target_c)+' °C');
      if (typeof pid.demand_percent === 'number') show(l.effort,this._format(pid.demand_percent)+'%');
      if (typeof pid.desired_setpoint_c === 'number') show(l.requested,this._format(pid.desired_setpoint_c)+' °C');
      const action = paused ? 'resume' : 'pause';
      const button = paused || active ? '<button type="button" class="pid-button" data-pid-area="' +
        escape(room.area_id) + '" data-pid-action="'+action+'">'+escape(paused ? l.resume : l.pause)+'</button>' : '';
      return '<section class="pid-panel"><div class="pid-title">' +
        this._icon('mdi:thermostat')+'<strong>'+escape(l.title)+'</strong><span>'+escape(title)+
        '</span></div><div class="pid-metrics">'+metrics.join('')+'</div>'+
        '<small>'+escape(this._controllerStatusLabel(pid.status))+'</small>'+
        '<small>'+escape(l.caution)+'</small>'+button+'</section>';
    }

    _shadingEvidence(area) {
      const snapshot=this._dashboardData || this._state()[1]?.attributes?.dashboard;
      const rooms=safeArray(snapshot?.rooms);
      return rooms.find((room)=>room?.area_id===area)?.environment?.shade_cooling || null;
    }

    _shadingSwitch(area) {
      const found=Object.entries(this._hass?.states || {}).filter(([id,state])=>
        id.startsWith('switch.') && state?.attributes?.area_id===area &&
        state.attributes.close_only === true &&
        Array.isArray(state.attributes.selected_shades));
      return found.length===1?{id:found[0][0],state:found[0][1]}:null;
    }

    _shadePanel(room) {
      const report=room?.environment?.shade_cooling;
      const covers=safeArray(report?.selected_covers).filter((id)=>
        typeof id==='string' && id.startsWith('cover.'));
      if (!covers.length) return '';
      const lang=this._language();
      const words={
        en:['Solar shade cooling','Enabled','Disabled','Open shade details',
            'Closes in sunny weather; reopens only after a confirmed automatic close. Manual opening pauses this shade until you turn room shading off and on again.',
            'Room','Sun','Status','Weather','Manual override: disable then re-enable room shading'],
        el:['Ηλιακή σκίαση για ψύξη','Ενεργό','Ανενεργό','Άνοιγμα στοιχείων σκίασης',
            'Κλείνει με ηλιοφάνεια και ανοίγει μόνο σκίαστρα που έκλεισε το ίδιο. Το χειροκίνητο άνοιγμα σταματά τον αυτοματισμό μέχρι να τον απενεργοποιήσεις και να τον ενεργοποιήσεις ξανά.',
            'Δωμάτιο','Ήλιος','Κατάσταση','Καιρός','Χειροκίνητη παρέμβαση: απενεργοποίησε και ενεργοποίησε ξανά'],
        de:['Solare Beschattung zur Kühlung','Ein','Aus','Beschattung anzeigen',
            'Schließt bei Sonne; öffnet nur zuvor bestätigt automatisch geschlossene Rollos. Manuelles Öffnen sperrt das Rollo bis zum Aus- und Einschalten der Automatik.',
            'Raum','Sonne','Status','Wetter','Manuelle Sperre: Automatik aus- und wieder einschalten'],
      }[lang] || ['Solar shade cooling','Enabled','Disabled','Open shade details',
        'Close in sun and reopen only shades this controller confirmed closing. A manual opening latches until explicit re-enable.',
        'Room','Sun','Status','Weather','Manual override: toggle shading off and back on'];
      const managed=this._shadingSwitch(room.area_id);
      const enabled=managed?.state?.state==='on';
      const toggle=managed?'<button type="button" data-shade-switch="'+escape(managed.id)+
        '" data-shade-area="'+escape(room.area_id)+'" class="shade-toggle">'+
        escape(enabled?words[1]:words[2])+'</button>':'';
      const status=this._controllerStatusLabel(report.status||'disabled');
      const list=covers.map((entityId)=>{
        const state=this._hass?.states?.[entityId];
        const title=state?.attributes?.friendly_name || entityId;
        const result=report.covers?.[entityId];
        return '<button type="button" class="shade-source" data-open-shade="'+
          escape(entityId)+'" data-shade-area="'+escape(room.area_id)+'" '+
          'title="'+escape(entityId)+'">'+escape(title)+
          ' · '+escape(result||state?.state||'unknown')+'</button>';
      }).join('');
      const details=[
        typeof report.temperature_c==='number' ? words[5]+' '+
          this._format(report.temperature_c)+' °C' : '',
        typeof report.sun_elevation==='number' ? words[6]+' '+
          this._format(report.sun_elevation)+'°' : '',
        Object.keys(report.weather_conditions || {}).length
          ? words[8]+' '+Object.values(report.weather_conditions).join(', ')
          : '',
      ].filter(Boolean).join(' · ');
      const manual=Object.values(report.covers || {}).some(value=>
        value==='manual_override'||value==='legacy_manual_hold');
      return '<section class="shade-panel" aria-label="'+escape(words[0])+'">'+
        '<div class="shade-heading">'+this._icon('mdi:blinds')+
        '<strong>'+escape(words[0])+'</strong>'+toggle+'</div>'+
        '<small>'+escape(words[4])+'</small>'+
        '<div class="shade-status">'+escape(words[7])+': '+escape(status)+
        (details?' · '+escape(details):'')+'</div>'+
        (manual?'<small role="status">'+escape(words[9])+'</small>':'')+
        '<div class="shade-sources">'+list+'</div></section>';
    }

    _room(room) {
      if (room?.climate_only === true) {
        const labels=CLIMATE_LABELS[this._language()] || CLIMATE_LABELS.en;
        return `<article class="room room-climate-only">
          <div class="room-heading">
            <div class="room-icon">${this._icon('mdi:thermostat')}</div>
            <div class="room-main"><h3>${escape(room.name)}</h3>
              <span>${escape(labels.title)}</span></div>
            ${this._editButton(room.area_id)}
          </div>
          ${this._climatePanel(room)}
          ${this._shadePanel(room)}
        </article>`;
      }
      const status = ['safe','attention','unknown'].includes(room.status) ? room.status : 'unknown';
      const readings = safeArray(room.readings);
      const windows = safeArray(room.windows);
      const moldReading = readings.find((item) => item.metric === 'mold' && !item.available);
      const moldCalibration = readings.find((item) => item.metric === 'mold' &&
        typeof item.details?.calibration_factor === 'number' &&
        Number.isFinite(item.details.calibration_factor));
      const rhFallback = room.rh_fallback?.active === true
        ? `<div class="rh-fallback" role="note">
          ${this._icon('mdi:water-percent')}
          <span><b>${escape(RH_FALLBACK_TEXT[this._language()] || RH_FALLBACK_TEXT.en)}</b>
          · ${escape(this._format(room.rh_fallback.value))}%
          · ${escape(this._t('limits'))} ${escape(this._format(room.rh_fallback.threshold))}%</span>
        </div>` : '';
      const moldWarnings = safeArray(room.mold_warnings).filter(
        (code) => ['calibration','indoor_temperature','outdoor_temperature',
                   'humidity','calculation'].includes(code)
      );
      const sourceDetails = moldReading?.details || {};
      const warningList = moldWarnings.length
        ? `<div class="mold-warnings" role="status">
          ${moldWarnings.map((code) => {
            const source = code === 'outdoor_temperature'
              ? sourceDetails.outdoor_weather_entity
              : code === 'indoor_temperature'
                ? sourceDetails.indoor_temperature_entity : null;
            return `<div class="mold-warning">
              ${this._icon('mdi:alert-outline')}
              <span>${escape(this._moldInputWarning(code))}${source
                ? ` <small>(${escape(source)})</small>` : ''}</span>
            </div>`;
          }).join('')}
        </div>` : '';
      const expanded = this._expanded.has(String(room.area_id));
      const shown = expanded ? readings : readings.slice(0,3);
      const button = (readings.length > 3 || moldCalibration) &&
        this._config.show_metrics !== false ? `<button type="button" class="expand" data-expand="${escape(room.area_id)}"
        aria-expanded="${expanded}">${escape(this._t(expanded ? 'less' : 'more'))} ${this._icon(expanded ? 'mdi:chevron-up' : 'mdi:chevron-down')}</button>` : '';
      const urgent = room.action === 'close';
      const actionable = room.action === 'open' || urgent;
      const recommendation = actionable
        ? `<div class="advice advice-${urgent ? 'close' : 'open'}">${this._icon(urgent ? 'mdi:window-closed-variant' : 'mdi:window-open-variant')}
            <span><b>${escape(this._t(urgent ? 'closeAdvice' : 'openAdvice'))}</b><small>${escape(windows
              .filter((win) => safeArray(room.action_window_ids).includes(win.entity_id))
              .map((win) => win.name).join(' · '))}</small></span></div>`
        : status === 'attention' && room.ventilating
          ? `<div class="advice advice-ventilating">${this._icon('mdi:air-filter')}${escape(this._t('ventilating'))}</div>`
          : status === 'attention' && room.high_count > 0 && !room.ventilating
            ? `<div class="advice advice-blocked">${this._icon('mdi:alert-circle-outline')}${escape(this._t('notSafeToOpen'))}</div>`
            : '';
      const availableCount = safeArray(room.readings).filter((item) =>
        item.available === true && typeof item.value === 'number'
      ).length;
      const roomStatusLabel = status === 'unknown' && availableCount > 0
        ? this._t('partial') : this._t(status);
      const subheading = room.high_count > 0 ? this._t('indoorHigh')
        : status === 'unknown' && room.status_detail === 'mold_not_calibrated'
          ? this._t('moldNotCalibrated')
        : status === 'unknown' && room.status_detail === 'mold_inputs_unavailable'
          ? this._t('moldInputsUnavailable')
        : status === 'unknown' && availableCount > 0
          ? this._t('partial')
        : status === 'unknown' ? this._t('missingIndoor')
          : this._t('allOkay');
      return `<article class="room room-${status}">
        <div class="room-heading">
          <div class="room-icon">${this._icon(status === 'safe' ? 'mdi:home-check-outline' : status === 'attention' ? 'mdi:home-alert-outline' : 'mdi:home-outline')}</div>
          <div class="room-main"><h3>${escape(room.name)}</h3><span>${escape(subheading)}</span></div>
          ${this._editButton(room.area_id)}
          <span class="status-tag">${this._icon(ICON[status])}${escape(roomStatusLabel)}</span>
        </div>
        ${this._config.show_metrics === false ? '' : readings.length ? `<div class="metric-grid">${shown.map((item) => this._metric(item)).join('')}</div>`
          : `<div class="empty-measurements">${this._icon('mdi:gauge-empty')} ${escape(this._t('missingIndoor'))}</div>`}
        ${button}
        ${expanded && this._config.show_metrics !== false
          ? this._moldCalibrationDetails(moldCalibration) : ''}
        ${this._climatePanel(room)}
        ${this._shadePanel(room)}
        ${this._pidPanel(room)}
        ${this._config.show_science === false ? '' : this._environmentReport(room)}
        ${rhFallback}
        ${warningList}
        <div class="window-section">
          <span class="field-label">${this._icon('mdi:window-closed-variant')}${escape(this._t('windows'))}</span>
          ${windows.length ? `<div class="window-list">${windows.map((window) => this._window(window)).join('')}</div>`
            : `<span class="subdued">${escape(this._t('noWindows'))}</span>`}
        </div>
        ${recommendation}
      </article>`;
    }

    _render(force = false) {
      if (!this._hass || !this._config) return;
      if (this._focusedEditor) {
        this._pendingRender = true;
        this._pendingForceRender = this._pendingForceRender || force;
        return; // Never replace an open native select / unfinished input.
      }
      try {
        this._renderContent(force);
        this._lastRenderError = null;
      } catch (error) {
        // A transient malformed/partial HA snapshot must not cause Lovelace's
        // generic broken-card error or poison the cache until a hard refresh.
        const message = String(error?.message || error);
        if (message !== this._lastRenderError) {
          console.warn('Home Environment Manager card update will retry', error);
        }
        this._lastRenderError = message;
        this._lastState = null;
        this._shownControllerSignature = null;
        this._lastConfigKey = null;
        const notice = this._language()==='el'
          ? 'Προσωρινό πρόβλημα δεδομένων. Αυτόματη επαναφορά.'
          : this._language()==='de'
            ? 'Daten vorübergehend nicht verfügbar. Automatischer neuer Versuch.'
            : 'Data temporarily unavailable. Retrying automatically.';
        const card = this._hasValidRender && this.shadowRoot.querySelector?.('ha-card');
        if (card) {
          card.setAttribute('aria-busy','true');
          if (!card.querySelector?.('[data-card-recovery]')) {
            card.insertAdjacentHTML?.('afterbegin',
              '<div data-card-recovery role="status" style="padding:12px">'+
              escape(notice)+'</div>');
          }
        } else {
          this.shadowRoot.innerHTML = '<ha-card><div role="status" style="padding:20px">'+
            escape(notice)+'</div></ha-card>';
        }
      }
    }

    _renderContent(force = false) {
      const [entity, state] = this._state();
      const lang = this._language();
      const key = JSON.stringify(this._config);
      const controllerSignature = this._controllerSignature();
      if (!force && this._lastState === state && this._shownEntity === entity &&
          this._shownLanguage === lang && this._lastConfigKey === key &&
          this._shownControllerSignature === controllerSignature) return;
      const inline = state?.attributes?.dashboard;
      const data = inline?.version === 1 ? inline :
        this._dashboardEntity === entity ? this._dashboardData : null;
      if (!data || data.version !== 1) {
        this.shadowRoot.innerHTML = `${this._styles()}<ha-card class="shell" dir="${RTL_LANGUAGES.has(lang) ? 'rtl' : 'ltr'}"><div class="empty-state">
        ${this._icon('mdi:air-filter')}<h3>${escape(this._t('title'))}</h3><p>${escape(
          state?.attributes?.dashboard_api==='environment_manager/dashboard'
            ? (lang==='el' ? 'Φόρτωση δεδομένων δωματίων…'
               : lang==='de' ? 'Raumdaten werden geladen…'
               : 'Loading room data…')
            : this._t('missingCard'))}</p></div></ha-card>`;
        // Keep retrying when the recommended sensor is still starting:
        // HA may later supply the dashboard on the same card instance.
        this._lastState = null;
        this._hasValidRender = false;
        return;
      }
      const rooms = safeArray(data.rooms).filter((room)=>room &&
        typeof room==='object' && typeof room.area_id==='string').slice().sort((a,b) =>
        ({attention:0,unknown:1,safe:2}[a.status] ?? 3) - ({attention:0,unknown:1,safe:2}[b.status] ?? 3) ||
        String(a.name).localeCompare(String(b.name), this._hass.language));
      this.shadowRoot.innerHTML = `${this._styles()}<ha-card class="shell" dir="${RTL_LANGUAGES.has(lang) ? 'rtl' : 'ltr'}">
        <header class="card-heading"><div><div class="overline">HOME ASSISTANT</div>
        <h2>${escape(this._config.title || this._t('title'))}</h2><span>${escape(this._t('subtitle'))}</span></div>
        <div class="header-actions"><button class="edit-device" type="button" data-edit-home
          aria-label="${escape(this._deviceEditLabel(true))}" title="${escape(this._deviceEditLabel(true))}"
          ${this._homeDeviceId ? '' : 'disabled'}>${this._icon('mdi:cog-outline')}</button>
        <div class="card-logo">${this._icon('mdi:air-filter')}</div></div></header>
        <div class="content">
          ${this._outside(data.outdoor || {})}
          ${this._pollenIndicator(data.outdoor || {})}
          ${this._summary(data.summary || {})}
          <div class="rooms-list">${rooms.length ? rooms.map((room) => this._room(room)).join('')
            : `<div class="empty-rooms">${this._icon('mdi:home-outline')}${escape(this._t('noRooms'))}</div>`}</div>
          <footer>${this._icon('mdi:shield-check-outline')} ${escape(this._t('sourceData'))}</footer>
        </div>
      </ha-card>`;
      // Commit the cache only after the complete template was constructed
      // and applied. A failed render must be retried on the next HA update.
      this._shownControllerSignature = controllerSignature;
      this._lastState = state;
      this._shownEntity = entity;
      this._shownLanguage = lang;
      this._lastConfigKey = key;
      this._hasValidRender = true;
    }

    _styles() { return `<style>
      :host{display:block;--aqa-green:#1f9d77;--aqa-amber:#df9143;--aqa-red:#df6d55;--aqa-blue:#499bb9;
        --aqa-muted:var(--secondary-text-color,#78848f);--aqa-text:var(--primary-text-color,#1a313d);
        --aqa-surface:var(--card-background-color,#fff);--aqa-edge:var(--divider-color,rgba(110,135,145,.17));
        font-family:var(--paper-font-body1_-_font-family,Roboto,Arial,sans-serif);color:var(--aqa-text)}
      .shell{overflow:hidden;border-radius:22px;background:var(--aqa-surface);box-shadow:var(--ha-card-box-shadow,0 2px 16px rgba(0,0,0,.06))}
      .card-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:24px 26px 20px}
      .header-actions{display:flex;gap:8px;align-items:center}
      .edit-device{display:inline-grid;place-items:center;flex:0 0 auto;min-width:32px;height:32px;
        padding:5px;border:1px solid var(--aqa-edge);border-radius:10px;cursor:pointer;
        background:var(--aqa-surface);color:var(--aqa-blue)}
      .edit-device ha-icon{--mdc-icon-size:19px}
      .edit-device:disabled{opacity:.35;cursor:not-allowed}
      .edit-device:focus-visible{outline:2px solid var(--aqa-blue);outline-offset:2px}
      .overline{color:var(--aqa-blue);font-size:10px;letter-spacing:2.2px;font-weight:800;margin-bottom:5px}
      h2{font-size:25px;line-height:1.15;margin:0 0 5px;font-weight:780;letter-spacing:-.8px}
      .card-heading span{color:var(--aqa-muted);font-size:12px}
      .card-logo{width:50px;height:50px;border-radius:15px;display:grid;place-items:center;
        background:color-mix(in srgb,var(--aqa-blue),transparent 87%);color:var(--aqa-blue)}
      .card-logo ha-icon{--mdc-icon-size:28px}
      .content{padding:0 20px 14px}
      .outside{position:relative;border:1px solid var(--aqa-edge);border-radius:18px;padding:18px 18px 16px;
        background:linear-gradient(115deg,color-mix(in srgb,var(--aqa-blue),transparent 92%),color-mix(in srgb,var(--aqa-green),transparent 95%));}
      .outside-safe{border-color:color-mix(in srgb,var(--aqa-green),transparent 71%)}
      .outside-unsafe{background:linear-gradient(115deg,color-mix(in srgb,var(--aqa-red),transparent 87%),color-mix(in srgb,var(--aqa-amber),transparent 94%));
        border-color:color-mix(in srgb,var(--aqa-red),transparent 62%)}
      .outside-partial,.outside-unknown{background:color-mix(in srgb,var(--aqa-amber),transparent 93%)}
      .outdoor-head{display:flex;gap:15px;align-items:center}
      .outdoor-icon{height:61px;width:61px;flex:0 0 61px;border-radius:17px;display:grid;place-items:center;
        background:color-mix(in srgb,var(--aqa-blue),transparent 81%);color:var(--aqa-blue)}
      .outside-unsafe .outdoor-icon{background:color-mix(in srgb,var(--aqa-red),transparent 82%);color:var(--aqa-red)}
      .outdoor-icon ha-icon{--mdc-icon-size:36px}
      .outdoor-text{flex:1;min-width:0}
      .eyebrow{display:block;font-size:11px;letter-spacing:.7px;text-transform:uppercase;color:var(--aqa-muted);font-weight:700}
      .outside-title{font-size:17px;font-weight:750;letter-spacing:-.25px;line-height:1.25;margin:5px 0}
      .weather-line{display:flex;align-items:center;gap:9px;flex-wrap:wrap;color:var(--aqa-muted);font-size:12px}
      .weather-line strong{font-size:15px;color:var(--aqa-text);font-weight:750}
      .weather-line span{display:inline-flex;align-items:center;gap:3px}
      .weather-line span ha-icon{--mdc-icon-size:15px}
      .weather-line .sep{margin:0 3px;color:var(--aqa-muted)}
      .outdoor-status{color:var(--aqa-green);align-self:flex-start}
      .outside-unsafe .outdoor-status{color:var(--aqa-red)}
      .outside-unknown .outdoor-status,.outside-partial .outdoor-status{color:var(--aqa-amber)}
      .out-metrics{display:flex;flex-wrap:wrap;gap:7px;margin-top:15px;padding-top:12px;border-top:1px solid var(--aqa-edge)}
      .out-chip{font-size:11px;padding:7px 10px;border-radius:9px;background:var(--aqa-surface);border:1px solid var(--aqa-edge);white-space:nowrap;color:var(--aqa-muted)}
      .out-chip b{color:var(--aqa-text);font-size:13px;margin-left:5px}
      .out-chip small{font-size:10px}
      .out-chip.elevated{border-color:color-mix(in srgb,var(--aqa-red),transparent 51%);color:var(--aqa-red)}
      .out-chip.dim{opacity:.68}
      .out-empty{font-size:12px;color:var(--aqa-muted);margin-top:14px}
      .outside-alerts{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
      .reason{display:inline-flex;align-items:center;gap:5px;padding:6px 8px;border-radius:9px;
        font-size:11px;background:color-mix(in srgb,var(--aqa-red),transparent 90%);color:var(--aqa-text)}
      .reason ha-icon{--mdc-icon-size:15px;color:var(--aqa-red)}
      .section-head{display:flex;justify-content:space-between;align-items:center;margin:22px 4px 12px}
      .section-title{font-size:13px;font-weight:790;display:inline-flex;align-items:center;gap:8px}
      .section-title ha-icon{--mdc-icon-size:19px;color:var(--aqa-blue)}
      .subdued{font-size:12px;color:var(--aqa-muted)}
      .overview{display:flex;gap:22px;align-items:center;padding:17px 18px;background:color-mix(in srgb,var(--aqa-muted),transparent 96%);
        border-radius:16px;border:1px solid var(--aqa-edge)}
      .donut-wrap{display:flex;align-items:center;justify-content:center}
      .donut{width:103px;height:103px;border-radius:50%;padding:12px;box-sizing:border-box;
        background:conic-gradient(var(--aqa-green) 0 var(--good-end),var(--aqa-amber) var(--good-end) var(--attention-end),
        color-mix(in srgb,var(--aqa-muted),transparent 56%) var(--attention-end) 100%);}
      .donut-inner{background:var(--aqa-surface);border-radius:50%;height:100%;display:flex;flex-direction:column;justify-content:center;
        align-items:center;gap:0;box-shadow:0 0 0 2px var(--aqa-surface)}
      .donut-inner strong{font-size:30px;line-height:1;font-weight:770}
      .donut-inner span{font-size:10px;color:var(--aqa-muted);margin-top:5px}
      .counts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));flex:1;gap:9px}
      .count{display:flex;flex-direction:column;min-width:0;padding:5px 9px;align-items:center;border-left:1px solid var(--aqa-edge)}
      .count-icon ha-icon{--mdc-icon-size:21px;color:var(--aqa-green)}
      .count-attention .count-icon ha-icon{color:var(--aqa-amber)}
      .count-unknown .count-icon ha-icon{color:var(--aqa-muted)}
      .count strong{font-size:24px;font-weight:750;line-height:1.2;margin-top:3px}
      .count small{font-size:10px;color:var(--aqa-muted);text-align:center;line-height:1.3}
      .rooms-list{display:grid;gap:12px;margin-top:15px;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));align-items:start}
      .room{padding:16px;border-radius:16px;border:1px solid var(--aqa-edge);background:var(--aqa-surface);min-width:0}
      .room-attention{border-color:color-mix(in srgb,var(--aqa-amber),transparent 60%);
        background:linear-gradient(150deg,color-mix(in srgb,var(--aqa-amber),transparent 96%),var(--aqa-surface) 65%)}
      .room-heading{display:flex;gap:10px;align-items:center;min-width:0;margin-bottom:13px}
      .room-icon{height:37px;width:37px;border-radius:12px;background:color-mix(in srgb,var(--aqa-green),transparent 89%);
        color:var(--aqa-green);display:grid;place-items:center;flex-shrink:0}
      .room-attention .room-icon{background:color-mix(in srgb,var(--aqa-amber),transparent 85%);color:var(--aqa-amber)}
      .room-unknown .room-icon{background:color-mix(in srgb,var(--aqa-muted),transparent 88%);color:var(--aqa-muted)}
      .shade-panel{margin-top:12px;padding:11px;border:1px solid var(--aqa-edge);
        background:color-mix(in srgb,var(--aqa-blue),transparent 96%);border-radius:12px;
        display:grid;gap:6px;min-width:0}
      .shade-panel small,.shade-status{color:var(--aqa-muted);font-size:11px;line-height:1.4}
      .shade-heading{display:flex;gap:7px;align-items:center;flex-wrap:wrap;font-size:12px}
      .shade-heading ha-icon{--mdc-icon-size:18px;color:var(--aqa-blue)}
      .shade-toggle{margin-inline-start:auto;border:1px solid var(--aqa-edge);
        border-radius:9px;background:var(--aqa-surface);padding:6px 9px;color:var(--aqa-text);
        font-size:11px;cursor:pointer}
      .shade-sources{display:flex;gap:5px;flex-wrap:wrap}
      .shade-source{min-width:0;max-width:100%;white-space:normal;overflow-wrap:anywhere;
        color:var(--aqa-text);font-size:11px;background:var(--aqa-surface);
        border-radius:8px;border:1px solid var(--aqa-edge);padding:5px 7px;cursor:pointer}
      .room-main{min-width:0;flex:1}
      .room-main h3{margin:0;font-size:14px;line-height:1.35;font-weight:760;overflow-wrap:anywhere}
      .room-main span{display:block;color:var(--aqa-muted);font-size:10px;line-height:1.35;margin-top:2px}
      .status-tag{display:inline-flex;gap:3px;align-items:center;border-radius:999px;padding:5px 8px;white-space:nowrap;font-size:10px;font-weight:750;
        color:var(--aqa-green);background:color-mix(in srgb,var(--aqa-green),transparent 88%)}
      .status-tag ha-icon{--mdc-icon-size:13px}
      .room-attention .status-tag{color:var(--aqa-amber);background:color-mix(in srgb,var(--aqa-amber),transparent 88%)}
      .room-unknown .status-tag{color:var(--aqa-muted);background:color-mix(in srgb,var(--aqa-muted),transparent 88%)}
      .rh-fallback{display:flex;align-items:flex-start;gap:7px;margin:10px 0;
        padding:9px 10px;border-radius:10px;font-size:11px;line-height:1.4;
        border:1px solid color-mix(in srgb,var(--aqa-blue),transparent 70%);
        background:color-mix(in srgb,var(--aqa-blue),transparent 93%)}
      .rh-fallback ha-icon{flex:0 0 auto;--mdc-icon-size:16px;color:var(--aqa-blue)}
      .rh-fallback b{font-weight:700}
      .mold-warnings{display:grid;gap:6px;margin:11px 0;padding:10px;border-radius:10px;
        background:color-mix(in srgb,var(--aqa-amber),transparent 91%);
        border:1px solid color-mix(in srgb,var(--aqa-amber),transparent 72%)}
      .mold-warning{display:flex;align-items:flex-start;gap:7px;color:var(--aqa-text);font-size:11px;line-height:1.4}
      .mold-warning ha-icon{flex:0 0 auto;--mdc-icon-size:15px;color:var(--aqa-amber)}
      .mold-warning small{color:var(--aqa-muted)}
      .metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,125px),1fr));gap:9px}
      .pollen-indicator{display:flex;align-items:center;gap:7px;margin:12px 0;color:var(--aqa-text);padding:8px 12px;border:1px solid var(--aqa-edge);border-radius:11px;font-size:11px;background:color-mix(in srgb,var(--aqa-amber),transparent 96%)}
      .pollen-indicator ha-icon{color:var(--aqa-amber);--mdc-icon-size:18px}
      .pid-panel{border:1px solid var(--aqa-edge);border-radius:12px;padding:11px;margin:10px 0;background:color-mix(in srgb,var(--aqa-blue),transparent 94%)}
      .pid-title{display:flex;flex-wrap:wrap;align-items:center;gap:7px;font-size:12px}
      .pid-title span{margin-inline-start:auto;color:var(--aqa-muted);font-size:11px}
      .pid-metrics{display:flex;flex-wrap:wrap;gap:7px 14px;margin:8px 0;font-size:11px}
      .pid-panel small{font-size:10px;line-height:1.4;color:var(--aqa-muted);display:block}
      .pid-button{padding:6px 10px;border:1px solid var(--aqa-edge);background:var(--aqa-surface);color:var(--aqa-text);border-radius:8px;cursor:pointer;margin-top:9px}
      .pid-button:focus-visible{outline:2px solid var(--aqa-blue)}
      .managed-controllers{display:grid;gap:9px;margin-top:12px;border-top:1px solid var(--aqa-edge);padding-top:10px}
      .managed-controllers>strong{font-size:11px}
      .managed-controller{padding:9px;border:1px solid var(--aqa-edge);border-radius:11px;
        background:var(--aqa-surface);min-width:0}
      .climate-entity-link{display:flex;align-items:center;gap:6px;max-width:100%;cursor:pointer;
        border:0;background:transparent;color:var(--aqa-text);padding:3px;font-size:11px;text-align:start}
      .climate-entity-link strong{overflow-wrap:anywhere}
      .climate-entity-link ha-icon{--mdc-icon-size:16px;color:var(--aqa-blue);flex:0 0 auto}
      .managed-status{font-size:10px;color:var(--aqa-muted);margin:5px 0 9px;overflow-wrap:anywhere}
      .managed-method-label,.climate-target-editor label{display:grid;gap:5px;font-size:10px}
      .managed-method-label select,.climate-target-editor input{border:1px solid var(--aqa-edge);
        border-radius:8px;background:var(--aqa-surface);color:var(--aqa-text);padding:7px;
        font:inherit;max-width:100%;min-width:0}
      .climate-target-editor{display:flex;align-items:end;gap:8px;flex-wrap:wrap;margin-top:9px}
      .climate-target-editor label{flex:1 1 120px}
      .climate-target-editor button{padding:7px 9px;border:1px solid var(--aqa-blue);border-radius:8px;
        background:var(--aqa-surface);color:var(--aqa-blue);cursor:pointer;font-size:10px}
      .climate-edit-error{color:var(--aqa-red)!important}
      .science-section{margin:10px 0 12px;padding:11px 12px;border:1px solid var(--aqa-edge);border-radius:12px;background:color-mix(in srgb,var(--aqa-blue),transparent 97%)}
      .science-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:6px 12px;margin-top:8px}
      .science-line{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11px;border-bottom:1px solid var(--aqa-edge);padding:5px 0}
      .science-line span{color:var(--aqa-muted);line-height:1.3}.science-line strong{font-size:12px;text-align:end;white-space:nowrap}
      .science-caveat{color:var(--aqa-muted);font-size:10px;line-height:1.3;margin-top:8px}
      .metric{border-radius:11px;background:color-mix(in srgb,var(--aqa-muted),transparent 96%);border:1px solid var(--aqa-edge);padding:10px;min-width:0}
      .metric-attention{border-color:color-mix(in srgb,var(--aqa-amber),transparent 66%)}
      .metric-line{display:flex;align-items:flex-start;gap:7px;justify-content:space-between;flex-wrap:wrap}
      .metric-name{font-size:10px;color:var(--aqa-muted);display:flex;align-items:flex-start;gap:5px;
        font-weight:700;min-width:0;width:100%;max-width:100%}
      .metric-name>ha-icon{--mdc-icon-size:15px;flex:0 0 15px}
      .metric-title{min-width:0;flex:1 1 auto;max-width:100%;overflow:hidden;overflow-wrap:anywhere;
        display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-height:1.3;white-space:normal}
      .metric-help{display:inline-flex;position:relative;align-items:center;flex:0 0 auto;
        margin-inline-start:auto}
      .metric-help summary{display:flex;align-items:center;cursor:pointer;list-style:none;color:var(--primary-color,#03a9f4);padding:2px}
      .metric-help summary::-webkit-details-marker{display:none}
      .metric-help-content{position:absolute;z-index:25;top:100%;left:-30px;width:min(280px,72vw);padding:12px;border-radius:12px;box-shadow:0 6px 24px #0006;background:var(--card-background-color,#20252b);color:var(--primary-text-color,#fff);font-size:12px;line-height:1.5;font-weight:400;white-space:normal}
      .metric-help[open] summary{color:var(--accent-color,#00bcd4)}

      .metric-number{font-size:15px;font-weight:760;white-space:nowrap;line-height:1.2;
        margin-inline-start:auto;min-width:0;max-width:100%}
      .metric-number small{font-size:9px;color:var(--aqa-muted);font-weight:500}
      .meter{position:relative;display:block;height:6px;border-radius:99px;margin-top:11px;background:color-mix(in srgb,var(--aqa-muted),transparent 80%);overflow:hidden}
      .meter-fill{height:100%;display:block;background:var(--aqa-green);border-radius:99px;transition:width .35s ease}
      .metric-attention .meter-fill{background:var(--aqa-amber)}
      .meter-limit{position:absolute;right:1px;top:0;height:100%;width:1px;background:var(--aqa-text);opacity:.24}
      .metric-limit{color:var(--aqa-muted);font-size:9px;line-height:1.3;margin-top:5px}
      .mold-summary{display:grid;gap:3px;margin-top:7px;color:var(--aqa-muted);
        font-size:9px;line-height:1.4;overflow-wrap:anywhere}
      .mold-calibration-details{display:grid;gap:7px;margin-top:9px;padding:10px;
        border:1px solid var(--aqa-edge);border-radius:10px;
        background:color-mix(in srgb,var(--aqa-muted),transparent 96%);font-size:11px}
      .mold-calibration-details>div{display:flex;align-items:baseline;
        justify-content:space-between;gap:10px;flex-wrap:wrap}
      .mold-calibration-details span{color:var(--aqa-muted)}
      .mold-calibration-details strong{font-weight:700;color:var(--aqa-text);
        overflow-wrap:anywhere;word-break:break-word}
      .expand{display:inline-flex;gap:3px;align-items:center;margin:10px 0 0;padding:4px 2px;
        background:none;border:0;color:var(--primary-color,var(--aqa-blue));cursor:pointer;font-size:11px;font-weight:700}
      .expand ha-icon{--mdc-icon-size:15px}
      .expand:focus-visible{outline:2px solid var(--primary-color,var(--aqa-blue));border-radius:4px}
      .window-section{margin-top:12px;padding-top:11px;border-top:1px solid var(--aqa-edge)}
      .field-label{display:inline-flex;align-items:center;gap:5px;font-weight:740;font-size:10px;text-transform:uppercase;
        letter-spacing:.6px;color:var(--aqa-muted);margin-bottom:8px}
      .field-label ha-icon{--mdc-icon-size:14px}
      .window-list{display:flex;flex-wrap:wrap;gap:6px}
      .window{display:inline-flex;align-items:center;gap:4px;border-radius:8px;padding:5px 7px;background:color-mix(in srgb,var(--aqa-muted),transparent 92%);
        font-size:10px;line-height:1.3;max-width:100%;overflow-wrap:anywhere}
      .window ha-icon{--mdc-icon-size:15px}
      .window.opened ha-icon{color:var(--aqa-green)}
      .window.unknown ha-icon{color:var(--aqa-amber)}
      .window small{color:var(--aqa-muted);white-space:nowrap}
      .advice{display:flex;align-items:center;gap:10px;padding:11px;margin-top:13px;border-radius:10px;font-size:12px;
        background:color-mix(in srgb,var(--aqa-blue),transparent 89%);color:var(--aqa-text)}
      .advice ha-icon{color:var(--aqa-blue);--mdc-icon-size:21px;flex-shrink:0}
      .advice-close,.advice-blocked{background:color-mix(in srgb,var(--aqa-red),transparent 89%)}
      .advice-close ha-icon,.advice-blocked ha-icon{color:var(--aqa-red)}
      .advice-ventilating{background:color-mix(in srgb,var(--aqa-green),transparent 90%)}
      .advice-ventilating ha-icon{color:var(--aqa-green)}
      .advice b{font-weight:750;display:block}
      .advice small{font-size:10px;display:block;opacity:.76;margin-top:3px;overflow-wrap:anywhere}
      .empty-measurements,.empty-rooms{border:1px dashed var(--aqa-edge);color:var(--aqa-muted);font-size:12px;
        padding:14px;border-radius:10px;display:flex;align-items:center;gap:9px}
      .empty-state{text-align:center;padding:32px 24px;color:var(--aqa-muted)}
      .empty-state ha-icon{color:var(--aqa-blue);--mdc-icon-size:36px}
      .empty-state h3{color:var(--aqa-text);margin:12px 0 5px}
      .empty-rooms{grid-column:1/-1;justify-content:center;padding:30px}
      footer{display:flex;gap:5px;align-items:center;justify-content:center;color:var(--aqa-muted);font-size:10px;padding:17px 8px 4px;text-align:center}
      footer ha-icon{--mdc-icon-size:14px}
      @media(max-width:420px){.card-heading{padding:19px 18px 16px}h2{font-size:22px}.content{padding:0 12px 12px}
        .outside{padding:13px}.outdoor-icon{height:48px;width:48px;flex-basis:48px;border-radius:13px}.outdoor-icon ha-icon{--mdc-icon-size:29px}
        .outside-title{font-size:15px}.overview{gap:8px;padding:12px 8px}.donut{width:89px;height:89px;padding:10px}
        .counts{gap:0}.count{padding:5px 3px}.count strong{font-size:20px}.room{padding:13px}}
      @media(prefers-reduced-motion:reduce){.meter-fill{transition:none}}
    </style>`; }
  }

  class AirQualityAdvisorCardEditor extends HTMLElement {
    constructor() { super(); this.attachShadow({mode:'open'}); this._config={}; }
    set hass(hass) { this._hass=hass; this._render(); }
    setConfig(config) { this._config={...config}; this._render(); }
    _render() {
      if (!this._hass) return;
      const lang = cardLanguage(this._hass.language);
      this.setAttribute('dir', RTL_LANGUAGES.has(lang) ? 'rtl' : 'ltr');
      const texts = LANGUAGE[lang] || LANGUAGE.en;
      const t = (key) => key === "title" ? BRAND_TITLE : (texts[key] || LANGUAGE.en[key]);
      const found = detected(this._hass);
      const chosen = this._config.entity || (found.length===1 ? found[0] : '');
      this.shadowRoot.innerHTML = `<style>:host{display:block;padding:8px 0}label{display:block;margin:10px 0;font:inherit;font-size:13px}
        select,input{box-sizing:border-box;width:100%;font:inherit;background:var(--card-background-color,#fff);
          border:1px solid var(--divider-color,#ddd);border-radius:8px;padding:12px;color:var(--primary-text-color,#222)}
        .tick{display:flex;align-items:center;gap:8px}.tick input{width:auto}</style>
        <label>${escape(t('title'))}<select data-setting="entity"><option value="">${escape(t('missingCard'))}</option>
        ${found.map((id) => `<option value="${escape(id)}" ${id===chosen?'selected':''}>${escape(this._hass.states[id]?.attributes?.friendly_name || id)}</option>`).join('')}</select></label>
        <label>${escape(t('title'))}<input data-setting="title" type="text" value="${escape(this._config.title || '')}" /></label>
        <label class="tick"><input type="checkbox" data-setting="show_outside" ${this._config.show_outside!==false?'checked':''}>${escape(t('outside'))}</label>
        <label class="tick"><input type="checkbox" data-setting="show_metrics" ${this._config.show_metrics!==false?'checked':''}>${escape(t('readings'))}</label>
        <label class="tick"><input type="checkbox" data-setting="show_science" ${this._config.show_science!==false?'checked':''}>${escape(SCIENCE_LABELS[lang]?.title || SCIENCE_LABELS.en.title)}</label>`;
      this.shadowRoot.querySelectorAll('[data-setting]').forEach((field) => {
        field.addEventListener('change', () => {
          const prop = field.dataset.setting;
          const value = field.type === 'checkbox' ? field.checked : field.value;
          this._config = {...this._config,[prop]:value};
          if (prop === 'entity' && !value) delete this._config.entity;
          this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:{...this._config}},bubbles:true,composed:true}));
        });
      });
    }
  }

/* HEM_CARD65_START */
  // Single bundled locale catalog: no per-render network fetch or filesystem I/O.
  const CARD65 = {"ar":{"text":{"overview":"نظرة عامة على الغرفة","devices":"وحدات تحكم الأجهزة","calibration":"المعايرة","details":"التشخيص","physical":"الجهاز الفعلي","target":"الهدف","demand":"الطلب","supply":"مصدر الطاقة","cooldown":"تأخير الفصل","sleep":"إيقاف أثناء النوم","reason":"السبب","lux":"شدة الإضاءة","idle":"خامل","mean":"متوسط المستشعرات المختارة","partialMean":"متوسط المستشعرات المتاحة","inputs":"أدخل قياسات صحيحة لكل مستوى","ready":"جاهز","unconfigured":"غير مهيأ","information":"معلومات","save":"حفظ","apply":"تطبيق","gain":"كسب العملية","timeConstant":"الثابت الزمني","deadTime":"زمن التأخير","speed":"سرعة المروحة","capacity":"القدرة النسبية","stage":"المستوى","waiting":"انتظار","summaryHelp":"ملخص الغرفة. لكل جهاز أدناه وحدة تحكم مستقلة.","luxHelp":"يقيس اللوكس الضوء المحيط، وليس جودة الهواء أو حرارة الشمس. يُستخدم لمراقبة الإضاءة وضوء النهار.","dataHelp":"تأتي القراءات من المستشعرات المختارة. تحقق من الوحدات وحداثة البيانات والمعايرة.","calHelp":"المعايرة اختيارية. استخدم قياسات فعلية؛ أعلى سرعة للمروحة هي مرجع 100%.","heat":"تدفئة","cool":"تبريد","dry":"إزالة الرطوبة","fan":"مروحة","choose":"اختر الوضع","on":"يعمل","off":"متوقف","unknown":"غير معروف","legacyStrategy":"الأصلي (غير معاير)","measuredStrategy":"نموذج القدرة المقاسة","estimateHelp":"تعتمد التقديرات على قراءات المستشعرات وافتراضات النموذج. البيانات المفقودة أو السجل غير الكافي لا يدعمان نتيجة موثوقة.","awayProfile":"خارج المنزل","comfortProfile":"راحة","ecoProfile":"توفير الطاقة"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"خارج المنزل","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"التحكم التلقائي نشط","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"المنزل","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"بانتظار الحد الأدنى الآمن لوقت الإيقاف","minimum_on_hold":"إبقاء الجهاز قيد التشغيل حتى اكتمال الحد الأدنى الآمن","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"التحكم التلقائي متوقف مؤقتًا","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"يطلب المتحكم PID تشغيل المخرج لكنه لا يزال متوقفًا","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"تعذّر التحقق مما إذا كانت الغرفة في وضع النوم","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"بانتظار انتهاء فحوص بدء التشغيل","storage_unavailable":"تعذّر تحميل سجل الأمان؛ تم تعليق التحكم التلقائي","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"ضمن النطاق المستهدف المحدد","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"خامل","selected_mean":"متوسط المستشعرات المختارة","selected_sensor":"متوسط المستشعرات المختارة","selected_partial_mean":"متوسط المستشعرات المتاحة","selected_partial_sensor":"متوسط المستشعرات المتاحة","room_selected_mean":"متوسط المستشعرات المختارة","complete_measured_stage_capacities_required":"أدخل قياسات صحيحة لكل مستوى","not_configured":"غير مهيأ","environment_only_no_hvac":"ملخص الغرفة. لكل جهاز أدناه وحدة تحكم مستقلة.","sleep":"النوم","comfort":"راحة","eco":"توفير الطاقة"},"words":{"outside":"خارجي","general":"عام","area":"منطقة","settings":"الإعدادات","devices":"الأجهزة","pollen":"حبوب اللقاح","room":"غرفة","house":"المنزل","sleep":"النوم","presence":"الإشغال","automatic":"تلقائي","control":"التحكم","select":"اختيار","sensor":"مستشعر","source":"المصدر","off":"إيقاف","hold":"تعليق","temperature":"الحرارة","humidity":"الرطوبة","required":"مطلوب","invalid":"غير صالح","speed":"السرعة","power":"الطاقة","target":"الهدف"},"profiles":{"none":"تلقائي","home":"المنزل","sleep":"النوم","away":"خارج المنزل","comfort":"راحة","eco":"توفير الطاقة"},"methods":{"existing":"متحكم الغرفة الحالي","automatic":"تلقائي","manual":"يدوي","off":"إيقاف","pid":"PID"},"methodLabel":"التحكم · طريقة التحكم"},"bg":{"text":{"overview":"Преглед на стаята","devices":"Контролери на устройствата","calibration":"Калибриране","details":"Диагностика","physical":"Физическо устройство","target":"Цел","demand":"Потребност","supply":"Захранване","cooldown":"Забавяне преди изключване","sleep":"Пауза при сън","reason":"Причина","lux":"Осветеност","idle":"Покой","mean":"Средно от избраните сензори","partialMean":"Средно от наличните сензори","inputs":"Въведете валидни измервания за всяка степен","ready":"Готово","unconfigured":"Не е настроено","information":"Информация","save":"Запази","apply":"Приложи","gain":"Усилване на процеса","timeConstant":"Времеконстанта","deadTime":"Мъртво време","speed":"Скорост на вентилатора","capacity":"Относителна мощност","stage":"Степен","waiting":"Изчакване","summaryHelp":"Обобщение на стаята. Всяко устройство по-долу има собствен контролер.","luxHelp":"Лукс измерва околната светлина, не качеството на въздуха или слънчевата топлина. Използва се за наблюдение на осветлението.","dataHelp":"Стойностите са от избрани сензори. Проверете единиците, актуалността и калибрирането.","calHelp":"Калибрирането е по избор. Използвайте реални измервания; максималната скорост на вентилатора е 100%.","heat":"Отопление","cool":"Охлаждане","dry":"Изсушаване","fan":"Вентилатор","choose":"Избор на режим","on":"Включено","off":"Изключено","unknown":"Неизвестно","legacyStrategy":"Първоначално (некалибрирано)","measuredStrategy":"Модел на измерена мощност","estimateHelp":"Оценките използват измервания и допускания на модела. Липсващи данни или недостатъчна история не дават надежден резултат.","awayProfile":"Отсъствие","comfortProfile":"Комфорт","ecoProfile":"Пестене на енергия"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Отсъствие","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Автоматичното управление е активно","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Дом","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Изчакване на минималното безопасно време за изключване","minimum_on_hold":"Уредът остава включен за минималното безопасно време","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Автоматичното управление е на пауза","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID изисква работа, но изходът е изключен","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Не може да се потвърди дали стаята е в режим за сън","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Изчакване на проверките след стартиране","storage_unavailable":"Историята за безопасност не може да се зареди; управлението е спряно","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"В зададения целеви диапазон","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Покой","selected_mean":"Средно от избраните сензори","selected_sensor":"Средно от избраните сензори","selected_partial_mean":"Средно от наличните сензори","selected_partial_sensor":"Средно от наличните сензори","room_selected_mean":"Средно от избраните сензори","complete_measured_stage_capacities_required":"Въведете валидни измервания за всяка степен","not_configured":"Не е настроено","environment_only_no_hvac":"Обобщение на стаята. Всяко устройство по-долу има собствен контролер.","sleep":"Сън","comfort":"Комфорт","eco":"Пестене на енергия"},"words":{"outside":"Външни","general":"Общи","area":"Зона","settings":"настройки","devices":"Устройства","pollen":"Полени","room":"Стая","house":"Дом","sleep":"Сън","presence":"Присъствие","automatic":"Автоматично","control":"управление","select":"Избор","sensor":"сензор","source":"източник","off":"Изключване","hold":"Пауза","temperature":"Температура","humidity":"Влажност","required":"Задължително","invalid":"Невалидно","speed":"Скорост","power":"Мощност","target":"цел"},"profiles":{"none":"Автоматично","home":"Дом","sleep":"Сън","away":"Отсъствие","comfort":"Комфорт","eco":"Пестене на енергия"},"methods":{"existing":"Съществуващ контролер на стаята","automatic":"Автоматично","manual":"Ръчно","off":"Изключване","pid":"PID"},"methodLabel":"Управление · Метод на управление"},"bn":{"text":{"overview":"ঘরের সারাংশ","devices":"যন্ত্রের নিয়ন্ত্রক","calibration":"ক্রমাঙ্কন","details":"ত্রুটি নির্ণয়","physical":"প্রকৃত যন্ত্র","target":"লক্ষ্য","demand":"চাহিদা","supply":"বিদ্যুৎ সরবরাহ","cooldown":"বন্ধ করার বিলম্ব","sleep":"ঘুমের সময় বিরতি","reason":"কারণ","lux":"আলোকমাত্রা","idle":"নিষ্ক্রিয়","mean":"নির্বাচিত সেন্সরের গড়","partialMean":"উপলব্ধ সেন্সরের গড়","inputs":"প্রতিটি ধাপের জন্য বৈধ পরিমাপ লিখুন","ready":"প্রস্তুত","unconfigured":"কনফিগার করা হয়নি","information":"তথ্য","save":"সংরক্ষণ","apply":"প্রয়োগ","gain":"প্রক্রিয়ার গেইন","timeConstant":"সময় ধ্রুবক","deadTime":"বিলম্বকাল","speed":"পাখার গতি","capacity":"আপেক্ষিক ক্ষমতা","stage":"ধাপ","waiting":"অপেক্ষা","summaryHelp":"ঘরের সারাংশ। নিচের প্রতিটি যন্ত্রের নিজস্ব নিয়ন্ত্রক আছে।","luxHelp":"লাক্স পরিবেশের আলো মাপে, বাতাসের মান বা সূর্যের তাপ নয়। এটি আলো পর্যবেক্ষণে ব্যবহৃত হয়।","dataHelp":"পাঠ নির্বাচিত সেন্সর থেকে আসে। একক, সাম্প্রতিকতা ও ক্রমাঙ্কন যাচাই করুন।","calHelp":"ক্রমাঙ্কন ঐচ্ছিক। প্রকৃত পরিমাপ ব্যবহার করুন; পাখার সর্বোচ্চ গতি 100% রেফারেন্স।","heat":"গরম করা","cool":"ঠান্ডা করা","dry":"আর্দ্রতা অপসারণ","fan":"পাখা","choose":"মোড বাছুন","on":"চালু","off":"বন্ধ","unknown":"অজানা","legacyStrategy":"মূল (ক্রমাঙ্কন ছাড়া)","measuredStrategy":"পরিমাপ করা ক্ষমতার মডেল","estimateHelp":"অনুমান সেন্সরের পাঠ ও মডেলের ধারণা ব্যবহার করে। অনুপস্থিত তথ্য বা অপর্যাপ্ত ইতিহাস নির্ভরযোগ্য ফল দেয় না।","awayProfile":"বাড়ির বাইরে","comfortProfile":"আরাম","ecoProfile":"শক্তি সাশ্রয়"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"বাড়ির বাইরে","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"স্বয়ংক্রিয় নিয়ন্ত্রণ সক্রিয়","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"বাড়ি","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"নিরাপদ ন্যূনতম বন্ধ থাকার সময়ের অপেক্ষায়","minimum_on_hold":"নিরাপদ ন্যূনতম সময় পর্যন্ত যন্ত্র চালু রাখা হচ্ছে","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"স্বয়ংক্রিয় নিয়ন্ত্রণ সাময়িকভাবে বন্ধ","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID কাজের অনুরোধ করছে, কিন্তু আউটপুট বন্ধ রয়েছে","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"এই ঘর ঘুমের মোডে আছে কি না নিশ্চিত করা যাচ্ছে না","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"শুরুর নিরাপত্তা পরীক্ষা শেষ হওয়ার অপেক্ষায়","storage_unavailable":"সুরক্ষা ইতিহাস লোড হয়নি; স্বয়ংক্রিয় নিয়ন্ত্রণ স্থগিত","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"নির্ধারিত লক্ষ্যমাত্রার সীমার মধ্যে","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"নিষ্ক্রিয়","selected_mean":"নির্বাচিত সেন্সরের গড়","selected_sensor":"নির্বাচিত সেন্সরের গড়","selected_partial_mean":"উপলব্ধ সেন্সরের গড়","selected_partial_sensor":"উপলব্ধ সেন্সরের গড়","room_selected_mean":"নির্বাচিত সেন্সরের গড়","complete_measured_stage_capacities_required":"প্রতিটি ধাপের জন্য বৈধ পরিমাপ লিখুন","not_configured":"কনফিগার করা হয়নি","environment_only_no_hvac":"ঘরের সারাংশ। নিচের প্রতিটি যন্ত্রের নিজস্ব নিয়ন্ত্রক আছে।","sleep":"ঘুম","comfort":"আরাম","eco":"শক্তি সাশ্রয়"},"words":{"outside":"বাইরের","general":"সাধারণ","area":"এলাকা","settings":"সেটিংস","devices":"ডিভাইস","pollen":"পরাগ","room":"ঘর","house":"বাড়ি","sleep":"ঘুম","presence":"উপস্থিতি","automatic":"স্বয়ংক্রিয়","control":"নিয়ন্ত্রণ","select":"নির্বাচন","sensor":"সেন্সর","source":"উৎস","off":"বন্ধ","hold":"বিরতি","temperature":"তাপমাত্রা","humidity":"আর্দ্রতা","required":"আবশ্যক","invalid":"অবৈধ","speed":"গতি","power":"শক্তি","target":"লক্ষ্য"},"profiles":{"none":"স্বয়ংক্রিয়","home":"বাড়ি","sleep":"ঘুম","away":"বাড়ির বাইরে","comfort":"আরাম","eco":"শক্তি সাশ্রয়"},"methods":{"existing":"বিদ্যমান ঘরের নিয়ন্ত্রক","automatic":"স্বয়ংক্রিয়","manual":"ম্যানুয়াল","off":"বন্ধ","pid":"PID"},"methodLabel":"নিয়ন্ত্রণ · নিয়ন্ত্রণ পদ্ধতি"},"cs":{"text":{"overview":"Přehled místnosti","devices":"Řadiče zařízení","calibration":"Kalibrace","details":"Diagnostika","physical":"Fyzické zařízení","target":"Cíl","demand":"Požadavek","supply":"Napájení","cooldown":"Prodleva před vypnutím","sleep":"Pauza při spánku","reason":"Důvod","lux":"Osvětlenost","idle":"Nečinnost","mean":"Průměr vybraných senzorů","partialMean":"Průměr dostupných senzorů","inputs":"Zadejte platná měření pro každý stupeň","ready":"Připraveno","unconfigured":"Nenastaveno","information":"Informace","save":"Uložit","apply":"Použít","gain":"Zesílení procesu","timeConstant":"Časová konstanta","deadTime":"Dopravní zpoždění","speed":"Otáčky ventilátoru","capacity":"Relativní výkon","stage":"Stupeň","waiting":"Čekání","summaryHelp":"Souhrn místnosti. Každé zařízení níže má vlastní řadič.","luxHelp":"Lux měří okolní světlo, nikoli kvalitu vzduchu nebo sluneční teplo. Slouží ke sledování osvětlení.","dataHelp":"Hodnoty pocházejí z vybraných senzorů. Ověřte jednotky, aktuálnost a kalibraci.","calHelp":"Kalibrace je volitelná. Použijte skutečná měření; nejvyšší otáčky ventilátoru jsou referencí 100%.","heat":"Topení","cool":"Chlazení","dry":"Odvlhčování","fan":"Ventilátor","choose":"Vybrat režim","on":"Zapnuto","off":"Vypnuto","unknown":"Neznámé","legacyStrategy":"Původní (nekalibrované)","measuredStrategy":"Model změřeného výkonu","estimateHelp":"Odhady používají naměřené údaje a předpoklady modelu. Chybějící vstupy nebo nedostatečná historie neumožňují spolehlivý výsledek.","awayProfile":"Nepřítomnost","comfortProfile":"Pohodlí","ecoProfile":"Úspora energie"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Nepřítomnost","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatické řízení je aktivní","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Domov","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Čekání na minimální bezpečnou dobu vypnutí","minimum_on_hold":"Zařízení zůstává zapnuté po minimální bezpečnou dobu","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatické řízení je pozastaveno","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID požaduje činnost, ale výstup je vypnutý","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nelze ověřit, zda je místnost v režimu spánku","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Čekání na dokončení kontrol po spuštění","storage_unavailable":"Nelze načíst bezpečnostní historii; řízení je pozastaveno","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"V nastaveném cílovém rozsahu","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Nečinnost","selected_mean":"Průměr vybraných senzorů","selected_sensor":"Průměr vybraných senzorů","selected_partial_mean":"Průměr dostupných senzorů","selected_partial_sensor":"Průměr dostupných senzorů","room_selected_mean":"Průměr vybraných senzorů","complete_measured_stage_capacities_required":"Zadejte platná měření pro každý stupeň","not_configured":"Nenastaveno","environment_only_no_hvac":"Souhrn místnosti. Každé zařízení níže má vlastní řadič.","sleep":"Spánek","comfort":"Pohodlí","eco":"Úspora energie"},"words":{"outside":"Venkovní","general":"Obecná","area":"Oblast","settings":"nastavení","devices":"Zařízení","pollen":"Pyl","room":"Místnost","house":"Domov","sleep":"Spánek","presence":"Obsazenost","automatic":"Automatické","control":"řízení","select":"Vybrat","sensor":"senzor","source":"zdroj","off":"Vypnout","hold":"Pozastavit","temperature":"Teplota","humidity":"Vlhkost","required":"Povinné","invalid":"Neplatné","speed":"Rychlost","power":"Výkon","target":"cíl"},"profiles":{"none":"Automatické","home":"Domov","sleep":"Spánek","away":"Nepřítomnost","comfort":"Pohodlí","eco":"Úspora energie"},"methods":{"existing":"Stávající regulátor místnosti","automatic":"Automatické","manual":"Ručně","off":"Vypnout","pid":"PID"},"methodLabel":"Ovládání · Způsob řízení"},"da":{"text":{"overview":"Rumoversigt","devices":"Enhedsregulatorer","calibration":"Kalibrering","details":"Diagnostik","physical":"Fysisk enhed","target":"Mål","demand":"Behov","supply":"Strømforsyning","cooldown":"Forsinkelse før slukning","sleep":"Søvnpause","reason":"Årsag","lux":"Belysningsstyrke","idle":"Hvile","mean":"Gennemsnit af valgte sensorer","partialMean":"Gennemsnit af tilgængelige sensorer","inputs":"Indtast gyldige målinger for hvert trin","ready":"Klar","unconfigured":"Ikke konfigureret","information":"Information","save":"Gem","apply":"Anvend","gain":"Procesforstærkning","timeConstant":"Tidskonstant","deadTime":"Dødtid","speed":"Blæserhastighed","capacity":"Relativ kapacitet","stage":"Trin","waiting":"Venter","summaryHelp":"Rumoversigt. Hver enhed nedenfor har sin egen regulator.","luxHelp":"Lux måler omgivende lys, ikke luftkvalitet eller solvarme. Det bruges til overvågning af lys og dagslys.","dataHelp":"Målingerne kommer fra valgte sensorer. Kontroller enheder, aktualitet og kalibrering.","calHelp":"Kalibrering er valgfri. Brug faktiske målinger; højeste blæserhastighed er referencen på 100%.","heat":"Opvarmning","cool":"Køling","dry":"Affugtning","fan":"Blæser","choose":"Vælg tilstand","on":"Tændt","off":"Slukket","unknown":"Ukendt","legacyStrategy":"Oprindelig (ukalibreret)","measuredStrategy":"Model for målt kapacitet","estimateHelp":"Estimater bruger sensormålinger og modelantagelser. Manglende data eller utilstrækkelig historik giver ikke pålidelige resultater.","awayProfile":"Ude","comfortProfile":"Komfort","ecoProfile":"Energibesparelse"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Ude","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatisk regulering aktiv","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Hjem","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Venter på den sikre minimumstid, hvor enheden skal være slukket","minimum_on_hold":"Enheden forbliver tændt i den sikre minimumstid","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatisk regulering sat på pause","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID kræver drift, men udgangen er slukket","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Kan ikke bekræfte, om rummet er i søvntilstand","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Venter på at opstartskontrollerne bliver færdige","storage_unavailable":"Sikkerhedshistorik kunne ikke indlæses; reguleringen er suspenderet","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Inden for det indstillede målområde","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Hvile","selected_mean":"Gennemsnit af valgte sensorer","selected_sensor":"Gennemsnit af valgte sensorer","selected_partial_mean":"Gennemsnit af tilgængelige sensorer","selected_partial_sensor":"Gennemsnit af tilgængelige sensorer","room_selected_mean":"Gennemsnit af valgte sensorer","complete_measured_stage_capacities_required":"Indtast gyldige målinger for hvert trin","not_configured":"Ikke konfigureret","environment_only_no_hvac":"Rumoversigt. Hver enhed nedenfor har sin egen regulator.","sleep":"Søvn","comfort":"Komfort","eco":"Energibesparelse"},"words":{"outside":"Udendørs","general":"Generelle","area":"Område","settings":"indstillinger","devices":"Enheder","pollen":"Pollen","room":"Rum","house":"Hjem","sleep":"Søvn","presence":"Tilstedeværelse","automatic":"Automatisk","control":"styring","select":"Vælg","sensor":"sensor","source":"kilde","off":"Sluk","hold":"Pause","temperature":"Temperatur","humidity":"Luftfugtighed","required":"Påkrævet","invalid":"Ugyldig","speed":"Hastighed","power":"Effekt","target":"mål"},"profiles":{"none":"Automatisk","home":"Hjem","sleep":"Søvn","away":"Ude","comfort":"Komfort","eco":"Energibesparelse"},"methods":{"existing":"Eksisterende rumregulering","automatic":"Automatisk","manual":"Manuel","off":"Sluk","pid":"PID"},"methodLabel":"Styring · Reguleringsmetode"},"de":{"text":{"overview":"Raumübersicht","devices":"Geräteregler","calibration":"Kalibrierung","details":"Diagnose","physical":"Physisches Gerät","target":"Zielwert","demand":"Bedarf","supply":"Stromversorgung","cooldown":"Nachlaufzeit","sleep":"Schlafpause","reason":"Grund","lux":"Beleuchtungsstärke","idle":"Leerlauf","mean":"Mittelwert ausgewählter Sensoren","partialMean":"Mittelwert verfügbarer Sensoren","inputs":"Gültige Messwerte für jede Stufe eingeben","ready":"Bereit","unconfigured":"Nicht konfiguriert","information":"Information","save":"Speichern","apply":"Anwenden","gain":"Prozessverstärkung","timeConstant":"Zeitkonstante","deadTime":"Totzeit","speed":"Lüfterdrehzahl","capacity":"Relative Leistung","stage":"Stufe","waiting":"Warten","summaryHelp":"Nur Raumübersicht. Jedes Gerät unten hat einen eigenen Regler.","luxHelp":"Lux misst Umgebungslicht, nicht Luftqualität oder Sonnenwärme. Es dient der Licht- und Tageslichtauswertung.","dataHelp":"Messwerte stammen von ausgewählten Sensoren. Einheiten, Aktualität und Kalibrierung beachten.","calHelp":"Kalibrierung ist optional. Reale Messwerte verwenden; die höchste Lüfterstufe entspricht 100%.","heat":"Heizen","cool":"Kühlen","dry":"Entfeuchten","fan":"Lüfter","choose":"Betriebsart wählen","on":"Ein","off":"Aus","unknown":"Unbekannt","legacyStrategy":"Bisherig (unkalibriert)","measuredStrategy":"Gemessenes Leistungsmodell","estimateHelp":"Schätzungen verwenden Sensordaten und Modellannahmen. Fehlende Eingaben oder zu wenig Verlauf erlauben keine verlässliche Aussage.","awayProfile":"Abwesend","comfortProfile":"Komfort","ecoProfile":"Energiesparen"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Warte auf die erste Reglerauswertung","awaiting_physical_acknowledgement":"Warte auf physische Zustandsbestätigung","away":"Abwesend","command_sent":"Befehl gesendet; warte auf Bestätigung","control_measurement_missing_or_stale":"Regelmesswert fehlt oder ist veraltet","controller_inactive":"Regler ist nicht aktiv","controller_paused":"Regler ist pausiert","controlling":"Automatische Regelung ist aktiv","cooling_priority_defer_dehumidifier":"Kühlen hat Vorrang; Entfeuchtung wartet","existing":"Gerät wird durch die vorhandene Integration gesteuert","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Zuhause","inactive":"Regler ist nicht aktiv","manual":"Manuelle Gerätesteuerung","manual_no_request":"Manueller Modus; keine Änderung angefordert","minimum_off_hold":"Warte auf die sichere Mindest-Ausschaltzeit","minimum_on_hold":"Gerät bleibt bis zum Ablauf der Mindestlaufzeit eingeschaltet","native_defrost_protection":"Gerät taut ab; Ausgangsänderung gesperrt","native_off_no_power_permission":"Gerät ist aus; automatisches Einschalten nicht erlaubt","native_power_mode_unsupported":"Gewünschte Gerätebetriebsart nicht unterstützt","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Aktueller Gerätesollwert nicht verfügbar","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Regler ausgeschaltet","open_or_unknown_window":"Fenster geöffnet oder Zustand unbekannt","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatische Regelung ist pausiert","physical_capabilities_unavailable":"Geräteeigenschaften konnten nicht gelesen werden","physical_device_unavailable":"Physisches Gerät nicht verfügbar","pid_output_inactive":"PID-Anforderung vorhanden, Ausgang ist derzeit ausgeschaltet","power_control_not_commissioned":"Automatisches Schalten nicht freigegeben","proportional_output_not_commissioned":"Proportionalregelung nicht freigegeben","proportional_output_not_verified":"Grenzen des Proportionalausgangs nicht geprüft","quiet_context_unknown":"Bedingungen für Ruhemodus nicht bestätigt","ready":"Ready","reconciled_waiting_minimum_off":"Gerät überprüft; Neustart erst nach Mindest-Ausschaltzeit","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Raum ist nachweislich leer","running_device_requires_off_before_automatic_power_ownership":"Laufendes Gerät vor Übernahme durch die Automatik ausschalten","select_control_method_to_authorize_current_device_sources":"Autorisierte Regelmethode für dieses Gerät auswählen","select_fan_purpose_on_controller_device":"Lüfterzweck auswählen: Abluft oder Filterung","select_single_direction_for_pid":"Für PID Heizen oder Kühlen auswählen","settings_updated":"Reglereinstellungen gespeichert","sleep_room_evidence_unknown":"Der Schlafstatus dieses Zimmers kann nicht bestätigt werden","source_deselected_or_moved":"Gerät ist diesem Raum nicht mehr zugeordnet","startup_warmup":"Warte auf Abschluss der Startprüfung","storage_unavailable":"Sicherheitsverlauf konnte nicht geladen werden; Regelung ausgesetzt","target_outside_device_limits":"Sollwert liegt außerhalb der Gerätegrenzen","target_outside_native_limits":"Sollwert liegt außerhalb des Betriebsbereichs","thermal_priority_defer_dry":"Heizen oder Kühlen hat Vorrang vor Entfeuchten","unrecognized_status":"Unbekannter Reglerzustand; status_code prüfen","unsupported_temperature_unit":"Temperatureinheit des Geräts nicht unterstützt","waiting_for_physical_device":"Warte auf Erreichbarkeit des physischen Geräts","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Innerhalb des eingestellten Zielbereichs","device_auto_control_disabled":"Automatische Steuerung für dieses Gerät deaktiviert","device_policy_approved":"Gerät zur automatischen Steuerung freigegeben","house_occupancy_unknown":"Nicht prüfbar, ob jemand zu Hause ist","house_unoccupied":"Niemand ist zu Hause","invalid_presence_policy":"Ungültige Anwesenheitsregel ausgewählt","invalid_sleep_policy":"Ungültige Schlafregel ausgewählt","room_not_absent":"Raum ist belegt; Abwesenheitssteuerung wartet","room_not_occupied":"Raum ist leer; Belegungssteuerung wartet","room_occupancy_unknown":"Raumbelegung kann nicht bestätigt werden","sleep_room_control_paused":"Regelung pausiert, weil der Raum im Schlafmodus ist","idle":"Leerlauf","selected_mean":"Mittelwert ausgewählter Sensoren","selected_sensor":"Mittelwert ausgewählter Sensoren","selected_partial_mean":"Mittelwert verfügbarer Sensoren","selected_partial_sensor":"Mittelwert verfügbarer Sensoren","room_selected_mean":"Mittelwert ausgewählter Sensoren","complete_measured_stage_capacities_required":"Gültige Messwerte für jede Stufe eingeben","not_configured":"Nicht konfiguriert","environment_only_no_hvac":"Nur Raumübersicht. Jedes Gerät unten hat einen eigenen Regler.","sleep":"Schlaf","comfort":"Komfort","eco":"Energiesparen"},"words":{"outside":"Außen","general":"Allgemeine","area":"Bereich","settings":"Einstellungen","devices":"Geräte","pollen":"Pollen","room":"Raum","house":"Zuhause","sleep":"Schlaf","presence":"Belegung","automatic":"Automatische","control":"Steuerung","select":"Auswählen","sensor":"Sensor","source":"Quelle","off":"Ausschalten","hold":"Pausieren","temperature":"Temperatur","humidity":"Luftfeuchtigkeit","required":"Erforderlich","invalid":"Ungültig","speed":"Geschwindigkeit","power":"Leistung","target":"Sollwert"},"profiles":{"none":"Automatische","home":"Zuhause","sleep":"Schlaf","away":"Abwesend","comfort":"Komfort","eco":"Energiesparen"},"methods":{"existing":"Bisherige Raumregelung","automatic":"Automatische","manual":"Manuell","off":"Ausschalten","pid":"PID"},"methodLabel":"Steuerung · Verfahren"},"el":{"text":{"overview":"Επισκόπηση δωματίου","devices":"Ελεγκτές συσκευών","calibration":"Βαθμονόμηση","details":"Διαγνωστικά","physical":"Φυσική συσκευή","target":"Στόχος","demand":"Ζήτηση","supply":"Τροφοδοσία","cooldown":"Χρόνος αναμονής απενεργοποίησης","sleep":"Παύση ύπνου","reason":"Αιτία","lux":"Φωτισμός","idle":"Αδράνεια","mean":"Μέσος όρος επιλεγμένων αισθητήρων","partialMean":"Μέσος όρος διαθέσιμων αισθητήρων","inputs":"Συμπλήρωσε έγκυρες μετρήσεις για κάθε βαθμίδα","ready":"Έτοιμο","unconfigured":"Δεν έχει ρυθμιστεί","information":"Πληροφορίες","save":"Αποθήκευση","apply":"Εφαρμογή","gain":"Κέρδος διεργασίας","timeConstant":"Χρονική σταθερά","deadTime":"Νεκρός χρόνος","speed":"Ταχύτητα ανεμιστήρα","capacity":"Σχετική απόδοση","stage":"Βαθμίδα","waiting":"Αναμονή","summaryHelp":"Σύνοψη δωματίου. Κάθε συσκευή παρακάτω έχει ανεξάρτητο ελεγκτή.","luxHelp":"Τα lux μετρούν τον φωτισμό, όχι την ποιότητα αέρα ή την ηλιακή θερμότητα. Χρησιμοποιούνται για την παρακολούθηση φωτός.","dataHelp":"Οι μετρήσεις προέρχονται από επιλεγμένους αισθητήρες. Έλεγξε τις μονάδες, την ενημέρωση και τη βαθμονόμηση.","calHelp":"Η βαθμονόμηση είναι προαιρετική. Χρησιμοποίησε πραγματικές μετρήσεις· η μέγιστη ταχύτητα ανεμιστήρα είναι η αναφορά 100%.","heat":"Θέρμανση","cool":"Ψύξη","dry":"Αφύγρανση","fan":"Ανεμιστήρας","choose":"Επιλογή λειτουργίας","on":"Ενεργό","off":"Ανενεργό","unknown":"Άγνωστο","legacyStrategy":"Αρχική κατανομή (χωρίς βαθμονόμηση)","measuredStrategy":"Μοντέλο μετρημένης απόδοσης","estimateHelp":"Οι εκτιμήσεις χρησιμοποιούν μετρήσεις αισθητήρων και παραδοχές μοντέλου. Ελλιπή δεδομένα ή ανεπαρκές ιστορικό δεν επιτρέπουν αξιόπιστο αποτέλεσμα.","awayProfile":"Απών","comfortProfile":"Άνεση","ecoProfile":"Εξοικονόμηση"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Αναμονή πρώτου ελέγχου λειτουργίας","awaiting_physical_acknowledgement":"Αναμονή επιβεβαίωσης κατάστασης συσκευής","away":"Απών","command_sent":"Η εντολή στάλθηκε· αναμονή επιβεβαίωσης","control_measurement_missing_or_stale":"Λείπει πρόσφατη και έγκυρη μέτρηση ελέγχου","controller_inactive":"Ο ελεγκτής δεν λειτουργεί","controller_paused":"Ο ελεγκτής βρίσκεται σε παύση","controlling":"Η αυτόματη ρύθμιση λειτουργεί","cooling_priority_defer_dehumidifier":"Προτεραιότητα στην ψύξη· η αφύγρανση περιμένει","existing":"Η συσκευή ελέγχεται από την υπάρχουσα ενσωμάτωση","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Σπίτι","inactive":"Ο ελεγκτής δεν λειτουργεί","manual":"Χειροκίνητος έλεγχος συσκευής","manual_no_request":"Χειροκίνητη λειτουργία χωρίς νέα εντολή","minimum_off_hold":"Αναμονή ελάχιστου ασφαλούς χρόνου εκτός λειτουργίας","minimum_on_hold":"Η συσκευή παραμένει ενεργή για τον ελάχιστο ασφαλή χρόνο","native_defrost_protection":"Η συσκευή κάνει απόψυξη· οι αλλαγές εμποδίζονται","native_off_no_power_permission":"Η συσκευή είναι κλειστή και δεν επιτρέπεται αυτόματη εκκίνηση","native_power_mode_unsupported":"Η ζητούμενη λειτουργία συσκευής δεν υποστηρίζεται","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Δεν είναι διαθέσιμος ο τρέχων στόχος θερμοκρασίας","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Ο ελεγκτής είναι απενεργοποιημένος","open_or_unknown_window":"Το παράθυρο είναι ανοιχτό ή άγνωστο","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Η αυτόματη λειτουργία έχει τεθεί σε παύση","physical_capabilities_unavailable":"Δεν είναι διαθέσιμες οι δυνατότητες της συσκευής","physical_device_unavailable":"Η φυσική συσκευή δεν είναι διαθέσιμη","pid_output_inactive":"Το PID ζητά θέρμανση ή ψύξη, αλλά η έξοδος παραμένει κλειστή","power_control_not_commissioned":"Δεν έχει εγκριθεί η αυτόματη ενεργοποίηση της συσκευής","proportional_output_not_commissioned":"Δεν έχει εγκριθεί ο αναλογικός έλεγχος εξόδου","proportional_output_not_verified":"Δεν έχουν επιβεβαιωθεί τα όρια της αναλογικής εξόδου","quiet_context_unknown":"Δεν επιβεβαιώνονται οι συνθήκες αθόρυβης λειτουργίας","ready":"Ready","reconciled_waiting_minimum_off":"Η συσκευή ελέγχθηκε· αναμονή για ασφαλή επανεκκίνηση","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Το δωμάτιο είναι άδειο","running_device_requires_off_before_automatic_power_ownership":"Κλείσε πρώτα τη συσκευή για ασφαλή ανάληψη αυτόματου ελέγχου","select_control_method_to_authorize_current_device_sources":"Επίλεξε εγκεκριμένη μέθοδο ελέγχου για τη συσκευή","select_fan_purpose_on_controller_device":"Επίλεξε αν ο ανεμιστήρας κάνει εξαγωγή ή φιλτράρισμα αέρα","select_single_direction_for_pid":"Επίλεξε θέρμανση ή ψύξη για το PID","settings_updated":"Οι ρυθμίσεις αποθηκεύτηκαν","sleep_room_evidence_unknown":"Δεν μπορεί να επιβεβαιωθεί αν το δωμάτιο βρίσκεται σε λειτουργία ύπνου","source_deselected_or_moved":"Η φυσική συσκευή δεν ανήκει πλέον σε αυτό το δωμάτιο","startup_warmup":"Αναμονή ολοκλήρωσης των ελέγχων εκκίνησης","storage_unavailable":"Αδυναμία ανάκτησης ιστορικού ασφαλείας· η αυτόματη λειτουργία αναστέλλεται","target_outside_device_limits":"Ο ζητούμενος στόχος ξεπερνά τα όρια της συσκευής","target_outside_native_limits":"Ο στόχος είναι εκτός ορίων λειτουργίας συσκευής","thermal_priority_defer_dry":"Η θέρμανση ή η ψύξη έχει προτεραιότητα από την αφύγρανση","unrecognized_status":"Άγνωστη κατάσταση ελεγκτή· έλεγξε το status_code","unsupported_temperature_unit":"Η μονάδα θερμοκρασίας της συσκευής δεν υποστηρίζεται","waiting_for_physical_device":"Αναμονή σύνδεσης της φυσικής συσκευής","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Εντός του καθορισμένου εύρους στόχου","device_auto_control_disabled":"Ο αυτόματος έλεγχος αυτής της συσκευής είναι απενεργοποιημένος","device_policy_approved":"Εγκρίθηκε ο αυτόματος έλεγχος της συσκευής","house_occupancy_unknown":"Δεν μπορεί να επιβεβαιωθεί αν υπάρχει κάποιος στο σπίτι","house_unoccupied":"Δεν βρίσκεται κανείς στο σπίτι","invalid_presence_policy":"Μη έγκυρος κανόνας παρουσίας","invalid_sleep_policy":"Μη έγκυρος κανόνας ύπνου","room_not_absent":"Υπάρχει παρουσία στο δωμάτιο· αναμονή ελέγχου απουσίας","room_not_occupied":"Το δωμάτιο είναι άδειο· αναμονή επιβεβαιωμένης παρουσίας","room_occupancy_unknown":"Δεν μπορεί να επιβεβαιωθεί η παρουσία στο δωμάτιο","sleep_room_control_paused":"Ο έλεγχος τέθηκε σε παύση λόγω λειτουργίας ύπνου","idle":"Αδράνεια","selected_mean":"Μέσος όρος επιλεγμένων αισθητήρων","selected_sensor":"Μέσος όρος επιλεγμένων αισθητήρων","selected_partial_mean":"Μέσος όρος διαθέσιμων αισθητήρων","selected_partial_sensor":"Μέσος όρος διαθέσιμων αισθητήρων","room_selected_mean":"Μέσος όρος επιλεγμένων αισθητήρων","complete_measured_stage_capacities_required":"Συμπλήρωσε έγκυρες μετρήσεις για κάθε βαθμίδα","not_configured":"Δεν έχει ρυθμιστεί","environment_only_no_hvac":"Σύνοψη δωματίου. Κάθε συσκευή παρακάτω έχει ανεξάρτητο ελεγκτή.","sleep":"Ύπνος","comfort":"Άνεση","eco":"Εξοικονόμηση"},"words":{"outside":"Εξωτερικά","general":"Γενικές","area":"Χώρου","settings":"ρυθμίσεις","devices":"Συσκευές","pollen":"Γύρη","room":"Δωμάτιο","house":"Σπίτι","sleep":"Ύπνος","presence":"Παρουσία","automatic":"Αυτόματος","control":"έλεγχος","select":"Επιλογή","sensor":"αισθητήρας","source":"πηγή","off":"Απενεργοποίηση","hold":"Παύση","temperature":"Θερμοκρασία","humidity":"Υγρασία","required":"Απαιτείται","invalid":"Μη έγκυρο","speed":"Ταχύτητα","power":"Ισχύς","target":"στόχος"},"profiles":{"none":"Αυτόματος","home":"Σπίτι","sleep":"Ύπνος","away":"Απών","comfort":"Άνεση","eco":"Εξοικονόμηση"},"methods":{"existing":"Υφιστάμενος ελεγκτής χώρου","automatic":"Αυτόματος","manual":"Χειροκίνητα","off":"Απενεργοποίηση","pid":"PID"},"methodLabel":"Έλεγχος · Μέθοδος"},"en":{"text":{"overview":"Room overview","devices":"Device controllers","calibration":"Calibration","details":"Diagnostics","physical":"Physical device","target":"Target","demand":"Demand","supply":"Power supply","cooldown":"Cooldown","sleep":"Sleep pause","reason":"Reason","lux":"Illuminance","idle":"Idle","mean":"Mean of selected sensors","partialMean":"Mean of available sensors","inputs":"Enter valid measurements for every stage","ready":"Ready","unconfigured":"Not configured","information":"Information","save":"Save","apply":"Apply","gain":"Process gain","timeConstant":"Time constant","deadTime":"Dead time","speed":"Fan speed","capacity":"Relative capacity","stage":"Stage","waiting":"Waiting","summaryHelp":"Room summary only. Each device below has its own controller.","luxHelp":"Lux measures ambient light, not air quality or solar heat. It is used for light-level and daylight reporting.","dataHelp":"Readings come from selected sensors. Check their units, freshness and calibration.","calHelp":"Calibration is optional. Use real measurements; the highest fan speed is the 100% reference.","heat":"Heating","cool":"Cooling","dry":"Drying","fan":"Fan","choose":"Choose mode","on":"On","off":"Off","unknown":"Unknown","legacyStrategy":"Original (uncalibrated)","measuredStrategy":"Measured capacity model","estimateHelp":"Estimates use sensor readings and model assumptions. Missing inputs or insufficient history cannot support a reliable result.","awayProfile":"Away","comfortProfile":"Comfort","ecoProfile":"Energy saving"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Away","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatic control is active","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Home","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Waiting for minimum safe OFF time before starting","minimum_on_hold":"Keeping equipment on until minimum runtime is met","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatic control is paused","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID demand is present, but the output is off","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Unable to confirm whether this room is sleeping","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Waiting for startup checks to finish","storage_unavailable":"Safety history could not be loaded; automatic control is suspended","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Within the configured target range","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Idle","selected_mean":"Mean of selected sensors","selected_sensor":"Mean of selected sensors","selected_partial_mean":"Mean of available sensors","selected_partial_sensor":"Mean of available sensors","room_selected_mean":"Mean of selected sensors","complete_measured_stage_capacities_required":"Enter valid measurements for every stage","not_configured":"Not configured","environment_only_no_hvac":"Room summary only. Each device below has its own controller.","sleep":"Sleep","comfort":"Comfort","eco":"Energy saving"},"words":{"outside":"Outside","general":"General","area":"Area","settings":"settings","devices":"Devices","pollen":"Pollen","room":"Room","house":"Home","sleep":"Sleep","presence":"Occupancy","automatic":"Automatic","control":"control","select":"Select","sensor":"sensor","source":"source","off":"Off","hold":"Hold","temperature":"Temperature","humidity":"Humidity","required":"Required","invalid":"Invalid","speed":"Speed","power":"Power","target":"target"},"profiles":{"none":"Automatic","home":"Home","sleep":"Sleep","away":"Away","comfort":"Comfort","eco":"Energy saving"},"methods":{"existing":"Existing room controller","automatic":"Automatic","manual":"Manual","off":"Off","pid":"PID"},"methodLabel":"Control · Method"},"es":{"text":{"overview":"Resumen de la habitación","devices":"Controladores de dispositivos","calibration":"Calibración","details":"Diagnóstico","physical":"Dispositivo físico","target":"Objetivo","demand":"Demanda","supply":"Alimentación","cooldown":"Espera antes del corte","sleep":"Pausa por sueño","reason":"Motivo","lux":"Iluminancia","idle":"En reposo","mean":"Media de sensores seleccionados","partialMean":"Media de sensores disponibles","inputs":"Introduce medidas válidas para cada etapa","ready":"Listo","unconfigured":"Sin configurar","information":"Información","save":"Guardar","apply":"Aplicar","gain":"Ganancia del proceso","timeConstant":"Constante de tiempo","deadTime":"Tiempo muerto","speed":"Velocidad del ventilador","capacity":"Capacidad relativa","stage":"Etapa","waiting":"En espera","summaryHelp":"Resumen de la habitación. Cada dispositivo de abajo tiene su propio controlador.","luxHelp":"Los lux miden luz ambiental, no calidad del aire ni calor solar. Se usan para informar sobre la iluminación.","dataHelp":"Las lecturas proceden de sensores seleccionados. Comprueba unidades, actualización y calibración.","calHelp":"La calibración es opcional. Usa medidas reales; la velocidad máxima del ventilador representa el 100%.","heat":"Calefacción","cool":"Refrigeración","dry":"Deshumidificación","fan":"Ventilador","choose":"Elegir modo","on":"Encendido","off":"Apagado","unknown":"Desconocido","legacyStrategy":"Original (sin calibrar)","measuredStrategy":"Modelo de capacidad medida","estimateHelp":"Las estimaciones usan lecturas y supuestos del modelo. La falta de datos o historial impide obtener un resultado fiable.","awayProfile":"Ausente","comfortProfile":"Confort","ecoProfile":"Ahorro de energía"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Ausente","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Control automático activo","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Casa","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Esperando el tiempo mínimo de apagado seguro","minimum_on_hold":"Manteniendo el equipo encendido durante el tiempo mínimo seguro","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Control automático en pausa","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"El PID solicita funcionamiento, pero la salida está apagada","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"No se puede confirmar si esta habitación está en modo sueño","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Esperando a que terminen las comprobaciones de inicio","storage_unavailable":"No se pudo cargar el historial de seguridad; control suspendido","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Dentro del rango objetivo configurado","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"En reposo","selected_mean":"Media de sensores seleccionados","selected_sensor":"Media de sensores seleccionados","selected_partial_mean":"Media de sensores disponibles","selected_partial_sensor":"Media de sensores disponibles","room_selected_mean":"Media de sensores seleccionados","complete_measured_stage_capacities_required":"Introduce medidas válidas para cada etapa","not_configured":"Sin configurar","environment_only_no_hvac":"Resumen de la habitación. Cada dispositivo de abajo tiene su propio controlador.","sleep":"Sueño","comfort":"Confort","eco":"Ahorro de energía"},"words":{"outside":"Exterior","general":"General","area":"Área","settings":"ajustes","devices":"Dispositivos","pollen":"Polen","room":"Habitación","house":"Casa","sleep":"Sueño","presence":"Ocupación","automatic":"Automático","control":"control","select":"Elegir","sensor":"sensor","source":"fuente","off":"Apagar","hold":"Pausar","temperature":"Temperatura","humidity":"Humedad","required":"Obligatorio","invalid":"No válido","speed":"Velocidad","power":"Potencia","target":"objetivo"},"profiles":{"none":"Automático","home":"Casa","sleep":"Sueño","away":"Ausente","comfort":"Confort","eco":"Ahorro de energía"},"methods":{"existing":"Controlador de estancia existente","automatic":"Automático","manual":"Manual","off":"Apagar","pid":"PID"},"methodLabel":"Control · Método"},"fa":{"text":{"overview":"نمای کلی اتاق","devices":"کنترل‌گرهای دستگاه","calibration":"کالیبراسیون","details":"عیب‌یابی","physical":"دستگاه فیزیکی","target":"هدف","demand":"نیاز","supply":"منبع تغذیه","cooldown":"تأخیر قطع برق","sleep":"توقف هنگام خواب","reason":"دلیل","lux":"روشنایی","idle":"بیکار","mean":"میانگین حسگرهای انتخاب‌شده","partialMean":"میانگین حسگرهای موجود","inputs":"برای هر مرحله اندازه‌گیری معتبر وارد کنید","ready":"آماده","unconfigured":"پیکربندی نشده","information":"اطلاعات","save":"ذخیره","apply":"اعمال","gain":"بهره فرایند","timeConstant":"ثابت زمانی","deadTime":"زمان مرده","speed":"سرعت فن","capacity":"ظرفیت نسبی","stage":"مرحله","waiting":"در انتظار","summaryHelp":"خلاصه اتاق. هر دستگاه زیر کنترل‌گر مستقل دارد.","luxHelp":"لوکس نور محیط را اندازه می‌گیرد، نه کیفیت هوا یا گرمای خورشید. برای پایش روشنایی و نور روز استفاده می‌شود.","dataHelp":"خوانش‌ها از حسگرهای انتخاب‌شده هستند. واحدها، تازگی و کالیبراسیون را بررسی کنید.","calHelp":"کالیبراسیون اختیاری است. از اندازه‌گیری واقعی استفاده کنید؛ بیشترین سرعت فن مرجع 100% است.","heat":"گرمایش","cool":"سرمایش","dry":"رطوبت‌گیری","fan":"فن","choose":"انتخاب حالت","on":"روشن","off":"خاموش","unknown":"نامشخص","legacyStrategy":"اصلی (کالیبره نشده)","measuredStrategy":"مدل ظرفیت اندازه‌گیری‌شده","estimateHelp":"برآوردها از داده‌های حسگر و فرض‌های مدل استفاده می‌کنند. داده‌های ناقص یا سابقه ناکافی نتیجه قابل اعتماد نمی‌دهند.","awayProfile":"بیرون از خانه","comfortProfile":"آسایش","ecoProfile":"صرفه‌جویی انرژی"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"بیرون از خانه","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"کنترل خودکار فعال است","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"خانه","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"در انتظار سپری شدن حداقل زمان ایمن خاموش بودن","minimum_on_hold":"دستگاه تا پایان حداقل زمان ایمن روشن می‌ماند","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"کنترل خودکار موقتاً متوقف است","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"کنترل‌کننده PID درخواست فعالیت دارد اما خروجی خاموش است","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"نمی‌توان تأیید کرد که این اتاق در حالت خواب است","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"در انتظار پایان بررسی‌های راه‌اندازی","storage_unavailable":"تاریخچه ایمنی بارگیری نشد؛ کنترل خودکار معلق شد","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"در محدوده هدف تنظیم‌شده","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"بیکار","selected_mean":"میانگین حسگرهای انتخاب‌شده","selected_sensor":"میانگین حسگرهای انتخاب‌شده","selected_partial_mean":"میانگین حسگرهای موجود","selected_partial_sensor":"میانگین حسگرهای موجود","room_selected_mean":"میانگین حسگرهای انتخاب‌شده","complete_measured_stage_capacities_required":"برای هر مرحله اندازه‌گیری معتبر وارد کنید","not_configured":"پیکربندی نشده","environment_only_no_hvac":"خلاصه اتاق. هر دستگاه زیر کنترل‌گر مستقل دارد.","sleep":"خواب","comfort":"آسایش","eco":"صرفه‌جویی انرژی"},"words":{"outside":"بیرون","general":"عمومی","area":"ناحیه","settings":"تنظیمات","devices":"دستگاه‌ها","pollen":"گرده","room":"اتاق","house":"خانه","sleep":"خواب","presence":"حضور","automatic":"خودکار","control":"کنترل","select":"انتخاب","sensor":"حسگر","source":"منبع","off":"خاموش","hold":"توقف","temperature":"دما","humidity":"رطوبت","required":"الزامی","invalid":"نامعتبر","speed":"سرعت","power":"توان","target":"هدف"},"profiles":{"none":"خودکار","home":"خانه","sleep":"خواب","away":"بیرون از خانه","comfort":"آسایش","eco":"صرفه‌جویی انرژی"},"methods":{"existing":"کنترل‌کنندهٔ فعلی اتاق","automatic":"خودکار","manual":"دستی","off":"خاموش","pid":"PID"},"methodLabel":"کنترل · روش کنترل"},"fi":{"text":{"overview":"Huoneen yleiskuva","devices":"Laiteohjaimet","calibration":"Kalibrointi","details":"Diagnostiikka","physical":"Fyysinen laite","target":"Tavoite","demand":"Tarve","supply":"Virransyöttö","cooldown":"Sammutusviive","sleep":"Unitauko","reason":"Syy","lux":"Valaistusvoimakkuus","idle":"Lepotila","mean":"Valittujen anturien keskiarvo","partialMean":"Saatavilla olevien anturien keskiarvo","inputs":"Syötä kelvolliset mittaukset jokaiselle tasolle","ready":"Valmis","unconfigured":"Ei määritetty","information":"Tiedot","save":"Tallenna","apply":"Käytä","gain":"Prosessin vahvistus","timeConstant":"Aikavakio","deadTime":"Kuollut aika","speed":"Puhaltimen nopeus","capacity":"Suhteellinen kapasiteetti","stage":"Taso","waiting":"Odottaa","summaryHelp":"Huoneen yhteenveto. Jokaisella alla olevalla laitteella on oma ohjain.","luxHelp":"Luksi mittaa ympäristön valoa, ei ilmanlaatua tai auringon lämpöä. Sitä käytetään valaistuksen seurantaan.","dataHelp":"Lukemat tulevat valituista antureista. Tarkista yksiköt, ajantasaisuus ja kalibrointi.","calHelp":"Kalibrointi on valinnainen. Käytä todellisia mittauksia; puhaltimen suurin nopeus on 100%:n vertailutaso.","heat":"Lämmitys","cool":"Jäähdytys","dry":"Kuivaus","fan":"Puhallin","choose":"Valitse tila","on":"Päällä","off":"Pois","unknown":"Tuntematon","legacyStrategy":"Alkuperäinen (kalibroimaton)","measuredStrategy":"Mitatun kapasiteetin malli","estimateHelp":"Arviot käyttävät anturilukemia ja mallin oletuksia. Puuttuvat tiedot tai riittämätön historia eivät mahdollista luotettavaa tulosta.","awayProfile":"Poissa","comfortProfile":"Mukavuus","ecoProfile":"Energiansäästö"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Poissa","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automaattinen ohjaus käytössä","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Koti","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Odotetaan turvallisen vähimmäisajan kulumista pois päältä","minimum_on_hold":"Laite pysyy päällä turvallisen vähimmäisajan","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automaattinen ohjaus keskeytetty","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID pyytää toimintaa, mutta lähtö on pois päältä","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Huoneen unitilaa ei voida vahvistaa","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Odotetaan käynnistystarkistusten valmistumista","storage_unavailable":"Turvahistoriaa ei voitu ladata; ohjaus keskeytetty","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Asetetulla tavoitealueella","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Lepotila","selected_mean":"Valittujen anturien keskiarvo","selected_sensor":"Valittujen anturien keskiarvo","selected_partial_mean":"Saatavilla olevien anturien keskiarvo","selected_partial_sensor":"Saatavilla olevien anturien keskiarvo","room_selected_mean":"Valittujen anturien keskiarvo","complete_measured_stage_capacities_required":"Syötä kelvolliset mittaukset jokaiselle tasolle","not_configured":"Ei määritetty","environment_only_no_hvac":"Huoneen yhteenveto. Jokaisella alla olevalla laitteella on oma ohjain.","sleep":"Uni","comfort":"Mukavuus","eco":"Energiansäästö"},"words":{"outside":"Ulko","general":"Yleiset","area":"Alue","settings":"asetukset","devices":"Laitteet","pollen":"Siitepöly","room":"Huone","house":"Koti","sleep":"Uni","presence":"Läsnäolo","automatic":"Automaattinen","control":"ohjaus","select":"Valitse","sensor":"anturi","source":"lähde","off":"Sammuta","hold":"Keskeytä","temperature":"Lämpötila","humidity":"Kosteus","required":"Vaaditaan","invalid":"Virheellinen","speed":"Nopeus","power":"Teho","target":"tavoite"},"profiles":{"none":"Automaattinen","home":"Koti","sleep":"Uni","away":"Poissa","comfort":"Mukavuus","eco":"Energiansäästö"},"methods":{"existing":"Nykyinen huonesäädin","automatic":"Automaattinen","manual":"Manuaalinen","off":"Sammuta","pid":"PID"},"methodLabel":"Ohjaus · Ohjaustapa"},"fr":{"text":{"overview":"Vue de la pièce","devices":"Régulateurs des appareils","calibration":"Étalonnage","details":"Diagnostic","physical":"Appareil physique","target":"Consigne","demand":"Demande","supply":"Alimentation","cooldown":"Délai avant coupure","sleep":"Pause sommeil","reason":"Raison","lux":"Éclairement","idle":"Au repos","mean":"Moyenne des capteurs sélectionnés","partialMean":"Moyenne des capteurs disponibles","inputs":"Saisissez des mesures valides pour chaque niveau","ready":"Prêt","unconfigured":"Non configuré","information":"Informations","save":"Enregistrer","apply":"Appliquer","gain":"Gain du procédé","timeConstant":"Constante de temps","deadTime":"Temps mort","speed":"Vitesse du ventilateur","capacity":"Capacité relative","stage":"Niveau","waiting":"En attente","summaryHelp":"Résumé de la pièce. Chaque appareil ci-dessous possède son propre régulateur.","luxHelp":"Les lux mesurent la lumière ambiante, pas la qualité de l’air ni la chaleur solaire. Ils servent au suivi de l’éclairage.","dataHelp":"Les mesures proviennent des capteurs sélectionnés. Vérifiez leurs unités, leur fraîcheur et leur étalonnage.","calHelp":"L’étalonnage est facultatif. Utilisez des mesures réelles ; la vitesse maximale représente 100%.","heat":"Chauffage","cool":"Refroidissement","dry":"Déshumidification","fan":"Ventilateur","choose":"Choisir le mode","on":"Marche","off":"Arrêt","unknown":"Inconnu","legacyStrategy":"Allocation initiale (non étalonnée)","measuredStrategy":"Modèle de capacité mesurée","estimateHelp":"Les estimations reposent sur les capteurs et les hypothèses du modèle. Des données manquantes ou un historique insuffisant ne permettent pas un résultat fiable.","awayProfile":"Absent","comfortProfile":"Confort","ecoProfile":"Économie d’énergie"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Absent","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Régulation automatique active","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Maison","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Attente de la durée minimale d'arrêt de sécurité","minimum_on_hold":"Maintien en marche pendant la durée minimale de sécurité","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Régulation automatique en pause","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"Le PID demande une action, mais la sortie reste désactivée","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Impossible de confirmer si cette pièce est en mode sommeil","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"En attente de la fin des vérifications de démarrage","storage_unavailable":"Historique de sécurité indisponible ; régulation suspendue","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Dans la plage cible définie","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Au repos","selected_mean":"Moyenne des capteurs sélectionnés","selected_sensor":"Moyenne des capteurs sélectionnés","selected_partial_mean":"Moyenne des capteurs disponibles","selected_partial_sensor":"Moyenne des capteurs disponibles","room_selected_mean":"Moyenne des capteurs sélectionnés","complete_measured_stage_capacities_required":"Saisissez des mesures valides pour chaque niveau","not_configured":"Non configuré","environment_only_no_hvac":"Résumé de la pièce. Chaque appareil ci-dessous possède son propre régulateur.","sleep":"Sommeil","comfort":"Confort","eco":"Économie d’énergie"},"words":{"outside":"Extérieur","general":"Général","area":"Zone","settings":"paramètres","devices":"Appareils","pollen":"Pollen","room":"Pièce","house":"Maison","sleep":"Sommeil","presence":"Présence","automatic":"Automatique","control":"contrôle","select":"Choisir","sensor":"capteur","source":"source","off":"Arrêt","hold":"Pause","temperature":"Température","humidity":"Humidité","required":"Obligatoire","invalid":"Invalide","speed":"Vitesse","power":"Puissance","target":"consigne"},"profiles":{"none":"Automatique","home":"Maison","sleep":"Sommeil","away":"Absent","comfort":"Confort","eco":"Économie d’énergie"},"methods":{"existing":"Régulateur de pièce existant","automatic":"Automatique","manual":"Manuel","off":"Arrêt","pid":"PID"},"methodLabel":"Contrôle · Méthode"},"he":{"text":{"overview":"סקירת החדר","devices":"בקרי המכשירים","calibration":"כיול","details":"אבחון","physical":"המכשיר הפיזי","target":"יעד","demand":"דרישה","supply":"אספקת חשמל","cooldown":"השהיית כיבוי","sleep":"השהיה בזמן שינה","reason":"סיבה","lux":"עוצמת הארה","idle":"סרק","mean":"ממוצע החיישנים שנבחרו","partialMean":"ממוצע החיישנים הזמינים","inputs":"יש להזין מדידות תקינות לכל דרגה","ready":"מוכן","unconfigured":"לא הוגדר","information":"מידע","save":"שמירה","apply":"החלה","gain":"הגבר התהליך","timeConstant":"קבוע זמן","deadTime":"זמן מת","speed":"מהירות מאוורר","capacity":"תפוקה יחסית","stage":"דרגה","waiting":"בהמתנה","summaryHelp":"סיכום החדר. לכל מכשיר להלן יש בקר נפרד.","luxHelp":"לוקס מודד אור סביבתי, לא איכות אוויר או חום שמש. הוא משמש למעקב אחר תאורה ואור יום.","dataHelp":"הקריאות מגיעות מהחיישנים שנבחרו. יש לבדוק יחידות, עדכניות וכיול.","calHelp":"הכיול אינו חובה. יש להשתמש במדידות אמיתיות; המהירות המרבית של המאוורר היא ייחוס של 100%.","heat":"חימום","cool":"קירור","dry":"ייבוש","fan":"מאוורר","choose":"בחירת מצב","on":"פועל","off":"כבוי","unknown":"לא ידוע","legacyStrategy":"מקורי (ללא כיול)","measuredStrategy":"מודל תפוקה נמדדת","estimateHelp":"ההערכות משתמשות בקריאות חיישנים ובהנחות המודל. נתונים חסרים או היסטוריה קצרה מדי אינם מאפשרים תוצאה אמינה.","awayProfile":"מחוץ לבית","comfortProfile":"נוחות","ecoProfile":"חיסכון באנרגיה"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"מחוץ לבית","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"הבקרה האוטומטית פעילה","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"בית","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"ממתין למשך הכיבוי הבטוח המינימלי","minimum_on_hold":"המכשיר נשאר דולק עד להשלמת זמן הפעולה המינימלי","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"הבקרה האוטומטית מושהית","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"בקר PID מבקש פעולה אך היציאה כבויה","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"לא ניתן לאמת אם החדר נמצא במצב שינה","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"ממתין להשלמת בדיקות האתחול","storage_unavailable":"לא ניתן לטעון את היסטוריית הבטיחות; הבקרה הושהתה","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"בתוך טווח היעד שהוגדר","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"סרק","selected_mean":"ממוצע החיישנים שנבחרו","selected_sensor":"ממוצע החיישנים שנבחרו","selected_partial_mean":"ממוצע החיישנים הזמינים","selected_partial_sensor":"ממוצע החיישנים הזמינים","room_selected_mean":"ממוצע החיישנים שנבחרו","complete_measured_stage_capacities_required":"יש להזין מדידות תקינות לכל דרגה","not_configured":"לא הוגדר","environment_only_no_hvac":"סיכום החדר. לכל מכשיר להלן יש בקר נפרד.","sleep":"שינה","comfort":"נוחות","eco":"חיסכון באנרגיה"},"words":{"outside":"חוץ","general":"כלליות","area":"אזור","settings":"הגדרות","devices":"התקנים","pollen":"אבקנים","room":"חדר","house":"בית","sleep":"שינה","presence":"נוכחות","automatic":"אוטומטי","control":"בקרה","select":"בחר","sensor":"חיישן","source":"מקור","off":"כיבוי","hold":"השהיה","temperature":"טמפרטורה","humidity":"לחות","required":"נדרש","invalid":"לא תקין","speed":"מהירות","power":"הספק","target":"יעד"},"profiles":{"none":"אוטומטי","home":"בית","sleep":"שינה","away":"מחוץ לבית","comfort":"נוחות","eco":"חיסכון באנרגיה"},"methods":{"existing":"בקר החדר הקיים","automatic":"אוטומטי","manual":"ידני","off":"כיבוי","pid":"PID"},"methodLabel":"בקרה · שיטת בקרה"},"hi":{"text":{"overview":"कमरे का अवलोकन","devices":"उपकरण नियंत्रक","calibration":"अंशांकन","details":"निदान","physical":"भौतिक उपकरण","target":"लक्ष्य","demand":"माँग","supply":"बिजली आपूर्ति","cooldown":"बंद करने में विलंब","sleep":"नींद के दौरान विराम","reason":"कारण","lux":"प्रकाश स्तर","idle":"निष्क्रिय","mean":"चुने गए सेंसरों का औसत","partialMean":"उपलब्ध सेंसरों का औसत","inputs":"हर स्तर के लिए मान्य माप दर्ज करें","ready":"तैयार","unconfigured":"कॉन्फ़िगर नहीं किया गया","information":"जानकारी","save":"सहेजें","apply":"लागू करें","gain":"प्रक्रिया गेन","timeConstant":"समय स्थिरांक","deadTime":"मृत समय","speed":"पंखे की गति","capacity":"सापेक्ष क्षमता","stage":"स्तर","waiting":"प्रतीक्षा","summaryHelp":"कमरे का सारांश। नीचे हर उपकरण का अलग नियंत्रक है।","luxHelp":"लक्स परिवेश का प्रकाश मापता है, हवा की गुणवत्ता या सौर ताप नहीं। इसका उपयोग प्रकाश की निगरानी में होता है।","dataHelp":"रीडिंग चुने गए सेंसरों से आती हैं। इकाइयाँ, ताज़गी और अंशांकन जाँचें।","calHelp":"अंशांकन वैकल्पिक है। वास्तविक माप इस्तेमाल करें; पंखे की अधिकतम गति 100% संदर्भ है।","heat":"हीटिंग","cool":"कूलिंग","dry":"नमी हटाना","fan":"पंखा","choose":"मोड चुनें","on":"चालू","off":"बंद","unknown":"अज्ञात","legacyStrategy":"मूल (बिना अंशांकन)","measuredStrategy":"मापी गई क्षमता का मॉडल","estimateHelp":"अनुमान सेंसर रीडिंग और मॉडल की मान्यताओं का उपयोग करते हैं। अधूरे डेटा या कम इतिहास से विश्वसनीय परिणाम नहीं मिलता।","awayProfile":"घर से बाहर","comfortProfile":"आराम","ecoProfile":"ऊर्जा बचत"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"घर से बाहर","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"स्वचालित नियंत्रण सक्रिय है","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"घर","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"न्यूनतम सुरक्षित बंद समय पूरा होने की प्रतीक्षा","minimum_on_hold":"उपकरण न्यूनतम सुरक्षित अवधि तक चालू रहेगा","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"स्वचालित नियंत्रण रुका हुआ है","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID संचालन चाहता है, लेकिन आउटपुट बंद है","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"यह पुष्टि नहीं हो सकी कि कमरा स्लीप मोड में है","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"स्टार्टअप जाँच पूरी होने की प्रतीक्षा","storage_unavailable":"सुरक्षा इतिहास लोड नहीं हो सका; नियंत्रण रोका गया है","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"निर्धारित लक्ष्य सीमा के भीतर","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"निष्क्रिय","selected_mean":"चुने गए सेंसरों का औसत","selected_sensor":"चुने गए सेंसरों का औसत","selected_partial_mean":"उपलब्ध सेंसरों का औसत","selected_partial_sensor":"उपलब्ध सेंसरों का औसत","room_selected_mean":"चुने गए सेंसरों का औसत","complete_measured_stage_capacities_required":"हर स्तर के लिए मान्य माप दर्ज करें","not_configured":"कॉन्फ़िगर नहीं किया गया","environment_only_no_hvac":"कमरे का सारांश। नीचे हर उपकरण का अलग नियंत्रक है।","sleep":"नींद","comfort":"आराम","eco":"ऊर्जा बचत"},"words":{"outside":"बाहरी","general":"सामान्य","area":"क्षेत्र","settings":"सेटिंग","devices":"उपकरण","pollen":"पराग","room":"कमरा","house":"घर","sleep":"नींद","presence":"उपस्थिति","automatic":"स्वचालित","control":"नियंत्रण","select":"चुनें","sensor":"सेंसर","source":"स्रोत","off":"बंद करें","hold":"रोकें","temperature":"तापमान","humidity":"आर्द्रता","required":"आवश्यक","invalid":"अमान्य","speed":"गति","power":"शक्ति","target":"लक्ष्य"},"profiles":{"none":"स्वचालित","home":"घर","sleep":"नींद","away":"घर से बाहर","comfort":"आराम","eco":"ऊर्जा बचत"},"methods":{"existing":"मौजूदा कमरे का नियंत्रक","automatic":"स्वचालित","manual":"मैनुअल","off":"बंद करें","pid":"PID"},"methodLabel":"नियंत्रण · नियंत्रण विधि"},"hr":{"text":{"overview":"Pregled prostorije","devices":"Upravljači uređaja","calibration":"Kalibracija","details":"Dijagnostika","physical":"Fizički uređaj","target":"Cilj","demand":"Potreba","supply":"Napajanje","cooldown":"Odgoda isključivanja","sleep":"Pauza tijekom spavanja","reason":"Razlog","lux":"Osvijetljenost","idle":"Mirovanje","mean":"Prosjek odabranih senzora","partialMean":"Prosjek dostupnih senzora","inputs":"Unesite valjana mjerenja za svaki stupanj","ready":"Spremno","unconfigured":"Nije postavljeno","information":"Informacije","save":"Spremi","apply":"Primijeni","gain":"Pojačanje procesa","timeConstant":"Vremenska konstanta","deadTime":"Mrtvo vrijeme","speed":"Brzina ventilatora","capacity":"Relativni kapacitet","stage":"Stupanj","waiting":"Čekanje","summaryHelp":"Sažetak prostorije. Svaki uređaj ispod ima vlastiti upravljač.","luxHelp":"Luksi mjere okolno svjetlo, ne kvalitetu zraka ni sunčevu toplinu. Koriste se za praćenje osvjetljenja.","dataHelp":"Očitanja dolaze iz odabranih senzora. Provjerite jedinice, ažurnost i kalibraciju.","calHelp":"Kalibracija nije obvezna. Koristite stvarna mjerenja; najveća brzina ventilatora predstavlja 100%.","heat":"Grijanje","cool":"Hlađenje","dry":"Odvlaživanje","fan":"Ventilator","choose":"Odaberi način","on":"Uključeno","off":"Isključeno","unknown":"Nepoznato","legacyStrategy":"Izvorno (nekalibrirano)","measuredStrategy":"Model izmjerenog kapaciteta","estimateHelp":"Procjene koriste očitanja senzora i pretpostavke modela. Nedostajući podaci ili nedovoljna povijest ne daju pouzdan rezultat.","awayProfile":"Odsutnost","comfortProfile":"Udobnost","ecoProfile":"Ušteda energije"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Odsutnost","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatsko upravljanje aktivno","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Dom","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Čekanje minimalnog sigurnog vremena isključenja","minimum_on_hold":"Uređaj ostaje uključen do minimalnog sigurnog vremena","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatsko upravljanje pauzirano","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID zahtijeva rad, ali izlaz je isključen","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nije moguće potvrditi je li soba u načinu spavanja","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Čekanje završetka provjera pri pokretanju","storage_unavailable":"Sigurnosna povijest nije učitana; upravljanje obustavljeno","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Unutar postavljenog ciljnog raspona","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Mirovanje","selected_mean":"Prosjek odabranih senzora","selected_sensor":"Prosjek odabranih senzora","selected_partial_mean":"Prosjek dostupnih senzora","selected_partial_sensor":"Prosjek dostupnih senzora","room_selected_mean":"Prosjek odabranih senzora","complete_measured_stage_capacities_required":"Unesite valjana mjerenja za svaki stupanj","not_configured":"Nije postavljeno","environment_only_no_hvac":"Sažetak prostorije. Svaki uređaj ispod ima vlastiti upravljač.","sleep":"Spavanje","comfort":"Udobnost","eco":"Ušteda energije"},"words":{"outside":"Vanjski","general":"Opće","area":"Područje","settings":"postavke","devices":"Uređaji","pollen":"Pelud","room":"Soba","house":"Dom","sleep":"Spavanje","presence":"Prisutnost","automatic":"Automatsko","control":"upravljanje","select":"Odaberi","sensor":"senzor","source":"izvor","off":"Isključi","hold":"Pauza","temperature":"Temperatura","humidity":"Vlažnost","required":"Obavezno","invalid":"Neispravno","speed":"Brzina","power":"Snaga","target":"cilj"},"profiles":{"none":"Automatsko","home":"Dom","sleep":"Spavanje","away":"Odsutnost","comfort":"Udobnost","eco":"Ušteda energije"},"methods":{"existing":"Postojeći sobni regulator","automatic":"Automatsko","manual":"Ručno","off":"Isključi","pid":"PID"},"methodLabel":"Upravljanje · Način upravljanja"},"hu":{"text":{"overview":"Szobaáttekintés","devices":"Eszközvezérlők","calibration":"Kalibrálás","details":"Diagnosztika","physical":"Fizikai eszköz","target":"Célérték","demand":"Igény","supply":"Tápellátás","cooldown":"Kikapcsolási késleltetés","sleep":"Alvási szünet","reason":"Ok","lux":"Megvilágítás","idle":"Nyugalom","mean":"Kiválasztott érzékelők átlaga","partialMean":"Elérhető érzékelők átlaga","inputs":"Adjon meg érvényes mérést minden fokozathoz","ready":"Kész","unconfigured":"Nincs beállítva","information":"Információ","save":"Mentés","apply":"Alkalmazás","gain":"Folyamaterősítés","timeConstant":"Időállandó","deadTime":"Holt idő","speed":"Ventilátor-fordulatszám","capacity":"Relatív teljesítmény","stage":"Fokozat","waiting":"Várakozás","summaryHelp":"A szoba összefoglalója. Minden alábbi eszköz saját vezérlővel rendelkezik.","luxHelp":"A lux a környezeti fényt méri, nem a levegőminőséget vagy a napsugárzás hőjét. Világítási adatokhoz használjuk.","dataHelp":"Az értékek a kiválasztott érzékelőkből származnak. Ellenőrizze az egységet, frissességet és kalibrálást.","calHelp":"A kalibrálás nem kötelező. Valós méréseket használjon; a legnagyobb ventilátor-fordulatszám a 100%-os referencia.","heat":"Fűtés","cool":"Hűtés","dry":"Páramentesítés","fan":"Ventilátor","choose":"Üzemmód választása","on":"Bekapcsolva","off":"Kikapcsolva","unknown":"Ismeretlen","legacyStrategy":"Eredeti (kalibrálatlan)","measuredStrategy":"Mért teljesítménymodell","estimateHelp":"A becslések érzékelőadatokat és modellfeltevéseket használnak. Hiányzó adatok vagy elégtelen előzmények nem adnak megbízható eredményt.","awayProfile":"Távol","comfortProfile":"Komfort","ecoProfile":"Energiatakarékosság"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Távol","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatikus vezérlés aktív","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Otthon","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Várakozás a biztonságos minimális kikapcsolási időre","minimum_on_hold":"A készülék bekapcsolva marad a minimális biztonságos ideig","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatikus vezérlés szünetel","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"A PID működést kér, de a kimenet ki van kapcsolva","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nem ellenőrizhető, hogy a szoba alvó üzemmódban van-e","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Várakozás az indítási ellenőrzések befejezésére","storage_unavailable":"A biztonsági előzmények nem tölthetők be; vezérlés felfüggesztve","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"A beállított céltartományon belül","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Nyugalom","selected_mean":"Kiválasztott érzékelők átlaga","selected_sensor":"Kiválasztott érzékelők átlaga","selected_partial_mean":"Elérhető érzékelők átlaga","selected_partial_sensor":"Elérhető érzékelők átlaga","room_selected_mean":"Kiválasztott érzékelők átlaga","complete_measured_stage_capacities_required":"Adjon meg érvényes mérést minden fokozathoz","not_configured":"Nincs beállítva","environment_only_no_hvac":"A szoba összefoglalója. Minden alábbi eszköz saját vezérlővel rendelkezik.","sleep":"Alvás","comfort":"Komfort","eco":"Energiatakarékosság"},"words":{"outside":"Kültéri","general":"Általános","area":"Terület","settings":"beállítások","devices":"Eszközök","pollen":"Pollen","room":"Szoba","house":"Otthon","sleep":"Alvás","presence":"Jelenlét","automatic":"Automatikus","control":"vezérlés","select":"Választás","sensor":"érzékelő","source":"forrás","off":"Kikapcsolás","hold":"Szünet","temperature":"Hőmérséklet","humidity":"Páratartalom","required":"Kötelező","invalid":"Érvénytelen","speed":"Sebesség","power":"Teljesítmény","target":"cél"},"profiles":{"none":"Automatikus","home":"Otthon","sleep":"Alvás","away":"Távol","comfort":"Komfort","eco":"Energiatakarékosság"},"methods":{"existing":"Meglévő helyiségszabályozó","automatic":"Automatikus","manual":"Kézi","off":"Kikapcsolás","pid":"PID"},"methodLabel":"Vezérlés · Szabályozási mód"},"id":{"text":{"overview":"Ringkasan ruangan","devices":"Pengontrol perangkat","calibration":"Kalibrasi","details":"Diagnostik","physical":"Perangkat fisik","target":"Target","demand":"Kebutuhan","supply":"Catu daya","cooldown":"Jeda sebelum daya diputus","sleep":"Jeda tidur","reason":"Alasan","lux":"Iluminansi","idle":"Siaga","mean":"Rata-rata sensor terpilih","partialMean":"Rata-rata sensor tersedia","inputs":"Masukkan pengukuran valid untuk setiap tahap","ready":"Siap","unconfigured":"Belum dikonfigurasi","information":"Informasi","save":"Simpan","apply":"Terapkan","gain":"Penguatan proses","timeConstant":"Konstanta waktu","deadTime":"Waktu tunda","speed":"Kecepatan kipas","capacity":"Kapasitas relatif","stage":"Tahap","waiting":"Menunggu","summaryHelp":"Ringkasan ruangan. Setiap perangkat di bawah memiliki pengontrol sendiri.","luxHelp":"Lux mengukur cahaya sekitar, bukan kualitas udara atau panas matahari. Digunakan untuk pemantauan pencahayaan.","dataHelp":"Pembacaan berasal dari sensor terpilih. Periksa satuan, kebaruan dan kalibrasi.","calHelp":"Kalibrasi bersifat opsional. Gunakan pengukuran nyata; kecepatan kipas tertinggi adalah acuan 100%.","heat":"Pemanasan","cool":"Pendinginan","dry":"Pengeringan","fan":"Kipas","choose":"Pilih mode","on":"Nyala","off":"Mati","unknown":"Tidak diketahui","legacyStrategy":"Asli (belum dikalibrasi)","measuredStrategy":"Model kapasitas terukur","estimateHelp":"Perkiraan memakai pembacaan sensor dan asumsi model. Data yang hilang atau riwayat yang kurang tidak menghasilkan hasil yang andal.","awayProfile":"Tidak di rumah","comfortProfile":"Nyaman","ecoProfile":"Hemat energi"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Tidak di rumah","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Kontrol otomatis aktif","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Rumah","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Menunggu waktu minimum aman saat perangkat mati","minimum_on_hold":"Perangkat tetap menyala selama waktu minimum yang aman","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Kontrol otomatis dijeda","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID meminta perangkat bekerja, tetapi keluarannya mati","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Tidak dapat memastikan apakah ruangan dalam mode tidur","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Menunggu pemeriksaan awal selesai","storage_unavailable":"Riwayat keamanan gagal dimuat; kontrol ditangguhkan","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Dalam rentang target yang ditetapkan","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Siaga","selected_mean":"Rata-rata sensor terpilih","selected_sensor":"Rata-rata sensor terpilih","selected_partial_mean":"Rata-rata sensor tersedia","selected_partial_sensor":"Rata-rata sensor tersedia","room_selected_mean":"Rata-rata sensor terpilih","complete_measured_stage_capacities_required":"Masukkan pengukuran valid untuk setiap tahap","not_configured":"Belum dikonfigurasi","environment_only_no_hvac":"Ringkasan ruangan. Setiap perangkat di bawah memiliki pengontrol sendiri.","sleep":"Tidur","comfort":"Nyaman","eco":"Hemat energi"},"words":{"outside":"Luar","general":"Umum","area":"Area","settings":"pengaturan","devices":"Perangkat","pollen":"Serbuk sari","room":"Ruangan","house":"Rumah","sleep":"Tidur","presence":"Kehadiran","automatic":"Otomatis","control":"kendali","select":"Pilih","sensor":"sensor","source":"sumber","off":"Matikan","hold":"Jeda","temperature":"Suhu","humidity":"Kelembapan","required":"Wajib","invalid":"Tidak valid","speed":"Kecepatan","power":"Daya","target":"target"},"profiles":{"none":"Otomatis","home":"Rumah","sleep":"Tidur","away":"Tidak di rumah","comfort":"Nyaman","eco":"Hemat energi"},"methods":{"existing":"Pengendali ruangan yang ada","automatic":"Otomatis","manual":"Manual","off":"Matikan","pid":"PID"},"methodLabel":"Kontrol · Metode kendali"},"it":{"text":{"overview":"Panoramica della stanza","devices":"Controllori dei dispositivi","calibration":"Calibrazione","details":"Diagnostica","physical":"Dispositivo fisico","target":"Obiettivo","demand":"Richiesta","supply":"Alimentazione","cooldown":"Attesa prima dello spegnimento","sleep":"Pausa sonno","reason":"Motivo","lux":"Illuminamento","idle":"Inattivo","mean":"Media dei sensori selezionati","partialMean":"Media dei sensori disponibili","inputs":"Inserisci misure valide per ogni livello","ready":"Pronto","unconfigured":"Non configurato","information":"Informazioni","save":"Salva","apply":"Applica","gain":"Guadagno di processo","timeConstant":"Costante di tempo","deadTime":"Tempo morto","speed":"Velocità della ventola","capacity":"Capacità relativa","stage":"Livello","waiting":"In attesa","summaryHelp":"Riepilogo della stanza. Ogni dispositivo sotto ha un proprio controllore.","luxHelp":"I lux misurano la luce ambiente, non la qualità dell’aria o il calore solare. Servono a monitorare l’illuminazione.","dataHelp":"Le misure provengono dai sensori selezionati. Verifica unità, aggiornamento e calibrazione.","calHelp":"La calibrazione è facoltativa. Usa misure reali; la velocità massima della ventola è il riferimento del 100%.","heat":"Riscaldamento","cool":"Raffrescamento","dry":"Deumidificazione","fan":"Ventola","choose":"Scegli modalità","on":"Acceso","off":"Spento","unknown":"Sconosciuto","legacyStrategy":"Originale (non calibrato)","measuredStrategy":"Modello di capacità misurata","estimateHelp":"Le stime usano misure e ipotesi del modello. Dati mancanti o uno storico insufficiente non consentono risultati affidabili.","awayProfile":"Assente","comfortProfile":"Comfort","ecoProfile":"Risparmio energetico"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Assente","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Controllo automatico attivo","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Casa","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"In attesa del tempo minimo di spegnimento sicuro","minimum_on_hold":"Dispositivo acceso per il tempo minimo di sicurezza","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Controllo automatico in pausa","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"Il PID richiede l'attivazione, ma l'uscita è spenta","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Impossibile confermare se la stanza è in modalità sonno","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"In attesa del completamento dei controlli iniziali","storage_unavailable":"Impossibile caricare lo storico di sicurezza; controllo sospeso","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Entro l'intervallo obiettivo impostato","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Inattivo","selected_mean":"Media dei sensori selezionati","selected_sensor":"Media dei sensori selezionati","selected_partial_mean":"Media dei sensori disponibili","selected_partial_sensor":"Media dei sensori disponibili","room_selected_mean":"Media dei sensori selezionati","complete_measured_stage_capacities_required":"Inserisci misure valide per ogni livello","not_configured":"Non configurato","environment_only_no_hvac":"Riepilogo della stanza. Ogni dispositivo sotto ha un proprio controllore.","sleep":"Sonno","comfort":"Comfort","eco":"Risparmio energetico"},"words":{"outside":"Esterno","general":"Generali","area":"Area","settings":"impostazioni","devices":"Dispositivi","pollen":"Polline","room":"Stanza","house":"Casa","sleep":"Sonno","presence":"Presenza","automatic":"Automatico","control":"controllo","select":"Seleziona","sensor":"sensore","source":"fonte","off":"Spegni","hold":"Pausa","temperature":"Temperatura","humidity":"Umidità","required":"Richiesto","invalid":"Non valido","speed":"Velocità","power":"Potenza","target":"obiettivo"},"profiles":{"none":"Automatico","home":"Casa","sleep":"Sonno","away":"Assente","comfort":"Comfort","eco":"Risparmio energetico"},"methods":{"existing":"Regolatore ambiente esistente","automatic":"Automatico","manual":"Manuale","off":"Spegni","pid":"PID"},"methodLabel":"Controllo · Metodo"},"ja":{"text":{"overview":"部屋の概要","devices":"機器コントローラー","calibration":"校正","details":"診断","physical":"実機の状態","target":"目標値","demand":"必要量","supply":"電源","cooldown":"電源オフまでの待機時間","sleep":"睡眠中の停止","reason":"理由","lux":"照度","idle":"待機","mean":"選択したセンサーの平均","partialMean":"利用可能なセンサーの平均","inputs":"各段階の有効な測定値を入力してください","ready":"準備完了","unconfigured":"未設定","information":"情報","save":"保存","apply":"適用","gain":"プロセスゲイン","timeConstant":"時定数","deadTime":"むだ時間","speed":"ファン速度","capacity":"相対能力","stage":"段階","waiting":"待機中","summaryHelp":"部屋の概要です。下の各機器には個別のコントローラーがあります。","luxHelp":"ルクスは周囲の明るさを測定し、空気質や日射熱を表しません。照明や日光の把握に使用します。","dataHelp":"値は選択したセンサーから取得します。単位、更新時刻、校正を確認してください。","calHelp":"校正は任意です。実測値を使用してください。最大ファン速度が100%の基準です。","heat":"暖房","cool":"冷房","dry":"除湿","fan":"ファン","choose":"モードを選択","on":"オン","off":"オフ","unknown":"不明","legacyStrategy":"初期設定（未校正）","measuredStrategy":"実測能力モデル","estimateHelp":"推定にはセンサー値とモデルの仮定を使います。入力や履歴が不足している場合、信頼できる結果は得られません。","awayProfile":"外出","comfortProfile":"快適","ecoProfile":"省エネ"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"外出","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"自動制御中","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"自宅","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"安全な最小停止時間が経過するまで待機中","minimum_on_hold":"最小安全運転時間が経過するまで運転を維持中","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"自動制御を一時停止中","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PIDは動作を要求していますが、出力はオフです","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"この部屋が睡眠モードか確認できません","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"起動時の安全確認が完了するまで待機中","storage_unavailable":"安全履歴を読み込めないため自動制御を停止中","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"設定した目標範囲内です","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"待機","selected_mean":"選択したセンサーの平均","selected_sensor":"選択したセンサーの平均","selected_partial_mean":"利用可能なセンサーの平均","selected_partial_sensor":"利用可能なセンサーの平均","room_selected_mean":"選択したセンサーの平均","complete_measured_stage_capacities_required":"各段階の有効な測定値を入力してください","not_configured":"未設定","environment_only_no_hvac":"部屋の概要です。下の各機器には個別のコントローラーがあります。","sleep":"睡眠","comfort":"快適","eco":"省エネ"},"words":{"outside":"屋外","general":"一般","area":"エリア","settings":"設定","devices":"デバイス","pollen":"花粉","room":"部屋","house":"自宅","sleep":"睡眠","presence":"在室","automatic":"自動","control":"制御","select":"選択","sensor":"センサー","source":"情報源","off":"オフ","hold":"一時停止","temperature":"温度","humidity":"湿度","required":"必須","invalid":"無効","speed":"速度","power":"電力","target":"目標"},"profiles":{"none":"自動","home":"自宅","sleep":"睡眠","away":"外出","comfort":"快適","eco":"省エネ"},"methods":{"existing":"既存の部屋コントローラー","automatic":"自動","manual":"手動","off":"オフ","pid":"PID"},"methodLabel":"制御 · 制御方式"},"ko":{"text":{"overview":"방 개요","devices":"기기 제어기","calibration":"보정","details":"진단","physical":"실제 기기","target":"목표","demand":"수요","supply":"전원 공급","cooldown":"전원 차단 대기 시간","sleep":"수면 중 일시 중지","reason":"이유","lux":"조도","idle":"대기","mean":"선택한 센서의 평균","partialMean":"사용 가능한 센서의 평균","inputs":"각 단계에 유효한 측정값을 입력하세요","ready":"준비됨","unconfigured":"설정되지 않음","information":"정보","save":"저장","apply":"적용","gain":"공정 이득","timeConstant":"시정수","deadTime":"지연 시간","speed":"팬 속도","capacity":"상대 용량","stage":"단계","waiting":"대기 중","summaryHelp":"방 요약입니다. 아래 각 기기에는 개별 제어기가 있습니다.","luxHelp":"럭스는 주변 밝기를 측정하며 공기질이나 태양열을 나타내지 않습니다. 조명 및 일광 정보에 사용됩니다.","dataHelp":"측정값은 선택한 센서에서 가져옵니다. 단위, 최신 여부와 보정을 확인하세요.","calHelp":"보정은 선택 사항입니다. 실제 측정값을 사용하세요. 최고 팬 속도가100% 기준입니다.","heat":"난방","cool":"냉방","dry":"제습","fan":"팬","choose":"모드 선택","on":"켜짐","off":"꺼짐","unknown":"알 수 없음","legacyStrategy":"기본 (보정되지 않음)","measuredStrategy":"측정 용량 모델","estimateHelp":"추정에는 센서 측정값과 모델 가정이 사용됩니다. 입력이나 이력이 부족하면 신뢰할 수 있는 결과를 얻을 수 없습니다.","awayProfile":"외출","comfortProfile":"쾌적","ecoProfile":"에너지 절약"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"외출","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"자동 제어 작동 중","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"집","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"안전한 최소 꺼짐 시간이 지나기를 기다리는 중","minimum_on_hold":"최소 안전 가동 시간이 끝날 때까지 장치를 켜 둡니다","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"자동 제어 일시 중지됨","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID가 동작을 요청했지만 출력이 꺼져 있습니다","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"이 방이 수면 모드인지 확인할 수 없습니다","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"시작 안전 점검이 끝나기를 기다리는 중","storage_unavailable":"안전 기록을 불러오지 못해 자동 제어가 중단됨","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"설정된 목표 범위 안에 있습니다","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"대기","selected_mean":"선택한 센서의 평균","selected_sensor":"선택한 센서의 평균","selected_partial_mean":"사용 가능한 센서의 평균","selected_partial_sensor":"사용 가능한 센서의 평균","room_selected_mean":"선택한 센서의 평균","complete_measured_stage_capacities_required":"각 단계에 유효한 측정값을 입력하세요","not_configured":"설정되지 않음","environment_only_no_hvac":"방 요약입니다. 아래 각 기기에는 개별 제어기가 있습니다.","sleep":"수면","comfort":"쾌적","eco":"에너지 절약"},"words":{"outside":"외부","general":"일반","area":"구역","settings":"설정","devices":"장치","pollen":"꽃가루","room":"방","house":"집","sleep":"수면","presence":"재실","automatic":"자동","control":"제어","select":"선택","sensor":"센서","source":"정보원","off":"끄기","hold":"일시 중지","temperature":"온도","humidity":"습도","required":"필수","invalid":"잘못됨","speed":"속도","power":"전력","target":"목표"},"profiles":{"none":"자동","home":"집","sleep":"수면","away":"외출","comfort":"쾌적","eco":"에너지 절약"},"methods":{"existing":"기존 방 제어기","automatic":"자동","manual":"수동","off":"끄기","pid":"PID"},"methodLabel":"제어 · 제어 방식"},"nb":{"text":{"overview":"Romoversikt","devices":"Enhetsregulatorer","calibration":"Kalibrering","details":"Diagnostikk","physical":"Fysisk enhet","target":"Mål","demand":"Behov","supply":"Strømforsyning","cooldown":"Forsinkelse før avslåing","sleep":"Søvnpause","reason":"Årsak","lux":"Belysningsstyrke","idle":"Hvile","mean":"Gjennomsnitt av valgte sensorer","partialMean":"Gjennomsnitt av tilgjengelige sensorer","inputs":"Skriv inn gyldige målinger for hvert trinn","ready":"Klar","unconfigured":"Ikke konfigurert","information":"Informasjon","save":"Lagre","apply":"Bruk","gain":"Prosessforsterkning","timeConstant":"Tidskonstant","deadTime":"Dødtid","speed":"Viftehastighet","capacity":"Relativ kapasitet","stage":"Trinn","waiting":"Venter","summaryHelp":"Romoversikt. Hver enhet nedenfor har sin egen regulator.","luxHelp":"Lux måler omgivelseslys, ikke luftkvalitet eller solvarme. Det brukes til lys- og dagslysrapportering.","dataHelp":"Målingene kommer fra valgte sensorer. Kontroller enheter, aktualitet og kalibrering.","calHelp":"Kalibrering er valgfri. Bruk faktiske målinger; høyeste viftehastighet er referansen på 100%.","heat":"Oppvarming","cool":"Kjøling","dry":"Avfukting","fan":"Vifte","choose":"Velg modus","on":"På","off":"Av","unknown":"Ukjent","legacyStrategy":"Opprinnelig (ukalibrert)","measuredStrategy":"Modell for målt kapasitet","estimateHelp":"Estimater bruker sensormålinger og modellforutsetninger. Manglende data eller utilstrekkelig historikk gir ikke pålitelige resultater.","awayProfile":"Borte","comfortProfile":"Komfort","ecoProfile":"Energisparing"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Borte","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatisk styring aktiv","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Hjem","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Venter på minste sikre av-tid","minimum_on_hold":"Enheten forblir på i minste sikre driftstid","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatisk styring satt på pause","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID ber om drift, men utgangen er slått av","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Kan ikke bekrefte om rommet er i sovemodus","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Venter på at oppstartskontrollene fullføres","storage_unavailable":"Sikkerhetshistorikken kunne ikke lastes; styring stanset","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Innenfor det angitte målområdet","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Hvile","selected_mean":"Gjennomsnitt av valgte sensorer","selected_sensor":"Gjennomsnitt av valgte sensorer","selected_partial_mean":"Gjennomsnitt av tilgjengelige sensorer","selected_partial_sensor":"Gjennomsnitt av tilgjengelige sensorer","room_selected_mean":"Gjennomsnitt av valgte sensorer","complete_measured_stage_capacities_required":"Skriv inn gyldige målinger for hvert trinn","not_configured":"Ikke konfigurert","environment_only_no_hvac":"Romoversikt. Hver enhet nedenfor har sin egen regulator.","sleep":"Søvn","comfort":"Komfort","eco":"Energisparing"},"words":{"outside":"Utendørs","general":"Generelle","area":"Område","settings":"innstillinger","devices":"Enheter","pollen":"Pollen","room":"Rom","house":"Hjem","sleep":"Søvn","presence":"Tilstedeværelse","automatic":"Automatisk","control":"styring","select":"Velg","sensor":"sensor","source":"kilde","off":"Slå av","hold":"Pause","temperature":"Temperatur","humidity":"Luftfuktighet","required":"Påkrevd","invalid":"Ugyldig","speed":"Hastighet","power":"Effekt","target":"mål"},"profiles":{"none":"Automatisk","home":"Hjem","sleep":"Søvn","away":"Borte","comfort":"Komfort","eco":"Energisparing"},"methods":{"existing":"Eksisterende romstyring","automatic":"Automatisk","manual":"Manuell","off":"Slå av","pid":"PID"},"methodLabel":"Styring · Styringsmetode"},"nl":{"text":{"overview":"Kameroverzicht","devices":"Apparaatregelaars","calibration":"Kalibratie","details":"Diagnose","physical":"Fysiek apparaat","target":"Doelwaarde","demand":"Vraag","supply":"Voeding","cooldown":"Wachttijd voor uitschakelen","sleep":"Slaappauze","reason":"Reden","lux":"Verlichtingssterkte","idle":"In rust","mean":"Gemiddelde geselecteerde sensoren","partialMean":"Gemiddelde beschikbare sensoren","inputs":"Voer geldige metingen in voor elke stand","ready":"Gereed","unconfigured":"Niet ingesteld","information":"Informatie","save":"Opslaan","apply":"Toepassen","gain":"Procesversterking","timeConstant":"Tijdconstante","deadTime":"Dode tijd","speed":"Ventilatorsnelheid","capacity":"Relatieve capaciteit","stage":"Stand","waiting":"Wachten","summaryHelp":"Kamersamenvatting. Elk apparaat hieronder heeft een eigen regelaar.","luxHelp":"Lux meet omgevingslicht, niet luchtkwaliteit of zonnewarmte. Het wordt gebruikt voor licht- en daglichtrapportage.","dataHelp":"Metingen komen van geselecteerde sensoren. Controleer eenheden, actualiteit en kalibratie.","calHelp":"Kalibratie is optioneel. Gebruik echte metingen; de hoogste ventilatorsnelheid is de 100%-referentie.","heat":"Verwarmen","cool":"Koelen","dry":"Ontvochtigen","fan":"Ventilator","choose":"Kies modus","on":"Aan","off":"Uit","unknown":"Onbekend","legacyStrategy":"Oorspronkelijk (ongekalibreerd)","measuredStrategy":"Gemeten capaciteitsmodel","estimateHelp":"Schattingen gebruiken sensormetingen en modelaannames. Ontbrekende gegevens of onvoldoende historie geven geen betrouwbaar resultaat.","awayProfile":"Afwezig","comfortProfile":"Comfort","ecoProfile":"Energiebesparing"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Afwezig","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatische regeling actief","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Thuis","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Wachten op de minimale veilige uitschakeltijd","minimum_on_hold":"Apparaat blijft aan tot de minimale veilige inschakeltijd","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatische regeling gepauzeerd","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID vraagt om werking, maar de uitgang is uit","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Niet te bevestigen of deze kamer in slaapstand staat","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Wachten totdat de opstartcontroles zijn afgerond","storage_unavailable":"Veiligheidsgeschiedenis niet geladen; regeling opgeschort","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Binnen het ingestelde doelbereik","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"In rust","selected_mean":"Gemiddelde geselecteerde sensoren","selected_sensor":"Gemiddelde geselecteerde sensoren","selected_partial_mean":"Gemiddelde beschikbare sensoren","selected_partial_sensor":"Gemiddelde beschikbare sensoren","room_selected_mean":"Gemiddelde geselecteerde sensoren","complete_measured_stage_capacities_required":"Voer geldige metingen in voor elke stand","not_configured":"Niet ingesteld","environment_only_no_hvac":"Kamersamenvatting. Elk apparaat hieronder heeft een eigen regelaar.","sleep":"Slaap","comfort":"Comfort","eco":"Energiebesparing"},"words":{"outside":"Buiten","general":"Algemene","area":"Ruimte","settings":"instellingen","devices":"Apparaten","pollen":"Pollen","room":"Kamer","house":"Thuis","sleep":"Slaap","presence":"Aanwezigheid","automatic":"Automatische","control":"regeling","select":"Kiezen","sensor":"sensor","source":"bron","off":"Uitschakelen","hold":"Pauzeren","temperature":"Temperatuur","humidity":"Vochtigheid","required":"Vereist","invalid":"Ongeldig","speed":"Snelheid","power":"Vermogen","target":"doelwaarde"},"profiles":{"none":"Automatische","home":"Thuis","sleep":"Slaap","away":"Afwezig","comfort":"Comfort","eco":"Energiebesparing"},"methods":{"existing":"Bestaande ruimteregeling","automatic":"Automatische","manual":"Handmatig","off":"Uitschakelen","pid":"PID"},"methodLabel":"Regeling · Regelmethode"},"pl":{"text":{"overview":"Przegląd pomieszczenia","devices":"Sterowniki urządzeń","calibration":"Kalibracja","details":"Diagnostyka","physical":"Urządzenie fizyczne","target":"Wartość docelowa","demand":"Zapotrzebowanie","supply":"Zasilanie","cooldown":"Opóźnienie wyłączenia","sleep":"Pauza podczas snu","reason":"Powód","lux":"Natężenie oświetlenia","idle":"Bezczynność","mean":"Średnia wybranych czujników","partialMean":"Średnia dostępnych czujników","inputs":"Wprowadź prawidłowe pomiary dla każdego stopnia","ready":"Gotowe","unconfigured":"Nie skonfigurowano","information":"Informacje","save":"Zapisz","apply":"Zastosuj","gain":"Wzmocnienie procesu","timeConstant":"Stała czasowa","deadTime":"Czas martwy","speed":"Prędkość wentylatora","capacity":"Względna wydajność","stage":"Stopień","waiting":"Oczekiwanie","summaryHelp":"Podsumowanie pomieszczenia. Każde urządzenie poniżej ma własny sterownik.","luxHelp":"Luksy mierzą światło otoczenia, nie jakość powietrza ani ciepło słoneczne. Służą do monitorowania oświetlenia.","dataHelp":"Odczyty pochodzą z wybranych czujników. Sprawdź jednostki, aktualność i kalibrację.","calHelp":"Kalibracja jest opcjonalna. Użyj rzeczywistych pomiarów; maksymalna prędkość wentylatora odpowiada 100%.","heat":"Ogrzewanie","cool":"Chłodzenie","dry":"Osuszanie","fan":"Wentylator","choose":"Wybierz tryb","on":"Włączone","off":"Wyłączone","unknown":"Nieznane","legacyStrategy":"Pierwotny (bez kalibracji)","measuredStrategy":"Model zmierzonej wydajności","estimateHelp":"Szacunki wykorzystują odczyty czujników i założenia modelu. Brak danych lub zbyt krótka historia nie zapewniają wiarygodnych wyników.","awayProfile":"Nieobecność","comfortProfile":"Komfort","ecoProfile":"Oszczędzanie energii"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Nieobecność","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Sterowanie automatyczne aktywne","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Dom","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Oczekiwanie na minimalny bezpieczny czas wyłączenia","minimum_on_hold":"Urządzenie pozostaje włączone przez minimalny bezpieczny czas","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Sterowanie automatyczne wstrzymane","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID wymaga pracy, ale wyjście jest wyłączone","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nie można potwierdzić, czy pomieszczenie jest w trybie snu","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Oczekiwanie na zakończenie kontroli po uruchomieniu","storage_unavailable":"Nie można wczytać historii zabezpieczeń; sterowanie wstrzymane","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"W ustawionym zakresie docelowym","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Bezczynność","selected_mean":"Średnia wybranych czujników","selected_sensor":"Średnia wybranych czujników","selected_partial_mean":"Średnia dostępnych czujników","selected_partial_sensor":"Średnia dostępnych czujników","room_selected_mean":"Średnia wybranych czujników","complete_measured_stage_capacities_required":"Wprowadź prawidłowe pomiary dla każdego stopnia","not_configured":"Nie skonfigurowano","environment_only_no_hvac":"Podsumowanie pomieszczenia. Każde urządzenie poniżej ma własny sterownik.","sleep":"Sen","comfort":"Komfort","eco":"Oszczędzanie energii"},"words":{"outside":"Zewnętrzne","general":"Ogólne","area":"Obszar","settings":"ustawienia","devices":"Urządzenia","pollen":"Pyłki","room":"Pokój","house":"Dom","sleep":"Sen","presence":"Obecność","automatic":"Automatyczne","control":"sterowanie","select":"Wybierz","sensor":"czujnik","source":"źródło","off":"Wyłącz","hold":"Wstrzymaj","temperature":"Temperatura","humidity":"Wilgotność","required":"Wymagane","invalid":"Nieprawidłowe","speed":"Prędkość","power":"Moc","target":"cel"},"profiles":{"none":"Automatyczne","home":"Dom","sleep":"Sen","away":"Nieobecność","comfort":"Komfort","eco":"Oszczędzanie energii"},"methods":{"existing":"Dotychczasowy regulator pomieszczenia","automatic":"Automatyczne","manual":"Ręczne","off":"Wyłącz","pid":"PID"},"methodLabel":"Sterowanie · Metoda sterowania"},"pt-br":{"text":{"overview":"Resumo do cômodo","devices":"Controladores dos dispositivos","calibration":"Calibração","details":"Diagnóstico","physical":"Dispositivo físico","target":"Meta","demand":"Demanda","supply":"Alimentação","cooldown":"Espera antes do desligamento","sleep":"Pausa durante o sono","reason":"Motivo","lux":"Iluminância","idle":"Em repouso","mean":"Média dos sensores selecionados","partialMean":"Média dos sensores disponíveis","inputs":"Insira medições válidas para cada estágio","ready":"Pronto","unconfigured":"Não configurado","information":"Informações","save":"Salvar","apply":"Aplicar","gain":"Ganho do processo","timeConstant":"Constante de tempo","deadTime":"Tempo morto","speed":"Velocidade do ventilador","capacity":"Capacidade relativa","stage":"Estágio","waiting":"Aguardando","summaryHelp":"Resumo do cômodo. Cada dispositivo abaixo tem seu próprio controlador.","luxHelp":"Lux mede a luz ambiente, não a qualidade do ar nem o calor solar. É usado para acompanhar a iluminação.","dataHelp":"As leituras vêm dos sensores selecionados. Verifique unidades, atualização e calibração.","calHelp":"A calibração é opcional. Use medições reais; a velocidade máxima do ventilador é a referência de 100%.","heat":"Aquecimento","cool":"Resfriamento","dry":"Desumidificação","fan":"Ventilador","choose":"Escolher modo","on":"Ligado","off":"Desligado","unknown":"Desconhecido","legacyStrategy":"Original (sem calibração)","measuredStrategy":"Modelo de capacidade medida","estimateHelp":"As estimativas usam medições e suposições do modelo. Dados ausentes ou histórico insuficiente não permitem resultados confiáveis.","awayProfile":"Ausente","comfortProfile":"Conforto","ecoProfile":"Economia de energia"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Ausente","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Controle automático ativo","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Casa","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Aguardando o tempo mínimo de desligamento seguro","minimum_on_hold":"Mantendo o equipamento ligado pelo tempo mínimo de segurança","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Controle automático pausado","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"O PID solicita funcionamento, mas a saída está desligada","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Não foi possível confirmar se este cômodo está em modo de sono","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Aguardando a conclusão das verificações de inicialização","storage_unavailable":"Falha ao carregar o histórico de segurança; controle suspenso","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Dentro da faixa de temperatura ou umidade desejada","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Em repouso","selected_mean":"Média dos sensores selecionados","selected_sensor":"Média dos sensores selecionados","selected_partial_mean":"Média dos sensores disponíveis","selected_partial_sensor":"Média dos sensores disponíveis","room_selected_mean":"Média dos sensores selecionados","complete_measured_stage_capacities_required":"Insira medições válidas para cada estágio","not_configured":"Não configurado","environment_only_no_hvac":"Resumo do cômodo. Cada dispositivo abaixo tem seu próprio controlador.","sleep":"Sono","comfort":"Conforto","eco":"Economia de energia"},"words":{"outside":"Externo","general":"Gerais","area":"Área","settings":"configurações","devices":"Dispositivos","pollen":"Pólen","room":"Cômodo","house":"Casa","sleep":"Sono","presence":"Ocupação","automatic":"Automático","control":"controle","select":"Selecionar","sensor":"sensor","source":"fonte","off":"Desligar","hold":"Pausar","temperature":"Temperatura","humidity":"Umidade","required":"Obrigatório","invalid":"Inválido","speed":"Velocidade","power":"Potência","target":"meta"},"profiles":{"none":"Automático","home":"Casa","sleep":"Sono","away":"Ausente","comfort":"Conforto","eco":"Economia de energia"},"methods":{"existing":"Controlador do ambiente existente","automatic":"Automático","manual":"Manual","off":"Desligar","pid":"PID"},"methodLabel":"Controle · Método de controle"},"pt":{"text":{"overview":"Resumo da divisão","devices":"Controladores dos dispositivos","calibration":"Calibração","details":"Diagnóstico","physical":"Dispositivo físico","target":"Objetivo","demand":"Necessidade","supply":"Alimentação","cooldown":"Espera antes do corte","sleep":"Pausa durante o sono","reason":"Motivo","lux":"Iluminância","idle":"Em repouso","mean":"Média dos sensores selecionados","partialMean":"Média dos sensores disponíveis","inputs":"Introduza medições válidas para cada nível","ready":"Pronto","unconfigured":"Não configurado","information":"Informações","save":"Guardar","apply":"Aplicar","gain":"Ganho do processo","timeConstant":"Constante de tempo","deadTime":"Tempo morto","speed":"Velocidade da ventoinha","capacity":"Capacidade relativa","stage":"Nível","waiting":"Em espera","summaryHelp":"Resumo da divisão. Cada dispositivo abaixo tem o seu próprio controlador.","luxHelp":"Lux mede a luz ambiente, não a qualidade do ar nem o calor solar. Serve para acompanhar a iluminação.","dataHelp":"As leituras provêm dos sensores selecionados. Verifique unidades, atualização e calibração.","calHelp":"A calibração é opcional. Use medições reais; a velocidade máxima da ventoinha é a referência de 100%.","heat":"Aquecimento","cool":"Arrefecimento","dry":"Desumidificação","fan":"Ventoinha","choose":"Escolher modo","on":"Ligado","off":"Desligado","unknown":"Desconhecido","legacyStrategy":"Original (sem calibração)","measuredStrategy":"Modelo de capacidade medida","estimateHelp":"As estimativas usam medições e pressupostos do modelo. Dados em falta ou histórico insuficiente não permitem resultados fiáveis.","awayProfile":"Ausente","comfortProfile":"Conforto","ecoProfile":"Poupança de energia"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Ausente","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Controlo automático ativo","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Casa","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"A aguardar o tempo mínimo de desligamento seguro","minimum_on_hold":"Equipamento ligado durante o tempo mínimo de segurança","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Controlo automático em pausa","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"O PID solicita funcionamento, mas a saída está desligada","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Não é possível confirmar se a divisão está em modo de sono","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"A aguardar a conclusão das verificações iniciais","storage_unavailable":"Não foi possível carregar o histórico de segurança; controlo suspenso","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Dentro do intervalo alvo configurado","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Em repouso","selected_mean":"Média dos sensores selecionados","selected_sensor":"Média dos sensores selecionados","selected_partial_mean":"Média dos sensores disponíveis","selected_partial_sensor":"Média dos sensores disponíveis","room_selected_mean":"Média dos sensores selecionados","complete_measured_stage_capacities_required":"Introduza medições válidas para cada nível","not_configured":"Não configurado","environment_only_no_hvac":"Resumo da divisão. Cada dispositivo abaixo tem o seu próprio controlador.","sleep":"Sono","comfort":"Conforto","eco":"Poupança de energia"},"words":{"outside":"Exterior","general":"Gerais","area":"Área","settings":"definições","devices":"Dispositivos","pollen":"Pólen","room":"Divisão","house":"Casa","sleep":"Sono","presence":"Ocupação","automatic":"Automático","control":"controlo","select":"Selecionar","sensor":"sensor","source":"fonte","off":"Desligar","hold":"Pausar","temperature":"Temperatura","humidity":"Humidade","required":"Obrigatório","invalid":"Inválido","speed":"Velocidade","power":"Potência","target":"objetivo"},"profiles":{"none":"Automático","home":"Casa","sleep":"Sono","away":"Ausente","comfort":"Conforto","eco":"Poupança de energia"},"methods":{"existing":"Controlador da divisão existente","automatic":"Automático","manual":"Manual","off":"Desligar","pid":"PID"},"methodLabel":"Controlo · Método de controlo"},"ro":{"text":{"overview":"Prezentarea camerei","devices":"Controlerele dispozitivelor","calibration":"Calibrare","details":"Diagnosticare","physical":"Dispozitiv fizic","target":"Țintă","demand":"Necesar","supply":"Alimentare","cooldown":"Întârziere la oprire","sleep":"Pauză în timpul somnului","reason":"Motiv","lux":"Iluminare","idle":"Repaus","mean":"Media senzorilor selectați","partialMean":"Media senzorilor disponibili","inputs":"Introduceți măsurători valide pentru fiecare treaptă","ready":"Pregătit","unconfigured":"Neconfigurat","information":"Informații","save":"Salvează","apply":"Aplică","gain":"Câștigul procesului","timeConstant":"Constanta de timp","deadTime":"Timp mort","speed":"Viteza ventilatorului","capacity":"Capacitate relativă","stage":"Treaptă","waiting":"Așteptare","summaryHelp":"Rezumatul camerei. Fiecare dispozitiv de mai jos are propriul controler.","luxHelp":"Luxul măsoară lumina ambientală, nu calitatea aerului sau căldura solară. Este folosit pentru monitorizarea iluminării.","dataHelp":"Valorile provin de la senzorii selectați. Verificați unitățile, actualitatea și calibrarea.","calHelp":"Calibrarea este opțională. Folosiți măsurători reale; viteza maximă a ventilatorului reprezintă 100%.","heat":"Încălzire","cool":"Răcire","dry":"Dezumidificare","fan":"Ventilator","choose":"Alege modul","on":"Pornit","off":"Oprit","unknown":"Necunoscut","legacyStrategy":"Inițial (necalibrat)","measuredStrategy":"Model de capacitate măsurată","estimateHelp":"Estimările folosesc măsurători și ipoteze ale modelului. Datele lipsă sau istoricul insuficient nu permit rezultate fiabile.","awayProfile":"Absent","comfortProfile":"Confort","ecoProfile":"Economisire energie"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Absent","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Control automat activ","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Acasă","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Se așteaptă timpul minim sigur de oprire","minimum_on_hold":"Dispozitivul rămâne pornit pentru durata minimă de siguranță","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Control automat în pauză","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID solicită funcționarea, dar ieșirea este oprită","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nu se poate confirma dacă încăperea este în modul somn","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Se așteaptă finalizarea verificărilor de pornire","storage_unavailable":"Istoricul de siguranță nu poate fi încărcat; control suspendat","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"În intervalul țintă configurat","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Repaus","selected_mean":"Media senzorilor selectați","selected_sensor":"Media senzorilor selectați","selected_partial_mean":"Media senzorilor disponibili","selected_partial_sensor":"Media senzorilor disponibili","room_selected_mean":"Media senzorilor selectați","complete_measured_stage_capacities_required":"Introduceți măsurători valide pentru fiecare treaptă","not_configured":"Neconfigurat","environment_only_no_hvac":"Rezumatul camerei. Fiecare dispozitiv de mai jos are propriul controler.","sleep":"Somn","comfort":"Confort","eco":"Economisire energie"},"words":{"outside":"Exterior","general":"Generale","area":"Zonă","settings":"setări","devices":"Dispozitive","pollen":"Polen","room":"Cameră","house":"Acasă","sleep":"Somn","presence":"Ocupare","automatic":"Automat","control":"control","select":"Selectați","sensor":"senzor","source":"sursă","off":"Oprire","hold":"Pauză","temperature":"Temperatură","humidity":"Umiditate","required":"Obligatoriu","invalid":"Invalid","speed":"Viteză","power":"Putere","target":"țintă"},"profiles":{"none":"Automat","home":"Acasă","sleep":"Somn","away":"Absent","comfort":"Confort","eco":"Economisire energie"},"methods":{"existing":"Controlerul existent al camerei","automatic":"Automat","manual":"Manual","off":"Oprire","pid":"PID"},"methodLabel":"Control · Metodă de control"},"ru":{"text":{"overview":"Обзор комнаты","devices":"Контроллеры устройств","calibration":"Калибровка","details":"Диагностика","physical":"Физическое устройство","target":"Цель","demand":"Потребность","supply":"Питание","cooldown":"Задержка отключения","sleep":"Пауза во время сна","reason":"Причина","lux":"Освещённость","idle":"Ожидание","mean":"Среднее выбранных датчиков","partialMean":"Среднее доступных датчиков","inputs":"Введите корректные измерения для каждой ступени","ready":"Готово","unconfigured":"Не настроено","information":"Информация","save":"Сохранить","apply":"Применить","gain":"Коэффициент усиления процесса","timeConstant":"Постоянная времени","deadTime":"Время задержки","speed":"Скорость вентилятора","capacity":"Относительная мощность","stage":"Ступень","waiting":"Ожидание","summaryHelp":"Сводка по комнате. У каждого устройства ниже свой контроллер.","luxHelp":"Люксы измеряют освещённость, а не качество воздуха или солнечное тепло. Они используются для наблюдения за освещением.","dataHelp":"Показания получены от выбранных датчиков. Проверьте единицы, актуальность и калибровку.","calHelp":"Калибровка необязательна. Используйте реальные измерения; максимальная скорость вентилятора соответствует 100%.","heat":"Нагрев","cool":"Охлаждение","dry":"Осушение","fan":"Вентилятор","choose":"Выбрать режим","on":"Включено","off":"Выключено","unknown":"Неизвестно","legacyStrategy":"Исходное (без калибровки)","measuredStrategy":"Модель измеренной мощности","estimateHelp":"Оценки используют показания датчиков и допущения модели. При нехватке данных или истории надёжный результат невозможен.","awayProfile":"Вне дома","comfortProfile":"Комфорт","ecoProfile":"Энергосбережение"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Вне дома","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Автоматическое управление активно","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Дом","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Ожидание минимального безопасного времени отключения","minimum_on_hold":"Устройство включено до истечения минимального безопасного времени","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Автоматическое управление приостановлено","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"ПИД запрашивает работу, но выход выключен","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Не удаётся подтвердить режим сна в этой комнате","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Ожидание завершения проверки после запуска","storage_unavailable":"Не удалось загрузить данные безопасности; управление приостановлено","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"В пределах заданного диапазона","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Ожидание","selected_mean":"Среднее выбранных датчиков","selected_sensor":"Среднее выбранных датчиков","selected_partial_mean":"Среднее доступных датчиков","selected_partial_sensor":"Среднее доступных датчиков","room_selected_mean":"Среднее выбранных датчиков","complete_measured_stage_capacities_required":"Введите корректные измерения для каждой ступени","not_configured":"Не настроено","environment_only_no_hvac":"Сводка по комнате. У каждого устройства ниже свой контроллер.","sleep":"Сон","comfort":"Комфорт","eco":"Энергосбережение"},"words":{"outside":"Снаружи","general":"Общие","area":"Область","settings":"настройки","devices":"Устройства","pollen":"Пыльца","room":"Комната","house":"Дом","sleep":"Сон","presence":"Присутствие","automatic":"Автоматическое","control":"управление","select":"Выбрать","sensor":"датчик","source":"источник","off":"Выключить","hold":"Приостановить","temperature":"Температура","humidity":"Влажность","required":"Обязательно","invalid":"Ошибка","speed":"Скорость","power":"Мощность","target":"цель"},"profiles":{"none":"Автоматическое","home":"Дом","sleep":"Сон","away":"Вне дома","comfort":"Комфорт","eco":"Энергосбережение"},"methods":{"existing":"Существующий контроллер комнаты","automatic":"Автоматическое","manual":"Вручную","off":"Выключить","pid":"PID"},"methodLabel":"Управление · Способ управления"},"sk":{"text":{"overview":"Prehľad miestnosti","devices":"Riadiace jednotky zariadení","calibration":"Kalibrácia","details":"Diagnostika","physical":"Fyzické zariadenie","target":"Cieľ","demand":"Požiadavka","supply":"Napájanie","cooldown":"Oneskorenie vypnutia","sleep":"Pauza počas spánku","reason":"Dôvod","lux":"Osvetlenosť","idle":"Nečinnosť","mean":"Priemer vybraných snímačov","partialMean":"Priemer dostupných snímačov","inputs":"Zadajte platné merania pre každý stupeň","ready":"Pripravené","unconfigured":"Nenastavené","information":"Informácie","save":"Uložiť","apply":"Použiť","gain":"Zosilnenie procesu","timeConstant":"Časová konštanta","deadTime":"Dopravné oneskorenie","speed":"Otáčky ventilátora","capacity":"Relatívny výkon","stage":"Stupeň","waiting":"Čakanie","summaryHelp":"Súhrn miestnosti. Každé zariadenie nižšie má vlastnú riadiacu jednotku.","luxHelp":"Lux meria okolité svetlo, nie kvalitu vzduchu ani slnečné teplo. Slúži na sledovanie osvetlenia.","dataHelp":"Hodnoty pochádzajú z vybraných snímačov. Overte jednotky, aktuálnosť a kalibráciu.","calHelp":"Kalibrácia je voliteľná. Použite skutočné merania; najvyššie otáčky ventilátora sú referenciou 100%.","heat":"Vykurovanie","cool":"Chladenie","dry":"Odvlhčovanie","fan":"Ventilátor","choose":"Vybrať režim","on":"Zapnuté","off":"Vypnuté","unknown":"Neznáme","legacyStrategy":"Pôvodné (nekalibrované)","measuredStrategy":"Model meraného výkonu","estimateHelp":"Odhady používajú namerané údaje a predpoklady modelu. Chýbajúce vstupy alebo nedostatočná história neumožňujú spoľahlivý výsledok.","awayProfile":"Neprítomnosť","comfortProfile":"Pohodlie","ecoProfile":"Úspora energie"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Neprítomnosť","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatické riadenie je aktívne","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Domov","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Čakanie na minimálny bezpečný čas vypnutia","minimum_on_hold":"Zariadenie zostáva zapnuté počas minimálneho bezpečného času","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatické riadenie je pozastavené","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID vyžaduje činnosť, ale výstup je vypnutý","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Nedá sa potvrdiť, či je miestnosť v režime spánku","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Čakanie na dokončenie kontrol po spustení","storage_unavailable":"Bezpečnostnú históriu sa nepodarilo načítať; riadenie pozastavené","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"V nastavenom cieľovom rozsahu","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Nečinnosť","selected_mean":"Priemer vybraných snímačov","selected_sensor":"Priemer vybraných snímačov","selected_partial_mean":"Priemer dostupných snímačov","selected_partial_sensor":"Priemer dostupných snímačov","room_selected_mean":"Priemer vybraných snímačov","complete_measured_stage_capacities_required":"Zadajte platné merania pre každý stupeň","not_configured":"Nenastavené","environment_only_no_hvac":"Súhrn miestnosti. Každé zariadenie nižšie má vlastnú riadiacu jednotku.","sleep":"Spánok","comfort":"Pohodlie","eco":"Úspora energie"},"words":{"outside":"Vonkajšie","general":"Všeobecné","area":"Oblasť","settings":"nastavenia","devices":"Zariadenia","pollen":"Peľ","room":"Miestnosť","house":"Domov","sleep":"Spánok","presence":"Obsadenosť","automatic":"Automatické","control":"ovládanie","select":"Vybrať","sensor":"senzor","source":"zdroj","off":"Vypnúť","hold":"Pozastaviť","temperature":"Teplota","humidity":"Vlhkosť","required":"Povinné","invalid":"Neplatné","speed":"Rýchlosť","power":"Výkon","target":"cieľ"},"profiles":{"none":"Automatické","home":"Domov","sleep":"Spánok","away":"Neprítomnosť","comfort":"Pohodlie","eco":"Úspora energie"},"methods":{"existing":"Existujúci regulátor miestnosti","automatic":"Automatické","manual":"Ručne","off":"Vypnúť","pid":"PID"},"methodLabel":"Ovládanie · Spôsob riadenia"},"sr":{"text":{"overview":"Преглед просторије","devices":"Контролери уређаја","calibration":"Калибрација","details":"Дијагностика","physical":"Физички уређај","target":"Циљ","demand":"Потреба","supply":"Напајање","cooldown":"Одлагање искључивања","sleep":"Пауза током спавања","reason":"Разлог","lux":"Осветљеност","idle":"Мировање","mean":"Просек изабраних сензора","partialMean":"Просек доступних сензора","inputs":"Унесите важећа мерења за сваки степен","ready":"Спремно","unconfigured":"Није подешено","information":"Информације","save":"Сачувај","apply":"Примени","gain":"Појачање процеса","timeConstant":"Временска константа","deadTime":"Мртво време","speed":"Брзина вентилатора","capacity":"Релативни капацитет","stage":"Степен","waiting":"Чекање","summaryHelp":"Сажетак просторије. Сваки уређај испод има сопствени контролер.","luxHelp":"Лукси мере околно светло, не квалитет ваздуха ни сунчеву топлоту. Користе се за праћење осветљења.","dataHelp":"Очитавања долазе са изабраних сензора. Проверите јединице, ажурност и калибрацију.","calHelp":"Калибрација није обавезна. Користите стварна мерења; највећа брзина вентилатора представља 100%.","heat":"Грејање","cool":"Хлађење","dry":"Одвлаживање","fan":"Вентилатор","choose":"Изабери режим","on":"Укључено","off":"Искључено","unknown":"Непознато","legacyStrategy":"Изворно (некалибрисано)","measuredStrategy":"Модел измереног капацитета","estimateHelp":"Процене користе очитавања сензора и претпоставке модела. Недостајући подаци или недовољна историја не дају поуздан резултат.","awayProfile":"Одсутност","comfortProfile":"Удобност","ecoProfile":"Уштеда енергије"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Одсутност","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Аутоматска контрола је активна","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Dom","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Чека се минимално безбедно време искључења","minimum_on_hold":"Уређај остаје укључен током минималног безбедног времена","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Аутоматска контрола је паузирана","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID захтева рад, али излаз је искључен","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Не може се потврдити да ли је соба у режиму спавања","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Чека се завршетак провера при покретању","storage_unavailable":"Безбедносна историја није учитана; контрола је обустављена","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"У оквиру подешеног циљног опсега","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Мировање","selected_mean":"Просек изабраних сензора","selected_sensor":"Просек изабраних сензора","selected_partial_mean":"Просек доступних сензора","selected_partial_sensor":"Просек доступних сензора","room_selected_mean":"Просек изабраних сензора","complete_measured_stage_capacities_required":"Унесите важећа мерења за сваки степен","not_configured":"Није подешено","environment_only_no_hvac":"Сажетак просторије. Сваки уређај испод има сопствени контролер.","sleep":"Spavanje","comfort":"Удобност","eco":"Уштеда енергије"},"words":{"outside":"Spoljašnji","general":"Opšta","area":"Oblast","settings":"podešavanja","devices":"Uređaji","pollen":"Polen","room":"Soba","house":"Dom","sleep":"Spavanje","presence":"Prisustvo","automatic":"Automatsko","control":"upravljanje","select":"Izaberi","sensor":"senzor","source":"izvor","off":"Isključi","hold":"Pauziraj","temperature":"Temperatura","humidity":"Vlažnost","required":"Obavezno","invalid":"Neispravno","speed":"Brzina","power":"Snaga","target":"cilj"},"profiles":{"none":"Automatsko","home":"Dom","sleep":"Spavanje","away":"Одсутност","comfort":"Удобност","eco":"Уштеда енергије"},"methods":{"existing":"Постојећи собни регулатор","automatic":"Automatsko","manual":"Ручно","off":"Isključi","pid":"PID"},"methodLabel":"Контрола · Начин управљања"},"sv":{"text":{"overview":"Rumsöversikt","devices":"Enhetsregulatorer","calibration":"Kalibrering","details":"Diagnostik","physical":"Fysisk enhet","target":"Målvärde","demand":"Behov","supply":"Strömförsörjning","cooldown":"Fördröjning före avstängning","sleep":"Sömnpaus","reason":"Orsak","lux":"Belysningsstyrka","idle":"Viloläge","mean":"Medelvärde för valda sensorer","partialMean":"Medelvärde för tillgängliga sensorer","inputs":"Ange giltiga mätningar för varje steg","ready":"Klar","unconfigured":"Inte konfigurerad","information":"Information","save":"Spara","apply":"Tillämpa","gain":"Processförstärkning","timeConstant":"Tidskonstant","deadTime":"Dödtid","speed":"Fläkthastighet","capacity":"Relativ kapacitet","stage":"Steg","waiting":"Väntar","summaryHelp":"Rumsöversikt. Varje enhet nedan har en egen regulator.","luxHelp":"Lux mäter omgivningsljus, inte luftkvalitet eller solvärme. Det används för ljus- och dagsljusrapportering.","dataHelp":"Värdena kommer från valda sensorer. Kontrollera enheter, aktualitet och kalibrering.","calHelp":"Kalibrering är valfri. Använd verkliga mätningar; högsta fläkthastigheten är referensen 100%.","heat":"Uppvärmning","cool":"Kylning","dry":"Avfuktning","fan":"Fläkt","choose":"Välj läge","on":"På","off":"Av","unknown":"Okänt","legacyStrategy":"Ursprunglig (okalibrerad)","measuredStrategy":"Modell för uppmätt kapacitet","estimateHelp":"Beräkningarna använder sensorvärden och modellantaganden. Saknade värden eller otillräcklig historik ger inget tillförlitligt resultat.","awayProfile":"Borta","comfortProfile":"Komfort","ecoProfile":"Energisparläge"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Borta","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Automatisk styrning aktiv","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Hem","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Väntar på minsta säkra avstängningstid","minimum_on_hold":"Enheten förblir på under minsta säkra drifttid","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Automatisk styrning pausad","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID begär drift, men utgången är avstängd","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Kan inte bekräfta om rummet är i sömnläge","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Väntar på att startkontrollerna slutförs","storage_unavailable":"Säkerhetshistoriken kunde inte läsas; styrningen stoppad","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Inom det inställda målintervallet","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Viloläge","selected_mean":"Medelvärde för valda sensorer","selected_sensor":"Medelvärde för valda sensorer","selected_partial_mean":"Medelvärde för tillgängliga sensorer","selected_partial_sensor":"Medelvärde för tillgängliga sensorer","room_selected_mean":"Medelvärde för valda sensorer","complete_measured_stage_capacities_required":"Ange giltiga mätningar för varje steg","not_configured":"Inte konfigurerad","environment_only_no_hvac":"Rumsöversikt. Varje enhet nedan har en egen regulator.","sleep":"Sömn","comfort":"Komfort","eco":"Energisparläge"},"words":{"outside":"Utomhus","general":"Allmänna","area":"Område","settings":"inställningar","devices":"Enheter","pollen":"Pollen","room":"Rum","house":"Hem","sleep":"Sömn","presence":"Närvaro","automatic":"Automatisk","control":"styrning","select":"Välj","sensor":"sensor","source":"källa","off":"Stäng av","hold":"Pausa","temperature":"Temperatur","humidity":"Luftfuktighet","required":"Krävs","invalid":"Ogiltig","speed":"Hastighet","power":"Effekt","target":"mål"},"profiles":{"none":"Automatisk","home":"Hem","sleep":"Sömn","away":"Borta","comfort":"Komfort","eco":"Energisparläge"},"methods":{"existing":"Befintlig rumsreglering","automatic":"Automatisk","manual":"Manuell","off":"Stäng av","pid":"PID"},"methodLabel":"Styrning · Styrmetod"},"ta":{"text":{"overview":"அறை கண்ணோட்டம்","devices":"சாதனக் கட்டுப்படுத்திகள்","calibration":"அளவுத்திருத்தம்","details":"கண்டறிதல்","physical":"இயற்பியல் சாதனம்","target":"இலக்கு","demand":"தேவை","supply":"மின்வழங்கல்","cooldown":"அணைக்கும் தாமதம்","sleep":"தூக்க இடைநிறுத்தம்","reason":"காரணம்","lux":"ஒளியளவு","idle":"செயலற்ற நிலை","mean":"தேர்ந்தெடுத்த உணரிகளின் சராசரி","partialMean":"கிடைக்கும் உணரிகளின் சராசரி","inputs":"ஒவ்வொரு நிலைக்கும் சரியான அளவீடுகளை உள்ளிடவும்","ready":"தயார்","unconfigured":"அமைக்கப்படவில்லை","information":"தகவல்","save":"சேமி","apply":"பயன்படுத்து","gain":"செயல்முறை பெருக்கம்","timeConstant":"கால மாறிலி","deadTime":"தாமத நேரம்","speed":"விசிறி வேகம்","capacity":"ஒப்பீட்டுத் திறன்","stage":"நிலை","waiting":"காத்திருக்கிறது","summaryHelp":"அறையின் சுருக்கம். கீழுள்ள ஒவ்வொரு சாதனத்திற்கும் தனிக் கட்டுப்படுத்தி உள்ளது.","luxHelp":"லக்ஸ் சுற்றுப்புற ஒளியை அளவிடுகிறது; காற்றுத் தரத்தையோ சூரிய வெப்பத்தையோ அல்ல. ஒளியைக் கண்காணிக்க இது பயன்படுகிறது.","dataHelp":"அளவீடுகள் தேர்ந்தெடுத்த உணரிகளிலிருந்து வருகின்றன. அலகுகள், புதுமை மற்றும் அளவுத்திருத்தத்தைச் சரிபார்க்கவும்.","calHelp":"அளவுத்திருத்தம் விருப்பமானது. உண்மையான அளவீடுகளைப் பயன்படுத்தவும்; அதிகபட்ச விசிறி வேகம் 100% குறிப்பு.","heat":"வெப்பமாக்கல்","cool":"குளிர்வித்தல்","dry":"ஈரப்பத நீக்கம்","fan":"விசிறி","choose":"முறையைத் தேர்ந்தெடு","on":"இயக்கத்தில்","off":"அணைந்துள்ளது","unknown":"தெரியவில்லை","legacyStrategy":"அசல் (அளவுத்திருத்தமற்றது)","measuredStrategy":"அளவிடப்பட்ட திறன் மாதிரி","estimateHelp":"மதிப்பீடுகள் உணரி அளவீடுகளையும் மாதிரி ஊகங்களையும் பயன்படுத்துகின்றன. குறைந்த தரவு அல்லது போதாத வரலாறு நம்பகமான முடிவைத் தராது.","awayProfile":"வீட்டில் இல்லை","comfortProfile":"வசதி","ecoProfile":"ஆற்றல் சேமிப்பு"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"வீட்டில் இல்லை","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"தானியங்கி கட்டுப்பாடு செயல்படுகிறது","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"வீடு","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"குறைந்தபட்ச பாதுகாப்பான நிறுத்த நேரத்திற்காக காத்திருக்கிறது","minimum_on_hold":"குறைந்தபட்ச பாதுகாப்பான நேரம் வரை சாதனம் இயங்குகிறது","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"தானியங்கி கட்டுப்பாடு இடைநிறுத்தப்பட்டது","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID இயங்கக் கோருகிறது, ஆனால் வெளியீடு அணைக்கப்பட்டுள்ளது","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"இந்த அறை உறக்க நிலையில் உள்ளதா என்பதை உறுதிப்படுத்த முடியவில்லை","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"தொடக்க பாதுகாப்புச் சோதனைகள் முடியும் வரை காத்திருக்கிறது","storage_unavailable":"பாதுகாப்பு வரலாறு ஏற்றப்படவில்லை; கட்டுப்பாடு நிறுத்தப்பட்டது","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"அமைக்கப்பட்ட இலக்கு வரம்புக்குள் உள்ளது","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"செயலற்ற நிலை","selected_mean":"தேர்ந்தெடுத்த உணரிகளின் சராசரி","selected_sensor":"தேர்ந்தெடுத்த உணரிகளின் சராசரி","selected_partial_mean":"கிடைக்கும் உணரிகளின் சராசரி","selected_partial_sensor":"கிடைக்கும் உணரிகளின் சராசரி","room_selected_mean":"தேர்ந்தெடுத்த உணரிகளின் சராசரி","complete_measured_stage_capacities_required":"ஒவ்வொரு நிலைக்கும் சரியான அளவீடுகளை உள்ளிடவும்","not_configured":"அமைக்கப்படவில்லை","environment_only_no_hvac":"அறையின் சுருக்கம். கீழுள்ள ஒவ்வொரு சாதனத்திற்கும் தனிக் கட்டுப்படுத்தி உள்ளது.","sleep":"தூக்கம்","comfort":"வசதி","eco":"ஆற்றல் சேமிப்பு"},"words":{"outside":"வெளிப்புற","general":"பொது","area":"பகுதி","settings":"அமைப்புகள்","devices":"சாதனங்கள்","pollen":"மகரந்தம்","room":"அறை","house":"வீடு","sleep":"தூக்கம்","presence":"இருப்பு","automatic":"தானியங்கி","control":"கட்டுப்பாடு","select":"தேர்வு","sensor":"உணரி","source":"மூலம்","off":"அணை","hold":"இடைநிறுத்து","temperature":"வெப்பநிலை","humidity":"ஈரப்பதம்","required":"தேவை","invalid":"செல்லாதது","speed":"வேகம்","power":"சக்தி","target":"இலக்கு"},"profiles":{"none":"தானியங்கி","home":"வீடு","sleep":"தூக்கம்","away":"வீட்டில் இல்லை","comfort":"வசதி","eco":"ஆற்றல் சேமிப்பு"},"methods":{"existing":"தற்போதைய அறைக் கட்டுப்படுத்தி","automatic":"தானியங்கி","manual":"கைமுறை","off":"அணை","pid":"PID"},"methodLabel":"கட்டுப்பாடு · கட்டுப்பாட்டு முறை"},"th":{"text":{"overview":"ภาพรวมห้อง","devices":"ตัวควบคุมอุปกรณ์","calibration":"การปรับเทียบ","details":"การวินิจฉัย","physical":"อุปกรณ์จริง","target":"เป้าหมาย","demand":"ความต้องการ","supply":"แหล่งจ่ายไฟ","cooldown":"เวลาหน่วงก่อนตัดไฟ","sleep":"หยุดระหว่างนอน","reason":"เหตุผล","lux":"ความส่องสว่าง","idle":"ไม่ได้ทำงาน","mean":"ค่าเฉลี่ยเซนเซอร์ที่เลือก","partialMean":"ค่าเฉลี่ยเซนเซอร์ที่ใช้งานได้","inputs":"ป้อนค่าที่ถูกต้องสำหรับทุกระดับ","ready":"พร้อม","unconfigured":"ยังไม่ได้ตั้งค่า","information":"ข้อมูล","save":"บันทึก","apply":"ใช้ค่า","gain":"อัตราขยายกระบวนการ","timeConstant":"ค่าคงตัวเวลา","deadTime":"เวลาหน่วง","speed":"ความเร็วพัดลม","capacity":"กำลังสัมพัทธ์","stage":"ระดับ","waiting":"กำลังรอ","summaryHelp":"สรุปห้อง อุปกรณ์แต่ละตัวด้านล่างมีตัวควบคุมของตนเอง","luxHelp":"ลักซ์วัดแสงโดยรอบ ไม่ใช่คุณภาพอากาศหรือความร้อนจากดวงอาทิตย์ ใช้ติดตามความสว่าง","dataHelp":"ค่ามาจากเซนเซอร์ที่เลือก ตรวจสอบหน่วย ความใหม่ และการปรับเทียบ","calHelp":"การปรับเทียบเป็นทางเลือก ใช้ค่าที่วัดจริง โดยความเร็วพัดลมสูงสุดเป็นค่าอ้างอิง 100%","heat":"ทำความร้อน","cool":"ทำความเย็น","dry":"ลดความชื้น","fan":"พัดลม","choose":"เลือกโหมด","on":"เปิด","off":"ปิด","unknown":"ไม่ทราบ","legacyStrategy":"เดิม (ยังไม่ปรับเทียบ)","measuredStrategy":"แบบจำลองกำลังที่วัดได้","estimateHelp":"ค่าประมาณใช้ข้อมูลเซนเซอร์และสมมติฐานของแบบจำลอง ข้อมูลที่ขาดหรือประวัติไม่เพียงพอไม่ให้ผลที่เชื่อถือได้","awayProfile":"ไม่อยู่บ้าน","comfortProfile":"สบาย","ecoProfile":"ประหยัดพลังงาน"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"ไม่อยู่บ้าน","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"ระบบควบคุมอัตโนมัติกำลังทำงาน","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"บ้าน","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"กำลังรอเวลาปิดเครื่องขั้นต่ำเพื่อความปลอดภัย","minimum_on_hold":"อุปกรณ์ยังคงเปิดจนถึงเวลาทำงานขั้นต่ำที่ปลอดภัย","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"ระบบควบคุมอัตโนมัติหยุดชั่วคราว","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID ต้องการให้ทำงาน แต่เอาต์พุตยังปิดอยู่","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"ไม่สามารถยืนยันได้ว่าห้องนี้อยู่ในโหมดนอนหลับหรือไม่","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"กำลังรอให้การตรวจสอบหลังเริ่มทำงานเสร็จสิ้น","storage_unavailable":"โหลดประวัติความปลอดภัยไม่ได้ จึงระงับการควบคุม","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"อยู่ในช่วงค่าเป้าหมายที่ตั้งไว้","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"ไม่ได้ทำงาน","selected_mean":"ค่าเฉลี่ยเซนเซอร์ที่เลือก","selected_sensor":"ค่าเฉลี่ยเซนเซอร์ที่เลือก","selected_partial_mean":"ค่าเฉลี่ยเซนเซอร์ที่ใช้งานได้","selected_partial_sensor":"ค่าเฉลี่ยเซนเซอร์ที่ใช้งานได้","room_selected_mean":"ค่าเฉลี่ยเซนเซอร์ที่เลือก","complete_measured_stage_capacities_required":"ป้อนค่าที่ถูกต้องสำหรับทุกระดับ","not_configured":"ยังไม่ได้ตั้งค่า","environment_only_no_hvac":"สรุปห้อง อุปกรณ์แต่ละตัวด้านล่างมีตัวควบคุมของตนเอง","sleep":"นอน","comfort":"สบาย","eco":"ประหยัดพลังงาน"},"words":{"outside":"ภายนอก","general":"ทั่วไป","area":"พื้นที่","settings":"การตั้งค่า","devices":"อุปกรณ์","pollen":"ละอองเกสร","room":"ห้อง","house":"บ้าน","sleep":"นอน","presence":"การมีคนอยู่","automatic":"อัตโนมัติ","control":"ควบคุม","select":"เลือก","sensor":"เซนเซอร์","source":"แหล่งข้อมูล","off":"ปิด","hold":"หยุดชั่วคราว","temperature":"อุณหภูมิ","humidity":"ความชื้น","required":"จำเป็น","invalid":"ไม่ถูกต้อง","speed":"ความเร็ว","power":"กำลังไฟ","target":"เป้าหมาย"},"profiles":{"none":"อัตโนมัติ","home":"บ้าน","sleep":"นอน","away":"ไม่อยู่บ้าน","comfort":"สบาย","eco":"ประหยัดพลังงาน"},"methods":{"existing":"ตัวควบคุมห้องเดิม","automatic":"อัตโนมัติ","manual":"ด้วยตนเอง","off":"ปิด","pid":"PID"},"methodLabel":"การควบคุม · วิธีควบคุม"},"tr":{"text":{"overview":"Oda özeti","devices":"Cihaz denetleyicileri","calibration":"Kalibrasyon","details":"Tanılama","physical":"Fiziksel cihaz","target":"Hedef","demand":"Talep","supply":"Güç kaynağı","cooldown":"Kapatma gecikmesi","sleep":"Uyku duraklaması","reason":"Neden","lux":"Aydınlık düzeyi","idle":"Boşta","mean":"Seçili sensörlerin ortalaması","partialMean":"Kullanılabilir sensörlerin ortalaması","inputs":"Her kademe için geçerli ölçümler girin","ready":"Hazır","unconfigured":"Yapılandırılmamış","information":"Bilgi","save":"Kaydet","apply":"Uygula","gain":"Proses kazancı","timeConstant":"Zaman sabiti","deadTime":"Ölü zaman","speed":"Fan hızı","capacity":"Göreli kapasite","stage":"Kademe","waiting":"Bekliyor","summaryHelp":"Oda özeti. Aşağıdaki her cihazın kendi denetleyicisi vardır.","luxHelp":"Lüks ortam ışığını ölçer; hava kalitesini veya güneş ısısını ölçmez. Aydınlık ve gün ışığı takibinde kullanılır.","dataHelp":"Değerler seçili sensörlerden gelir. Birimleri, güncelliği ve kalibrasyonu kontrol edin.","calHelp":"Kalibrasyon isteğe bağlıdır. Gerçek ölçümleri kullanın; en yüksek fan hızı %100 referansıdır.","heat":"Isıtma","cool":"Soğutma","dry":"Nem alma","fan":"Fan","choose":"Mod seçin","on":"Açık","off":"Kapalı","unknown":"Bilinmiyor","legacyStrategy":"Orijinal (kalibre edilmemiş)","measuredStrategy":"Ölçülen kapasite modeli","estimateHelp":"Tahminler sensör verilerini ve model varsayımlarını kullanır. Eksik veriler veya yetersiz geçmiş güvenilir sonuç sağlamaz.","awayProfile":"Evde değil","comfortProfile":"Konfor","ecoProfile":"Enerji tasarrufu"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Evde değil","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Otomatik kontrol etkin","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Ev","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Güvenli asgari kapalı kalma süresi bekleniyor","minimum_on_hold":"Cihaz güvenli asgari çalışma süresi boyunca açık tutuluyor","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Otomatik kontrol duraklatıldı","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID çalışma istiyor ancak çıkış kapalı","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Odanın uyku modunda olduğu doğrulanamıyor","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Başlangıç kontrollerinin tamamlanması bekleniyor","storage_unavailable":"Güvenlik geçmişi yüklenemedi; kontrol askıya alındı","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Ayarlanan hedef aralığında","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Boşta","selected_mean":"Seçili sensörlerin ortalaması","selected_sensor":"Seçili sensörlerin ortalaması","selected_partial_mean":"Kullanılabilir sensörlerin ortalaması","selected_partial_sensor":"Kullanılabilir sensörlerin ortalaması","room_selected_mean":"Seçili sensörlerin ortalaması","complete_measured_stage_capacities_required":"Her kademe için geçerli ölçümler girin","not_configured":"Yapılandırılmamış","environment_only_no_hvac":"Oda özeti. Aşağıdaki her cihazın kendi denetleyicisi vardır.","sleep":"Uyku","comfort":"Konfor","eco":"Enerji tasarrufu"},"words":{"outside":"Dış","general":"Genel","area":"Alan","settings":"ayarlar","devices":"Cihazlar","pollen":"Polen","room":"Oda","house":"Ev","sleep":"Uyku","presence":"Doluluk","automatic":"Otomatik","control":"kontrol","select":"Seç","sensor":"sensör","source":"kaynak","off":"Kapat","hold":"Duraklat","temperature":"Sıcaklık","humidity":"Nem","required":"Gerekli","invalid":"Geçersiz","speed":"Hız","power":"Güç","target":"hedef"},"profiles":{"none":"Otomatik","home":"Ev","sleep":"Uyku","away":"Evde değil","comfort":"Konfor","eco":"Enerji tasarrufu"},"methods":{"existing":"Mevcut oda denetleyicisi","automatic":"Otomatik","manual":"Manuel","off":"Kapat","pid":"PID"},"methodLabel":"Kontrol · Kontrol yöntemi"},"uk":{"text":{"overview":"Огляд кімнати","devices":"Контролери пристроїв","calibration":"Калібрування","details":"Діагностика","physical":"Фізичний пристрій","target":"Ціль","demand":"Потреба","supply":"Живлення","cooldown":"Затримка вимкнення","sleep":"Пауза під час сну","reason":"Причина","lux":"Освітленість","idle":"Спокій","mean":"Середнє вибраних датчиків","partialMean":"Середнє доступних датчиків","inputs":"Введіть коректні вимірювання для кожного ступеня","ready":"Готово","unconfigured":"Не налаштовано","information":"Інформація","save":"Зберегти","apply":"Застосувати","gain":"Підсилення процесу","timeConstant":"Стала часу","deadTime":"Час затримки","speed":"Швидкість вентилятора","capacity":"Відносна потужність","stage":"Ступінь","waiting":"Очікування","summaryHelp":"Підсумок кімнати. Кожен пристрій нижче має власний контролер.","luxHelp":"Люкси вимірюють освітленість, а не якість повітря чи сонячне тепло. Вони використовуються для спостереження за освітленням.","dataHelp":"Показання надходять від вибраних датчиків. Перевірте одиниці, актуальність і калібрування.","calHelp":"Калібрування необов’язкове. Використовуйте реальні вимірювання; максимальна швидкість вентилятора відповідає 100%.","heat":"Обігрів","cool":"Охолодження","dry":"Осушення","fan":"Вентилятор","choose":"Вибрати режим","on":"Увімкнено","off":"Вимкнено","unknown":"Невідомо","legacyStrategy":"Початкове (без калібрування)","measuredStrategy":"Модель виміряної потужності","estimateHelp":"Оцінки використовують показання датчиків і припущення моделі. За браку даних чи історії надійний результат неможливий.","awayProfile":"Відсутність","comfortProfile":"Комфорт","ecoProfile":"Енергозбереження"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Відсутність","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Автоматичне керування активне","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Дім","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Очікування мінімального безпечного часу вимкнення","minimum_on_hold":"Пристрій залишатиметься увімкненим протягом мінімального безпечного часу","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Автоматичне керування призупинено","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"ПІД вимагає роботи, але вихід вимкнений","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Неможливо підтвердити, чи перебуває кімната в режимі сну","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Очікування завершення перевірок після запуску","storage_unavailable":"Не вдалося завантажити історію безпеки; керування зупинено","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"У межах заданого цільового діапазону","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Спокій","selected_mean":"Середнє вибраних датчиків","selected_sensor":"Середнє вибраних датчиків","selected_partial_mean":"Середнє доступних датчиків","selected_partial_sensor":"Середнє доступних датчиків","room_selected_mean":"Середнє вибраних датчиків","complete_measured_stage_capacities_required":"Введіть коректні вимірювання для кожного ступеня","not_configured":"Не налаштовано","environment_only_no_hvac":"Підсумок кімнати. Кожен пристрій нижче має власний контролер.","sleep":"Сон","comfort":"Комфорт","eco":"Енергозбереження"},"words":{"outside":"Зовнішні","general":"Загальні","area":"Зона","settings":"налаштування","devices":"Пристрої","pollen":"Пилок","room":"Кімната","house":"Дім","sleep":"Сон","presence":"Присутність","automatic":"Автоматичне","control":"керування","select":"Обрати","sensor":"датчик","source":"джерело","off":"Вимкнути","hold":"Призупинити","temperature":"Температура","humidity":"Вологість","required":"Обов'язково","invalid":"Неправильно","speed":"Швидкість","power":"Потужність","target":"ціль"},"profiles":{"none":"Автоматичне","home":"Дім","sleep":"Сон","away":"Відсутність","comfort":"Комфорт","eco":"Енергозбереження"},"methods":{"existing":"Наявний контролер кімнати","automatic":"Автоматичне","manual":"Вручну","off":"Вимкнути","pid":"PID"},"methodLabel":"Керування · Спосіб керування"},"ur":{"text":{"overview":"کمرے کا جائزہ","devices":"آلات کے کنٹرولر","calibration":"کیلیبریشن","details":"تشخیص","physical":"اصل آلہ","target":"ہدف","demand":"طلب","supply":"بجلی کی فراہمی","cooldown":"بند کرنے میں تاخیر","sleep":"نیند کے دوران توقف","reason":"وجہ","lux":"روشنی کی شدت","idle":"غیر فعال","mean":"منتخب سینسروں کی اوسط","partialMean":"دستیاب سینسروں کی اوسط","inputs":"ہر درجے کے لیے درست پیمائش درج کریں","ready":"تیار","unconfigured":"ترتیب نہیں دی گئی","information":"معلومات","save":"محفوظ کریں","apply":"لاگو کریں","gain":"عمل کا گین","timeConstant":"وقت کا مستقل","deadTime":"تاخیر کا وقت","speed":"پنکھے کی رفتار","capacity":"نسبتی صلاحیت","stage":"درجہ","waiting":"انتظار","summaryHelp":"کمرے کا خلاصہ۔ نیچے ہر آلے کا اپنا کنٹرولر ہے۔","luxHelp":"لکس ماحول کی روشنی ناپتا ہے، ہوا کا معیار یا سورج کی حرارت نہیں۔ اسے روشنی کی نگرانی کے لیے استعمال کیا جاتا ہے۔","dataHelp":"ریڈنگ منتخب سینسروں سے آتی ہے۔ اکائیاں، تازگی اور کیلیبریشن چیک کریں۔","calHelp":"کیلیبریشن اختیاری ہے۔ حقیقی پیمائش استعمال کریں؛ پنکھے کی سب سے زیادہ رفتار 100% حوالہ ہے۔","heat":"گرم کرنا","cool":"ٹھنڈا کرنا","dry":"نمی دور کرنا","fan":"پنکھا","choose":"موڈ منتخب کریں","on":"چالو","off":"بند","unknown":"نامعلوم","legacyStrategy":"اصل (بغیر کیلیبریشن)","measuredStrategy":"ماپی گئی صلاحیت کا ماڈل","estimateHelp":"تخمینے سینسر کی ریڈنگ اور ماڈل کے مفروضوں پر مبنی ہیں۔ نامکمل ڈیٹا یا ناکافی تاریخ قابل اعتماد نتیجہ نہیں دیتی۔","awayProfile":"گھر سے باہر","comfortProfile":"آرام","ecoProfile":"توانائی کی بچت"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"گھر سے باہر","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"خودکار کنٹرول فعال ہے","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"گھر","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"کم از کم محفوظ بند رہنے کے وقت کا انتظار","minimum_on_hold":"آلہ کم از کم محفوظ مدت تک چلتا رہے گا","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"خودکار کنٹرول عارضی طور پر روکا گیا ہے","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID کام کی درخواست کر رہا ہے مگر آؤٹ پٹ بند ہے","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"یہ تصدیق نہیں ہو سکتی کہ کمرہ نیند کے موڈ میں ہے","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"ابتدائی حفاظتی جانچ مکمل ہونے کا انتظار","storage_unavailable":"حفاظتی تاریخ لوڈ نہیں ہو سکی؛ کنٹرول معطل ہے","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"طے شدہ ہدف کی حد کے اندر","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"غیر فعال","selected_mean":"منتخب سینسروں کی اوسط","selected_sensor":"منتخب سینسروں کی اوسط","selected_partial_mean":"دستیاب سینسروں کی اوسط","selected_partial_sensor":"دستیاب سینسروں کی اوسط","room_selected_mean":"منتخب سینسروں کی اوسط","complete_measured_stage_capacities_required":"ہر درجے کے لیے درست پیمائش درج کریں","not_configured":"ترتیب نہیں دی گئی","environment_only_no_hvac":"کمرے کا خلاصہ۔ نیچے ہر آلے کا اپنا کنٹرولر ہے۔","sleep":"نیند","comfort":"آرام","eco":"توانائی کی بچت"},"words":{"outside":"باہر","general":"عمومی","area":"علاقہ","settings":"ترتیبات","devices":"آلات","pollen":"زرگل","room":"کمرہ","house":"گھر","sleep":"نیند","presence":"موجودگی","automatic":"خودکار","control":"کنٹرول","select":"منتخب کریں","sensor":"سینسر","source":"ماخذ","off":"بند","hold":"وقفہ","temperature":"درجہ حرارت","humidity":"نمی","required":"ضروری","invalid":"غلط","speed":"رفتار","power":"طاقت","target":"ہدف"},"profiles":{"none":"خودکار","home":"گھر","sleep":"نیند","away":"گھر سے باہر","comfort":"آرام","eco":"توانائی کی بچت"},"methods":{"existing":"موجودہ کمرے کا کنٹرولر","automatic":"خودکار","manual":"دستی","off":"بند","pid":"PID"},"methodLabel":"کنٹرول · کنٹرول کا طریقہ"},"vi":{"text":{"overview":"Tổng quan phòng","devices":"Bộ điều khiển thiết bị","calibration":"Hiệu chuẩn","details":"Chẩn đoán","physical":"Thiết bị thực","target":"Mục tiêu","demand":"Nhu cầu","supply":"Nguồn điện","cooldown":"Thời gian chờ ngắt điện","sleep":"Tạm dừng khi ngủ","reason":"Lý do","lux":"Độ rọi","idle":"Nghỉ","mean":"Trung bình cảm biến đã chọn","partialMean":"Trung bình cảm biến khả dụng","inputs":"Nhập số đo hợp lệ cho từng cấp","ready":"Sẵn sàng","unconfigured":"Chưa cấu hình","information":"Thông tin","save":"Lưu","apply":"Áp dụng","gain":"Hệ số khuếch đại quá trình","timeConstant":"Hằng số thời gian","deadTime":"Thời gian trễ","speed":"Tốc độ quạt","capacity":"Công suất tương đối","stage":"Cấp","waiting":"Đang chờ","summaryHelp":"Tóm tắt phòng. Mỗi thiết bị bên dưới có bộ điều khiển riêng.","luxHelp":"Lux đo ánh sáng xung quanh, không đo chất lượng không khí hay nhiệt mặt trời. Nó dùng để theo dõi ánh sáng.","dataHelp":"Số đo đến từ cảm biến đã chọn. Kiểm tra đơn vị, độ mới và hiệu chuẩn.","calHelp":"Hiệu chuẩn là tùy chọn. Dùng số đo thực; tốc độ quạt cao nhất là mốc 100%.","heat":"Sưởi","cool":"Làm mát","dry":"Hút ẩm","fan":"Quạt","choose":"Chọn chế độ","on":"Bật","off":"Tắt","unknown":"Không rõ","legacyStrategy":"Ban đầu (chưa hiệu chuẩn)","measuredStrategy":"Mô hình công suất đã đo","estimateHelp":"Ước tính sử dụng số đo cảm biến và giả định mô hình. Thiếu dữ liệu hoặc lịch sử không đủ sẽ không cho kết quả đáng tin cậy.","awayProfile":"Vắng nhà","comfortProfile":"Thoải mái","ecoProfile":"Tiết kiệm năng lượng"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"Vắng nhà","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"Điều khiển tự động đang hoạt động","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"Nhà","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"Đang chờ hết thời gian tắt tối thiểu để bảo vệ thiết bị","minimum_on_hold":"Thiết bị duy trì hoạt động trong thời gian bật tối thiểu an toàn","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"Điều khiển tự động tạm dừng","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID yêu cầu hoạt động nhưng đầu ra đang tắt","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"Không thể xác nhận phòng này đang ở chế độ ngủ","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"Đang chờ hoàn tất kiểm tra khi khởi động","storage_unavailable":"Không thể tải lịch sử an toàn; điều khiển tạm dừng","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"Nằm trong khoảng mục tiêu đã đặt","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"Nghỉ","selected_mean":"Trung bình cảm biến đã chọn","selected_sensor":"Trung bình cảm biến đã chọn","selected_partial_mean":"Trung bình cảm biến khả dụng","selected_partial_sensor":"Trung bình cảm biến khả dụng","room_selected_mean":"Trung bình cảm biến đã chọn","complete_measured_stage_capacities_required":"Nhập số đo hợp lệ cho từng cấp","not_configured":"Chưa cấu hình","environment_only_no_hvac":"Tóm tắt phòng. Mỗi thiết bị bên dưới có bộ điều khiển riêng.","sleep":"Ngủ","comfort":"Thoải mái","eco":"Tiết kiệm năng lượng"},"words":{"outside":"Bên ngoài","general":"Chung","area":"Khu vực","settings":"cài đặt","devices":"Thiết bị","pollen":"Phấn hoa","room":"Phòng","house":"Nhà","sleep":"Ngủ","presence":"Hiện diện","automatic":"Tự động","control":"điều khiển","select":"Chọn","sensor":"cảm biến","source":"nguồn","off":"Tắt","hold":"Tạm dừng","temperature":"Nhiệt độ","humidity":"Độ ẩm","required":"Bắt buộc","invalid":"Không hợp lệ","speed":"Tốc độ","power":"Công suất","target":"mục tiêu"},"profiles":{"none":"Tự động","home":"Nhà","sleep":"Ngủ","away":"Vắng nhà","comfort":"Thoải mái","eco":"Tiết kiệm năng lượng"},"methods":{"existing":"Bộ điều khiển phòng hiện có","automatic":"Tự động","manual":"Thủ công","off":"Tắt","pid":"PID"},"methodLabel":"Điều khiển · Phương pháp điều khiển"},"zh-hans":{"text":{"overview":"房间概览","devices":"设备控制器","calibration":"校准","details":"诊断","physical":"实体设备","target":"目标","demand":"需求","supply":"供电","cooldown":"断电等待时间","sleep":"睡眠暂停","reason":"原因","lux":"照度","idle":"待机","mean":"所选传感器的平均值","partialMean":"可用传感器的平均值","inputs":"请为每个档位输入有效测量值","ready":"就绪","unconfigured":"未配置","information":"信息","save":"保存","apply":"应用","gain":"过程增益","timeConstant":"时间常数","deadTime":"延迟时间","speed":"风扇速度","capacity":"相对能力","stage":"档位","waiting":"等待中","summaryHelp":"房间概览。下方每台设备都有独立的控制器。","luxHelp":"勒克斯衡量环境光，不代表空气质量或太阳热量。用于光照和日光信息。","dataHelp":"读数来自所选传感器。请检查单位、更新时间和校准情况。","calHelp":"校准是可选的。请使用实际测量值；最高风速是100%的参考值。","heat":"制热","cool":"制冷","dry":"除湿","fan":"风扇","choose":"选择模式","on":"开启","off":"关闭","unknown":"未知","legacyStrategy":"原始分配（未校准）","measuredStrategy":"实测能力模型","estimateHelp":"估算使用传感器读数和模型假设。输入缺失或历史记录不足时，无法得到可靠结果。","awayProfile":"离家","comfortProfile":"舒适","ecoProfile":"节能"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"离家","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"自动控制正在运行","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"家中","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"等待满足安全最短关闭时间","minimum_on_hold":"设备将保持开启直至满足安全最短运行时间","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"自动控制已暂停","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID 已请求运行，但输出仍处于关闭状态","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"无法确认该房间是否处于睡眠模式","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"等待启动检查完成","storage_unavailable":"无法加载安全历史记录；自动控制已暂停","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"处于设定的目标范围内","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"待机","selected_mean":"所选传感器的平均值","selected_sensor":"所选传感器的平均值","selected_partial_mean":"可用传感器的平均值","selected_partial_sensor":"可用传感器的平均值","room_selected_mean":"所选传感器的平均值","complete_measured_stage_capacities_required":"请为每个档位输入有效测量值","not_configured":"未配置","environment_only_no_hvac":"房间概览。下方每台设备都有独立的控制器。","sleep":"睡眠","comfort":"舒适","eco":"节能"},"words":{"outside":"室外","general":"常规","area":"区域","settings":"设置","devices":"设备","pollen":"花粉","room":"房间","house":"家中","sleep":"睡眠","presence":"占用","automatic":"自动","control":"控制","select":"选择","sensor":"传感器","source":"来源","off":"关闭","hold":"暂停","temperature":"温度","humidity":"湿度","required":"必填","invalid":"无效","speed":"速度","power":"功率","target":"目标"},"profiles":{"none":"自动","home":"家中","sleep":"睡眠","away":"离家","comfort":"舒适","eco":"节能"},"methods":{"existing":"现有房间控制器","automatic":"自动","manual":"手动","off":"关闭","pid":"PID"},"methodLabel":"控制 · 控制方式"},"zh-hant":{"text":{"overview":"房間概覽","devices":"裝置控制器","calibration":"校正","details":"診斷","physical":"實體裝置","target":"目標","demand":"需求","supply":"供電","cooldown":"斷電等待時間","sleep":"睡眠暫停","reason":"原因","lux":"照度","idle":"待機","mean":"所選感測器的平均值","partialMean":"可用感測器的平均值","inputs":"請為每個檔位輸入有效測量值","ready":"就緒","unconfigured":"未設定","information":"資訊","save":"儲存","apply":"套用","gain":"程序增益","timeConstant":"時間常數","deadTime":"延遲時間","speed":"風扇速度","capacity":"相對能力","stage":"檔位","waiting":"等待中","summaryHelp":"房間概覽。下方每台裝置都有獨立的控制器。","luxHelp":"勒克斯衡量環境光，不代表空氣品質或太陽熱量。用於光照和日光資訊。","dataHelp":"讀數來自所選感測器。請檢查單位、更新時間及校正情況。","calHelp":"校正是可選的。請使用實際測量值；最高風速是100%的參考值。","heat":"暖房","cool":"冷房","dry":"除濕","fan":"風扇","choose":"選擇模式","on":"開啟","off":"關閉","unknown":"未知","legacyStrategy":"原始分配（未校正）","measuredStrategy":"實測能力模型","estimateHelp":"估算使用感測器讀數和模型假設。輸入缺漏或歷史記錄不足時，無法得到可靠結果。","awayProfile":"離家","comfortProfile":"舒適","ecoProfile":"節能"},"states":{"air_quality_decision_expired":"Air quality decision expired","authority_or_evidence_changed_before_dispatch":"Authority or evidence changed before dispatch","awaiting_evaluation":"Waiting for the first controller evaluation","awaiting_physical_acknowledgement":"Waiting for physical device to confirm its state","away":"離家","command_sent":"Command sent to physical device; waiting for confirmation","control_measurement_missing_or_stale":"Required control measurement is unavailable or outdated","controller_inactive":"Controller is not running","controller_paused":"Controller is paused","controlling":"自動控制正在運作","cooling_priority_defer_dehumidifier":"Cooling has priority; dehumidifier will wait","existing":"Control is handled by the existing device integration","existing_controller_selected":"Existing controller selected","fan_limits_have_no_supported_step":"Fan limits have no supported step","home":"家中","inactive":"Controller is not running","manual":"Device is in manual control","manual_no_request":"Manual mode selected; no change requested","minimum_off_hold":"等待符合安全最短關閉時間","minimum_on_hold":"裝置將保持開啟直到符合安全最短運轉時間","native_defrost_protection":"Device is defrosting; changing output is blocked","native_off_no_power_permission":"Device is off; controller cannot power it on","native_power_mode_unsupported":"Requested physical power mode is unsupported","native_service_unavailable":"Native service unavailable","native_setpoint_unavailable":"Current physical temperature setpoint is missing","native_step_exceeds_setpoint_rate_limit":"Native step exceeds setpoint rate limit","off":"Controller is switched off","open_or_unknown_window":"Window is open or its state is unknown","opposing_humidity_climate_active":"Opposing humidity climate active","opposing_humidity_device_active_or_unknown":"Opposing humidity device active or unknown","other_climate_unavailable":"Other climate unavailable","other_endpoint_acknowledgement_pending":"Other endpoint acknowledgement pending","outside_air_not_verified":"Outside air not verified","owned_shutdown_identity_or_dwell_hold":"Owned shutdown identity or dwell hold","particle_sensor_not_verified":"Particle sensor not verified","paused":"自動控制已暫停","physical_capabilities_unavailable":"Physical device capabilities cannot be read","physical_device_unavailable":"Physical device is unavailable","pid_output_inactive":"PID 已要求運作，但輸出仍處於關閉狀態","power_control_not_commissioned":"Automatic power switching is not authorized","proportional_output_not_commissioned":"Proportional output is not authorized","proportional_output_not_verified":"Proportional output limits are not verified","quiet_context_unknown":"Quiet-hours conditions cannot be verified","ready":"Ready","reconciled_waiting_minimum_off":"Device verified; waiting before restarting","retired_identity_requires_manual_reconciliation":"Retired identity requires manual reconciliation","retired_outputs_reconciled":"Retired outputs reconciled","retired_requires_manual_reconciliation":"Retired requires manual reconciliation","room_unoccupied":"Room is confirmed empty","running_device_requires_off_before_automatic_power_ownership":"Turn off the running device before automatic control can take ownership","select_control_method_to_authorize_current_device_sources":"Select an authorized control method for this device","select_fan_purpose_on_controller_device":"Choose whether the fan extracts or filters air","select_single_direction_for_pid":"Select heating or cooling direction for PID","settings_updated":"Controller settings saved","sleep_room_evidence_unknown":"無法確認此房間是否處於睡眠模式","source_deselected_or_moved":"Physical device is no longer assigned to this room","startup_warmup":"等待啟動檢查完成","storage_unavailable":"無法載入安全紀錄；自動控制已暫停","target_outside_device_limits":"Requested target exceeds device limits","target_outside_native_limits":"Requested target is outside the device operating range","thermal_priority_defer_dry":"Heating or cooling has priority over drying","unrecognized_status":"Controller condition not recognized - check status_code","unsupported_temperature_unit":"Device temperature unit is unsupported","waiting_for_physical_device":"Waiting for the physical device to become available","window_already_open_or_unknown":"Window already open or unknown","within_target_band":"位於設定的目標範圍內","device_auto_control_disabled":"Automatic control is disabled for this device","device_policy_approved":"Device is approved for automatic control","house_occupancy_unknown":"Cannot verify whether anyone is home","house_unoccupied":"Nobody is home","invalid_presence_policy":"The selected presence policy is invalid","invalid_sleep_policy":"The selected sleep policy is invalid","room_not_absent":"Someone is in the room; absence-only control is held","room_not_occupied":"Room is empty; occupancy-only control is held","room_occupancy_unknown":"Room occupancy cannot be confirmed","sleep_room_control_paused":"Control is paused because this room is sleeping","idle":"待機","selected_mean":"所選感測器的平均值","selected_sensor":"所選感測器的平均值","selected_partial_mean":"可用感測器的平均值","selected_partial_sensor":"可用感測器的平均值","room_selected_mean":"所選感測器的平均值","complete_measured_stage_capacities_required":"請為每個檔位輸入有效測量值","not_configured":"未設定","environment_only_no_hvac":"房間概覽。下方每台裝置都有獨立的控制器。","sleep":"睡眠","comfort":"舒適","eco":"節能"},"words":{"outside":"室外","general":"一般","area":"區域","settings":"設定","devices":"裝置","pollen":"花粉","room":"房間","house":"家中","sleep":"睡眠","presence":"佔用","automatic":"自動","control":"控制","select":"選擇","sensor":"感測器","source":"來源","off":"關閉","hold":"暫停","temperature":"溫度","humidity":"濕度","required":"必填","invalid":"無效","speed":"速度","power":"功率","target":"目標"},"profiles":{"none":"自動","home":"家中","sleep":"睡眠","away":"離家","comfort":"舒適","eco":"節能"},"methods":{"existing":"現有房間控制器","automatic":"自動","manual":"手動","off":"關閉","pid":"PID"},"methodLabel":"控制 · 控制方式"}};
  const proto65 = AirQualityAdvisorCard.prototype;
  proto65._l65 = function(key) {
    return (CARD65[this._language()] || CARD65.en).text[key] || CARD65.en.text[key] || '';
  };
  for (const [lang, data] of Object.entries(CARD65)) {
    LANGUAGE[lang] = {...LANGUAGE[lang], metric_illuminance:data.text.lux};
  }
  proto65._controllerStatusLabel = function(code) {
    const key=String(code ?? '').trim();
    if (!key) return '';
    const lang=this._language(), data=CARD65[lang] || CARD65.en, t=data.text;
    const modes={...data.profiles,heat:t.heat,cool:t.cool,dry:t.dry,fan_only:t.fan,
      on:t.on,off:t.off,unknown:t.unknown,unavailable:this._t('missing'),
      idle:t.idle,selected_mean:t.mean,selected_sensor:t.mean,
      selected_partial_mean:t.partialMean,selected_partial_sensor:t.partialMean,
      room_selected_mean:t.mean,not_configured:t.unconfigured,
      complete_measured_stage_capacities_required:t.inputs,
      ready_to_apply_when_physical_off:t.ready,
      ready:t.ready,measured:t.ready,choose:t.choose,
      select_pid_and_nonmanual_method:t.unconfigured,
      select_pid_and_measured_capacity_strategy:t.unconfigured,
      highest_speed_is_reference_100:t.calHelp,
      environment_only_no_hvac:t.summaryHelp,environment_only_no_primary_hvac:t.summaryHelp};
    if (modes[key]) return modes[key];
    const native=this._hass?.localize?.(
      'component.environment_manager.entity.sensor.equipment_control_status.state.'+key);
    const value=data.states[key];
    const english=CARD65.en.states[key];
    // Exact machine codes remain available in the explicit diagnostics section.
    if (typeof native==='string' && native.trim() && !native.startsWith('component.') &&
        native!==key && (lang==='en' || native!==english)) return native;
    if (value && (lang==='en' || value!==english)) return value;
    if (key==='sleep_room_control_paused') return t.sleep;
    if (key==='waiting_for_physical_device') return t.waiting+': '+t.physical;
    if (key==='sleep_room_evidence_unknown') return t.sleep+': '+t.unknown;
    if (/calibration|capacity|stage/.test(key) && /required|invalid|incomplete|missing|unmeasured/.test(key)) return t.inputs;
    if (/waiting|hold|pending|warmup/.test(key)) return t.waiting;
    return t.unknown;
  };
  proto65._climateLabels65 = function() {
    const lang=this._language(), t=CARD65[lang]?.text || CARD65.en.text;
    const data=CARD65[lang] || CARD65.en;
    const base=CLIMATE_LABELS[lang];
    const l=base ? {...base} : Object.fromEntries(Object.keys(CLIMATE_LABELS.en).map(k=>[k,t.information]));
    const state=(key)=>this._controllerStatusLabel(key);
    return {...l,
      advisory:t.overview,environmentOnly:t.summaryHelp,devices:t.devices,
      method:data.methodLabel,manual:data.methods.manual,automatic:data.methods.automatic,
      existing:data.methods.existing,off:t.off,pid:'PID',
      title:base?.title || t.overview,device:t.physical,selectedDevice:t.physical,
      target:t.target,mode:t.choose,currentHumidity:this._t('humidity'),
      humidity:base?.humidity || this._t('humidity'),humidityPower:base?.humidityPower || t.supply,
      sourceStatus:t.information,moistureAction:base?.moistureAction || this._t('humidity'),
      roomTemperature:MOLD_DETAIL_LABELS[lang]?.[5] || t.physical,
      temperatureMissing:this._t('missing'),noPriority:t.idle,
      home:state('home'),away:state('away'),sleep:state('sleep'),eco:state('eco'),
      comfort:state('comfort'),holding:t.waiting,
      heat:t.heat,cool:t.cool,primary:t.physical,secondary:t.physical,
      fan:t.speed,fanPower:t.supply,dryFanAuto:t.choose,
      manualTemperature:base?.manualTemperature || t.target,
      manualHumidity:base?.manualHumidity || t.target,save:t.save,
      openEntity:base?.openEntity || t.details,editFailed:base?.editFailed || this._t('missing'),
      invalidTarget:base?.invalidTarget || t.inputs,
      pause:base?.pause || state('paused'),resume:base?.resume || t.ready,
    };
  };
  proto65._pidLabels65 = function() {
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    return ['PID · '+t.calibration,this._climateLabels65().manual,'IMC / λ','Cohen-Coon',
      t.gain,t.timeConstant+' (min)',t.deadTime+' (min)','λ (min)',t.save,t.apply,t.inputs];
  };
  proto65._fanLabels65 = function() {
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    return ['PID · '+t.capacity,t.legacyStrategy,t.measuredStrategy,t.choose,t.choose,
      t.heat,t.cool,t.dry,t.fan,t.stage,t.speed,t.capacity,t.save,t.apply,t.calHelp,
      t.demand,t.capacity,t.demand,t.physical+': '+t.off];
  };
  const originalManaged65=proto65._managedControllers;
  proto65._managedControllers = function(area) {
    const states=this._hass?.states || {};
    if (this._statusStates65!==states) {
      this._statusStates65=states;
      this._statusIndex65=new Map();
      for (const [id,s] of Object.entries(states)) {
        const a=s?.attributes;
        if (!id.startsWith('sensor.') || !a || !('status_code' in a) ||
            typeof a.area_id!=='string') continue;
        const sources=Array.isArray(a.source_entity_ids) ? a.source_entity_ids : Object.keys(a.physical_entity_states || {});
        if (!sources.length) continue;
        const key=JSON.stringify([a.area_id,[...sources].sort()]);
        // Duplicate matches are ambiguous, not permission to choose one.
        this._statusIndex65.set(key,this._statusIndex65.has(key)?null:{id,state:s});
      }
    }
    return originalManaged65.call(this,area).map(entry=>({...entry,
      statusInfo:this._statusIndex65.get(JSON.stringify([area,
        [...entry.climate.attributes.source_entity_ids].sort()])) || null,
    }));
  };
  proto65._deviceSummary65 = function(entry) {
    const a=entry.climate.attributes || {}, d=entry.statusInfo?.state?.attributes || {};
    const c=a.controller_status || {};
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    const numeric=(v)=>typeof v==='number' && Number.isFinite(v);
    const value=(v,unit='')=>numeric(v)?this._format(v)+unit:null;
    const rows=[];
    const add=(label,display)=>{if(display!==null && display!==undefined && display!=='')
      rows.push('<div title="'+escape(label+': '+display)+'"><span>'+escape(label)+'</span><b>'+
        escape(display)+'</b></div>');};
    const physical=a.physical_source_state;
    add(t.physical,this._controllerStatusLabel(physical ?? 'unavailable'));
    add(t.choose,this._controllerStatusLabel(a.requested_hvac_mode || entry.climate.state));
    const observedRh=a.measurements?.humidity ?? a.current_humidity;
    if (numeric(observedRh)) add(this._t('humidity'),value(observedRh,'%'));
    if (numeric(a.humidity)) add(this._t('humidity')+' · '+t.target,value(a.humidity,'%'));
    const nativeUnit=a.temperature_unit || '°C';
    const thermalTarget=Array.isArray(a.hvac_modes) &&
      a.hvac_modes.some(mode=>['heat','cool','heat_cool','auto'].includes(mode)) &&
      !!((Number(a.supported_features) || 0) & 3);
    const hasMeasuredTemp=numeric(a.measurements?.temperature);
    const observedTemp=hasMeasuredTemp?a.measurements.temperature:a.current_temperature;
    if (numeric(observedTemp)) add(MOLD_DETAIL_LABELS[this._language()]?.[5] || t.physical,value(observedTemp,' '+(hasMeasuredTemp?'°C':nativeUnit)));
    if (thermalTarget && numeric(a.temperature)) add(t.target,value(a.temperature,' '+nativeUnit));
    if (thermalTarget && numeric(a.target_temp_low) && numeric(a.target_temp_high))
      add(t.target,this._format(a.target_temp_low)+' - '+this._format(a.target_temp_high)+' '+nativeUnit);
    add(t.demand,value(d.demand_percent ?? c.demand_percent,'%'));
    const supplyId=d.upstream_power_switch || a.upstream_power_switch;
    if (supplyId) {
      const supply=this._hass?.states?.[supplyId];
      add(t.supply,this._controllerStatusLabel(supply?.state ?? d.upstream_power_state ?? a.upstream_power_state ?? 'unavailable'));
    }
    if (numeric(d.upstream_idle_since) && numeric(d.upstream_idle_cooldown_seconds)) {
      const elapsed=Math.max(0,Date.now()/1000-d.upstream_idle_since);
      add(t.cooldown,this._format(Math.max(0,d.upstream_idle_cooldown_seconds-elapsed),0)+' s');
    }
    if (d.sleep_pause_requested===true) add(t.sleep,this._controllerStatusLabel('sleep_room_control_paused'));
    const status=d.status_code || c.status;
    const reason=d.status_reason_code || c.reason;
    const reasonLabel=reason?this._controllerStatusLabel(reason):'';
    const diagnostics=[entry.entityId,...safeArray(a.source_entity_ids),supplyId,status,reason].filter(Boolean);
    const friendlySupply=this._hass?.states?.[supplyId]?.attributes?.friendly_name;
    return '<div class="managed-status">'+escape(this._controllerStatusLabel(status || entry.climate.state))+'</div>'+
      '<div class="hem-device-data">'+rows.join('')+'</div>'+
      (friendlySupply?'<small>'+escape(t.supply)+': '+escape(friendlySupply)+'</small>':'')+
      (reasonLabel && reasonLabel!==t.unknown ? '<small>'+escape(t.reason)+': '+escape(reasonLabel)+'</small>':'')+
      '<details class="hem-diagnostics"><summary>'+escape(t.details)+'</summary><code>'+
      diagnostics.map(escape).join('<br>')+'</code></details>';
  };
  proto65._calibrationDetails65 = function(entry,content) {
    if (!content) return '';
    const opened=this._calibrationExpanded65?.has(entry.entityId)===true;
    return '<details class="hem-calibration" data-calibration-id="'+escape(entry.entityId)+'" '+
      (opened?'open':'')+'><summary>'+escape(this._l65('calibration'))+' · PID</summary>'+content+'</details>';
  };
  // Read-only informational inputs: no actuator, occupancy or air-quality claim.
  const originalMetricHelp65=proto65._metricHelp;
  proto65._metricHelp = function(item) {
    if (item.metric!=='illuminance' && ['en','el','de'].includes(this._language()))
      return originalMetricHelp65.call(this,item);
    const note=item.metric==='illuminance'?this._l65('luxHelp'):
      this._metricName(item.metric)+'. '+this._l65('dataHelp');
    const limit=typeof item.threshold==='number' && Number.isFinite(item.threshold)
      ? ' '+this._t('limits')+': '+this._format(item.threshold)+' '+String(item.unit || '')+'.' : '';
    return note+limit;
  };
  const originalScienceHelp65=proto65._scienceHelp;
  proto65._scienceHelp = function(topic) {
    return ['en','el'].includes(this._language()) ? originalScienceHelp65.call(this,topic) : this._l65('estimateHelp');
  };
  const originalMetric65=proto65._metric;
  proto65._metric = function(item,miniature=false) {
    const html=originalMetric65.call(this,item,miniature);
    if (item.metric!=='illuminance' || miniature) return html;
    const label=this._hass?.states?.[item.entity_id]?.attributes?.friendly_name || item.name;
    return label ? html.replace(/<\/div>\s*$/, '<small class="hem-source">'+escape(label)+'</small></div>') : html;
  };
  const originalStyles65=proto65._styles;
  proto65._styles = function() { return originalStyles65.call(this)+`<style>
    .hem-device-data{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}
    .hem-device-data>div{padding:8px;border-radius:9px;background:var(--secondary-background-color,rgba(127,127,127,.09));min-width:0}
    .hem-device-data span{display:block;font-size:11px;color:var(--secondary-text-color);overflow-wrap:anywhere}
    .hem-device-data b{display:block;margin-top:4px;font-size:14px;overflow-wrap:anywhere}
    .hem-calibration,.hem-diagnostics{margin-top:12px;border-top:1px solid var(--divider-color,rgba(127,127,127,.25));padding-top:8px}
    .hem-calibration>summary,.hem-diagnostics>summary{cursor:pointer;padding:8px 0;font-weight:600}
    .hem-calibration:not([open])>*:not(summary),.hem-diagnostics:not([open])>*:not(summary){display:none}
    .hem-calibration[open]>summary{margin-bottom:10px}
    .hem-diagnostics code{display:block;overflow-wrap:anywhere;white-space:normal;font-size:11px;margin:8px 0;user-select:text}
    .hem-source{display:block;font-size:10px;opacity:.8;overflow-wrap:anywhere;margin-top:6px}
    .managed-controller{min-width:0}.managed-controller .climate-entity-link strong{overflow-wrap:anywhere}
    @media(max-width:340px){.hem-device-data{grid-template-columns:1fr}}
  </style>`; };

/* HEM_CARD65_END */
/* HEM_CARD66_START */
  /* Persist user disclosure choices synchronously, before live HA renders. */
  const CARD66 = {"en":{"windowSwitch":"Stop when a window opens","windowOpen":"Paused for an open window","windowWarmup":"Waiting after windows closed","windowUnknown":"Waiting for window status","windowReady":"Windows closed","rawDetails":"Technical identifiers","controller":"Controller","source":"Physical device","status":"Status","aqiSetup":"AQI scale not configured","aqiHelp":"Select the provider's scale in outdoor AQI settings.","outsideIncomplete":"Outdoor air data incomplete","windowHelp":"Resume after 60 s continuously closed; device protection limits still apply."},"el":{"windowSwitch":"Διακοπή με ανοιχτό παράθυρο","windowOpen":"Παύση λόγω ανοιχτού παραθύρου","windowWarmup":"Αναμονή μετά το κλείσιμο παραθύρων","windowUnknown":"Αναμονή έγκυρης κατάστασης παραθύρων","windowReady":"Παράθυρα κλειστά","rawDetails":"Τεχνικά αναγνωριστικά","controller":"Ελεγκτής","source":"Φυσική συσκευή","status":"Κατάσταση","aqiSetup":"Δεν έχει οριστεί η κλίμακα AQI","aqiHelp":"Επίλεξε την κλίμακα του παρόχου στις ρυθμίσεις εξωτερικού AQI.","outsideIncomplete":"Ελλιπή δεδομένα εξωτερικού αέρα","windowHelp":"Συνέχιση μετά από 60 s με κλειστά παράθυρα, τηρώντας τα όρια προστασίας της συσκευής."},"de":{"windowSwitch":"Bei offenem Fenster ausschalten","windowOpen":"Wegen offenem Fenster pausiert","windowWarmup":"Wartezeit nach Fensterschließung","windowUnknown":"Warten auf Fensterstatus","windowReady":"Fenster geschlossen","rawDetails":"Technische Kennungen","controller":"Regler","source":"Physisches Gerät","status":"Status","aqiSetup":"AQI-Skala nicht eingerichtet","aqiHelp":"Skala des Anbieters in den Außen-AQI-Einstellungen wählen.","outsideIncomplete":"Außenluftdaten unvollständig","windowHelp":"Fortsetzen nach 60 s durchgehend geschlossenen Fenstern; Geräteschutzzeiten gelten weiterhin."},"fr":{"windowSwitch":"Arrêter à l’ouverture d’une fenêtre","windowOpen":"Pause : fenêtre ouverte","windowWarmup":"Attente après fermeture des fenêtres","windowUnknown":"En attente de l’état des fenêtres","windowReady":"Fenêtres fermées","rawDetails":"Identifiants techniques","controller":"Régulateur","source":"Appareil physique","status":"État","aqiSetup":"Échelle AQI non configurée","aqiHelp":"Choisir l’échelle du fournisseur dans les réglages AQI extérieurs.","outsideIncomplete":"Données d’air extérieur incomplètes","windowHelp":"Reprise après 60 s de fermeture continue ; les protections de l’appareil restent actives."},"es":{"windowSwitch":"Apagar al abrir una ventana","windowOpen":"Pausa por ventana abierta","windowWarmup":"Espera tras cerrar las ventanas","windowUnknown":"Esperando el estado de las ventanas","windowReady":"Ventanas cerradas","rawDetails":"Identificadores técnicos","controller":"Controlador","source":"Dispositivo físico","status":"Estado","aqiSetup":"Escala AQI sin configurar","aqiHelp":"Selecciona la escala del proveedor en los ajustes de AQI exterior.","outsideIncomplete":"Datos del aire exterior incompletos","windowHelp":"Se reanuda tras 60 s con las ventanas cerradas; se mantienen las protecciones del dispositivo."},"it":{"windowSwitch":"Spegnere quando si apre una finestra","windowOpen":"Pausa per finestra aperta","windowWarmup":"Attesa dopo la chiusura delle finestre","windowUnknown":"In attesa dello stato delle finestre","windowReady":"Finestre chiuse","rawDetails":"Identificativi tecnici","controller":"Regolatore","source":"Dispositivo fisico","status":"Stato","aqiSetup":"Scala AQI non configurata","aqiHelp":"Seleziona la scala del fornitore nelle impostazioni AQI esterne.","outsideIncomplete":"Dati dell’aria esterna incompleti","windowHelp":"Ripresa dopo 60 s di chiusura continua; restano valide le protezioni del dispositivo."},"pt":{"windowSwitch":"Desligar ao abrir uma janela","windowOpen":"Pausa por janela aberta","windowWarmup":"Espera após fechar as janelas","windowUnknown":"A aguardar o estado das janelas","windowReady":"Janelas fechadas","rawDetails":"Identificadores técnicos","controller":"Controlador","source":"Dispositivo físico","status":"Estado","aqiSetup":"Escala AQI não configurada","aqiHelp":"Selecione a escala do fornecedor nas definições de AQI exterior.","outsideIncomplete":"Dados do ar exterior incompletos","windowHelp":"Retoma após 60 s com as janelas fechadas; mantêm-se as proteções do dispositivo."},"pt-br":{"windowSwitch":"Desligar ao abrir uma janela","windowOpen":"Pausa por janela aberta","windowWarmup":"Espera após fechar as janelas","windowUnknown":"Aguardando o estado das janelas","windowReady":"Janelas fechadas","rawDetails":"Identificadores técnicos","controller":"Controlador","source":"Dispositivo físico","status":"Estado","aqiSetup":"Escala AQI não configurada","aqiHelp":"Selecione a escala do fornecedor nas configurações de AQI externo.","outsideIncomplete":"Dados do ar externo incompletos","windowHelp":"Retoma após 60 s com as janelas fechadas; as proteções do dispositivo continuam ativas."},"nl":{"windowSwitch":"Uitschakelen bij een open raam","windowOpen":"Gepauzeerd wegens open raam","windowWarmup":"Wachten na sluiten van ramen","windowUnknown":"Wachten op raamstatus","windowReady":"Ramen gesloten","rawDetails":"Technische identificaties","controller":"Regelaar","source":"Fysiek apparaat","status":"Status","aqiSetup":"AQI-schaal niet ingesteld","aqiHelp":"Kies de schaal van de aanbieder in de instellingen voor buiten-AQI.","outsideIncomplete":"Buitenluchtgegevens onvolledig","windowHelp":"Hervatten na 60 s onafgebroken gesloten ramen; apparaatbeveiligingen blijven gelden."},"da":{"windowSwitch":"Sluk, når et vindue åbnes","windowOpen":"Pause på grund af åbent vindue","windowWarmup":"Venter efter lukning af vinduer","windowUnknown":"Venter på vinduesstatus","windowReady":"Vinduer lukkede","rawDetails":"Tekniske identifikatorer","controller":"Styring","source":"Fysisk enhed","status":"Status","aqiSetup":"AQI-skala ikke konfigureret","aqiHelp":"Vælg udbyderens skala i indstillingerne for udendørs AQI.","outsideIncomplete":"Udendørs luftdata er ufuldstændige","windowHelp":"Genoptag efter 60 s med lukkede vinduer; enhedens beskyttelsesgrænser gælder stadig."},"nb":{"windowSwitch":"Slå av når et vindu åpnes","windowOpen":"Pause på grunn av åpent vindu","windowWarmup":"Venter etter at vinduene er lukket","windowUnknown":"Venter på vindusstatus","windowReady":"Vinduer lukket","rawDetails":"Tekniske identifikatorer","controller":"Kontroller","source":"Fysisk enhet","status":"Status","aqiSetup":"AQI-skala ikke konfigurert","aqiHelp":"Velg leverandørens skala i innstillingene for utendørs AQI.","outsideIncomplete":"Utendørs luftdata er ufullstendige","windowHelp":"Gjenoppta etter 60 s med lukkede vinduer; enhetens beskyttelsesgrenser gjelder fortsatt."},"sv":{"windowSwitch":"Stäng av när ett fönster öppnas","windowOpen":"Pausad på grund av öppet fönster","windowWarmup":"Väntar efter stängning av fönster","windowUnknown":"Väntar på fönsterstatus","windowReady":"Fönster stängda","rawDetails":"Tekniska identifierare","controller":"Styrenhet","source":"Fysisk enhet","status":"Status","aqiSetup":"AQI-skala inte konfigurerad","aqiHelp":"Välj leverantörens skala i inställningarna för utomhus-AQI.","outsideIncomplete":"Utomhusluftdata är ofullständiga","windowHelp":"Återuppta efter 60 s med stängda fönster; enhetens skyddsgränser gäller fortfarande."},"fi":{"windowSwitch":"Sammuta ikkunan avautuessa","windowOpen":"Tauko avoimen ikkunan vuoksi","windowWarmup":"Odotus ikkunoiden sulkemisen jälkeen","windowUnknown":"Odotetaan ikkunoiden tilatietoa","windowReady":"Ikkunat suljettu","rawDetails":"Tekniset tunnisteet","controller":"Säädin","source":"Fyysinen laite","status":"Tila","aqiSetup":"AQI-asteikkoa ei ole määritetty","aqiHelp":"Valitse palveluntarjoajan asteikko ulkoilman AQI-asetuksista.","outsideIncomplete":"Ulkoilman tiedot ovat puutteellisia","windowHelp":"Jatka ikkunoiden oltua kiinni 60 s; laitteen suojarajat ovat edelleen voimassa."},"pl":{"windowSwitch":"Wyłącz po otwarciu okna","windowOpen":"Wstrzymano z powodu otwartego okna","windowWarmup":"Oczekiwanie po zamknięciu okien","windowUnknown":"Oczekiwanie na stan okien","windowReady":"Okna zamknięte","rawDetails":"Identyfikatory techniczne","controller":"Sterownik","source":"Urządzenie fizyczne","status":"Stan","aqiSetup":"Nie skonfigurowano skali AQI","aqiHelp":"Wybierz skalę dostawcy w ustawieniach zewnętrznego AQI.","outsideIncomplete":"Niepełne dane o powietrzu na zewnątrz","windowHelp":"Wznowienie po 60 s przy zamkniętych oknach; zabezpieczenia urządzenia nadal obowiązują."},"cs":{"windowSwitch":"Vypnout při otevření okna","windowOpen":"Pozastaveno kvůli otevřenému oknu","windowWarmup":"Čekání po zavření oken","windowUnknown":"Čekání na stav oken","windowReady":"Okna zavřená","rawDetails":"Technické identifikátory","controller":"Regulátor","source":"Fyzické zařízení","status":"Stav","aqiSetup":"Stupnice AQI není nastavena","aqiHelp":"Vyberte stupnici poskytovatele v nastavení venkovního AQI.","outsideIncomplete":"Neúplná data o venkovním vzduchu","windowHelp":"Obnovení po 60 s se zavřenými okny; ochranné limity zařízení zůstávají platné."},"sk":{"windowSwitch":"Vypnúť pri otvorení okna","windowOpen":"Pozastavené pre otvorené okno","windowWarmup":"Čakanie po zatvorení okien","windowUnknown":"Čakanie na stav okien","windowReady":"Okná zatvorené","rawDetails":"Technické identifikátory","controller":"Regulátor","source":"Fyzické zariadenie","status":"Stav","aqiSetup":"Stupnica AQI nie je nastavená","aqiHelp":"Vyberte stupnicu poskytovateľa v nastaveniach vonkajšieho AQI.","outsideIncomplete":"Neúplné údaje o vonkajšom vzduchu","windowHelp":"Obnovenie po 60 s so zatvorenými oknami; ochranné limity zariadenia zostávajú platné."},"hr":{"windowSwitch":"Isključi pri otvaranju prozora","windowOpen":"Pauza zbog otvorenog prozora","windowWarmup":"Čekanje nakon zatvaranja prozora","windowUnknown":"Čekanje na stanje prozora","windowReady":"Prozori zatvoreni","rawDetails":"Tehnički identifikatori","controller":"Upravljač","source":"Fizički uređaj","status":"Stanje","aqiSetup":"AQI ljestvica nije postavljena","aqiHelp":"Odaberite ljestvicu pružatelja u postavkama vanjskog AQI-ja.","outsideIncomplete":"Nepotpuni podaci o vanjskom zraku","windowHelp":"Nastavak nakon 60 s sa zatvorenim prozorima; zaštitna ograničenja uređaja ostaju aktivna."},"sr":{"windowSwitch":"Искључи при отварању прозора","windowOpen":"Пауза због отвореног прозора","windowWarmup":"Чекање после затварања прозора","windowUnknown":"Чекање на стање прозора","windowReady":"Прозори затворени","rawDetails":"Технички идентификатори","controller":"Контролер","source":"Физички уређај","status":"Стање","aqiSetup":"AQI скала није подешена","aqiHelp":"Изаберите скалу добављача у подешавањима спољног AQI.","outsideIncomplete":"Непотпуни подаци о спољном ваздуху","windowHelp":"Наставак после 60 s са затвореним прозорима; заштитна ограничења уређаја остају активна."},"bg":{"windowSwitch":"Изключване при отваряне на прозорец","windowOpen":"Пауза заради отворен прозорец","windowWarmup":"Изчакване след затваряне на прозорците","windowUnknown":"Изчакване на състоянието на прозорците","windowReady":"Прозорците са затворени","rawDetails":"Технически идентификатори","controller":"Контролер","source":"Физическо устройство","status":"Състояние","aqiSetup":"Скалата AQI не е настроена","aqiHelp":"Изберете скалата на доставчика в настройките за външен AQI.","outsideIncomplete":"Непълни данни за външния въздух","windowHelp":"Продължаване след 60 s със затворени прозорци; защитните ограничения остават в сила."},"ro":{"windowSwitch":"Oprire la deschiderea unei ferestre","windowOpen":"Pauză din cauza ferestrei deschise","windowWarmup":"Așteptare după închiderea ferestrelor","windowUnknown":"Se așteaptă starea ferestrelor","windowReady":"Ferestre închise","rawDetails":"Identificatori tehnici","controller":"Controler","source":"Dispozitiv fizic","status":"Stare","aqiSetup":"Scala AQI nu este configurată","aqiHelp":"Selectați scala furnizorului în setările AQI exterior.","outsideIncomplete":"Date incomplete despre aerul exterior","windowHelp":"Reluare după 60 s cu ferestrele închise; protecțiile dispozitivului rămân valabile."},"hu":{"windowSwitch":"Kikapcsolás ablaknyitáskor","windowOpen":"Szünet nyitott ablak miatt","windowWarmup":"Várakozás az ablakok bezárása után","windowUnknown":"Várakozás az ablakok állapotára","windowReady":"Ablakok bezárva","rawDetails":"Műszaki azonosítók","controller":"Vezérlő","source":"Fizikai eszköz","status":"Állapot","aqiSetup":"Az AQI-skála nincs beállítva","aqiHelp":"Válassza ki a szolgáltató skáláját a kültéri AQI beállításaiban.","outsideIncomplete":"Hiányos kültéri levegőadatok","windowHelp":"Folytatás 60 s folyamatosan zárt ablak után; az eszköz védelmi korlátai továbbra is érvényesek."},"ru":{"windowSwitch":"Выключать при открытии окна","windowOpen":"Пауза из-за открытого окна","windowWarmup":"Ожидание после закрытия окон","windowUnknown":"Ожидание состояния окон","windowReady":"Окна закрыты","rawDetails":"Технические идентификаторы","controller":"Контроллер","source":"Физическое устройство","status":"Состояние","aqiSetup":"Шкала AQI не настроена","aqiHelp":"Выберите шкалу поставщика в настройках наружного AQI.","outsideIncomplete":"Неполные данные о наружном воздухе","windowHelp":"Возобновление через 60 с непрерывно закрытых окон; ограничения защиты устройства сохраняются."},"uk":{"windowSwitch":"Вимикати при відкритті вікна","windowOpen":"Пауза через відкрите вікно","windowWarmup":"Очікування після закриття вікон","windowUnknown":"Очікування стану вікон","windowReady":"Вікна закриті","rawDetails":"Технічні ідентифікатори","controller":"Контролер","source":"Фізичний пристрій","status":"Стан","aqiSetup":"Шкалу AQI не налаштовано","aqiHelp":"Виберіть шкалу постачальника в налаштуваннях зовнішнього AQI.","outsideIncomplete":"Неповні дані про зовнішнє повітря","windowHelp":"Відновлення через 60 с безперервно закритих вікон; захисні обмеження пристрою зберігаються."},"tr":{"windowSwitch":"Pencere açılınca kapat","windowOpen":"Açık pencere nedeniyle duraklatıldı","windowWarmup":"Pencereler kapandıktan sonra bekleniyor","windowUnknown":"Pencere durumu bekleniyor","windowReady":"Pencereler kapalı","rawDetails":"Teknik tanımlayıcılar","controller":"Denetleyici","source":"Fiziksel cihaz","status":"Durum","aqiSetup":"AQI ölçeği yapılandırılmamış","aqiHelp":"Dış ortam AQI ayarlarından sağlayıcının ölçeğini seçin.","outsideIncomplete":"Dış hava verileri eksik","windowHelp":"Pencereler 60 s kesintisiz kapalı kaldığında sürdürülür; cihaz koruma sınırları geçerlidir."},"ar":{"windowSwitch":"إيقاف عند فتح نافذة","windowOpen":"متوقف مؤقتًا بسبب نافذة مفتوحة","windowWarmup":"انتظار بعد إغلاق النوافذ","windowUnknown":"انتظار حالة النوافذ","windowReady":"النوافذ مغلقة","rawDetails":"المعرّفات التقنية","controller":"وحدة التحكم","source":"الجهاز الفعلي","status":"الحالة","aqiSetup":"مقياس AQI غير مضبوط","aqiHelp":"اختر مقياس المزود في إعدادات AQI الخارجي.","outsideIncomplete":"بيانات الهواء الخارجي غير مكتملة","windowHelp":"الاستئناف بعد إغلاق النوافذ باستمرار لمدة 60 ثانية؛ تبقى حدود حماية الجهاز سارية."},"fa":{"windowSwitch":"خاموش کردن هنگام باز شدن پنجره","windowOpen":"توقف به دلیل پنجره باز","windowWarmup":"انتظار پس از بسته شدن پنجره‌ها","windowUnknown":"در انتظار وضعیت پنجره‌ها","windowReady":"پنجره‌ها بسته‌اند","rawDetails":"شناسه‌های فنی","controller":"کنترل‌کننده","source":"دستگاه واقعی","status":"وضعیت","aqiSetup":"مقیاس AQI تنظیم نشده است","aqiHelp":"مقیاس ارائه‌دهنده را در تنظیمات AQI بیرون انتخاب کنید.","outsideIncomplete":"داده‌های هوای بیرون ناقص است","windowHelp":"ادامه پس از ۶۰ ثانیه بسته بودن پیوسته پنجره‌ها؛ محدودیت‌های حفاظتی دستگاه برقرارند."},"he":{"windowSwitch":"כיבוי בעת פתיחת חלון","windowOpen":"הושהה עקב חלון פתוח","windowWarmup":"המתנה לאחר סגירת החלונות","windowUnknown":"ממתין למצב החלונות","windowReady":"החלונות סגורים","rawDetails":"מזהים טכניים","controller":"בקר","source":"מכשיר פיזי","status":"מצב","aqiSetup":"סולם AQI לא הוגדר","aqiHelp":"יש לבחור את סולם הספק בהגדרות AQI חיצוני.","outsideIncomplete":"נתוני האוויר בחוץ אינם מלאים","windowHelp":"חידוש לאחר 60 שניות שבהן החלונות סגורים ברציפות; מגבלות ההגנה של המכשיר נשמרות."},"hi":{"windowSwitch":"खिड़की खुलने पर बंद करें","windowOpen":"खुली खिड़की के कारण रुका हुआ","windowWarmup":"खिड़कियाँ बंद होने के बाद प्रतीक्षा","windowUnknown":"खिड़कियों की स्थिति की प्रतीक्षा","windowReady":"खिड़कियाँ बंद हैं","rawDetails":"तकनीकी पहचानकर्ता","controller":"नियंत्रक","source":"वास्तविक उपकरण","status":"स्थिति","aqiSetup":"AQI पैमाना निर्धारित नहीं है","aqiHelp":"बाहरी AQI सेटिंग में प्रदाता का पैमाना चुनें।","outsideIncomplete":"बाहरी हवा के आँकड़े अधूरे हैं","windowHelp":"खिड़कियाँ लगातार 60 सेकंड बंद रहने पर फिर चालू होगा; उपकरण के सुरक्षा नियम लागू रहेंगे।"},"bn":{"windowSwitch":"জানালা খুললে বন্ধ করুন","windowOpen":"খোলা জানালার কারণে বিরতি","windowWarmup":"জানালা বন্ধ হওয়ার পর অপেক্ষা","windowUnknown":"জানালার অবস্থার জন্য অপেক্ষা","windowReady":"জানালা বন্ধ","rawDetails":"প্রযুক্তিগত শনাক্তকারী","controller":"নিয়ন্ত্রক","source":"বাস্তব যন্ত্র","status":"অবস্থা","aqiSetup":"AQI স্কেল নির্ধারিত নয়","aqiHelp":"বাইরের AQI সেটিংসে সরবরাহকারীর স্কেল বেছে নিন।","outsideIncomplete":"বাইরের বাতাসের তথ্য অসম্পূর্ণ","windowHelp":"জানালা একটানা 60 সেকেন্ড বন্ধ থাকলে আবার চলবে; যন্ত্রের সুরক্ষা সীমা বহাল থাকবে।"},"ur":{"windowSwitch":"کھڑکی کھلنے پر بند کریں","windowOpen":"کھلی کھڑکی کی وجہ سے توقف","windowWarmup":"کھڑکیاں بند ہونے کے بعد انتظار","windowUnknown":"کھڑکیوں کی حالت کا انتظار","windowReady":"کھڑکیاں بند ہیں","rawDetails":"تکنیکی شناخت کار","controller":"کنٹرولر","source":"اصل آلہ","status":"حالت","aqiSetup":"AQI پیمانہ مقرر نہیں","aqiHelp":"بیرونی AQI کی ترتیبات میں فراہم کنندہ کا پیمانہ منتخب کریں۔","outsideIncomplete":"بیرونی ہوا کا ڈیٹا نامکمل ہے","windowHelp":"کھڑکیاں مسلسل 60 سیکنڈ بند رہنے کے بعد دوبارہ چلے گا؛ آلے کی حفاظتی حدود برقرار رہیں گی۔"},"ta":{"windowSwitch":"சாளரம் திறந்தால் அணைக்கவும்","windowOpen":"திறந்த சாளரத்தால் இடைநிறுத்தப்பட்டது","windowWarmup":"சாளரங்கள் மூடிய பிறகு காத்திருப்பு","windowUnknown":"சாளர நிலைக்காகக் காத்திருக்கிறது","windowReady":"சாளரங்கள் மூடப்பட்டுள்ளன","rawDetails":"தொழில்நுட்ப அடையாளங்கள்","controller":"கட்டுப்படுத்தி","source":"உண்மையான சாதனம்","status":"நிலை","aqiSetup":"AQI அளவுகோல் அமைக்கப்படவில்லை","aqiHelp":"வெளிப்புற AQI அமைப்புகளில் வழங்குநரின் அளவுகோலைத் தேர்ந்தெடுக்கவும்.","outsideIncomplete":"வெளிப்புறக் காற்றுத் தரவு முழுமையில்லை","windowHelp":"சாளரங்கள் தொடர்ந்து 60 வினாடிகள் மூடிய பின் மீண்டும் இயங்கும்; சாதனப் பாதுகாப்பு வரம்புகள் தொடரும்."},"th":{"windowSwitch":"ปิดเมื่อเปิดหน้าต่าง","windowOpen":"หยุดชั่วคราวเพราะหน้าต่างเปิด","windowWarmup":"รอหลังจากปิดหน้าต่าง","windowUnknown":"รอสถานะหน้าต่าง","windowReady":"หน้าต่างปิด","rawDetails":"รหัสทางเทคนิค","controller":"ตัวควบคุม","source":"อุปกรณ์จริง","status":"สถานะ","aqiSetup":"ยังไม่ตั้งค่ามาตรา AQI","aqiHelp":"เลือกมาตราของผู้ให้บริการในการตั้งค่า AQI ภายนอก","outsideIncomplete":"ข้อมูลอากาศภายนอกไม่ครบถ้วน","windowHelp":"ทำงานต่อเมื่อหน้าต่างปิดต่อเนื่อง 60 วินาที โดยยังคงข้อจำกัดการป้องกันอุปกรณ์"},"vi":{"windowSwitch":"Tắt khi cửa sổ mở","windowOpen":"Tạm dừng vì cửa sổ mở","windowWarmup":"Chờ sau khi đóng cửa sổ","windowUnknown":"Đang chờ trạng thái cửa sổ","windowReady":"Cửa sổ đã đóng","rawDetails":"Mã định danh kỹ thuật","controller":"Bộ điều khiển","source":"Thiết bị vật lý","status":"Trạng thái","aqiSetup":"Chưa cấu hình thang AQI","aqiHelp":"Chọn thang của nhà cung cấp trong cài đặt AQI ngoài trời.","outsideIncomplete":"Dữ liệu không khí ngoài trời chưa đầy đủ","windowHelp":"Tiếp tục sau 60 giây cửa sổ đóng liên tục; vẫn tuân thủ giới hạn bảo vệ thiết bị."},"id":{"windowSwitch":"Matikan saat jendela dibuka","windowOpen":"Dijeda karena jendela terbuka","windowWarmup":"Menunggu setelah jendela ditutup","windowUnknown":"Menunggu status jendela","windowReady":"Jendela tertutup","rawDetails":"Pengenal teknis","controller":"Pengontrol","source":"Perangkat fisik","status":"Status","aqiSetup":"Skala AQI belum diatur","aqiHelp":"Pilih skala penyedia dalam pengaturan AQI luar ruangan.","outsideIncomplete":"Data udara luar belum lengkap","windowHelp":"Lanjut setelah jendela tertutup terus-menerus selama 60 detik; batas perlindungan perangkat tetap berlaku."},"ja":{"windowSwitch":"窓が開いたら停止","windowOpen":"窓が開いているため一時停止","windowWarmup":"窓を閉じた後の待機中","windowUnknown":"窓の状態を確認中","windowReady":"窓は閉じています","rawDetails":"技術識別子","controller":"コントローラー","source":"実機","status":"状態","aqiSetup":"AQIの尺度が未設定","aqiHelp":"屋外AQI設定で提供元の尺度を選択してください。","outsideIncomplete":"屋外空気のデータが不十分","windowHelp":"窓が連続して60秒閉じた後に再開します。機器の保護制限は引き続き適用されます。"},"ko":{"windowSwitch":"창문이 열리면 끄기","windowOpen":"열린 창문으로 인해 일시 중지","windowWarmup":"창문을 닫은 후 대기 중","windowUnknown":"창문 상태를 기다리는 중","windowReady":"창문 닫힘","rawDetails":"기술 식별자","controller":"제어기","source":"실제 장치","status":"상태","aqiSetup":"AQI 척도가 설정되지 않음","aqiHelp":"실외 AQI 설정에서 제공업체의 척도를 선택하세요.","outsideIncomplete":"실외 공기 데이터가 불완전함","windowHelp":"창문이 연속 60초 동안 닫힌 후 재개하며 장치 보호 제한은 계속 적용됩니다."},"zh-hans":{"windowSwitch":"开窗时停止","windowOpen":"因窗户打开而暂停","windowWarmup":"关窗后等待中","windowUnknown":"等待窗户状态","windowReady":"窗户已关闭","rawDetails":"技术标识符","controller":"控制器","source":"实体设备","status":"状态","aqiSetup":"未设置AQI标准","aqiHelp":"请在室外AQI设置中选择提供商的标准。","outsideIncomplete":"室外空气数据不完整","windowHelp":"窗户持续关闭60秒后恢复，设备保护限制仍然有效。"},"zh-hant":{"windowSwitch":"開窗時停止","windowOpen":"因窗戶開啟而暫停","windowWarmup":"關窗後等待中","windowUnknown":"等待窗戶狀態","windowReady":"窗戶已關閉","rawDetails":"技術識別碼","controller":"控制器","source":"實體裝置","status":"狀態","aqiSetup":"未設定AQI標準","aqiHelp":"請在室外AQI設定中選擇供應商的標準。","outsideIncomplete":"室外空氣資料不完整","windowHelp":"窗戶持續關閉60秒後恢復，裝置保護限制仍然有效。"}};
  const proto66 = AirQualityAdvisorCard.prototype;
  proto66._l66 = function(key) {return (CARD66[this._language()] || CARD66.en)[key] || CARD66.en[key] || '';};
  proto66._installInteractions66 = function() {
    if(this._interactions66) return;
    this._interactions66=true;
    this._detailsExpanded66=new Set();
    this._windowSwitchPending66=new Set();
    const identify=(node)=>{
      if(!node?.getAttribute) return null;
      const calibration=node.getAttribute('data-calibration-id');
      if(calibration) return [this._calibrationExpanded65,calibration];
      const id=node.getAttribute('data-detail-id');
      return id ? [this._detailsExpanded66,id] : null;
    };
    const setOpen=(node,open)=>{
      const item=identify(node);if(!item) return;
      const [set,key]=item;if(open)set.add(key);else set.delete(key);
    };
    this.shadowRoot.addEventListener('pointerdown',(e)=>{
      const summary=e.target.closest?.('summary');
      if(summary && identify(summary.parentElement)) {
        this._detailPointer66=true;clearTimeout(this._detailPointerTimer66);
        this._detailPointerTimer66=setTimeout(()=>release(),1000);
      }
    },true);
    const release=()=>{this._detailPointer66=false;clearTimeout(this._detailPointerTimer66);this._flushDeferredRenderSoon();};
    this.shadowRoot.addEventListener('pointerup',()=>setTimeout(release,0),true);
    this.shadowRoot.addEventListener('pointercancel',release,true);
    this.shadowRoot.addEventListener('click',(e)=>{
      const summary=e.target.closest?.('summary');
      const node=summary?.parentElement;
      if(summary && identify(node)) {
        e.preventDefault();e.stopPropagation();
        // Native toggle events are asynchronous. Store the intended choice
        // now so a concurrent state refresh cannot rebuild it as CLOSED.
        const open=!node.open;setOpen(node,open);node.open=open;
        release();return;
      }
      const button=e.target.closest?.('[data-window-policy-switch]');
      if(!button || !this._hass?.callService) return;
      e.preventDefault();e.stopPropagation();
      const area=button.dataset.controllerArea;
      const device=button.dataset.windowController;
      const id=button.dataset.windowPolicySwitch;
      const match=this._managedControllers(area).find(x=>x.entityId===device);
      const actual=match?.windowPolicyInfo;
      if(!actual || actual.id!==id || !['on','off'].includes(actual.state.state) ||
         this._windowSwitchPending66.has(id)) return;
      const action=actual.state.state==='on'?'turn_off':'turn_on';
      this._windowSwitchPending66.add(id);button.disabled=true;
      Promise.resolve().then(()=>this._hass.callService('switch',action,{entity_id:id}))
        .catch(()=>{this._climateEditError=this._climateLabels65().editFailed;})
        .finally(()=>{this._windowSwitchPending66.delete(id);this._render(true);});
    },true);
    this.shadowRoot.addEventListener('toggle',(e)=>{
      // Discard queued events belonging to a replaced DOM subtree.
      if(!e.target.isConnected || e.target.getRootNode()!==this.shadowRoot) return;
      setOpen(e.target,e.target.open);
    },true);
  };
  const originalDisconnect66=proto66.disconnectedCallback;
  proto66.disconnectedCallback=function(){this._detailPointer66=false;clearTimeout(this._detailPointerTimer66);return originalDisconnect66.call(this);};
  const originalRender66=proto66._render;
  proto66._render=function(force=false) {
    if(this._detailPointer66){this._pendingRender=true;this._pendingForceRender ||= force;return;}
    return originalRender66.call(this,force);
  };
  const originalStatus66=proto66._controllerStatusLabel;
  proto66._controllerStatusLabel=function(code) {
    const map={window_open_pause:'windowOpen',window_close_warmup:'windowWarmup',
      window_state_unknown:'windowUnknown',window_closed_ready:'windowReady',
      aqi_scale_unconfigured:'aqiSetup'};
    return map[code]?this._l66(map[code]):originalStatus66.call(this,code);
  };
  const originalManaged66=proto66._managedControllers;
  proto66._managedControllers=function(area) {
    const states=this._hass?.states || {};
    if(this._windowStates66!==states) {
      this._windowStates66=states;this._windowIndex66=new Map();
      for(const [id,state] of Object.entries(states)) {
        const a=state?.attributes;
        if(!id.startsWith('switch.') || a?.window_pause_role!=='policy' ||
           typeof a.area_id!=='string' || !Array.isArray(a.source_entity_ids) || !a.source_entity_ids.length) continue;
        const key=JSON.stringify([a.area_id,[...a.source_entity_ids].sort()]);
        this._windowIndex66.set(key,this._windowIndex66.has(key)?null:{id,state});
      }
    }
    return originalManaged66.call(this,area).map(entry=>({...entry,
      windowPolicyInfo:this._windowIndex66.get(JSON.stringify([area,
        [...entry.climate.attributes.source_entity_ids].sort()])) || null,
    }));
  };
  // Include configuration-switch-only changes and window timers in rendering.
  const originalSignature66=proto66._controllerSignature;
  proto66._controllerSignature=function() {
    return originalSignature66.call(this)+JSON.stringify(Object.entries(this._hass?.states || {})
      .filter(([id,s])=>s?.attributes?.window_pause_role==='policy' ||
        (id.startsWith('sensor.') && s?.attributes?.window_policy))
      .map(([id,s])=>[id,s.state,s.attributes.window_policy,s.attributes.source_entity_ids]));
  };
  proto66._detail66=function(key,title,content,cls='hem-diagnostics') {
    const opened=this._detailsExpanded66?.has(key)===true;
    return '<details class="'+escape(cls)+'" data-detail-id="'+escape(key)+'" '+(opened?'open':'')+
      '><summary>'+escape(title)+'</summary>'+content+'</details>';
  };
  const originalSummary66=proto66._deviceSummary65;
  proto66._deviceSummary65=function(entry) {
    this._installInteractions66();
    const previous=originalSummary66.call(this,entry);
    const marker=previous.indexOf('<details class="hem-diagnostics">');
    const base=marker<0?previous:previous.slice(0,marker);
    const a=entry.climate.attributes || {}, d=entry.statusInfo?.state?.attributes || {};
    const c=a.controller_status || {}, id=entry.entityId;
    const states=this._hass?.states || {};
    const friendly=entity=>states[entity]?.attributes?.friendly_name || entity;
    const row=(label,value)=>'<div><dt>'+escape(label)+'</dt><dd>'+escape(value)+'</dd></div>';
    const status=d.status_code || c.status || entry.climate.state;
    const reason=d.status_reason_code || c.reason;
    const sources=safeArray(a.source_entity_ids);
    const supply=d.upstream_power_switch || a.upstream_power_switch;
    let diagnostics=row(this._l66('controller'),a.friendly_name || friendly(id));
    diagnostics+=sources.map(entity=>row(this._l66('source'),friendly(entity))).join('');
    diagnostics+=row(this._l66('status'),this._controllerStatusLabel(status));
    if(reason && reason!==status)diagnostics+=row(this._l65('reason'),this._controllerStatusLabel(reason));
    if(supply)diagnostics+=row(this._l65('supply'),friendly(supply));
    const raw=[id,...sources,supply].filter(Boolean).map(escape).join('<br>');
    diagnostics='<dl class="hem-diagnostic-data66">'+diagnostics+'</dl>'+
      this._detail66('raw:'+id,this._l66('rawDetails'),'<code>'+raw+'</code>','hem-technical66');
    const info=entry.windowPolicyInfo, w=d.window_policy || {};
    let toggle='';
    if(info) {
      const on=info.state.state==='on';
      const disabled=!['on','off'].includes(info.state.state) || this._windowSwitchPending66.has(info.id);
      toggle='<div class="hem-window-policy66"><button type="button" role="switch" aria-checked="'+on+
        '" aria-label="'+escape(this._l66('windowSwitch'))+'" title="'+escape(this._l66('windowHelp'))+
        '" data-window-policy-switch="'+escape(info.id)+'" data-window-controller="'+escape(id)+
        '" data-controller-area="'+escape(a.area_id)+'" '+(disabled?'disabled':'')+'>'+
        this._icon('mdi:window-open-variant')+'<span>'+escape(this._l66('windowSwitch'))+'</span><b>'+
        escape(this._controllerStatusLabel(info.state.state))+'</b></button><small>'+escape(this._l66('windowHelp'))+'</small>';
      if(on && w.blocked) {
        const remain=typeof w.closed_since==='number' && typeof w.resume_delay_seconds==='number'
          ? Math.max(0,w.resume_delay_seconds-(Date.now()/1000-w.closed_since)):w.remaining_seconds;
        toggle+='<small class="hem-window-hold66">'+escape(this._controllerStatusLabel(w.status))+
          (typeof remain==='number' && remain>0?' · '+escape(this._format(remain,0))+' s':'')+'</small>';
      }
      toggle+='</div>';
    }
    return base+toggle+this._detail66('diagnostics:'+id,this._l65('details'),diagnostics);
  };
  proto66._roomHumidity66=function(room) {
    const p=room?.environment?.climate_plan || {};
    let rh=p.equipment_plan?.humidity?.measured_rh;
    if(typeof rh!=='number' || !Number.isFinite(rh) || rh<=0 || rh>100) {
      const readings=safeArray(room.readings).filter(r=>r.metric==='humidity' &&
        r.available!==false && typeof r.value==='number' && Number.isFinite(r.value) && r.value>0 && r.value<=100);
      rh=readings.length?readings.reduce((n,r)=>n+r.value,0)/readings.length:null;
    }
    return '<span class="hem-room-humidity66">'+escape(this._t('humidity'))+': <b>'+
      (typeof rh==='number' && Number.isFinite(rh)?escape(this._format(rh))+' %':escape(this._t('missing')))+'</b></span>';
  };
  const originalClimate66=proto66._climatePanel;
  proto66._climatePanel=function(room){this._installInteractions66();return originalClimate66.call(this,room);};
  const originalBlocker66=proto66._outsideBlocker;
  proto66._outsideBlocker=function(reason) {
    if(reason.code==='aqi_scale_unconfigured') {
      return '<span class="reason hem-aqi-setup66">'+this._icon('mdi:information-outline')+
        escape(this._l66('aqiSetup'))+(reason.label?' · '+escape(reason.label):'')+'</span>'+
        '<small class="hem-outside-help66">'+escape(this._l66('aqiHelp'))+'</small>';
    }
    return originalBlocker66.call(this,reason);
  };
  const originalOutside66=proto66._outside;
  proto66._outside=function(outdoor) {
    let html=originalOutside66.call(this,outdoor);
    if(outdoor.status!=='unknown') return html;
    const blockers=safeArray(outdoor.blockers);
    const weather=safeArray(outdoor.weather).some(w=>!!w.condition);
    const missingWeather=blockers.some(b=>['no_weather_data','unavailable_weather'].includes(b.code));
    const aqi=blockers.some(b=>b.code==='aqi_scale_unconfigured');
    const label=missingWeather?this._t('unavailableWeather'):aqi?this._l66('aqiSetup'):
      weather?this._l66('outsideIncomplete'):this._t('missingOutside');
    return html.replace('<div class="outside-title">'+escape(this._t('missingOutside'))+'</div>',
      '<div class="outside-title">'+escape(label)+'</div>');
  };
  const originalStyles66=proto66._styles;
  proto66._styles=function(){return originalStyles66.call(this)+`<style>
    .hem-room-readings66{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}
    .hem-room-readings66>span{display:flex;flex-direction:column;gap:5px;font-size:13px;padding:10px;border-radius:10px;background:var(--secondary-background-color,rgba(127,127,127,.08));overflow-wrap:anywhere}
    .hem-room-readings66 b{font-size:19px;color:var(--primary-text-color)}
    .hem-window-policy66{margin-top:12px}.hem-window-policy66>button{width:100%;display:flex;align-items:center;gap:9px;padding:10px;border:1px solid var(--divider-color);border-radius:10px;background:transparent;color:inherit;font:inherit;text-align:start;cursor:pointer}
    .hem-window-policy66>button[aria-checked=true]{border-color:var(--primary-color,#03a9f4)}
    .hem-window-policy66>button span{flex:1}.hem-window-policy66 small,.hem-outside-help66{display:block;margin-top:5px;color:var(--secondary-text-color);font-size:12px;overflow-wrap:anywhere}
    .hem-diagnostic-data66{margin:8px 0;font-size:12px}.hem-diagnostic-data66>div{margin:7px 0;overflow-wrap:anywhere}
    .hem-diagnostic-data66 dt{color:var(--secondary-text-color)}.hem-diagnostic-data66 dd{margin:3px 0;font-weight:500}
    .hem-technical66{margin-top:10px}.hem-technical66>summary{cursor:pointer;font-size:12px;padding:5px 0}.hem-technical66 code{font-size:11px}
    .hem-outside-help66{flex-basis:100%}.hem-aqi-setup66{white-space:normal}
    @media(max-width:340px){.hem-room-readings66{grid-template-columns:1fr}}
  </style>`;};

/* HEM_CARD66_END */

  /* HEM_CARD68_START: coalesce display work, never physical control. */
  const proto68 = AirQualityAdvisorCard.prototype;
  const managed68 = proto68._managedControllers;
  proto68._managedControllers = function(area) {
    if (this._managedStates68 !== this._hass?.states) {
      this._managedStates68 = this._hass?.states;
      this._managedAreas68 = new Map();
    }
    if (!this._managedAreas68.has(area)) this._managedAreas68.set(area,managed68.call(this,area));
    return this._managedAreas68.get(area);
  };
  const render68 = proto68._render;
  proto68._render = function(force=false) {
    if (!this.isConnected || !this._hass || !this._config) return;
    this._frameForce68 = this._frameForce68 || force;
    if (this._frameHandle68 != null) return;
    this._frameHandle68 = requestAnimationFrame(()=>{
      this._frameHandle68 = null;
      const forced = this._frameForce68; this._frameForce68 = false;
      if (this.isConnected) render68.call(this,forced);
    });
  };
  const disconnect68 = proto68.disconnectedCallback;
  proto68.disconnectedCallback = function() {
    if (this._frameHandle68 != null) cancelAnimationFrame(this._frameHandle68);
    this._frameHandle68 = null; this._frameForce68 = false;
    disconnect68.call(this);
  };
  proto68.connectedCallback = function() {
    if (this._hass) this._render(true);
  };
  /* HEM_CARD68_END */

  /* HEM_COMPACT76_START: display-only; no new listeners or physical services. */
  const proto76 = AirQualityAdvisorCard.prototype;
  const badge76 = (icon,label,tone='normal',title=label) =>
    '<span class="hem-status-pill76 hem-tone-'+escape(tone)+'" title="'+escape(title)+
    '" aria-label="'+escape(title)+'">'+
    '<ha-icon icon="'+escape(icon)+'"></ha-icon>'+
    '<span>'+escape(label)+'</span></span>';

  // The Beta66 delegated disclosure handler saves this key BEFORE the DOM
  // changes. It also handles touch, keyboard, and full state-frame refresh.
  proto76._info76 = function(key,label,details) {
    const opened=this._detailsExpanded66?.has(key) === true;
    return '<details class="hem-context76" data-detail-id="'+escape(key)+'" '+
      (opened?'open':'')+'><summary aria-label="'+escape(label)+'" title="'+escape(label)+'">'+
      '<ha-icon icon="mdi:information-outline"></ha-icon></summary>'+
      '<div class="hem-context-body76">'+details+'</div></details>';
  };
  const originalClimate76=proto76._climatePanel;
  proto76._climatePanel=function(room) {
    const rendered=originalClimate76.call(this,room);
    if (!rendered || !rendered.includes('<div class="hem-room-readings66">')) return rendered;
    const p=room?.environment?.climate_plan || {};
    const lang=this._language();
    const t=CARD65[lang]?.text || CARD65.en.text;
    const w=CARD65[lang]?.words || CARD65.en.words;
    const deviceAttrs=(this._managedControllers(room.area_id) || [])
      .map(entry=>entry.statusInfo?.state?.attributes)
      .find(a=>a && typeof a==='object') || {};
    const profile=p.profile || deviceAttrs.effective_preset || 'home';
    const occupancy=p.occupancy ?? deviceAttrs.room_occupancy;
    const home=p.away ?? deviceAttrs.home_presence_status;
    const sleeping=p.sleeping ?? deviceAttrs.sleeping;
    const chips=[];
    const profileName=this._controllerStatusLabel(profile);
    if (profile && profile!=='none')
      chips.push(badge76('mdi:home-outline',profileName,'neutral'));
    if (home==='away'||home==='unoccupied')
      chips.push(badge76('mdi:home-export-outline',
        this._controllerStatusLabel('away'),'neutral'));
    if (occupancy==='occupied')
      chips.push(badge76('mdi:account-check-outline',w.presence || t.information,'good'));
    else if (occupancy==='unoccupied')
      chips.push(badge76('mdi:account-off-outline',w.presence || t.information,'neutral',
        this._controllerStatusLabel('room_unoccupied')));
    else if (occupancy==='unknown')
      chips.push(badge76('mdi:account-question-outline',w.presence || t.information,'warn',
        this._controllerStatusLabel('room_occupancy_unknown')));
    if (sleeping===true)
      chips.push(badge76('mdi:power-sleep',t.sleep,'warn',
        this._controllerStatusLabel('sleep_room_control_paused')));
    const windows=safeArray(room.windows).filter(win=>typeof win.entity_id==='string');
    if (windows.length) {
      const raw=windows.map(win=>{
        const source=this._hass?.states?.[win.entity_id];
        if (source && ['on','off'].includes(source.state)) return source.state;
        if (source && !['on','off'].includes(source.state)) return 'unknown';
        return typeof win.opened==='boolean' ? (win.opened?'on':'off') : 'unknown';
      });
      const situation=raw.includes('on')?'windowOpen':
        raw.includes('unknown')?'windowUnknown':'windowReady';
      chips.push(badge76(
        situation==='windowReady'?'mdi:window-closed-variant':'mdi:window-open-variant',
        this._l66(situation),situation==='windowReady'?'good':'warn'
      ));
    }
    if (p.status && ['hold','unavailable','unsupported_mode','unsupported_device'].includes(p.status))
      chips.push(badge76('mdi:alert-outline',this._controllerStatusLabel(p.status),'warn'));
    const header='<div class="hem-room-readings66">';
    const open=rendered.indexOf(header),close=rendered.indexOf('</div>',open);
    if (open<0||close<0) return rendered;
    const split=rendered.indexOf('<div class="managed-controllers">',close);
    let top=rendered.slice(0,split<0?rendered.length:split);
    const bottom=split<0?'':rendered.slice(split);
    const explanatory=[...top.matchAll(/<small(?:\s[^>]*)?>[\s\S]*?<\/small>/g)]
      .map(match=>match[0]);
    // The source explanations are preserved inside the info disclosure,
    // not removed from the UI or flattened into a tooltip-only message.
    top=top.replace(/<small(?:\s[^>]*)?>[\s\S]*?<\/small>/g,'');
    top=top.replace('<section class="pid-panel"',
      '<section class="pid-panel hem-compact-climate76"');
    const insertAt=top.indexOf('</div>',top.indexOf(header))+'</div>'.length;
    const information=explanatory.length ? explanatory.join('') :
      '<span>'+escape(this._controllerStatusLabel(p.reason||p.status||'within_target_band'))+'</span>';
    const context='<div class="hem-context-row76" role="group" aria-label="'+escape(t.information)+'">'+
      chips.join('')+this._info76('room-info:'+room.area_id,t.information,information)+'</div>';
    return top.slice(0,insertAt)+context+top.slice(insertAt)+bottom;
  };

  // A mini-data grid with one readable status and clickable explanations.
  // The original summary still builds exact live data, supply/window states,
  // diagnostics, and the existing controlled switch; we only reflow it.
  const originalDevice76=proto76._deviceSummary65;
  proto76._deviceSummary65=function(entry) {
    let html=originalDevice76.call(this,entry);
    const a=entry.climate?.attributes || {};
    const d=entry.statusInfo?.state?.attributes || {};
    const c=a.controller_status || {};
    const t=CARD65[this._language()]?.text || CARD65.en.text;
    const id=entry.entityId, state=d.status_code || c.status || entry.climate.state;
    const label=this._controllerStatusLabel(state);
    const tone=/(paused|hold|unavailable|unknown|failed|error|blocked|inactive|missing)/.test(
      String(state))?'warn':/^(controlling|ready|within_target_band|manual)$/.test(
      String(state))?'good':'neutral';
    const info=[];
    const reason=d.status_reason_code || c.reason;
    if (reason && reason!==state)
      info.push('<div>'+escape(t.reason)+': '+escape(this._controllerStatusLabel(reason))+'</div>');
    // All truncated mini-tile values remain fully readable on touch as well
    // as hover, without repeating them permanently below the measurements.
    const tileDetails=[...html.matchAll(
      /<div title="([^"]*)"><span>[^<]*<\/span><b>[^<]*<\/b><\/div>/g
    )].map(match=>'<div>'+match[1]+'</div>');
    info.push(...tileDetails);
    const supplyId=d.upstream_power_switch || a.upstream_power_switch;
    const supply=this._hass?.states?.[supplyId];
    if(supplyId && supply)
      info.push('<div>'+escape(t.supply)+': '+escape(supply.attributes?.friendly_name || supplyId)+'</div>');
    const toggle=entry.windowPolicyInfo;
    const windowState=d.window_policy || {};
    if (toggle && windowState.status && windowState.status!=='window_closed_ready')
      info.push('<div>'+escape(this._l66('windowSwitch'))+': '+
        escape(this._controllerStatusLabel(windowState.status))+'</div>');
    const badge=badge76(
      tone==='warn'?'mdi:alert-circle-outline':'mdi:check-circle-outline',
      label,tone
    );
    let chips='<div class="hem-device-state76" role="status">'+badge;
    if (supplyId) {
      const text=this._controllerStatusLabel(supply?.state || d.upstream_power_state || 'unavailable');
      chips+=badge76('mdi:power-plug-outline',t.supply,'neutral',t.supply+': '+text);
    }
    if (d.sleep_pause_requested===true)
      chips+=badge76('mdi:power-sleep',t.sleep,'warn');
    if (toggle)
      chips+=badge76('mdi:window-open-variant',
        windowState.blocked===true?this._l66('windowOpen'):this._l66('windowSwitch'),
        windowState.blocked===true?'warn':'neutral');
    chips+=this._info76('device-info:'+id,t.information,
      info.length?info.join(''):'<div>'+escape(label)+'</div>');
    chips+='</div>';
    // The old full-width status and repeated text rows are replaced with
    // compact, accessible pills. The technical/details disclosure is retained.
    const statusNode=/<div class="managed-status">[\s\S]*?<\/div>/;
    if (statusNode.test(html)) html=html.replace(statusNode,chips);
    const control=html.indexOf('<div class="hem-window-policy66">');
    const detail=html.indexOf('<details class="hem-diagnostics"');
    const limit=[control,detail].filter(x=>x>=0).reduce(
      (min,value)=>Math.min(min,value),html.length);
    html=html.slice(0,limit).replace(/<small(?:\s[^>]*)?>[\s\S]*?<\/small>/g,'')+
      html.slice(limit);
    return html;
  };
  const originalController76=proto76._controllerPanel;
  proto76._controllerPanel=function(room) {
    return originalController76.call(this,room)
      .replaceAll('<section class="managed-controller">',
        '<section class="managed-controller hem-compact-device76">');
  };

  const originalStyles76=proto76._styles;
  proto76._styles=function() { return originalStyles76.call(this)+`<style>
    /* Density only: preserve source elements and all existing controls. */
    .card-heading{padding:16px 18px 12px;gap:10px}
    .card-logo{width:38px;height:38px;border-radius:11px}
    .card-logo ha-icon{--mdc-icon-size:23px}
    h2{font-size:22px}
    .content{padding:0 11px 10px}
    .outside{padding:12px;border-radius:14px}
    .outdoor-icon{height:45px;width:45px;flex-basis:45px;border-radius:12px}
    .outdoor-icon ha-icon{--mdc-icon-size:28px}
    .out-metrics{margin-top:9px;padding-top:8px}
    .section-head{margin:14px 3px 9px}
    .rooms-list{gap:9px;margin-top:10px}
    .room{padding:11px;border-radius:13px}
    .room-heading{margin-bottom:8px}
    .metric-grid{gap:6px;grid-template-columns:repeat(auto-fit,minmax(min(100%,105px),1fr))}
    .metric{padding:7px 8px;border-radius:9px}
    .metric-number{font-size:14px}
    .metric-name{font-size:10px;gap:3px}
    .metric-name>ha-icon{--mdc-icon-size:13px;flex-basis:13px}
    .metric-title{-webkit-line-clamp:1}
    .meter{margin-top:7px;height:4px}
    .metric-limit{margin-top:3px}
    .hem-source{font-size:9px;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .hem-compact-climate76{padding:9px;margin:7px 0}
    .hem-compact-climate76>.pid-metrics{display:none}
    .hem-compact-climate76>.pid-title{margin-bottom:5px}
    .hem-room-readings66{gap:6px;margin:6px 0}
    .hem-room-readings66>span{padding:7px 8px;gap:3px;border-radius:8px;font-size:10px}
    .hem-room-readings66 b{font-size:17px;line-height:1.15}
    .hem-context-row76,.hem-device-state76{
      display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin:5px 0
    }
    .hem-status-pill76{
      display:inline-flex;align-items:center;gap:3px;max-width:100%;min-width:0;
      padding:4px 6px;border-radius:999px;font-size:10px;line-height:1.1;
      background:color-mix(in srgb,var(--aqa-muted),transparent 89%);
      color:var(--aqa-text)
    }
    .hem-status-pill76>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:185px}
    .hem-status-pill76 ha-icon{--mdc-icon-size:13px;width:13px;height:13px;flex:0 0 13px}
    .hem-tone-warn{color:var(--aqa-amber);
      background:color-mix(in srgb,var(--aqa-amber),transparent 88%)}
    .hem-tone-good{color:var(--aqa-green);
      background:color-mix(in srgb,var(--aqa-green),transparent 90%)}
    .hem-context76{position:relative;display:inline-flex;flex:0 0 auto;margin-inline-start:auto}
    .hem-context76>summary{cursor:pointer;list-style:none;display:grid;place-items:center;
      width:27px;height:27px;border-radius:8px;border:1px solid var(--aqa-edge);
      color:var(--primary-color,var(--aqa-blue));background:var(--aqa-surface)}
    .hem-context76>summary::-webkit-details-marker{display:none}
    .hem-context76>summary ha-icon{--mdc-icon-size:16px}
    .hem-context76>summary:focus-visible{outline:2px solid var(--aqa-blue);outline-offset:2px}
    .hem-context-body76{position:absolute;z-index:30;inset-inline-end:0;top:31px;
      width:min(300px,76vw);max-height:230px;overflow-y:auto;
      padding:10px 11px;border-radius:10px;border:1px solid var(--aqa-edge);
      background:var(--card-background-color,#23282d);
      box-shadow:0 9px 22px #0006;color:var(--aqa-text);font-size:11px;line-height:1.4}
    .hem-context-body76 small{display:block;font-size:11px;line-height:1.4;margin:3px 0}
    .hem-compact-device76{padding:7px;border-radius:9px}
    .hem-compact-device76 .climate-entity-link{font-size:11px;line-height:1.2;padding:2px}
    .hem-compact-device76 .hem-device-data{
      grid-template-columns:repeat(auto-fit,minmax(min(100%,104px),1fr));
      gap:5px;margin:5px 0 6px
    }
    .hem-compact-device76 .hem-device-data>div{padding:6px 7px;border-radius:7px}
    .hem-compact-device76 .hem-device-data span{
      font-size:10px;line-height:1.15;white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis;overflow-wrap:normal
    }
    .hem-compact-device76 .hem-device-data b{
      font-size:13px;margin-top:3px;line-height:1.2;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;overflow-wrap:normal
    }
    .hem-compact-device76 .managed-method-label{margin-top:6px;gap:3px}
    .hem-compact-device76 .managed-method-label select{padding:6px}
    .hem-window-policy66{margin-top:5px}
    .hem-window-policy66>button{padding:6px 7px;gap:6px;font-size:11px}
    .hem-window-policy66>button ha-icon{--mdc-icon-size:15px}
    .hem-window-policy66>small:not(.hem-window-hold66){display:none}
    .hem-window-policy66 .hem-window-hold66{font-size:10px;margin-top:2px}
    .hem-diagnostics,.hem-calibration{margin-top:6px;padding-top:4px}
    .hem-diagnostics>summary,.hem-calibration>summary{padding:4px 0;font-size:12px}
    .managed-controllers{margin-top:8px;gap:6px;padding-top:7px}
    .managed-controller .hem-context76{margin-inline-start:0}
    @media(max-width:370px) {
      .hem-compact-device76 .hem-device-data{grid-template-columns:repeat(2,minmax(0,1fr))}
      .hem-room-readings66{grid-template-columns:repeat(2,minmax(0,1fr))}
      .hem-status-pill76>span{max-width:100px}
    }
    @media(prefers-reduced-motion:reduce){.hem-context-body76{scroll-behavior:auto}}
  </style>`; };
  /* HEM_COMPACT76_END */

  if (!customElements.get('air-quality-advisor-card')) customElements.define('air-quality-advisor-card',AirQualityAdvisorCard);
  if (!customElements.get('air-quality-advisor-card-editor')) customElements.define('air-quality-advisor-card-editor',AirQualityAdvisorCardEditor);
  // New brand alias; old Lovelace YAML configurations keep working unmodified.
  if (!customElements.get('home-environment-manager-card')) {
    customElements.define('home-environment-manager-card', class extends AirQualityAdvisorCard {});
  }
  if (!customElements.get('home-environment-manager-card-editor')) {
    customElements.define('home-environment-manager-card-editor', class extends AirQualityAdvisorCardEditor {});
  }
  customElements.get('home-environment-manager-card').getConfigElement =
    () => document.createElement('home-environment-manager-card-editor');
  AirQualityAdvisorCard.getConfigElement = () => document.createElement('air-quality-advisor-card-editor');
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === 'air-quality-advisor-card')) {
    window.customCards.push({
      type:'air-quality-advisor-card',
      name:BRAND_TITLE,
      description:'Evidence-grounded room environment, air quality, thermal comfort, ventilation and climate advice. Individual device controls are available.',
      preview:true,
      documentationURL:'https://github.com/Chreece/HA-Air-Quality-Advisor',
      getEntitySuggestion: (hass,entityId) =>
        (hass.states[entityId]?.attributes?.dashboard?.version === 1 ||
         hass.states[entityId]?.attributes?.dashboard_api === 'environment_manager/dashboard')
          ? {config:{type:'custom:air-quality-advisor-card',entity:entityId}}
          : null
    });
  }
  if (!window.customCards.some((card) => card.type === 'home-environment-manager-card')) {
    window.customCards.push({
      type:'home-environment-manager-card',
      name:BRAND_TITLE,
      description:'Indoor air, moisture, thermal comfort, exposure and climate guidance.',
      preview:true,
      documentationURL:'https://github.com/Chreece/HA-Air-Quality-Advisor',
      getEntitySuggestion:(hass,entityId) =>
        (hass.states[entityId]?.attributes?.dashboard?.version === 1 ||
         hass.states[entityId]?.attributes?.dashboard_api === 'environment_manager/dashboard')
          ? {config:{type:'custom:home-environment-manager-card',entity:entityId}}
          : null
    });
  }
})();
