<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Accueil Gestionnaire de l'environnement - qualité de l'air, confort, ventilation et contrôle du climat plus intelligents" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Soutenir Chreece sur Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <strong>Français</strong> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Home Environment Manager

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="Logo HEM" width="420">
</p>

<p align="center"><strong>L'environnement de toute votre maison, réuni dans une seule carte Home Assistant.</strong></p>

[Exemples par pièce](#what-can-hem-do) · [Fonctionnalités](#explore-the-features) · [Captures d’écran](#see-hem-in-action) · [Installation](#installation) · [Premiers pas](#getting-started) · [Questions fréquentes](#common-questions) · [Dépannage](#help-and-troubleshooting) · [Soutien et licence](#support-and-license)

## En bref

HEM utilise les capteurs que vous avez déjà dans Home Assistant pour afficher la température, l’humidité et la qualité de l’air pièce par pièce. Il compare les conditions intérieures et extérieures pour vous conseiller quand ouvrir ou fermer les fenêtres. Vous pouvez suivre ses conseils ou lui confier les appareils de votre choix (chauffage, climatisation, ventilateurs, déshumidificateurs), avec des consignes différentes selon que vous êtes chez vous, absent ou en train de dormir.

<p align="center">
  <a href="../../docs/images/hem-dashboard-overview.png">
    <img src="../../docs/images/hem-dashboard-overview.png" alt="Tableau de bord HEM : conseils d'aération et relevés de cinq pièces" width="640">
  </a>
</p>

[Guide détaillé](../../docs/advanced-configuration.md) · [Tous les réglages (en anglais)](../../docs/settings-reference.md)

<a id="what-can-hem-do"></a>
## Que peut faire HEM ?

| Situation | Comment HEM peut vous aider |
| --- | --- |
| **Le logement est vide** | Appliquer les consignes d'absence (Away), respecter les règles de présence de chaque pièce et éviter le fonctionnement inutile de certains équipements. |
| **Vous êtes sur le chemin du retour** | Grâce à **Préparer l'arrivée**, utiliser temporairement les consignes Home des régulateurs automatiques autorisés, même avant le retour d'un occupant. |
| **Quelqu'un dort** | Utiliser les consignes Sleep, réduire le bruit des ventilateurs ou maintenir certains appareils éteints lorsque toutes les pièces occupées sont en mode sommeil. |
| **Une pièce est trop humide** | Comparer l'humidité et l'indicateur de risque de moisissure aux objectifs, conseiller l'aération ou piloter un déshumidificateur autorisé, en mode Automatic ou PID. |
| **Il fait chaud et le soleil est fort** | Tenir compte de la température, de l'ensoleillement, de la météo et des contacts de fenêtre avant de déplacer des protections solaires dont vous avez autorisé la commande. |
| **L'air extérieur est plus favorable** | Recommander l'aération selon les besoins intérieurs, la pollution extérieure, la température, l'humidité, le vent et les éventuelles alertes météo ou données polliniques. |
| **Un chauffage ou une vanne thermostatique (TRV) ne répond plus** | Afficher son indisponibilité ou son attente, conserver la configuration du régulateur et signaler les défauts pris en charge, sans supposer que la batterie ou le relais fonctionne de nouveau. |

Ces situations sont des exemples, pas des actions imposées à tous les logements. Les possibilités dépendent des capteurs sélectionnés, des capacités réelles de vos équipements dans Home Assistant et des autorisations que vous accordez.

<a id="explore-the-features"></a>
## Fonctionnalités

<a id="a-complete-home-dashboard"></a>
### Un tableau de bord pour toute la maison

La carte HEM offre une vue d'ensemble sans avoir à ouvrir plusieurs intégrations.

- Consultez les conditions extérieures, la qualité de l'air et les recommandations d'aération.
- Comparez toutes les pièces suivies : température, humidité relative, AQI, PM2.5, indicateur de risque de moisissure, luminosité et autres mesures disponibles.
- Dépliez une pièce pour voir ses mesures, les portes et fenêtres, les appareils, les régulateurs actifs, les motifs d'attente et des estimations de physique du bâtiment.
- Examinez l'historique et les tendances, identifiez les capteurs utilisés dans une moyenne et distinguez les mesures absentes des valeurs réellement relevées.
- Regroupez les pièces par étage tel qu'il est défini dans Home Assistant, ou utilisez une simple liste si vous n'avez pas configuré d'étages.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Des paramètres distincts pour le logement, les pièces et les appareils

HEM sépare les règles communes des décisions propres à chaque pièce et à chaque équipement.

| Niveau | Paramètres disponibles |
| --- | --- |
| **Logement** | Sources météo et de pollution extérieure, pièces surveillées, limites générales d'aération, présence du foyer, préparation de l'arrivée et diffusion des annonces. |
| **Pièce** | Capteurs de température et d'humidité, seuils de qualité de l'air, contacts de fenêtre et de porte, règles de présence et de sommeil, consignes de confort, aération et protections solaires. |
| **Appareil** | Modes réellement disponibles, méthode Automatic/Manual/PID, consignes selon le profil, capteurs, réglages silencieux, durées minimales de fonctionnement, protections électriques, comportement en cas de fenêtre ouverte et alertes de défaut. |

Les réglages du logement, des pièces et des appareils sont regroupés et accessibles par recherche dans la carte. Choisissez **Base**, **Avancé** ou **Expert** pour déterminer les réglages affichés. Base comprend les commandes courantes et la configuration indispensable. Avancé ajoute le réglage manuel des coefficients PID et les ajustements détaillés. Expert ajoute les modèles spécialisés et le réglage de la capacité des appareils. Chaque niveau inclut les précédents. Vous pouvez actualiser les sources disponibles lorsque votre installation Home Assistant évolue. <!-- HEM-I18N:levels -->


<a id="climate-control-and-pid-device-by-device"></a>
### Régulation du climat et PID, appareil par appareil

HEM peut fonctionner avec les appareils Home Assistant compatibles de type **climate**, **humidifier** et **fan** : chauffage, refroidissement, déshumidification, humidification, circulation et purification d'air lorsque ces fonctions sont prises en charge.

Choisissez indépendamment la méthode de commande de **chaque mode physique compatible** :

| Méthode | Fonctionnement |
| --- | --- |
| **Existing** | Laisser l'appareil fonctionner selon sa commande existante. |
| **Automatic** | Suivre les besoins mesurés, les consignes liées à la situation et les autorisations définies dans HEM. |
| **PID** | Utiliser une régulation proportionnelle, intégrale et dérivée, avec retour de mesure, lorsque le matériel le permet. |
| **Manual** | Commander l'appareil au moyen des demandes et consignes manuelles disponibles. |
| **Off** | Maintenir ce régulateur à l'arrêt, sans contourner les exigences de protection et de retour d'état. |

Un climatiseur peut, par exemple, utiliser **PID en chauffage** et **Automatic en refroidissement**. Un déshumidificateur peut disposer de son propre étalonnage PID, de ses consignes et de ses temporisations. Certains ventilateurs peuvent également bénéficier du PID si les mesures et la fonction commandée s'y prêtent.

**Le PID n'est pas un passe-droit.** HEM ne propose que les méthodes effectivement compatibles avec l'appareil, son mode de fonctionnement et les mesures disponibles. Les options avancées comprennent le réglage et l'étalonnage par mode, les ajustements suggérés, le fonctionnement silencieux et les vitesses de ventilation prises en charge. Les changements proposés nécessitent votre accord, sauf si vous activez explicitement une adaptation automatique encadrée.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Du confort à la maison, des économies en votre absence

HEM peut sélectionner les profils **Comfort, Home, Away, Sleep et Eco** selon la situation du foyer, les informations de chaque pièce et vos choix.

- **Home et Away :** Consignes de chauffage, de refroidissement et d'humidité différentes selon la présence confirmée au domicile.
- **Présence dans la pièce :** Faire fonctionner un appareil compatible lorsque cela est nécessaire, uniquement si la pièce est occupée, ou au contraire uniquement si elle est vide.
- **Sleep :** Appliquer des consignes nocturnes et réduire le bruit des ventilateurs. Un appareil peut rester éteint tant que toutes les pièces occupées sont en mode sommeil.
- **Eco :** Utiliser des objectifs plus économes là où ils ont été configurés. Une porte intérieure fermée peut contribuer à une politique Eco sécurisée si la pièce est confirmée vide et si d'autres conditions sont réunies. Une porte fermée ne prouve pas, à elle seule, l'isolement d'une pièce.
- **Préparation du réveil :** Grâce à une source indiquant la prochaine alarme, sortir du mode Sleep avant le réveil pour laisser aux appareils compatibles le temps de réagir.

Lorsque la présence, la disponibilité d'un appareil ou une autre information indispensable est incertaine, HEM ne présume pas qu'un démarrage automatique est sans risque.

<a id="prepare-your-environment-before-you-arrive"></a>
### Préparer votre maison avant votre retour

**Préparer l'arrivée** est une action limitée dans le temps, disponible quand l'absence du foyer (Away) est confirmée. Lancez-la depuis l'en-tête de la carte ou l'appareil Home de HEM.

HEM applique temporairement les **consignes Home** aux régulateurs Automatic/PID éligibles. Certaines pièces peuvent ainsi commencer à chauffer, à refroidir ou à ajuster leur humidité avant votre retour. L'action peut aussi autoriser provisoirement un régulateur normalement réservé aux pièces occupées, **mais seulement s'il dispose déjà de l'autorisation nécessaire pour commander physiquement l'appareil**.

Cette préparation ne met pas tous les équipements en marche. Il faut toujours un besoin réel, des capteurs valides et les autorisations requises. Les conditions liées aux fenêtres, les durées minimales ON/OFF et les protections restent applicables. L'action se termine à l'arrivée d'un occupant, à votre demande ou à la fin du délai. Un redémarrage de Home Assistant ne remet pas ce délai à zéro.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Conseils d'aération, fenêtres, portes et protections solaires

HEM confronte **les besoins de chaque pièce** à **l'intérêt d'utiliser l'air extérieur**.

- Il conseille d'ouvrir ou de fermer les fenêtres selon les mesures intérieures, l'humidité et la pollution extérieures, la température, le vent, les alertes météo et, si disponibles, les données sur les pollens.
- L’indice AQI est facultatif. Si l’échelle du fournisseur n’est pas configurée, HEM signale des données incomplètes ; cela ne suffit pas à bloquer l’aération ou à demander la fermeture d’une fenêtre. Les mesures valides de polluants et les valeurs AQI réellement dangereuses, interprétées avec la bonne échelle, restent prises en compte. <!-- HEM-I18N:aqi -->
- Il utilise les contacts de porte et de fenêtre choisis pour interpréter les conditions des pièces, sans considérer qu'un contact à l'état inconnu est fermé.
- Vous pouvez inclure les portes de balcon ou de terrasse de classe de capteur binaire Home Assistant `door` ou `opening` comme **contacts de fenêtre**. Elles apparaissent dans le sélecteur de fenêtres de la pièce, mais ne sont **jamais présélectionnées**. La surveillance habituelle des portes reste indépendante. <!-- HEM-I18N:balcony -->
- Sur demande, il peut proposer d'essayer d'ouvrir une fenêtre avant de démarrer un appareil automatique compatible, puis reprendre la régulation normale après le délai d'attente configuré si nécessaire.
- Les informations sur les portes servent à mieux connaître les limites entre pièces, à préciser les conseils d'aération et à appliquer des règles Eco facultatives et prudentes.
- Les volets, stores et protections solaires autorisés peuvent être pilotés selon les fenêtres, la température, la météo, la hauteur du soleil et éventuellement la luminosité.

Il n'est pas nécessaire de posséder des fenêtres motorisées pour recevoir des conseils d'aération. **HEM n'ouvre pas les fenêtres de lui-même** au seul motif que l'aération serait utile.

<a id="humidity-mold-indication-and-air-quality"></a>
### Humidité, estimation du risque de moisissure et qualité de l'air

HEM rassemble les mesures prises en charge, notamment **température, humidité, CO₂, particules fines, COV, AQI et luminosité**, pour donner une vision plus complète de chaque pièce. Les valeurs disponibles dépendent des capteurs présents chez vous.

L'**indicateur de risque de moisissure** estime les conditions d'humidité à la surface froide d'une pièce à partir des températures intérieure et extérieure et d'une mesure d'étalonnage. Lorsqu'il est correctement configuré, il peut influer sur la consigne effective d'un régulateur automatique d'humidité compatible.

**Il s'agit d'une estimation, pas d'un détecteur de moisissures ni de spores.** Des données absentes ou trop anciennes ne doivent pas déclencher de nouveaux ordres fondés sur cette estimation.

<a id="announcements-diagnostics-and-protection"></a>
### Annonces, diagnostics et protections

Vous pouvez diffuser conseils et alertes au moyen des notifications Home Assistant, de TTS/lecteurs multimédias ou d'**Announcement Hub**. L'IA peut, en option, rendre un message plus naturel. **Les décisions de commande physique restent déterministes** et ne sont pas confiées à l'IA.

HEM comporte également des protections et diagnostics propres à chaque appareil :

- Durées minimales de marche et d'arrêt, durée maximale de fonctionnement et prise en charge des interrupteurs d'alimentation externes compatibles.
- Restrictions liées aux fenêtres et à la présence, respect des interventions manuelles et vérification des accusés de réception des commandes natives.
- Signalement des erreurs et de l'indisponibilité d'un appareil, avec des options de notification individuelles.
- Pour chaque appareil, HEM peut surveiller si le chauffage, le refroidissement, la déshumidification ou l’humidification semble continuer après l’arrêt. Choisissez la surveillance seule ou autorisez jusqu’à deux nouveaux ordres d’arrêt.
- Motifs d'attente, état de fonctionnement et disponibilité des sources clairement affichés pour faciliter le diagnostic avant d'autoriser de nouvelles commandes.

**Les limites de sécurité restent en vigueur même si une alerte est désactivée.** Le fait qu'un ordre ait été envoyé ne prouve pas que l'appareil l'a réellement exécuté.

<a id="see-hem-in-action"></a>
## HEM en images

Ces illustrations, en anglais, utilisent des pièces et des mesures fictives. Elles montrent l'interface, et non les données réelles d'un logement particulier.

<a id="home-at-a-glance"></a>
### Toute la maison en un coup d'œil

Consultez les recommandations d'aération, les conditions météo et l'état de chaque pièce suivie depuis une seule carte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.png" alt="Tableau de bord HEM : conseils d'aération et relevés de cinq pièces" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Les détails de chaque pièce

Examinez la qualité de l'air, le risque de moisissure, la présence, les fenêtres, les appareils climatiques et les raisons de chaque décision.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.png" alt="Vue détaillée d'une salle de bain avec mesures et régulateurs indépendants" width="760">
</p>

<a id="home-settings"></a>
### Paramètres du logement

Configurez les données extérieures, la présence générale, les pièces, les limites d'aération, la préparation de l'arrivée et les annonces.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="Paramètres généraux HEM avec groupes recherchables et gestion des sources" width="900">
</p>

<a id="room-settings"></a>
### Paramètres d'une pièce

Sélectionnez les capteurs, consignes, règles de présence, portes, fenêtres, ventilation, stores et protections adaptés à chaque pièce.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Paramètres de pièce HEM regroupés : capteurs, appareils, sommeil et fenêtres" width="760">
</p>

<a id="device-settings"></a>
### Paramètres d'un appareil

Réglez chaque appareil séparément : modes de commande, PID, fonctionnement silencieux, temporisations et signalement des erreurs.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Paramètres d'appareil HEM : régulation, PID, protections d'alimentation et notifications" width="900">
</p>

<a id="getting-started"></a>
## Premiers pas

1. **Organisez vos pièces.** Créez ou vérifiez les Zones (Areas) de Home Assistant et affectez à chacune les capteurs et les appareils appropriés.
2. **Choisissez les pièces à suivre.** Ajoutez HEM, sélectionnez vos pièces et vérifiez les sources suggérées pour la température, l'humidité, les fenêtres, la qualité de l'air et les appareils. Les groupes inutilisés peuvent rester vides.
3. **Configurez les informations communes.** Choisissez les données météo et de qualité de l'air extérieur, les indices de présence du foyer et, si vous le souhaitez, les destinataires des annonces.
4. **Ajoutez la carte.** Ouvrez un tableau de bord en mode édition et ajoutez la carte **Home Environment Manager**. Commencez par surveiller les pièces, leurs mesures et les conseils d'aération.
5. **Autorisez uniquement les commandes utiles.** Ouvrez une pièce, choisissez un appareil compatible, vérifiez son régulateur et sélectionnez explicitement Automatic ou PID pour les modes que HEM pourra piloter.

**Vous n'avez pas besoin d'un appareil connecté dans chaque pièce.** Commencez avec vos capteurs existants, puis activez la commande automatique progressivement, un équipement à la fois.

<a id="add-the-card-manually"></a>
### Ajouter la carte manuellement

L'intégration enregistre normalement sa propre carte Lovelace. Si vous préférez utiliser YAML :

~~~yaml
type: custom:home-environment-manager-card
~~~

Si votre installation Home Assistant comporte plusieurs capteurs de recommandation HEM, il faudra peut-être préciser l'**entité (entity)** appropriée :

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Pour approfondir les sources de données, profils, paramètres PID, règles de fenêtres, préparation d'arrivée, étalonnage du risque de moisissure, protections solaires et annonces, consultez le [guide de configuration détaillé](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### Avec HACS (Home Assistant Community Store)

1. Ouvrez **HACS** dans Home Assistant.
2. Ajoutez **https://github.com/Chreece/HA-Home-Environment-Manager** comme **dépôt personnalisé (custom repository)** de catégorie **Integration**, s'il n'apparaît pas déjà.
3. Recherchez **Home Environment Manager** et installez-le.
4. Redémarrez **Home Assistant** pour charger l'intégration.
5. Dans **Paramètres → Appareils et services → Ajouter une intégration**, recherchez **Home Environment Manager** et terminez la configuration.

<a id="manual-installation"></a>
### Installation manuelle

Copiez le dossier **custom_components/environment_manager** du dépôt vers le répertoire **custom_components** correspondant de votre configuration Home Assistant, en conservant le nom de dossier **environment_manager**. Redémarrez Home Assistant, puis ajoutez l'intégration depuis **Paramètres → Appareils et services**.

Lors des mises à jour, conservez l'intégration HEM existante et ses paramètres. Si l'affichage de la carte ne se met pas immédiatement à jour, rechargez la page du tableau de bord dans votre navigateur.

<a id="common-questions"></a>
## Questions fréquentes

**Puis-je utiliser HEM sans lui autoriser le contrôle de mes appareils ?**

Oui. La surveillance, les mesures, les conseils d'aération, l'historique et plusieurs indicateurs environnementaux fonctionnent sans commande d'appareil.

**HEM commande-t-il automatiquement tous les appareils détectés ?**

Non. Vous choisissez les équipements à gérer et autorisez explicitement les méthodes de commande pour les modes compatibles. Les fonctions possibles dépendent toujours des capacités des appareils et des capteurs.

**Tous les appareils prennent-ils en charge PID ?**

Non. PID n'est disponible que pour les modes de **chauffage, refroidissement, humidité ou ventilation appropriés**, avec les capacités et mesures nécessaires. HEM ne crée pas artificiellement un contrôle PID pour un mode incompatible.

**Puis-je appliquer des règles différentes à chaque pièce ?**

Oui. La présence, le sommeil, les sources, les consignes et certains choix de sécurité peuvent varier selon la pièce. Chaque appareil conserve en outre ses paramètres de fonctionnement et de protection.

**HEM peut-il préparer ma maison pendant mon absence ?**

Oui. **Préparer l'arrivée** permet provisoirement aux régulateurs automatiques éligibles et déjà autorisés d'utiliser les consignes Home. Les protections restent actives et l'atteinte des objectifs n'est pas garantie.

**Une recommandation d'aération ouvre-t-elle mes fenêtres ?**

Non. Elle explique quand il peut être utile d'aérer. La commande motorisée est une fonctionnalité distincte et facultative pour les protections solaires ou volets compatibles, soumise à ses propres vérifications de sécurité.

**Que se passe-t-il si un capteur ou un appareil devient indisponible ?**

HEM distingue l'inconnu d'une mesure réelle, conserve autant que possible les informations de configuration et affiche les motifs d'attente et les diagnostics. Toute commande automatique nécessite encore des données récentes, valides et une autorisation adaptée.

<a id="help-and-troubleshooting"></a>
## Aide et dépannage

En cas de problème, vérifiez le **Motif (Reason)**, les **Diagnostics**, la disponibilité des sources et la méthode de commande du régulateur ou de la pièce concernée. Le [guide de configuration détaillé](../../docs/advanced-configuration.md) explique les états d'attente courants, les règles de présence, l'éligibilité PID, les fenêtres et les réponses des appareils.

Si vous pouvez reproduire un défaut, [ouvrez un ticket GitHub](https://github.com/Chreece/HA-Home-Environment-Manager/issues) avec le comportement attendu, celui constaté, les paramètres concernés et les étapes de reproduction. Retirez toute information personnelle des journaux et captures d'écran.

Les contributions et améliorations sont bienvenues. Consultez [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Soutien et licence

Si HEM vous est utile, vous pouvez [soutenir Chreece sur Ko-fi](https://ko-fi.com/chreece).

Distribué sous [licence MIT](../../LICENSE).
