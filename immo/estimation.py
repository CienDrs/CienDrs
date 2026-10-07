"""Estimation de la valeur en l'état et après travaux à partir des comparables (B2-B8, B13-B16, E1-E3).

Chaque comparable est ramené à l'état visé par les coefficients d'état (paramètres), corrigé de la
marge de négociation (prix demandé -> prix de vente), puis on prend les quartiles du prix/m².
"""
import math

import numpy as np

from immo import annonces, parametres

ETATS_RENOVES = ("Comme neuf", "Fraîchement rénové")


def _nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _criteres(bien):
    c = {"chambres": bien.get("chambres"), "surface_terrain": bien.get("surface_terrain"),
         "lat": bien.get("latitude"), "lon": bien.get("longitude"), "commune": bien.get("commune"),
         "facades": bien.get("facades")}
    return {k: (None if _nan(v) else v) for k, v in c.items()}


def confiance(n, dispersion):
    if n < 5:
        return "faible"
    if n >= 10 and dispersion is not None and dispersion < 0.30:
        return "élevé"
    return "moyen"


def estimer_valeur(bien: dict, df, etat_cible=None, p=None):
    """Valeur basse / centrale / haute du bien dans l'état `etat_cible` (par défaut : son état actuel)."""
    p = p or parametres.charger()
    pe = p["estimation"]
    surface = bien.get("surface_habitable")
    if _nan(surface) or not surface:
        return {"disponible": False, "raison": "surface habitable inconnue"}
    etat_cible = etat_cible or bien.get("etat") or "Bon"
    coefs = pe["coef_etat"]
    sel, criteres = annonces.comparables(df, surface, exclure_id=bien.get("immoweb_id"), **_criteres(bien))
    sel = sel[sel["prix_m2_actualise"].notna()]
    if sel.empty:
        return {"disponible": False, "raison": "aucun comparable", "criteres": criteres, "n": 0}
    coef_cible = coefs.get(etat_cible, 1.0)
    norm = sel["prix_m2_actualise"] * coef_cible / sel["etat"].map(lambda e: coefs.get(e, 1.0) if e else 1.0)
    norm = norm * (1 - pe["marge_negociation"])
    q1, q3 = norm.quantile(0.25), norm.quantile(0.75)
    garde = norm.between(q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))   # valeurs aberrantes (IQR)
    norm, sel = norm[garde], sel[garde]
    p25, p50, p75 = (float(norm.quantile(q)) for q in (0.25, 0.5, 0.75))
    dispersion = (p75 - p25) / p50 if p50 else None
    meme_etat = int((sel["etat"] == etat_cible).sum())
    return {
        "disponible": True, "etat": etat_cible, "n": len(sel), "n_meme_etat": meme_etat, "criteres": criteres,
        "prix_m2": {"bas": p25, "central": p50, "haut": p75},
        "basse": p25 * surface, "centrale": p50 * surface, "haute": p75 * surface,
        "dispersion": dispersion, "confiance": confiance(len(sel), dispersion),
        "p90_prix_secteur": float(np.percentile(sel["prix_actualise"], 90)),
        "comparables": sel.assign(prix_m2_ramene=norm),
    }


def estimer_valeurs(bien: dict, df, p=None):
    """Valeur en l'état (état actuel) et valeur après travaux (état « Fraîchement rénové »)."""
    p = p or parametres.charger()
    en_l_etat = estimer_valeur(bien, df, bien.get("etat"), p)
    apres = estimer_valeur(bien, df, "Fraîchement rénové", p)
    if apres.get("disponible"):
        apres["alerte_sur_renovation"] = apres["centrale"] > apres["p90_prix_secteur"]
    return en_l_etat, apres
