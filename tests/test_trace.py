"""Rejeu indépendant d'une trace produite par l'agent."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agent import main
from base_fournie import reconfort_io as rio


RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "base_fournie"
DIRECTIONS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1)}
TYPES = {
    "#": "mur",
    ".": "libre",
    "R": "libre",
    "A": "armoire",
    "D": "dictionnaire",
    "P": "resident",
}


class TestRejeuTrace(unittest.TestCase):
    def test_trace_rejouable_sur_la_realite(self):
        carte = rio.charger_carte(BASE / "cartes" / "appartement_01.json")
        armoire = rio.charger_armoire(
            BASE / "donnees" / "armoire_standard.json"
        )
        with TemporaryDirectory(dir=RACINE / "tests") as dossier:
            sortie = Path(dossier) / "trace.json"
            code = main(
                [
                    "agent.py",
                    str(BASE / "cartes" / "appartement_01.json"),
                    str(BASE / "cartes" / "scenario_01.json"),
                    str(BASE / "donnees"),
                    str(sortie),
                ]
            )
            trace = json.loads(sortie.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)

        position = tuple(carte["depart_robot"])
        selecteur = tuple(armoire["casier_depart"])
        contenus = {
            (casier["ligne"], casier["colonne"]): casier["objet"]
            for casier in armoire["casiers"]
        }
        transporte = None

        def perception_reelle():
            ligne, colonne = position
            return {
                direction: TYPES[
                    carte["grille"][ligne + delta_ligne][
                        colonne + delta_colonne
                    ]
                ]
                for direction, (delta_ligne, delta_colonne) in DIRECTIONS.items()
            }

        for temps, pas in enumerate(trace["pas"]):
            self.assertEqual(pas["t"], temps)
            self.assertEqual(tuple(pas["position"]), position)
            self.assertEqual(tuple(pas["casier"]), selecteur)
            perception = perception_reelle()
            self.assertEqual(pas["perception"], perception)
            contenu_attendu = (
                contenus[selecteur]
                if "armoire" in perception.values()
                else None
            )
            self.assertEqual(pas["contenu_casier"], contenu_attendu)

            action = pas["action"]
            argument = pas["argument"]
            if action == "AVANCER":
                self.assertEqual(perception[argument], "libre")
                delta_ligne, delta_colonne = DIRECTIONS[argument]
                position = (
                    position[0] + delta_ligne,
                    position[1] + delta_colonne,
                )
            elif action == "CONSULTER":
                self.assertIn("dictionnaire", perception.values())
            elif action == "CHERCHER":
                self.assertIn("armoire", perception.values())
                ligne, colonne = selecteur
                if argument == "N":
                    ligne -= 1
                elif argument == "S":
                    ligne += 1
                elif argument == "E":
                    colonne = (colonne + 1) % 8
                else:
                    colonne = (colonne - 1) % 8
                selecteur = (ligne, colonne)
            elif action == "PRENDRE":
                self.assertIsNone(transporte)
                self.assertEqual(contenus[selecteur], argument)
                transporte = argument
                contenus[selecteur] = None
            elif action == "DONNER":
                self.assertEqual(transporte, argument)
                self.assertIn("resident", perception.values())
                transporte = None
            else:
                self.assertEqual(action, "ATTENDRE")

        self.assertIsNone(transporte)
        self.assertEqual(trace["resume"]["pas_total"], len(trace["pas"]))
        self.assertEqual(trace["resume"]["echecs"], 0)


if __name__ == "__main__":
    unittest.main()
