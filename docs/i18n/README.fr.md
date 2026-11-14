<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Accueil Gestionnaire de l'environnement - qualité de l'air, confort, ventilation et contrôle du climat plus intelligents" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Soutenir la Grèce Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <strong>Français</strong> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <a href="README.vi.md">Tiếng Việt</a> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Gestionnaire de l'environnement

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM le logo" width="420">
</p>

<p align="center"><strong>Tout l'environnement de votre maison, en un seul Home Assistant Une carte.</strong></p>

**HEM aide votre maison à comprendre son environnement et à réagir aux besoins réels de chaque pièce.** Il vous apporte votre Home Assistant des capteurs, des données météorologiques, des informations sur l'occupation et des dispositifs climatiques compatibles, afin que vous puissiez surveiller la qualité de l'air, recevoir des conseils utiles sur la ventilation, gérer le confort et automatiser l'équipement que vous choisissez.

Par exemple, HEM Il peut réduire le chauffage pendant que tout le monde est absent, préparer des chambres sélectionnées avant votre retour, utiliser une cible d'humidité différente pendant votre sommeil, ou vous demander d'ouvrir une fenêtre avant d'exécuter un déshumidificateur. **surveiller et recommander**, sans contrôler aucun appareil.

**Reste à la tête.** Chaque pièce a ses propres réglages, chaque appareil supporté a son propre contrôleur, ses modes de fonctionnement, ses cibles et ses limites de sécurité. HEM ne suppose jamais que la sélection d'un dispositif lui donne l'autorisation d'exploiter ce dispositif.

[Découvrez les caractéristiques](#what-can-hem-do) · Les États membres [Voir l'interface](#see-hem-in-action) · Les États membres [Installez HEM](#installation) · Les États membres [Faites votre maison.](#getting-started) · Les États membres [Guide détaillé](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Qu'est-ce qui peut HEM Je ne sais pas.

| Votre situation | Comment ? HEM peut aider |
| --- | --- |
| **La maison est vide.** | Passez aux cibles de l'extérieur, respectez les règles de présence de chaque pièce et évitez d'exécuter inutilement des équipements sélectionnés. |
| **Vous êtes en route pour la maison.** | La presse **Préparez-vous à l'arrivée.** d'utiliser temporairement les cibles de confort à domicile pour les contrôleurs automatiques admissibles, même si tout le monde est encore absent. |
| **Quelqu' un dort.** | Utilisez des cibles de sommeil, réduisez le bruit des ventilateurs ou éteignez les appareils choisis pendant que chaque pièce occupée dort. |
| **Une pièce est humide .** | Comparer son indication d'humidité et de moule avec les cibles, suggérer une ventilation utile ou utiliser un déshumidificateur autorisé en utilisant des outils automatiques ou PID Le contrôle. |
| **C'est chaud et ensoleillé** | Évaluer la température ambiante, la lumière du soleil, le temps et les contacts de fenêtre connectés avant de déplacer les nuances optées. |
| **L'air extérieur est meilleur.** | Recommander la ventilation en utilisant la demande intérieure, la pollution extérieure, la température, l'humidité, le vent et les alertes de pollen ou de météo disponibles. |
| **Un chauffeur ou un TRV cesse de répondre** | Afficher son état de non-disponibilité ou d'attente, conserver son contrôleur configuré et signaler les défaillances du dispositif pris en charge sans supposer qu'une batterie ou un relais s'est rétablie. |

Ce sont des exemples, pas des actions qui HEM Les résultats dépendent de vos capteurs sélectionnés, de l'efficacité de chaque appareil Home Assistant les capacités et vos paramètres d'accès.

<a id="explore-the-features"></a>
## Découvrez les caractéristiques

<a id="a-complete-home-dashboard"></a>
### Un tableau de bord complet à la maison

Les HEM la carte vous donne un aperçu utile sans ouvrir plusieurs intégrations.

- Vérifiez les conditions extérieures, la qualité de l'air et si une ventilation est recommandée.
- Comparer toutes les pièces surveillées en un coup d'œil: température, humidité relative, AQI, PM2.5, indication de moule, lumière et autres mesures prises en charge.
- Élargir les espaces pour des mesures détaillées, des informations sur les fenêtres et les portes, l'état climatique, les contrôleurs actifs, les raisons d'attente et les estimations physiques du bâtiment.
- Voir les histories et les tendances, voir quels capteurs ont contribué à la moyenne et distinguer les lectures manquantes des valeurs mesurées.
- Chambres de groupe par effectif Home Assistant les étages, ou utilisez une simple liste de chambres lorsque vous n'avez pas de plancher.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Différents paramètres pour chaque maison, chaque chambre et chaque appareil

HEM Les politiques partagées sont séparées des décisions locales.

| Niveau des paramètres | Ce que vous pouvez configurer |
| --- | --- |
| **À la maison** | Météo extérieur et sources de pollution, salles surveillées, limites de ventilation mondiales, présence des ménages, préparation de l'arrivée et diffusion des annonces. |
| **La chambre** | Sources de température et d'humidité intérieures, seuils de qualité de l'air, contacts entre fenêtres et portes, comportement de sommeil et d'occupation, objectifs de confort spécifiques à la pièce, ventilation et options d'ombrage. |
| **Dispositif individuel** | Les modes de commande disponibles, automatique/manuel/PID méthode, cibles par profil, capteurs, réglages de ventilateur silencieux, temps d'exploitation minimum, protection de l'alimentation, comportement des fenêtres et notifications d'erreur de l'appareil. |

Tous les trois niveaux sont accessibles à travers des paramètres groupés et recherchables dans la carte. Home Assistant changements de configuration.

<a id="climate-control-and-pid-device-by-device"></a>
### Le contrôle du climat et PID, dispositif par dispositif

HEM peut fonctionner avec compatible Home Assistant **le climat**, **humidificateur** et **le ventilateur** les dispositifs, y compris les appareils de chauffage, de refroidissement, de déshumidification, d'humidification et de circulation de l'air ou de nettoyage de l'air.

Pour chaque **mode de fonctionnement physique pris en charge**, choisissez indépendamment la méthode de contrôle:

| Méthode | Ce que cela signifie |
| --- | --- |
| **Les produits existants** | Laissez fonctionner avec le chemin du contrôleur existant. |
| **Automatise** | Suivez HEMLa demande mesurée, les objectifs et les autorisations basés sur la situation. |
| **PID** | Utilisez un contrôle proportionnel, intégral et dérivé basé sur des rétroactions lorsque l'appareil et la mesure le soutiennent. |
| **Le manuel** | Contrôle par des demandes et des objectifs explicites. |
| **Je suis désolé.** | Gardez ce contrôleur éteint, sous réserve des exigences de protection physique et de rétroaction. |

Par exemple, un climatiseur peut utiliser **PID pour le chauffage** et **Automatique pour le refroidissement**Un déshumidificateur peut avoir son propre PID Les ventilateurs éligibles peuvent utiliser des PID lorsque des retours appropriés et des contrôles spécifiques sont disponibles.

PID est **pas** une suppression universelle: HEM Les options avancées comprennent l'ajustement et l'étalonnage par mode, les réglages suggérés/adaptatifs, le fonctionnement silencieux et les réglages de ventilateurs en scène pris en charge. Vous approuvez les modifications suggérées sauf si vous optez explicitement pour une adaptation automatique limitée.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Comfortable quand on est à la maison, économique quand on est absent

HEM peut choisir entre **Le confort, la maison, l'éloignement, le sommeil et l'environnement** les objectifs en fonction de la situation du ménage, des preuves de la chambre et de vos choix explicites.

- **À la maison et à l'extérieur** Utilisez différents objectifs de chauffage, de refroidissement et d'humidité selon la présence vérifiée à la maison.
- **Présence de la pièce:** Exécutez un dispositif admissible toujours lorsqu'il y a une demande, seulement pendant que sa chambre est occupée, ou seulement pendant que la pièce est vide.
- **Le sommeil:** L'appareil sélectionné peut rester éteint lorsque toutes les chambres occupées dorment.
- **Éco:** Utilisez des objectifs économiques lorsqu'ils sont configurés. Une porte intérieure fermée peut participer à une politique écologique protégée lorsque la pièce est vérifiée vide et que d'autres conditions sont remplies; une porte fermée seule ne prouve pas que la pièce est isolée.
- **Préparation au réveil:** Utilisez une source d'alarme suivante configurée pour laisser le sommeil automatique avant l'alarme et donner aux appareils admissibles le temps de répondre.

Si l'occupation, la disponibilité du dispositif ou toute autre preuve requise sont incertaines, HEM n'assume pas simplement qu'il est sûr de démarrer un dispositif automatique.

<a id="prepare-your-environment-before-you-arrive"></a>
### Préparez votre environnement avant d'arriver

**Préparez-vous à l'arrivée.** C'est une action planifiée pour une résidence confirmée. HEMC'est le dispositif de la maison.

HEM applique temporairement le paramètre configuré **Objectifs à domicile** à l'automatique admissible/PID les contrôleurs afin que les pièces puissent commencer à se réchauffer, refroidir ou régler l'humidité avant votre retour. **uniquement lorsqu'il dispose déjà de l'autorisation de contrôle physique nécessaire**.

La préparation n'est pas une commande pour allumer tout. Les appareils ont toujours besoin d'une demande authentique, de capteurs valides et d'autorisations, et doivent respecter les fenêtres, les temps d'allumage et de déconnexion minimaux et leurs propres protections. Home Assistant le redémarrage ne démarre pas le timer complet.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Conseils sur la ventilation, les fenêtres, les portes et l'ombre

HEM Comparaison **ce qu'une chambre a besoin** avec **si l'air extérieur peut aider**.

- Recommander l'ouverture ou la fermeture des fenêtres en utilisant les mesures actuelles de l'intérieur, de l'humidité extérieure, de la pollution, de la température, du vent, des alertes météorologiques et du contexte de pollen facultatif.
- Utilisez des contacts de fenêtre et de porte sélectionnés pour expliquer les conditions de la pièce et évitez de considérer un contact inconnu comme fermé.
- Vous pouvez également essayer d'ouvrir une fenêtre avant de démarrer un appareil automatique pris en charge, puis continuer le contrôle normal après que la réponse configurée ait attendu si nécessaire.
- Utilisez l'information de la porte pour la prise de conscience des limites de la pièce, les précautions de ventilation et le comportement écologique en option.
- Gérer les obturateurs, les obturateurs et les ombrages optés en utilisant des fenêtres, des températures, des conditions météorologiques, de l'élévation du soleil et des éléments d'illumination optionnels appropriés.

HEM Il ne s'ouvre pas par lui-même simplement parce que l'aération aiderait.

<a id="humidity-mold-indication-and-air-quality"></a>
### Humidité, indication de moule et qualité de l'air

HEM combinent des lectures prises en charge telles que **la température, l'humidité, le CO2, les particules, les COV, l'IQI et l'éclairage** Les mesures disponibles dépendent de ce que votre Home Assistant l'installation est prévue.

Il s'agit **indication de moule** une mesure de calibration et une estimation des conditions d'humidité sur une surface froide à partir de températures ambiantes et extérieures.

**L'indication de moule est une estimation, pas un détecteur de moule ou de spores.** Les données du capteur manquantes ou périmées ne peuvent justifier une nouvelle commande de dispositif basée sur des moules.

<a id="announcements-diagnostics-and-protection"></a>
### Annonces, diagnostics et protection

Vous pouvez envoyer des recommandations et des alertes pertinentes par l'intermédiaire de Home Assistant les notifications, les lecteurs TTS/médias ou **Centre d' annonce**L'IA peut modifier la façon dont un message est formulé; HEMLes décisions de contrôle physique restent déterministes.

HEM inclut également les protections et les diagnostics spécifiques à l'appareil:

- Durée minimale de mise en service et de mise hors service, réglages de temps de fonctionnement maximaux et manipulation de commutateurs de puissance externes supportés.
- Restrictions de fenêtre et d'occupation, manipulation manuelle et vérification de la reconnaissance de commandes natives.
- Rapport d'erreur et de périphérique non disponible, avec un choix de comportement de notification pour chaque périphérique.
- Un chien de surveillance optionnel après la fermeture pour la chauffage suspecté de continuer après un commandement de fermeture, avec une surveillance surveillée et des tentatives de récupération limitées.
- Des raisons claires d'attente, l'état d'exploitation actuel et la disponibilité de la source, afin que vous puissiez enquêter avant d'activer plus de contrôle.

**Les limites de sécurité restent en vigueur même lorsque l'alerte est désactivée.** HEM ne traite jamais une expédition de commande réussie comme une preuve qu'un appareil a réagi physiquement.

<a id="see-hem-in-action"></a>
## Vous voyez ? HEM en action

Ces illustrations en anglais utilisent des échantillons de pièces et des mesures pour démontrer l'interface plutôt que des données en direct d'une maison particulière.

<a id="home-at-a-glance"></a>
### À la maison en un clin d'œil

Obtenez des conseils sur la ventilation, les conditions météorologiques et l'état de chaque chambre surveillée dans une seule carte.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM tableau de bord à domicile avec des conseils de ventilation et des lectures environnementales dans cinq pièces" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Élargir une salle pour les détails complets

Inspecter la qualité de l'air, l'indication de la moisissure, la présence, l'état des fenêtres, les contrôles climatiques et les explications pour chaque décision.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Panneau de bord de salle de bain élargi avec lectures et contrôleurs indépendants de l'appareil" width="760">
</p>

<a id="home-settings"></a>
### Paramètres de la maison

Gérer les sources extérieures, la présence dans toute la maison, les salles surveillées, les limites de ventilation, la préparation et les notifications.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Configuration de la maison avec des groupes de recherche et gestion des sources et des chambres" width="900">
</p>

<a id="room-settings"></a>
### Paramètres de la chambre

Choisissez ce qui compte pour chaque pièce: ses propres capteurs, cibles, occupation, portes, fenêtres, ventilation, ombre et protections.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Groupe HEM réglages de chambre pour les capteurs, les commandes de l'appareil, le sommeil, les fenêtres et la protection" width="760">
</p>

<a id="device-settings"></a>
### Paramètres de l'appareil

réglage d'un dispositif sans modifier les autres, y compris les méthodes de contrôle prises en charge, PID, une opération silencieuse, un calendrier et des signalements de défauts.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Groupe HEM réglages de l'appareil avec contrôle, PID, protection de l'énergie et notifications" width="900">
</p>

<a id="getting-started"></a>
## Je commence

1. **Organisez vos chambres.** Dans Home Assistant, créer ou vérifier vos zones et attribuer les capteurs et les dispositifs appropriés à chacun.
2. **Choisissez ce que vous surveillez.** Ajouter HEM, sélectionnez les chambres qui vous intéressent et vérifiez la température, l'humidité, la fenêtre, la qualité de l'air et les sources d'appareils suggérés.
3. **Configurer les informations partagées.** Sélectionnez les sources météorologiques ou de qualité de l'air disponibles à l'extérieur, les preuves de l'occupation des ménages et les destinations d'annonce que vous souhaitez.
4. **Ajoutez la carte.** Ouvrez un tableau de bord en mode édition et ajoutez le **Gestionnaire de l'environnement** Commencez par la surveillance de la pièce, les lectures et les conseils de ventilation.
5. **Activer le contrôle uniquement lorsqu'il est utile.** Ouvrez une pièce, choisissez un appareil pris en charge, examinez son contrôleur et sélectionnez explicitement PID pour les modes que vous voulez HEM pour opérer.

Vous le faites. **pas** Vous avez besoin d'un appareil intelligent dans chaque pièce. Commencez par les capteurs que vous avez, et introduisez un contrôle automatique un appareil à la fois.

<a id="add-the-card-manually"></a>
### Ajoutez la carte manuellement

L'intégration enregistre normalement sa propre carte Lovelace.Si vous préférez YAML, utilisez:

~~~yaml
type: custom:home-environment-manager-card
~~~

Si votre Home Assistant l'installation a plus d'une HEM le capteur de recommandation, vous devrez peut-être définir le **entité** explicitement:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Pour des instructions étape par étape sur les sources de la chambre, les profils, PID les réglages, les politiques de fenêtre, la préparation, l'étalonnage des moules, l'ombrage solaire et la diffusion des annonces, utilisez le [Guide de configuration détaillé](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Installation

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Boutique communautaire

1. Ouvert **HACS** dans Home Assistant.
2. Ajouter **Le projet de règlement (UE) no 1303/2013 a été adopté par le Conseil.** comme un **référentiel personnalisé** dans le **L'intégration** catégorie si elle n'est pas déjà répertoriée.
3. Trouver **Gestionnaire de l'environnement** et l'installer.
4. Réinitialiser **Home Assistant** pour charger l'intégration.
5. Allez à **Paramètres → Dispositifs et services → Ajouter l'intégration**, à la recherche **Gestionnaire de l'environnement** et compléter l'installation.

<a id="manual-installation"></a>
### Installation manuelle

Une copie du référentiel **personnalisé_components/environment_manager** le dossier dans la correspondance **composants personnalisés** répertoire dans votre Home Assistant configuration, en conservant le nom du répertoire **environnement_gestionnaire**Retournez. Home Assistant et ajouter l'intégration à travers **Paramètres → Dispositifs et services**.

Pour les modifications ultérieures à l'installation, conservez votre HEM l'entrée et les paramètres d'intégration. recharger le tableau de bord dans votre navigateur si l'apparence de la carte ne se renouvelle pas immédiatement.

<a id="common-questions"></a>
## Questions courantes

**Je peux utiliser HEM sans lui donner le contrôle de mes appareils ?**

Oui, la surveillance, les mesures, les conseils sur la ventilation, l'historique et de nombreuses indications environnementales fonctionnent sans permettre l'activation du dispositif.

**- Je veux. HEM contrôler automatiquement chaque appareil qu'il découvre ?**

Non. Vous sélectionnez les appareils physiques que vous souhaitez gérer et choisissez explicitement la méthode de contrôle pour les modes pris en charge.

**Tout appareil prend en charge PID?**

- Je ne sais pas. HEM les aides PID pour **éligibles** les voies de chauffage, de refroidissement, d'humidité ou de contrôle des ventilateurs lorsque l'appareil et les mesures sélectionnées fournissent les capacités et les rétroactions nécessaires. PID Le contrôle.

**Je peux donner des règles différentes à chaque chambre ?**

Oui, les conditions d'occupation, le comportement du sommeil, les sources, les cibles et certaines préférences de sécurité peuvent varier en fonction de la pièce, tandis que chaque appareil physique a ses propres paramètres d'exploitation et de protection.

**On peut HEM Prépare ma maison pendant que je suis absent ?**

- Je sais. **Préparez-vous à l'arrivée.** Il permet temporairement aux contrôleurs automatiques admissibles, déjà autorisés, d'utiliser les cibles d'accueil pendant une période limitée.

**Une recommandation pour la ventilation ouvre-t-elle mes fenêtres ?**

Non. Il explique quand l'aération peut aider. Le mouvement automatique est une fonctionnalité séparée, opt-in pour les nuances ou couvertures éligibles, sous réserve de leurs propres contrôles de sécurité.

**Que faire si un capteur ou un appareil devient indisponible?**

HEM Il distingue les données inconnues des lectures réelles, conserve les informations du contrôleur configurées dans la mesure du possible et expose les raisons d'attente et les diagnostics.

<a id="help-and-troubleshooting"></a>
## Aide et dépannage

Si quelque chose semble mal, vérifiez la salle ou le contrôleur concerné **La raison**, **Diagnostic**La méthode de contrôle de la source et la méthode de contrôle du courant [Guide de configuration détaillé](../../docs/advanced-configuration.md) couvre les états d'attente communs, les politiques de présence, PID l'admissibilité, les fenêtres et le dépannage de la réponse de l'appareil.

Pour un problème reproduisable, [ouvrir une GitHub émission](https://github.com/Chreece/HA-Home-Environment-Manager/issues) avec le comportement attendu, le comportement réel, les paramètres de salle/appareil pertinents et les étapes à reproduire.

Les contributions et améliorations sont les bienvenues. [Contribution.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Appui et licence

Si HEM est utile pour vous, vous pouvez [appui à la Grèce sur le Ko-fi](https://ko-fi.com/chreece).

Distribué dans le cadre du [Licence du MIT](../../LICENSE).
