#!/usr/bin/env python3
"""Point d'entree du robot de reconfort."""

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from armoire import classer_casiers, determiner_repli, mouvements_selecteur
from base_fournie import reconfort_io as rio
from environnement import Environnement
from navigation import DestinationInaccessible, Navigateur, rejoindre
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
    environnement = Environnement(carte, armoire)
    navigateur = Navigateur(environnement.informations_initiales())
    index_dictionnaire = indexer_dictionnaire(dictionnaire)
    informations_armoire = environnement.informations_armoire()
    emotions = informations_armoire["emotions"]
    intensites = informations_armoire["intensites"]
    position_dictionnaire = carte["dictionnaire"]["position"]
    position_armoire = carte["armoire"]["position"]
    positions_residents = {
        resident["id"]: resident["position"]
        for resident in carte["residents"]
    }

    def contenu_visible():
        if "armoire" in environnement.percevoir().values():
            return environnement.contenu_casier()
        return None

    def journaliser_deplacement(numero):
        def journaliser(position, perception, direction):
            trace.ajouter_pas(
                demande=numero,
                position=position,
                casier=environnement.casier_courant,
                action="AVANCER",
                argument=direction,
                perception=perception,
                contenu_casier=contenu_visible(),
            )

        return journaliser

    for demande in scenario["demandes"]:
        numero = demande["numero"]

        rejoindre(
            navigateur,
            position_dictionnaire,
            environnement.percevoir,
            environnement.avancer,
            journaliser_deplacement(numero),
        )

        perception = environnement.percevoir()
        trace.ajouter_pas(
            demande=numero,
            position=navigateur.position,
            casier=environnement.casier_courant,
            action="CONSULTER",
            perception=perception,
            contenu_casier=contenu_visible(),
        )
        environnement.consulter()
        resultat = lire_emotion(demande["message"], index_dictionnaire)

        if resultat is None:
            trace.ajouter_livraison(
                demande=numero,
                resident=demande["resident"],
                emotion=None,
                intensite=None,
                casier_choisi=None,
                repli="aucun",
                objet=None,
                succes=False,
                motif_echec="emotion indeterminee",
            )
            continue

        emotion, intensite = resultat
        rejoindre(
            navigateur,
            position_armoire,
            environnement.percevoir,
            environnement.avancer,
            journaliser_deplacement(numero),
        )

        candidats = classer_casiers(
            emotion,
            intensite,
            emotions,
            intensites,
        )
        casier_choisi = None
        objet = None
        for candidat in candidats:
            mouvements = mouvements_selecteur(
                environnement.casier_courant,
                candidat,
                len(emotions),
            )
            for direction in mouvements:
                perception = environnement.percevoir()
                trace.ajouter_pas(
                    demande=numero,
                    position=navigateur.position,
                    casier=environnement.casier_courant,
                    action="CHERCHER",
                    argument=direction,
                    perception=perception,
                    contenu_casier=environnement.contenu_casier(),
                )
                environnement.chercher(direction)

            objet_courant = environnement.contenu_casier()
            if objet_courant is not None:
                perception = environnement.percevoir()
                trace.ajouter_pas(
                    demande=numero,
                    position=navigateur.position,
                    casier=environnement.casier_courant,
                    action="PRENDRE",
                    argument=objet_courant,
                    perception=perception,
                    contenu_casier=objet_courant,
                )
                environnement.prendre(objet_courant)
                casier_choisi = candidat
                objet = objet_courant
                break

            trace.ajouter_pas(
                demande=numero,
                position=navigateur.position,
                casier=environnement.casier_courant,
                action="ATTENDRE",
                perception=environnement.percevoir(),
                contenu_casier=None,
                commentaire="casier candidat vide",
            )

        if objet is None:
            trace.ajouter_livraison(
                demande=numero,
                resident=demande["resident"],
                emotion=emotion,
                intensite=intensite,
                casier_choisi=None,
                repli="aucun",
                objet=None,
                succes=False,
                motif_echec="armoire vide",
            )
            continue

        position_resident = positions_residents[demande["resident"]]
        try:
            rejoindre(
                navigateur,
                position_resident,
                environnement.percevoir,
                environnement.avancer,
                journaliser_deplacement(numero),
            )
        except DestinationInaccessible:
            trace.ajouter_livraison(
                demande=numero,
                resident=demande["resident"],
                emotion=emotion,
                intensite=intensite,
                casier_choisi=casier_choisi,
                repli=determiner_repli(
                    (intensites.index(intensite), emotions.index(emotion)),
                    casier_choisi,
                    emotions,
                ),
                objet=objet,
                succes=False,
                motif_echec="resident inaccessible",
            )
            continue

        trace.ajouter_pas(
            demande=numero,
            position=navigateur.position,
            casier=environnement.casier_courant,
            action="DONNER",
            argument=objet,
            perception=environnement.percevoir(),
            contenu_casier=contenu_visible(),
        )
        environnement.donner(objet, position_resident)
        trace.ajouter_livraison(
            demande=numero,
            resident=demande["resident"],
            emotion=emotion,
            intensite=intensite,
            casier_choisi=casier_choisi,
            repli=determiner_repli(
                (intensites.index(intensite), emotions.index(emotion)),
                casier_choisi,
                emotions,
            ),
            objet=objet,
            succes=True,
        )

    trace.ecrire(chemin_trace)
    print(f"trace écrite : {chemin_trace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
