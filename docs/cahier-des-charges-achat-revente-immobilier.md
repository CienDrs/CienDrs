# Cahier des charges — Outil d'aide à la décision pour l'achat-revente immobilier

| Élément | Valeur |
|---|---|
| Projet | Outil d'analyse d'opérations d'achat-revente de maisons (« fix & flip ») |
| Version | 1.0 |
| Date | 07/10/2026 |
| Statut | Proposition — à valider |

---

## 1. Contexte et objectifs

### 1.1 Contexte
L'activité consiste à acheter des maisons sous-évaluées (souvent à rénover), à réaliser des travaux de rénovation, puis à les revendre au prix du marché d'un bien rénové. La rentabilité dépend de quatre estimations, chacune source d'erreur :

1. **La valeur de marché actuelle** du bien (en l'état) ;
2. **Le prix d'achat négocié** ;
3. **Le coût réel des travaux** (et leur durée) ;
4. **Le prix de revente** après rénovation.

Aujourd'hui ces estimations sont faites « à la main » et de façon hétérogène. Le projet vise à les fiabiliser, les standardiser et les relier dans un modèle financier unique.

### 1.2 Objectifs métier
| # | Objectif | Critère mesurable |
|---|---|---|
| O1 | Estimer la valeur de marché d'une maison en l'état | Écart médian ≤ 10 % avec le prix de vente réel constaté (sur historique) |
| O2 | Acheter environ **20 % sous le prix du marché** | Prix d'achat ≤ 0,80 × valeur de marché estimée (tolérance paramétrable) |
| O3 | Estimer le coût des travaux de rénovation | Écart ≤ 15 % entre budget estimé et coût final (hors aléas provisionnés) |
| O4 | Estimer le prix de revente après travaux | Écart médian ≤ 8 % avec le prix de revente réel |
| O5 | Garantir une **plus-value nette minimale de 30 000 €** par opération | Aucune offre émise si la marge nette prévisionnelle (scénario prudent) < 30 000 € |

### 1.3 Définition de la plus-value cible
Pour éviter toute ambiguïté, la **plus-value nette** retenue comme critère de décision est :

```
Plus-value nette = Prix de revente net vendeur
                 − Prix d'achat
                 − Frais d'acquisition (notaire, agence côté achat)
                 − Coût des travaux (y compris provision pour aléas)
                 − Frais de portage (intérêts, assurance, taxe foncière, énergie, charges)
                 − Frais de revente (agence, diagnostics, mainlevée d'hypothèque)
```

- Elle est calculée **avant impôt** (seuil : **≥ 30 000 €**).
- L'outil affiche également la **plus-value après impôt** selon le régime fiscal choisi (cf. §6), à titre informatif ; le seuil après impôt est un paramètre optionnel.

---

## 2. Périmètre

### 2.1 Inclus
- Maisons individuelles (anciennes, > 5 ans) en France métropolitaine.
- Sourcing et qualification d'annonces.
- Estimation de la valeur en l'état et après travaux.
- Chiffrage des travaux par lots.
- Modèle financier complet et décision Go / No-Go.
- Calcul du prix d'achat maximum (prix plafond de l'offre).
- Suivi de l'opération jusqu'à la revente et comparaison prévu / réel.

### 2.2 Exclus (version 1)
- Appartements en copropriété, immeubles de rapport, terrains à bâtir, division parcellaire.
- Opérations de construction neuve / rénovation lourde assimilée à du neuf (régime TVA spécifique).
- Gestion locative.
- Signature électronique des actes, comptabilité complète.

---

## 3. Acteurs et utilisateurs

| Acteur | Rôle |
|---|---|
| Investisseur / porteur de projet | Utilisateur principal : analyse, décide, fait les offres |
| Chasseur / apporteur d'affaires | Saisit des biens repérés |
| Artisans / maître d'œuvre | Fournissent les devis, valident le chiffrage |
| Agent immobilier | Source des biens, avis de valeur à la revente |
| Notaire, expert-comptable | Validation fiscale et juridique (hors outil) |
| Banque / financeur | Destinataire du dossier de financement exporté |

---

## 4. Processus cible

```
 1. Sourcing ──► 2. Pré-qualification ──► 3. Visite & diagnostic ──► 4. Estimation valeur en l'état
                                                                               │
 8. Suivi chantier ◄── 7. Achat ◄── 6. Offre (≤ prix plafond) ◄── 5. Chiffrage travaux + valeur après travaux
        │                                                              + modèle financier → GO / NO-GO
        ▼
 9. Mise en vente ──► 10. Revente ──► 11. Bilan prévu / réel (alimente les modèles)
```

---

## 5. Exigences fonctionnelles

### 5.1 Module A — Sourcing et pré-qualification

| ID | Exigence | Priorité |
|---|---|---|
| A1 | Saisie manuelle d'un bien (adresse, surface habitable, terrain, pièces, année, DPE, prix affiché, URL, photos) | Must |
| A2 | Import d'annonces (URL ou fichier CSV) | Should |
| A3 | Géocodage automatique de l'adresse (API Adresse / BAN) | Must |
| A4 | Détection des signaux de décote : bien en vente depuis longtemps, baisses de prix successives, DPE F/G, succession, mention « travaux à prévoir » | Should |
| A5 | Score de pré-qualification rapide : `prix affiché / valeur estimée` ; alerte si ≤ 0,85 | Must |
| A6 | Alertes (email) sur nouveaux biens correspondant aux critères (zone, budget, surface, écart de prix) | Could |

### 5.2 Module B — Estimation de la valeur de marché en l'état

**Méthode principale : comparaison par transactions réelles.**

| ID | Exigence | Priorité |
|---|---|---|
| B1 | Récupération des ventes comparables via **DVF** (Demandes de Valeurs Foncières, data.gouv.fr) : maisons, rayon paramétrable (défaut 1 km, élargi à 3 km si < 10 ventes), 24 derniers mois | Must |
| B2 | Filtrage des comparables : surface ± 25 %, terrain comparable, exclusion des valeurs aberrantes (méthode IQR) | Must |
| B3 | Calcul du prix médian au m², quartiles, nombre de comparables, et **indice de confiance** (faible / moyen / élevé selon nombre et dispersion) | Must |
| B4 | Ajustements qualitatifs paramétrables (en % ou €) : état général, DPE, terrain, exposition, nuisances, stationnement, piscine, dépendances | Must |
| B5 | Actualisation temporelle des ventes DVF (indice notaires-INSEE) | Should |
| B6 | Croisement avec les prix des annonces actives (prix affichés, en général 3 à 8 % au-dessus des prix signés) | Could |
| B7 | Saisie d'avis de valeur externes (agents) et affichage de l'écart avec l'estimation | Should |
| B8 | Résultat : **valeur basse / centrale / haute**, avec justification (liste des comparables, carte) | Must |

```
Valeur en l'état = Prix médian €/m² (comparables « à rénover » si disponibles) × Surface habitable
                   × (1 + Σ ajustements)
```

### 5.3 Module C — Prix d'achat cible et offre

| ID | Exigence | Priorité |
|---|---|---|
| C1 | Prix cible = valeur en l'état × (1 − décote cible), **décote cible par défaut = 20 %** (paramétrable) | Must |
| C2 | Calcul du **prix d'achat maximum** garantissant la marge minimale (formule ci-dessous) | Must |
| C3 | Prix d'offre recommandé = min(prix cible, prix maximum) | Must |
| C4 | Génération d'un argumentaire de négociation (travaux chiffrés, comparables, durée de mise en vente, DPE) | Should |
| C5 | Génération d'une lettre d'offre avec conditions suspensives (prêt, permis/déclaration préalable si nécessaire) | Could |

**Prix d'achat maximum (net vendeur)** :

```
Prix_max = (Revente_nette − Travaux_total − Portage − Frais_revente − Marge_min) / (1 + taux_frais_acquisition)
```
avec `Marge_min = 30 000 €` et `taux_frais_acquisition` selon le régime (cf. §6).

> Règle : si `Prix_max < Prix_cible`, c'est `Prix_max` qui borne l'offre. Si `Prix_max` est très inférieur au prix affiché (paramètre : > 25 % d'écart), le bien est signalé « non négociable réalistement ».

### 5.4 Module D — Estimation du coût des travaux

| ID | Exigence | Priorité |
|---|---|---|
| D1 | Grille de visite structurée (checklist) : structure, toiture, façade, menuiseries, électricité, plomberie, chauffage, isolation, VMC, sols, murs, cuisine, salles d'eau, extérieurs, assainissement | Must |
| D2 | Chiffrage par **lots** à partir d'un référentiel de prix unitaires (€/m², €/unité) paramétrable par région | Must |
| D3 | Niveaux de rénovation prédéfinis (ratios indicatifs, à calibrer localement) : | Must |
|    | — Rafraîchissement : 200 – 500 €/m² | |
|    | — Rénovation moyenne : 500 – 1 000 €/m² | |
|    | — Rénovation lourde : 1 000 – 1 800 €/m² | |
| D4 | Remplacement progressif des estimations par les **devis réels** des artisans (suivi : estimé / devis / facturé) | Must |
| D5 | Provision pour **aléas** : 10 % (rafraîchissement) à 20 % (rénovation lourde / bâti ancien) | Must |
| D6 | Prise en compte des diagnostics obligatoires (DPE, amiante, plomb, termites, électricité, gaz, assainissement, ERP/Géorisques) : alertes sur les postes à risque | Must |
| D7 | Simulation du **gain de classe DPE** après travaux (impact sur la valeur de revente) | Should |
| D8 | Estimation de la **durée des travaux** (planning par lot) alimentant le calcul de portage | Must |
| D9 | Signalement des formalités d'urbanisme (déclaration préalable, permis) selon les travaux (façade, ouvertures, extension) et le PLU | Should |

### 5.5 Module E — Estimation du prix de revente après travaux

| ID | Exigence | Priorité |
|---|---|---|
| E1 | Comparables DVF filtrés sur des biens **en bon état / récemment rénovés** (si identifiables) ou quartile supérieur des ventes du secteur | Must |
| E2 | Ajustement selon le DPE cible (une passoire F/G rénovée en C/D se revend nettement mieux) | Must |
| E3 | Plafonnement : alerte si la valeur après travaux dépasse le 90e percentile du secteur (risque de « sur-rénovation ») | Must |
| E4 | Estimation du délai de revente (délai moyen de vente local) | Should |
| E5 | Trois scénarios : **prudent** (−5 % sur prix de revente, +20 % travaux, +3 mois), **central**, **optimiste** | Must |

### 5.6 Module F — Modèle financier et décision

| ID | Exigence | Priorité |
|---|---|---|
| F1 | Bilan d'opération complet (cf. formule §1.3) pour les 3 scénarios | Must |
| F2 | Frais d'acquisition selon le régime (particulier ≈ 7,5 – 8,5 % ; marchand de biens avec engagement de revente ≈ 2,5 – 3,5 %) | Must |
| F3 | Frais de portage : intérêts du prêt (taux, durée, différé), assurance emprunteur, frais de dossier/garantie, taxe foncière au prorata, assurance PNO, énergie, abonnements | Must |
| F4 | Frais de revente : honoraires d'agence (si vente via agence), diagnostics, mainlevée | Must |
| F5 | Indicateurs : plus-value nette, marge sur prix de revient (%), TRI, rendement sur fonds propres, durée totale | Must |
| F6 | Calcul fiscal (cf. §6) et plus-value après impôt | Should |
| F7 | **Décision automatique** (cf. §5.7) avec justification | Must |
| F8 | Analyse de sensibilité : impact de ±10 % sur travaux, ±5 % sur prix de revente, +3/+6 mois de délai | Should |
| F9 | Export PDF « dossier banque » (descriptif, estimation, travaux, bilan, planning) | Should |

### 5.7 Règles de décision Go / No-Go

| Règle | Condition | Résultat |
|---|---|---|
| R1 | Plus-value nette (scénario **prudent**) ≥ 30 000 € | Obligatoire pour GO |
| R2 | Prix d'achat ≤ 80 % de la valeur en l'état (tolérance paramétrable, ex. 82 %) | Obligatoire pour GO |
| R3 | Marge nette (central) ≥ 15 % du prix de revient total | Recommandé |
| R4 | Indice de confiance de l'estimation ≥ « moyen » | Sinon : GO sous réserve d'avis de valeur externe |
| R5 | Aucun risque bloquant (structure, pollution, zone inondable non maîtrisée, servitude, litige) | Obligatoire |
| R6 | Durée totale d'opération ≤ 12 mois (paramétrable) | Recommandé |

**Statuts** : `GO` (toutes règles obligatoires et recommandées OK) · `GO SOUS CONDITIONS` (obligatoires OK, recommandées partiellement) · `NO-GO`.

### 5.8 Module G — Suivi d'opération et retour d'expérience

| ID | Exigence | Priorité |
|---|---|---|
| G1 | Tableau de bord des opérations (pipeline : repéré, visité, offre, compromis, acte, travaux, en vente, vendu) | Must |
| G2 | Suivi budgétaire du chantier (estimé / engagé / payé) avec alerte de dépassement > 10 % | Must |
| G3 | Suivi du planning et recalcul du portage en cas de retard | Should |
| G4 | Bilan final prévu / réel par poste | Must |
| G5 | Recalibrage des référentiels (prix unitaires travaux, ajustements de valeur) à partir des opérations clôturées | Could |

---

## 6. Paramètres fiscaux et juridiques (à valider par un notaire / expert-comptable)

L'outil doit permettre de choisir le **régime** de l'opération, car il change fortement la rentabilité :

| Paramètre | Particulier (opération ponctuelle) | Marchand de biens (société à l'IS) |
|---|---|---|
| Frais d'acquisition | ≈ 7,5 – 8,5 % (droits de mutation selon département) | ≈ 2,5 – 3,5 % avec engagement de revente sous 5 ans |
| Imposition de la plus-value | Plus-value immobilière des particuliers : 19 % IR + prélèvements sociaux (17,2 % — taux à vérifier selon la loi de finances en vigueur), + surtaxe si PV > 50 000 € ; pas d'abattement pour durée de détention < 6 ans | Bénéfice imposé à l'IS (15 % jusqu'au plafond légal, 25 % au-delà), puis fiscalité de la distribution |
| Travaux déductibles | Uniquement sur justificatifs d'entreprises (pas la main-d'œuvre propre) | Charges de l'opération (stock) |
| TVA | Non applicable en principe | Vente d'un bien achevé depuis > 5 ans : exonérée (sauf option) ; **attention** : une rénovation lourde rendant l'immeuble « à l'état neuf » rend la vente taxable à la TVA |
| Risque | Requalification en activité de marchand de biens si opérations répétées (habitude + intention spéculative) | Obligations comptables et déclaratives, garanties dues aux acquéreurs |

**Exigences associées :**
- P1 — Tous les taux sont des **paramètres modifiables** (aucun taux codé en dur), avec date de validité.
- P2 — Avertissement systématique : les calculs fiscaux sont indicatifs et doivent être validés par un professionnel.
- P3 — Alerte si le profil « particulier » enchaîne plus de 2 opérations sur 3 ans (risque de requalification).

---

## 7. Données et sources

| Donnée | Source | Usage |
|---|---|---|
| Transactions immobilières | DVF / DVF+ (data.gouv.fr, Cerema) | Comparables, prix au m² |
| Géocodage | API Adresse (BAN) | Localisation |
| Cadastre | API Cadastre / IGN | Parcelle, surface terrain |
| Performance énergétique | Base DPE ADEME (API) | DPE du bien et des comparables |
| Risques | Géorisques | Inondation, argiles, radon, sites pollués |
| Urbanisme | Géoportail de l'urbanisme (PLU) | Contraintes travaux, extensions |
| Indices de prix | Indices notaires-INSEE | Actualisation des ventes |
| Données socio-démographiques | INSEE | Attractivité du secteur |
| Prix travaux | Référentiel interne + devis artisans | Chiffrage |

**Contraintes données :** DVF a un décalage de publication (≈ 6 mois) et ne contient ni l'état du bien ni le DPE : d'où les ajustements manuels et le croisement avec la base DPE.

---

## 8. Exemple chiffré (scénario central)

Maison de 100 m² habitables, DPE F, à rénover (rénovation moyenne). Régime : particulier.

| Poste | Calcul | Montant |
|---|---|---|
| Valeur de marché en l'état | 2 500 €/m² × 100 m² | 250 000 € |
| **Prix d'achat (−20 %)** | 250 000 × 0,80 | **200 000 €** |
| Frais de notaire | ≈ 8 % | 16 000 € |
| Travaux | 400 €/m² × 100 m² | 40 000 € |
| Aléas | 10 % des travaux | 4 000 € |
| Portage (6 mois) | intérêts ≈ 4 % sur 260 k€ × 0,5 an + taxe foncière, assurance, énergie | 7 200 € |
| **Prix de revient total** | | **267 200 €** |
| Prix de revente après travaux (DPE C) | 3 300 €/m² × 100 m² | 330 000 € |
| Frais de revente | agence 4 % + diagnostics | 13 700 € |
| Revente nette | | 316 300 € |
| **Plus-value nette avant impôt** | 316 300 − 267 200 | **49 100 € ✅** |

**Scénario prudent** (revente −5 % → 313 500 €, travaux +20 % → 52 800 € aléas compris, +3 mois de portage → 10 800 €, frais de revente ≈ 13 040 €) :
plus-value ≈ 313 500 − 13 040 − (200 000 + 16 000 + 52 800 + 10 800) ≈ **20 860 € ❌ < 30 000 €**

**Prix d'achat maximum (scénario prudent)** :
`(300 460 − 52 800 − 10 800 − 30 000) / 1,08 ≈ 191 500 €`

➡ Décision : **GO SOUS CONDITIONS** — l'offre doit être plafonnée à ≈ **191 500 €** (soit −23 % sous la valeur en l'état) pour respecter le seuil de 30 000 € dans le scénario prudent, ou la revente doit se faire sans agence.

---

## 9. Exigences non fonctionnelles

| ID | Exigence |
|---|---|
| NF1 | Application web responsive (utilisable sur smartphone pendant les visites, y compris prise de photos et saisie de la checklist) |
| NF2 | Mode hors-ligne pour la checklist de visite, synchronisation ultérieure |
| NF3 | Temps de calcul d'une estimation complète < 10 secondes |
| NF4 | Traçabilité : chaque estimation est historisée (version, date, hypothèses, sources) |
| NF5 | Paramètres (taux, ratios, seuils) modifiables sans développement |
| NF6 | Sécurité : authentification, données chiffrées au repos et en transit, sauvegardes quotidiennes |
| NF7 | Conformité RGPD (données personnelles des vendeurs, artisans) |
| NF8 | Exports PDF et Excel/CSV |
| NF9 | Code documenté, tests automatisés sur le moteur de calcul financier (couverture ≥ 90 %) |

---

## 10. Risques et mesures de maîtrise

| Risque | Impact | Mesure |
|---|---|---|
| Surestimation de la valeur de revente | Marge détruite | Scénario prudent obligatoire, plafond 90e percentile, avis de valeur d'agents |
| Dérive du coût des travaux | Marge réduite | Provision aléas, devis avant offre ferme, suivi budgétaire |
| Vices cachés / structure | Très élevé | Visite avec professionnel du bâtiment, diagnostics, condition suspensive |
| Allongement des délais (chantier, vente) | Portage accru | Planning, simulation +3/+6 mois |
| Retournement du marché / hausse des taux | Prix de revente en baisse | Suivi des indices, durée d'opération courte |
| Requalification fiscale | Imposition alourdie | Alerte P3, validation par expert-comptable |
| Qualité des données (DVF incomplet) | Estimation biaisée | Indice de confiance, élargissement du rayon, croisement sources |

---

## 11. Livrables

1. Application web (modules A à G).
2. Moteur de calcul financier documenté et testé.
3. Référentiel de prix travaux initial (par lot et par région).
4. Paramétrage fiscal initial.
5. Modèles d'exports (dossier banque, lettre d'offre, bilan d'opération).
6. Documentation utilisateur et guide de la checklist de visite.

---

## 12. Planning indicatif

| Phase | Contenu | Durée |
|---|---|---|
| Phase 0 | Cadrage, validation du cahier des charges | 2 semaines |
| Phase 1 — MVP | Saisie d'un bien, estimation DVF (B), chiffrage travaux par ratios (D), modèle financier et Go/No-Go (F) | 6 à 8 semaines |
| Phase 2 | Prix d'achat max et offre (C), scénarios et sensibilité, exports PDF | 4 semaines |
| Phase 3 | Sourcing et alertes (A), suivi d'opération (G), mode hors-ligne | 6 semaines |
| Phase 4 | Recalibrage automatique, intégration DPE / Géorisques avancée | En continu |

> Alternative rapide : une **première version sous tableur** (Excel/Google Sheets) reprenant le modèle financier (§1.3, §5.3, §5.7) peut être livrée en 1 semaine pour valider les hypothèses avant le développement de l'application.

---

## 13. Critères de recette

- Le calcul de l'exemple §8 est reproduit à l'euro près par l'outil.
- Sur un jeu de 20 ventes historiques connues, l'estimation en l'état respecte l'objectif O1.
- Aucun bien dont la plus-value nette du scénario prudent est < 30 000 € n'obtient le statut `GO`.
- La modification d'un taux fiscal ou d'un seuil met à jour tous les bilans non clôturés.
- Les exports PDF contiennent les hypothèses et les sources de chaque estimation.

---

## 14. Glossaire

- **DVF** : base publique des transactions immobilières (Demandes de Valeurs Foncières).
- **DPE** : Diagnostic de Performance Énergétique (classes A à G).
- **Portage** : ensemble des coûts supportés entre l'achat et la revente.
- **Prix de revient** : prix d'achat + frais d'acquisition + travaux + portage.
- **Marchand de biens** : professionnel dont l'activité habituelle est l'achat-revente d'immeubles.
- **TRI** : Taux de Rendement Interne de l'opération.
