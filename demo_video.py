"""Anime une livraison complète à partir de la trace réelle du robot."""

import argparse
import io
import json
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from agent import main as executer_agent
from base_fournie import reconfort_io as rio


DIRECTIONS = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "O": (0, -1),
}

SYMBOLES = {
    "mur": "#",
    "libre": ".",
    "armoire": "A",
    "dictionnaire": "D",
    "resident": "P",
}

ACTIONS = {
    "AVANCER": "Déplacement",
    "CONSULTER": "Consultation du dictionnaire",
    "CHERCHER": "Déplacement du sélecteur",
    "PRENDRE": "Prise de l'objet",
    "DONNER": "Livraison au résident",
    "ATTENDRE": "Casier vide",
}


def effacer_terminal() -> None:
    print("\033[2J\033[H", end="", flush=True)


def connaissances_initiales(carte: dict) -> dict:
    memoire = {tuple(carte["depart_robot"]): "."}
    memoire[tuple(carte["armoire"]["position"])] = "A"
    memoire[tuple(carte["dictionnaire"]["position"])] = "D"
    for resident in carte["residents"]:
        memoire[tuple(resident["position"])] = "P"
    return memoire


def memoriser_perception(memoire: dict, position, perception: dict) -> list:
    position = tuple(position)
    memoire[position] = "."
    nouveaux_murs = []
    for direction, type_case in perception.items():
        delta_ligne, delta_colonne = DIRECTIONS[direction]
        voisin = (
            position[0] + delta_ligne,
            position[1] + delta_colonne,
        )
        symbole = SYMBOLES[type_case]
        if symbole == "#" and memoire.get(voisin) != "#":
            nouveaux_murs.append(voisin)
        memoire[voisin] = symbole
    return nouveaux_murs


def afficher_carte(carte: dict, memoire: dict, position) -> None:
    hauteur = carte["dimensions"]["hauteur"]
    largeur = carte["dimensions"]["largeur"]
    for ligne in range(hauteur):
        print(
            "  "
            + " ".join(
                "R"
                if (ligne, colonne) == tuple(position)
                else memoire.get((ligne, colonne), "?")
                for colonne in range(largeur)
            )
        )


def afficher_armoire(casier) -> None:
    ligne_courante, colonne_courante = casier
    print("\nArmoire 3 x 8 :")
    print("      " + " ".join(str(colonne) for colonne in range(8)))
    for ligne in range(3):
        cases = [
            "X" if (ligne, colonne) == (ligne_courante, colonne_courante) else "·"
            for colonne in range(8)
        ]
        print(f"  {ligne}   " + " ".join(cases))


def phase(action: str, consultation_effectuee: bool, objet_pris: bool) -> str:
    if action == "CONSULTER" or not consultation_effectuee:
        return "Dictionnaire"
    if action in {"CHERCHER", "PRENDRE", "ATTENDRE"} or not objet_pris:
        return "Armoire"
    return "Résident"


def afficher_pas(
    carte: dict,
    demande: dict,
    livraison: dict,
    pas: dict,
    memoire: dict,
    nouveaux_murs: list,
    consultation_effectuee: bool,
    objet_pris: bool,
) -> None:
    effacer_terminal()
    action = pas["action"]
    argument = pas.get("argument")

    print("ROBOT DE RÉCONFORT".center(54))
    print("=" * 54)
    print(
        f"Demande {demande['numero']} - résident {demande['resident']}"
        f" - étape {pas['t'] + 1}"
    )
    print(f"Message : {demande['message']}")
    print(f"Phase   : {phase(action, consultation_effectuee, objet_pris)}")
    print("-" * 54)

    afficher_carte(carte, memoire, pas["position"])
    print("\nLégende : R robot | ? inconnu | # mur | D dictionnaire")
    print("          A armoire | P résident | . case libre")

    description = ACTIONS[action]
    if argument is not None:
        description += f" {argument}"
    print(f"\nAction  : {description}")

    if nouveaux_murs:
        murs = ", ".join(str(list(position)) for position in nouveaux_murs)
        print(f"Nouveau mur détecté en {murs} : chemin recalculé.")

    if consultation_effectuee or action == "CONSULTER":
        print(
            "Émotion : "
            f"{livraison['emotion']} ({livraison['intensite']})"
        )

    if action in {"CHERCHER", "PRENDRE", "ATTENDRE"}:
        afficher_armoire(pas["casier"])
        contenu = pas.get("contenu_casier")
        print(f"Contenu observé : {contenu if contenu else 'vide'}")


def afficher_resultat(carte, demande, livraison, memoire, position) -> None:
    effacer_terminal()
    print("ROBOT DE RÉCONFORT".center(54))
    print("=" * 54)
    afficher_carte(carte, memoire, position)
    print()
    if livraison["succes"]:
        print("LIVRAISON RÉUSSIE".center(54))
        print(f"Résident : {demande['resident']}")
        print(f"Objet    : {livraison['objet']}")
        print(
            f"Émotion  : {livraison['emotion']} "
            f"({livraison['intensite']})"
        )
        print(f"Repli    : {livraison['repli']}")
    else:
        print("LIVRAISON ÉCHOUÉE".center(54))
        print(f"Motif : {livraison['motif_echec']}")


def produire_trace(carte, scenario, donnees, trace) -> tuple[int, str]:
    sortie = io.StringIO()
    erreurs = io.StringIO()
    arguments = [
        "agent.py",
        str(carte),
        str(scenario),
        str(donnees),
        str(trace),
    ]
    with redirect_stdout(sortie), redirect_stderr(erreurs):
        code = executer_agent(arguments)
    return code, erreurs.getvalue().strip()


def analyser_arguments(argv=None):
    dossier = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--carte",
        type=Path,
        default=dossier / "base_fournie" / "cartes" / "appartement_01.json",
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=dossier / "base_fournie" / "cartes" / "scenario_01.json",
    )
    parser.add_argument(
        "--donnees",
        type=Path,
        default=dossier / "base_fournie" / "donnees",
    )
    parser.add_argument("--demande", type=int, default=1)
    parser.add_argument("--delai", type=float, default=0.28)
    parser.add_argument("--pause-finale", type=float, default=3.0)
    args = parser.parse_args(argv)
    if args.delai < 0 or args.pause_finale < 0:
        parser.error("les délais doivent être positifs ou nuls")
    return args


def main(argv=None) -> int:
    args = analyser_arguments(argv)

    try:
        carte = rio.charger_carte(args.carte)
        scenario = rio.charger_scenario(args.scenario)
    except rio.ErreurFichier as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        return 1

    demandes = {
        demande["numero"]: demande
        for demande in scenario["demandes"]
    }
    if args.demande not in demandes:
        print(f"erreur : demande {args.demande} absente du scénario", file=sys.stderr)
        return 1

    with TemporaryDirectory() as temporaire:
        chemin_trace = Path(temporaire) / "trace.json"
        code, erreur = produire_trace(
            args.carte,
            args.scenario,
            args.donnees,
            chemin_trace,
        )
        if code != 0:
            print(erreur or "erreur pendant l'exécution du robot", file=sys.stderr)
            return code
        trace = json.loads(chemin_trace.read_text(encoding="utf-8"))

    pas_demande = [
        pas for pas in trace["pas"]
        if pas["demande"] == args.demande
    ]
    livraison = next(
        livraison for livraison in trace["livraisons"]
        if livraison["demande"] == args.demande
    )
    demande = demandes[args.demande]
    memoire = connaissances_initiales(carte)
    consultation_effectuee = False
    objet_pris = False

    for pas in pas_demande:
        nouveaux_murs = memoriser_perception(
            memoire,
            pas["position"],
            pas["perception"],
        )
        afficher_pas(
            carte,
            demande,
            livraison,
            pas,
            memoire,
            nouveaux_murs,
            consultation_effectuee,
            objet_pris,
        )
        if pas["action"] == "CONSULTER":
            consultation_effectuee = True
        elif pas["action"] == "PRENDRE":
            objet_pris = True

        pause = args.delai
        if pas["action"] in {"CONSULTER", "PRENDRE"}:
            pause = max(pause, 0.9)
        elif pas["action"] == "DONNER":
            pause = max(pause, 1.2)
        time.sleep(pause)

    position_finale = pas_demande[-1]["position"]
    afficher_resultat(
        carte,
        demande,
        livraison,
        memoire,
        position_finale,
    )
    time.sleep(args.pause_finale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
