"""Démonstration de notre partie : dictionnaire, armoire, puis résidents.

Ce script montre les trajets ; il ne traite pas les messages et ne produit
pas la trace de livraison attendue pour le rendu complet.
"""

import argparse
import sys
import time
from pathlib import Path

import reconfort_io as rio
from navigation import DestinationInaccessible, Navigateur, rejoindre
from simulateur import SimulateurNavigation


def afficher(navigateur):
    """Affiche la mémoire du robot : ? inconnu, # mur, R robot."""
    symboles = {"mur": "#", "libre": ".", "armoire": "A",
                "dictionnaire": "D", "resident": "P"}
    memoire = navigateur.carte_mentale
    for l in range(memoire.hauteur):
        print("".join(
            "R" if (l, c) == navigateur.position
            else symboles.get(memoire.cases.get((l, c)), "?")
            for c in range(memoire.largeur)
        ))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("carte", nargs="?", type=Path,
                        default=Path(__file__).parent / "cartes/appartement_01.json")
    parser.add_argument("--animer", action="store_true", help="afficher la carte mentale à chaque pas")
    parser.add_argument("--delai", type=float, default=0.1, help="secondes entre deux pas animés")
    args = parser.parse_args(argv)
    if args.delai < 0:
        parser.error("--delai doit être positif ou nul")
    try:
        monde = SimulateurNavigation(rio.charger_carte(args.carte))
    except rio.ErreurFichier as err:
        print(f"erreur : {err}", file=sys.stderr)
        return 1
    informations = monde.informations_initiales()
    navigateur = Navigateur(informations)

    def journaliser(position, perception, direction):
        if args.animer:
            print("\033[2J\033[H", end="", flush=True)
            afficher(navigateur)
            print(f"AVANCER {direction} depuis {position} | {perception}", flush=True)
            time.sleep(args.delai)

    cibles = [("dictionnaire", informations["dictionnaire"]["position"]),
              ("armoire", informations["armoire"]["position"])]
    cibles.extend((resident["id"], resident["position"]) for resident in informations["residents"])
    for nom, cible in cibles:
        try:
            pas = rejoindre(navigateur, cible, monde.percevoir, monde.avancer, journaliser)
            print(f"{nom} : atteint en {pas} déplacement(s), position {navigateur.position}")
        except DestinationInaccessible:
            print(f"{nom} : inaccessible ; poursuite vers la cible suivante")
    afficher(navigateur)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
