# Robot de réconfort

Réalisé par Mohammed M'BARKI et Mohamed MESTI.

Projet du module HAI716 - Programmation orientée agents et systèmes
multi-agents.

## Objectif

Développer un robot autonome chargé de répondre aux demandes des résidents
d'un appartement. Pour chaque message, le robot doit déterminer l'émotion
exprimée, chercher un objet de réconfort adapté dans une armoire, puis le
livrer au résident concerné.

Le robot ne connaît pas les murs à l'avance. Il perçoit uniquement les
quatre cases voisines et doit construire progressivement sa propre carte de
l'environnement.

## Fonctionnement général

Pour chaque demande, le robot doit :

1. rejoindre et consulter le dictionnaire ;
2. déterminer l'émotion et son intensité ;
3. rejoindre et fouiller l'armoire ;
4. prendre un objet adapté ;
5. livrer cet objet au résident.

Le Projet 1 porte sur un seul robot. Le Projet 2 étendra le système à
plusieurs robots capables de se coordonner.

## Prérequis

- Python 3.9 ou version ultérieure ;
- aucune dépendance externe.

## Exécution

```bash
python agent.py \
  base_fournie/cartes/appartement_01.json \
  base_fournie/cartes/scenario_01.json \
  base_fournie/donnees \
  sortie.json
```

## Tester

```bash
python -m unittest discover -s tests -v
```

## Démonstration de la navigation

```bash
python demo_navigation.py base_fournie/cartes/appartement_01.json
```

L'option `--animer` affiche la carte mentale après chaque déplacement.

## Organisation actuelle

| Fichier | Rôle |
|---|---|
| `agent.py` | point d'entrée et boucle complète de traitement |
| `environnement.py` | validation, état réel, perceptions et déplacements |
| `navigation.py` | carte mentale, BFS et replanification |
| `armoire.py` | ordre des candidats, replis et trajets du sélecteur |
| `validation.py` | validation et cohérence des quatre entrées JSON |
| `demo_navigation.py` | démonstration autonome de la navigation |
| `base_fournie/reconfort_io.py` | lecture des entrées et écriture de la trace |
| `tests/` | tests automatisés du dictionnaire et de la navigation |
| `rendu.json` | commande utilisée pour l'évaluation automatique |

## État actuel

Le point d'entrée valide les quatre fichiers, construit l'environnement et
traite les demandes dans l'ordre. Le robot rejoint le dictionnaire, consulte
le message, fouille l'armoire selon l'ordre de repli imposé, prend un objet et
le livre au résident. Chaque action et chaque perception sont journalisées.
La navigation locale fonctionne sur les cinq cartes fournies : le robot
construit une carte mentale, calcule un chemin avec un parcours en largeur et
replanifie lorsqu'il découvre un mur.

## Limites connues

La stratégie recalcule un BFS complet après chaque perception. Elle privilégie
la simplicité et la robustesse plutôt que l'optimisation du nombre de calculs.
La fouille visite les candidats dans l'ordre imposé sans optimiser les
allers-retours du sélecteur entre plusieurs candidats vides.
