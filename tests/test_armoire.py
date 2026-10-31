"""Tests de la décision et des actions liées à l'armoire."""

from pathlib import Path
import unittest

from armoire import classer_casiers, determiner_repli, mouvements_selecteur
from base_fournie import reconfort_io as rio
from environnement import ActionImpossible, Environnement
from navigation import Navigateur, rejoindre
from validation import EMOTIONS, INTENSITES


RACINE = Path(__file__).resolve().parents[1]
BASE = RACINE / "base_fournie"


class TestsRegleDeRepli(unittest.TestCase):
    def test_ordre_surprise_forte_de_lannexe(self):
        candidats = classer_casiers(
            "surprise",
            "forte",
            EMOTIONS,
            INTENSITES,
        )
        self.assertEqual(
            candidats[:5],
            [(2, 3), (1, 3), (0, 3), (2, 4), (2, 2)],
        )
        self.assertEqual(len(candidats), 15)

    def test_etiquettes_de_repli(self):
        cible = (2, 3)
        self.assertEqual(determiner_repli(cible, (2, 3), EMOTIONS), "aucun")
        self.assertEqual(
            determiner_repli(cible, (1, 3), EMOTIONS),
            "intensite",
        )
        self.assertEqual(
            determiner_repli(cible, (2, 4), EMOTIONS),
            "voisine_1",
        )
        self.assertEqual(
            determiner_repli(cible, (2, 5), EMOTIONS),
            "voisine_2",
        )

    def test_mouvements_cycliques(self):
        self.assertEqual(mouvements_selecteur((1, 7), (1, 0)), ["E"])
        self.assertEqual(mouvements_selecteur((1, 0), (1, 7)), ["O"])
        self.assertEqual(
            mouvements_selecteur((2, 7), (0, 1)),
            ["N", "N", "E", "E"],
        )
        self.assertEqual(
            mouvements_selecteur((1, 0), (2, 6)),
            ["S", "O", "O"],
        )


class TestsActionsArmoire(unittest.TestCase):
    def setUp(self):
        carte = rio.charger_carte(BASE / "cartes" / "appartement_01.json")
        armoire = rio.charger_armoire(
            BASE / "donnees" / "armoire_standard.json"
        )
        self.environnement = Environnement(carte, armoire)
        self.navigateur = Navigateur(
            self.environnement.informations_initiales()
        )
        rejoindre(
            self.navigateur,
            carte["armoire"]["position"],
            self.environnement.percevoir,
            self.environnement.avancer,
        )

    def test_les_informations_ne_revelent_aucun_objet(self):
        informations = self.environnement.informations_armoire()
        self.assertTrue(
            all("objet" not in casier for casier in informations["casiers"])
        )

    def test_selecteur_boucle_horizontalement(self):
        self.assertEqual(self.environnement.casier_courant, (1, 0))
        self.environnement.chercher("O")
        self.assertEqual(self.environnement.casier_courant, (1, 7))
        self.environnement.chercher("E")
        self.assertEqual(self.environnement.casier_courant, (1, 0))

    def test_selecteur_refuse_de_sortir_verticalement(self):
        self.environnement.chercher("N")
        self.assertEqual(self.environnement.casier_courant, (0, 0))
        with self.assertRaises(ActionImpossible):
            self.environnement.chercher("N")

    def test_prendre_et_donner_un_objet(self):
        objet = self.environnement.contenu_casier()
        self.assertEqual(objet, "photo de famille")
        self.environnement.prendre(objet)
        self.assertEqual(self.environnement.objet_transporte, objet)
        self.assertIsNone(self.environnement.contenu_casier())

        carte = self.environnement.informations_initiales()
        position_resident = carte["residents"][0]["position"]
        rejoindre(
            self.navigateur,
            position_resident,
            self.environnement.percevoir,
            self.environnement.avancer,
        )
        self.environnement.donner(objet, position_resident)
        self.assertIsNone(self.environnement.objet_transporte)


if __name__ == "__main__":
    unittest.main()
