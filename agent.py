#!/usr/bin/env python3
"""Point d'entree du robot de reconfort."""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from base_fournie import reconfort_io as rio


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
    """Charge les entrees et produit une trace minimale de demarrage."""
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
        rio.charger_dictionnaire(dossier_donnees / "dictionnaire.json")
        armoire = rio.charger_armoire(
            dossier_donnees / f"{scenario['armoire']}.json"
        )
    except rio.ErreurFichier as erreur:
        print(f"erreur de chargement : {erreur}", file=sys.stderr)
        return 1

    trace = rio.Trace(
        nom_carte=carte["nom"],
        nom_scenario=scenario["nom"],
        equipe=["A completer", "A completer"],
    )

    for demande in scenario["demandes"]:
        trace.ajouter_pas(
            demande=demande["numero"],
            position=carte["depart_robot"],
            casier=armoire["casier_depart"],
            action="ATTENDRE",
            commentaire="premier jalon : entrees chargees",
        )
        trace.ajouter_livraison(
            demande=demande["numero"],
            resident=demande["resident"],
            emotion=None,
            intensite=None,
            casier_choisi=None,
            repli="aucun",
            objet=None,
            succes=False,
            motif_echec="agent non implemente",
        )

    trace.ecrire(chemin_trace)
    print(f"entrees chargees, trace ecrite : {chemin_trace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
