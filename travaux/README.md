# Régression linéaire sur le coût des travaux

Implémentation des exigences D12 à D14 du [cahier des charges](../docs/cahier-des-charges-achat-revente-immobilier-wallonie.md).

| Fichier | Rôle |
|---|---|
| `regression_travaux.py` | Estime les modèles (moindres carrés ordinaires), écrit le rapport et les coefficients, prédit le coût d'un bien |
| `generer_donnees_exemple.py` | Génère des données **synthétiques** pour tester le pipeline |
| `data/chantiers_exemple.csv` | Une ligne par chantier : données de l'annonce + coût total TVAC |
| `data/postes_exemple.csv` | Une ligne par poste de travaux : quantité, unité, gamme, coût TVAC |
| `rapport_regression_travaux.md` | Rapport généré (coefficients, qualité, exemple) |
| `coefficients_travaux.csv` | Coefficients de tous les modèles |

## Utilisation

```bash
pip install numpy pandas
python regression_travaux.py                      # estimation + rapport
python regression_travaux.py --predire surface=130 etat="À rénover" peb_avant=F peb_apres=C facades=3 annee=1930 gamme=standard
python regression_travaux.py --chantiers mes_chantiers.csv --postes mes_postes.csv   # données réelles
```

## Remplacer les données d'exemple par des données réelles

Conserver les mêmes colonnes que les fichiers d'exemple et saisir, pour chaque chantier réalisé ou chiffré, les **coûts TVAC réels** (factures, sinon devis acceptés), actualisés à la date du jour. Valeurs attendues : `etat_immoweb` ∈ {À rafraîchir, À rénover, À restaurer} ; `gamme` ∈ {eco, standard, premium} ; classes PEB A++ à G.
