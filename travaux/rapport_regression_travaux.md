# Régression linéaire — estimation du coût des travaux

Source des données : `chantiers_exemple.csv`

> ⚠️ **Données synthétiques** : tant que les fichiers d'exemple sont utilisés, les coefficients ne font que retrouver les hypothèses de prix du générateur (`generer_donnees_exemple.py`). Ils ne deviennent informatifs qu'une fois alimentés par les **devis et factures réels** des chantiers (même format CSV).

## 1. Modèle « annonce » — analyse préliminaire

Coût total des travaux TVAC expliqué par les seules données de l'annonce Immoweb (référence : état « À rafraîchir », gamme standard).

```
Coût = β0 + β1·surface + β2·[À rénover] + β3·[À restaurer] + β4·saut_classes_PEB
     + β5·façades + β6·[avant 1945] + β7·[gamme éco] + β8·[gamme premium] + ε
```

n = 150 · R² = 0,609 · R² ajusté = 0,587 · RMSE = 12 139 € · MAE = 9 249 € · **validation croisée 5 plis : MAE = 10 067 €, MAPE = 26,4 %**

| Variable | Coefficient | Erreur type | t |
|---|---:|---:|---:|
| Constante (€) | -7 326 | 6 878 | -1,1 |
| Surface habitable (€/m²) | 198 | 34 | 5,8 |
| État « À rénover » vs « À rafraîchir » (€) | 18 146 | 2 372 | 7,6 |
| État « À restaurer » vs « À rafraîchir » (€) | 32 872 | 2 931 | 11,2 |
| Par classe PEB gagnée (€) | 9 511 | 1 317 | 7,2 |
| Par façade supplémentaire (€) | 28 | 1 376 | 0,0 |
| Bâti d'avant 1945 (€) | 699 | 2 101 | 0,3 |
| Gamme éco vs standard (€) | -5 787 | 2 271 | -2,5 |
| Gamme premium vs standard (€) | 11 998 | 3 367 | 3,6 |

**Application à l'exemple du cahier des charges** (maison 3 façades, 130 m², 1930, « À rénover », PEB F → C, gamme standard) :

- Estimation centrale : **65 827 €**
- Intervalle de prédiction 80 % (P10 – P90) : 49 426 € – **82 227 €**
- La borne P90 alimente le **scénario prudent** (au lieu d'un pourcentage d'imprévus fixe).

## 2. Modèles par poste — après visite

```
Coût_poste = coût_fixe + quantité × (prix_unitaire + ajust_éco·[éco] + ajust_premium·[premium] + ajust_ancien·[avant 1945]) + ε
```

| Poste | Unité | n | Coût fixe (€) | Prix unitaire (€/unité) | Ajust. éco | Ajust. premium | Ajust. avant 1945 | R² | MAPE (val. croisée) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| chassis | pièce | 97 | -122 | 962 | -154 | 203 | 36 | 0,851 | 10,4 % |
| chauffage | m² habitable | 93 | 2 987 | 53 | -9 | 22 | 2 | 0,796 | 9,3 % |
| cuisine | ml cuisine | 111 | 1 127 | 1 301 | -223 | 330 | -16 | 0,782 | 11,1 % |
| electricite | m² habitable | 110 | 1 781 | 62 | -13 | 25 | 10 | 0,872 | 8,9 % |
| humidite | ml mur | 58 | 775 | 126 | -25 | 51 | 20 | 0,811 | 12,9 % |
| isolation_toiture | m² toiture | 69 | 133 | 58 | -7 | 12 | 1 | 0,834 | 11,1 % |
| peinture_sols | m² habitable | 150 | 471 | 58 | -9 | 13 | 4 | 0,866 | 9,1 % |
| salle_de_bain | m² SDB | 108 | 3 639 | 874 | -194 | 370 | 79 | 0,714 | 9,4 % |
| toiture | m² toiture | 48 | 3 440 | 192 | -46 | 52 | 16 | 0,900 | 9,4 % |

Lecture : pour la toiture, le coût estimé = coût fixe + quantité (m²) × prix unitaire, le prix unitaire étant corrigé de l'ajustement correspondant pour une gamme éco / premium ou un bâti d'avant 1945.

## 3. Utilisation et limites

- **Mise à jour** : relancer le script après chaque chantier clôturé (factures réelles) ; un poste n'est modélisé qu'à partir de 15 observations.
- **Contrôle** : un coefficient dont |t| < 2 n'est pas significatif ; un R² faible ou une MAPE > 25 % signale qu'il faut affiner les variables (ex. état de la charpente, accessibilité).
- **Hétéroscédasticité** : l'erreur croît avec la taille du chantier ; si besoin, estimer en coût par m² ou en logarithme.
- **TVA** : coûts TVAC à 6 % ; corriger les observations facturées à 21 % avant estimation.
- **Inflation** : actualiser les coûts historiques (indice ABEX) avant estimation.
