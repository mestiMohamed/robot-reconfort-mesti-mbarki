"""Validation structurelle et croisée des fichiers d'entrée."""

from base_fournie import reconfort_io as rio
from environnement import valider_carte


EMOTIONS = [
    "joie",
    "confiance",
    "peur",
    "surprise",
    "tristesse",
    "degout",
    "colere",
    "anticipation",
]
INTENSITES = ["faible", "moyenne", "forte"]


def _valider_entete(donnees, format_attendu, nom_fichier):
    if not isinstance(donnees, dict):
        raise rio.ErreurFichier(f"{nom_fichier} : un objet JSON est attendu")
    if donnees.get("format") != format_attendu:
        raise rio.ErreurFichier(f"{nom_fichier} : format inattendu")
    if type(donnees.get("version")) is not int or donnees["version"] != 1:
        raise rio.ErreurFichier(f"{nom_fichier} : version inattendue")
    if not isinstance(donnees.get("nom"), str) or not donnees["nom"]:
        raise rio.ErreurFichier(f"{nom_fichier} : nom absent ou invalide")


def valider_dictionnaire(dictionnaire):
    """Vérifie les émotions, les intensités, les entrées et les formes."""
    _valider_entete(
        dictionnaire,
        "robot-reconfort/dictionnaire",
        "dictionnaire",
    )
    if dictionnaire.get("emotions") != EMOTIONS:
        raise rio.ErreurFichier(
            "dictionnaire : liste ou ordre des émotions invalide"
        )
    if dictionnaire.get("intensites") != INTENSITES:
        raise rio.ErreurFichier(
            "dictionnaire : liste ou ordre des intensités invalide"
        )

    entrees = dictionnaire.get("entrees")
    if not isinstance(entrees, list):
        raise rio.ErreurFichier(
            "dictionnaire : liste des entrées absente ou invalide"
        )
    formes_vues = set()
    for indice, entree in enumerate(entrees):
        if not isinstance(entree, dict):
            raise rio.ErreurFichier(
                f"dictionnaire : entrée {indice} invalide"
            )
        formes = entree.get("formes")
        if (
            not isinstance(formes, list)
            or not formes
            or any(not isinstance(forme, str) or not forme for forme in formes)
        ):
            raise rio.ErreurFichier(
                f"dictionnaire : formes de l'entrée {indice} invalides"
            )
        if entree.get("emotion") not in EMOTIONS:
            raise rio.ErreurFichier(
                f"dictionnaire : émotion inconnue dans l'entrée {indice}"
            )
        if entree.get("intensite") not in INTENSITES:
            raise rio.ErreurFichier(
                f"dictionnaire : intensité inconnue dans l'entrée {indice}"
            )
        for forme in formes:
            if forme in formes_vues:
                raise rio.ErreurFichier(
                    f"dictionnaire : forme présente plusieurs fois : {forme}"
                )
            formes_vues.add(forme)


def _valider_position_casier(position, nom):
    if (
        not isinstance(position, (list, tuple))
        or len(position) != 2
        or any(type(coordonnee) is not int for coordonnee in position)
    ):
        raise rio.ErreurFichier(f"armoire : {nom} invalide")
    ligne, colonne = position
    if not (0 <= ligne < len(INTENSITES) and 0 <= colonne < len(EMOTIONS)):
        raise rio.ErreurFichier(f"armoire : {nom} hors de l'armoire")


def valider_armoire(armoire, dictionnaire):
    """Vérifie la grille de casiers et sa cohérence avec le dictionnaire."""
    _valider_entete(armoire, "robot-reconfort/armoire", "armoire")
    if armoire.get("emotions") != dictionnaire["emotions"]:
        raise rio.ErreurFichier(
            "armoire : émotions incohérentes avec le dictionnaire"
        )
    if armoire.get("intensites") != dictionnaire["intensites"]:
        raise rio.ErreurFichier(
            "armoire : intensités incohérentes avec le dictionnaire"
        )

    _valider_position_casier(armoire.get("casier_depart"), "casier de départ")
    casiers = armoire.get("casiers")
    nombre_attendu = len(EMOTIONS) * len(INTENSITES)
    if not isinstance(casiers, list) or len(casiers) != nombre_attendu:
        raise rio.ErreurFichier(
            f"armoire : {nombre_attendu} casiers sont attendus"
        )

    positions = set()
    for indice, casier in enumerate(casiers):
        if not isinstance(casier, dict):
            raise rio.ErreurFichier(f"armoire : casier {indice} invalide")
        position = (casier.get("ligne"), casier.get("colonne"))
        _valider_position_casier(position, f"position du casier {indice}")
        if position in positions:
            raise rio.ErreurFichier(
                f"armoire : casier en double à la position {position}"
            )
        positions.add(position)

        ligne, colonne = position
        if casier.get("emotion") != EMOTIONS[colonne]:
            raise rio.ErreurFichier(
                f"armoire : émotion incohérente pour le casier {position}"
            )
        if casier.get("intensite") != INTENSITES[ligne]:
            raise rio.ErreurFichier(
                f"armoire : intensité incohérente pour le casier {position}"
            )
        objet = casier.get("objet")
        if objet is not None and (not isinstance(objet, str) or not objet):
            raise rio.ErreurFichier(
                f"armoire : objet invalide pour le casier {position}"
            )


def valider_scenario(scenario, carte, armoire):
    """Vérifie les demandes et les références vers la carte et l'armoire."""
    _valider_entete(scenario, "robot-reconfort/scenario", "scénario")
    if scenario.get("carte") != carte["nom"]:
        raise rio.ErreurFichier(
            "scénario : la carte référencée ne correspond pas à la carte chargée"
        )
    if scenario.get("armoire") != armoire["nom"]:
        raise rio.ErreurFichier(
            "scénario : l'armoire référencée ne correspond pas à l'armoire chargée"
        )

    demandes = scenario.get("demandes")
    if not isinstance(demandes, list):
        raise rio.ErreurFichier(
            "scénario : liste des demandes absente ou invalide"
        )
    residents = {resident["id"] for resident in carte["residents"]}
    numeros = set()
    for indice, demande in enumerate(demandes):
        if not isinstance(demande, dict):
            raise rio.ErreurFichier(f"scénario : demande {indice} invalide")
        numero = demande.get("numero")
        if type(numero) is not int or numero < 1:
            raise rio.ErreurFichier(
                f"scénario : numéro de demande invalide à l'indice {indice}"
            )
        if numero in numeros:
            raise rio.ErreurFichier(
                f"scénario : numéro de demande en double : {numero}"
            )
        numeros.add(numero)
        resident = demande.get("resident")
        if not isinstance(resident, str) or resident not in residents:
            raise rio.ErreurFichier(
                f"scénario : résident inconnu dans la demande {numero}"
            )
        if not isinstance(demande.get("message"), str):
            raise rio.ErreurFichier(
                f"scénario : message invalide dans la demande {numero}"
            )


def valider_entrees(carte, scenario, dictionnaire, armoire):
    """Valide tous les fichiers et leurs relations avant la simulation."""
    valider_carte(carte)
    valider_dictionnaire(dictionnaire)
    valider_armoire(armoire, dictionnaire)
    valider_scenario(scenario, carte, armoire)
