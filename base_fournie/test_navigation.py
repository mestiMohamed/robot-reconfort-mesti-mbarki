"""Tests du lot navigation (bibliothèque standard uniquement)."""

from copy import deepcopy
from pathlib import Path
import unittest

import reconfort_io as rio
from navigation import (CarteMentale, DestinationInaccessible, Navigateur,
                        plus_court_chemin, rejoindre)
from simulateur import SimulateurNavigation, percevoir


def fabriquer_carte(lignes):
    """Petite carte lisible à la main ; ses positions viennent des symboles."""
    carte = {"format": "robot-reconfort/carte", "version": 1, "nom": "test",
             "dimensions": {"hauteur": len(lignes), "largeur": len(lignes[0])},
             "grille": lignes, "residents": []}
    for l, ligne in enumerate(lignes):
        for c, symbole in enumerate(ligne):
            if symbole == "R":
                carte["depart_robot"] = [l, c]
            elif symbole in "AD":
                carte["armoire" if symbole == "A" else "dictionnaire"] = {"position": [l, c]}
            elif symbole == "P":
                identifiant = f"R{len(carte['residents']) + 1}"
                carte["residents"].append({"id": identifiant, "nom": identifiant, "position": [l, c]})
    return carte


def carte_detour():
    # Le chemin réel vers (1, 4) mesure 7 pas : il contourne par le bas.
    return fabriquer_carte([
        "#######",
        "#R.#.P#",
        "#.#..##",
        "#...AD#",
        "#######",
    ])


class TestsPerception(unittest.TestCase):
    def test_quatre_voisins_seulement(self):
        carte = fabriquer_carte(["#######", "#R.ADP#", "#.....#", "#######"])
        self.assertEqual(percevoir(carte, (1, 2)),
                         {"N": "mur", "S": "libre", "E": "armoire", "O": "libre"})
        self.assertEqual(percevoir(carte, (2, 4))["N"], "dictionnaire")
        self.assertEqual(percevoir(carte, (2, 5))["N"], "resident")

    def test_hors_grille_est_un_mur(self):
        self.assertEqual(percevoir(carte_detour(), (0, 0))["N"], "mur")
        self.assertEqual(percevoir(carte_detour(), (0, 0))["O"], "mur")

    def test_informations_sans_grille_et_copies_independantes(self):
        monde = SimulateurNavigation(carte_detour())
        infos = monde.informations_initiales()
        self.assertNotIn("grille", infos)
        infos["depart_robot"][0] = 99
        infos["armoire"]["position"][0] = 99
        self.assertEqual(monde.informations_initiales()["depart_robot"], [1, 1])
        self.assertEqual(monde.informations_initiales()["armoire"]["position"], [3, 4])

    def test_simulateur_refuse_murs_meubles_et_residents(self):
        carte = fabriquer_carte(["#######", "#RADP.#", "#.....#", "#######"])
        monde = SimulateurNavigation(carte)
        for direction in ("N", "O", "E", "X"):
            with self.subTest(direction=direction), self.assertRaises(ValueError):
                monde.avancer(direction)
        self.assertEqual(monde.position, (1, 1))
        monde.avancer("S")
        monde.avancer("E")
        with self.assertRaises(ValueError):
            monde.avancer("N")  # armoire
        monde.avancer("E")
        with self.assertRaises(ValueError):
            monde.avancer("N")  # dictionnaire
        monde.avancer("E")
        with self.assertRaises(ValueError):
            monde.avancer("N")  # résident


class TestsMemoireEtBFS(unittest.TestCase):
    def setUp(self):
        self.carte = carte_detour()
        self.monde = SimulateurNavigation(self.carte)
        self.memoire = CarteMentale(self.monde.informations_initiales())

    def test_aucun_mur_connu_avant_perception(self):
        self.assertNotIn("mur", self.memoire.cases.values())
        self.assertTrue(self.memoire.est_traversable((1, 3)))  # mur encore inconnu
        self.assertFalse(self.memoire.est_traversable((-1, 1)))
        for case in ((3, 4), (3, 5), (1, 5)):
            self.assertFalse(self.memoire.est_traversable(case))

    def test_mise_a_jour_locale_sans_vision_lointaine(self):
        self.memoire.mettre_a_jour((1, 1), self.monde.percevoir())
        self.assertEqual(self.memoire.cases[(0, 1)], "mur")
        self.assertEqual(self.memoire.cases[(1, 2)], "libre")
        self.assertNotIn((2, 2), self.memoire.cases)  # diagonale
        self.assertNotIn((1, 3), self.memoire.cases)  # distance 2

    def test_perception_incomplete_ou_inconnue_refusee(self):
        avant = dict(self.memoire.cases)
        for perception in ({"N": "mur"}, {"N": "mur", "S": "libre", "E": "inconnu", "O": "mur"}):
            with self.subTest(perception=perception), self.assertRaises(ValueError):
                self.memoire.mettre_a_jour((1, 1), perception)
            self.assertEqual(self.memoire.cases, avant)

    def test_chemin_de_longueur_connue(self):
        # Le test fournit une mémoire complète pour vérifier BFS seul.
        for l, ligne in enumerate(self.carte["grille"]):
            for c, symbole in enumerate(ligne):
                self.memoire.cases[(l, c)] = "libre" if symbole in ".R" else "mur"
        chemin = plus_court_chemin(self.memoire, (1, 1), {(1, 4)})
        self.assertEqual(chemin, [(1, 1), (2, 1), (3, 1), (3, 2),
                                 (3, 3), (2, 3), (2, 4), (1, 4)])
        self.assertEqual(len(chemin) - 1, 7)

    def test_bfs_choisit_la_plus_proche_des_arrivees(self):
        chemin = plus_court_chemin(self.memoire, (1, 1), {(3, 3), (1, 2)})
        self.assertEqual(chemin, [(1, 1), (1, 2)])
        self.assertEqual(plus_court_chemin(self.memoire, (1, 1), {(1, 1)}), [(1, 1)])
        self.assertIsNone(plus_court_chemin(self.memoire, (1, 1), set()))
        self.assertIsNone(plus_court_chemin(self.memoire, (1, 1), {(3, 4)}))  # armoire


class TestsNavigation(unittest.TestCase):
    def setUp(self):
        self.monde = SimulateurNavigation(carte_detour())
        self.infos = self.monde.informations_initiales()
        self.navigateur = Navigateur(self.infos)
        self.cible = self.infos["residents"][0]["position"]

    def test_mur_decouvert_provoque_un_detour(self):
        mouvements = []

        def journaliser(position, perception, direction):
            mouvements.append(direction)
            self.assertEqual(perception[direction], "libre")
            self.assertEqual(position, self.monde.position)  # avant l'action

        pas = rejoindre(self.navigateur, self.cible, self.monde.percevoir,
                        self.monde.avancer, journaliser)
        self.assertEqual(mouvements[:3], ["E", "O", "S"])
        self.assertEqual(pas, len(mouvements))
        self.assertEqual(self.navigateur.carte_mentale.cases[(1, 3)], "mur")
        self.assertEqual(self.navigateur.position, (1, 4))
        self.assertEqual(self.navigateur.position, self.monde.position)

    def test_arrivee_deja_adjacente_sans_action(self):
        cible = self.infos["armoire"]["position"]
        rejoindre(self.navigateur, cible, self.monde.percevoir, self.monde.avancer)

        def action_interdite(*args):
            self.fail("aucune action ne doit être exécutée")

        self.assertEqual(rejoindre(self.navigateur, cible, self.monde.percevoir,
                                  action_interdite, action_interdite), 0)

    def test_memoire_et_position_persistent_entre_cibles(self):
        rejoindre(self.navigateur, self.cible, self.monde.percevoir, self.monde.avancer)
        memoire = self.navigateur.carte_mentale
        anciennes_cases = dict(memoire.cases)
        rejoindre(self.navigateur, self.infos["armoire"]["position"],
                  self.monde.percevoir, self.monde.avancer)
        self.assertIs(self.navigateur.carte_mentale, memoire)
        self.assertTrue(anciennes_cases.items() <= memoire.cases.items())
        self.assertEqual(self.navigateur.position, self.monde.position)

    def test_deplacement_inconnu_non_confirme(self):
        with self.assertRaises(ValueError):
            self.navigateur.confirmer_deplacement("E")  # pas encore perçu
        self.assertEqual(self.navigateur.position, (1, 1))

    def test_echec_execution_ne_deplace_pas_la_memoire(self):
        def avancer_en_echec(direction):
            raise RuntimeError("action refusée")

        with self.assertRaises(RuntimeError):
            rejoindre(self.navigateur, self.cible, self.monde.percevoir, avancer_en_echec)
        self.assertEqual(self.navigateur.position, (1, 1))

    def test_cible_hors_limites(self):
        with self.assertRaises(ValueError):
            self.navigateur.prochaine_direction((99, 0), self.monde.percevoir())

    def test_resident_mure_et_poursuite_vers_autre_cible(self):
        carte = fabriquer_carte([
            "#########",
            "#R..#P###",
            "#...#####",
            "#AD.....#",
            "#########",
        ])
        monde = SimulateurNavigation(carte)
        navigateur = Navigateur(monde.informations_initiales())
        actions = []

        def surveiller(position, perception, direction):
            actions.append(direction)
            self.assertLess(len(actions), 100, "le robot ne doit pas tourner en boucle")

        with self.assertRaises(DestinationInaccessible):
            rejoindre(navigateur, (1, 5), monde.percevoir, monde.avancer, surveiller)
        self.assertGreater(len(actions), 0)  # preuve acquise par exploration
        rejoindre(navigateur, carte["dictionnaire"]["position"], monde.percevoir, monde.avancer)
        l, c = navigateur.position
        self.assertEqual(abs(l - 3) + abs(c - 2), 1)

    def test_toutes_les_cibles_des_cinq_cartes_fournies(self):
        dossier = Path(__file__).parent / "cartes"
        for chemin in sorted(dossier.glob("appartement_*.json")):
            with self.subTest(carte=chemin.name):
                carte = rio.charger_carte(chemin)
                monde = SimulateurNavigation(carte)
                infos = monde.informations_initiales()
                navigateur = Navigateur(infos)
                cibles = [infos["dictionnaire"]["position"], infos["armoire"]["position"]]
                cibles.extend(resident["position"] for resident in infos["residents"])
                for cible in cibles:
                    def verifier(position, perception, direction):
                        self.assertEqual(position, monde.position)
                        self.assertEqual(perception, monde.percevoir())
                        self.assertEqual(perception[direction], "libre")
                    rejoindre(navigateur, cible, monde.percevoir, monde.avancer, verifier)
                    l, c = navigateur.position
                    self.assertEqual(abs(l - cible[0]) + abs(c - cible[1]), 1)
                    self.assertEqual(navigateur.position, monde.position)


class TestsValidationCarte(unittest.TestCase):
    def test_cartes_invalides(self):
        cas = [
            ("format", lambda c: c.update(format="autre"), "format"),
            ("version booléenne", lambda c: c.update(version=True), "version"),
            ("champ absent", lambda c: c.pop("dimensions"), "dimensions"),
            ("nom invalide", lambda c: c.update(nom=5), "nom"),
            ("dimension invalide", lambda c: c["dimensions"].update(largeur=True), "entiers"),
            ("dimensions incohérentes", lambda c: c["dimensions"].update(hauteur=99), "dimensions"),
            ("grille non rectangulaire", lambda c: c["grille"].__setitem__(2, "#"), "rectangulaire"),
            ("ligne mal typée", lambda c: c["grille"].__setitem__(2, None), "grille"),
            ("symbole inconnu", lambda c: c["grille"].__setitem__(2, "#.X..##"), "symbole"),
            ("bord ouvert", lambda c: c["grille"].__setitem__(0, "#.#####"), "bord"),
            ("départ hors limites", lambda c: c.update(depart_robot=[99, 1]), "hors"),
            ("départ mal typé", lambda c: c.update(depart_robot="11"), "position"),
            ("départ sur mur", lambda c: c.update(depart_robot=[0, 1]), "symbole"),
            ("armoire absente", lambda c: c.pop("armoire"), "armoire"),
            ("dictionnaire incorrect", lambda c: c["dictionnaire"].update(position=[1, 1]), "symbole"),
            ("résidents mal typés", lambda c: c.update(residents=None), "résidents"),
            ("résident mal typé", lambda c: c["residents"].append(None), "résident"),
            ("identifiant en double", lambda c: c["residents"].append(deepcopy(c["residents"][0])), "double"),
            ("résident hors limites", lambda c: c["residents"][0].update(position=[1, 99]), "hors"),
            ("résident sur mur", lambda c: c["residents"][0].update(position=[0, 0]), "symbole"),
            ("résident sans nom", lambda c: c["residents"][0].pop("nom"), "nom"),
            ("robot supplémentaire", lambda c: c["grille"].__setitem__(2, "#R#..##"), "nombre"),
        ]
        for nom, modifier, message in cas:
            with self.subTest(cas=nom):
                carte = carte_detour()
                modifier(carte)
                with self.assertRaisesRegex(rio.ErreurFichier, message):
                    SimulateurNavigation(carte)


if __name__ == "__main__":
    unittest.main()
