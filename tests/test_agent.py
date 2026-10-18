import unittest
from pathlib import Path

from agent import indexer_dictionnaire, lire_emotion
from base_fournie import reconfort_io as rio


class TestLectureEmotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        chemin = (
            Path(__file__).resolve().parents[1]
            / "base_fournie"
            / "donnees"
            / "dictionnaire.json"
        )
        dictionnaire = rio.charger_dictionnaire(chemin)
        cls.index_dictionnaire = indexer_dictionnaire(dictionnaire)

    def test_message_du_premier_scenario(self) -> None:
        resultat = lire_emotion(
            "Je me sens tellement seule ce soir, personne n'est passe.",
            self.index_dictionnaire,
        )
        self.assertEqual(resultat, ("tristesse", "moyenne"))

    def test_accents_et_premier_mot_reconnu(self) -> None:
        resultat = lire_emotion(
            "Je suis sidéré, puis je me sens seule.",
            self.index_dictionnaire,
        )
        self.assertEqual(resultat, ("surprise", "forte"))

    def test_ordre_des_mots(self) -> None:
        resultat = lire_emotion(
            "Je suis heureux mais inquiet.",
            self.index_dictionnaire,
        )
        self.assertEqual(resultat, ("joie", "moyenne"))

    def test_emotion_indeterminee(self) -> None:
        resultat = lire_emotion(
            "Cette phrase ne contient aucun terme repertorie.",
            self.index_dictionnaire,
        )
        self.assertIsNone(resultat)


if __name__ == "__main__":
    unittest.main()
