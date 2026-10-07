# Analyse immo Mons — V1

Outil d'aide à la décision pour l'**achat – rénovation – revente de maisons** dans un rayon de 10 km autour de Mons (Wallonie) : estimer la valeur d'une maison, viser un achat ~20 % sous le marché, chiffrer les travaux et la revente, et ne faire une offre que si la **plus-value nette atteint au moins 30 000 €** dans le scénario prudent.

Cahier des charges : [`docs/cahier-des-charges-achat-revente-immobilier-wallonie.md`](docs/cahier-des-charges-achat-revente-immobilier-wallonie.md).

## Démarrer

```bash
uv sync                      # installe Python et les dépendances
uv run streamlit run app.py  # ouvre l'application sur http://localhost:8501
```

Au premier lancement, la base est vide : page **Données** → « Charger les données d'exemple (fictives) » pour essayer l'outil, puis remplacez-les par vos données.

Optionnel : `export ANTHROPIC_API_KEY=…` pour extraire les annonces collées en texte avec l'API Claude (sinon, extraction par expressions régulières).

## Ce que fait la V1

| Page | Fonctions |
|---|---|
| **Ajouter un bien** | Import d'une page Immoweb enregistrée (Ctrl+S), d'un texte d'annonce de n'importe quel site (API Claude ou expressions régulières) ou saisie manuelle → **écran de vérification** obligatoire (prix, surface, code postal wallon) → géocodage et vérification des risques |
| **Biens** | Liste filtrable (commune, état, en ligne, exemples), prix/m², jours en ligne, baisses de prix, dernière décision |
| **Fiche du bien** | Prix/m², **écart au médian Statbel** de la commune, **prix/m² vs comparables**, valeur en l'état et après travaux (fourchette, confiance), graphiques et carte, pré-chiffrage des travaux, **modèle financier** (3 scénarios, frais wallons, portage, impôt indicatif), **prix d'achat maximum**, **décision GO / GO SOUS CONDITIONS / NO-GO** (règles R1 à R7), risques automatiques et manuels, historique des prix, analyses enregistrées |
| **Données** | Import Statbel (CSV/Excel), codes postaux, indices de prix, annonces CSV ; mise à jour des statuts ; export |
| **Paramètres** | Taux, ratios et seuils (fichier `immo/parametres.toml`) |

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
| `tests/` | Tests automatisés (`uv run pytest`), dont la page Immoweb réelle et l'exemple chiffré du cahier des charges |

## Limites connues de la V1

- **Données d'exemple fictives** : annonces `EX…`, médianes Statbel et indices marqués « FICTIF ». À remplacer par les fichiers officiels de Statbel et vos propres annonces.
- **Collecte des annonces** : pas de collecte automatique d'Immoweb (mode M7 en attente de décision) ; import page par page, texte collé ou CSV.
- **Risques WalOnMap** : les adresses des services du géoportail wallon sont configurées dans `parametres.toml` mais n'ont pas pu être vérifiées depuis l'environnement de développement ; en cas d'échec, la fiche le signale et les risques se cochent à la main.
- **Ratios de travaux** indicatifs (cahier des charges D4) : à calibrer avec vos devis ; le modèle hédonique et le score arrivent en V2.
- **Fiscalité** indicative : à valider par un notaire / fiscaliste.
