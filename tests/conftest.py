import os
import sys
import tempfile
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
# Les tests n'utilisent ni le réseau ni les paramètres personnels de l'utilisateur
os.environ["IMMO_HORS_LIGNE"] = "1"
os.environ["IMMO_PARAMETRES_UTILISATEUR"] = str(Path(tempfile.mkdtemp()) / "parametres_utilisateur.json")

from immo import annonces, statbel  # noqa: E402


@pytest.fixture
def base_exemple(tmp_path):
    """Base remplie avec les données d'exemple + l'annonce réelle 21894138 (surface fictive de 125 m²)."""
    chemin = tmp_path / "test.sqlite"
    con = annonces.connecter(chemin)
    annonces.importer_csv(con, RACINE / "data" / "annonces_exemple.csv")
    annonces.importer_indices(con, RACINE / "data" / "indices_prix_exemple.csv")
    statbel.importer_codes_postaux(con, RACINE / "data" / "codes_postaux_zone_mons.csv")
    statbel.importer_medianes(con, RACINE / "tests" / "fixtures" / "statbel_medianes_exemple.csv", source="FICTIF")
    annonces.importer_page(con, RACINE / "tests" / "fixtures" / "immoweb_21894138.html", "2026-10-07")
    annonces.completer(con, "21894138", surface_habitable=125)
    annonces.maj_statut(con, 14, "2026-10-07")
    yield con, chemin
    con.close()


@pytest.fixture(autouse=True)
def parametres_par_defaut():
    """Chaque test démarre avec les paramètres par défaut."""
    from immo import parametres
    parametres.reinitialiser()
    yield
    parametres.reinitialiser()
