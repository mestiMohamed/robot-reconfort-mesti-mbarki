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

## Organisation actuelle

| Fichier | Rôle |
|---|---|
| `agent.py` | point d'entrée et premier traitement du dictionnaire |
| `environnement.py` | état réel de la carte et perceptions locales |
| `base_fournie/reconfort_io.py` | lecture des entrées et écriture de la trace |
| `tests/test_agent.py` | tests automatisés des fonctionnalités disponibles |

## État actuel

Le point d'entrée charge les fichiers du projet et produit une première
trace minimale. L'environnement sait maintenant fournir les quatre
perceptions locales sans exposer la grille complète à l'agent. Il peut aussi
exécuter un déplacement vers une case libre et refuse les déplacements
illégaux. Le comportement autonome du robot est en cours de développement.
