"""Base de données des annonces de maisons à vendre (Immoweb) autour de Mons.

Fonctions principales :
  - enregistrer une observation d'annonce (création, mise à jour, historique des prix) ;
  - importer un fichier CSV d'observations ou une page d'annonce Immoweb sauvegardée ;
  - marquer les annonces retirées (plus vues depuis N jours) ;
  - calculer les indicateurs : prix actuel, prix/m², prix actualisé, baisses de prix,
    durée en ligne ;
  - situer un bien par rapport aux maisons comparables (moyenne, médiane, min, max).

Les conditions d'utilisation d'Immoweb interdisent l'extraction automatisée : la base est
alimentée par des pages consultées et sauvegardées manuellement, des exports CSV ou une
saisie, sauf accord de données avec Immoweb.

Usage (CLI) :
  python base_annonces.py init
  python base_annonces.py importer-csv data/annonces_exemple.csv
  python base_annonces.py importer-page annonce.html [--date 2026-10-07]
  python base_annonces.py importer-indices data/indices_prix_exemple.csv
  python base_annonces.py maj-statut --jours 14
  python base_annonces.py retirer 12345678 --date 2026-10-01
  python base_annonces.py lister [--commune Frameries]
  python base_annonces.py situer 12345678
  python base_annonces.py situer --surface 130 --chambres 3 --prix 189000 --lat 50.40 --lon 3.89
"""
import argparse
import csv
import json
import math
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ICI = Path(__file__).parent
BASE_PAR_DEFAUT = ICI / "data" / "annonces.sqlite"
GRAND_PLACE_MONS = (50.4542, 3.9517)
RAYON_ZONE_KM = 10.0
ZONE_INDICE = "Hainaut"
SEUIL_ACTUALISATION_JOURS = 365
CHAMPS_ANNONCE = [
    "url", "type_bien", "rue", "numero", "code_postal", "commune", "latitude", "longitude",
    "adresse_precise", "surface_habitable", "surface_terrain", "chambres", "salles_de_bain",
    "facades", "annee_construction", "etat", "peb_lettre", "peb_kwh_m2", "description",
    "date_publication",
]
NUMERIQUES = {"latitude", "longitude", "surface_habitable", "surface_terrain", "peb_kwh_m2"}
ENTIERS = {"chambres", "salles_de_bain", "facades", "annee_construction", "adresse_precise"}


# ------------------------------------------------------------------- connexion

def connecter(chemin=BASE_PAR_DEFAUT) -> sqlite3.Connection:
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(chemin)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((ICI / "schema.sql").read_text(encoding="utf-8"))
    return con


# ------------------------------------------------------------------- utilitaires

def distance_km(lat1, lon1, lat2, lon2):
    """Distance orthodromique (formule de haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def trimestre(d: str) -> str:
    a, m = int(d[:4]), int(d[5:7])
    return f"{a}-T{(m - 1) // 3 + 1}"


def _nettoyer(champ, valeur):
    if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)) or valeur == "":
        return None
    if champ in NUMERIQUES:
        return float(valeur)
    if champ in ENTIERS:
        return int(float(valeur))
    return str(valeur).strip()


# --------------------------------------------------------------- enregistrement

def enregistrer_observation(con, immoweb_id, prix, date_observation=None, commit=True, **champs):
    """Enregistre une observation d'annonce à une date donnée.

    - crée l'annonce si elle est nouvelle, sinon met à jour les champs fournis ;
    - ajoute une ligne à l'historique uniquement si le prix a changé ;
    - une annonce revue en ligne après avoir été marquée retirée redevient « en ligne ».
    """
    immoweb_id = str(immoweb_id)
    d = date_observation or date.today().isoformat()
    champs = {k: _nettoyer(k, v) for k, v in champs.items() if k in CHAMPS_ANNONCE}
    champs = {k: v for k, v in champs.items() if v is not None}
    if champs.get("latitude") is not None and champs.get("longitude") is not None:
        champs["distance_mons_km"] = round(distance_km(champs["latitude"], champs["longitude"],
                                                       *GRAND_PLACE_MONS), 2)

    existe = con.execute("SELECT premiere_observation, derniere_observation FROM annonces "
                         "WHERE immoweb_id = ?", (immoweb_id,)).fetchone()
    if existe is None:
        colonnes = ["immoweb_id", "premiere_observation", "derniere_observation", *champs]
        con.execute(f"INSERT INTO annonces ({', '.join(colonnes)}) VALUES ({', '.join('?' * len(colonnes))})",
                    [immoweb_id, d, d, *champs.values()])
    else:
        champs["premiere_observation"] = min(existe[0], d)
        champs["derniere_observation"] = max(existe[1], d)
        if d >= existe[1]:
            champs["date_retrait"] = None
        affectations = ", ".join(f"{k} = ?" for k in champs)
        con.execute(f"UPDATE annonces SET {affectations} WHERE immoweb_id = ?", [*champs.values(), immoweb_id])

    if prix is not None and not (isinstance(prix, float) and math.isnan(prix)):
        precedent = con.execute("SELECT prix FROM historique_prix WHERE immoweb_id = ? AND date_observation <= ? "
                                "ORDER BY date_observation DESC LIMIT 1", (immoweb_id, d)).fetchone()
        if precedent is None or precedent[0] != float(prix):
            con.execute("INSERT OR REPLACE INTO historique_prix VALUES (?, ?, ?)", (immoweb_id, d, float(prix)))
    if commit:
        con.commit()


def importer_csv(con, chemin):
    """Une ligne = une observation (colonnes : immoweb_id, date_observation, prix + champs d'annonce)."""
    n = 0
    with open(chemin, encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            prix = ligne.pop("prix", None)
            enregistrer_observation(con, ligne.pop("immoweb_id"), float(prix) if prix else None,
                                    ligne.pop("date_observation", None) or None, commit=False, **ligne)
            n += 1
    con.commit()
    return n


def importer_indices(con, chemin):
    df = pd.read_csv(chemin)
    con.executemany("INSERT OR REPLACE INTO indices_prix VALUES (?, ?, ?, ?)",
                    df[["zone", "periode", "indice", "source"]].itertuples(index=False, name=None))
    con.commit()
    return len(df)


# ------------------------------------------------- import d'une page Immoweb

def _chemin(d, *cles):
    for c in cles:
        if not isinstance(d, dict):
            return None
        d = d.get(c)
    return d


ETATS_IMMOWEB = {
    "AS_NEW": "Comme neuf", "JUST_RENOVATED": "Fraîchement rénové", "GOOD": "Bon",
    "TO_BE_DONE_UP": "À rafraîchir", "TO_RENOVATE": "À rénover", "TO_RESTORE": "À restaurer",
}


def extraire_page_immoweb(html: str) -> dict:
    """Extrait les données d'une page d'annonce Immoweb sauvegardée (objet JS `window.classified`).

    La structure de la page peut évoluer : vérifier l'extraction sur une page réelle et
    adapter les chemins ci-dessous si nécessaire.
    """
    m = re.search(r"window\.classified\s*=\s*", html)
    if not m:
        raise ValueError("Objet `window.classified` introuvable dans la page")
    data, _ = json.JSONDecoder().raw_decode(html[m.end():])
    prop, loc = data.get("property") or {}, _chemin(data, "property", "location") or {}
    certif = _chemin(data, "transaction", "certificates") or {}
    creation = _chemin(data, "publication", "creationDate")
    return {
        "immoweb_id": str(data.get("id")),
        "prix": _chemin(data, "price", "mainValue") or _chemin(data, "transaction", "sale", "price"),
        "url": f"https://www.immoweb.be/fr/annonce/{data.get('id')}",
        "type_bien": (prop.get("type") or "").lower().replace("house", "maison") or None,
        "rue": loc.get("street"), "numero": loc.get("number"),
        "code_postal": loc.get("postalCode"), "commune": loc.get("locality"),
        "latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
        "adresse_precise": int(bool(loc.get("street") and loc.get("number"))),
        "surface_habitable": prop.get("netHabitableSurface"),
        "surface_terrain": _chemin(prop, "land", "surface"),
        "chambres": prop.get("bedroomCount"), "salles_de_bain": prop.get("bathroomCount"),
        "facades": _chemin(prop, "building", "facadeCount"),
        "annee_construction": _chemin(prop, "building", "constructionYear"),
        "etat": ETATS_IMMOWEB.get(_chemin(prop, "building", "condition"), _chemin(prop, "building", "condition")),
        "peb_lettre": certif.get("epcScore"),
        "peb_kwh_m2": certif.get("primaryEnergyConsumptionPerSqm"),
        "description": prop.get("description") or data.get("description"),
        "date_publication": creation[:10] if creation else None,
    }


def importer_page(con, chemin, date_observation=None):
    champs = extraire_page_immoweb(Path(chemin).read_text(encoding="utf-8"))
    enregistrer_observation(con, champs.pop("immoweb_id"), champs.pop("prix"), date_observation, **champs)


# ---------------------------------------------------------------- statut en ligne

def maj_statut(con, jours=14, aujourd_hui=None):
    """Marque comme retirées les annonces non revues depuis `jours` jours."""
    limite = (date.fromisoformat(aujourd_hui or date.today().isoformat()) - timedelta(days=jours)).isoformat()
    cur = con.execute("UPDATE annonces SET date_retrait = derniere_observation "
                      "WHERE date_retrait IS NULL AND derniere_observation < ?", (limite,))
    con.commit()
    return cur.rowcount


def retirer(con, immoweb_id, date_retrait=None):
    con.execute("UPDATE annonces SET date_retrait = ? WHERE immoweb_id = ?",
                (date_retrait or date.today().isoformat(), str(immoweb_id)))
    con.commit()


# -------------------------------------------------------------------- indicateurs

def tableau_annonces(con, aujourd_hui=None, zone_indice=ZONE_INDICE) -> pd.DataFrame:
    """Une ligne par annonce avec tous les indicateurs calculés."""
    today = aujourd_hui or date.today().isoformat()
    ann = pd.read_sql("SELECT * FROM annonces", con)
    hist = pd.read_sql("SELECT * FROM historique_prix ORDER BY immoweb_id, date_observation", con)
    if ann.empty:
        return ann
    agg = hist.groupby("immoweb_id").agg(
        prix_initial=("prix", "first"), prix_actuel=("prix", "last"),
        date_prix_actuel=("date_observation", "last"), nb_changements_prix=("prix", lambda s: len(s) - 1),
        nb_baisses_prix=("prix", lambda s: int((s.diff() < 0).sum())))
    agg["historique_prix"] = hist.groupby("immoweb_id").apply(
        lambda g: " → ".join(f"{d}: {p:,.0f} €".replace(",", " ")
                             for d, p in zip(g.date_observation, g.prix)), include_groups=False)
    df = ann.merge(agg, left_on="immoweb_id", right_index=True, how="left")

    df["en_ligne"] = df["date_retrait"].isna()
    debut = df["date_publication"].fillna(df["premiere_observation"])
    fin = df["date_retrait"].fillna(today)
    df["jours_en_ligne"] = (pd.to_datetime(fin) - pd.to_datetime(debut)).dt.days
    df["variation_prix_pct"] = (df["prix_actuel"] / df["prix_initial"] - 1) * 100
    df["prix_m2"] = df["prix_actuel"] / df["surface_habitable"]

    # Actualisation : le prix est daté de sa dernière observation. Il est actualisé avec l'indice
    # de la zone s'il a plus d'un an (annonce retirée depuis longtemps) ; une annonce toujours
    # en ligne reflète le marché actuel, même si elle a été publiée il y a plus d'un an.
    indices = pd.read_sql("SELECT periode, indice FROM indices_prix WHERE zone = ?", con, params=(zone_indice,))
    df["date_reference_prix"] = df["derniere_observation"]
    df["coef_actualisation"] = 1.0
    if not indices.empty:
        serie = indices.set_index("periode")["indice"].sort_index()
        indice_courant = serie.iloc[-1]
        age = (pd.to_datetime(today) - pd.to_datetime(df["date_reference_prix"])).dt.days
        for i in df.index[age >= SEUIL_ACTUALISATION_JOURS]:
            t = trimestre(df.at[i, "date_reference_prix"])
            base = serie[serie.index <= t]
            if not base.empty:
                df.at[i, "coef_actualisation"] = indice_courant / base.iloc[-1]
    df["prix_actualise"] = df["prix_actuel"] * df["coef_actualisation"]
    df["prix_m2_actualise"] = df["prix_actualise"] / df["surface_habitable"]
    return df


# ---------------------------------------------------------------- comparables

def comparables(df, surface, chambres=None, surface_terrain=None, lat=None, lon=None, commune=None,
                facades=None, etat=None, exclure_id=None, rayon_km=3.0, tolerance_surface=0.25,
                min_resultats=8):
    """Sélectionne les maisons similaires, en élargissant les critères si trop peu de résultats."""
    base = df[(df["type_bien"].fillna("maison") == "maison") & df["prix_actuel"].notna()
              & df["surface_habitable"].notna()]
    if exclure_id is not None:
        base = base[base["immoweb_id"] != str(exclure_id)]
    if lat is not None and lon is not None and base["latitude"].notna().any():
        base = base.assign(distance_km=[distance_km(lat, lon, a, o) if pd.notna(a) else math.inf
                                        for a, o in zip(base["latitude"], base["longitude"])])
    else:
        base = base.assign(distance_km=math.nan)

    etapes = [
        dict(rayon=rayon_km, tol=tolerance_surface, ch=1, terrain=True, facades=True, etat=True),
        dict(rayon=rayon_km, tol=tolerance_surface, ch=1, terrain=True, facades=True, etat=False),
        dict(rayon=5.0, tol=tolerance_surface, ch=1, terrain=False, facades=False, etat=False),
        dict(rayon=RAYON_ZONE_KM, tol=tolerance_surface, ch=1, terrain=False, facades=False, etat=False),
        dict(rayon=RAYON_ZONE_KM, tol=0.35, ch=None, terrain=False, facades=False, etat=False),
    ]
    for e in etapes:
        sel = base[base["surface_habitable"].between(surface * (1 - e["tol"]), surface * (1 + e["tol"]))]
        if base["distance_km"].notna().any():
            sel = sel[sel["distance_km"] <= e["rayon"]]
        elif commune:
            sel = sel[sel["commune"].str.lower() == commune.lower()]
        if chambres is not None and e["ch"] is not None:
            sel = sel[sel["chambres"].isna() | (sel["chambres"] - chambres).abs().le(e["ch"])]
        if e["terrain"] and surface_terrain:
            sel = sel[sel["surface_terrain"].isna()
                      | sel["surface_terrain"].between(surface_terrain * 0.5, surface_terrain * 1.5)]
        if e["facades"] and facades:
            sel = sel[sel["facades"].isna() | (sel["facades"] == facades)]
        if e["etat"] and etat:
            sel = sel[sel["etat"].isna() | (sel["etat"] == etat)]
        if len(sel) >= min_resultats:
            break
    criteres = (f"rayon {e['rayon']:g} km, surface ±{e['tol']:.0%}"
                + (f", chambres ±{e['ch']}" if chambres is not None and e["ch"] is not None else "")
                + (", terrain ±50 %" if e["terrain"] and surface_terrain else "")
                + (f", {facades} façades" if e["facades"] and facades else "")
                + (f", état « {etat} »" if e["etat"] and etat else ""))
    return sel, criteres


def statistiques(sel: pd.DataFrame) -> pd.DataFrame:
    stats = {}
    for col, lib in [("prix_actualise", "Prix actualisé (€)"), ("prix_m2_actualise", "Prix/m² actualisé (€)"),
                     ("jours_en_ligne", "Jours en ligne")]:
        s = sel[col].dropna()
        stats[lib] = {"n": len(s), "moyenne": s.mean(), "mediane": s.median(), "min": s.min(),
                      "p25": s.quantile(0.25), "p75": s.quantile(0.75), "max": s.max()}
    return pd.DataFrame(stats).T


ORDRE_ETATS = ["Comme neuf", "Fraîchement rénové", "Bon", "À rafraîchir", "À rénover", "À restaurer"]


def par_groupe(sel, colonne, ordre):
    """Prix/m² actualisé des comparables ventilé par état ou par classe PEB."""
    g = sel.groupby(colonne)["prix_m2_actualise"].agg(["count", "median", "min", "max"])
    return g.reindex([o for o in ordre if o in g.index] + [i for i in g.index if i not in ordre])


def situer(df, prix=None, surface=None, immoweb_id=None, **criteres):
    """Positionne un bien (de la base ou décrit par ses caractéristiques) parmi ses comparables."""
    if immoweb_id is not None:
        b = df[df["immoweb_id"] == str(immoweb_id)]
        if b.empty:
            raise KeyError(f"Annonce {immoweb_id} absente de la base")
        b = b.iloc[0]
        prix, surface = b["prix_actuel"], b["surface_habitable"]
        criteres = {"chambres": b["chambres"], "surface_terrain": b["surface_terrain"],
                    "lat": b["latitude"], "lon": b["longitude"], "commune": b["commune"],
                    "facades": b["facades"], "etat": b["etat"], **criteres}
        criteres = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in criteres.items()}
    sel, texte_criteres = comparables(df, surface, exclure_id=immoweb_id, **criteres)
    stats = statistiques(sel)
    res = {"comparables": sel, "criteres": texte_criteres, "statistiques": stats,
           "par_etat": par_groupe(sel, "etat", ORDRE_ETATS),
           "par_peb": par_groupe(sel, "peb_lettre", ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"])}
    if prix and surface and len(sel):
        pm2 = prix / surface
        m2 = sel["prix_m2_actualise"].dropna()
        res["prix_m2"] = pm2
        res["ecart_mediane_pct"] = (pm2 / m2.median() - 1) * 100
        res["percentile"] = (m2 < pm2).mean() * 100
        res["valeur_mediane_estimee"] = m2.median() * surface
        baisse = sel[sel["nb_baisses_prix"] > 0]
        res["part_comparables_en_baisse_pct"] = len(baisse) / len(sel) * 100
        res["mediane_m2_sans_baisse"] = sel.loc[sel["nb_baisses_prix"] == 0, "prix_m2_actualise"].median()
        res["mediane_m2_retirees"] = sel.loc[~sel["en_ligne"], "prix_m2_actualise"].median()
    return res


def fmt(x, dec=0):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else \
        f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def afficher_situation(res):
    print(f"Comparables : {len(res['comparables'])} ({res['criteres']})")
    print(res["statistiques"].map(fmt).to_string())
    for cle, titre in [("par_etat", "état du bien"), ("par_peb", "classe PEB")]:
        print(f"\nPrix/m² actualisé par {titre} :")
        print(res[cle].rename(columns={"count": "n", "median": "médiane"}).map(fmt).to_string())
    if "prix_m2" in res:
        print(f"\nPrix/m² du bien : {fmt(res['prix_m2'])} € — écart à la médiane : "
              f"{fmt(res['ecart_mediane_pct'], 1)} % — percentile : {res['percentile']:.0f}")
        print(f"Valeur au prix/m² médian des comparables : {fmt(res['valeur_mediane_estimee'])} €")
        print(f"Médiane €/m² des comparables sans baisse de prix : {fmt(res['mediane_m2_sans_baisse'])} € ; "
              f"des annonces retirées : {fmt(res['mediane_m2_retirees'])} €")
        print(f"Part des comparables ayant baissé leur prix : {res['part_comparables_en_baisse_pct']:.0f} %")


# ------------------------------------------------------------------------- CLI

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=BASE_PAR_DEFAUT)
    p.add_argument("--aujourdhui", help="date de référence (tests)")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init")
    s = sp.add_parser("importer-csv"); s.add_argument("fichier")
    s = sp.add_parser("importer-page"); s.add_argument("fichier"); s.add_argument("--date")
    s = sp.add_parser("importer-indices"); s.add_argument("fichier")
    s = sp.add_parser("maj-statut"); s.add_argument("--jours", type=int, default=14)
    s = sp.add_parser("retirer"); s.add_argument("immoweb_id"); s.add_argument("--date")
    s = sp.add_parser("lister"); s.add_argument("--commune"); s.add_argument("--csv")
    s = sp.add_parser("situer")
    s.add_argument("immoweb_id", nargs="?")
    for opt, t in [("--prix", float), ("--surface", float), ("--chambres", int), ("--terrain", float),
                   ("--lat", float), ("--lon", float), ("--facades", int), ("--rayon", float)]:
        s.add_argument(opt, type=t)
    s.add_argument("--commune"); s.add_argument("--etat")
    a = p.parse_args()

    con = connecter(a.base)
    if a.cmd == "init":
        print(f"Base prête : {a.base}")
    elif a.cmd == "importer-csv":
        print(f"{importer_csv(con, a.fichier)} observations importées")
    elif a.cmd == "importer-page":
        importer_page(con, a.fichier, a.date); print("Annonce importée")
    elif a.cmd == "importer-indices":
        print(f"{importer_indices(con, a.fichier)} indices importés")
    elif a.cmd == "maj-statut":
        print(f"{maj_statut(con, a.jours, a.aujourdhui)} annonces marquées comme retirées")
    elif a.cmd == "retirer":
        retirer(con, a.immoweb_id, a.date)
    elif a.cmd == "lister":
        df = tableau_annonces(con, a.aujourdhui)
        if a.commune:
            df = df[df["commune"].str.lower() == a.commune.lower()]
        cols = ["immoweb_id", "commune", "surface_habitable", "chambres", "surface_terrain", "peb_lettre",
                "peb_kwh_m2", "prix_actuel", "prix_m2", "prix_actualise", "en_ligne", "jours_en_ligne",
                "nb_baisses_prix", "variation_prix_pct"]
        if a.csv:
            df.to_csv(a.csv, index=False); print(f"Export : {a.csv}")
        else:
            print(df[cols].to_string(index=False))
    elif a.cmd == "situer":
        df = tableau_annonces(con, a.aujourdhui)
        criteres = {k: v for k, v in dict(chambres=a.chambres, surface_terrain=a.terrain, lat=a.lat, lon=a.lon,
                                          commune=a.commune, facades=a.facades, etat=a.etat).items()
                    if v is not None}
        if a.rayon:
            criteres["rayon_km"] = a.rayon
        afficher_situation(situer(df, prix=a.prix, surface=a.surface, immoweb_id=a.immoweb_id, **criteres))


if __name__ == "__main__":
    main()
