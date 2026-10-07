# Cahier des charges — Outil d'aide à la décision pour l'achat-revente de maisons (Wallonie — région de Mons)

| Élément | Valeur |
|---|---|
| Projet | Outil d'analyse d'opérations d'achat-revente de maisons (« achat – rénovation – revente ») |
| Zone | Belgique, Région wallonne — **rayon de 10 km autour de Mons** |
| Type de bien (v1) | **Maisons** uniquement |
| Point d'entrée | **Annonce Immoweb** du bien, **importée par l'utilisateur** (pas de collecte automatique, cf. §4.1) |
| Version | 2.1 (acquisition des annonces par import utilisateur) |
| Date | 07/10/2026 |
| Statut | Proposition — à valider |

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
- **Les annonces Immoweb ne peuvent pas être collectées automatiquement** : l'extraction automatisée est interdite par les conditions d'utilisation du site, le site est protégé contre les robots, et l'environnement d'exécution de l'outil n'y a pas accès (vérifié : requête vers `www.immoweb.be` refusée). Un lien d'annonce seul ne suffit donc pas : c'est l'utilisateur qui importe l'annonce qu'il consulte (cf. §4.1).
- **Une offre d'achat écrite acceptée vaut vente** : l'offre doit être émise avec des conditions suspensives et un prix déjà validé par le modèle.

### 1.2 Objectifs métier
| # | Objectif | Critère mesurable |
|---|---|---|
| O1 | Estimer la valeur de marché d'une maison en l'état à partir de son annonce Immoweb | Écart médian ≤ 10 % avec le prix de vente réel (sur les opérations suivies) |
| O2 | Acheter environ **20 % sous le prix du marché** | Prix d'achat ≤ 0,80 × valeur de marché estimée (paramétrable) |
| O3 | Estimer le coût des travaux de rénovation | Écart ≤ 15 % entre budget estimé et coût final (hors imprévus provisionnés) |
| O4 | Estimer le prix de revente après travaux | Écart médian ≤ 8 % avec le prix de revente réel |
| O5 | Garantir une **plus-value nette minimale de 30 000 €** par opération | Aucune offre émise si la plus-value nette prévisionnelle (scénario prudent) < 30 000 € |

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

### 2.3 Exclus (v1)
- Appartements, immeubles de rapport, division d'une maison en plusieurs logements (permis d'urbanisme spécifique), terrains à bâtir.
- Démolition-reconstruction et rénovations assimilées à du neuf (régime TVA spécifique).
- Ventes publiques (Biddit) — à envisager en v2.
- Gestion locative.

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

---

## 4. Processus cible

```
 1. Annonce Immoweb consultée et importée par l'utilisateur ──► 2. Analyse préliminaire (fiche 1 page) ──► 3. Visite + checklist ──► 4. Estimation affinée
                                                                                                 │
 8. Compromis → acte (≤ 4 mois) ◄── 7. Offre écrite (conditions suspensives) ◄── 6. GO/NO-GO ◄── 5. Devis travaux
        │
        ▼
 9. Travaux (suivi budget/planning) ──► 10. Certificats (PEB, électricité) ──► 11. Mise en vente (Immoweb)
        ──► 12. Revente ──► 13. Bilan prévu / réel (recalibre les modèles)
```

### 4.1 Acquisition des annonces — contrainte structurante

L'outil **ne télécharge jamais lui-même** les pages Immoweb. Le lien (URL) d'une annonce sert d'identifiant et permet d'ouvrir l'annonce, mais ses données doivent être **transmises par l'utilisateur** qui la consulte dans son navigateur.

| Mode d'import | Description | Effort utilisateur | Priorité |
|---|---|---|---|
| **M1 — Page sauvegardée** | L'utilisateur enregistre la page (Ctrl+S, « HTML ») et la dépose dans l'outil ; les données sont extraites de l'objet `window.classified` de la page | ≈ 20 s par annonce | Must |
| **M2 — Marque-page d'import** (bookmarklet) ou petite extension de navigateur | Sur la page affichée, un clic lit les données de l'annonce et les envoie à l'outil (une annonce à la fois, à l'initiative de l'utilisateur) | 1 clic | Should |
| **M3 — Copier-coller du texte** | L'utilisateur colle le texte de l'annonce ; l'outil reconnaît prix, surfaces, chambres, PEB, kWh/m², etc. et demande les champs manquants | ≈ 1 min | Should |
| **M4 — Saisie / import CSV** | Formulaire ou fichier (une ligne par observation datée) | Variable | Must |
| **M5 — Accord de données** | Flux fourni par Immoweb ou un fournisseur de données immobilières sous contrat ; supprime la contrainte d'import manuel | Aucun | Could (à négocier) |

**Conséquences sur l'outil :**
- **Historique des prix et durée en ligne** : ils n'existent que pour les annonces **revues régulièrement**. L'outil produit une **liste de tournée** (annonces suivies non revues depuis 7 jours, avec leurs liens) que l'utilisateur parcourt chaque semaine en réimportant chaque page (M1/M2) ; une annonce introuvable lors de la tournée est marquée retirée.
- **Couverture du marché** : la base ne contient que les annonces importées. L'outil affiche pour chaque estimation le **nombre de comparables** et un **taux de couverture** (annonces suivies / annonces maisons de la zone, ce dernier nombre étant relevé manuellement sur Immoweb) ; une couverture faible abaisse l'indice de confiance.
- **Nouvelles annonces** : repérées via les **alertes e-mail Immoweb** de l'utilisateur, qui ouvre puis importe les annonces intéressantes.
- **Robustesse** : la structure des pages Immoweb peut changer ; l'extraction est testée sur des pages réelles sauvegardées, et toute erreur d'extraction bascule vers la saisie assistée (M3/M4) au lieu de bloquer.
- **Données personnelles** : les noms et coordonnées d'agents ou de vendeurs présents dans les pages ne sont pas conservés (RGPD).

---

## 5. Exigences fonctionnelles

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
| B1 | **Médianes Statbel** par commune (et si possible par ancienne commune / secteur), par type de maison (2-3 façades / 4 façades), dernière année et tendance | Must |
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

**Régression linéaire sur les travaux** — implémentation de référence dans [`travaux/`](../travaux/README.md) :

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
| Changement de structure des pages Immoweb | Tests d'extraction sur pages réelles | Bascule vers saisie assistée, mise à jour de l'extracteur |
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

**Limite majeure** : en Belgique, les prix de transaction ne sont pas publiés à l'adresse. Les comparables sont donc des **prix demandés**, corrigés de la marge de négociation et recoupés avec Statbel et les avis d'agents. Les opérations réalisées alimentent progressivement une base interne de prix réels.

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

---

## 11. Livrables

1. Application web (modules A à G).
2. Moteur de calcul financier et fiscal (Wallonie) documenté et testé.
3. Référentiel initial des prix de travaux (Hainaut) et des ratios par niveau de rénovation.
4. Paramétrage fiscal initial (droits d'enregistrement, barème notarial, taxation des plus-values, TVA).
5. Base initiale de comparables pour la zone de Mons (Statbel + annonces).
6. Modèles d'exports : fiche d'analyse préliminaire, offre d'achat, dossier banque, bilan d'opération.
7. Documentation utilisateur et guide de la checklist de visite.

---

## 12. Planning indicatif

| Phase | Contenu | Durée |
|---|---|---|
| Phase 0 | Cadrage, validation du cahier des charges et des paramètres fiscaux avec un notaire | 2 semaines |
| Phase 1 — MVP | Import par page sauvegardée et CSV (M1, M4), base des annonces, fiche d'analyse préliminaire (A), estimation (B), travaux par régression / ratios (D), modèle financier, prix maximum et Go/No-Go (C, F) | 6 à 8 semaines |
| Phase 2 | Scénarios et sensibilité, simulation PEB, intégration WalOnMap / BDES, exports PDF | 4 semaines |
| Phase 3 | Marque-page d'import et copier-coller (M2, M3), liste de tournée, suivi d'opération (G), mode hors-ligne | 6 semaines |
| Phase 4 | Démarche d'accord de données (M5), base interne de prix réels, recalibrage, extension aux appartements | En continu |

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
