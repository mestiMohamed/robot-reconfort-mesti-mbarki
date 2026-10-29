"""Mémoire et navigation d'un seul robot, sans accès à la carte réelle."""

from collections import deque


# Cet ordre départage les chemins de même longueur de façon reproductible.
DIRECTIONS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "O": (0, -1)}
TYPES_CASES = {"mur", "libre", "armoire", "dictionnaire", "resident"}


class DestinationInaccessible(Exception):
    """Aucune case adjacente à la cible n'est atteignable, même avec optimisme."""


class CarteMentale:
    """Les cases absentes de `cases` sont inconnues, donc supposées libres."""

    def __init__(self, informations):
        self.hauteur = informations["dimensions"]["hauteur"]
        self.largeur = informations["dimensions"]["largeur"]
        self.cases = {tuple(informations["depart_robot"]): "libre"}
        for meuble in ("armoire", "dictionnaire"):
            self.cases[tuple(informations[meuble]["position"])] = meuble
        for resident in informations["residents"]:
            self.cases[tuple(resident["position"])] = "resident"

    def dans_limites(self, position):
        l, c = position
        return 0 <= l < self.hauteur and 0 <= c < self.largeur

    def est_traversable(self, position):
        return self.dans_limites(position) and self.cases.get(position, "libre") == "libre"

    def voisins(self, position):
        l, c = position
        for dl, dc in DIRECTIONS.values():
            voisin = (l + dl, c + dc)
            if self.dans_limites(voisin):
                yield voisin

    def mettre_a_jour(self, position, perception):
        """Mémorise uniquement la case courante et ses quatre voisines."""
        if set(perception) != set(DIRECTIONS):
            raise ValueError("la perception doit contenir exactement N, S, E et O")
        if any(type_case not in TYPES_CASES for type_case in perception.values()):
            raise ValueError("la perception contient un type de case inconnu")
        position = tuple(position)
        if not self.dans_limites(position):
            raise ValueError("position du robot hors de la carte mentale")
        self.cases[position] = "libre"
        for direction, (dl, dc) in DIRECTIONS.items():
            voisin = (position[0] + dl, position[1] + dc)
            if self.dans_limites(voisin):
                self.cases[voisin] = perception[direction]


def plus_court_chemin(carte_mentale, depart, arrivees):
    """BFS optimiste ; renvoie les cases du chemin (départ inclus), ou None.

    Les arrivées sont un ensemble de cases possibles, par exemple les cases
    adjacentes à un meuble. Chaque arête coûte un déplacement.
    """
    depart = tuple(depart)
    arrivees = {tuple(case) for case in arrivees if carte_mentale.est_traversable(tuple(case))}
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
    """Décide un pas à la fois et conserve sa mémoire entre deux demandes."""

    def __init__(self, informations):
        self.position = tuple(informations["depart_robot"])
        self.carte_mentale = CarteMentale(informations)

    def prochaine_direction(self, cible, perception):
        """Rejoint une case adjacente à `cible`, sans entrer sur sa case.

        Renvoie N/S/E/O, ou None si le robot est déjà adjacent. Lève
        DestinationInaccessible si aucun chemin optimiste n'existe.
        """
        cible = tuple(cible)
        if not self.carte_mentale.dans_limites(cible):
            raise ValueError("cible hors de la carte")
        self.carte_mentale.mettre_a_jour(self.position, perception)
        arrivees = self.carte_mentale.voisins(cible)
        chemin = plus_court_chemin(self.carte_mentale, self.position, arrivees)
        if chemin is None:
            raise DestinationInaccessible(f"destination inaccessible : {cible}")
        if len(chemin) == 1:
            return None
        suivant = chemin[1]
        mouvement = (suivant[0] - self.position[0], suivant[1] - self.position[1])
        return next(direction for direction, delta in DIRECTIONS.items() if delta == mouvement)

    def confirmer_deplacement(self, direction):
        """À appeler seulement après l'exécution réussie de AVANCER."""
        if direction not in DIRECTIONS:
            raise ValueError(f"direction inconnue : {direction}")
        dl, dc = DIRECTIONS[direction]
        suivant = (self.position[0] + dl, self.position[1] + dc)
        if self.carte_mentale.cases.get(suivant) != "libre":
            raise ValueError("le déplacement doit viser une case perçue comme libre")
        self.position = suivant


def rejoindre(navigateur, cible, percevoir, avancer, journaliser=None):
    """Exécute la navigation jusqu'à une case adjacente et compte les pas.

    `percevoir()` et `avancer(direction)` sont fournis par le simulateur.
    `journaliser(position, perception, direction)` est appelé AVANT chaque
    déplacement. Le binôme y ajoute demande, casier et contenu du casier
    pour construire la trace complète. Une arrivée immédiate ne coûte rien.
    """
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
