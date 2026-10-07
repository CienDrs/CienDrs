"""Chargement des paramètres (immo/parametres.toml), modifiables sans développement (NF5)."""
import copy
import tomllib
from functools import lru_cache
from pathlib import Path

CHEMIN_DEFAUT = Path(__file__).with_name("parametres.toml")


@lru_cache(maxsize=4)
def _charger(chemin: str) -> dict:
    with open(chemin, "rb") as f:
        return tomllib.load(f)


def charger(chemin=CHEMIN_DEFAUT) -> dict:
    """Retourne une copie des paramètres (modifiable sans effet de bord)."""
    return copy.deepcopy(_charger(str(chemin)))
