import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent import indexer_dictionnaire, lire_emotion, main
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

    def test_consulter_uniquement_devant_le_dictionnaire(self) -> None:
        carte = fabriquer_carte(
            [
                "#####",
                "#PRD#",
                "#.A.#",
                "#####",
            ]
        )
        environnement = Environnement(carte)
        environnement.consulter()

        carte_eloignee = fabriquer_carte(
            [
                "#######",
                "#R..AD#",
                "#...P.#",
                "#######",
            ]
        )
        environnement = Environnement(carte_eloignee)
        with self.assertRaises(ActionImpossible):
            environnement.consulter()


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


class TestIntegrationDictionnaire(unittest.TestCase):
    def test_agent_navigue_et_consulte_pour_chaque_demande(self) -> None:
        racine = Path(__file__).resolve().parents[1]
        base = racine / "base_fournie"
        with TemporaryDirectory(dir=racine / "tests") as dossier:
            sortie = Path(dossier) / "trace.json"
            code = main(
                [
                    "agent.py",
                    str(base / "cartes" / "appartement_01.json"),
                    str(base / "cartes" / "scenario_01.json"),
                    str(base / "donnees"),
                    str(sortie),
                ]
            )
            trace = json.loads(sortie.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(
            trace["equipe"],
            ["Mohammed M'BARKI", "Mohamed Mesti"],
        )
        consultations = [
            pas for pas in trace["pas"] if pas["action"] == "CONSULTER"
        ]
        self.assertEqual(len(consultations), 4)
        self.assertNotIn("ATTENDRE", {pas["action"] for pas in trace["pas"]})

        for pas in trace["pas"]:
            if pas["action"] == "AVANCER":
                self.assertEqual(
                    pas["perception"][pas["argument"]],
                    "libre",
                )
            elif pas["action"] == "CONSULTER":
                self.assertIn("dictionnaire", pas["perception"].values())

        self.assertEqual(
            [livraison["emotion"] for livraison in trace["livraisons"]],
            ["tristesse", "peur", "colere", "joie"],
        )
        self.assertTrue(
            all(livraison["succes"] for livraison in trace["livraisons"])
        )
        self.assertEqual(
            [livraison["objet"] for livraison in trace["livraisons"]],
            ["couverture", "veilleuse", "balle antistress", "photo de famille"],
        )
        actions = {pas["action"] for pas in trace["pas"]}
        self.assertTrue(
            {"AVANCER", "CONSULTER", "CHERCHER", "PRENDRE", "DONNER"}
            <= actions
        )

    def test_cinq_scenarios_fournis_sans_erreur(self) -> None:
        racine = Path(__file__).resolve().parents[1]
        base = racine / "base_fournie"
        with TemporaryDirectory(dir=racine / "tests") as dossier:
            dossier = Path(dossier)
            for numero in range(1, 6):
                suffixe = f"{numero:02d}"
                with self.subTest(scenario=suffixe):
                    sortie = dossier / f"trace_{suffixe}.json"
                    code = main(
                        [
                            "agent.py",
                            str(base / "cartes" / f"appartement_{suffixe}.json"),
                            str(base / "cartes" / f"scenario_{suffixe}.json"),
                            str(base / "donnees"),
                            str(sortie),
                        ]
                    )
                    trace = json.loads(sortie.read_text(encoding="utf-8"))
                    scenario = rio.charger_scenario(
                        base / "cartes" / f"scenario_{suffixe}.json"
                    )
                    self.assertEqual(code, 0)
                    self.assertEqual(
                        len(trace["livraisons"]),
                        len(scenario["demandes"]),
                    )
                    self.assertNotIn(
                        "agent non implemente",
                        {
                            livraison["motif_echec"]
                            for livraison in trace["livraisons"]
                        },
                    )


if __name__ == "__main__":
    unittest.main()
