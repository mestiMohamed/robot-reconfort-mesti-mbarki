"""Monde réel pour la navigation : seul ce module lit les murs.

La gestion du dictionnaire, de l'armoire et des objets sera ajoutée lors
de l'intégration avec l'autre partie du projet 1.
"""

from copy import deepcopy
from pathlib import Path

import reconfort_io as rio


def valider_carte(carte):
    """Vérifie la géométrie et les positions ; lève ErreurFichier sinon."""
    if not isinstance(carte, dict):
        raise rio.ErreurFichier("carte : un objet JSON est attendu")
    if (carte.get("format") != "robot-reconfort/carte"
            or type(carte.get("version")) is not int or carte["version"] != 1):
        raise rio.ErreurFichier("carte : format ou version inattendus")
    if not isinstance(carte.get("nom"), str) or not carte["nom"]:
        raise rio.ErreurFichier("carte : nom absent ou invalide")
    dimensions = carte.get("dimensions")
    if not isinstance(dimensions, dict):
        raise rio.ErreurFichier("carte : dimensions absentes ou invalides")
    hauteur, largeur = dimensions.get("hauteur"), dimensions.get("largeur")
    if any(type(n) is not int or n < 3 for n in (hauteur, largeur)):
        raise rio.ErreurFichier("carte : hauteur et largeur doivent être des entiers >= 3")
    grille = carte.get("grille")
    if (not isinstance(grille, list) or len(grille) != hauteur
            or any(not isinstance(ligne, str) or len(ligne) != largeur for ligne in grille)):
        raise rio.ErreurFichier("carte : grille non rectangulaire ou dimensions incohérentes")
    if any(symbole not in "#.RADP" for ligne in grille for symbole in ligne):
        raise rio.ErreurFichier("carte : symbole inconnu dans la grille")
    if (any(s != "#" for s in grille[0] + grille[-1])
            or any(ligne[0] != "#" or ligne[-1] != "#" for ligne in grille)):
        raise rio.ErreurFichier("carte : le bord de la grille doit être constitué de murs")

    def position_valide(position, symbole, nom):
        if (not isinstance(position, (list, tuple)) or len(position) != 2
                or any(type(n) is not int for n in position)):
            raise rio.ErreurFichier(f"carte : position de {nom} absente ou invalide")
        l, c = position
        if not (0 <= l < hauteur and 0 <= c < largeur):
            raise rio.ErreurFichier(f"carte : position de {nom} hors de la grille")
        if grille[l][c] != symbole:
            raise rio.ErreurFichier(f"carte : position de {nom} incompatible avec le symbole {symbole}")

    position_valide(carte.get("depart_robot"), "R", "départ du robot")
    for champ, symbole in (("armoire", "A"), ("dictionnaire", "D")):
        meuble = carte.get(champ)
        if not isinstance(meuble, dict):
            raise rio.ErreurFichier(f"carte : {champ} absent ou invalide")
        position_valide(meuble.get("position"), symbole, champ)
    residents = carte.get("residents")
    if not isinstance(residents, list):
        raise rio.ErreurFichier("carte : liste des résidents absente ou invalide")
    identifiants, positions = set(), set()
    for resident in residents:
        if (not isinstance(resident, dict)
                or not isinstance(resident.get("id"), str) or not resident["id"]
                or not isinstance(resident.get("nom"), str) or not resident["nom"]):
            raise rio.ErreurFichier("carte : identifiant ou nom de résident absent ou invalide")
        identifiant = resident["id"]
        if identifiant in identifiants:
            raise rio.ErreurFichier(f"carte : identifiant de résident en double : {identifiant}")
        position_valide(resident.get("position"), "P", identifiant)
        position = tuple(resident["position"])
        if position in positions:
            raise rio.ErreurFichier("carte : deux résidents occupent la même position")
        identifiants.add(identifiant)
        positions.add(position)
    for symbole, nombre in (("R", 1), ("A", 1), ("D", 1), ("P", len(residents))):
        if sum(ligne.count(symbole) for ligne in grille) != nombre:
            raise rio.ErreurFichier(f"carte : nombre de symboles {symbole} incohérent avec les positions")


def percevoir(carte, position):
    ligne, colonne = position

    # Les quatre positions autour du robot.
    voisins = {
        "N": (ligne - 1, colonne),
        "S": (ligne + 1, colonne),
        "E": (ligne, colonne + 1),
        "O": (ligne, colonne - 1),
    }

    # Traduction des symboles de la carte.
    types = {
        "#": "mur",
        ".": "libre",
        "R": "libre",
        "A": "armoire",
        "D": "dictionnaire",
        "P": "resident",
    }

    grille = carte["grille"]
    perception = {}

    for direction, (l, c) in voisins.items():
        if 0 <= l < len(grille) and 0 <= c < len(grille[l]):
            symbole = grille[l][c]
            perception[direction] = types[symbole]
        else:
            perception[direction] = "mur"

    return perception


class SimulateurNavigation:
    """Conserve la carte réelle et refuse les déplacements illégaux."""

    def __init__(self, carte):
        valider_carte(carte)
        self._carte = deepcopy(carte)
        self.position = tuple(carte["depart_robot"])

    def informations_initiales(self):
        """Données autorisées pour l'agent, sans grille ni contenu de casier."""
        champs = ("dimensions", "depart_robot", "armoire", "dictionnaire", "residents")
        return deepcopy({champ: self._carte[champ] for champ in champs})

    def percevoir(self):
        return percevoir(self._carte, self.position)

    def avancer(self, direction):
        directions = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1)}
        if direction not in directions:
            raise ValueError(f"direction inconnue : {direction}")
        if self.percevoir()[direction] != "libre":
            raise ValueError(f"déplacement interdit vers {direction} depuis {self.position}")
        dl, dc = directions[direction]
        self.position = (self.position[0] + dl, self.position[1] + dc)
        return self.position


# Ce bloc sert à essayer notre fonction.
if __name__ == "__main__":
    carte = rio.charger_carte(Path(__file__).parent / "cartes/appartement_02.json")
    position = carte["depart_robot"]

    print("Position du robot :", position)
    print("Ce qu'il voit :", percevoir(carte, position))
