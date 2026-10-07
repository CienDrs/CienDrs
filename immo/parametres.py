"""Paramètres de l'outil, modifiables sans développement (NF5).

Les valeurs par défaut sont dans immo/parametres.toml ; les valeurs modifiées depuis la page
« Paramètres » de l'application sont enregistrées à part (data/parametres_utilisateur.json, ou le
chemin de la variable d'environnement IMMO_PARAMETRES_UTILISATEUR) et priment sur les défauts.
"""
import copy
import json
import os
import tomllib
from functools import lru_cache
from pathlib import Path

CHEMIN_DEFAUT = Path(__file__).with_name("parametres.toml")
RACINE = Path(__file__).resolve().parents[1]


def fichier_utilisateur() -> Path:
    return Path(os.environ.get("IMMO_PARAMETRES_UTILISATEUR", RACINE / "data" / "parametres_utilisateur.json"))


@lru_cache(maxsize=4)
def _charger(chemin: str) -> dict:
    with open(chemin, "rb") as f:
        return tomllib.load(f)


def defauts(chemin=CHEMIN_DEFAUT) -> dict:
    return copy.deepcopy(_charger(str(chemin)))


def _fusion(base: dict, surcharge: dict) -> dict:
    for k, v in surcharge.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _fusion(base[k], v)
        else:
            base[k] = v
    return base


def surcharges() -> dict:
    f = fichier_utilisateur()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def charger(chemin=CHEMIN_DEFAUT) -> dict:
    """Paramètres effectifs : défauts du fichier TOML + valeurs modifiées par l'utilisateur."""
    return _fusion(defauts(chemin), surcharges())


def enregistrer(modifications: dict):
    """Ajoute / remplace des valeurs modifiées (dictionnaire imbriqué, ex. {"strategie": {"decote_cible": 0.25}})."""
    f = fichier_utilisateur()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(_fusion(surcharges(), modifications), ensure_ascii=False, indent=2), encoding="utf-8")


def reinitialiser(section=None):
    """Revient aux valeurs par défaut (toutes, ou celles d'une section)."""
    f = fichier_utilisateur()
    if section is None:
        f.unlink(missing_ok=True)
        return
    s = surcharges()
    s.pop(section, None)
    f.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
