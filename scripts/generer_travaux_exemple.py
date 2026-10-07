"""Génère un jeu de données SYNTHÉTIQUE de chantiers de rénovation (région de Mons).

Ces données servent uniquement à tester le pipeline de régression : elles sont tirées
d'hypothèses de prix unitaires (TVAC, 6 %) indicatives pour le Hainaut, avec du bruit.
Elles doivent être remplacées par les devis et factures réels des opérations.

Sorties :
  data/postes_exemple.csv    une ligne par poste de travaux et par chantier
  data/chantiers_exemple.csv une ligne par chantier (données de l'annonce + coût total)
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_CHANTIERS = 150
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "travaux"

PEB = ["A", "B", "C", "D", "E", "F", "G"]
ETATS = ["À rafraîchir", "À rénover", "À restaurer"]
GAMMES = {"eco": 0.85, "standard": 1.00, "premium": 1.25}
COMMUNES = ["Mons", "Jemappes", "Cuesmes", "Quaregnon", "Frameries", "Colfontaine",
            "Quévy", "Jurbise", "Saint-Ghislain", "Ghlin", "Nimy", "Havré"]

# poste: (unité, coût fixe €, prix unitaire € TVAC, majoration bâti < 1945)
POSTES = {
    "toiture":            ("m² toiture",   2500, 200, 0.10),
    "isolation_toiture":  ("m² toiture",    500,  55, 0.00),
    "chassis":            ("pièce",         500, 900, 0.00),
    "electricite":        ("m² habitable", 1500,  65, 0.10),
    "chauffage":          ("m² habitable", 4000,  45, 0.05),
    "salle_de_bain":      ("m² SDB",       3000, 1000, 0.05),
    "cuisine":            ("ml cuisine",   1500, 1200, 0.00),
    "peinture_sols":      ("m² habitable",  800,  55, 0.05),
    "humidite":           ("ml mur",        800, 120, 0.15),
    "isolation_facade":   ("m² façade",    2000, 160, 0.05),
}


def postes_du_chantier(rng, etat, peb_avant, peb_apres):
    """Choisit les postes réalisés selon l'état Immoweb et le saut de classe PEB."""
    saut = PEB.index(peb_avant) - PEB.index(peb_apres)
    proba = {
        "peinture_sols": 1.0,
        "electricite": {"À rafraîchir": 0.3, "À rénover": 0.85, "À restaurer": 1.0}[etat],
        "salle_de_bain": {"À rafraîchir": 0.4, "À rénover": 0.9, "À restaurer": 1.0}[etat],
        "cuisine": {"À rafraîchir": 0.4, "À rénover": 0.85, "À restaurer": 1.0}[etat],
        "humidite": {"À rafraîchir": 0.1, "À rénover": 0.4, "À restaurer": 0.7}[etat],
        "toiture": {"À rafraîchir": 0.05, "À rénover": 0.3, "À restaurer": 0.8}[etat],
        "isolation_toiture": min(1.0, 0.3 + 0.25 * saut),
        "chassis": min(1.0, 0.2 + 0.25 * saut),
        "chauffage": min(1.0, 0.2 + 0.2 * saut),
        "isolation_facade": max(0.0, 0.15 * (saut - 1)),
    }
    postes = [p for p, pr in proba.items() if rng.random() < pr]
    # une toiture refaite inclut son isolation
    if "toiture" in postes and "isolation_toiture" in postes:
        postes.remove("isolation_toiture")
    return postes


def quantite(rng, poste, surface, facades):
    if poste in ("toiture", "isolation_toiture"):
        return round(surface * rng.uniform(0.55, 0.8))
    if poste == "chassis":
        return int(round(surface / 12 + rng.integers(-2, 3)))
    if poste in ("electricite", "chauffage", "peinture_sols"):
        return surface
    if poste == "salle_de_bain":
        return round(rng.uniform(4, 10), 1)
    if poste == "cuisine":
        return round(rng.uniform(2.5, 6), 1)
    if poste == "humidite":
        return round(rng.uniform(10, 40))
    if poste == "isolation_facade":
        return round(surface * rng.uniform(0.35, 0.6) * (5 - facades) / 2)
    raise ValueError(poste)


def main():
    rng = np.random.default_rng(SEED)
    lignes_postes, lignes_chantiers = [], []
    for i in range(1, N_CHANTIERS + 1):
        cid = f"CH{i:03d}"
        etat = rng.choice(ETATS, p=[0.3, 0.5, 0.2])
        surface = int(np.clip(rng.normal(125, 30), 70, 220))
        facades = int(rng.choice([2, 3, 4], p=[0.5, 0.3, 0.2]))
        annee = int(rng.choice([1910, 1930, 1950, 1965, 1975, 1985, 1995],
                               p=[0.2, 0.25, 0.15, 0.15, 0.1, 0.1, 0.05]) + rng.integers(0, 10))
        peb_avant = rng.choice(PEB[3:], p=[0.15, 0.3, 0.3, 0.25])
        peb_apres = PEB[max(1, PEB.index(peb_avant) - int(rng.integers(1, 4)))]
        gamme = rng.choice(list(GAMMES), p=[0.3, 0.55, 0.15])
        total = 0.0
        for poste in postes_du_chantier(rng, etat, peb_avant, peb_apres):
            unite, fixe, pu, maj_ancien = POSTES[poste]
            q = quantite(rng, poste, surface, facades)
            cout = (fixe + pu * q) * GAMMES[gamme] * (1 + maj_ancien * (annee < 1945))
            cout *= rng.lognormal(0, 0.12)
            cout = round(cout, -1)
            total += cout
            lignes_postes.append(dict(chantier_id=cid, poste=poste, unite=unite, quantite=q,
                                      gamme=gamme, annee_construction=annee, cout_ttc=cout))
        lignes_chantiers.append(dict(
            chantier_id=cid, commune=rng.choice(COMMUNES), surface_habitable=surface,
            facades=facades, annee_construction=annee, etat_immoweb=etat,
            peb_avant=peb_avant, peb_apres=peb_apres, gamme=gamme, cout_total_ttc=round(total, -1)))
    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(lignes_postes).to_csv(DATA_DIR / "postes_exemple.csv", index=False)
    pd.DataFrame(lignes_chantiers).to_csv(DATA_DIR / "chantiers_exemple.csv", index=False)
    print(f"{N_CHANTIERS} chantiers, {len(lignes_postes)} lignes de postes générés dans {DATA_DIR}")


if __name__ == "__main__":
    main()
