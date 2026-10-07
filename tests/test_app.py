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


def test_parametres_formulaires_sans_json(app):
    at = app("parametres")
    assert not at.json                                      # plus d'affichage JSON brut
    assert len(at.tabs) == 7
    champ = next(n for n in at.number_input if n.label.startswith("Décote visée"))
    assert champ.value == pytest.approx(20.0)
    champ.set_value(25.0)
    next(b for b in at.button if b.label == "💾 Enregistrer" and b.key == "e1").click().run()
    assert not at.exception, [e.value for e in at.exception]
    from immo import parametres
    assert parametres.charger()["strategie"]["decote_cible"] == pytest.approx(0.25)


def test_donnees_sans_import_statbel_manuel(app):
    at = app("donnees")
    assert not at.exception
    assert not any("Statbel" in (u.label or "") for u in at.get("file_uploader"))


def test_base_de_donnees_reperage(app):
    at = app("biens")
    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value.endswith("Base de données")
    labels = {m.label: m.value for m in at.metric}
    assert int(labels["Biens dans la base"]) == 181
    assert any(r.label == "Référence" for r in at.radio)
    # le seuil change le nombre de GO
    go_20 = int(labels["Repérés GO"])
    next(s for s in at.slider if s.label.startswith("GO si")).set_value(5).run()
    assert int({m.label: m.value for m in at.metric}["Repérés GO"]) > go_20


def test_fiche_onglets_et_travaux(app):
    at = app("fiche", bien="21894138")
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs][:6] == ["Annonce", "Repérage et prix", "Estimation des travaux", "Rentabilité",
                                              "Risques", "Historique"]
    next(b for b in at.button if b.label == "Appliquer le modèle").click().run()
    assert not at.exception, [e.value for e in at.exception]
    totaux = {m.label: m.value for m in at.metric}
    assert totaux["Total TVAC"] != "0 €"
    next(b for b in at.button if b.label.startswith("💾 Enregistrer le chantier")).click().run()
    assert not at.exception, [e.value for e in at.exception]
    from immo import annonces, chantier
    import os
    c = annonces.connecter(os.environ["IMMO_BASE"])
    assert chantier.lire(c, "21894138")["lignes"]


def test_fiche_avec_historique_de_prix(base_exemple, app):
    con, _ = base_exemple
    from immo import annonces
    annonces.enregistrer_observation(con, "21894138", 215000, "2026-10-08")      # baisse de prix -> graphique
    at = app("fiche", bien="21894138")
    assert not at.exception, [e.value for e in at.exception]
