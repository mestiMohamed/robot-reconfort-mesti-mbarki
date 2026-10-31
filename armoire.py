"""Décision et déplacements dans l'armoire de réconfort."""


def distance_cyclique(indice_a, indice_b, taille):
    ecart = abs(indice_a - indice_b)
    return min(ecart, taille - ecart)


def classer_casiers(emotion, intensite, emotions, intensites):
    """Retourne les quinze casiers candidats dans l'ordre imposé."""
    colonne_cible = emotions.index(emotion)
    ligne_cible = intensites.index(intensite)
    taille = len(emotions)

    def cle(position):
        ligne, colonne = position
        horaire = (colonne - colonne_cible) % taille
        antihoraire = (colonne_cible - colonne) % taille
        distance = min(horaire, antihoraire)
        sens = 0 if horaire <= antihoraire else 1
        return (
            distance,
            abs(ligne_cible - ligne),
            ligne,
            sens,
        )

    candidats = [
        (ligne, colonne)
        for ligne in range(len(intensites))
        for colonne in range(taille)
        if distance_cyclique(colonne_cible, colonne, taille) <= 2
    ]
    return sorted(candidats, key=cle)


def determiner_repli(cible, choisi, emotions):
    """Détermine l'étiquette de repli associée au casier choisi."""
    ligne_cible, colonne_cible = cible
    ligne_choisie, colonne_choisie = choisi
    distance = distance_cyclique(
        colonne_cible,
        colonne_choisie,
        len(emotions),
    )
    if distance == 0 and ligne_cible == ligne_choisie:
        return "aucun"
    if distance == 0:
        return "intensite"
    return f"voisine_{distance}"


def mouvements_selecteur(depart, arrivee, nombre_colonnes=8):
    """Calcule un trajet minimal, vertical puis horizontal."""
    ligne, colonne = depart
    ligne_cible, colonne_cible = arrivee
    mouvements = []

    direction_verticale = "S" if ligne_cible > ligne else "N"
    mouvements.extend(
        [direction_verticale] * abs(ligne_cible - ligne)
    )

    est = (colonne_cible - colonne) % nombre_colonnes
    ouest = nombre_colonnes - est
    if est <= ouest:
        mouvements.extend(["E"] * est)
    else:
        mouvements.extend(["O"] * ouest)
    return mouvements
