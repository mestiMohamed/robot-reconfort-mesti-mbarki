# Robot de réconfort
# Réalisé par Mohammed M'BARKI et Mohamed MESTI

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
python3 agent.py \
  base_fournie/cartes/appartement_01.json \
  base_fournie/cartes/scenario_01.json \
  base_fournie/donnees \
  sortie.json
```

## Tester

```bash
python3 -m unittest discover -s tests -v
```

## Démonstration de la navigation

```bash
python3 demo_navigation.py base_fournie/cartes/appartement_01.json
```

L'option `--animer` affiche la carte mentale après chaque déplacement.

## Organisation actuelle

| Fichier | Rôle |
|---|---|
| `agent.py` | point d'entrée, navigation et consultation du dictionnaire |
| `environnement.py` | validation, état réel, perceptions et déplacements |
| `navigation.py` | carte mentale, BFS et replanification |
| `validation.py` | validation et cohérence des quatre entrées JSON |
| `demo_navigation.py` | démonstration autonome de la navigation |
| `base_fournie/reconfort_io.py` | lecture des entrées et écriture de la trace |
| `tests/` | tests automatisés du dictionnaire et de la navigation |

## État actuel

Le point d'entrée valide les quatre fichiers, construit l'environnement et
traite les demandes dans l'ordre. Le robot rejoint réellement le dictionnaire,
journalise chaque déplacement et exécute `CONSULTER`. La navigation locale
fonctionne sur les cinq cartes fournies : le robot construit une carte mentale,
calcule un chemin avec un parcours en largeur et replanifie lorsqu'il découvre
un mur. La fouille de l'armoire et la livraison restent à intégrer.
