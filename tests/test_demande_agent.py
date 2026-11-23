import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.main import (calendar_reply, is_demande_followup,
                      is_demande_request, run_agent)

# main.py ajoute src/ au chemin et utilise « import tools » : on prend
# donc la même copie du module (mêmes brouillons en mémoire).
import tools


def response(content=None, tool_calls=None):
    message = SimpleNamespace(
        content=content, tool_calls=tool_calls,
        model_dump=Mock(return_value={"role": "assistant", "content": content,
                                      "tool_calls": []}))
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def call(name, args):
    return SimpleNamespace(
        id="c1", function=SimpleNamespace(name=name,
                                          arguments=json.dumps(args)))


class TestDemandeAgent(unittest.TestCase):

    def setUp(self):
        tools.consume_new_drafts()

    def test_detection_intention(self):
        self.assertTrue(is_demande_request(
            "Rédige ma demande de rattrapage pour Réseaux"))
        self.assertTrue(is_demande_request("n7eb talab rattrapage"))
        self.assertFalse(is_demande_request(
            "Que doit contenir la demande de rattrapage ?"))
        self.assertFalse(is_demande_request("Quand est le rattrapage ?"))

    @patch("src.main.client")
    def test_le_modele_decide_le_programme_agit(self, client):
        args = {"nom_etudiant": "Sami Test", "numero_etudiant": "ET12345",
                "module": "Réseaux", "motif": "maladie"}
        client.chat.completions.create.side_effect = [
            response(tool_calls=[call("generer_demande", args)]),
            response(content="Brouillon prêt : relisez-le et confirmez."),
        ]
        answer = run_agent(
            "Rédige ma demande de rattrapage Réseaux, je suis Sami Test, "
            "ET12345, malade")
        self.assertIn("Brouillon", answer)
        drafts = tools.consume_new_drafts()
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0]["status"], "en_attente")  # pas envoyé

    @patch("src.main.client")
    def test_infos_manquantes_pas_de_brouillon(self, client):
        client.chat.completions.create.return_value = response(
            content="Quel est votre nom complet et votre numéro étudiant ?")
        answer = run_agent("Rédige ma demande de rattrapage")
        self.assertIn("numéro étudiant", answer)
        self.assertEqual(tools.consume_new_drafts(), [])

    def test_suite_de_la_demande(self):
        history = [
            {"role": "user", "content": "Rédige ma demande de rattrapage"},
            {"role": "assistant", "content": "Quel est votre nom ?"},
        ]
        self.assertTrue(is_demande_followup(
            "Sami Test ET12345 réseaux maladie", history))
        self.assertFalse(is_demande_followup(
            "wakteh rattrapage réseaux", history))
        self.assertFalse(is_demande_followup(
            "Sami Test ET12345 réseaux maladie", []))

    @patch("src.main.client")
    def test_la_suite_utilise_l_historique(self, client):
        args = {"nom_etudiant": "Sami Test", "numero_etudiant": "ET12345",
                "module": "Réseaux", "motif": "maladie"}
        client.chat.completions.create.side_effect = [
            response(tool_calls=[call("generer_demande", args)]),
            response(content="Brouillon prêt."),
        ]
        history = [
            {"role": "user", "content": "Rédige ma demande de rattrapage"},
            {"role": "assistant", "content": "Quel est votre nom ?"},
        ]
        run_agent("Sami Test ET12345 réseaux maladie", history)
        sent = client.chat.completions.create.call_args_list[0].kwargs
        contents = [m["content"] for m in sent["messages"]]
        self.assertIn("Rédige ma demande de rattrapage", contents)
        self.assertEqual(len(tools.consume_new_drafts()), 1)

    def test_suite_apres_un_message_incomplet(self):
        history = [
            {"role": "user", "content": "Rédige ma demande de rattrapage"},
            {"role": "assistant", "content": "Il me faut votre nom..."},
            {"role": "user", "content": "test 123456 bases de données"},
            {"role": "assistant", "content": "Je n'ai pas compris."},
        ]
        self.assertTrue(is_demande_followup(
            "Sami Test ET12345 réseaux maladie", history))

    def test_calendrier_sans_modele(self):
        fr = calendar_reply("wakteh ratrrapage réseaux", "derja_latin")
        self.assertIn("18/01/2027 à 09h00", fr)
        self.assertIn("Salle B14", fr)
        self.assertNotIn("Amphithéâtre", fr)
        self.assertIn("Amphithéâtre B",
                      calendar_reply("quand est l'examen de réseaux", "fr"))
        self.assertIsNone(calendar_reply(
            "Le certificat médical doit-il être daté ?", "fr"))
        self.assertIsNone(calendar_reply("quand est le rattrapage", "fr"))
        self.assertIsNone(calendar_reply("quand est le projet", "fr"))

    @patch("src.main.client")
    def test_nom_et_numero_inventes_refuses(self, client):
        invented = {"nom_etudiant": "Jean Dupont",
                    "numero_etudiant": "12345678",
                    "module": "Réseaux", "motif": "maladie"}
        client.chat.completions.create.side_effect = [
            response(tool_calls=[call("generer_demande", invented)]),
            response(content="Quel est votre nom et votre numéro ?"),
        ]
        run_agent("Rédige ma demande de rattrapage")
        self.assertEqual(tools.consume_new_drafts(), [])


if __name__ == "__main__":
    unittest.main()
