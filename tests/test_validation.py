"""Tests des validations structurelles et croisées des entrées."""

from contextlib import redirect_stderr
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from agent import main
from base_fournie import reconfort_io as rio
from validation import (
    valider_armoire,
    valider_dictionnaire,
    valider_scenario,
)


RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "base_fournie"


class TestsValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carte = rio.charger_carte(BASE / "cartes" / "appartement_01.json")
        cls.scenario = rio.charger_scenario(
            BASE / "cartes" / "scenario_01.json"
        )
        cls.dictionnaire = rio.charger_dictionnaire(
            BASE / "donnees" / "dictionnaire.json"
        )
        cls.armoire = rio.charger_armoire(
            BASE / "donnees" / "armoire_standard.json"
        )

    def test_fichiers_fournis_valides(self):
        valider_dictionnaire(self.dictionnaire)
        valider_armoire(self.armoire, self.dictionnaire)
        valider_scenario(self.scenario, self.carte, self.armoire)

    def test_scenarios_invalides(self):
        cas = [
            (lambda s: s.update(nom=5), "nom"),
            (lambda s: s.update(carte="autre"), "carte"),
            (lambda s: s.update(armoire="autre"), "armoire"),
            (lambda s: s.update(demandes=None), "demandes"),
            (lambda s: s["demandes"].append(None), "demande"),
            (lambda s: s["demandes"][0].update(numero=True), "numéro"),
            (
                lambda s: s["demandes"][1].update(
                    numero=s["demandes"][0]["numero"]
                ),
                "double",
            ),
            (lambda s: s["demandes"][0].update(resident="RX"), "résident"),
            (lambda s: s["demandes"][0].update(message=5), "message"),
        ]
        for modifier, message in cas:
            with self.subTest(message=message):
                scenario = deepcopy(self.scenario)
                modifier(scenario)
                with self.assertRaisesRegex(rio.ErreurFichier, message):
                    valider_scenario(scenario, self.carte, self.armoire)

    def test_dictionnaires_invalides(self):
        cas = [
            (lambda d: d.update(nom=""), "nom"),
            (lambda d: d["emotions"].reverse(), "émotions"),
            (lambda d: d["intensites"].pop(), "intensités"),
            (lambda d: d.update(entrees=None), "entrées"),
            (lambda d: d["entrees"].append(None), "entrée"),
            (lambda d: d["entrees"][0].update(formes=[]), "formes"),
            (lambda d: d["entrees"][0].update(emotion="inconnue"), "émotion"),
            (lambda d: d["entrees"][0].update(intensite="maximale"), "intensité"),
            (
                lambda d: d["entrees"][1]["formes"].append(
                    d["entrees"][0]["formes"][0]
                ),
                "plusieurs fois",
            ),
        ]
        for modifier, message in cas:
            with self.subTest(message=message):
                dictionnaire = deepcopy(self.dictionnaire)
                modifier(dictionnaire)
                with self.assertRaisesRegex(rio.ErreurFichier, message):
                    valider_dictionnaire(dictionnaire)

    def test_armoires_invalides(self):
        cas = [
            (lambda a: a.update(nom=5), "nom"),
            (lambda a: a["emotions"].reverse(), "émotions"),
            (lambda a: a["intensites"].reverse(), "intensités"),
            (lambda a: a.update(casier_depart=[3, 0]), "hors"),
            (lambda a: a.update(casier_depart=[True, 0]), "invalide"),
            (lambda a: a.update(casiers=None), "24 casiers"),
            (lambda a: a["casiers"].pop(), "24 casiers"),
            (lambda a: a["casiers"].__setitem__(0, None), "casier"),
            (
                lambda a: a["casiers"][1].update(
                    ligne=a["casiers"][0]["ligne"],
                    colonne=a["casiers"][0]["colonne"],
                ),
                "double",
            ),
            (lambda a: a["casiers"][0].update(ligne=3), "hors"),
            (lambda a: a["casiers"][0].update(emotion="peur"), "émotion"),
            (lambda a: a["casiers"][0].update(intensite="forte"), "intensité"),
            (lambda a: a["casiers"][0].update(objet=4), "objet"),
        ]
        for modifier, message in cas:
            with self.subTest(message=message):
                armoire = deepcopy(self.armoire)
                modifier(armoire)
                with self.assertRaisesRegex(rio.ErreurFichier, message):
                    valider_armoire(armoire, self.dictionnaire)

    def test_agent_necrit_pas_de_trace_si_les_donnees_sont_invalides(self):
        with TemporaryDirectory(dir=RACINE / "tests") as dossier:
            dossier = Path(dossier)
            scenario = deepcopy(self.scenario)
            scenario["demandes"][0]["resident"] = "INCONNU"
            chemin_scenario = dossier / "scenario.json"
            chemin_scenario.write_text(
                json.dumps(scenario, ensure_ascii=False),
                encoding="utf-8",
            )
            sortie = dossier / "trace.json"

            erreurs = StringIO()
            with redirect_stderr(erreurs):
                code = main(
                    [
                        "agent.py",
                        str(BASE / "cartes" / "appartement_01.json"),
                        str(chemin_scenario),
                        str(BASE / "donnees"),
                        str(sortie),
                    ]
                )

            self.assertNotEqual(code, 0)
            self.assertIn("résident inconnu", erreurs.getvalue())
            self.assertFalse(sortie.exists())


if __name__ == "__main__":
    unittest.main()
