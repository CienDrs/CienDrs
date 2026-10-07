"""V1.1 : photos, repérage GO / NO-GO, chantier poste par poste, collecte (dossier d'import)."""
import shutil

import pytest

from conftest import RACINE
from immo import analyse, annonces, chantier, collecte, parametres, reperage

AUJ = "2026-10-07"
P = parametres.charger()


def test_photos_extraites_et_enregistrees(base_exemple):
    con, _ = base_exemple
    photos = annonces.lire_photos(con, "21894138")
    assert len(photos) == 22
    assert photos[0]["miniature"].endswith(".jpg") and "/300x300/" in photos[0]["miniature"]
    assert "/736x736/" in photos[0]["grande"]


def _base_reperage():
    con = annonces.connecter(":memory:")
    commun = dict(commune="Mons", latitude=50.45, longitude=3.95, chambres=3, type_bien="maison", etat="Bon",
                  facades=2, date_publication="2026-09-01")
    for i, prix in enumerate([200000, 205000, 210000, 195000, 200000, 190000], start=1):
        annonces.enregistrer_observation(con, f"C{i}", prix, AUJ, surface_habitable=100, **commun)
    annonces.enregistrer_observation(con, "CIBLE", 150000, AUJ, surface_habitable=100, **commun)   # 1 500 €/m²
    annonces.enregistrer_observation(con, "CHER", 210000, AUJ, surface_habitable=100, **commun)
    return con


def test_reperage_go_no_go():
    con = _base_reperage()
    df = annonces.tableau_annonces(con, AUJ)
    r = reperage.reperer_tous(df, P).set_index("immoweb_id")
    assert r.loc["CIBLE", "reperage"] == reperage.GO
    assert r.loc["CIBLE", "ecart_reference"] == pytest.approx(1500 / 2000 - 1)      # médiane des autres : 2 000 €/m²
    assert r.loc["CHER", "reperage"] == reperage.NO_GO
    # seuil plus strict : la cible n'est plus GO
    r2 = reperage.reperer_tous(df, P, seuil=0.30).set_index("immoweb_id")
    assert r2.loc["CIBLE", "reperage"] == reperage.NO_GO
    # trop peu de comparables
    r3 = reperage.reperer_tous(df, P, min_comparables=10).set_index("immoweb_id")
    assert (r3["reperage"] == reperage.INSUFFISANT).all()


def test_reperage_ramene_au_meme_etat():
    con = _base_reperage()
    annonces.completer(con, "CIBLE", etat="À rénover")          # comparables « Bon » ramenés à « À rénover » (× 0,75)
    df = annonces.tableau_annonces(con, AUJ)
    res = reperage.reperer_bien(df.set_index("immoweb_id").loc["CIBLE"].to_dict() | {"immoweb_id": "CIBLE"}, df, P)
    assert res["reference_m2"] == pytest.approx(2000 * 0.75)
    assert res["statut"] == reperage.NO_GO                        # 1 500 €/m² = prix normal pour une maison à rénover


def test_quantites_proposees():
    bien = {"surface_habitable": 120, "nb_etages": 2, "salles_de_bain": 2, "annee_construction": 1930}
    q = chantier.quantite_proposee
    assert q("SH", bien) == 120 and q("SH*3.5", bien) == 420 and q("SH/12", bien) == 10
    assert q("toit", bien) == 78 and q("rdc", bien) == 60 and q("conteneur", bien) == 3
    assert q("salles_eau", bien) == 2 and q("amiante", bien) == 1 and q("a_mesurer", bien) is None
    assert q("amiante", {**bien, "annee_construction": 2010}) == 0


def test_calcul_chantier():
    cfg = {"lignes": [
        {"code": "plafonnage", "quantite": 100, "niveau": "bas", "tva": 0.06, "categorie": "Plafonnage", "poste": "p"},
        {"code": "chaudiere_gaz", "quantite": 1, "niveau": "haut", "tva": 0.21, "categorie": "Chauffage", "poste": "c"},
        {"code": "carrelage", "quantite": 50, "niveau": "moyen", "prix_saisi": 48, "tva": 0.06, "categorie": "Sols",
         "poste": "s"},
        {"code": "", "quantite": 2, "prix_saisi": 500, "tva": 0.21, "categorie": "Autre", "poste": "libre"}],
        "imprevus": 0.1, "duree_travaux_mois": 4}
    c = chantier.calculer(cfg)
    htva = 100 * 15 + 6000 + 50 * 48 + 1000
    tva = 1500 * 0.06 + 6000 * 0.21 + 2400 * 0.06 + 1000 * 0.21
    assert c["total_htva"] == pytest.approx(htva) and c["total_tva"] == pytest.approx(tva)
    assert c["total_general"] == pytest.approx((htva + tva) * 1.1)
    assert list(c["lignes"]["origine"]) == ["Bas", "Haut", "devis", "devis"]


def test_modele_et_rentabilite(base_exemple):
    con, _ = base_exemple
    bien, _ = analyse.charger_bien(con, "21894138", AUJ)
    cfg = chantier.appliquer_modele("renovation_lourde", bien)
    codes = {l["code"] for l in cfg["lignes"]}
    assert {"toiture_complete", "chassis_m2", "electricite", "chape", "pac"} <= codes
    analyse.enregistrer_hypotheses(con, "21894138", {"travaux": 1.0, "prix_achat": 150000})
    chantier.enregistrer(con, "21894138", cfg)
    res = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    total = chantier.calculer(cfg)["total_tvac"]
    assert res["hypotheses"]["travaux"] == pytest.approx(total)                  # le chantier remplace l'hypothèse
    assert res["hypotheses"]["prix_achat"] == 150000                             # les autres hypothèses restent
    assert res["hypotheses"]["duree_mois"] == cfg["duree_travaux_mois"] + P["travaux"]["delai_revente_mois"]
    assert res["decision"]["bilans"]["central"]["travaux_total"] == pytest.approx(total * (1 + cfg["imprevus"]))


def test_collecte_dossier(base_exemple, tmp_path):
    con, _ = base_exemple
    p = {**P, "collecte": {**P["collecte"], "dossier_import": str(tmp_path), "sources": ["dossier", "api"]}}
    con.execute("DELETE FROM annonces WHERE immoweb_id = '21894138'")
    con.commit()
    shutil.copy(RACINE / "tests" / "fixtures" / "immoweb_21894138.html", tmp_path / "annonce.html")
    (tmp_path / "abime.html").write_text("<html>pas une annonce</html>", encoding="utf-8")
    bilan = {r["source"]: r for r in collecte.executer(con, p, AUJ)}
    d = bilan["dossier"]
    assert d["nouvelles"] == ["21894138"] and len(d["erreurs"]) == 1
    assert (tmp_path / "traites" / "annonce.html").exists() and (tmp_path / "erreurs" / "abime.html").exists()
    assert bilan["api"]["statut"] == "non configurée"
    j = collecte.journal(con)
    assert set(j["source"]) == {"dossier", "api"}
    # deuxième passage : dossier vide, rien de nouveau
    assert collecte.executer(con, {**p, "collecte": {**p["collecte"], "sources": ["dossier"]}}, AUJ)[0]["vues"] == 0


def test_bien_reel_jamais_compare_aux_exemples_fictifs(base_exemple):
    con, _ = base_exemple
    con.execute("UPDATE annonces SET source = 'exemple fictif' WHERE source = 'test'")
    res = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert not res["valeur_en_l_etat"]["disponible"] and res["reperage"]["statut"] == reperage.INSUFFISANT
    df = annonces.tableau_annonces(con, AUJ)
    exemple = df[df["source"] == "exemple fictif"].iloc[0].to_dict()
    assert reperage.reperer_bien(exemple, df, P)["n_comparables"] > 0       # les exemples restent comparables entre eux
