# Base de données des annonces de maisons (Immoweb) — région de Mons

Implémentation des exigences B9 à B17 du [cahier des charges](../docs/cahier-des-charges-achat-revente-immobilier-wallonie.md#521-base-de-données-des-annonces-de-maisons-immoweb).
SQLite + Python (numpy, pandas), sans serveur.

| Fichier | Rôle |
|---|---|
| `schema.sql` | Tables `annonces`, `historique_prix`, `indices_prix` |
| `base_annonces.py` | Import, indicateurs, comparables, ligne de commande |
| `generer_exemple.py` | Génère des annonces **fictives** pour tester |
| `data/annonces_exemple.csv` | Observations fictives (identifiants `EX…`) |
| `data/indices_prix_exemple.csv` | Indices **fictifs** — à remplacer par l'indice des prix des maisons de Statbel |
| `tests/` | Tests unitaires (`python -m unittest discover -s tests`) |

## Alimentation de la base

Les conditions d'utilisation d'Immoweb interdisent l'extraction automatisée. La base est donc alimentée :
- par les **pages d'annonces sauvegardées** en naviguant (Ctrl+S) : `importer-page annonce.html` ;
- par **import CSV** (une ligne = une observation datée, mêmes colonnes que `data/annonces_exemple.csv`) ;
- ou par un accord de données avec Immoweb ou un fournisseur de données immobilières.

Chaque import est une **observation** : la date de dernière observation est mise à jour et le prix n'est ajouté à l'historique que s'il a changé. Plus les annonces sont revues régulièrement (ex. chaque semaine), plus l'historique des prix et les durées en ligne sont précis. L'outil ne connaît que les prix qu'il a observés : une baisse antérieure au premier import n'apparaît pas.

L'extraction des pages repose sur l'objet `window.classified` de la page Immoweb ; sa structure peut évoluer, il faut la vérifier sur une page réelle.

## Utilisation

```bash
python base_annonces.py init
python base_annonces.py importer-page annonce.html
python base_annonces.py importer-csv mes_observations.csv
python base_annonces.py importer-indices indices_statbel.csv
python base_annonces.py maj-statut --jours 14        # annonces non revues depuis 14 jours = retirées
python base_annonces.py lister --commune Frameries --csv export.csv

# Situer une annonce de la base, ou un bien décrit par ses caractéristiques
python base_annonces.py situer 12345678
python base_annonces.py situer --prix 160000 --surface 130 --chambres 3 --lat 50.408 --lon 3.897 --facades 3 --etat "À rénover"
```

`situer` affiche les comparables retenus et les critères appliqués, la moyenne, la médiane, le minimum, le maximum et les quartiles du prix et du prix/m² (actualisés), la durée en ligne, une ventilation par état et par classe PEB, puis la position du bien (écart à la médiane et percentile).
