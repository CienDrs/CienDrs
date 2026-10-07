"""Tests de l'interface Streamlit (exécution sans navigateur)."""
import pytest
from streamlit.testing.v1 import AppTest

from conftest import RACINE


@pytest.fixture
def app(base_exemple, monkeypatch):
    _, chemin = base_exemple
    monkeypatch.setenv("IMMO_BASE", str(chemin))

    def ouvrir(page, **etat):
        at = AppTest.from_file(str(RACINE / "app.py"), default_timeout=120)
        at.session_state["_page_test"] = page
        for k, v in etat.items():
            at.session_state[k] = v
        return at.run()
    return ouvrir


@pytest.mark.parametrize("page", ["biens", "ajouter", "fiche", "donnees", "parametres"])
def test_pages_sans_erreur(app, page):
    at = app(page, bien="21894138")
    assert not at.exception, [e.value for e in at.exception]


def test_fiche_affiche_decision(app):
    at = app("fiche", bien="21894138")
    labels = {m.label: m.value for m in at.metric}
    assert labels["Prix demandé"] == "225 000 €"
    assert labels["Décision"] in ("GO", "GO SOUS CONDITIONS", "NO-GO")


def test_ajout_par_texte_puis_verification(app):
    at = app("ajouter")
    at.text_area[0].input("Maison 2 façades, 7000 Mons. Prix : 165 000 €. Surface habitable : 110 m². "
                          "3 chambres. À rénover. PEB : G").run()
    next(b for b in at.button if b.label == "Extraire le texte").click().run()
    assert not at.exception
    assert at.session_state["brouillon"]["prix"] == 165_000
    next(b for b in at.button if "Valider" in b.label).click().run()
    assert not at.exception, [e.value for e in at.exception]
