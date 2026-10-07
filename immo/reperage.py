"""Repérage des biens sous la valeur du marché — phase 1 (cahier des charges §5.0, module R).

Écart = prix/m² demandé actualisé du bien / référence − 1, la référence étant la médiane (ou la
moyenne) du prix/m² actualisé des biens similaires, ramenés au même état que le bien.
GO si l'écart est inférieur ou égal à −seuil, NO-GO sinon, « Données insuffisantes » si le bien
n'a pas de surface ou s'il a moins de comparables que le minimum.
"""
import math

import pandas as pd

from immo import annonces, parametres

GO, NO_GO, INSUFFISANT = "GO", "NO-GO", "Données insuffisantes"


def _nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def reglages(p=None, **surcharges):
    p = p or parametres.charger()
    r = dict(p["reperage"])
    r.update({k: v for k, v in surcharges.items() if v is not None})
    return r


def reperer_bien(bien: dict, df: pd.DataFrame, p=None, **surcharges) -> dict:
    p = p or parametres.charger()
    r = reglages(p, **surcharges)
    surface, pm2 = bien.get("surface_habitable"), bien.get("prix_m2_actualise")
    vide = {"statut": INSUFFISANT, "ecart": None, "reference_m2": None, "n_comparables": 0}
    if _nan(surface) or not surface or _nan(pm2):
        return {**vide, "raison": "surface habitable inconnue"}
    crit = {k: (None if _nan(bien.get(c)) else bien.get(c)) for k, c in
            [("chambres", "chambres"), ("surface_terrain", "surface_terrain"), ("lat", "latitude"),
             ("lon", "longitude"), ("commune", "commune"), ("facades", "facades")]}
    sel, criteres = annonces.comparables(annonces.base_de_reference(df, bien), surface, exclure_id=bien.get("immoweb_id"),
                                         rayon_km=float(r["rayon_km"]), min_resultats=int(r["min_comparables"]),
                                         **crit)
    sel = sel[sel["prix_m2_actualise"].notna()]
    if len(sel) < int(r["min_comparables"]):
        return {**vide, "n_comparables": len(sel), "raison": f"{len(sel)} comparable(s) seulement", "criteres": criteres}
    coefs = p["estimation"]["coef_etat"]
    cible = coefs.get(bien.get("etat") or "Bon", 1.0)
    ramenes = sel["prix_m2_actualise"] * cible / sel["etat"].map(lambda e: coefs.get(e, 1.0) if e else 1.0)
    reference = float(ramenes.mean() if r["reference"] == "moyenne" else ramenes.median())
    ecart = pm2 / reference - 1
    return {"statut": GO if ecart <= -float(r["seuil"]) + 1e-12 else NO_GO, "ecart": ecart,
            "reference_m2": reference, "n_comparables": len(sel), "criteres": criteres,
            "reference": r["reference"], "seuil": float(r["seuil"])}


def reperer_tous(df: pd.DataFrame, p=None, **surcharges) -> pd.DataFrame:
    """Statut de repérage de chaque maison du tableau des annonces."""
    p = p or parametres.charger()
    utiles = ["immoweb_id", "type_bien", "prix_actuel", "surface_habitable", "prix_m2_actualise", "prix_actualise",
              "latitude", "longitude", "commune", "chambres", "surface_terrain", "facades", "etat", "source"]
    leger = df[[c for c in utiles if c in df.columns]]
    lignes = []
    for b in leger.to_dict("records"):
        res = reperer_bien(b, leger, p, **surcharges)
        lignes.append({"immoweb_id": b["immoweb_id"], "reperage": res["statut"], "ecart_reference": res["ecart"],
                       "reference_m2": res["reference_m2"], "n_comparables": res["n_comparables"]})
    return pd.DataFrame(lignes, columns=["immoweb_id", "reperage", "ecart_reference", "reference_m2", "n_comparables"])
