"""Communes (code NIS) et prix médians Statbel (exigences B1, B19, indicateur « écart au médian communal »).

Statbel publie des prix médians par commune et par type de bien, issus des actes de vente.
L'application les télécharge elle-même (`mettre_a_jour`) depuis les sources configurées dans
parametres.toml [statbel] : le jeu de données WalStat / Open Data Wallonie-Bruxelles (API), puis,
à défaut, le fichier open data le plus récent de la page « Prix de l'immobilier » de Statbel.
La lecture accepte les intitulés de colonnes Statbel (FR / NL / codes), le format « long »
(une ligne par indicateur) et les fichiers CSV, Excel ou ZIP.
"""
import io
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime

import pandas as pd

ALIAS = {
    "nis": ["cd_refnis", "refnis", "nis", "code_nis", "cd_ref_nis"],
    "commune": ["cd_refnis_fr", "tx_descr_fr", "commune", "nom", "cd_refnis_nl", "tx_descr_nl", "gemeente"],
    "annee": ["cd_year", "annee", "année", "jaar", "year"],
    "periode": ["cd_period", "periode", "période", "periode_nl", "period"],
    "type_bien": ["cd_type_fr", "cd_type", "type", "type_bien", "cd_type_nl"],
    "mediane": ["ms_p_50", "ms_p50", "ms_price_p50", "mediane", "médiane", "median", "prix_median", "p50"],
    "nb_transactions": ["ms_transactions", "ms_trans", "nb_transactions", "transactions", "aantal",
                        "nombre_de_transactions"],
}
ALIAS["nis"] += ["code_ins", "ins", "codeins", "code_insee", "cod_ins", "nis5", "refnis_commune"]
ALIAS["commune"] += ["entite", "entité", "nom_commune", "libelle", "territoire", "nom_entite"]
ALIAS["annee"] += ["date", "an"]
ALIAS["type_bien"] += ["type_de_bien", "categorie", "catégorie", "type_batiment"]
ALIAS["mediane"] += ["prix_median", "prix_médian", "median_price", "mediane_prix"]
ALIAS_LONG = {"indicateur": ["indicateur", "variable", "libelle_indicateur", "indicator", "mesure", "serie"],
              "valeur": ["valeur", "value", "val", "donnee", "donnée", "valeur_indicateur"]}


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


def _cle(c):
    return normaliser(c).replace(" ", "_")


def _colonnes(df):
    bas = {_cle(c): c for c in df.columns}
    bas.update({c.lower().strip(): c for c in df.columns})
    trouve = {}
    for cible, alias in ALIAS.items():
        for a in alias:
            if a in bas or _cle(a) in bas:
                trouve[cible] = bas.get(a, bas.get(_cle(a)))
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
    if hasattr(chemin_ou_flux, "read"):
        return lire_contenu(chemin_ou_flux.read(), nom)
    with open(chemin_ou_flux, "rb") as f:
        return lire_contenu(f.read(), nom)


def _format_long_vers_large(df):
    """Format « une ligne par indicateur » (ex. WalStat) -> une ligne par commune / année / type de bien."""
    bas = {_cle(c): c for c in df.columns}
    ind = next((bas[_cle(a)] for a in ALIAS_LONG["indicateur"] if _cle(a) in bas), None)
    val = next((bas[_cle(a)] for a in ALIAS_LONG["valeur"] if _cle(a) in bas), None)
    if ind is None or val is None:
        return _colonnes_indicateurs_vers_large(df)
    d = df.copy()
    libelle = d[ind].astype(str)
    d["_type"] = libelle.map(type_maison)
    d["_mesure"] = libelle.map(lambda t: "mediane" if re.search(r"m[ée]dian|p ?50", t, re.I)
                               else ("nb_transactions" if re.search(r"nombre|transaction|aantal", t, re.I) else None))
    d = d[d["_type"].notna() & d["_mesure"].notna()]
    autres = [c for c in d.columns if c not in (ind, val, "_mesure")]
    large = d.pivot_table(index=autres, columns="_mesure", values=val, aggfunc="first").reset_index()
    large.columns.name = None
    return large.rename(columns={"_type": "type_bien"})


def _colonnes_indicateurs_vers_large(df):
    """Format « une colonne par indicateur » (ex. « Prix médian des maisons d'habitation ordinaires »)."""
    medianes = {c: type_maison(c) for c in df.columns
                if re.search(r"m[ée]dian|p ?50", str(c), re.I) and type_maison(c)}
    if not medianes or any(_cle(a) in {_cle(c) for c in df.columns} for a in ALIAS["mediane"]):
        return df
    nombres = {type_maison(c): c for c in df.columns
               if re.search(r"nombre|transaction", str(c), re.I) and type_maison(c)}
    fixes = [c for c in df.columns if c not in medianes and c not in nombres.values()]
    morceaux = []
    for col, t in medianes.items():
        m = df[fixes].copy()
        m["type_bien"], m["mediane"] = t, df[col]
        m["nb_transactions"] = df[nombres[t]] if t in nombres else None
        morceaux.append(m)
    return pd.concat(morceaux, ignore_index=True)


def _communes_seulement(df):
    """Les fichiers WalStat mêlent communes, arrondissements, provinces et région : on garde les communes."""
    col = next((c for c in df.columns if _cle(c) in ("type_entite", "type_d_entite", "niveau", "type_territoire")), None)
    if col is None:
        return df
    est_commune = df[col].astype(str).map(normaliser).str.contains("commune|gemeente|municipal")
    return df[est_commune] if est_commune.any() else df


def _annee_depuis_periode(df):
    """Fichiers annuels où l'année est dans la colonne « période » (ex. WalStat : periode = 2024)."""
    cles = {_cle(c) for c in df.columns}
    if any(_cle(a) in cles for a in ALIAS["annee"]):
        return df
    col = next((c for c in df.columns if _cle(c) in ("periode", "period", "cd_period")), None)
    if col is None:
        return df
    annees = df[col].astype(str).str.extract(r"((?:19|20)\d{2})")[0]
    return df.assign(annee=pd.to_numeric(annees, errors="coerce")).dropna(subset=["annee"]).drop(columns=[col])


def importer_medianes(con, chemin_ou_flux, nom=None, source="Statbel"):
    df = lire_fichier(chemin_ou_flux, nom) if not isinstance(chemin_ou_flux, pd.DataFrame) else chemin_ou_flux
    df = _format_long_vers_large(df)
    df = _communes_seulement(df)
    df = _annee_depuis_periode(df)
    c = _colonnes(df)
    df = df[df[c["mediane"]].notna()].copy()
    if "type_bien" in c:
        df["_type"] = df[c["type_bien"]].map(lambda t: t if t in ("maison", "maison_2_3_facades", "maison_4_facades")
                                             else type_maison(t))
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
        annee = int(str(r[c["annee"]])[:4])
        con.execute("INSERT OR REPLACE INTO medianes_statbel VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nis, annee, r["_periode"], r["_type"], float(str(r[c["mediane"]]).replace(",", ".")),
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


# ------------------------------------------------------- mise à jour automatique

USER_AGENT = "analyse-immo/1.0 (usage personnel)"
EXTENSIONS = (".csv", ".txt", ".xlsx", ".xls", ".zip")


def telecharger(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get_content_type() if hasattr(r.headers, "get_content_type") else ""


def lire_contenu(donnees: bytes, nom: str) -> pd.DataFrame:
    """CSV (séparateur détecté), Excel ou archive ZIP contenant l'un de ces formats."""
    nom = nom.lower()
    if nom.endswith(".zip") or donnees[:2] == b"PK" and not nom.endswith((".xlsx", ".xls")):
        with zipfile.ZipFile(io.BytesIO(donnees)) as z:
            interne = next((n for n in z.namelist() if n.lower().endswith((".csv", ".txt", ".xlsx", ".xls"))), None)
            if interne is None:
                raise ValueError("archive sans fichier de données")
            return lire_contenu(z.read(interne), interne)
    if nom.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(donnees))
    texte = donnees.decode("utf-8-sig", errors="replace")
    return pd.read_csv(io.StringIO(texte), sep=separateur(texte))


def separateur(texte):
    """Séparateur le plus fréquent sur la ligne d'en-tête (; | tabulation ,)."""
    entete = texte.splitlines()[0] if texte else ""
    return max([";", "|", "\t", ","], key=entete.count)


def liens_fichiers(html: str, base_url: str, mots_cles=()):
    """Liens vers des fichiers de données dans une page, les plus pertinents d'abord."""
    liens = []
    for href in re.findall(r'href="([^"]+)"', html):
        url = urllib.parse.urljoin(base_url, href)
        if url.lower().split("?")[0].endswith(EXTENSIONS):
            score = sum(m.lower() in url.lower() for m in mots_cles)
            liens.append((score, url))
    return [u for _, u in sorted(liens, key=lambda x: -x[0])]


def journal(con, source, statut, lignes=None, message=None):
    maintenant = datetime.now().isoformat(timespec="seconds")
    precedent = con.execute("SELECT date_succes FROM mises_a_jour WHERE source = ?", (source,)).fetchone()
    succes = maintenant if statut == "ok" else (precedent[0] if precedent else None)
    con.execute("INSERT OR REPLACE INTO mises_a_jour VALUES (?, ?, ?, ?, ?, ?)",
                (source, maintenant, statut, lignes, message, succes))
    con.commit()


def etat_mise_a_jour(con, source="statbel"):
    r = con.execute("SELECT date, statut, lignes, message, date_succes FROM mises_a_jour WHERE source = ?",
                    (source,)).fetchone()
    return dict(zip(("date", "statut", "lignes", "message", "date_succes"), r)) if r else None


def a_mettre_a_jour(con, p):
    etat = etat_mise_a_jour(con)
    if etat is None or etat["date"] is None:
        return True
    derniere = datetime.fromisoformat(etat["date"])
    return (datetime.now() - derniere).days >= p["statbel"]["frequence_jours"]


def calculer_indice(con, p, zone=None):
    """Indice annuel d'évolution des prix (base 100 la première année) à partir des médianes des
    maisons des communes de la zone ; enregistré pour les 4 trimestres de chaque année."""
    zone = zone or p["statbel"]["zone_indice"]
    communes = {r[0] for r in con.execute("SELECT DISTINCT commune FROM codes_postaux")}
    noms = {normaliser(c) for c in communes}
    lignes = con.execute("SELECT m.annee, m.mediane, c.nom_normalise FROM medianes_statbel m "
                         "JOIN communes c ON c.nis = m.nis WHERE m.type_bien LIKE 'maison%'").fetchall()
    df = pd.DataFrame(lignes, columns=["annee", "mediane", "nom"])
    if noms:
        df = df[df["nom"].isin(noms)]
    if df.empty:
        return 0
    serie = df.groupby("annee")["mediane"].median().sort_index()
    serie = serie / serie.iloc[0] * 100
    con.execute("DELETE FROM indices_prix WHERE zone = ? AND source LIKE 'Calculé%'", (zone,))
    for annee, v in serie.items():
        for t in range(1, 5):
            con.execute("INSERT OR REPLACE INTO indices_prix VALUES (?, ?, ?, ?)",
                        (zone, f"{annee}-T{t}", float(v), "Calculé depuis les médianes Statbel"))
    con.commit()
    return len(serie)


def mettre_a_jour(con, p, force=False, telecharger_fn=telecharger):
    """Télécharge et importe les médianes Statbel si nécessaire. Ne lève jamais d'exception."""
    if not force and not a_mettre_a_jour(con, p):
        return {**(etat_mise_a_jour(con) or {}), "statut": "à jour"}
    erreurs = []
    for src in p["statbel"]["sources"]:
        try:
            if src.get("type") == "page":
                html, _ = telecharger_fn(src["url"])
                liens = liens_fichiers(html.decode("utf-8", errors="replace"), src["url"], src.get("mots_cles", ()))
                if not liens:
                    raise ValueError("aucun fichier de données trouvé sur la page")
                url = liens[0]
            else:
                url = src["url"]
            donnees, _ = telecharger_fn(url)
            nom = urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1] or "export.csv"
            if "exports/csv" in url:
                nom = "export.csv"
            n = importer_medianes(con, lire_contenu(donnees, nom), source=src["nom"])
            if n == 0:
                raise ValueError("aucune médiane de maison reconnue dans le fichier")
            calculer_indice(con, p)
            journal(con, "statbel", "ok", n, src["nom"])
            return {"statut": "ok", "lignes": n, "source": src["nom"]}
        except urllib.error.HTTPError as e:
            erreurs.append(f"{src['nom']} : erreur HTTP {e.code}")
        except urllib.error.URLError as e:
            erreurs.append(f"{src['nom']} : source injoignable ({e.reason})")
        except Exception as e:     # format inattendu, fichier vide…
            erreurs.append(f"{src['nom']} : {type(e).__name__} — {e}")
    message = " | ".join(erreurs)
    journal(con, "statbel", "erreur", None, message)
    return {"statut": "erreur", "message": message}


def importer_codes_postaux_par_defaut(con, chemin):
    """Charge la table des codes postaux de la zone fournie avec l'application si elle est vide."""
    if con.execute("SELECT COUNT(*) FROM codes_postaux").fetchone()[0] == 0:
        return importer_codes_postaux(con, chemin)
    return 0
