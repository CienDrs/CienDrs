"""Régression linéaire (moindres carrés ordinaires) sur le coût des travaux de rénovation.

Deux niveaux de modèles (cf. cahier des charges, module D) :

1. Modèle « annonce » (analyse préliminaire) : coût total du chantier expliqué
   uniquement par les données disponibles dans l'annonce Immoweb
   (surface, état, saut de classe PEB visé, façades, année, gamme de finition).

2. Modèles « par poste » (après visite) : pour chaque poste de travaux,
   coût = coût fixe + prix unitaire × quantité, avec ajustements du prix unitaire
   selon la gamme de finition et le bâti d'avant 1945.

Usage :
  python regression_travaux.py                       # estime les modèles, écrit le rapport
  python regression_travaux.py --chantiers X.csv --postes Y.csv
  python regression_travaux.py --predire surface=130 etat="À rénover" peb_avant=F \
         peb_apres=C facades=3 annee=1930 gamme=standard

Dépendances : numpy, pandas.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).parent
PEB = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]
Z_80 = 1.2816  # quantile normal pour un intervalle de prédiction à 80 % (P10 – P90)
MIN_OBS_POSTE = 15
N_PLIS = 5


# --------------------------------------------------------------------------- OLS

class MCO:
    """Régression linéaire par moindres carrés ordinaires, avec statistiques usuelles."""

    def __init__(self, X: pd.DataFrame, y: pd.Series):
        self.noms = list(X.columns)
        Xv, yv = X.to_numpy(float), y.to_numpy(float)
        self.n, self.k = Xv.shape
        self.xtx_inv = np.linalg.pinv(Xv.T @ Xv)
        self.beta = self.xtx_inv @ Xv.T @ yv
        residus = yv - Xv @ self.beta
        ddl = max(self.n - self.k, 1)
        self.s2 = residus @ residus / ddl
        self.se = np.sqrt(np.diag(self.xtx_inv) * self.s2)
        sst = ((yv - yv.mean()) ** 2).sum()
        self.r2 = 1 - (residus @ residus) / sst
        self.r2_ajuste = 1 - (1 - self.r2) * (self.n - 1) / ddl
        self.rmse = np.sqrt((residus ** 2).mean())
        self.mae = np.abs(residus).mean()
        self.mape = np.mean(np.abs(residus) / np.abs(yv))

    def predire(self, X: pd.DataFrame):
        """Retourne (prédiction, borne basse P10, borne haute P90)."""
        Xv = X[self.noms].to_numpy(float)
        pred = Xv @ self.beta
        se_pred = np.sqrt(self.s2 * (1 + np.einsum("ij,jk,ik->i", Xv, self.xtx_inv, Xv)))
        return pred, pred - Z_80 * se_pred, pred + Z_80 * se_pred

    def tableau(self) -> pd.DataFrame:
        return pd.DataFrame({"coefficient": self.beta, "erreur_type": self.se,
                             "t": self.beta / np.where(self.se > 0, self.se, np.nan)},
                            index=self.noms)


def validation_croisee(X: pd.DataFrame, y: pd.Series, n_plis=N_PLIS, seed=0):
    """MAE et MAPE hors échantillon par validation croisée en k plis."""
    idx = np.random.default_rng(seed).permutation(len(y))
    erreurs, relatives = [], []
    for pli in np.array_split(idx, n_plis):
        apprentissage = np.setdiff1d(idx, pli)
        m = MCO(X.iloc[apprentissage], y.iloc[apprentissage])
        pred, _, _ = m.predire(X.iloc[pli])
        e = np.abs(y.iloc[pli].to_numpy() - pred)
        erreurs.extend(e)
        relatives.extend(e / y.iloc[pli].to_numpy())
    return float(np.mean(erreurs)), float(np.mean(relatives))


# ----------------------------------------------------------- variables explicatives

def saut_peb(avant, apres):
    return pd.Series(avant).map(PEB.index).to_numpy() - pd.Series(apres).map(PEB.index).to_numpy()


def variables_annonce(df: pd.DataFrame) -> pd.DataFrame:
    """Variables du modèle « annonce » (référence : À rafraîchir, gamme standard)."""
    return pd.DataFrame({
        "constante": 1.0,
        "surface_habitable": df["surface_habitable"],
        "etat_a_renover": (df["etat_immoweb"] == "À rénover").astype(float),
        "etat_a_restaurer": (df["etat_immoweb"] == "À restaurer").astype(float),
        "saut_classes_peb": saut_peb(df["peb_avant"], df["peb_apres"]),
        "facades": df["facades"],
        "avant_1945": (df["annee_construction"] < 1945).astype(float),
        "gamme_eco": (df["gamme"] == "eco").astype(float),
        "gamme_premium": (df["gamme"] == "premium").astype(float),
    }, index=df.index)


def variables_poste(df: pd.DataFrame) -> pd.DataFrame:
    """coût = fixe + quantité × (prix unitaire + ajustements gamme / bâti ancien)."""
    q = df["quantite"].astype(float)
    return pd.DataFrame({
        "cout_fixe": 1.0,
        "prix_unitaire": q,
        "ajust_pu_eco": q * (df["gamme"] == "eco"),
        "ajust_pu_premium": q * (df["gamme"] == "premium"),
        "ajust_pu_avant_1945": q * (df["annee_construction"] < 1945),
    }, index=df.index)


# ------------------------------------------------------------------- estimation

def estimer_modele_annonce(chantiers: pd.DataFrame):
    X, y = variables_annonce(chantiers), chantiers["cout_total_ttc"]
    modele = MCO(X, y)
    modele.cv_mae, modele.cv_mape = validation_croisee(X, y)
    return modele


def estimer_modeles_postes(postes: pd.DataFrame):
    modeles = {}
    for poste, groupe in postes.groupby("poste"):
        if len(groupe) < MIN_OBS_POSTE:
            continue
        X, y = variables_poste(groupe), groupe["cout_ttc"]
        # retire les ajustements sans aucune observation (colonne nulle)
        X = X.loc[:, (X != 0).any() | (X.columns == "cout_fixe")]
        m = MCO(X, y)
        m.cv_mae, m.cv_mape = validation_croisee(X, y)
        m.unite = groupe["unite"].iloc[0]
        modeles[poste] = m
    return modeles


# ----------------------------------------------------------------------- rapport

def fmt(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",") if pd.notna(x) else "—"


def tableau_md(modele: MCO, libelles=None) -> str:
    lignes = ["| Variable | Coefficient | Erreur type | t |", "|---|---:|---:|---:|"]
    for nom, r in modele.tableau().iterrows():
        nom_affiche = (libelles or {}).get(nom, nom)
        lignes.append(f"| {nom_affiche} | {fmt(r.coefficient)} | {fmt(r.erreur_type)} | {fmt(r.t, 1)} |")
    return "\n".join(lignes)


def qualite_md(m: MCO) -> str:
    return (f"n = {m.n} · R² = {fmt(m.r2, 3)} · R² ajusté = {fmt(m.r2_ajuste, 3)} · "
            f"RMSE = {fmt(m.rmse)} € · MAE = {fmt(m.mae)} € · "
            f"**validation croisée {N_PLIS} plis : MAE = {fmt(m.cv_mae)} €, MAPE = {fmt(100 * m.cv_mape, 1)} %**")


LIBELLES_ANNONCE = {
    "constante": "Constante (€)",
    "surface_habitable": "Surface habitable (€/m²)",
    "etat_a_renover": "État « À rénover » vs « À rafraîchir » (€)",
    "etat_a_restaurer": "État « À restaurer » vs « À rafraîchir » (€)",
    "saut_classes_peb": "Par classe PEB gagnée (€)",
    "facades": "Par façade supplémentaire (€)",
    "avant_1945": "Bâti d'avant 1945 (€)",
    "gamme_eco": "Gamme éco vs standard (€)",
    "gamme_premium": "Gamme premium vs standard (€)",
}

EXEMPLE = dict(surface=130, etat="À rénover", peb_avant="F", peb_apres="C",
               facades=3, annee=1930, gamme="standard")


def ecrire_rapport(modele_annonce, modeles_postes, source, chemin: Path):
    ex = prediction_annonce(modele_annonce, **EXEMPLE)
    lignes = [
        "# Régression linéaire — estimation du coût des travaux",
        "",
        f"Source des données : `{source}`",
        "",
        "> ⚠️ **Données synthétiques** : tant que les fichiers d'exemple sont utilisés, les coefficients "
        "ne font que retrouver les hypothèses de prix du générateur (`generer_donnees_exemple.py`). "
        "Ils ne deviennent informatifs qu'une fois alimentés par les **devis et factures réels** "
        "des chantiers (même format CSV).",
        "",
        "## 1. Modèle « annonce » — analyse préliminaire",
        "",
        "Coût total des travaux TVAC expliqué par les seules données de l'annonce Immoweb "
        "(référence : état « À rafraîchir », gamme standard).",
        "",
        "```",
        "Coût = β0 + β1·surface + β2·[À rénover] + β3·[À restaurer] + β4·saut_classes_PEB",
        "     + β5·façades + β6·[avant 1945] + β7·[gamme éco] + β8·[gamme premium] + ε",
        "```",
        "",
        qualite_md(modele_annonce),
        "",
        tableau_md(modele_annonce, LIBELLES_ANNONCE),
        "",
        "**Application à l'exemple du cahier des charges** (maison 3 façades, 130 m², 1930, "
        "« À rénover », PEB F → C, gamme standard) :",
        "",
        f"- Estimation centrale : **{fmt(ex[0])} €**",
        f"- Intervalle de prédiction 80 % (P10 – P90) : {fmt(ex[1])} € – **{fmt(ex[2])} €**",
        "- La borne P90 alimente le **scénario prudent** (au lieu d'un pourcentage d'imprévus fixe).",
        "",
        "## 2. Modèles par poste — après visite",
        "",
        "```",
        "Coût_poste = coût_fixe + quantité × (prix_unitaire + ajust_éco·[éco] + ajust_premium·[premium]"
        " + ajust_ancien·[avant 1945]) + ε",
        "```",
        "",
        "| Poste | Unité | n | Coût fixe (€) | Prix unitaire (€/unité) | Ajust. éco | Ajust. premium "
        "| Ajust. avant 1945 | R² | MAPE (val. croisée) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for poste, m in sorted(modeles_postes.items()):
        c = m.tableau()["coefficient"]
        lignes.append(
            f"| {poste} | {m.unite} | {m.n} | {fmt(c.get('cout_fixe'))} | {fmt(c.get('prix_unitaire'))} "
            f"| {fmt(c.get('ajust_pu_eco'))} | {fmt(c.get('ajust_pu_premium'))} "
            f"| {fmt(c.get('ajust_pu_avant_1945'))} | {fmt(m.r2, 3)} | {fmt(100 * m.cv_mape, 1)} % |")
    lignes += [
        "",
        "Lecture : pour la toiture, le coût estimé = coût fixe + quantité (m²) × prix unitaire, "
        "le prix unitaire étant corrigé de l'ajustement correspondant pour une gamme éco / premium "
        "ou un bâti d'avant 1945.",
        "",
        "## 3. Utilisation et limites",
        "",
        "- **Mise à jour** : relancer le script après chaque chantier clôturé (factures réelles) ; "
        f"un poste n'est modélisé qu'à partir de {MIN_OBS_POSTE} observations.",
        "- **Contrôle** : un coefficient dont |t| < 2 n'est pas significatif ; un R² faible ou une MAPE "
        "> 25 % signale qu'il faut affiner les variables (ex. état de la charpente, accessibilité).",
        "- **Hétéroscédasticité** : l'erreur croît avec la taille du chantier ; si besoin, estimer en "
        "coût par m² ou en logarithme.",
        "- **TVA** : coûts TVAC à 6 % ; corriger les observations facturées à 21 % avant estimation.",
        "- **Inflation** : actualiser les coûts historiques (indice ABEX) avant estimation.",
        "",
    ]
    chemin.write_text("\n".join(lignes), encoding="utf-8")


# --------------------------------------------------------------------- prédiction

def prediction_annonce(modele, surface, etat, peb_avant, peb_apres, facades, annee, gamme):
    df = pd.DataFrame([dict(surface_habitable=float(surface), etat_immoweb=etat, peb_avant=peb_avant,
                            peb_apres=peb_apres, facades=int(facades),
                            annee_construction=int(annee), gamme=gamme)])
    pred, bas, haut = modele.predire(variables_annonce(df))
    return float(pred[0]), float(bas[0]), float(haut[0])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chantiers", default=ICI / "data" / "chantiers_exemple.csv")
    p.add_argument("--postes", default=ICI / "data" / "postes_exemple.csv")
    p.add_argument("--rapport", default=ICI / "rapport_regression_travaux.md")
    p.add_argument("--predire", nargs="+", metavar="CLE=VALEUR",
                   help="surface etat peb_avant peb_apres facades annee gamme")
    args = p.parse_args()

    chantiers, postes = pd.read_csv(args.chantiers), pd.read_csv(args.postes)
    modele_annonce = estimer_modele_annonce(chantiers)
    modeles_postes = estimer_modeles_postes(postes)

    if args.predire:
        params = {**EXEMPLE, **dict(kv.split("=", 1) for kv in args.predire)}
        pred, bas, haut = prediction_annonce(modele_annonce, **params)
        print(f"Coût travaux estimé : {fmt(pred)} € (P10 {fmt(bas)} € – P90 {fmt(haut)} €)")
        return

    ecrire_rapport(modele_annonce, modeles_postes, Path(args.chantiers).name, Path(args.rapport))
    pd.concat({"annonce": modele_annonce.tableau(),
               **{f"poste:{k}": m.tableau() for k, m in modeles_postes.items()}}) \
        .to_csv(ICI / "coefficients_travaux.csv", index_label=["modele", "variable"])
    print(qualite_md(modele_annonce))
    print(f"Rapport écrit dans {args.rapport}")


if __name__ == "__main__":
    main()
