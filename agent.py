#!/usr/bin/env python3
"""Point d'entree du robot de reconfort."""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from base_fournie import reconfort_io as rio
from environnement import Environnement
from navigation import Navigateur, rejoindre
from validation import valider_entrees


Emotion = Tuple[str, str]


def indexer_dictionnaire(dictionnaire: dict) -> Dict[str, Emotion]:
    """Associe chaque forme connue a son emotion et son intensite."""
    index: Dict[str, Emotion] = {}
    for entree in dictionnaire["entrees"]:
        emotion = entree["emotion"]
        intensite = entree["intensite"]
        for forme in entree["formes"]:
            index[forme] = (emotion, intensite)
    return index


def lire_emotion(
    message: str,
    index_dictionnaire: Dict[str, Emotion],
) -> Optional[Emotion]:
    """Retourne l'emotion du premier mot reconnu, sinon None."""
    for mot in rio.normaliser(message):
        if mot in index_dictionnaire:
            return index_dictionnaire[mot]
    return None


def main(argv: list[str]) -> int:
    """Charge les entrées et traite chaque demande dans l'ordre."""
    if len(argv) != 5:
        print(
            "usage : python3 agent.py <carte> <scenario> "
            "<dossier_donnees> <trace_sortie>",
            file=sys.stderr,
        )
        return 2

    chemin_carte = Path(argv[1])
    chemin_scenario = Path(argv[2])
    dossier_donnees = Path(argv[3])
    chemin_trace = Path(argv[4])

    try:
        carte = rio.charger_carte(chemin_carte)
        scenario = rio.charger_scenario(chemin_scenario)
        dictionnaire = rio.charger_dictionnaire(
            dossier_donnees / "dictionnaire.json"
        )
        armoire = rio.charger_armoire(
            dossier_donnees / f"{scenario['armoire']}.json"
        )
        valider_entrees(carte, scenario, dictionnaire, armoire)
    except rio.ErreurFichier as erreur:
        print(f"erreur de chargement : {erreur}", file=sys.stderr)
        return 1

    trace = rio.Trace(
        nom_carte=carte["nom"],
        nom_scenario=scenario["nom"],
        equipe=["Mohammed M'BARKI", "Mohamed Mesti"],
    )
    environnement = Environnement(carte)
    navigateur = Navigateur(environnement.informations_initiales())
    index_dictionnaire = indexer_dictionnaire(dictionnaire)
    casier = tuple(armoire["casier_depart"])
    position_dictionnaire = carte["dictionnaire"]["position"]

    for demande in scenario["demandes"]:
        numero = demande["numero"]

        def journaliser_deplacement(position, perception, direction):
            trace.ajouter_pas(
                demande=numero,
                position=position,
                casier=casier,
                action="AVANCER",
                argument=direction,
                perception=perception,
            )

        rejoindre(
            navigateur,
            position_dictionnaire,
            environnement.percevoir,
            environnement.avancer,
            journaliser_deplacement,
        )

        perception = environnement.percevoir()
        trace.ajouter_pas(
            demande=numero,
            position=navigateur.position,
            casier=casier,
            action="CONSULTER",
            perception=perception,
        )
        environnement.consulter()
        resultat = lire_emotion(demande["message"], index_dictionnaire)

        if resultat is None:
            emotion = None
            intensite = None
            motif_echec = "emotion indeterminee"
        else:
            emotion, intensite = resultat
            motif_echec = "agent non implemente"

        trace.ajouter_livraison(
            demande=numero,
            resident=demande["resident"],
            emotion=emotion,
            intensite=intensite,
            casier_choisi=None,
            repli="aucun",
            objet=None,
            succes=False,
            motif_echec=motif_echec,
        )

    trace.ecrire(chemin_trace)
    print(f"trace écrite : {chemin_trace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
