import unittest
from pathlib import Path

from agent import indexer_dictionnaire, lire_emotion
from base_fournie import reconfort_io as rio
from environnement import ActionImpossible, Environnement


def fabriquer_carte(lignes):
    carte = {
        "format": "robot-reconfort/carte",
        "version": 1,
        "nom": "test_agent",
        "dimensions": {
            "hauteur": len(lignes),
            "largeur": len(lignes[0]),
        },
        "legende": {
            "#": "mur",
            ".": "libre",
            "R": "depart",
            "A": "armoire",
            "D": "dictionnaire",
            "P": "resident",
        },
        "grille": lignes,
        "residents": [],
    }
    for ligne, contenu in enumerate(lignes):
        for colonne, symbole in enumerate(contenu):
            if symbole == "R":
                carte["depart_robot"] = [ligne, colonne]
            elif symbole in "AD":
                champ = "armoire" if symbole == "A" else "dictionnaire"
                carte[champ] = {"position": [ligne, colonne]}
            elif symbole == "P":
                carte["residents"].append(
                    {
                        "id": "R1",
                        "nom": "Résident",
                        "position": [ligne, colonne],
                    }
                )
    return carte


class TestPerception(unittest.TestCase):
    def test_perception_au_depart_de_la_carte_fournie(self) -> None:
        chemin = (
            Path(__file__).resolve().parents[1]
            / "base_fournie"
            / "cartes"
            / "appartement_01.json"
        )
        carte = rio.charger_carte(chemin)

        environnement = Environnement(carte)

        self.assertEqual(environnement.position_robot, (6, 1))
        self.assertEqual(
            environnement.percevoir(),
            {"N": "libre", "S": "libre", "E": "libre", "O": "mur"},
        )

    def test_perception_des_elements_non_traversables(self) -> None:
        carte = fabriquer_carte(
            [
                "#####",
                "#PRD#",
                "#.A.#",
                "#####",
            ]
        )

        environnement = Environnement(carte)

        self.assertEqual(
            environnement.percevoir(),
            {
                "N": "mur",
                "S": "armoire",
                "E": "dictionnaire",
                "O": "resident",
            },
        )


class TestDeplacement(unittest.TestCase):
    def test_avancer_vers_une_case_libre(self) -> None:
        carte = fabriquer_carte(
            [
                "#######",
                "#R..AD#",
                "#...P.#",
                "#######",
            ]
        )
        environnement = Environnement(carte)

        environnement.avancer("E")

        self.assertEqual(environnement.position_robot, (1, 2))

    def test_refuser_les_cases_non_traversables(self) -> None:
        carte = fabriquer_carte(
            [
                "#####",
                "#PRD#",
                "#.A.#",
                "#####",
            ]
        )

        for direction in ("N", "S", "E", "O"):
            with self.subTest(direction=direction):
                environnement = Environnement(carte)

                with self.assertRaises(ActionImpossible):
                    environnement.avancer(direction)

                self.assertEqual(environnement.position_robot, (1, 2))

    def test_refuser_une_direction_inconnue(self) -> None:
        carte = fabriquer_carte(
            [
                "#######",
                "#R..AD#",
                "#...P.#",
                "#######",
            ]
        )
        environnement = Environnement(carte)

        with self.assertRaisesRegex(ValueError, "direction inconnue"):
            environnement.avancer("NE")

        self.assertEqual(environnement.position_robot, (1, 1))


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
