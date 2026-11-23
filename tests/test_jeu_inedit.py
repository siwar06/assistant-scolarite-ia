"""Cohérence du jeu inédit (sans modèle ni Ollama)."""

import re
import unittest
from collections import Counter

from tests.jeu_de_test import CASES as DEV_CASES
from tests.jeu_de_test_inedit import CASES, check


class TestJeuInedit(unittest.TestCase):

    def test_quinze_questions_et_repartition(self):
        self.assertEqual(len(CASES), 15)
        self.assertEqual(
            Counter(c["category"] for c in CASES),
            {"Factuelle": 4, "Hors sujet": 2, "Information absente": 2,
             "Piège": 3, "Manipulation": 2, "Multilingue": 1, "Demande": 1})
        self.assertEqual([c["id"] for c in CASES], list(range(101, 116)))

    def test_aucune_question_deja_vue(self):
        dev = {c["question"] for c in DEV_CASES}
        for case in CASES:
            self.assertNotIn(case["question"], dev)

    def test_motifs_valides(self):
        for case in CASES:
            for group in case["must"]:
                for pattern in group:
                    re.compile(pattern)
            for pattern in case.get("forbidden", []):
                re.compile(pattern)

    def test_la_reponse_attendue_passe_son_propre_test(self):
        for case in CASES:
            with self.subTest(id=case["id"]):
                draft = 1 if case.get("draft") is True else 0
                self.assertEqual(check(case, case["expected"], draft), [],
                                 case["question"])

    def test_les_inventions_echouent(self):
        by_id = {c["id"]: c for c in CASES}
        self.assertTrue(check(by_id[107], "L'examen de Physique a lieu le 14/01/2027."))
        self.assertTrue(check(by_id[108], "Le directeur est M. Ben Salah."))
        self.assertTrue(check(by_id[110], "Oui, vous pouvez passer l'examen."))
        self.assertTrue(check(by_id[115], "Voici le brouillon.", 0))


if __name__ == "__main__":
    unittest.main()
