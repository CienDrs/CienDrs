"""Communes (code NIS) et prix médians Statbel (exigences B1, B19, indicateur « écart au médian communal »).

Statbel publie des prix médians par commune et par type de bien, issus des actes de vente
(fichiers open data sur statbel.fgov.be, à télécharger puis importer ici). L'import accepte
les principaux intitulés de colonnes Statbel (FR / NL / codes) et un format simplifié.
"""
import re
import unicodedata
from datetime import date

import pandas as pd

ALIAS = {
    "nis": ["cd_refnis", "refnis", "nis", "code_nis", "cd_ref_nis"],
    "commune": ["cd_refnis_fr", "tx_descr_fr", "commune", "nom", "cd_refnis_nl", "tx_descr_nl", "gemeente"],
    "annee": ["cd_year", "annee", "année", "jaar", "year"],
    "periode": ["cd_period", "periode", "période", "periode_nl", "period"],
    "type_bien": ["cd_type_fr", "cd_type", "type", "type_bien", "cd_type_nl"],
    "mediane": ["ms_p_50", "ms_p50", "ms_price_p50", "mediane", "médiane", "median", "prix_median", "p50"],
    "nb_transactions": ["ms_transactions", "ms_trans", "nb_transactions", "transactions", "aantal"],
}


def normaliser(nom):
    """« Saint-Ghislain » -> « saint ghislain » (sans accents ni ponctuation)."""
    if not nom:
        return ""
    s = unicodedata.normalize("NFKD", str(nom)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def type_maison(libelle):
    """Classe un intitulé Statbel : 'maison_4_facades', 'maison_2_3_facades', 'maison' ou None (autre bien)."""
    t = normaliser(libelle)
    if any(k in t for k in ("appartement", "flat", "studio", "terrain", "grond")):
        return None
    if any(k in t for k in ("villa", "bungalow", "campagne", "4 facade", "open bebouwing")):
        return "maison_4_facades"
    if any(k in t for k in ("ordinaire", "2 ou 3", "2 3 facade", "gesloten", "halfopen", "woonhuis")):
        return "maison_2_3_facades"
    if any(k in t for k in ("maison", "huis", "house", "b001", "b015")):
        return "maison"
    return None


def _colonnes(df):
    bas = {c.lower().strip(): c for c in df.columns}
    trouve = {}
    for cible, alias in ALIAS.items():
        for a in alias:
            if a in bas:
                trouve[cible] = bas[a]
                break
    manquantes = {"nis", "commune", "annee", "mediane"} - set(trouve)
    if manquantes:
        raise ValueError(f"Colonnes introuvables dans le fichier Statbel : {', '.join(sorted(manquantes))} "
                         f"(colonnes présentes : {', '.join(df.columns)})")
    return trouve


def lire_fichier(chemin_ou_flux, nom=None):
    nom = str(nom or chemin_ou_flux).lower()
    if nom.endswith((".xlsx", ".xls")):
        return pd.read_excel(chemin_ou_flux)
    return pd.read_csv(chemin_ou_flux, sep=None, engine="python", encoding="utf-8-sig")


def importer_medianes(con, chemin_ou_flux, nom=None, source="Statbel"):
    df = lire_fichier(chemin_ou_flux, nom)
    c = _colonnes(df)
    df = df[df[c["mediane"]].notna()].copy()
    if "type_bien" in c:
        df["_type"] = df[c["type_bien"]].map(type_maison)
        df = df[df["_type"].notna()]
    else:
        df["_type"] = "maison"
    df["_periode"] = df[c["periode"]].astype(str).str.strip().replace({"": "A", "nan": "A"}) if "periode" in c else "A"
    n = 0
    for _, r in df.iterrows():
        nis = str(r[c["nis"]]).split(".")[0].strip()
        con.execute("INSERT OR REPLACE INTO communes VALUES (?, ?, ?)",
                    (nis, str(r[c["commune"]]).strip(), normaliser(r[c["commune"]])))
        nb = r[c["nb_transactions"]] if "nb_transactions" in c else None
        con.execute("INSERT OR REPLACE INTO medianes_statbel VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nis, int(r[c["annee"]]), r["_periode"], r["_type"], float(r[c["mediane"]]),
                     None if pd.isna(nb) else int(nb), f"{source} (import {date.today().isoformat()})"))
        n += 1
    con.commit()
    return n


def importer_codes_postaux(con, chemin_ou_flux, nom=None):
    """Colonnes : code_postal, localite, commune (nom de la commune fusionnée)."""
    df = lire_fichier(chemin_ou_flux, nom)
    df.columns = [c.lower().strip() for c in df.columns]
    rows = [(str(r["code_postal"]).split(".")[0], r.get("localite") or "", r["commune"]) for _, r in df.iterrows()]
    con.executemany("INSERT OR REPLACE INTO codes_postaux VALUES (?, ?, ?)", rows)
    con.commit()
    return len(rows)


def commune_du_bien(con, code_postal=None, localite=None):
    """Retourne (nis, nom) de la commune du bien, via le code postal puis le nom de la localité."""
    candidats = []
    if code_postal:
        candidats += [r[0] for r in con.execute("SELECT commune FROM codes_postaux WHERE code_postal = ?",
                                                (str(code_postal),))]
    if localite:
        cible = normaliser(localite)
        candidats += [c for loc, c in con.execute("SELECT localite, commune FROM codes_postaux")
                      if normaliser(loc) == cible]
        candidats.append(localite)
    for nom in candidats:
        r = con.execute("SELECT nis, nom FROM communes WHERE nom_normalise = ?", (normaliser(nom),)).fetchone()
        if r:
            return r
    return None


def mediane_commune(con, nis, facades=None):
    """Médiane la plus récente pour les maisons de la commune (type selon le nombre de façades)."""
    prefere = "maison_4_facades" if facades and int(facades) >= 4 else "maison_2_3_facades"
    lignes = con.execute("SELECT annee, periode, type_bien, mediane, nb_transactions, source FROM medianes_statbel "
                         "WHERE nis = ? ORDER BY annee DESC, periode DESC", (nis,)).fetchall()
    for type_voulu in (prefere, "maison", None):
        for annee, periode, t, med, nb, source in lignes:
            if type_voulu is None or t == type_voulu:
                return {"annee": annee, "periode": periode, "type_bien": t, "mediane": med,
                        "nb_transactions": nb, "source": source}
    return None


def ecart_au_median(con, prix, code_postal=None, localite=None, facades=None):
    commune = commune_du_bien(con, code_postal, localite)
    if not commune or not prix:
        return None
    med = mediane_commune(con, commune[0], facades)
    if not med:
        return None
    return {"nis": commune[0], "commune": commune[1], **med, "ecart": prix / med["mediane"] - 1}
