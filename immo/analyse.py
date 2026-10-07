"""Assemble l'analyse complète d'un bien : indicateurs de prix, estimations, travaux, risques,
modèle financier et décision (fiche du bien, exigences A6, H2)."""
import json
import math
from datetime import date

from immo import annonces, estimation, finance, geo, parametres, statbel, travaux

VERSION_MODELE = "v1-comparables-ratios"


def _propre(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else v


def charger_bien(con, ident, aujourd_hui=None):
    df = annonces.tableau_annonces(con, aujourd_hui)
    ligne = df[df["immoweb_id"] == str(ident)]
    if ligne.empty:
        raise KeyError(f"Bien {ident} introuvable")
    bien = {k: _propre(v) for k, v in ligne.iloc[0].to_dict().items()}
    return bien, df


def nouvel_identifiant_manuel(con):
    n = con.execute("SELECT COUNT(*) FROM annonces WHERE immoweb_id LIKE 'M%'").fetchone()[0]
    while True:
        n += 1
        ident = f"M{n:04d}"
        if not con.execute("SELECT 1 FROM annonces WHERE immoweb_id = ?", (ident,)).fetchone():
            return ident


# ------------------------------------------------------------- hypothèses

def lire_hypotheses(con, ident):
    r = con.execute("SELECT hypotheses FROM hypotheses_operation WHERE immoweb_id = ?", (str(ident),)).fetchone()
    return json.loads(r[0]) if r else {}


def enregistrer_hypotheses(con, ident, hypotheses: dict):
    con.execute("INSERT OR REPLACE INTO hypotheses_operation VALUES (?, ?, ?)",
                (str(ident), json.dumps(hypotheses, ensure_ascii=False), date.today().isoformat()))
    con.commit()


def risques_manuels(con, ident):
    return geo.lire(con, ident).get("risques_manuels", {}).get("valeur") or []


def risques_leves(con, ident):
    """Risques automatiques vérifiés par l'utilisateur et jugés non bloquants (clés des couches)."""
    return geo.lire(con, ident).get("risques_leves", {}).get("valeur") or []


def enregistrer_risques_leves(con, ident, cles):
    geo.enregistrer(con, ident, "risques_leves", list(cles), "Vérification utilisateur")


def enregistrer_risques_manuels(con, ident, liste):
    geo.enregistrer(con, ident, "risques_manuels", list(liste), "Saisie utilisateur (WalOnMap / visite)")


# ---------------------------------------------------------------- analyse

def analyser(con, ident, p=None, surcharges=None, aujourd_hui=None):
    p = p or parametres.charger()
    bien, df = charger_bien(con, ident, aujourd_hui)
    surface = bien.get("surface_habitable")
    prix = bien.get("prix_actuel")
    res = {"bien": bien, "date": aujourd_hui or date.today().isoformat(), "version_modele": VERSION_MODELE}

    # Indicateurs de prix
    res["prix_m2"] = prix / surface if prix and surface else None
    res["statbel"] = statbel.ecart_au_median(con, prix, bien.get("code_postal"), bien.get("commune"),
                                             bien.get("facades"))
    en_l_etat, apres = estimation.estimer_valeurs(bien, df, p)
    res["valeur_en_l_etat"], res["valeur_apres_travaux"] = en_l_etat, apres
    if en_l_etat.get("disponible") and res["prix_m2"]:
        brut = en_l_etat["comparables"]["prix_m2_actualise"]
        res["position_prix_m2"] = {"mediane_comparables": float(brut.median()),
                                   "ecart": res["prix_m2"] / float(brut.median()) - 1,
                                   "percentile": float((brut < res["prix_m2"]).mean() * 100)}

    # Travaux
    cible = p["estimation"]["peb_classe_cible_defaut"]
    res["travaux"] = travaux.estimer(surface, bien.get("etat"), bien.get("peb_lettre"), cible, p=p)

    # Risques (automatiques + saisis)
    enrich = geo.lire(con, ident)
    auto = (enrich.get("risques_auto") or {}).get("valeur") or {}
    manuels = risques_manuels(con, ident)
    res["risques"] = {"auto": auto, "auto_date": (enrich.get("risques_auto") or {}).get("date"),
                      "manuels": manuels}
    leves = risques_leves(con, ident)
    res["risques"]["leves"] = leves
    bloquants = [r["libelle"] for cle, r in auto.items() if r.get("bloquant") and cle not in leves] + list(manuels)

    # Hypothèses : valeurs par défaut < hypothèses enregistrées < surcharges de l'écran
    defaut = {
        "prix_achat": prix,
        "valeur_en_l_etat": en_l_etat.get("centrale"),
        "travaux": res["travaux"].get("central"),
        "niveau_renovation": res["travaux"]["niveau"] if res["travaux"]["niveau"] != "aucun" else "rafraichissement",
        "taux_imprevus": res["travaux"]["taux_imprevus"],
        "prix_revente": apres.get("centrale"),
        "duree_mois": p["travaux"]["duree_defaut_mois"],
        "regime": p["acquisition"]["regime"],
        "revenu_cadastral": bien.get("revenu_cadastral"),
        "portage_mensuel": None,
        "vente_par_agence": True,
    }
    hyp = {**defaut, **{k: v for k, v in lire_hypotheses(con, ident).items() if v is not None},
           **{k: v for k, v in (surcharges or {}).items() if v is not None}}
    res["hypotheses"], res["hypotheses_defaut"] = hyp, defaut

    manquants = [lib for cle, lib in [("prix_achat", "prix"), ("travaux", "coût des travaux (surface ?)"),
                                      ("prix_revente", "prix de revente (comparables rénovés ?)")]
                 if not hyp.get(cle)]
    res["manquants_decision"] = manquants
    res["champs_manquants"] = annonces.champs_manquants(con, ident)
    distance = bien.get("distance_mons_km")
    if distance is None and bien.get("latitude") is not None:
        distance = geo.distance_centre(bien["latitude"], bien["longitude"], p)
    if not manquants:
        h = finance.Hypotheses(**{k: hyp[k] for k in finance.Hypotheses.__dataclass_fields__ if k in hyp})
        ctx = finance.Contexte(en_l_etat.get("confiance"), bloquants, distance)
        res["decision"] = finance.decider(h, ctx, p)
    else:
        res["decision"] = None
    return res


def resume(res):
    """Version sérialisable de l'analyse (sans tableaux de comparables) pour l'historique."""
    def nettoyer(v):
        if isinstance(v, dict):
            return {k: nettoyer(x) for k, x in v.items() if k != "comparables"}
        if isinstance(v, list):
            return [nettoyer(x) for x in v]
        if isinstance(v, float) and math.isnan(v):
            return None
        return v if isinstance(v, (str, int, float, bool, type(None))) else str(v)
    return nettoyer({k: v for k, v in res.items() if k != "bien"} | {"immoweb_id": res["bien"]["immoweb_id"]})


def enregistrer_analyse(con, res):
    con.execute("INSERT OR REPLACE INTO analyses VALUES (?, ?, ?, ?)",
                (res["bien"]["immoweb_id"], res["date"], res["version_modele"],
                 json.dumps(resume(res), ensure_ascii=False)))
    con.commit()
