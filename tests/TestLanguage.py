import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.main import (
    detect_language,
    run_agent,
    smalltalk_reply,
    NO_INFO,
    NO_INFO_BY_LANG,
)


def fake_response(content):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class TestLanguageDetection(unittest.TestCase):

    CASES = [
        ("Quand a lieu l'examen de Réseaux ?", "fr"),
        ("Je suis en 3ème année, combien de semaines de stage ?", "fr"),
        ("Examen à 09h00 salle B12", "fr"),
        ("examen reseaux", "fr"),
        ("When is the make-up exam for Networks?", "en"),
        ("wa9tech rattrapage reseaux ?", "derja_latin"),
        ("9addech 3andi wa9t bech nwada3 certificat medical ?", "derja_latin"),
        ("chneya les conditions bech nbarer absence examen ?", "derja_latin"),
        ("شنوة يصير كان نغيب أكثر من 4 مرات sans justificatif ?", "derja_ar"),
        ("كيفاش نبرر غيابي؟", "derja_ar"),
        ("متى موعد امتحان الشبكات؟", "ar"),
        ("¿Cuándo es el examen de redes?", "es"),
        ("Wann ist die Prüfung in Netzwerke?", "de"),
        ("Quando è l'esame di reti?", "it"),
        ("Quando é o exame de redes na faculdade?", "pt"),
        ("Расписание экзаменов по сетям", "other"),
    ]

    def test_detection(self):
        for question, expected in self.CASES:
            with self.subTest(question=question):
                self.assertEqual(detect_language(question), expected)

    def test_smalltalk(self):
        self.assertIn("Aslema", smalltalk_reply("salam"))
        self.assertIn("Hello", smalltalk_reply("Hello"))
        self.assertIn("welcome", smalltalk_reply("thanks"))
        self.assertIsNone(smalltalk_reply("Bonjour, quand est l'examen ?"))


class TestLanguageInPrompt(unittest.TestCase):

    def ask(self, question):
        with patch("src.main.client.chat.completions.create") as mock_create:
            mock_create.return_value = fake_response("réponse")
            run_agent(question)
            return mock_create.call_args.kwargs["messages"]

    def test_derja_latin_instruction_sent_to_model(self):
        messages = self.ask("kifech nbarer ghyebi 3and el doctor ?")
        self.assertIn("derja tunisienne écrite en lettres latines", messages[-1]["content"])

    def test_derja_arabic_instruction_sent_to_model(self):
        messages = self.ask("وقتاش التدارك متاع ريزو؟")
        self.assertIn("lettres arabes", messages[-1]["content"])

    def test_english_instruction_sent_to_model(self):
        messages = self.ask("How do I justify an absence with a medical certificate?")
        self.assertIn("English only", messages[-1]["content"])

    def test_french_instruction_sent_to_model(self):
        messages = self.ask("Comment justifier une absence avec un certificat médical ?")
        self.assertIn("français", messages[-1]["content"])

    def test_no_info_is_localised(self):
        self.assertEqual(NO_INFO_BY_LANG["fr"], NO_INFO)
        with patch("src.main.client.chat.completions.create") as mock_create:
            mock_create.return_value = fake_response("x")
            answer = run_agent("kifech nlaa9a el ma3louma hethi zzzxqv987654unik ?")
        self.assertEqual(answer, NO_INFO_BY_LANG["derja_latin"])


if __name__ == "__main__":
    unittest.main()
