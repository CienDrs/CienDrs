# Analyse immo Mons — V1

Outil d'aide à la décision pour l'**achat – rénovation – revente de maisons** dans un rayon de 10 km autour de Mons (Wallonie) : estimer la valeur d'une maison, viser un achat ~20 % sous le marché, chiffrer les travaux et la revente, et ne faire une offre que si la **plus-value nette atteint au moins 30 000 €** dans le scénario prudent.

Cahier des charges : [`docs/cahier-des-charges-achat-revente-immobilier-wallonie.md`](docs/cahier-des-charges-achat-revente-immobilier-wallonie.md).

## Démarrer

Prérequis : **Python 3.11 ou plus récent**.

### Avec Poetry

```bash
pip install poetry               # si Poetry n'est pas encore installé (ou : pipx install poetry)
poetry install                   # crée l'environnement et installe les dépendances (poetry.lock)
poetry run streamlit run app.py  # ouvre l'application sur http://localhost:8501
poetry run pytest                # lance les tests
```

### Avec pip (sans Poetry)

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate     Mac / Linux : source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

`requirements.txt` est généré depuis `poetry.lock` (`poetry export --only main --without-hashes -f requirements.txt -o requirements.txt`, extension `poetry-plugin-export`) ; pour les tests, ajoutez `pip install pytest`.

Au lancement, l'application **importe elle-même les prix médians Statbel** par commune (connexion internet nécessaire, puis au plus tous les 30 jours) et la table des codes postaux de la zone. Pour essayer l'outil sans vos propres annonces : page **Données** → « Charger des annonces d'exemple (fictives) ».

Optionnel : définir `ANTHROPIC_API_KEY` pour extraire les annonces collées en texte avec l'API Claude (sinon, extraction par expressions régulières).

## Ce que fait l'application (V1.1)

| Page | Fonctions |
|---|---|
| **Base de données** | Tous les biens récoltés avec le **repérage GO / NO-GO** (phase 1) : écart du prix/m² à la médiane ou à la moyenne des biens similaires ramenés au même état ; réglages à l'écran (référence, seuil, rayon, nombre de comparables) ; filtres (repérage, commune, prix, prix/m², surface, distance, terrain, chambres, façades, état, PEB, année, écart, baisse de prix, date de publication, durée en ligne, en ligne / retirée) ; photo miniature ; export CSV ; un clic ouvre la fiche |
| **Fiche du bien** | Onglets **Annonce** (photos, toutes les informations, description, champs à compléter), **Repérage et prix** (statut, comparables, médian Statbel, valeur en l'état et après travaux, graphiques, carte), **Estimation des travaux** (chantier composé poste par poste à partir du catalogue de prix de l'annexe A : modèles, quantités proposées, niveau bas / moyen / haut ou prix de devis, postes libres, totaux HTVA / TVA / TVAC, imprévus, durée), **Rentabilité** (3 scénarios, prix d'achat maximum, décision R1 à R7), **Risques** (géoportail wallon et risques saisis), **Historique** |
| **Ajouter un bien** | Page Immoweb enregistrée (avec ses photos), texte d'annonce collé (API Claude ou expressions régulières) ou saisie, avec écran de vérification |
| **Données** | Mise à jour automatique Statbel, collecte automatique (journal, lancement manuel), import / export d'annonces |
| **Paramètres** | Formulaires par thème ; valeurs modifiées enregistrées dans `data/parametres_utilisateur.json` |

## Collecte automatique

```bash
poetry run python -m immo.collecte            # une collecte (à planifier toutes les heures : cron, planificateur Windows)
poetry run python -m immo.collecte --boucle   # collecte en continu, toutes les 60 minutes
```

Sources (section `[collecte]` de `immo/parametres.toml`) :
- **dossier d'import** (`data/import/`) : les pages d'annonces enregistrées (.html, avec photos) et les fichiers CSV qui y sont déposés sont importés puis rangés dans `traites/` (ou `erreurs/`) ;
- **API** : emplacement prévu pour un accès officiel aux données (clé dans la variable d'environnement `IMMO_API_CLE`), à brancher quand un accès est obtenu.

La lecture automatique des pages d'Immoweb (mode M7 du cahier des charges) n'est pas incluse dans cette version.

## Organisation

| Chemin | Contenu |
|---|---|
| `app.py` | Interface Streamlit |
| `immo/annonces.py` | Base SQLite des annonces, historique des prix, actualisation, comparables, import de page Immoweb |
| `immo/estimation.py` | Valeur en l'état et après travaux à partir des comparables |
| `immo/reperage.py` | Repérage GO / NO-GO (phase 1) |
| `immo/chantier.py` | Estimation des travaux poste par poste ; catalogue `data/catalogue_travaux.csv` |
| `immo/collecte.py` | Collecte automatique (dossier d'import, API), journal |
| `immo/finance.py` | Bilan d'opération, scénarios, prix d'achat maximum, règles de décision |
| `immo/travaux.py` | Pré-chiffrage des travaux (ratios €/m² par niveau + gain PEB) |
| `immo/regression_travaux.py` | Régression sur le coût des travaux (à alimenter avec les chantiers réels) |
| `immo/statbel.py` | Communes, codes postaux, prix médians Statbel |
| `immo/geo.py` | Géocodage (Nominatim) et risques WalOnMap (aléa d'inondation, contraintes géotechniques, plan de secteur) |
| `immo/extraction_texte.py` | Extraction depuis un texte collé (API Claude en sortie structurée + expressions régulières) |
| `immo/analyse.py` | Assemblage de la fiche, hypothèses et analyses enregistrées |
| `immo/parametres.toml` | Tous les paramètres modifiables |
| `data/` | Données d'exemple (**fictives**, sauf la table des codes postaux) |
| `tests/` | Tests automatisés (`poetry run pytest`), dont la page Immoweb réelle et l'exemple chiffré du cahier des charges |

## Limites connues de la V1

- **Données d'exemple fictives** : annonces `EX…` (masquables dans la liste). Les médianes Statbel sont, elles, téléchargées automatiquement.
- **Sources Statbel et géoportail non testées en conditions réelles** : l'environnement de développement n'y a pas accès. L'application gère plusieurs formats de fichier et affiche clairement les échecs ; envoyez le message d'erreur de la page Données ou de l'onglet Risques s'il y en a un.
- **Collecte des annonces** : pas de collecte automatique d'Immoweb (mode M7 en attente de décision) ; import page par page, texte collé ou CSV.
- **Ratios de travaux** indicatifs (cahier des charges D4) : à calibrer avec vos devis ; le modèle hédonique et le score arrivent en V2.
- **Fiscalité** indicative : à valider par un notaire / fiscaliste.
