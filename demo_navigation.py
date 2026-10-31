"""Démonstration de la navigation sur une carte fournie."""

import argparse
import sys
import time
from pathlib import Path

from base_fournie import reconfort_io as rio
from environnement import Environnement
from navigation import DestinationInaccessible, Navigateur, rejoindre


def afficher(navigateur) -> None:
    """Affiche la carte mentale : ? inconnu, # mur, R robot."""
    symboles = {
        "mur": "#",
        "libre": ".",
        "armoire": "A",
        "dictionnaire": "D",
        "resident": "P",
    }
    memoire = navigateur.carte_mentale
    for ligne in range(memoire.hauteur):
        print(
            "".join(
                "R"
                if (ligne, colonne) == navigateur.position
                else symboles.get(memoire.cases.get((ligne, colonne)), "?")
                for colonne in range(memoire.largeur)
            )
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "carte",
        nargs="?",
        type=Path,
        default=(
            Path(__file__).parent
            / "base_fournie"
            / "cartes"
            / "appartement_01.json"
        ),
    )
    parser.add_argument(
        "--animer",
        action="store_true",
        help="afficher la carte mentale à chaque pas",
    )
    parser.add_argument(
        "--delai",
        type=float,
        default=0.1,
        help="secondes entre deux pas animés",
    )
    args = parser.parse_args(argv)
    if args.delai < 0:
        parser.error("--delai doit être positif ou nul")

    try:
        environnement = Environnement(rio.charger_carte(args.carte))
    except rio.ErreurFichier as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    informations = environnement.informations_initiales()
    navigateur = Navigateur(informations)

    def journaliser(position, perception, direction):
        if args.animer:
            print("\033[2J\033[H", end="", flush=True)
            afficher(navigateur)
            print(
                f"AVANCER {direction} depuis {position} | {perception}",
                flush=True,
            )
            time.sleep(args.delai)

    cibles = [
        ("dictionnaire", informations["dictionnaire"]["position"]),
        ("armoire", informations["armoire"]["position"]),
    ]
    cibles.extend(
        (resident["id"], resident["position"])
        for resident in informations["residents"]
    )
    for nom, cible in cibles:
        try:
            pas = rejoindre(
                navigateur,
                cible,
                environnement.percevoir,
                environnement.avancer,
                journaliser,
            )
            print(
                f"{nom} : atteint en {pas} déplacement(s), "
                f"position {navigateur.position}"
            )
        except DestinationInaccessible:
            print(f"{nom} : inaccessible ; poursuite vers la cible suivante")
    afficher(navigateur)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
