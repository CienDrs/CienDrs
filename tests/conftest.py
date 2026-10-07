import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from immo import annonces, statbel  # noqa: E402


@pytest.fixture
def base_exemple(tmp_path):
    """Base remplie avec les données d'exemple + l'annonce réelle 21894138 (surface fictive de 125 m²)."""
    chemin = tmp_path / "test.sqlite"
    con = annonces.connecter(chemin)
    annonces.importer_csv(con, RACINE / "data" / "annonces_exemple.csv")
    annonces.importer_indices(con, RACINE / "data" / "indices_prix_exemple.csv")
    statbel.importer_codes_postaux(con, RACINE / "data" / "codes_postaux_zone_mons.csv")
    statbel.importer_medianes(con, RACINE / "data" / "statbel_medianes_exemple.csv", source="FICTIF")
    annonces.importer_page(con, RACINE / "tests" / "fixtures" / "immoweb_21894138.html", "2026-10-07")
    annonces.completer(con, "21894138", surface_habitable=125)
    annonces.maj_statut(con, 14, "2026-10-07")
    yield con, chemin
    con.close()
