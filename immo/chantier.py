"""Estimation détaillée des travaux, composée poste par poste (cahier des charges §5.4.1, D15 à D22).

Le catalogue (data/catalogue_travaux.csv, Annexe A) donne pour chaque poste une fourchette de prix
unitaires HTVA, le taux de TVA et une règle de quantité proposée à partir de l'annonce. L'utilisateur
coche des postes, ajuste quantités et niveaux de prix (ou saisit le prix d'un devis) ; le total TVAC
et la durée alimentent le modèle financier.
"""
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from immo import parametres

CATALOGUE = Path(__file__).resolve().parents[1] / "data" / "catalogue_travaux.csv"
NIVEAUX = {"bas": "Bas", "moyen": "Moyen", "haut": "Haut"}
MODELES = {
    "rafraichissement": "Rafraîchissement",
    "renovation_moyenne": "Rénovation moyenne",
    "renovation_lourde": "Rénovation lourde",
    "renovation_energetique": "Rénovation énergétique",
}
DUREE_MODELE_MOIS = {"rafraichissement": 1, "renovation_moyenne": 3, "renovation_lourde": 6, "renovation_energetique": 3}


@lru_cache(maxsize=2)
def _catalogue(chemin: str) -> pd.DataFrame:
    df = pd.read_csv(chemin)
    df["prix_moyen"] = (df["prix_bas"] + df["prix_haut"]) / 2
    df["modeles"] = df["modeles"].fillna("")
    return df


def catalogue(chemin=CATALOGUE) -> pd.DataFrame:
    return _catalogue(str(chemin)).copy()


def _nombre(v, defaut=None):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return defaut


def quantite_proposee(regle, bien: dict):
    """Quantité proposée par la règle du catalogue ; None si le poste est « à mesurer »."""
    sh = _nombre(bien.get("surface_habitable"))
    etages = max(1.0, _nombre(bien.get("nb_etages"), 2) or 2)
    regle = str(regle or "").strip()
    if regle == "a_mesurer" or not regle:
        return None
    if regle == "1":
        return 1.0
    if regle == "salles_eau":
        return max(1.0, _nombre(bien.get("salles_de_bain"), 1) or 1)
    if regle == "amiante":
        annee = _nombre(bien.get("annee_construction"))
        return 1.0 if annee is None or annee < 2001 else 0.0
    if sh is None:
        return None
    if regle == "conteneur":
        return float(max(1, math.ceil(sh / 50)))
    if regle == "toit":
        return round(sh / etages * 1.3)
    if regle == "rdc":
        return round(sh / etages)
    if regle == "SH":
        return round(sh)
    if regle.startswith("SH*"):
        return round(sh * float(regle[3:]), 1)
    if regle.startswith("SH/"):
        return float(max(1, round(sh / float(regle[3:]))))
    raise ValueError(f"Règle de quantité inconnue : {regle}")


def ligne_catalogue(code, bien, niveau="moyen", cat=None):
    cat = catalogue() if cat is None else cat
    r = cat[cat["code"] == code].iloc[0]
    q = quantite_proposee(r["quantite"], bien)
    return {"code": code, "categorie": r["categorie"], "poste": r["poste"], "unite": r["unite"],
            "quantite": q if q is not None else 0.0, "a_mesurer": q is None, "niveau": niveau,
            "prix_saisi": None, "tva": float(r["tva"])}


def appliquer_modele(modele, bien, cat=None):
    cat = catalogue() if cat is None else cat
    codes = [c for c, m in zip(cat["code"], cat["modeles"]) if modele in m.split(",")]
    return {"lignes": [ligne_catalogue(c, bien, cat=cat) for c in codes],
            "imprevus": parametres.charger()["travaux"]["imprevus"].get(modele, 0.15),
            "duree_travaux_mois": DUREE_MODELE_MOIS.get(modele, 3), "modele": modele}


def prix_unitaire(ligne, cat=None):
    if ligne.get("prix_saisi") not in (None, ""):
        return float(ligne["prix_saisi"])
    if not ligne.get("code"):                 # poste libre sans prix
        return 0.0
    cat = catalogue() if cat is None else cat
    r = cat[cat["code"] == ligne["code"]]
    if r.empty:
        return 0.0
    return float(r.iloc[0][{"bas": "prix_bas", "haut": "prix_haut"}.get(ligne.get("niveau"), "prix_moyen")])


def calculer(config: dict, cat=None) -> dict:
    """Détail par ligne, sous-totaux par catégorie et totaux (HTVA, TVA, TVAC, imprévus)."""
    cat = catalogue() if cat is None else cat
    lignes = []
    for l in config.get("lignes", []):
        pu = prix_unitaire(l, cat)
        q = float(l.get("quantite") or 0)
        htva = pu * q
        tva = htva * float(l.get("tva", 0.06))
        lignes.append({**l, "prix_unitaire": pu, "htva": htva, "tva_montant": tva, "tvac": htva + tva,
                       "origine": "devis" if l.get("prix_saisi") not in (None, "") else
                       ("libre" if not l.get("code") else NIVEAUX.get(l.get("niveau"), "Moyen"))})
    df = pd.DataFrame(lignes)
    htva = float(df["htva"].sum()) if not df.empty else 0.0
    tva = float(df["tva_montant"].sum()) if not df.empty else 0.0
    imprevus_pct = float(config.get("imprevus", 0.15))
    par_categorie = (df.groupby("categorie", sort=False)[["htva", "tvac"]].sum().reset_index()
                     if not df.empty else pd.DataFrame(columns=["categorie", "htva", "tvac"]))
    return {"lignes": df, "par_categorie": par_categorie, "total_htva": htva, "total_tva": tva,
            "total_tvac": htva + tva, "imprevus_pct": imprevus_pct, "imprevus": (htva + tva) * imprevus_pct,
            "total_general": (htva + tva) * (1 + imprevus_pct),
            "duree_travaux_mois": float(config.get("duree_travaux_mois", 3)),
            "postes_a_mesurer": [l["poste"] for l in config.get("lignes", []) if l.get("a_mesurer")
                                 and not float(l.get("quantite") or 0)]}


# ---------------------------------------------------------------- persistance

def lire(con, ident):
    r = con.execute("SELECT configuration FROM travaux_bien WHERE immoweb_id = ?", (str(ident),)).fetchone()
    return json.loads(r[0]) if r else None


def enregistrer(con, ident, config: dict):
    """Enregistre le chantier ; ses totaux remplacent les hypothèses « travaux » saisies auparavant (D21)."""
    con.execute("INSERT OR REPLACE INTO travaux_bien VALUES (?, ?, ?)",
                (str(ident), json.dumps(config, ensure_ascii=False), date.today().isoformat()))
    r = con.execute("SELECT hypotheses FROM hypotheses_operation WHERE immoweb_id = ?", (str(ident),)).fetchone()
    if r:
        h = {k: v for k, v in json.loads(r[0]).items() if k not in ("travaux", "taux_imprevus", "duree_mois")}
        con.execute("UPDATE hypotheses_operation SET hypotheses = ? WHERE immoweb_id = ?",
                    (json.dumps(h, ensure_ascii=False), str(ident)))
    con.commit()


def supprimer(con, ident):
    con.execute("DELETE FROM travaux_bien WHERE immoweb_id = ?", (str(ident),))
    con.commit()


def hypotheses_depuis_chantier(config, p=None):
    """Valeurs reprises par le modèle financier : travaux TVAC hors imprévus, imprévus, durée totale."""
    p = p or parametres.charger()
    c = calculer(config)
    return {"travaux": c["total_tvac"], "taux_imprevus": c["imprevus_pct"],
            "duree_mois": c["duree_travaux_mois"] + p["travaux"].get("delai_revente_mois", 3)}
