"""Modèle financier d'une opération achat – rénovation – revente (cahier des charges §1.3, §5.3, §5.6, §5.7).

Plus-value nette = Prix de revente − Frais de revente − Prix d'achat − Frais d'acquisition
                   − Travaux TVAC (imprévus compris) − Frais de portage
"""
from dataclasses import asdict, dataclass, field

from immo import parametres

SCENARIOS = ("prudent", "central", "optimiste")
GO, GO_SOUS_CONDITIONS, NO_GO = "GO", "GO SOUS CONDITIONS", "NO-GO"


@dataclass
class Hypotheses:
    prix_achat: float
    travaux: float                       # coût des travaux TVAC, hors imprévus
    prix_revente: float                  # prix de revente après travaux
    valeur_en_l_etat: float | None = None
    taux_imprevus: float | None = None   # None : selon le niveau de rénovation (paramètres)
    niveau_renovation: str = "renovation_moyenne"
    duree_mois: float | None = None      # durée totale de l'opération (achat -> revente)
    regime: str | None = None            # "personne_physique" ou "marchand_de_biens"
    portage_mensuel: float | None = None # forfait mensuel ; None : calcul détaillé
    revenu_cadastral: float | None = None
    vente_par_agence: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass
class Contexte:
    """Éléments de décision qui ne sont pas financiers (règles R4 à R6)."""
    confiance_estimation: str | None = None     # "faible", "moyen", "élevé"
    risques_bloquants: list = field(default_factory=list)
    distance_km: float | None = None


# ----------------------------------------------------------------- composantes

def taux_droits(p, regime):
    return p["acquisition"]["droits_marchand_de_biens" if regime == "marchand_de_biens"
                            else "droits_personne_physique"]


def frais_acquisition(prix, p, regime):
    droits = prix * taux_droits(p, regime)
    notaire = p["acquisition"]["frais_notaire_fixes"]
    return {"droits_enregistrement": droits, "frais_notaire": notaire, "total": droits + notaire}


def frais_portage(h: Hypotheses, p, duree, base_financee):
    """Coût de détention pendant `duree` mois (forfait mensuel ou calcul détaillé)."""
    forfait = h.portage_mensuel if h.portage_mensuel is not None else p["portage"].get("portage_mensuel", 0)
    if forfait:
        return {"forfait": forfait * duree, "total": forfait * duree}
    pp = p["portage"]
    emprunt = base_financee * pp["quotite_financee"]
    interets = emprunt * pp["taux_interet"] * duree / 12
    acte_credit = emprunt * pp["frais_acte_credit"]
    precompte = 0.0
    if h.revenu_cadastral:
        precompte = (h.revenu_cadastral * pp["indexation_revenu_cadastral"] * pp["taux_precompte_regional"]
                     * (1 + pp["centimes_additionnels"] / 100) * duree / 12)
    charges = pp["charges_mensuelles"] * duree
    total = interets + acte_credit + precompte + charges
    return {"interets": interets, "acte_credit": acte_credit, "precompte_immobilier": precompte,
            "charges": charges, "total": total}


def frais_revente(prix_revente, p, par_agence=True):
    r = p["revente"]
    agence = prix_revente * r["commission_agence"] * (1 + r["tva_commission"]) if par_agence else 0.0
    return {"agence": agence, "frais_fixes": r["frais_fixes"], "total": agence + r["frais_fixes"]}


def impot(plus_value, p, regime):
    if plus_value <= 0:
        return 0.0
    f = p["fiscalite"]
    if regime == "marchand_de_biens":
        return plus_value * f["taux_isoc"]
    return plus_value * f["taux_plus_value_pp"] * (1 + f["additionnels_communaux"])


# ----------------------------------------------------------------------- bilan

def _resolus(h: Hypotheses, p):
    regime = h.regime or p["acquisition"]["regime"]
    imprevus = h.taux_imprevus if h.taux_imprevus is not None else \
        p["travaux"]["imprevus"].get(h.niveau_renovation, 0.15)
    duree = h.duree_mois if h.duree_mois is not None else p["travaux"]["duree_defaut_mois"]
    return regime, imprevus, duree


def ajustements(p, scenario):
    if scenario == "central":
        return {"revente": 0.0, "travaux": 0.0, "mois": 0}
    return dict(p["scenarios"][scenario])


def bilan(h: Hypotheses, p=None, scenario="central"):
    """Bilan complet de l'opération pour un scénario."""
    p = p or parametres.charger()
    regime, imprevus, duree0 = _resolus(h, p)
    adj = ajustements(p, scenario)
    revente = h.prix_revente * (1 + adj["revente"])
    travaux_hors_imprevus = h.travaux * (1 + adj["travaux"])
    travaux_total = travaux_hors_imprevus * (1 + imprevus)
    duree = max(1, duree0 + adj["mois"])

    acq = frais_acquisition(h.prix_achat, p, regime)
    port = frais_portage(h, p, duree, h.prix_achat + acq["total"] + travaux_total)
    rev = frais_revente(revente, p, h.vente_par_agence)
    revient = h.prix_achat + acq["total"] + travaux_total + port["total"]
    revente_nette = revente - rev["total"]
    plus_value = revente_nette - revient
    imp = impot(plus_value, p, regime)
    return {
        "scenario": scenario, "regime": regime, "duree_mois": duree,
        "prix_achat": h.prix_achat, "frais_acquisition": acq,
        "travaux_hors_imprevus": travaux_hors_imprevus, "imprevus": travaux_total - travaux_hors_imprevus,
        "travaux_total": travaux_total, "portage": port, "prix_revient": revient,
        "prix_revente": revente, "frais_revente": rev, "revente_nette": revente_nette,
        "plus_value": plus_value, "marge_sur_revient": plus_value / revient if revient else None,
        "impot": imp, "plus_value_apres_impot": plus_value - imp,
        "rendement_annualise": (plus_value / revient) * 12 / duree if revient else None,
    }


def prix_achat_maximum(h: Hypotheses, p=None, scenario="prudent", marge=None):
    """Prix d'achat (net vendeur) qui laisse exactement la marge minimale dans le scénario donné.

    Prix_max = (Revente nette − Travaux − Portage − Marge − Frais fixes notaire) / (1 + droits)
    Le portage détaillé dépend du prix (intérêts) : résolution par itérations successives.
    """
    p = p or parametres.charger()
    marge = p["strategie"]["plus_value_min"] if marge is None else marge
    regime = _resolus(h, p)[0]
    prix = h.prix_achat
    for _ in range(50):
        b = bilan(Hypotheses(**{**h.to_dict(), "prix_achat": prix}), p, scenario)
        nouveau = ((b["revente_nette"] - b["travaux_total"] - b["portage"]["total"] - marge
                    - p["acquisition"]["frais_notaire_fixes"]) / (1 + taux_droits(p, regime)))
        if abs(nouveau - prix) < 0.01:
            break
        prix = nouveau
    return max(0.0, nouveau)


# --------------------------------------------------------------------- décision

def decider(h: Hypotheses, ctx: Contexte | None = None, p=None):
    """Applique les règles R1 à R7 et retourne le statut GO / GO SOUS CONDITIONS / NO-GO."""
    p = p or parametres.charger()
    ctx = ctx or Contexte()
    s = p["strategie"]
    bilans = {sc: bilan(h, p, sc) for sc in SCENARIOS}
    prudent, central = bilans["prudent"], bilans["central"]
    plafond_decote = 1 - s["decote_cible"] + s.get("tolerance_decote", 0)
    regles = []

    def regle(code, libelle, ok, obligatoire, detail):
        regles.append({"code": code, "libelle": libelle, "ok": ok, "obligatoire": obligatoire, "detail": detail})

    regle("R1", f"Plus-value nette (prudent) ≥ {s['plus_value_min']:,.0f} €".replace(",", " "),
          prudent["plus_value"] >= s["plus_value_min"], True, f"{prudent['plus_value']:,.0f} €".replace(",", " "))
    if h.valeur_en_l_etat:
        ratio = h.prix_achat / h.valeur_en_l_etat
        regle("R2", f"Prix d'achat ≤ {plafond_decote:.0%} de la valeur en l'état", ratio <= plafond_decote + 1e-9,
              True, f"{ratio:.1%} de la valeur".replace(".", ","))
    else:
        regle("R2", "Prix d'achat ≤ 80 % de la valeur en l'état", None, True, "valeur en l'état inconnue")
    regle("R3", f"Marge (central) ≥ {s['marge_min_pct_revient']:.0%} du prix de revient",
          (central["marge_sur_revient"] or 0) >= s["marge_min_pct_revient"], False,
          f"{(central['marge_sur_revient'] or 0):.1%}".replace(".", ","))
    regle("R4", "Indice de confiance de l'estimation ≥ moyen",
          None if ctx.confiance_estimation is None else ctx.confiance_estimation != "faible", False,
          ctx.confiance_estimation or "non évalué")
    regle("R5", "Aucun risque bloquant", not ctx.risques_bloquants, True,
          ", ".join(ctx.risques_bloquants) or "aucun signalé")
    rayon = p["zone"]["rayon_km"]
    regle("R6", f"Bien dans le rayon de {rayon} km", None if ctx.distance_km is None else ctx.distance_km <= rayon,
          True, "distance inconnue" if ctx.distance_km is None else f"{ctx.distance_km:.1f} km")
    regle("R7", f"Durée totale ≤ {s['duree_max_mois']} mois", central["duree_mois"] <= s["duree_max_mois"], False,
          f"{central['duree_mois']:g} mois")

    if any(r["obligatoire"] and r["ok"] is False for r in regles):
        statut = NO_GO
    elif all(r["ok"] is True for r in regles):
        statut = GO
    else:
        statut = GO_SOUS_CONDITIONS

    prix_max = prix_achat_maximum(h, p, "prudent")
    prix_cible = h.valeur_en_l_etat * (1 - s["decote_cible"]) if h.valeur_en_l_etat else None
    prix_offre = min(x for x in (prix_cible, prix_max) if x is not None)
    return {"statut": statut, "regles": regles, "bilans": bilans, "prix_max": prix_max,
            "prix_cible": prix_cible, "prix_offre_recommande": prix_offre,
            "prix_max_borne_offre": prix_cible is None or prix_max < prix_cible}
