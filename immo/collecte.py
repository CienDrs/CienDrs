"""Collecte automatique des annonces (cahier des charges §4.1, exigences C1 à C9).

À planifier toutes les heures (cron, planificateur de tâches) ou à lancer en continu :
  python -m immo.collecte            # une exécution
  python -m immo.collecte --boucle   # une exécution toutes les `intervalle_minutes`

Sources disponibles (parametres.toml [collecte] sources) :
  - "dossier" : importe les pages d'annonces enregistrées (.html) et les fichiers CSV déposés dans le
    dossier d'import (par vous, une extension de navigateur ou un autre outil), puis les range dans
    « traites/ » (ou « erreurs/ ») ;
  - "api" : accès officiel aux données d'annonces, à brancher quand un accès est obtenu (M5).
La lecture automatique des pages d'Immoweb (M7) n'est pas incluse dans cette version.
"""
import argparse
import csv
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

from immo import annonces, parametres

RACINE = Path(__file__).resolve().parents[1]


class SourceNonConfiguree(Exception):
    pass


def _dossier(p):
    d = Path(p["collecte"]["dossier_import"])
    return d if d.is_absolute() else RACINE / d


def collecter_dossier(con, p, aujourd_hui=None):
    """Importe chaque page .html / fichier .csv du dossier d'import ; retourne les compteurs."""
    dossier = _dossier(p)
    dossier.mkdir(parents=True, exist_ok=True)
    avant = {r[0]: r[1] for r in con.execute(
        "SELECT a.immoweb_id, (SELECT prix FROM historique_prix h WHERE h.immoweb_id = a.immoweb_id "
        "ORDER BY date_observation DESC LIMIT 1) FROM annonces a")}
    vues, erreurs, ids = 0, [], set()
    for f in sorted(dossier.iterdir()):
        if not f.is_file() or f.suffix.lower() not in (".html", ".htm", ".csv"):
            continue
        try:
            if f.suffix.lower() == ".csv":
                vues += annonces.importer_csv(con, f)
                with open(f, encoding="utf-8") as fh:
                    ids |= {ligne["immoweb_id"] for ligne in csv.DictReader(fh)}
            else:
                ids.add(annonces.importer_page(con, f, aujourd_hui))
                vues += 1
            cible = dossier / "traites"
        except Exception as e:      # un fichier illisible ne bloque pas les autres
            erreurs.append(f"{f.name} : {type(e).__name__} — {e}")
            cible = dossier / "erreurs"
        cible.mkdir(exist_ok=True)
        shutil.move(str(f), cible / f.name)
    apres = {r[0]: r[1] for r in con.execute(
        "SELECT a.immoweb_id, (SELECT prix FROM historique_prix h WHERE h.immoweb_id = a.immoweb_id "
        "ORDER BY date_observation DESC LIMIT 1) FROM annonces a")}
    nouvelles = [i for i in ids if i in apres and i not in avant]
    modifiees = [i for i in ids if i in avant and apres.get(i) != avant[i]]
    return {"vues": vues, "nouvelles": nouvelles, "modifiees": modifiees, "retirees": [], "erreurs": erreurs,
            "couverture_complete": False}


def collecter_api(con, p, aujourd_hui=None):
    """Point d'entrée pour un accès officiel aux annonces (API sous accord, M5)."""
    url, cle = p["collecte"].get("api_url"), os.environ.get(p["collecte"].get("api_cle_variable", ""), "")
    if not url or not cle:
        raise SourceNonConfiguree("aucun accès API configuré (api_url et clé) : demande d'accès en cours")
    raise SourceNonConfiguree("connecteur API à développer selon la documentation fournie avec l'accès")


SOURCES = {"dossier": collecter_dossier, "api": collecter_api}


def journaliser(con, debut, source, statut, r=None, erreurs=""):
    r = r or {}
    con.execute("INSERT OR REPLACE INTO collectes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (debut, datetime.now().isoformat(timespec="seconds"), source, statut, r.get("vues", 0),
                 len(r.get("nouvelles", [])), len(r.get("modifiees", [])), len(r.get("retirees", [])), erreurs))
    con.commit()


def executer(con, p=None, aujourd_hui=None):
    """Une exécution de collecte sur toutes les sources activées. Ne lève pas d'exception."""
    p = p or parametres.charger()
    bilan = []
    for nom in p["collecte"]["sources"]:
        debut = datetime.now().isoformat(timespec="microseconds")
        try:
            r = SOURCES[nom](con, p, aujourd_hui)
            if r.get("couverture_complete"):
                r["retirees"] = annonces.maj_statut(con, 1, aujourd_hui or date.today().isoformat())
            journaliser(con, debut, nom, "ok" if not r["erreurs"] else "erreur", r, " | ".join(r["erreurs"]))
            bilan.append({"source": nom, "statut": "ok", **r})
        except SourceNonConfiguree as e:
            journaliser(con, debut, nom, "non configurée", erreurs=str(e))
            bilan.append({"source": nom, "statut": "non configurée", "message": str(e)})
        except Exception as e:
            journaliser(con, debut, nom, "erreur", erreurs=f"{type(e).__name__} — {e}")
            bilan.append({"source": nom, "statut": "erreur", "message": str(e)})
    return bilan


def journal(con, limite=50):
    import pandas as pd
    return pd.read_sql("SELECT * FROM collectes ORDER BY debut DESC LIMIT ?", con, params=(limite,))


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--base", default=os.environ.get("IMMO_BASE", annonces.BASE_PAR_DEFAUT))
    a.add_argument("--boucle", action="store_true", help="relancer la collecte à intervalle régulier")
    args = a.parse_args()
    while True:
        p = parametres.charger()
        con = annonces.connecter(args.base)
        for r in executer(con, p):
            print(f"[{datetime.now():%Y-%m-%d %H:%M}] {r['source']} : {r['statut']} — "
                  + (f"{r.get('vues', 0)} vues, {len(r.get('nouvelles', []))} nouvelles, "
                     f"{len(r.get('modifiees', []))} modifiées" if r["statut"] == "ok" else r.get("message", "")))
        con.close()
        if not args.boucle:
            break
        time.sleep(p["collecte"]["intervalle_minutes"] * 60)


if __name__ == "__main__":
    main()
