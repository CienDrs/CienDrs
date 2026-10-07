import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import base_annonces as ba  # noqa: E402

AUJ = "2026-10-07"


class TestBaseAnnonces(unittest.TestCase):
    def setUp(self):
        self.con = ba.connecter(":memory:")
        commun = dict(commune="Frameries", latitude=50.408, longitude=3.897, surface_habitable=100,
                      chambres=3, type_bien="maison", etat="À rénover", peb_lettre="F")
        # annonce en ligne avec deux baisses de prix
        ba.enregistrer_observation(self.con, "A1", 200000, "2026-05-01", date_publication="2026-05-01", **commun)
        ba.enregistrer_observation(self.con, "A1", 200000, "2026-06-01", **commun)
        ba.enregistrer_observation(self.con, "A1", 190000, "2026-07-01", **commun)
        ba.enregistrer_observation(self.con, "A1", 180000, AUJ, **commun)
        # annonce retirée il y a plus d'un an -> prix actualisé
        ba.enregistrer_observation(self.con, "A2", 150000, "2024-03-01", date_publication="2024-01-15", **commun)
        ba.enregistrer_observation(self.con, "A2", 150000, "2025-02-10", **commun)
        self.con.executemany("INSERT INTO indices_prix VALUES ('Hainaut', ?, ?, 'test')",
                             [("2025-T1", 100.0), ("2026-T3", 110.0)])
        self.con.commit()
        ba.maj_statut(self.con, 14, AUJ)
        self.df = ba.tableau_annonces(self.con, AUJ).set_index("immoweb_id")

    def tearDown(self):
        self.con.close()

    def test_historique_ne_garde_que_les_changements(self):
        n = self.con.execute("SELECT COUNT(*) FROM historique_prix WHERE immoweb_id='A1'").fetchone()[0]
        self.assertEqual(n, 3)
        a1 = self.df.loc["A1"]
        self.assertEqual(a1.nb_baisses_prix, 2)
        self.assertAlmostEqual(a1.variation_prix_pct, -10.0)
        self.assertEqual(a1.prix_m2, 1800)

    def test_statut_et_duree_en_ligne(self):
        self.assertTrue(self.df.loc["A1"].en_ligne)
        self.assertFalse(self.df.loc["A2"].en_ligne)
        self.assertEqual(self.df.loc["A2"].jours_en_ligne, 392)  # 15/01/2024 -> 10/02/2025
        self.assertEqual(self.df.loc["A1"].jours_en_ligne, 159)

    def test_actualisation_si_prix_vieux_d_un_an(self):
        self.assertAlmostEqual(self.df.loc["A2"].prix_actualise, 165000)
        self.assertAlmostEqual(self.df.loc["A1"].prix_actualise, 180000)  # en ligne : pas d'actualisation

    def test_retour_en_ligne(self):
        ba.enregistrer_observation(self.con, "A2", 145000, AUJ)
        df = ba.tableau_annonces(self.con, AUJ).set_index("immoweb_id")
        self.assertTrue(df.loc["A2"].en_ligne)

    def test_situer(self):
        res = ba.situer(self.df.reset_index(), prix=160000, surface=100, chambres=3, lat=50.408, lon=3.897)
        self.assertEqual(len(res["comparables"]), 2)
        self.assertAlmostEqual(res["statistiques"].loc["Prix/m² actualisé (€)", "mediane"], 1725)
        self.assertAlmostEqual(res["ecart_mediane_pct"], (1600 / 1725 - 1) * 100)

    def test_extraction_page(self):
        html = ('<script>window.classified = {"id": 999, "price": {"mainValue": 175000}, "property": '
                '{"type": "HOUSE", "bedroomCount": 3, "netHabitableSurface": 120, "land": {"surface": 300},'
                ' "building": {"condition": "TO_RENOVATE", "facadeCount": 3}, "location": {"locality": "Mons",'
                ' "postalCode": "7000", "latitude": 50.45, "longitude": 3.95}, "description": "Belle maison"},'
                ' "transaction": {"certificates": {"epcScore": "F", "primaryEnergyConsumptionPerSqm": 450}},'
                ' "publication": {"creationDate": "2026-09-01T10:00:00"}};</script>')
        d = ba.extraire_page_immoweb(html)
        self.assertEqual((d["immoweb_id"], d["prix"], d["etat"], d["peb_lettre"], d["date_publication"]),
                         ("999", 175000, "À rénover", "F", "2026-09-01"))
        self.assertEqual(d["type_bien"], "maison")


if __name__ == "__main__":
    unittest.main()
