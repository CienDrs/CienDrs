"""Génère des observations d'annonces FICTIVES (identifiants EX…) pour tester la base.

Ces données ne proviennent pas d'Immoweb : elles servent uniquement à démontrer le
fonctionnement (historique de prix, retraits, actualisation, comparables).
"""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
AUJOURDHUI = date(2026, 10, 7)
DATA = Path(__file__).parent / "data"
# commune: (latitude, longitude, prix médian indicatif €/m² d'une maison en bon état)
COMMUNES = {
    "Mons": (50.4542, 3.9517, 1950), "Jemappes": (50.4520, 3.8870, 1550), "Cuesmes": (50.4370, 3.9220, 1500),
    "Quaregnon": (50.4400, 3.8650, 1450), "Frameries": (50.4080, 3.8970, 1600), "Colfontaine": (50.4110, 3.8510, 1400),
    "Quévy": (50.3800, 3.9400, 2000), "Jurbise": (50.5250, 3.9100, 2150), "Saint-Ghislain": (50.4480, 3.8180, 1550),
    "Ghlin": (50.4870, 3.9060, 1800), "Nimy": (50.4730, 3.9540, 1750), "Havré": (50.4650, 4.0450, 1800),
    "Hyon": (50.4410, 3.9700, 2100), "Saint-Symphorien": (50.4370, 4.0100, 1900),
}
ETATS = {"Comme neuf": 1.25, "Fraîchement rénové": 1.2, "Bon": 1.0, "À rafraîchir": 0.88,
         "À rénover": 0.75, "À restaurer": 0.6}
PEB = {"B": 130, "C": 210, "D": 300, "E": 380, "F": 470, "G": 600}
RUES = ["Rue de la Station", "Rue du Moulin", "Rue des Écoles", "Avenue des Tilleuls", "Rue de l'Église"]


def main():
    rng = np.random.default_rng(SEED)
    lignes = []
    for i in range(1, 181):
        commune = rng.choice(list(COMMUNES))
        lat0, lon0, pm2 = COMMUNES[commune]
        etat = rng.choice(list(ETATS), p=[0.08, 0.12, 0.35, 0.2, 0.18, 0.07])
        peb = rng.choice(list(PEB), p=[0.05, 0.15, 0.2, 0.2, 0.2, 0.2]) if etat not in ("Comme neuf", "Fraîchement rénové") \
            else rng.choice(["A", "B", "C"])
        surface = int(np.clip(rng.normal(135, 35), 65, 260))
        chambres = int(np.clip(round(surface / 40 + rng.normal(0, 0.6)), 1, 6))
        facades = int(rng.choice([2, 3, 4], p=[0.5, 0.3, 0.2]))
        terrain = int(rng.uniform(80, 300) if facades == 2 else rng.uniform(250, 1500))
        prix = round(pm2 * ETATS[etat] * surface * (1 + 0.05 * (facades - 2)) * rng.lognormal(0, 0.1), -3)
        publication = AUJOURDHUI - timedelta(days=int(rng.integers(5, 800)))
        ident = f"EX{i:04d}"
        base = dict(
            immoweb_id=ident, url="", type_bien="maison", rue=rng.choice(RUES), numero=str(rng.integers(1, 200)),
            code_postal="", commune=commune, latitude=round(lat0 + rng.normal(0, 0.006), 5),
            longitude=round(lon0 + rng.normal(0, 0.009), 5), adresse_precise=1, surface_habitable=surface,
            surface_terrain=terrain, chambres=chambres, salles_de_bain=1 + int(surface > 160), facades=facades,
            annee_construction=int(rng.choice([1900, 1925, 1950, 1970, 1990, 2005]) + rng.integers(0, 20)),
            etat=etat, peb_lettre=peb, peb_kwh_m2=PEB.get(peb, 80) + int(rng.integers(-30, 30)),
            description=f"Maison {facades} façades de {surface} m² à {commune}, {chambres} chambres, état : {etat.lower()}.",
            date_publication=publication.isoformat())
        # observations mensuelles avec baisses de prix éventuelles, retrait éventuel
        surevaluee = rng.random() < 0.35
        duree = int(rng.integers(30, 420)) if rng.random() < 0.6 else (AUJOURDHUI - publication).days
        fin = min(AUJOURDHUI, publication + timedelta(days=duree))
        d, p = publication, prix * (1.12 if surevaluee else 1.0)
        while d <= fin:
            lignes.append({**base, "date_observation": d.isoformat(), "prix": round(p, -3)})
            d += timedelta(days=30)
            if surevaluee and rng.random() < 0.25:
                p *= 1 - rng.uniform(0.03, 0.08)
    pd.DataFrame(lignes).to_csv(DATA / "annonces_exemple.csv", index=False)
    print(f"{len(lignes)} observations fictives pour 180 annonces -> data/annonces_exemple.csv")


if __name__ == "__main__":
    main()
