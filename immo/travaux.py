"""Pré-chiffrage des travaux à partir de l'annonce (exigences D2, D4, D7, D8).

Niveau de rénovation déduit de l'état Immoweb, ratio €/m² TVAC du niveau, plus un supplément
par classe PEB gagnée. Les ratios sont des paramètres à calibrer avec les devis réels ;
la régression sur chantiers réels (immo.regression_travaux) les remplacera quand assez de
chantiers seront enregistrés.
"""
from immo import parametres

CLASSES_PEB = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]
LIBELLES_NIVEAUX = {"aucun": "Aucun (bien rénové)", "rafraichissement": "Rafraîchissement",
                    "renovation_moyenne": "Rénovation moyenne", "renovation_lourde": "Rénovation lourde"}


def classes_gagnees(peb_avant, peb_apres):
    if peb_avant not in CLASSES_PEB or peb_apres not in CLASSES_PEB:
        return 0
    return max(0, CLASSES_PEB.index(peb_avant) - CLASSES_PEB.index(peb_apres))


def niveau_pour_etat(etat, p=None):
    p = p or parametres.charger()
    return p["travaux"]["niveau_par_etat"].get(etat or "", "renovation_moyenne")


def estimer(surface, etat=None, peb_avant=None, peb_apres=None, niveau=None, p=None):
    """Retourne la fourchette de coût des travaux TVAC (hors imprévus) et le taux d'imprévus."""
    p = p or parametres.charger()
    niveau = niveau or niveau_pour_etat(etat, p)
    bas_m2, haut_m2 = p["travaux"]["niveaux"].get(niveau, (0, 0))
    gain = classes_gagnees(peb_avant, peb_apres)
    supplement_m2 = gain * p["travaux"]["supplement_par_classe_peb_m2"]
    if not surface:
        return {"niveau": niveau, "classes_peb_gagnees": gain, "bas": None, "central": None, "haut": None,
                "taux_imprevus": p["travaux"]["imprevus"].get(niveau, 0.0)}
    return {
        "niveau": niveau, "libelle_niveau": LIBELLES_NIVEAUX.get(niveau, niveau),
        "classes_peb_gagnees": gain, "supplement_peb": supplement_m2 * surface,
        "bas": (bas_m2 + supplement_m2) * surface,
        "central": ((bas_m2 + haut_m2) / 2 + supplement_m2) * surface,
        "haut": (haut_m2 + supplement_m2) * surface,
        "taux_imprevus": p["travaux"]["imprevus"].get(niveau, 0.0),
    }
