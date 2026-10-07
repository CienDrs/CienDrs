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

## Ce que fait la V1

| Page | Fonctions |
|---|---|
| **Ajouter un bien** | Import d'une page Immoweb enregistrée (Ctrl+S), d'un texte d'annonce de n'importe quel site (API Claude ou expressions régulières) ou saisie manuelle → **écran de vérification** obligatoire (prix, surface, code postal wallon) → géocodage et vérification des risques |
| **Biens** | Liste filtrable (commune, état, en ligne, exemples), prix/m², jours en ligne, baisses de prix, dernière décision |
| **Fiche du bien** | Prix/m², **écart au médian Statbel** de la commune, **prix/m² vs comparables**, valeur en l'état et après travaux (fourchette, confiance), graphiques et carte, pré-chiffrage des travaux, **modèle financier** (3 scénarios, frais wallons, portage, impôt indicatif), **prix d'achat maximum**, **décision GO / GO SOUS CONDITIONS / NO-GO** (règles R1 à R7), risques automatiques et manuels, historique des prix, analyses enregistrées |
| **Données** | État de la mise à jour automatique Statbel (date, source, erreurs) et bouton « Mettre à jour maintenant » ; médianes de la zone ; import / export d'annonces |
| **Paramètres** | Formulaires par thème (stratégie, fiscalité, financement, revente, travaux, scénarios, estimation) ; les valeurs modifiées sont enregistrées dans `data/parametres_utilisateur.json`, les valeurs par défaut restent dans `immo/parametres.toml` |

## Organisation

| Chemin | Contenu |
|---|---|
| `app.py` | Interface Streamlit |
| `immo/annonces.py` | Base SQLite des annonces, historique des prix, actualisation, comparables, import de page Immoweb |
| `immo/estimation.py` | Valeur en l'état et après travaux à partir des comparables |
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
