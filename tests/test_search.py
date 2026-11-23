
import unittest

from src.main import search_documents


class TestDocumentSearch(unittest.TestCase):

    # ARTICLE 1
    def test_absences(self):
        result = search_documents("5 absences injustifiees dans un module")
        self.assertIn("ARTICLE 1", result)
        self.assertIn("plus de 4 absences", result)

    # CALENDRIER
    def test_reseaux_exam(self):
        result = search_documents("examen module Reseaux")
        self.assertIn("11/01/2027", result)
        self.assertIn("Amphith", result)

    def test_reseaux_makeup(self):
        result = search_documents("rattrapage module Reseaux")
        self.assertIn("18/01/2027", result)
        self.assertIn("Salle B14", result)

    # ARTICLE 10
    def test_project_no_makeup(self):
        result = search_documents("Projet de fin de module rattrapage")
        self.assertIn("Rattrapage : Aucun", result)
        self.assertIn("ARTICLE 10", result)

    # ARTICLE 11
    def test_internship_duration(self):
        result = search_documents("duree minimale du stage de fin d'etudes")
        self.assertIn("ARTICLE 11", result)
        self.assertIn("8 semaines", result)

    # ARTICLE 12
    def test_internship_convention(self):
        result = search_documents("convention de stage delai de depot")
        self.assertIn("ARTICLE 12", result)
        self.assertIn("15 jours", result)

    # ARTICLE 6
    def test_hospitalization(self):
        result = search_documents("hospitalisation delai justificatif")
        self.assertIn("ARTICLE 6", result)
        self.assertIn("7 jours ouvrables", result)

    # ARTICLE 15
    def test_grade_complaint(self):
        result = search_documents("reclamation concernant une note")
        self.assertIn("ARTICLE 15", result)
        self.assertIn("5 jours ouvrables", result)

    # ARTICLE 2
    def test_justification_absence(self):
        result = search_documents(
            "justifier absence certificat medical convocation force majeure"
        )
        self.assertIn("ARTICLE 2", result)
        self.assertIn("convocation officielle", result)

    # ARTICLE 3
    def test_absence_exam_unjustified(self):
        result = search_documents("absence examen sans justificatif note zero")
        self.assertIn("ARTICLE 3", result)
        self.assertIn("0/20", result)

    # ARTICLE 4
    def test_certificate_deadline(self):
        result = search_documents(
            "certificat medical delai trois jours ouvrables examen"
        )
        self.assertIn("ARTICLE 4", result)
        self.assertIn("3 jours ouvrables", result)

    # ARTICLE 5
    def test_certificate_validity(self):
        result = search_documents(
            "certificat medical date signe cachete medecin duree incapacite"
        )
        self.assertIn("ARTICLE 5", result)
        self.assertIn("cacheté", result)

    # ARTICLE 7
    def test_makeup_eligibility(self):
        result = search_documents(
            "absence justifiee session rattrapage calendrier officiel"
        )
        self.assertIn("ARTICLE 7", result)
        self.assertIn("session de rattrapage", result)

    # ARTICLE 8
    def test_makeup_request(self):
        result = search_documents(
            "demande ecrite responsable bureau scolarite numero etudiant module"
        )
        self.assertIn("ARTICLE 8", result)
        self.assertIn("numéro étudiant", result)

    # ARTICLE 9
    def test_makeup_grade(self):
        result = search_documents(
            "note obtenue session rattrapage remplace note initiale"
        )
        self.assertIn("ARTICLE 9", result)
        self.assertIn("remplace", result)

    # ARTICLE 14
    def test_internship_report(self):
        result = search_documents(
            "rapport stage delai dix jours fin stage soutenance jury"
        )
        self.assertIn("ARTICLE 14", result)
        self.assertIn("10 jours", result)
        # PRECISION DE LA RECHERCHE EN ANGLAIS
    def test_english_networks_makeup(self):
        result = search_documents(
            "When is the make-up exam for Networks?"
        )

        self.assertIn("18/01/2027", result)
        self.assertIn("Salle B14", result)
        self.assertNotIn("ARTICLE 1", result)
        self.assertNotIn("ARTICLE 2", result)

class TestRacines(unittest.TestCase):

    def test_hospitalise_retrouve_article_6(self):
        result = search_documents(
            "Que se passe-t-il si je suis hospitalisé le jour de l'examen ?")
        self.assertIn("ARTICLE 6", result)


if __name__ == "__main__":
    unittest.main()
