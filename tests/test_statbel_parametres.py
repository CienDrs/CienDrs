import io
import urllib.error
import zipfile

import pandas as pd
import pytest

from conftest import RACINE
from immo import annonces, parametres, statbel

LONG = pd.DataFrame({
    "Code INS": ["53053"] * 4 + ["53028"] * 2, "Entité": ["Mons"] * 4 + ["Frameries"] * 2,
    "Année": [2024, 2024, 2025, 2025, 2024, 2025],
    "Indicateur": ["Prix médian des maisons d'habitation ordinaires (€)",
                   "Nombre de transactions de maisons d'habitation ordinaires",
                   "Prix médian des maisons d'habitation ordinaires (€)", "Prix médian des appartements (€)",
                   "Prix médian des maisons d'habitation ordinaires (€)",
                   "Prix médian des maisons d'habitation ordinaires (€)"],
    "Valeur": [198000, 400, 207000, 160000, 170000, 178500]})


@pytest.fixture
def con():
    c = annonces.connecter(":memory:")
    statbel.importer_codes_postaux(c, RACINE / "data" / "codes_postaux_zone_mons.csv")
    yield c
    c.close()


def csv_bytes(df, sep=";"):
    return df.to_csv(index=False, sep=sep).encode("utf-8")


def test_mise_a_jour_api_odwb(con):
    P = parametres.charger()
    urls = []

    def fake(url):
        urls.append(url)
        return csv_bytes(LONG), "text/csv"

    r = statbel.mettre_a_jour(con, P, telecharger_fn=fake)
    assert r["statut"] == "ok" and r["lignes"] == 4 and "odwb.be" in urls[0]
    assert statbel.ecart_au_median(con, 207000, "7000", "Mons", 2)["mediane"] == 207000
    assert statbel.ecart_au_median(con, 100000, "7012", "Jemappes", 2)["commune"] == "Mons"
    # indice calculé depuis les médianes (base 100 la première année)
    ind = dict(con.execute("SELECT periode, indice FROM indices_prix WHERE zone = 'Hainaut'").fetchall())
    assert ind["2024-T1"] == 100 and ind["2025-T4"] == pytest.approx((207000 + 178500) / (198000 + 170000) * 100)
    assert statbel.etat_mise_a_jour(con)["statut"] == "ok"
    # pas de nouvelle tentative avant la fréquence configurée
    assert statbel.mettre_a_jour(con, P, telecharger_fn=fake)["statut"] == "à jour" and len(urls) == 1


def test_mise_a_jour_repli_sur_la_page_statbel(con):
    P = parametres.charger()
    zip_ = io.BytesIO()
    with zipfile.ZipFile(zip_, "w") as z:
        z.writestr("TF_IMMO_COMMUNES.txt", LONG.to_csv(index=False, sep="|"))

    def fake(url):
        if "odwb" in url:
            raise urllib.error.HTTPError(url, 503, "indisponible", {}, None)
        if url.endswith("prix-de-limmobilier"):
            return (b'<a href="/files/autre.pdf">x</a><a href="/sites/default/files/files/opendata/immo/'
                    b'vastgoed_communes.zip">open data</a>'), "text/html"
        assert url == "https://statbel.fgov.be/sites/default/files/files/opendata/immo/vastgoed_communes.zip"
        return zip_.getvalue(), "application/zip"

    r = statbel.mettre_a_jour(con, P, force=True, telecharger_fn=fake)
    assert r["statut"] == "ok" and r["source"].startswith("Statbel")


def test_mise_a_jour_echec_signale(con):
    P = parametres.charger()

    def fake(url):
        raise urllib.error.URLError("blocked")

    r = statbel.mettre_a_jour(con, P, force=True, telecharger_fn=fake)
    assert r["statut"] == "erreur" and "injoignable" in r["message"]
    assert statbel.etat_mise_a_jour(con)["statut"] == "erreur"


def test_parametres_surcharges():
    assert parametres.charger()["strategie"]["decote_cible"] == 0.20
    parametres.enregistrer({"strategie": {"decote_cible": 0.25}, "travaux": {"imprevus": {"renovation_lourde": 0.3}}})
    P = parametres.charger()
    assert P["strategie"]["decote_cible"] == 0.25 and P["strategie"]["plus_value_min"] == 30000
    assert P["travaux"]["imprevus"]["renovation_lourde"] == 0.3 and P["travaux"]["imprevus"]["rafraichissement"] == 0.10
    parametres.reinitialiser("strategie")
    assert parametres.charger()["strategie"]["decote_cible"] == 0.20
    assert parametres.charger()["travaux"]["imprevus"]["renovation_lourde"] == 0.3
    parametres.reinitialiser()
    assert parametres.surcharges() == {}
