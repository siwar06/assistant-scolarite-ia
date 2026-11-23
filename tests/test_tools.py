import unittest

from src import tools


class TestCalendrier(unittest.TestCase):

    def test_module_exact(self):
        result = tools.get_calendrier("Réseaux")
        self.assertIn("18/01/2027 à 09h00", result)
        self.assertIn("Salle B14", result)

    def test_alias(self):
        self.assertIn("Salle B12", tools.get_calendrier("BD"))

    def test_module_inconnu(self):
        self.assertIn("introuvable", tools.get_calendrier("Chimie"))

    def test_projet_sans_rattrapage(self):
        self.assertIn("Article 10", tools.get_calendrier("Projet"))


class TestDemande(unittest.TestCase):

    def setUp(self):
        tools.consume_new_drafts()

    def test_brouillon_maladie(self):
        result = tools.generer_demande(
            "Sami Test", "ET12345", "Bases de données", "maladie")
        self.assertIn("NON ENVOYÉ", result)
        self.assertIn("13/01/2027", result)       # 3 jours ouvrables
        drafts = tools.consume_new_drafts()
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["status"], "en_attente")

    def test_hospitalisation_7_jours(self):
        result = tools.generer_demande(
            "Sami Test", "ET12345", "Réseaux", "hospitalisation")
        self.assertIn("20/01/2027", result)
        self.assertIn("Article 6", result)

    def test_champs_invalides(self):
        for args in [("", "ET12345", "Réseaux", "maladie"),
                     ("Sami Test", "", "Réseaux", "maladie"),
                     ("Sami Test", "ET12345", "Réseaux", "grippe"),
                     ("Sami Test", "ET12345", "Chimie", "maladie"),
                     ("Sami Test", "ET12345", "Projet", "maladie")]:
            self.assertTrue(tools.generer_demande(*args).startswith("Erreur"))
        self.assertEqual(tools.consume_new_drafts(), [])

    def test_validation_humaine(self):
        tools.generer_demande("Sami Test", "ET12345", "Réseaux", "maladie")
        draft = tools.consume_new_drafts()[0]
        self.assertTrue(tools.annuler_brouillon(draft["id"])["ok"])
        # un brouillon annulé ne peut plus être envoyé
        self.assertFalse(tools.confirmer_envoi(draft["id"])["ok"])
        self.assertFalse(tools.confirmer_envoi("inconnu")["ok"])

    def test_pas_d_outil_d_envoi(self):
        from src.main import TOOLS
        names = {t["function"]["name"] for t in TOOLS}
        self.assertEqual(
            names, {"search_documents", "get_calendrier", "generer_demande"})


if __name__ == "__main__":
    unittest.main()
