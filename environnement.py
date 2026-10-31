"""Monde réel du robot : validation, perception et déplacement.

Ce module est le seul composant fonctionnel autorisé à connaître la grille
complète. L'agent reçoit les informations initiales publiques et les quatre
perceptions locales, jamais le champ ``grille`` de la carte.
"""

from copy import deepcopy
from typing import Dict, Tuple

from base_fournie import reconfort_io as rio


Position = Tuple[int, int]


class ActionImpossible(Exception):
    """Action refusée parce que ses conditions ne sont pas réunies."""


def valider_carte(carte: dict) -> None:
    """Vérifie la géométrie et les positions de la carte."""
    if not isinstance(carte, dict):
        raise rio.ErreurFichier("carte : un objet JSON est attendu")
    if (
        carte.get("format") != "robot-reconfort/carte"
        or type(carte.get("version")) is not int
        or carte["version"] != 1
    ):
        raise rio.ErreurFichier("carte : format ou version inattendus")
    if not isinstance(carte.get("nom"), str) or not carte["nom"]:
        raise rio.ErreurFichier("carte : nom absent ou invalide")

    dimensions = carte.get("dimensions")
    if not isinstance(dimensions, dict):
        raise rio.ErreurFichier("carte : dimensions absentes ou invalides")
    hauteur = dimensions.get("hauteur")
    largeur = dimensions.get("largeur")
    if any(type(n) is not int or n < 3 for n in (hauteur, largeur)):
        raise rio.ErreurFichier(
            "carte : hauteur et largeur doivent être des entiers >= 3"
        )

    grille = carte.get("grille")
    if (
        not isinstance(grille, list)
        or len(grille) != hauteur
        or any(
            not isinstance(ligne, str) or len(ligne) != largeur
            for ligne in grille
        )
    ):
        raise rio.ErreurFichier(
            "carte : grille non rectangulaire ou dimensions incohérentes"
        )
    if any(symbole not in "#.RADP" for ligne in grille for symbole in ligne):
        raise rio.ErreurFichier("carte : symbole inconnu dans la grille")
    if (
        any(symbole != "#" for symbole in grille[0] + grille[-1])
        or any(ligne[0] != "#" or ligne[-1] != "#" for ligne in grille)
    ):
        raise rio.ErreurFichier(
            "carte : le bord de la grille doit être constitué de murs"
        )

    def position_valide(position, symbole, nom):
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 2
            or any(type(n) is not int for n in position)
        ):
            raise rio.ErreurFichier(
                f"carte : position de {nom} absente ou invalide"
            )
        ligne, colonne = position
        if not (0 <= ligne < hauteur and 0 <= colonne < largeur):
            raise rio.ErreurFichier(f"carte : position de {nom} hors de la grille")
        if grille[ligne][colonne] != symbole:
            raise rio.ErreurFichier(
                f"carte : position de {nom} incompatible avec le symbole {symbole}"
            )

    position_valide(carte.get("depart_robot"), "R", "départ du robot")
    for champ, symbole in (("armoire", "A"), ("dictionnaire", "D")):
        meuble = carte.get(champ)
        if not isinstance(meuble, dict):
            raise rio.ErreurFichier(f"carte : {champ} absent ou invalide")
        position_valide(meuble.get("position"), symbole, champ)

    residents = carte.get("residents")
    if not isinstance(residents, list):
        raise rio.ErreurFichier("carte : liste des résidents absente ou invalide")
    identifiants = set()
    positions = set()
    for resident in residents:
        if (
            not isinstance(resident, dict)
            or not isinstance(resident.get("id"), str)
            or not resident["id"]
            or not isinstance(resident.get("nom"), str)
            or not resident["nom"]
        ):
            raise rio.ErreurFichier(
                "carte : identifiant ou nom de résident absent ou invalide"
            )
        identifiant = resident["id"]
        if identifiant in identifiants:
            raise rio.ErreurFichier(
                f"carte : identifiant de résident en double : {identifiant}"
            )
        position_valide(resident.get("position"), "P", identifiant)
        position = tuple(resident["position"])
        if position in positions:
            raise rio.ErreurFichier(
                "carte : deux résidents occupent la même position"
            )
        identifiants.add(identifiant)
        positions.add(position)

    nombres_attendus = (
        ("R", 1),
        ("A", 1),
        ("D", 1),
        ("P", len(residents)),
    )
    for symbole, nombre in nombres_attendus:
        if sum(ligne.count(symbole) for ligne in grille) != nombre:
            raise rio.ErreurFichier(
                f"carte : nombre de symboles {symbole} incohérent avec les positions"
            )


class Environnement:
    """Conserve l'état réel et contrôle les interactions avec la carte."""

    _DEPLACEMENTS = {
        "N": (-1, 0),
        "S": (1, 0),
        "E": (0, 1),
        "O": (0, -1),
    }

    _TYPES_CASE = {
        "#": "mur",
        ".": "libre",
        "R": "libre",
        "A": "armoire",
        "D": "dictionnaire",
        "P": "resident",
    }

    def __init__(self, carte: dict) -> None:
        valider_carte(carte)
        self._carte = deepcopy(carte)
        self._grille = tuple(carte["grille"])
        self._position_robot: Position = tuple(carte["depart_robot"])

    @property
    def position_robot(self) -> Position:
        """Retourne la position réelle courante du robot."""
        return self._position_robot

    def informations_initiales(self) -> dict:
        """Retourne les connaissances initiales autorisées, sans la grille."""
        champs = (
            "dimensions",
            "depart_robot",
            "armoire",
            "dictionnaire",
            "residents",
        )
        return deepcopy({champ: self._carte[champ] for champ in champs})

    def percevoir(self) -> Dict[str, str]:
        """Retourne uniquement le type des quatre cases adjacentes."""
        perception: Dict[str, str] = {}
        for direction in self._DEPLACEMENTS:
            ligne, colonne = self._position_voisine(direction)
            symbole = self._grille[ligne][colonne]
            perception[direction] = self._TYPES_CASE[symbole]
        return perception

    def avancer(self, direction: str) -> Position:
        """Déplace le robot d'une case si la destination est libre."""
        ligne, colonne = self._position_voisine(direction)
        symbole = self._grille[ligne][colonne]
        type_case = self._TYPES_CASE[symbole]
        if type_case != "libre":
            raise ActionImpossible(
                f"déplacement impossible vers {direction} : case {type_case}"
            )
        self._position_robot = (ligne, colonne)
        return self._position_robot

    def _position_voisine(self, direction: str) -> Position:
        """Calcule la position voisine dans une direction valide."""
        if direction not in self._DEPLACEMENTS:
            raise ValueError(f"direction inconnue : {direction!r}")
        ligne, colonne = self._position_robot
        delta_ligne, delta_colonne = self._DEPLACEMENTS[direction]
        return ligne + delta_ligne, colonne + delta_colonne
