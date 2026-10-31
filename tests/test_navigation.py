"""Tests de l'environnement, de la mémoire et de la navigation."""

from copy import deepcopy
from pathlib import Path
import unittest

from base_fournie import reconfort_io as rio
from environnement import ActionImpossible, Environnement
from navigation import (
    CarteMentale,
    DestinationInaccessible,
    Navigateur,
    plus_court_chemin,
    rejoindre,
)


def fabriquer_carte(lignes):
    """Construit une carte de test à partir de symboles lisibles."""
    carte = {
        "format": "robot-reconfort/carte",
        "version": 1,
        "nom": "test",
        "dimensions": {
            "hauteur": len(lignes),
            "largeur": len(lignes[0]),
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
                identifiant = f"R{len(carte['residents']) + 1}"
                carte["residents"].append(
                    {
                        "id": identifiant,
                        "nom": identifiant,
                        "position": [ligne, colonne],
                    }
                )
    return carte


def carte_detour():
    """Carte dont le chemin réel vers (1, 4) mesure sept pas."""
    return fabriquer_carte(
        [
            "#######",
            "#R.#.P#",
            "#.#..##",
            "#...AD#",
            "#######",
        ]
    )


class TestsPerception(unittest.TestCase):
    def test_quatre_voisins_seulement(self):
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

    def test_informations_sans_grille_et_copies_independantes(self):
        environnement = Environnement(carte_detour())
        informations = environnement.informations_initiales()
        self.assertNotIn("grille", informations)
        informations["depart_robot"][0] = 99
        informations["armoire"]["position"][0] = 99
        nouvelles = environnement.informations_initiales()
        self.assertEqual(nouvelles["depart_robot"], [1, 1])
        self.assertEqual(nouvelles["armoire"]["position"], [3, 4])

    def test_environnement_refuse_les_obstacles(self):
        carte = fabriquer_carte(
            [
                "#######",
                "#RADP.#",
                "#.....#",
                "#######",
            ]
        )
        environnement = Environnement(carte)
        for direction in ("N", "O", "E"):
            with self.subTest(direction=direction):
                with self.assertRaises(ActionImpossible):
                    environnement.avancer(direction)
        with self.assertRaises(ValueError):
            environnement.avancer("X")
        self.assertEqual(environnement.position_robot, (1, 1))

        environnement.avancer("S")
        environnement.avancer("E")
        with self.assertRaises(ActionImpossible):
            environnement.avancer("N")
        environnement.avancer("E")
        with self.assertRaises(ActionImpossible):
            environnement.avancer("N")
        environnement.avancer("E")
        with self.assertRaises(ActionImpossible):
            environnement.avancer("N")


class TestsMemoireEtBFS(unittest.TestCase):
    def setUp(self):
        self.carte = carte_detour()
        self.environnement = Environnement(self.carte)
        self.memoire = CarteMentale(
            self.environnement.informations_initiales()
        )

    def test_aucun_mur_connu_avant_perception(self):
        self.assertNotIn("mur", self.memoire.cases.values())
        self.assertTrue(self.memoire.est_traversable((1, 3)))
        self.assertFalse(self.memoire.est_traversable((-1, 1)))
        for case in ((3, 4), (3, 5), (1, 5)):
            self.assertFalse(self.memoire.est_traversable(case))

    def test_mise_a_jour_locale_sans_vision_lointaine(self):
        self.memoire.mettre_a_jour(
            (1, 1),
            self.environnement.percevoir(),
        )
        self.assertEqual(self.memoire.cases[(0, 1)], "mur")
        self.assertEqual(self.memoire.cases[(1, 2)], "libre")
        self.assertNotIn((2, 2), self.memoire.cases)
        self.assertNotIn((1, 3), self.memoire.cases)

    def test_perception_incomplete_ou_inconnue_refusee(self):
        avant = dict(self.memoire.cases)
        perceptions = (
            {"N": "mur"},
            {
                "N": "mur",
                "S": "libre",
                "E": "inconnu",
                "O": "mur",
            },
        )
        for perception in perceptions:
            with self.subTest(perception=perception):
                with self.assertRaises(ValueError):
                    self.memoire.mettre_a_jour((1, 1), perception)
                self.assertEqual(self.memoire.cases, avant)

    def test_chemin_de_longueur_connue(self):
        for ligne, contenu in enumerate(self.carte["grille"]):
            for colonne, symbole in enumerate(contenu):
                self.memoire.cases[(ligne, colonne)] = (
                    "libre" if symbole in ".R" else "mur"
                )
        chemin = plus_court_chemin(self.memoire, (1, 1), {(1, 4)})
        self.assertEqual(
            chemin,
            [
                (1, 1),
                (2, 1),
                (3, 1),
                (3, 2),
                (3, 3),
                (2, 3),
                (2, 4),
                (1, 4),
            ],
        )
        self.assertEqual(len(chemin) - 1, 7)

    def test_bfs_choisit_la_plus_proche_des_arrivees(self):
        chemin = plus_court_chemin(
            self.memoire,
            (1, 1),
            {(3, 3), (1, 2)},
        )
        self.assertEqual(chemin, [(1, 1), (1, 2)])
        self.assertEqual(
            plus_court_chemin(self.memoire, (1, 1), {(1, 1)}),
            [(1, 1)],
        )
        self.assertIsNone(
            plus_court_chemin(self.memoire, (1, 1), set())
        )
        self.assertIsNone(
            plus_court_chemin(self.memoire, (1, 1), {(3, 4)})
        )


class TestsNavigation(unittest.TestCase):
    def setUp(self):
        self.environnement = Environnement(carte_detour())
        self.informations = self.environnement.informations_initiales()
        self.navigateur = Navigateur(self.informations)
        self.cible = self.informations["residents"][0]["position"]

    def rejoindre_cible(self, cible, journaliser=None):
        return rejoindre(
            self.navigateur,
            cible,
            self.environnement.percevoir,
            self.environnement.avancer,
            journaliser,
        )

    def test_mur_decouvert_provoque_un_detour(self):
        mouvements = []

        def journaliser(position, perception, direction):
            mouvements.append(direction)
            self.assertEqual(perception[direction], "libre")
            self.assertEqual(position, self.environnement.position_robot)

        pas = self.rejoindre_cible(self.cible, journaliser)
        self.assertEqual(mouvements[:3], ["E", "O", "S"])
        self.assertEqual(pas, len(mouvements))
        self.assertEqual(
            self.navigateur.carte_mentale.cases[(1, 3)],
            "mur",
        )
        self.assertEqual(self.navigateur.position, (1, 4))
        self.assertEqual(
            self.navigateur.position,
            self.environnement.position_robot,
        )

    def test_arrivee_deja_adjacente_sans_action(self):
        cible = self.informations["armoire"]["position"]
        self.rejoindre_cible(cible)

        def action_interdite(*args):
            self.fail("aucune action ne doit être exécutée")

        self.assertEqual(
            rejoindre(
                self.navigateur,
                cible,
                self.environnement.percevoir,
                action_interdite,
                action_interdite,
            ),
            0,
        )

    def test_memoire_et_position_persistent_entre_cibles(self):
        self.rejoindre_cible(self.cible)
        memoire = self.navigateur.carte_mentale
        anciennes_cases = dict(memoire.cases)
        self.rejoindre_cible(self.informations["armoire"]["position"])
        self.assertIs(self.navigateur.carte_mentale, memoire)
        self.assertTrue(anciennes_cases.items() <= memoire.cases.items())
        self.assertEqual(
            self.navigateur.position,
            self.environnement.position_robot,
        )

    def test_deplacement_inconnu_non_confirme(self):
        with self.assertRaises(ValueError):
            self.navigateur.confirmer_deplacement("E")
        self.assertEqual(self.navigateur.position, (1, 1))

    def test_echec_execution_ne_deplace_pas_la_memoire(self):
        def avancer_en_echec(direction):
            raise RuntimeError("action refusée")

        with self.assertRaises(RuntimeError):
            rejoindre(
                self.navigateur,
                self.cible,
                self.environnement.percevoir,
                avancer_en_echec,
            )
        self.assertEqual(self.navigateur.position, (1, 1))

    def test_cible_hors_limites(self):
        with self.assertRaises(ValueError):
            self.navigateur.prochaine_direction(
                (99, 0),
                self.environnement.percevoir(),
            )

    def test_resident_mure_et_poursuite_vers_autre_cible(self):
        carte = fabriquer_carte(
            [
                "#########",
                "#R..#P###",
                "#...#####",
                "#AD.....#",
                "#########",
            ]
        )
        environnement = Environnement(carte)
        navigateur = Navigateur(environnement.informations_initiales())
        actions = []

        def surveiller(position, perception, direction):
            actions.append(direction)
            self.assertLess(len(actions), 100)

        with self.assertRaises(DestinationInaccessible):
            rejoindre(
                navigateur,
                (1, 5),
                environnement.percevoir,
                environnement.avancer,
                surveiller,
            )
        self.assertGreater(len(actions), 0)
        rejoindre(
            navigateur,
            carte["dictionnaire"]["position"],
            environnement.percevoir,
            environnement.avancer,
        )
        ligne, colonne = navigateur.position
        self.assertEqual(abs(ligne - 3) + abs(colonne - 2), 1)

    def test_toutes_les_cibles_des_cinq_cartes_fournies(self):
        dossier = (
            Path(__file__).resolve().parents[1]
            / "base_fournie"
            / "cartes"
        )
        for chemin in sorted(dossier.glob("appartement_*.json")):
            with self.subTest(carte=chemin.name):
                environnement = Environnement(rio.charger_carte(chemin))
                informations = environnement.informations_initiales()
                navigateur = Navigateur(informations)
                cibles = [
                    informations["dictionnaire"]["position"],
                    informations["armoire"]["position"],
                ]
                cibles.extend(
                    resident["position"]
                    for resident in informations["residents"]
                )
                for cible in cibles:
                    rejoindre(
                        navigateur,
                        cible,
                        environnement.percevoir,
                        environnement.avancer,
                    )
                    ligne, colonne = navigateur.position
                    self.assertEqual(
                        abs(ligne - cible[0]) + abs(colonne - cible[1]),
                        1,
                    )
                    self.assertEqual(
                        navigateur.position,
                        environnement.position_robot,
                    )


class TestsValidationCarte(unittest.TestCase):
    def test_cartes_invalides(self):
        cas = [
            ("format", lambda c: c.update(format="autre"), "format"),
            ("version booléenne", lambda c: c.update(version=True), "version"),
            ("champ absent", lambda c: c.pop("dimensions"), "dimensions"),
            ("nom invalide", lambda c: c.update(nom=5), "nom"),
            (
                "dimension invalide",
                lambda c: c["dimensions"].update(largeur=True),
                "entiers",
            ),
            (
                "dimensions incohérentes",
                lambda c: c["dimensions"].update(hauteur=99),
                "dimensions",
            ),
            (
                "grille non rectangulaire",
                lambda c: c["grille"].__setitem__(2, "#"),
                "rectangulaire",
            ),
            (
                "ligne mal typée",
                lambda c: c["grille"].__setitem__(2, None),
                "grille",
            ),
            (
                "symbole inconnu",
                lambda c: c["grille"].__setitem__(2, "#.X..##"),
                "symbole",
            ),
            (
                "bord ouvert",
                lambda c: c["grille"].__setitem__(0, "#.#####"),
                "bord",
            ),
            (
                "départ hors limites",
                lambda c: c.update(depart_robot=[99, 1]),
                "hors",
            ),
            (
                "départ mal typé",
                lambda c: c.update(depart_robot="11"),
                "position",
            ),
            (
                "départ sur mur",
                lambda c: c.update(depart_robot=[0, 1]),
                "symbole",
            ),
            ("armoire absente", lambda c: c.pop("armoire"), "armoire"),
            (
                "dictionnaire incorrect",
                lambda c: c["dictionnaire"].update(position=[1, 1]),
                "symbole",
            ),
            (
                "résidents mal typés",
                lambda c: c.update(residents=None),
                "résidents",
            ),
            (
                "résident mal typé",
                lambda c: c["residents"].append(None),
                "résident",
            ),
            (
                "identifiant en double",
                lambda c: c["residents"].append(
                    deepcopy(c["residents"][0])
                ),
                "double",
            ),
            (
                "résident hors limites",
                lambda c: c["residents"][0].update(position=[1, 99]),
                "hors",
            ),
            (
                "résident sur mur",
                lambda c: c["residents"][0].update(position=[0, 0]),
                "symbole",
            ),
            (
                "résident sans nom",
                lambda c: c["residents"][0].pop("nom"),
                "nom",
            ),
            (
                "robot supplémentaire",
                lambda c: c["grille"].__setitem__(2, "#R#..##"),
                "nombre",
            ),
        ]
        for nom, modifier, message in cas:
            with self.subTest(cas=nom):
                carte = carte_detour()
                modifier(carte)
                with self.assertRaisesRegex(rio.ErreurFichier, message):
                    Environnement(carte)


if __name__ == "__main__":
    unittest.main()
