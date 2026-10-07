import json

import pytest

from immo import analyse, estimation, extraction_texte, finance, geo, parametres, statbel, travaux

P = parametres.charger()
AUJ = "2026-10-07"


def test_statbel_rattachement_et_ecart(base_exemple):
    con, _ = base_exemple
    assert statbel.commune_du_bien(con, "7012", "Jemappes")[1] == "Mons"      # section -> commune fusionnée
    assert statbel.commune_du_bien(con, None, "Saint Ghislain")[1] == "Saint-Ghislain"
    e = statbel.ecart_au_median(con, 225_000, "7000", "Mons", facades=2)
    assert e["mediane"] == 205_000 and e["type_bien"] == "maison_2_3_facades"
    assert e["ecart"] == pytest.approx(225_000 / 205_000 - 1)
    assert statbel.ecart_au_median(con, 400_000, "7000", "Mons", facades=4)["mediane"] == 340_000


def test_statbel_type_maison():
    assert statbel.type_maison("Maisons d'habitation ordinaires") == "maison_2_3_facades"
    assert statbel.type_maison("Villas, bungalows, maisons de campagne") == "maison_4_facades"
    assert statbel.type_maison("Appartements, flats, studios") is None


def test_travaux_ratios():
    t = travaux.estimer(100, "À rénover", "F", "C", p=P)
    assert t["niveau"] == "renovation_moyenne" and t["classes_peb_gagnees"] == 3
    assert t["central"] == pytest.approx((850 + 3 * 40) * 100)
    assert travaux.estimer(100, "Comme neuf", "B", "C", p=P)["central"] == 0


def test_estimation_valeurs(base_exemple):
    con, _ = base_exemple
    bien, df = analyse.charger_bien(con, "21894138", AUJ)
    en_l_etat, apres = estimation.estimer_valeurs(bien, df, P)
    assert en_l_etat["disponible"] and en_l_etat["n"] >= 5
    assert en_l_etat["basse"] <= en_l_etat["centrale"] <= en_l_etat["haute"]
    assert apres["centrale"] > en_l_etat["centrale"]                         # rénové vaut plus que « à rafraîchir »
    assert "21894138" not in set(en_l_etat["comparables"]["immoweb_id"])     # le bien n'est pas son propre comparable


def test_analyse_complete(base_exemple):
    con, _ = base_exemple
    res = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert res["prix_m2"] == pytest.approx(1800)
    assert res["decision"]["statut"] in (finance.GO, finance.GO_SOUS_CONDITIONS, finance.NO_GO)
    assert res["hypotheses"]["prix_achat"] == 225_000
    assert "surface du terrain (m²)" in res["champs_manquants"]
    # surcharges et hypothèses enregistrées
    analyse.enregistrer_hypotheses(con, "21894138", {"prix_achat": 120_000, "travaux": 20_000})
    res2 = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert res2["hypotheses"]["prix_achat"] == 120_000
    # risque manuel bloquant -> NO-GO
    analyse.enregistrer_risques_manuels(con, "21894138", ["Pollution du sol (BDES)"])
    res3 = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert res3["decision"]["statut"] == finance.NO_GO
    # enregistrement de l'analyse (sérialisable)
    analyse.enregistrer_analyse(con, res3)
    stocke = json.loads(con.execute("SELECT resultat FROM analyses").fetchone()[0])
    assert stocke["decision"]["statut"] == finance.NO_GO


def test_analyse_sans_surface(base_exemple):
    con, _ = base_exemple
    con.execute("UPDATE annonces SET surface_habitable = NULL WHERE immoweb_id = '21894138'")
    res = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert res["decision"] is None and res["manquants_decision"]


def test_identifiant_manuel(base_exemple):
    con, _ = base_exemple
    assert analyse.nouvel_identifiant_manuel(con) == "M0001"


# ------------------------------------------------------------------ extraction texte

TEXTE = """Maison 3 façades à vendre - 7080 Frameries
Prix : 189.000 €
Surface habitable : 135 m² - Terrain de 4 a 50 ca
3 chambres, 1 salle de bains. Construite en 1932. À rénover.
PEB : F (452 kWh/m²/an). Chauffage central au gaz. Revenu cadastral : 812 €.
Contact : 0495 12 34 56 ou agence@exemple.be"""


def test_extraction_regex():
    r = extraction_texte.extraire(TEXTE, utiliser_llm=False)
    c = r["champs"]
    assert (c["prix"], c["surface_habitable"], c["surface_terrain"]) == (189_000, 135, 450)
    assert (c["chambres"], c["facades"], c["annee_construction"]) == (3, 3, 1932)
    assert (c["peb_lettre"], c["peb_kwh_m2"], c["etat"]) == ("F", 452, "À rénover")
    assert (c["code_postal"], c["commune"], c["revenu_cadastral"]) == ("7080", "Frameries", 812)
    assert "0495" not in c["description"] and "agence@exemple.be" not in c["description"]


class _Bloc:
    def __init__(self, texte):
        self.type, self.text = "text", texte


class _FauxClient:
    def __init__(self, reponse, stop="end_turn"):
        self.appels = []
        outer = self

        class Msgs:
            def create(self, **kw):
                outer.appels.append(kw)
                return type("R", (), {"stop_reason": stop, "content": [_Bloc(json.dumps(reponse))]})()
        self.beta = type("B", (), {"messages": Msgs()})()


def test_extraction_llm_complete_regex():
    llm = {k: None for k in extraction_texte.CHAMPS} | {"surface_habitable": 140, "titre": "Maison de maître"}
    client = _FauxClient(llm)
    r = extraction_texte.extraire(TEXTE, client=client)
    assert r["methode"].startswith("API Claude")
    assert r["champs"]["surface_habitable"] == 140 and r["champs"]["prix"] == 189_000
    appel = client.appels[0]
    assert appel["model"] == "claude-opus-5-5" and appel["fallbacks"] == "default"
    assert appel["output_config"]["format"]["type"] == "json_schema"


def test_extraction_llm_refus_bascule_regex():
    r = extraction_texte.extraire(TEXTE, client=_FauxClient({}, stop="refusal"))
    assert r["methode"] == "expressions régulières" and r["avertissements"]
    assert r["champs"]["prix"] == 189_000


# ------------------------------------------------------------------ géo

def test_risques_et_geocodage_simules(base_exemple):
    con, _ = base_exemple

    def http(url):
        if "nominatim" in url:
            return [{"lat": "50.4467", "lon": "3.9429"}]
        if "ALEA_INOND" in url:
            return {"features": [{"attributes": {"OBJECTID": 1, "VALEUR": "Aléa élevé"}}]}
        if "CONTRAINTES" in url:
            return {"features": []}
        raise geo.SourceIndisponible("service en panne")

    r = geo.verifier_risques(50.4467, 3.9429, P, http)
    assert r["alea_inondation"]["bloquant"] and not r["contraintes_geotechniques"]["touche"]
    assert r["plan_de_secteur"]["erreur"]
    faible = geo.verifier_risques(50.4, 3.9, P, lambda u: {"features": [{"attributes": {"VALEUR": "Aléa faible"}}]})
    assert faible["alea_inondation"]["touche"] and not faible["alea_inondation"]["bloquant"]

    con.execute("UPDATE annonces SET latitude = NULL, longitude = NULL WHERE immoweb_id = '21894138'")
    bien, _ = analyse.charger_bien(con, "21894138", AUJ)
    messages = geo.enrichir(con, bien, P, http)
    assert any("indisponible" in m for m in messages)
    res = analyse.analyser(con, "21894138", P, aujourd_hui=AUJ)
    assert res["bien"]["latitude"] == pytest.approx(50.4467)
    assert res["decision"]["statut"] == finance.NO_GO                         # aléa élevé -> bloquant
