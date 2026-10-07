"""Recette : l'exemple chiffré du cahier des charges (§9) est reproduit à l'euro près."""
import pytest

from immo import finance, parametres

P = parametres.charger()
EXEMPLE = finance.Hypotheses(prix_achat=160_000, travaux=50_000, prix_revente=292_500, valeur_en_l_etat=200_000,
                             taux_imprevus=0.15, duree_mois=6, portage_mensuel=1_500,
                             regime="personne_physique")


def test_bilan_central_exemple_cahier_des_charges():
    b = finance.bilan(EXEMPLE, P, "central")
    assert b["frais_acquisition"]["droits_enregistrement"] == 20_000
    assert b["frais_acquisition"]["total"] == 23_000
    assert b["travaux_total"] == pytest.approx(57_500)
    assert b["portage"]["total"] == 9_000
    assert b["prix_revient"] == pytest.approx(249_500)
    assert round(b["frais_revente"]["total"]) == 11_418
    assert round(b["plus_value"]) == 31_582
    assert round(b["impot"]) == 5_602


def test_bilan_prudent_exemple():
    b = finance.bilan(EXEMPLE, P, "prudent")
    assert b["prix_revente"] == pytest.approx(277_875)
    assert b["travaux_total"] == pytest.approx(69_000)
    assert b["portage"]["total"] == 13_500
    assert round(b["frais_revente"]["total"]) == 10_887
    assert round(b["plus_value"]) == 1_488


def test_prix_maximum_exemple():
    assert round(finance.prix_achat_maximum(EXEMPLE, P, "prudent")) == 134_656
    mdb = finance.Hypotheses(**{**EXEMPLE.to_dict(), "regime": "marchand_de_biens"})
    assert round(finance.prix_achat_maximum(mdb, P, "prudent")) == 144_274


def test_prix_maximum_donne_exactement_la_marge():
    pmax = finance.prix_achat_maximum(EXEMPLE, P, "prudent")
    h = finance.Hypotheses(**{**EXEMPLE.to_dict(), "prix_achat": pmax})
    assert finance.bilan(h, P, "prudent")["plus_value"] == pytest.approx(30_000, abs=0.05)


def test_decision_exemple_no_go():
    d = finance.decider(EXEMPLE, finance.Contexte("moyen", [], 6.0), P)
    assert d["statut"] == finance.NO_GO
    r = {x["code"]: x for x in d["regles"]}
    assert r["R1"]["ok"] is False and r["R2"]["ok"] is True
    assert round(d["prix_offre_recommande"]) == 134_656
    assert d["prix_max_borne_offre"]


def test_decision_go_et_conditions():
    bon = finance.Hypotheses(**{**EXEMPLE.to_dict(), "prix_achat": 125_000})
    assert finance.decider(bon, finance.Contexte("élevé", [], 3.0), P)["statut"] == finance.GO
    assert finance.decider(bon, finance.Contexte("faible", [], 3.0), P)["statut"] == finance.GO_SOUS_CONDITIONS
    assert finance.decider(bon, finance.Contexte("élevé", ["Aléa d'inondation"], 3.0), P)["statut"] == finance.NO_GO
    assert finance.decider(bon, finance.Contexte("élevé", [], 14.0), P)["statut"] == finance.NO_GO


def test_portage_detaille():
    h = finance.Hypotheses(prix_achat=200_000, travaux=40_000, prix_revente=320_000, revenu_cadastral=745,
                           taux_imprevus=0.1, duree_mois=6)
    port = finance.bilan(h, P)["portage"]
    base = 200_000 + 25_000 + 3_000 + 44_000
    assert port["interets"] == pytest.approx(base * 0.8 * 0.035 / 2)
    assert port["acte_credit"] == pytest.approx(base * 0.8 * 0.02)
    assert port["precompte_immobilier"] == pytest.approx(745 * 2.2 * 0.0125 * 27 / 2)
    # le prix maximum reste cohérent quand le portage dépend du prix
    pmax = finance.prix_achat_maximum(h, P, "prudent")
    hb = finance.Hypotheses(**{**h.to_dict(), "prix_achat": pmax})
    assert finance.bilan(hb, P, "prudent")["plus_value"] == pytest.approx(30_000, abs=1)
