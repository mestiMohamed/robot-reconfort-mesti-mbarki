"""Environnement reel du robot de reconfort.

Ce module est le seul composant fonctionnel autorise a connaitre la grille
complete. L'agent ne recevra que les perceptions locales produites par la
classe : il ne manipulera jamais directement le champ ``grille`` de la carte.
"""

from typing import Dict, Tuple


Position = Tuple[int, int]


class Environnement:
    """Conserve l'etat reel et produit les perceptions du robot."""

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
        self._grille = tuple(carte["grille"])
        self._position_robot: Position = tuple(carte["depart_robot"])

    @property
    def position_robot(self) -> Position:
        """Retourne la position reelle courante du robot."""
        return self._position_robot

    def percevoir(self) -> Dict[str, str]:
        """Retourne uniquement le type des quatre cases adjacentes."""
        ligne, colonne = self._position_robot
        perception: Dict[str, str] = {}

        for direction, (delta_ligne, delta_colonne) in self._DEPLACEMENTS.items():
            symbole = self._grille[ligne + delta_ligne][colonne + delta_colonne]
            perception[direction] = self._TYPES_CASE[symbole]

        return perception
