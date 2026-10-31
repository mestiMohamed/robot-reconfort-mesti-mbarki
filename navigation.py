"""Mémoire et navigation d'un seul robot, sans accès à la carte réelle."""

from collections import deque


DIRECTIONS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1)}
TYPES_CASES = {"mur", "libre", "armoire", "dictionnaire", "resident"}


class DestinationInaccessible(Exception):
    """Aucune case adjacente à la cible n'est atteignable."""


class CarteMentale:
    """Représentation partielle du monde construite par les perceptions."""

    def __init__(self, informations: dict) -> None:
        self.hauteur = informations["dimensions"]["hauteur"]
        self.largeur = informations["dimensions"]["largeur"]
        self.cases = {tuple(informations["depart_robot"]): "libre"}
        for meuble in ("armoire", "dictionnaire"):
            self.cases[tuple(informations[meuble]["position"])] = meuble
        for resident in informations["residents"]:
            self.cases[tuple(resident["position"])] = "resident"

    def dans_limites(self, position) -> bool:
        ligne, colonne = position
        return 0 <= ligne < self.hauteur and 0 <= colonne < self.largeur

    def est_traversable(self, position) -> bool:
        """Considère les cases inconnues comme libres pour explorer."""
        return (
            self.dans_limites(position)
            and self.cases.get(position, "libre") == "libre"
        )

    def voisins(self, position):
        ligne, colonne = position
        for delta_ligne, delta_colonne in DIRECTIONS.values():
            voisin = (ligne + delta_ligne, colonne + delta_colonne)
            if self.dans_limites(voisin):
                yield voisin

    def mettre_a_jour(self, position, perception) -> None:
        """Mémorise la case courante et ses quatre voisines."""
        if set(perception) != set(DIRECTIONS):
            raise ValueError("la perception doit contenir exactement N, S, E et O")
        if any(type_case not in TYPES_CASES for type_case in perception.values()):
            raise ValueError("la perception contient un type de case inconnu")

        position = tuple(position)
        if not self.dans_limites(position):
            raise ValueError("position du robot hors de la carte mentale")
        self.cases[position] = "libre"
        for direction, (delta_ligne, delta_colonne) in DIRECTIONS.items():
            voisin = (
                position[0] + delta_ligne,
                position[1] + delta_colonne,
            )
            if self.dans_limites(voisin):
                self.cases[voisin] = perception[direction]


def plus_court_chemin(carte_mentale, depart, arrivees):
    """Calcule un plus court chemin optimiste avec un parcours en largeur."""
    depart = tuple(depart)
    arrivees = {
        tuple(case)
        for case in arrivees
        if carte_mentale.est_traversable(tuple(case))
    }
    if not arrivees or not carte_mentale.est_traversable(depart):
        return None
    if depart in arrivees:
        return [depart]

    file = deque([depart])
    predecesseurs = {depart: None}
    while file:
        courant = file.popleft()
        for voisin in carte_mentale.voisins(courant):
            if voisin in predecesseurs or not carte_mentale.est_traversable(voisin):
                continue
            predecesseurs[voisin] = courant
            if voisin in arrivees:
                chemin = [voisin]
                while predecesseurs[chemin[-1]] is not None:
                    chemin.append(predecesseurs[chemin[-1]])
                return list(reversed(chemin))
            file.append(voisin)
    return None


class Navigateur:
    """Décide un pas à la fois et conserve sa mémoire entre les demandes."""

    def __init__(self, informations: dict) -> None:
        self.position = tuple(informations["depart_robot"])
        self.carte_mentale = CarteMentale(informations)

    def prochaine_direction(self, cible, perception):
        """Choisit le prochain pas vers une case adjacente à la cible."""
        cible = tuple(cible)
        if not self.carte_mentale.dans_limites(cible):
            raise ValueError("cible hors de la carte")

        self.carte_mentale.mettre_a_jour(self.position, perception)
        arrivees = self.carte_mentale.voisins(cible)
        chemin = plus_court_chemin(
            self.carte_mentale,
            self.position,
            arrivees,
        )
        if chemin is None:
            raise DestinationInaccessible(f"destination inaccessible : {cible}")
        if len(chemin) == 1:
            return None

        suivant = chemin[1]
        mouvement = (
            suivant[0] - self.position[0],
            suivant[1] - self.position[1],
        )
        return next(
            direction
            for direction, delta in DIRECTIONS.items()
            if delta == mouvement
        )

    def confirmer_deplacement(self, direction: str) -> None:
        """Met à jour la mémoire après une action AVANCER réussie."""
        if direction not in DIRECTIONS:
            raise ValueError(f"direction inconnue : {direction}")
        delta_ligne, delta_colonne = DIRECTIONS[direction]
        suivant = (
            self.position[0] + delta_ligne,
            self.position[1] + delta_colonne,
        )
        if self.carte_mentale.cases.get(suivant) != "libre":
            raise ValueError(
                "le déplacement doit viser une case perçue comme libre"
            )
        self.position = suivant


def rejoindre(navigateur, cible, percevoir, avancer, journaliser=None) -> int:
    """Exécute la navigation jusqu'à une case adjacente à la cible."""
    pas = 0
    while True:
        perception = percevoir()
        direction = navigateur.prochaine_direction(cible, perception)
        if direction is None:
            return pas
        if journaliser is not None:
            journaliser(navigateur.position, dict(perception), direction)
        avancer(direction)
        navigateur.confirmer_deplacement(direction)
        pas += 1
