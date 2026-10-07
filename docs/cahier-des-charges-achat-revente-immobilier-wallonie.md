# Cahier des charges — Outil d'aide à la décision pour l'achat-revente de maisons (Wallonie — région de Mons)

| Élément | Valeur |
|---|---|
| Projet | Outil d'analyse d'opérations d'achat-revente de maisons (« achat – rénovation – revente ») |
| Zone | Belgique, Région wallonne — **rayon de 10 km autour de Mons** |
| Type de bien (v1) | **Maisons** uniquement |
| Point d'entrée | **Annonce Immoweb** du bien, **importée par l'utilisateur** (pas de collecte automatique, cf. §4.1) |
| Version | 3.1 (repérage GO / NO-GO, fiche annonce avec photos, estimation détaillée des travaux, collecte automatique horaire) |
| Date | 07/10/2026 |
| Statut | Proposition — à valider |
| Versions produit | **MVP** → **V2** → **V3** (cf. §12) |

> ⚠️ Les taux fiscaux, droits d'enregistrement et obligations légales cités dans ce document sont des **valeurs par défaut indicatives**, à faire valider par un notaire et un comptable/fiscaliste avant toute opération. Ils sont tous **paramétrables** dans l'outil.

---

## 1. Contexte et objectifs

### 1.1 Contexte
L'activité consiste à acheter des maisons sous-évaluées (souvent à rénover) dans la région de Mons, à les rénover, puis à les revendre au prix du marché d'un bien rénové. La rentabilité dépend de quatre estimations :

1. **La valeur de marché actuelle** du bien (en l'état) ;
2. **Le prix d'achat négocié** ;
3. **Le coût réel des travaux** (et leur durée) ;
4. **Le prix de revente** après rénovation.

Spécificités belges qui pèsent fortement sur le modèle :
- **Pas de base publique des transactions à l'adresse** (pas d'équivalent du DVF français) : l'estimation repose sur les annonces (Immoweb), les médianes communales Statbel, le baromètre des notaires et les avis de valeur.
- **Droits d'enregistrement élevés** en Wallonie pour un achat d'investissement (12,5 % par défaut), qui réduisent fortement la marge.
- **Collecte des annonces Immoweb** : dans la **version finale**, les annonces sont récoltées **automatiquement toutes les heures** par un script — par API si un accès est obtenu, sinon par lecture des pages publiques (décision du porteur de projet du 07/10/2026, cf. §4.1). Immoweb ne propose pas d'API publique de lecture des annonces et ses conditions d'utilisation interdisent l'extraction automatisée : ce risque est **assumé par le porteur de projet**, et la collecte est conçue pour rester discrète et s'arrêter au premier refus. Les premières versions fonctionnent par import manuel (page enregistrée, texte collé, saisie).
- **Une offre d'achat écrite acceptée vaut vente** : l'offre doit être émise avec des conditions suspensives et un prix déjà validé par le modèle.

### 1.2 Objectifs métier
| # | Objectif | Critère mesurable |
|---|---|---|
| O1 | Estimer la valeur de marché d'une maison en l'état à partir de son annonce Immoweb | Écart médian ≤ 10 % avec le prix de vente réel (sur les opérations suivies) |
| O2 | Acheter environ **20 % sous le prix du marché** | Prix d'achat ≤ 0,80 × valeur de marché estimée (paramétrable) |
| O3 | Estimer le coût des travaux de rénovation | Écart ≤ 15 % entre budget estimé et coût final (hors imprévus provisionnés) |
| O4 | Estimer le prix de revente après travaux | Écart médian ≤ 8 % avec le prix de revente réel |
| O5 | Garantir une **plus-value nette minimale de 30 000 €** par opération | Aucune offre émise si la plus-value nette prévisionnelle (scénario prudent) < 30 000 € |
| O6 | Dire en quelques secondes si le **prix demandé est dans la norme** (écart au médian Statbel, prix/m² vs comparables, puis score du modèle) | Fiche complète en < 10 s après validation de l'import |
| O7 | Signaler automatiquement les **risques du terrain** (zone inondable, plan de secteur, contraintes géotechniques) | 100 % des biens géocodés vérifiés sur WalOnMap |
| O8 | **Suivre les annonces dans le temps** : baisses de prix, durée en ligne, retrait / vente | Une baisse de prix sur une annonce suivie est détectée et signalée |
| O9 | **Explorer un secteur** (commune ou rayon) : statistiques, graphiques, carte | Vue secteur disponible dès 30 biens en base |

**Succès réel** : l'outil a servi à décider d'une visite, d'une offre ou d'un renoncement.

### 1.3 Définition de la plus-value cible

```
Plus-value nette = Prix de revente
                 − Frais de revente (agence + TVA 21 %, certificats et attestations)
                 − Prix d'achat
                 − Frais d'acquisition (droits d'enregistrement, honoraires et frais du notaire, TVA)
                 − Coût des travaux TVAC (y compris provision pour imprévus)
                 − Frais de portage (acte de crédit, intérêts, précompte immobilier,
                                     assurance incendie, énergie, raccordements)
```

- Elle est calculée **avant impôt** (seuil : **≥ 30 000 €**).
- L'outil affiche aussi la **plus-value après impôt** selon le régime choisi (cf. §6), avec un seuil après impôt optionnel.

---

## 2. Périmètre

### 2.1 Zone géographique
- Rayon de **10 km** autour du centre de Mons (Grand-Place), calculé **à l'adresse exacte** du bien (géocodage), et non à la commune.
- Communes concernées, en tout ou en partie (indicatif) : **Mons** (et ses anciennes communes : Jemappes, Cuesmes, Flénu, Ghlin, Nimy, Havré, Obourg, Hyon, Ciply, Mesvin, Saint-Symphorien, Spiennes, etc.), **Quaregnon, Frameries, Colfontaine, Quévy, Jurbise, Saint-Ghislain** ; en limite : Boussu, Le Rœulx, Estinnes, Lens.
- Le rayon est un paramètre (ex. 15 km pour élargir la recherche de comparables).

### 2.2 Inclus (v1)
- **Maisons** : mitoyennes (2 façades), semi-mitoyennes (3 façades), 4 façades / villas, maisons de rangée.
- Analyse préliminaire à partir de l'**annonce Immoweb**.
- Estimation de la valeur en l'état et après travaux.
- Chiffrage des travaux par postes.
- Modèle financier, décision Go / No-Go et prix d'offre maximum.
- Suivi de l'opération jusqu'à la revente et bilan prévu / réel.

### 2.3 Principes d'architecture et d'usage
- **Usage personnel**, un seul utilisateur (plus éventuellement un apporteur d'affaires) ; pas de diffusion publique ni de revente des données d'annonces.
- **Extensible** : chaque source d'annonces (Immoweb, puis Zimmo, Immovlan) et chaque source géographique (géoportail wallon ; plus tard Flandre et Bruxelles) est un **module séparé**. L'extension aux appartements et à toute la Wallonie ne demande pas de refonte.

### 2.4 Exclus (v1)
- Appartements, immeubles de rapport, division d'une maison en plusieurs logements (permis d'urbanisme spécifique), terrains à bâtir.
- Démolition-reconstruction et rénovations assimilées à du neuf (régime TVA spécifique).
- Ventes publiques (Biddit) — à envisager en v2.
- Gestion locative, locations, biens commerciaux.
- Flandre et Bruxelles (géoportails et fiscalité différents).
- Application mobile native (l'application web responsive suffit).
- Collecte massive d'annonces.

---

## 3. Acteurs et utilisateurs

| Acteur | Rôle |
|---|---|
| Investisseur / porteur de projet | Utilisateur principal : analyse, décide, fait les offres |
| Apporteur d'affaires | Transmet des annonces Immoweb repérées (page sauvegardée ou import via le marque-page, et pas seulement le lien) |
| Entrepreneurs / architecte | Fournissent les devis, valident le chiffrage ; architecte obligatoire si permis d'urbanisme |
| Agent immobilier | Source de biens, avis de valeur à la revente |
| Notaire | Renseignements urbanistiques, compromis, acte authentique, calcul des droits |
| Comptable / fiscaliste | Validation du régime fiscal (hors outil) |
| Banque | Destinataire du dossier de financement exporté |

### 3.1 User stories

| ID | En tant qu'investisseur, je veux… | Afin de… | Version |
|---|---|---|---|
| US1 | importer une annonce (URL, page sauvegardée ou texte collé) et voir ses infos pré-remplies | ne pas tout retaper | MVP |
| US2 | corriger ou compléter les champs extraits sur un écran de vérification | garder des données fiables | MVP |
| US3 | ajouter un bien à la main | analyser un bien hors annonce (agence, bouche-à-oreille) | MVP |
| US4 | voir l'écart entre le prix demandé et le médian Statbel de la commune | savoir si le prix est dans la norme | MVP |
| US5 | voir le prix/m² comparé aux maisons similaires proches | comparer à surface égale | MVP |
| US6 | voir si le bien est en zone inondable, son affectation au plan de secteur et les contraintes géotechniques | éviter un piège | MVP |
| US7 | obtenir le prix d'achat maximum qui garantit 30 000 € de plus-value | savoir jusqu'où négocier | MVP |
| US8 | obtenir un prix estimé par le modèle et un score (sous-coté / dans la norme / surcoté) | repérer les bonnes affaires | V2 |
| US9 | être prévenu quand le prix d'une annonce suivie baisse | négocier au bon moment | V2 |
| US10 | explorer un secteur (commune ou rayon) avec graphiques et carte | connaître le marché local | V2 |
| US11 | comparer 2 à 4 biens côte à côte | trancher entre plusieurs visites | V2 |
| US12 | ajouter mes notes et photos de visite | garder mes impressions avec les chiffres | V3 |
| US13 | voir commerces, écoles et gare à proximité | juger l'attractivité à la revente | V3 |

---

## 4. Processus cible

```
 1. Annonce collectée (toutes les heures) ou importée ──► 1b. Repérage GO / NO-GO ──► 2. Analyse préliminaire (fiche 1 page) ──► 3. Visite + checklist ──► 4. Estimation affinée
                                                                                                 │
 8. Compromis → acte (≤ 4 mois) ◄── 7. Offre écrite (conditions suspensives) ◄── 6. GO/NO-GO ◄── 5. Devis travaux
        │
        ▼
 9. Travaux (suivi budget/planning) ──► 10. Certificats (PEB, électricité) ──► 11. Mise en vente (Immoweb)
        ──► 12. Revente ──► 13. Bilan prévu / réel (recalibre les modèles)
```

> **Règle** : l'extraction propose, l'utilisateur valide. Aucune donnée n'entre en base sans passer par l'**écran de vérification** (champs pré-remplis, champs manquants ou douteux mis en évidence, règles de validation : surface > 0, PEB parmi A++ à G, code postal wallon). Les réimports d'annonces déjà suivies (mise à jour du prix) ne demandent une validation que si un champ autre que le prix a changé.

### 4.1 Acquisition des annonces

**Version finale : collecte automatique toutes les heures.** L'utilisateur n'a plus à charger les annonces : un script récolte les nouvelles annonces de maisons de la zone et met à jour les annonces existantes (prix, retrait) **une fois par heure**. Les modes manuels restent disponibles en secours et pour les biens hors annonce.

| Mode | Description | Effort utilisateur | Version |
|---|---|---|---|
| **M1 — Page enregistrée** | L'utilisateur enregistre la page (Ctrl+S, « HTML ») et la dépose dans l'outil ; les données sont lues dans l'objet `window.classified` de la page | ≈ 20 s par annonce | V1 (réalisé) |
| **M3 — Texte collé** (secours universel) | Texte d'une annonce de n'importe quel site ; extraction par l'API Claude (ou expressions régulières), puis écran de vérification | ≈ 1 min | V1 (réalisé) |
| **M4 — Saisie / import CSV** | Formulaire ou fichier | Variable | V1 (réalisé) |
| **M3b — Autres portails** | Extracteurs Zimmo et Immovlan | ≈ 20 s | V2 |
| **M5 — API / accès officiel** (prioritaire) | Accès aux données par une API sous accord : demande à Immoweb (api@immoweb.be ; son API connue sert aux professionnels pour **publier** des annonces, pas à lire celles du marché) ou contrat avec un fournisseur de données immobilières belge. Si un accès est obtenu, il remplace M7 | Aucun | À demander dès la V2 |
| **M7 — Collecte automatique horaire** (à défaut d'API) | Lecture des pages publiques de résultats et d'annonces Immoweb par un script planifié, selon les règles ci-dessous | Aucun | **Version finale** |

**Fonctionnement de la collecte horaire (M7)**

| ID | Exigence |
|---|---|
| C1 | **Planification** : exécution toutes les heures (cron ou planificateur intégré) sur une machine de l'utilisateur ou un serveur (VPS, serveur domestique) ; une exécution ne démarre pas si la précédente n'est pas terminée |
| C2 | **Recherche** : parcours des pages de résultats d'une recherche « maisons à vendre » sur les codes postaux de la zone, triées par date (les plus récentes d'abord) ; arrêt dès qu'une page ne contient plus que des annonces déjà connues et inchangées |
| C3 | **Lecture détaillée ciblée** : la page de l'annonce n'est lue que pour une **nouvelle** annonce, un **prix modifié** dans les résultats, ou une annonce non relue depuis 24 h ; le reste est mis à jour à partir des résultats seuls |
| C4 | **Retraits** : une annonce absente de toutes les collectes complètes pendant 24 h est marquée retirée (date de retrait = dernière observation) ; une collecte interrompue ne marque rien comme retiré |
| C5 | **Discrétion** : au plus 1 requête toutes les 3 à 5 s, plafond de requêtes par heure (défaut 300), respect du robots.txt, identification honnête du client, **aucun contournement des protections anti-robots** (pas de résolution de captcha, de rotation d'adresses IP ni d'imitation de navigateur) ; arrêt immédiat de l'exécution au premier refus (403, 429, captcha) et nouvel essai à l'heure suivante, avec alerte après 3 échecs consécutifs |
| C6 | **Journal** : pour chaque exécution, nombre d'annonces vues, nouvelles, modifiées, retirées, erreurs et durée ; visible dans la page « Données » |
| C7 | **Après chaque collecte** : recalcul du repérage (module R) pour les annonces nouvelles ou modifiées et notification des nouveaux biens « GO » (e-mail ou Telegram, cf. H6) |
| C8 | **Photos** : seuls les liens des photos sont enregistrés (affichage depuis Immoweb) ; aucune redistribution des photos ni des annonces |
| C9 | **Robustesse** : extracteur isolé et testé sur des pages réelles enregistrées ; si la structure des pages change, la collecte s'arrête proprement et l'erreur est signalée |

> ⚠️ **Risque assumé** : Immoweb interdit l'extraction automatisée dans ses conditions d'utilisation et protège son site par un service anti-robots. La collecte peut être bloquée à tout moment, et Immoweb peut invoquer ses conditions d'utilisation. Le porteur de projet a décidé d'en assumer le risque pour la version finale ; la démarche d'accès officiel (M5) est menée en parallèle pour le supprimer.

**Conséquences sur l'outil :**
- **Historique des prix et durée en ligne** : complets et à l'heure près pour toutes les annonces de la zone dès que la collecte horaire tourne ; avant cela, ils ne couvrent que les annonces réimportées.
- **Couverture du marché** : proche de 100 % des maisons de la zone avec M7 ; avec l'import manuel, l'outil affiche un **taux de couverture** qui abaisse l'indice de confiance s'il est faible.
- **Données personnelles** : noms et coordonnées d'agents ou de vendeurs non conservés ; téléphones et e-mails retirés des descriptions (RGPD).
- **Données brutes** : le JSON d'extraction est conservé pour pouvoir ré-extraire les champs sans relire la page.
- **Écran de vérification** : obligatoire pour les imports manuels ; les annonces collectées automatiquement entrent directement en base et restent signalées « non vérifiées » jusqu'à la consultation de leur fiche.

---

## 5. Exigences fonctionnelles

### 5.0 Module R — Repérage : base de données des biens et statut GO / NO-GO (phase 1)

**Objectif de la phase 1** : trouver rapidement, parmi tous les biens récoltés, ceux dont le prix est **sous la valeur du marché**. Le statut de repérage ne regarde que le positionnement du prix ; la rentabilité complète (travaux, frais, revente) est évaluée ensuite dans la fiche du bien (modules C à F).

**Règle de repérage**

```
Écart = prix/m² demandé (actualisé) du bien / référence − 1
Référence = médiane (par défaut) ou moyenne du prix/m² actualisé des biens similaires (comparables, B13)

GO     si Écart ≤ −seuil              (seuil par défaut : 20 %, cohérent avec l'achat visé à −20 %)
NO-GO  si Écart > −seuil
« Données insuffisantes » si moins de 5 comparables ou surface habitable inconnue
```

La référence n'est ni celle de la rue ni celle de la Belgique : elle est calculée **pour chaque bien** à partir des annonces de la base situées dans un rayon de 3 km (élargi à 5 puis 10 km s'il y a trop peu de biens similaires). Les annonces d'exemple fictives ne servent jamais de référence pour un bien réel. Les comparables sont **ramenés au même état** que le bien (coefficients d'état, B6) pour ne pas comparer une maison à rénover à des maisons rénovées. L'écart au **médian Statbel** de la commune est affiché à côté, à titre de contrôle.

| ID | Exigence | Version |
|---|---|---|
| RP1 | Page **« Base de données »** : liste de tous les biens récoltés, avec la colonne **Repérage : GO / NO-GO / Données insuffisantes**, l'écart (%) et la référence utilisée | V1.1 |
| RP2 | Colonnes : photo miniature, commune, prix, prix/m², surface, terrain, chambres, façades, état, PEB, écart à la référence, écart au médian Statbel, nombre de comparables, baisses de prix, jours en ligne, date de publication, statut en ligne / retirée, décision de rentabilité (si calculée) | V1.1 |
| RP3 | **Paramètres de repérage modifiables à l'écran** : référence (médiane / moyenne), seuil (%), rayon des comparables, nombre minimal de comparables ; le statut se recalcule immédiatement | V1.1 |
| RP4 | **Filtres** : statut de repérage, commune, distance à Mons, prix min / max, prix/m² min / max, surface min / max, terrain min / max, chambres, façades, état, classe PEB, année de construction, écart (%), baisse de prix (oui / non), durée en ligne, publiée depuis (24 h, 7 jours, 30 jours), en ligne / retirée, source | V1.1 |
| RP5 | Tri sur chaque colonne ; filtres mémorisés ; export CSV de la sélection | V1.1 |
| RP6 | Un clic sur un bien ouvre sa **fiche détaillée** (§5.10) | V1.1 |
| RP7 | Recalcul automatique du repérage après chaque collecte (C7) et mise en avant des **nouveaux GO** des dernières 24 h | Version finale |

> Le statut de repérage « GO » signifie « à étudier en priorité », pas « à acheter » : la décision d'offre reste celle du module F (règles R1 à R7, plus-value ≥ 30 000 € dans le scénario prudent).

### 5.1 Module A — Analyse préliminaire à partir de l'annonce Immoweb

**But** : en quelques minutes, à partir d'une annonce Immoweb, savoir si le bien mérite une visite et à quel prix maximum il devient intéressant.

| ID | Exigence | Priorité |
|---|---|---|
| A1 | Création d'une fiche bien par **import de l'annonce par l'utilisateur** (modes M1 à M4, §4.1) ; le lien / code Immoweb sert d'identifiant et évite les doublons | Must |
| A2 | Aucune requête automatique vers Immoweb ; en cas d'échec d'extraction, bascule vers la saisie assistée avec les champs déjà reconnus pré-remplis | Must |
| A3 | Contrôle de complétude : liste des champs manquants à demander à l'agence (PEB, revenu cadastral, contrôle électrique, permis…) | Must |
| A4 | Géocodage de l'adresse et **vérification du rayon de 10 km** (si l'adresse exacte est masquée : localisation approximative signalée) | Must |
| A5 | Historique de l'annonce : date de publication, **baisses de prix**, remises en ligne (signaux de négociation), à partir des réimports successifs | Should |
| A6 | Génération automatique de la **fiche d'analyse préliminaire** (cf. ci-dessous) | Must |
| A7 | Liste de questions et de points à vérifier lors de la visite, déduite de l'annonce | Should |
| A8 | Nouvelles annonces repérées via les **alertes e-mail Immoweb** de l'utilisateur (critères : zone, budget, état « à rénover », PEB E/F/G), puis importées | Could |
| A9 | **Liste de tournée hebdomadaire** : annonces suivies non revues depuis 7 jours, avec liens, pour réimport | Should |

**Données de l'annonce Immoweb exploitées :**

| Donnée | Usage dans l'analyse |
|---|---|
| Prix demandé, date de publication | Écart avec la valeur estimée, marge de négociation |
| Localisation (commune, code postal, adresse si publiée) | Rayon 10 km, médianes communales, comparables |
| Type de maison, nombre de façades | Sélection des comparables, coût d'isolation |
| Surface habitable, surface du terrain | Prix au m², chiffrage des travaux |
| Nombre de chambres, salles de bain, WC | Attractivité à la revente, travaux sanitaires |
| Année de construction | Risques (amiante si avant 2001, électricité ancienne, plomb) |
| **État du bâtiment** (À restaurer / À rénover / À rafraîchir / Bon / Fraîchement rénové / Comme neuf) | Niveau de rénovation par défaut |
| **Classe PEB** et consommation (kWh/m²/an), n° de certificat | Travaux énergétiques, gain de valeur après travaux |
| Type de chauffage, double vitrage, panneaux solaires | Postes de travaux |
| **Revenu cadastral** | Précompte immobilier (portage) |
| Garage / parking, jardin, terrasse, orientation | Ajustements de valeur |
| Zone inondable, affectation au plan de secteur, permis délivré, infraction urbanistique, droit de préemption | Risques bloquants |
| Photos et description | Indices sur l'état (toiture, humidité, cuisine, salle de bain) |

**Contenu de la fiche d'analyse préliminaire (1 page) :**
1. Résumé du bien (données clés + carte).
2. Fourchette de **valeur en l'état** (basse / centrale / haute) et indice de confiance.
3. **Niveau de rénovation présumé** et budget travaux par ratio.
4. **Valeur après travaux** estimée.
5. **Prix d'achat cible (−20 %)** et **prix d'achat maximum** (marge ≥ 30 000 €).
6. Écart entre prix demandé et prix maximum → statut : *À visiter* / *À surveiller (attendre une baisse)* / *À écarter*.
7. Alertes de risques et questions pour la visite.

### 5.2 Module B — Estimation de la valeur de marché en l'état

En l'absence de base publique de transactions à l'adresse, l'estimation **croise plusieurs sources** :

| ID | Exigence | Priorité |
|---|---|---|
| B1 | **Médianes Statbel** par commune, par type de maison (2-3 façades / 4 façades), dernière année et tendance, **importées automatiquement par l'application** (au démarrage, au plus tous les 30 jours) depuis l'API Open Data Wallonie-Bruxelles (jeu WalStat « Prix de l'immobilier résidentiel », source Statbel) ou, à défaut, le fichier open data le plus récent de Statbel ; l'indice d'évolution des prix de la zone est recalculé à chaque mise à jour ; aucun import par l'utilisateur | Must |
| B2 | **Comparables d'annonces** : maisons de même type et même état dans un rayon de 2 km (élargi à 5 puis 10 km si moins de 8 comparables), surface ± 25 %, annonces actives et vendues récemment | Must |
| B3 | Correction prix demandé → prix de vente (marge de négociation moyenne, défaut −5 %, paramétrable par commune) | Must |
| B4 | Exclusion des valeurs aberrantes (méthode IQR) ; calcul de la médiane €/m², des quartiles et d'un **indice de confiance** | Must |
| B5 | Intégration du **baromètre des notaires** (évolution des prix par province / arrondissement) pour l'actualisation | Should |
| B6 | Ajustements paramétrables (en % ou €) : état, PEB, nombre de façades, terrain, garage, jardin/orientation, nuisances (axe routier, voie ferrée), environnement (rue, quartier) | Must |
| B7 | Saisie d'**avis de valeur externes** (agents, géomètre-expert) et écart avec l'estimation | Should |
| B8 | Résultat : **valeur basse / centrale / haute** avec justification (liste des comparables, carte, sources) | Must |

```
Valeur en l'état = Médiane €/m² des comparables de même état (corrigée de la négociation)
                   × Surface habitable × (1 + Σ ajustements)
```
> Contrôle de cohérence : la valeur est comparée à la médiane Statbel de la commune ; un écart > 30 % déclenche une alerte.

**Trois indicateurs de prix, du plus simple au plus fin.** Chacun n'est affiché que si ses conditions de fiabilité sont remplies.

| Indicateur | Calcul | Condition | Version |
|---|---|---|---|
| Écart au médian communal | (prix demandé − médian Statbel) / médian Statbel, même type de maison | Médian Statbel disponible pour la commune | MVP |
| Prix/m² vs comparables | Médiane du prix/m² actualisé des comparables (§5.2.1, B13) | Au moins 5 comparables | MVP |
| Résidu du modèle hédonique | (prix demandé − prix prédit) / prix prédit | Au moins 30 maisons dans le secteur | V2 |

| ID | Exigence | Priorité |
|---|---|---|
| B19 | Rattachement de chaque bien à sa commune par le **code NIS** (clé de Statbel), à partir des coordonnées ou du code postal (un code postal peut couvrir une partie de commune seulement) | Must |
| B20 | **Modèle hédonique** (V2) : régression linéaire multiple sur le **logarithme du prix**, pour des coefficients lisibles en % (« une façade de plus = +X % ») et un poids limité des biens très chers : `log(prix) = β0 + β1·surface + β2·log(terrain) + β3·façades + β4·PEB + β5·état + β6·année + ε`. PEB et état en variables catégorielles ; commune en effet fixe si le secteur couvre plusieurs communes. On démarre avec la surface seule, puis on ajoute une variable à la fois, avec au moins 10 biens par variable | Should (V2) |
| B21 | Validation croisée à 5 plis : erreur moyenne absolue (%) et R² affichés à côté de chaque estimation ; **intervalle de prédiction à 80 %** affiché avec le prix estimé ; estimations **versionnées** pour comparer les modèles entre eux | Should (V2) |
| B22 | **Score** à partir du résidu : < −10 % « sous-coté », entre −10 % et +10 % « dans la norme », > +10 % « surcoté » ; seuils recalibrés quand l'erreur réelle du modèle est connue | Should (V2) |
| B23 | **Marge de négociation indicative par commune** : écart moyen entre les prix demandés en base et les prix de vente Statbel ; l'estimation n'est jamais présentée comme une valeur vénale | Should |

> Pour l'investisseur, le modèle hédonique estime la **valeur en l'état** (avec l'état réel du bien) et la **valeur après travaux** (en remplaçant l'état et la classe PEB par ceux visés), ce qui alimente directement les modules C et E.

#### 5.2.1 Base de données des annonces de maisons (Immoweb)

Pour pallier l'absence de prix de transaction publics, une **base interne** enregistre dans le temps toutes les annonces de maisons à vendre de la zone. Implémentation de référence : [`base_annonces/`](../base_annonces/README.md) (SQLite + Python).

**Données enregistrées par annonce :**

| Donnée | Détail |
|---|---|
| Identifiant et lien | Code Immoweb, URL |
| Adresse | Rue, numéro, code postal, commune, coordonnées, indicateur « adresse exacte publiée », distance à Mons |
| Caractéristiques | Surface habitable, surface du terrain, chambres, salles de bain, façades, année de construction, état du bâtiment |
| PEB | Lettre (A++ à G) et consommation (kWh/m²/an) |
| Description | Texte de l'annonce |
| Dates | Date de publication, première et dernière observation, date de retrait |
| **Historique des prix** | Une ligne à chaque changement du prix demandé (date, prix) |

**Indicateurs calculés :**

| Indicateur | Calcul |
|---|---|
| Prix actuel, prix initial | Dernier et premier prix de l'historique |
| Nombre de baisses, variation totale (%) | À partir de l'historique des prix |
| En ligne / retirée | Retirée si marquée comme telle ou non revue depuis 14 jours (paramétrable) |
| Durée en ligne (jours) | (date de retrait ou aujourd'hui) − date de publication |
| Prix/m² | Prix actuel / surface habitable |
| **Prix actualisé** | Si le prix a été observé pour la dernière fois **il y a un an ou plus** : prix × indice actuel / indice du trimestre de cette observation (indice des prix des maisons, Statbel, par province ou arrondissement). Une annonce toujours en ligne n'est pas actualisée : son prix est déjà un prix actuel, même si elle a été publiée il y a plus d'un an |
| Prix/m² actualisé | Prix actualisé / surface habitable |

| ID | Exigence | Priorité |
|---|---|---|
| B9 | Enregistrement de chaque consultation d'annonce comme une **observation datée** (création ou mise à jour de l'annonce, historique du prix si changement) | Must |
| B10 | Alimentation exclusivement par les modes d'import utilisateur M1 à M4 (ou M5 si accord) ; aucune collecte automatique | Must |
| B11 | Mise à jour du statut en ligne / retirée et de la durée en ligne (annonce non revue depuis 14 jours ou introuvable lors de la tournée = retirée) | Must |
| B12 | Actualisation des prix de plus d'un an par un indice de prix régional importé | Must |
| B13 | **Recherche de comparables** : maisons dans un rayon de 3 km, surface ± 25 %, chambres ± 1, terrain ± 50 %, même nombre de façades et même état, avec élargissement progressif (5 km, puis 10 km, puis critères assouplis) jusqu'à au moins 8 comparables | Must |
| B14 | **Statistiques des comparables** : nombre, moyenne, médiane, minimum, maximum, quartiles du prix actualisé, du prix/m² actualisé et de la durée en ligne ; ventilation par **état** (valeur en l'état et valeur après rénovation) et par **classe PEB** | Must |
| B15 | **Positionnement du bien ciblé** : écart à la médiane (%), percentile, valeur au prix/m² médian ; comparaison avec la médiane des comparables **sans baisse de prix** et des annonces **retirées** (les plus proches des prix réellement acceptés) | Must |
| B16 | Signal « prix trop élevé » : une annonce dont le prix a baissé, ou qui reste en ligne plus longtemps que la médiane de ses comparables, est probablement surévaluée ; ces annonces sont signalées et pèsent moins dans l'estimation | Should |
| B17 | Export CSV de la base et des comparables | Should |
| B18 | Affichage du **taux de couverture** de la base et prise en compte dans l'indice de confiance | Should |

### 5.3 Module C — Prix d'achat cible et offre

| ID | Exigence | Priorité |
|---|---|---|
| C1 | Prix cible = valeur en l'état × (1 − décote cible), **décote cible par défaut = 20 %** | Must |
| C2 | Calcul du **prix d'achat maximum** garantissant la marge minimale (formule ci-dessous) | Must |
| C3 | Prix d'offre recommandé = min(prix cible, prix maximum) | Must |
| C4 | Argumentaire de négociation : travaux chiffrés, classe PEB, durée de mise en vente, baisses de prix passées, comparables | Should |
| C5 | Génération d'une **offre d'achat écrite** comprenant obligatoirement : durée de validité, **conditions suspensives** (obtention du crédit, renseignements urbanistiques conformes, absence d'infraction urbanistique, résultat de l'attestation de sol), et rappel qu'une offre acceptée vaut vente | Must |
| C6 | Rappel des échéances : acompte (généralement 10 %) au compromis, acte authentique et paiement des droits d'enregistrement dans les **4 mois** | Should |

**Prix d'achat maximum** :

```
Prix_max = (Revente − Frais_revente − Travaux_total − Portage − Marge_min − Frais_fixes_notaire)
           / (1 + taux_droits_enregistrement + taux_frais_variables_notaire)
```
avec `Marge_min = 30 000 €`.

> Règle : si `Prix_max < Prix_cible`, c'est `Prix_max` qui borne l'offre. En Wallonie, avec 12,5 % de droits d'enregistrement, **le prix maximum est souvent plus contraignant que la règle des −20 %** (cf. exemple §8).

### 5.4 Module D — Estimation du coût des travaux

| ID | Exigence | Priorité |
|---|---|---|
| D1 | Checklist de visite structurée : stabilité / fissures, toiture et charpente, humidité (ascensionnelle, infiltrations, condensation), façades et rejointoyage, châssis, électricité, plomberie, chauffage (mazout / gaz / électrique, citerne), isolation (toit, murs, sol), ventilation, égouttage, cuisine, salles d'eau, finitions, abords | Must |
| D2 | Pré-chiffrage depuis l'annonce : niveau de rénovation déduit de l'**état Immoweb**, de la **classe PEB** et de l'**année de construction** | Must |
| D3 | Chiffrage par **postes** avec un référentiel de prix unitaires (€/m², €/unité), TVAC, calibré sur le Hainaut | Must |
| D4 | Niveaux de rénovation (ratios indicatifs TVAC, à calibrer avec les devis locaux) : | Must |
|    | — Rafraîchissement (peinture, sols, petites remises en état) : 250 – 500 €/m² | |
|    | — Rénovation moyenne (cuisine, salle de bain, électricité, chauffage partiel, isolation toiture) : 600 – 1 100 €/m² | |
|    | — Rénovation lourde (toiture, châssis, électricité et chauffage complets, isolation, humidité) : 1 100 – 1 800 €/m² | |
| D5 | Gestion de la **TVA** : 6 % sur la rénovation de logements de plus de 10 ans lorsque les conditions sont remplies, 21 % sinon (paramètre par poste, à vérifier selon la qualité du maître d'ouvrage) | Must |
| D6 | Remplacement progressif des estimations par les **devis** (suivi : estimé / devis / facturé) | Must |
| D7 | Provision pour **imprévus** : 10 % (rafraîchissement) à 20 % (rénovation lourde, bâti ancien du Borinage) | Must |
| D8 | **Simulation PEB** : classe actuelle → classe visée après travaux (isolation toiture, murs, châssis, chauffage, pompe à chaleur, photovoltaïque) et impact sur la valeur de revente | Must |
| D9 | Estimation de la **durée des travaux** (planning par poste) alimentant le portage | Must |
| D10 | Signalement des formalités : **permis d'urbanisme** (CoDT) si modification de façade, de volume, de toiture visible ou du nombre de logements ; recours obligatoire à un architecte dans ce cas | Should |
| D11 | Postes post-travaux obligatoires : nouveau **contrôle de l'installation électrique** (RGIE), nouveau **certificat PEB**, **DIU** (dossier d'intervention ultérieure) | Must |
| D12 | **Modèle de régression linéaire « annonce »** : coût total des travaux estimé à partir des seules données Immoweb (surface, état, saut de classes PEB, façades, année, gamme), avec intervalle de prédiction 80 % | Must |
| D13 | **Modèles de régression par poste** (après visite) : coût = coût fixe + quantité × prix unitaire, ajusté selon la gamme et le bâti d'avant 1945 ; ré-estimés après chaque chantier clôturé | Should |
| D14 | La borne haute (P90) de l'intervalle de prédiction remplace le pourcentage d'imprévus fixe dans le **scénario prudent** dès que le modèle dispose d'au moins 30 chantiers réels | Should |

**Régression linéaire sur les travaux** — implémentation de référence dans [`immo/regression_travaux.py`](../immo/regression_travaux.py) :

```
Modèle annonce : Coût = β0 + β1·surface + β2·[À rénover] + β3·[À restaurer] + β4·saut_classes_PEB
                      + β5·façades + β6·[avant 1945] + β7·[éco] + β8·[premium] + ε
Modèle poste   : Coût_poste = coût_fixe + quantité × (prix_unitaire + ajustements gamme / bâti ancien) + ε
```
Indicateurs suivis : R², R² ajusté, erreur type et t de chaque coefficient, MAE et MAPE en validation croisée (5 plis). Les données d'exemple fournies sont **synthétiques** et doivent être remplacées par les devis et factures réels.

**Classes PEB en Wallonie (consommation spécifique, kWh/m²/an) — pour la simulation :**

| A++ | A+ | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|---|
| ≤ 0 | 0 – 45 | 45 – 85 | 85 – 170 | 170 – 255 | 255 – 340 | 340 – 425 | 425 – 510 | > 510 |

> La réglementation wallonne sur la performance énergétique des logements existants évolue (objectifs de rénovation, éventuelles obligations à l'acquisition) : l'outil doit permettre d'ajouter une règle « obligation de rénovation » paramétrable.

#### 5.4.1 Onglet « Estimation des travaux » (configurable par l'utilisateur)

L'utilisateur compose lui-même le chantier : il **coche les postes de travaux**, ajuste les **quantités** et le **niveau de prix**, et le total alimente directement l'étude de rentabilité. Le pré-chiffrage par ratios (D2, D4) ne sert plus que de point de départ quand aucun poste n'est encore choisi.

| ID | Exigence | Version |
|---|---|---|
| D15 | **Catalogue de postes** de travaux (Annexe A) : catégorie, libellé, unité (m², ml, m³, unité, forfait), prix unitaire **bas / moyen / haut HTVA**, taux de TVA applicable, source et date de mise à jour | V1.1 |
| D16 | **Sélection** des postes par cases à cocher, regroupés par catégorie (démolition, toiture, façade et humidité, menuiseries extérieures, isolation, plafonnage et cloisons, sols, finitions, électricité, plomberie et chauffage, ventilation, sanitaires et cuisine, désamiantage) ; possibilité d'**ajouter un poste libre** (libellé, unité, prix) | V1.1 |
| D17 | **Quantités proposées** à partir de l'annonce (règles de l'Annexe A, ex. surface des murs et plafonds ≈ 3,5 × surface habitable), toujours modifiables ; les postes à mesurer sur place sont signalés « à mesurer » | V1.1 |
| D18 | **Niveau de prix** par poste (bas / moyen / haut) ou **prix unitaire saisi** (ex. prix d'un devis) ; un poste dont le prix vient d'un devis est marqué « devis » | V1.1 |
| D19 | **Calcul** : sous-total par poste et par catégorie, total HTVA, TVA (6 % pour la rénovation d'un logement de plus de 10 ans lorsque les conditions sont remplies, 21 % sinon — **21 % pour les chaudières gaz et mazout depuis le 29/07/2025**), total TVAC, imprévus (%), total général | V1.1 |
| D20 | **Durée estimée** du chantier (somme indicative par poste, modifiable) reprise dans le portage | V1.1 |
| D21 | Le **total TVAC** et la durée remplacent automatiquement les hypothèses « travaux » et « durée » du modèle financier ; la plus-value, le prix d'achat maximum et la décision se recalculent immédiatement | V1.1 |
| D22 | **Modèles de chantier** pré-remplis (rafraîchissement, rénovation moyenne, rénovation lourde, rénovation énergétique) à appliquer puis ajuster ; enregistrement de la configuration propre à chaque bien | V1.1 |
| D23 | Catalogue **modifiable** dans l'outil (prix, nouveaux postes) ; les prix réels des devis et factures des opérations servent à le recalibrer (G5) | V2 |

#### 5.4.2 Étude des prix (synthèse)

L'Annexe A rassemble les prix unitaires observés en Belgique en 2025-2026 pour chaque poste (fourchettes HTVA, pose comprise sauf mention). Points d'attention :
- Les sources disponibles sont surtout des **guides de prix de plateformes de mise en relation** (TrustUp, Bobex, guides rénovation) : les fourchettes sont larges et doivent être **recalibrées avec au moins 3 devis locaux** (Mons – Borinage) avant la première opération.
- Le niveau « moyen » retenu par défaut est le milieu de la fourchette.
- Les prix du bâti ancien du Borinage (murs épais, humidité, amiante) se situent plutôt dans le haut des fourchettes : les imprévus restent provisionnés à part (D7).

### 5.5 Module E — Estimation du prix de revente après travaux

| ID | Exigence | Priorité |
|---|---|---|
| E1 | Comparables Immoweb en état « **Fraîchement rénové / Comme neuf / Excellent** », même secteur, même type de maison | Must |
| E2 | Ajustement selon la **classe PEB visée** (une maison passant de F/G à C se revend nettement mieux) | Must |
| E3 | Plafonnement : alerte si la valeur après travaux dépasse le **90e percentile** du secteur (risque de sur-rénovation, notamment dans les quartiers ouvriers du Borinage) | Must |
| E4 | Estimation du délai de revente (durée moyenne de mise en ligne des annonces comparables) | Should |
| E5 | Trois scénarios : **prudent** (revente −5 %, travaux +20 %, +3 mois), **central**, **optimiste** | Must |

### 5.6 Module F — Modèle financier et décision

| ID | Exigence | Priorité |
|---|---|---|
| F1 | Bilan d'opération complet (formule §1.3) pour les 3 scénarios | Must |
| F2 | **Frais d'acquisition** selon le régime : droits d'enregistrement (cf. §6) + honoraires du notaire (barème légal dégressif) + frais administratifs + TVA 21 % sur honoraires et frais | Must |
| F3 | **Frais de crédit** : acte de crédit hypothécaire (droit d'inscription hypothécaire, honoraires, frais), ou mandat hypothécaire ; intérêts, assurance solde restant dû, frais de dossier | Must |
| F4 | Portage : **précompte immobilier** au prorata (calculé sur le revenu cadastral indexé et les centimes additionnels de la commune), assurance incendie, énergie, eau, abonnements | Must |
| F5 | Frais de revente : commission d'agence (défaut 3 % + TVA 21 %), certificat PEB, contrôle électrique, attestation de sol, renseignements urbanistiques, mainlevée hypothécaire | Must |
| F6 | Indicateurs : plus-value nette, marge sur prix de revient (%), TRI, rendement sur fonds propres, durée totale | Must |
| F7 | Calcul fiscal (cf. §6) et plus-value après impôt | Should |
| F8 | **Décision automatique** (cf. §5.7) avec justification | Must |
| F9 | Analyse de sensibilité : ±10 % travaux, ±5 % prix de revente, +3/+6 mois, variation du taux d'intérêt | Should |
| F10 | Export PDF « dossier banque » (annonce, estimation, travaux, bilan, planning) | Should |

### 5.7 Règles de décision Go / No-Go

| Règle | Condition | Résultat |
|---|---|---|
| R1 | Plus-value nette (scénario **prudent**) ≥ 30 000 € | Obligatoire pour GO |
| R2 | Prix d'achat ≤ 80 % de la valeur en l'état (tolérance paramétrable) | Obligatoire pour GO |
| R3 | Marge nette (central) ≥ 15 % du prix de revient total | Recommandé |
| R4 | Indice de confiance de l'estimation ≥ « moyen » | Sinon : GO sous réserve d'un avis de valeur externe |
| R5 | Aucun risque bloquant (cf. §7) : infraction urbanistique non régularisable, problème de stabilité, puits de mine / contrainte géotechnique majeure, zone d'aléa d'inondation élevé, pollution du sol | Obligatoire |
| R6 | Bien situé dans le rayon de 10 km | Obligatoire |
| R7 | Durée totale d'opération ≤ 12 mois (paramétrable) | Recommandé |

**Statuts** : `GO` · `GO SOUS CONDITIONS` (règles obligatoires respectées, recommandées partiellement) · `NO-GO`.

### 5.8 Module G — Suivi d'opération et retour d'expérience

| ID | Exigence | Priorité |
|---|---|---|
| G1 | Tableau de bord (pipeline : annonce repérée, analysée, visitée, offre, compromis, acte, travaux, en vente, vendu) | Must |
| G2 | Suivi budgétaire du chantier (estimé / engagé / payé) avec alerte de dépassement > 10 % | Must |
| G3 | Suivi des échéances légales : acte dans les 4 mois, mise en conformité électrique (18 mois si non conforme à l'achat), certificats avant la mise en vente | Must |
| G4 | Bilan final prévu / réel par poste | Must |
| G5 | Recalibrage des référentiels (prix travaux, marge de négociation par commune, ajustements de valeur) à partir des opérations clôturées | Could |

### 5.9 Module H — Exploration de secteur, comparateur et confort

| ID | Exigence | Version |
|---|---|---|
| H1 | **Liste des biens** filtrable et triable (commune, prix, prix/m², score, PEB, état, statut actif / retiré / vendu) | MVP |
| H2 | **Fiche du bien** : prix, prix/m², écart au médian communal, comparables, risques, historique des prix, mini-carte, prix d'achat maximum (détail : §5.10) | MVP |
| H3 | **Écran « Données »** : état des mises à jour automatiques (date, source, erreurs), bouton « Mettre à jour maintenant », médianes de la zone | MVP |
| H3b | **Écran « Paramètres »** : formulaires par thème (stratégie, achat et fiscalité, financement, revente, travaux, scénarios, estimation), valeurs en % et en €, aides contextuelles, retour aux valeurs par défaut ; les valeurs modifiées priment sur le fichier `parametres.toml` | MVP |
| H4 | **Vue secteur** (commune ou rayon) : nuage prix / surface avec droite de régression, distribution du prix/m², carte des biens colorés par score | V2 |
| H5 | **Comparateur** de 2 à 4 biens côte à côte, écarts mis en évidence | V2 |
| H6 | **Notifications** (e-mail ou Telegram) sur les baisses de prix des annonces suivies et les nouvelles opportunités (prix ≤ prix d'achat maximum) | V2 / V3 |
| H7 | **Notes et photos de visite** rattachées au bien (en complément de la checklist D1) | V3 |
| H8 | **Points d'intérêt** : commerces, écoles, arrêts (OpenStreetMap / Overpass) et temps de trajet en train vers Mons, Bruxelles, etc. (iRail) | V3 |
| H9 | Export PDF ou HTML d'une fiche | V3 |

### 5.10 Fiche détaillée du bien (accès depuis la base de données)

| Onglet | Contenu | Version |
|---|---|---|
| **Annonce** | **Toutes les informations de l'annonce** : titre, adresse, prix et historique, caractéristiques (surfaces habitable, terrain, jardin, terrasse ; chambres, salles d'eau, façades, étages, cave, grenier), état, année, PEB (classe, kWh/m², n° de certificat), chauffage, cuisine, revenu cadastral, vendeur (agence / particulier), date de publication, vues et favoris, description complète, lien vers l'annonce d'origine ; **galerie de photos** de l'annonce (affichées depuis Immoweb) ; champs manquants à demander à l'agence | V1.1 |
| **Repérage et prix** | Statut GO / NO-GO, écart à la médiane / moyenne des comparables, écart au médian Statbel, comparables (tableau, graphiques, carte), valeur en l'état et après travaux | V1 (réalisé) + V1.1 |
| **Estimation des travaux** | Composition du chantier poste par poste (§5.4.1) | V1.1 |
| **Rentabilité** | Hypothèses, bilan en 3 scénarios, prix d'achat maximum, décision R1 à R7 | V1 (réalisé) |
| **Risques** | Vérification WalOnMap et risques saisis | V1 (réalisé) |
| **Historique** | Évolution du prix, durée en ligne, analyses enregistrées | V1 (réalisé) |

---

## 6. Paramètres fiscaux et juridiques — Wallonie (à valider par un notaire / fiscaliste)

| Paramètre | Personne physique (opération ponctuelle) | Société « marchand de biens » |
|---|---|---|
| Droits d'enregistrement à l'achat | **12,5 %** (le taux réduit de 3 % pour l'habitation propre et unique ne s'applique pas à un achat destiné à la revente) | Taux réduit pour les personnes faisant profession d'acheter et de vendre des immeubles (défaut ≈ 5 %), sous conditions (déclaration, revente dans le délai légal), sinon complément de droits |
| Honoraires et frais du notaire | Barème légal dégressif + frais administratifs + TVA 21 % (≈ 1,5 – 2,5 % du prix pour une maison de 150 – 250 k€) | Idem |
| Frais de l'acte de crédit | ≈ 1,5 – 2,5 % du montant emprunté | Idem |
| Imposition de la plus-value | Plus-value sur immeuble bâti revendu **dans les 5 ans** : **16,5 %** + taxe communale additionnelle (base calculée selon le CIR : prix d'acquisition majoré des frais, revalorisation annuelle, travaux facturés par des entrepreneurs) ; si les opérations sont jugées **spéculatives ou répétées** : 33 % ou imposition comme revenus professionnels au taux progressif | Impôt des sociétés : 25 % (taux réduit de 20 % sur la première tranche pour les PME qui remplissent les conditions), puis fiscalité de la distribution |
| TVA sur la revente | Non applicable (bien ancien) | Vente d'un bâtiment ancien exonérée ; **attention** : une rénovation lourde peut faire considérer le bâtiment comme « neuf » et rendre la vente soumise à TVA 21 % |
| TVA sur les travaux | 6 % (logement > 10 ans, conditions à vérifier) ou 21 % | Idem, à vérifier selon l'affectation |
| Primes régionales (rénovation, énergie) | Généralement conditionnées à l'occupation ou à la mise en location du bien : **par défaut non comptées** | Non comptées |
| Risque | Requalification en activité professionnelle si opérations répétées | Comptabilité, obligations déclaratives |

**Exigences associées :**
- P1 — Tous les taux, barèmes et seuils sont des **paramètres modifiables** avec date de validité (aucune valeur codée en dur).
- P2 — Avertissement systématique : calculs fiscaux indicatifs, validation par un professionnel requise.
- P3 — Alerte si une personne physique enchaîne plus de 2 opérations sur 3 ans (risque de requalification).
- P4 — Comparaison automatique des deux régimes sur chaque opération.

**Documents et obligations liés à la vente en Wallonie (à intégrer dans la checklist) :**
certificat PEB, procès-verbal de contrôle de l'installation électrique, extrait de la Banque de données de l'état des sols (BDES), renseignements urbanistiques, informations sur l'aléa d'inondation, attestation de la citerne à mazout le cas échéant, DIU pour les travaux postérieurs à 2001, situation au regard de l'égouttage (PASH), inventaire amiante selon la réglementation en vigueur.

---

## 7. Risques spécifiques à la région de Mons

| Risque | Source de vérification | Traitement |
|---|---|---|
| **Anciens puits de mine, affaissements miniers, karst** (Borinage, bassin du Centre) | WalOnMap — contraintes géotechniques majeures | Bloquant si le bien est concerné sans étude ; sinon provision |
| **Zones d'aléa d'inondation** (vallées de la Haine et de la Trouille) | WalOnMap — cartographie de l'aléa d'inondation | Bloquant si aléa élevé ; impact sur la revente et l'assurance |
| **Pollution du sol** (sites industriels, anciennes activités) | BDES | Bloquant si pollution avérée |
| **Infractions urbanistiques** (annexes, vérandas, transformations sans permis) | Renseignements urbanistiques, comparaison avec les plans | Condition suspensive dans l'offre |
| **Humidité ascensionnelle et caves humides** (maisons ouvrières anciennes) | Visite, mesures | Poste de travaux + imprévus majorés |
| **Amiante** (toitures et bardages en fibrociment, constructions avant 2001) | Inventaire / visite | Désamiantage chiffré |
| **Électricité non conforme** | PV de contrôle | Mise en conformité dans les 18 mois |
| **Citerne à mazout** | Visite, attestation | Neutralisation / enlèvement chiffrés |
| Sur-rénovation par rapport au quartier | Plafond 90e percentile (E3) | Limitation du budget travaux |
| Estimation trop optimiste (données d'annonces) | Indice de confiance, avis d'agents | Scénario prudent obligatoire |
| Base d'annonces incomplète (import manuel) | Taux de couverture, nombre de comparables | Tournée hebdomadaire, croisement avec Statbel, accord de données à terme |
| Changement de structure des pages Immoweb (probabilité élevée) | Tests d'extraction sur pages réelles | Secours par texte collé + modèle de langage, saisie manuelle ; extracteur isolé |
| Trop peu de biens pour une régression fiable (probabilité élevée) | Nombre de biens par secteur | Modèle activé seulement au-delà de 30 biens ; indicateurs simples en attendant |
| Données d'annonce fausses ou incomplètes (ex. surface non publiée) | Écran de vérification | Validation obligatoire, détection des valeurs aberrantes, champs à demander à l'agence |
| Biais prix demandé / prix de vente (certain) | Écart moyen par commune (B23) | Ne jamais présenter l'estimation comme une valeur vénale |
| Services WFS wallons lents ou modifiés | Suivi des erreurs d'enrichissement | Cache local, enrichissement relançable |
| Géocodage imprécis (adresse masquée) | Indicateur « position approximative » | Repli sur le centre de la commune, signalé |
| Fichiers Statbel qui changent de format | Contrôle des colonnes à l'import | Script d'import isolé |
| Projet trop ambitieux, abandonné en route | Jalons | MVP volontairement petit, livrable en quelques semaines |
| Collecte horaire bloquée par Immoweb (probabilité élevée) | Journal des collectes, alerte après 3 échecs | Arrêt propre, reprise à l'heure suivante ; import manuel en secours ; démarche d'accès officiel (M5) |
| Recours d'Immoweb lié à ses conditions d'utilisation | — | Usage strictement personnel, volume faible, aucune redistribution ; accès officiel recherché |
| Prix des travaux sous-estimés (sources génériques) | Écart estimé / devis / facturé (G2) | Recalibrage du catalogue avec des devis locaux ; imprévus provisionnés |
| Hausse des taux, allongement des délais | Sensibilité F9 | Durée d'opération courte |

---

## 8. Données et sources

| Donnée | Source | Usage |
|---|---|---|
| Annonce du bien, comparables, prix demandés | **Immoweb**, via import par l'utilisateur (§4.1) ; flux sous contrat en option | Point d'entrée, base des annonces, comparables |
| Prix médians par commune et type de maison | **Statbel** (statistiques des ventes immobilières) | Référence de marché, contrôle de cohérence |
| Tendances de prix | Baromètre des notaires (Fednot) | Actualisation |
| Géocodage, rayon de 10 km | Adresses officielles (BeSt Address / ICAR / géoservices du SPW) | Localisation |
| Cadastre, revenu cadastral | SPF Finances (CadGIS, MyMinfin pour le propriétaire) | Parcelle, précompte immobilier |
| Plan de secteur, aléa d'inondation, contraintes géotechniques, patrimoine | **WalOnMap** (Géoportail de la Wallonie) | Risques, urbanisme |
| État des sols | BDES (SPW) | Pollution |
| Performance énergétique | Certificat PEB du vendeur (n° dans l'annonce) | Classe actuelle, simulation |
| Centimes additionnels communaux | Communes / SPF Finances | Précompte immobilier, taxe sur la plus-value |
| Prix des travaux | Référentiel interne + devis d'entrepreneurs locaux | Chiffrage |
| Codes NIS, codes postaux, revenus par commune | Statbel (open data, annuel) | Rattachement communal, attractivité |
| Géocodage | Nominatim (OpenStreetMap, ≈ 1 requête/s) en complément des adresses officielles ; repli sur le centre de la commune signalé « position approximative » | Localisation |
| Zones inondables, plan de secteur, contraintes du sous-sol | Services ArcGIS REST du géoportail wallon (`EAU/ALEA_INOND`, `AMENAGEMENT_TERRITOIRE/PDS`, `SOL_SOUS_SOL/CONSULT_SSOL`), opération « identify » au point du bien sur toutes les couches ; résultats présentés en clair (couche et valeur), sans liens ni champs techniques ; un risque automatique peut être marqué « vérifié, non bloquant » | Risques |
| Annonces d'autres portails | Zimmo, Immovlan (pages sauvegardées) | V2 |
| Texte d'annonce de n'importe quel site | Extraction par modèle de langage (API Claude ou Ollama en local) | Secours d'import |
| Commerces, écoles, arrêts | Overpass (OpenStreetMap) | V3 |
| Gares et temps de trajet | iRail (API SNCB open source) | V3 |

> Statbel publie des **prix médians par bien**, pas au m² : le prix au m² du secteur est calculé par l'outil à partir des annonces en base. Toutes les sources hors annonces sont **gratuites et publiques** ; les annonces sont le point le plus fragile.

**Limite majeure** : en Belgique, les prix de transaction ne sont pas publiés à l'adresse. Les comparables sont donc des **prix demandés**, corrigés de la marge de négociation et recoupés avec Statbel et les avis d'agents. Les opérations réalisées alimentent progressivement une base interne de prix réels.

### 8.1 Modèle de données (SQLite)

| Table | Contenu |
|---|---|
| `annonces` (bien) | Caractéristiques, adresse, coordonnées, code NIS, statut, source (Immoweb, Zimmo, saisie…) |
| `historique_prix` (relevés de prix) | Un relevé daté à chaque changement de prix : le prix actuel est le dernier relevé, l'historique est gratuit |
| `extraction_brute` | JSON ou texte d'origine, date et extracteur utilisé (ré-extraction sans réimport) |
| `enrichissement` | Résultats WalOnMap (inondation, plan de secteur, contraintes géotechniques), géocodage, points d'intérêt ; chaque valeur garde **sa source et sa date** ; un champ vide = source indisponible, relançable plus tard |
| `commune` | Code NIS, nom, codes postaux, médianes Statbel par type de maison et par période |
| `indices_prix` | Indice d'évolution des prix par zone et trimestre |
| `estimation` | Prix estimés, intervalle, résidu, score, **version du modèle** |
| `operation` | Modèle financier, scénarios, décision, suivi de chantier (modules C à G) |
| `photos` | Liens des photos de chaque annonce, dans l'ordre de l'annonce |
| `catalogue_travaux` | Postes de travaux : catégorie, libellé, unité, prix bas / moyen / haut HTVA, TVA, règle de quantité, source, date |
| `travaux_bien` | Configuration du chantier d'un bien : postes cochés, quantité, niveau ou prix saisi, origine (catalogue / devis) |
| `collectes` | Journal des collectes horaires (début, fin, annonces vues / nouvelles / modifiées / retirées, erreurs) |
| `secteur_suivi` (V2), `visite` (V3) | Secteurs à surveiller ; notes et photos de visite |

Unités : prix en euros entiers, surfaces en m², dates ISO (AAAA-MM-JJ).

### 8.2 Architecture technique

La logique métier vit dans des **modules Python indépendants de l'interface** : l'interface peut être remplacée plus tard (API + application) sans toucher aux calculs ni à la base.

| Brique | Technologie | Pourquoi |
|---|---|---|
| Langage | Python 3.12+, environnement géré avec `uv` | Écosystème données et statistiques complet |
| Interface | Streamlit | Formulaires, tableaux, graphiques sans frontend à écrire |
| Base | SQLite (+ SQLAlchemy) | Un fichier, zéro serveur ; passage à PostgreSQL possible |
| Extraction | Parseurs par site (JSON intégré, JSON-LD) sur pages sauvegardées ; BeautifulSoup si nécessaire | Isolés et testés |
| Secours d'extraction | API Claude ou modèle local (Ollama) | Champs en JSON depuis un texte collé, tous sites |
| Géocodage | `geopy` + Nominatim, adresses officielles | Gratuit |
| Données géographiques | Requêtes WFS wallonnes + `shapely` | Test « point dans zone » sans SIG lourd |
| Statistiques | pandas, numpy, `statsmodels` | Régressions, intervalles, diagnostics |
| Graphiques et carte | Plotly + `streamlit-folium` | Interactifs, intégrés à l'interface |
| Tâches planifiées | APScheduler ou cron | Mises à jour Statbel, lecture des alertes e-mail, notifications |
| Tests | `pytest` / `unittest` + pages HTML sauvegardées | Détecte un extracteur cassé sans réseau |
| Déploiement | Local (Windows / Linux), puis Docker sur un serveur domestique | Même code, accessible depuis le réseau de la maison |

> **V1.1 réalisée** (cf. `README.md`) : page « Base de données » avec repérage GO / NO-GO, réglages et filtres (module R) ; fiche avec onglet Annonce (photos et toutes les informations) ; onglet « Estimation des travaux » configurable à partir du catalogue de l'annexe A (`data/catalogue_travaux.csv`) ; infrastructure de collecte horaire (`python -m immo.collecte`, journal, source « dossier d'import », emplacement pour une API). Reste à faire pour la version finale : la source de données automatique d'Immoweb (API sous accord, ou lecture des pages M7).
>
> **V1 réalisée** (cf. `README.md`) : application Streamlit et paquet `immo/` couvrant le périmètre MVP — import (page Immoweb, texte collé avec API Claude, saisie) avec écran de vérification, base des annonces, médianes Statbel et rattachement communal, comparables, valeur en l'état et après travaux, pré-chiffrage des travaux, modèle financier et prix d'achat maximum, règles R1-R7, risques WalOnMap (automatiques et manuels), historique. Reste à faire pour le jalon 2 : importer les fichiers Statbel officiels et saisir 20 maisons réelles.

---

## 9. Exemple chiffré (illustratif, régime personne physique)

Maison 3 façades, 130 m² habitables, à Frameries, état « À rénover », PEB F. Valeurs indicatives, non contractuelles.

| Poste | Calcul | Montant |
|---|---|---|
| Valeur de marché en l'état | ≈ 1 540 €/m² × 130 m² | 200 000 € |
| **Prix d'achat (−20 %)** | 200 000 × 0,80 | **160 000 €** |
| Droits d'enregistrement | 12,5 % | 20 000 € |
| Honoraires et frais du notaire (TVAC) | forfait indicatif | 3 000 € |
| Travaux TVAC (rénovation moyenne, PEB F → C) | ≈ 385 €/m² × 130 m² | 50 000 € |
| Imprévus | 15 % | 7 500 € |
| Portage (6 mois) | acte de crédit + intérêts ≈ 3,5 % + précompte, assurance, énergie | 9 000 € |
| **Prix de revient total** | | **249 500 €** |
| Prix de revente après travaux (PEB C) | 2 250 €/m² × 130 m² | 292 500 € |
| Frais de revente | agence 3 % + TVA 21 % (3,63 %) + certificats ≈ 800 € | 11 418 € |
| **Plus-value nette avant impôt** | 292 500 − 11 418 − 249 500 | **≈ 31 600 € ✅ (de justesse)** |
| Impôt indicatif (16,5 % + additionnels) | selon base CIR | ≈ 5 500 € |

**Scénario prudent** (revente −5 % → 277 875 €, travaux +20 % → 60 000 € + 15 % = 69 000 €, portage +50 % → 13 500 €, frais de revente ≈ 10 887 €) :
plus-value ≈ 277 875 − 10 887 − (160 000 + 23 000 + 69 000 + 13 500) ≈ **1 500 € ❌**

**Prix d'achat maximum (scénario prudent, marge 30 000 €)** :
`(266 988 − 69 000 − 13 500 − 30 000 − 3 000) / 1,125 ≈ 134 650 €` → soit **≈ −33 %** sous la valeur en l'état.

**Enseignements :**
- En Wallonie, avec 12,5 % de droits d'enregistrement, **acheter à −20 % ne suffit généralement pas** à garantir 30 000 € dans le scénario prudent : la décote réelle nécessaire est plutôt de **25 à 35 %**, ou il faut des biens où la rénovation crée beaucoup de valeur (fort gain PEB, maison sous-exploitée).
- Avec le régime marchand de biens (droits ≈ 5 %), le prix maximum remonte à ≈ (266 988 − 69 000 − 13 500 − 30 000 − 3 000) / 1,05 ≈ **144 300 €** (≈ −28 %).
- L'outil doit donc mettre en avant le **prix maximum** plutôt que la seule règle des −20 %.

➡ Décision pour cet exemple : **NO-GO au prix de 160 000 €** ; offre possible jusqu'à ≈ 134 650 € (personne physique).

---

## 10. Exigences non fonctionnelles

| ID | Exigence |
|---|---|
| NF1 | Application web responsive (smartphone pendant les visites : photos, checklist) |
| NF2 | Mode hors-ligne pour la checklist de visite, synchronisation ultérieure |
| NF3 | Fiche d'analyse préliminaire générée en < 30 secondes après l'import de l'annonce ; import d'une page sauvegardée en < 5 secondes |
| NF4 | Traçabilité : chaque estimation est historisée (version, date, hypothèses, sources, copie de l'annonce au jour de l'analyse) |
| NF5 | Paramètres (taux, barèmes, ratios, seuils, rayon) modifiables sans développement |
| NF6 | Sécurité : authentification, chiffrement au repos et en transit, sauvegardes quotidiennes |
| NF7 | Conformité **RGPD** (données des vendeurs, agents, entrepreneurs) |
| NF8 | Exports PDF et Excel/CSV |
| NF9 | Interface en français ; montants en euros, format belge |
| NF10 | Tests automatisés sur le moteur de calcul financier et fiscal (couverture ≥ 90 %) |
| NF11 | **Performance** : import d'une annonce jusqu'à la fiche complète en < 10 s (géocodage et WFS compris) |
| NF12 | **Robustesse** : une source en panne n'empêche pas l'enregistrement du bien ; le champ concerné reste vide, un indicateur le signale et l'enrichissement est relançable |
| NF13 | **Traçabilité des données** : chaque valeur enrichie garde sa source et sa date ; données brutes d'extraction conservées |
| NF14 | **Coût** : 0 € en fonctionnement normal ; modèle de langage limité au secours d'import (quelques centimes par annonce) |
| NF15 | **Maintenance** : un extracteur par site, isolé, avec un test sur une page réelle sauvegardée |
| NF16 | **Légal** : usage strictement personnel, pas de redistribution des annonces |
| NF17 | **Portabilité** : fonctionne en local sous Windows et Linux, puis en conteneur Docker |

---

## 11. Livrables

1. Application web locale (modules A à H).
2. Moteur de calcul financier et fiscal (Wallonie) documenté et testé.
3. Référentiel initial des prix de travaux (Hainaut) et des ratios par niveau de rénovation.
4. Paramétrage fiscal initial (droits d'enregistrement, barème notarial, taxation des plus-values, TVA).
5. Base initiale de comparables pour la zone de Mons (Statbel + annonces).
6. Modèles d'exports : fiche d'analyse préliminaire, offre d'achat, dossier banque, bilan d'opération.
7. Documentation utilisateur et guide de la checklist de visite.

---

## 12. Planning indicatif

On ne passe à la version suivante qu'une fois son jalon atteint.

| Version | Contenu | Jalon | Durée |
|---|---|---|---|
| Phase 0 | Cadrage, validation du cahier des charges et des paramètres fiscaux avec un notaire | Cahier des charges validé | 2 semaines |
| **MVP** | Projet `uv`, base SQLite ; codes NIS et médians Statbel ; saisie manuelle et liste des biens ; fiche avec écart au médian communal (**jalon 1**) ; extracteur Immoweb + écran de vérification ; secours par texte collé ; géocodage et couches WalOnMap ; prix/m² vs comparables ; travaux par régression / ratios ; modèle financier, prix maximum et Go/No-Go ; **20 vrais biens saisis** (**jalon 2**) | Jalons 1 et 2 | 6 à 8 semaines |
| **V1.1** | Page « Base de données » avec repérage GO / NO-GO et filtres (module R) ; fiche détaillée avec toutes les informations de l'annonce et les photos ; onglet « Estimation des travaux » configurable avec le catalogue de l'Annexe A ; photos enregistrées à l'import | Le repérage fait ressortir les biens sous la valeur du marché ; un chantier composé poste par poste alimente la rentabilité | 3 à 4 semaines |
| **V2** | Extracteurs Zimmo / Immovlan ; demande d'accès officiel aux données (M5) ; alertes e-mail (M6) ; suivi des annonces et historique des prix ; modèle hédonique, score ; vue secteur ; comparateur ; scénarios et sensibilité ; simulation PEB ; exports PDF ; décision sur M7 (prise : collecte horaire en version finale) | **Jalon 3** : 30 maisons dans le secteur, erreur du modèle < 15 % | 6 semaines |
| **V3** | Points d'intérêt et trajets ; notes et photos de visite ; notifications ; suivi d'opération complet (G) ; mode hors-ligne ; Docker | Outil utilisé pour une vraie décision | 6 semaines |
| **Version finale** | **Collecte automatique toutes les heures** (API si obtenue, sinon M7) sur un serveur ; journal des collectes ; recalcul du repérage et notification des nouveaux GO | Collecte horaire stable pendant 2 semaines, nouvelles annonces visibles en moins d'une heure | 3 semaines |
| Continu | Accord de données (M5), base interne de prix réels, recalibrage, extension aux appartements et à toute la Wallonie | — | — |

> Alternative rapide : une **version tableur** (Excel / Google Sheets) de la fiche d'analyse préliminaire et du modèle financier (§1.3, §5.3, §5.7, §9) peut être livrée en 1 semaine pour tester la méthode sur les annonces actuelles autour de Mons.

---

## 13. Critères de recette

- Le calcul de l'exemple §9 est reproduit à l'euro près par l'outil.
- L'extraction est validée sur au moins **10 pages Immoweb réelles sauvegardées** de la zone (prix, surfaces, chambres, PEB, kWh/m², description, date de publication correctement reconnus) ; pour chacune, la fiche d'analyse préliminaire est produite avec un statut et un prix maximum.
- Une page dont l'extraction échoue ouvre la saisie assistée sans perte des champs reconnus.
- Le réimport d'une annonce dont le prix a baissé ajoute une entrée à l'historique et met à jour le nombre de baisses.
- Un bien situé à plus de 10 km de Mons est automatiquement exclu.
- Aucun bien dont la plus-value nette du scénario prudent est < 30 000 € n'obtient le statut `GO`.
- La modification d'un taux (ex. droits d'enregistrement) met à jour tous les bilans non clôturés.
- Les exports contiennent les hypothèses, les sources et la date de l'annonce analysée.

**MVP réussi si :**
- une annonce Immoweb est importée, vérifiée et analysée en moins de 2 minutes ;
- 9 annonces sur 10 ont leurs champs principaux (prix, surface, chambres, PEB, code postal) bien extraits ;
- chaque fiche affiche l'écart au médian Statbel, le prix/m² vs comparables, les risques WalOnMap et le prix d'achat maximum ;
- 20 maisons réelles sont enregistrées et analysées.

**V2 réussie si :**
- au moins 30 maisons sont suivies dans le secteur ;
- l'erreur moyenne du modèle hédonique est inférieure à 15 % en validation croisée ;
- une baisse de prix sur une annonce suivie est détectée sans intervention.

**V1.1 réussie si :**
- la page « Base de données » affiche pour chaque bien le statut GO / NO-GO et l'écart à la référence, et le statut change quand on modifie le seuil ou la référence ;
- chaque filtre de RP4 réduit correctement la liste ;
- la fiche d'une annonce Immoweb importée affiche toutes ses informations et ses photos ;
- un chantier composé de 5 postes (ex. toiture, plafonnage, chape, carrelage, châssis) donne un total HTVA / TVAC recalculé à chaque modification, repris dans la rentabilité.

**Version finale réussie si :**
- la collecte tourne toutes les heures sans intervention pendant 2 semaines, en respectant le plafond de requêtes ;
- une nouvelle annonce de la zone apparaît dans la base en moins d'une heure, avec son statut de repérage ;
- un retrait d'annonce est détecté en moins de 24 h ;
- un blocage par le site arrête proprement la collecte et déclenche une alerte.

---

## Annexe A — Catalogue des prix des travaux (Belgique, 2025-2026)

Prix unitaires **HTVA, pose comprise** sauf mention, relevés dans des guides de prix belges en 2025-2026 (sources en fin d'annexe). Fourchettes indicatives, à recalibrer avec des devis locaux. Colonne « Quantité proposée » : règle utilisée pour pré-remplir la quantité à partir de l'annonce (SH = surface habitable), toujours modifiable.

| Catégorie | Poste | Unité | Bas | Haut | TVA | Quantité proposée |
|---|---|---|---:|---:|---|---|
| Démolition | Vidage / débarras | m³ | 35 | 70 | 6 % | à mesurer |
| Démolition | Évacuation des gravats | m³ | 20 | 45 | 6 % | à mesurer |
| Démolition | Location de conteneur | unité | 200 | 800 | 21 % | 1 par tranche de 50 m² rénovés |
| Désamiantage | Diagnostic amiante | forfait | 150 | 600 | 21 % | 1 si construit avant 2001 |
| Désamiantage | Retrait toiture fibrociment, évacuation comprise | m² | 25 | 65 | 6 % | à mesurer |
| Toiture | Toiture inclinée complète (tuiles, sous-toiture, isolation) | m² de toit | 150 | 250 | 6 % | SH / nombre d'étages × 1,3 |
| Toiture | Isolation de toiture par l'intérieur | m² de toit | 20 | 60 | 6 % | SH / nombre d'étages × 1,3 |
| Toiture | Toiture plate EPDM | m² | 55 | 90 | 6 % | à mesurer |
| Toiture | Gouttières (zinc ou PVC) | ml | 30 | 80 | 6 % | à mesurer |
| Façade et humidité | Rejointoyage de façade | m² | 40 | 60 | 6 % | à mesurer |
| Façade et humidité | Crépi de façade | m² | 35 | 120 | 6 % | à mesurer |
| Façade et humidité | Isolation de façade par l'extérieur (crépi sur isolant) | m² | 100 | 250 | 6 % | à mesurer |
| Façade et humidité | Injection contre l'humidité ascensionnelle | ml de mur | 40 | 150 | 6 % | à mesurer |
| Façade et humidité | Enduit de rénovation après assèchement | m² | 25 | 45 | 6 % | à mesurer |
| Menuiseries extérieures | Châssis PVC double vitrage posés | m² de baie | 300 | 700 | 6 % | 0,15 × SH |
| Menuiseries extérieures | Remplacement d'une fenêtre | unité | 400 | 1 300 | 6 % | SH / 12 |
| Isolation | Isolation du sol | m² | 20 | 60 | 6 % | SH du rez-de-chaussée |
| Plafonnage et cloisons | Plafonnage traditionnel murs et plafonds (rénovation) | m² | 15 | 45 | 6 % | 3,5 × SH |
| Plafonnage et cloisons | Gyproc (doublage, plafond) | m² | 25 | 60 | 6 % | à mesurer |
| Plafonnage et cloisons | Cloison en gyproc sur ossature (isolée : +15 €) | m² | 30 | 70 | 6 % | à mesurer |
| Plafonnage et cloisons | Faux plafond | m² | 45 | 120 | 6 % | à mesurer |
| Sols | Chape traditionnelle | m² | 25 | 45 | 6 % | SH |
| Sols | Chape liquide | m² | 35 | 60 | 6 % | SH |
| Sols | Ragréage | m² | 8 | 15 | 6 % | SH |
| Sols | Carrelage grès cérame, fourni et posé | m² | 40 | 70 | 6 % | 0,4 × SH |
| Sols | Pose de carrelage seule (hors fourniture) | m² | 25 | 75 | 6 % | 0,4 × SH |
| Sols | Stratifié fourni et posé | m² | 30 | 60 | 6 % | 0,6 × SH |
| Sols | Parquet contrecollé fourni et posé | m² | 50 | 90 | 6 % | 0,6 × SH |
| Finitions | Peinture murs et plafonds (préparation + 2 couches) | m² | 15 | 45 | 6 % | 3,5 × SH |
| Finitions | Porte intérieure posée | unité | 150 | 600 | 6 % | SH / 15 |
| Électricité | Rénovation électrique complète (mise aux normes RGIE) | m² SH | 80 | 150 | 6 % | SH |
| Électricité | Mise en conformité RGIE ponctuelle | forfait | 1 500 | 5 000 | 6 % | 1 |
| Plomberie et chauffage | Remplacement des conduites | forfait | 1 500 | 4 000 | 6 % | 1 |
| Plomberie et chauffage | Chaudière gaz à condensation (avec eau chaude) | unité | 3 000 | 6 000 | **21 %** | 1 |
| Plomberie et chauffage | Pompe à chaleur air-eau | unité | 8 000 | 15 000 | 6 % | 1 |
| Ventilation | VMC simple flux hygroréglable | unité | 800 | 1 600 | 6 % | 1 |
| Ventilation | VMC double flux | unité | 2 300 | 4 600 | 6 % | 1 |
| Sanitaires et cuisine | Salle de bain complète (5 à 10 m²) | forfait | 5 000 | 20 000 | 6 % | 1 par salle d'eau |
| Sanitaires et cuisine | Cuisine équipée posée (entrée de gamme : 3 000 – 5 000) | forfait | 5 000 | 20 000 | 6 % | 1 |

**Repères globaux** (contrôle de cohérence du total) : rafraîchissement 300 – 800 €/m² HTVA ; rénovation moyenne avec cuisine, salle de bain et plomberie 800 – 1 500 €/m² ; rénovation lourde avec isolation, toiture et mise en conformité 1 500 – 2 500 €/m².

**TVA** : 6 % pour la rénovation d'un logement privé de plus de 10 ans facturée par l'entrepreneur (conditions à vérifier), 21 % pour les matériaux achetés soi-même, la location de matériel et, depuis le 29/07/2025, l'installation de chaudières gaz et mazout. Aucune prime régionale n'est prévue en 2026 pour les chaudières gaz ; les primes (non comptées par défaut, §6) concernent surtout l'isolation et les pompes à chaleur.

**Sources** (consultées le 07/10/2026) :
- TrustUp, guides de prix : [rénovation de maison](https://blog.trustup.be/fr/prix-renovation-maison/), [plafonnage ou gyproc](https://blog.trustup.be/fr/plafonnage-ou-gyproc-comparatif/), [faux plafond](https://blog.trustup.be/fr/prix-faux-plafond/), [pose de carrelage](https://blog.trustup.be/fr/quel-type-de-pose-de-carrelage-choisir/), [revêtements de sol](https://blog.trustup.be/fr/type-revetement-sol-guide/), [châssis PVC](https://blog.trustup.be/fr/?p=15954), [fenêtres](https://blog.trustup.be/fr/prix-changer-fenetres/), [installation électrique](https://blog.trustup.be/fr/?p=16140), [chaudière à condensation](https://blog.trustup.be/fr/prix-chaudiere-a-condensation/), [salle de bain](https://blog.trustup.be/fr/?p=9823), [peinture](https://blog.trustup.be/fr/?p=2833), [humidité](https://blog.trustup.be/fr/traiter-humidite-habitation/), [isolation de façade](https://blog.trustup.be/fr/prix-isolation-facade/), [crépi](https://blog.trustup.be/fr/prix-crepi-de-facade/), [désamiantage](https://blog.trustup.be/fr/prix-desamiantage/), [gouttières zinc](https://blog.trustup.be/fr/prix-gouttiere-zinc/), [toit plat](https://blog.trustup.be/fr/?p=15855), [cloisons](https://blog.trustup.be/fr/?p=7166), [gyproc](https://blog.trustup.be/fr/prix-pose-placo/), [porte intérieure](https://blog.trustup.be/fr/?p=15995), [isolation des sols](https://blog.trustup.be/fr/prix-isolation-sols/), [VMC](https://blog.trustup.be/fr/?p=17345)
- Bobex : [rénovation de toiture](https://www.bobex.be/fr-be/travaux-de-toiture/prix-renovation-toiture/), [châssis au m²](https://www.bobex.be/fr-be/chassis-portes-et-fenetres/prix-chassis-au-m2/), [rejointoyage](https://www.bobex.be/fr-be/travaux-renovation-de-facades/rejointoyage-facade/), [cuisine](https://www.bobex.be/fr-be/renovation-cuisine/prix-cuisine/), [VMC](https://www.bobex.be/fr-be/systeme-de-ventilation/vmc/prix/), [désamiantage](https://www.bobex.be/fr-be/enlevement-de-lamiante/prix-desamiantage/), [plafonnage](https://www.bobex.be/travaux-plafonnage/contenu-100004)
- [Prix rénovation toiture Belgique 2026](https://prix-renovation-toiture.be/guides/prix-renovation-toiture-belgique/), [Guide rénovation — isolation](https://www.guide-renovation.be/isolation/prix-isolation), [Économie énergie — isolation du toit](https://www.economie-energie.be/isolation/isolation-du-toit/), [Batibouw+ — chape](https://www.batibouwplus.be/fr/prix-m2-chape-belgique-devis)

---

## 14. Glossaire

- **PEB** : Performance Énergétique des Bâtiments ; le certificat PEB (classes A++ à G) est obligatoire pour la vente en Wallonie.
- **Droits d'enregistrement** : impôt régional payé par l'acquéreur à l'achat d'un bien immobilier.
- **Revenu cadastral (RC)** : revenu fictif servant de base au précompte immobilier.
- **Précompte immobilier** : impôt annuel sur la propriété immobilière.
- **CoDT** : Code wallon du Développement Territorial (urbanisme, permis).
- **RGIE** : Règlement général sur les installations électriques (contrôle obligatoire à la vente).
- **BDES** : Banque de données de l'état des sols.
- **DIU** : Dossier d'intervention ultérieure.
- **WalOnMap** : géoportail cartographique de la Wallonie.
- **Statbel** : office belge de statistique.
- **Portage** : coûts supportés entre l'achat et la revente.
- **Prix de revient** : prix d'achat + frais d'acquisition + travaux + portage.
- **TRI** : Taux de Rendement Interne.
