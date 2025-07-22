# Dashboard de Qualité des Données

Ce projet contient un dashboard Streamlit pour visualiser et analyser la qualité des données provenant de Snowflake.

## Structure du Projet

```
data_quality_dashboard/
├── main.py                 # Application principale
├── config.py              # Configuration et constantes
├── data_utils.py          # Utilitaires de traitement des données
├── viz_components.py      # Composants de visualisation
├── ui_components.py       # Composants d'interface utilisateur
├── requirements.txt       # Dépendances Python
└── README.md             # Ce fichier
```

## Description des Modules

### `main.py`
Point d'entrée principal de l'application Streamlit. Orchestre l'ensemble du dashboard en utilisant les autres modules.

### `config.py`
Contient toutes les constantes et configurations :
- Configuration Snowflake
- Couleurs et thèmes
- Seuils de qualité
- Indicateurs booléens
- Configuration par défaut

### `data_utils.py`
Fonctions utilitaires pour le traitement des données :
- Chargement depuis Snowflake
- Transformations des données
- Calculs de scores
- Création de tableaux croisés dynamiques

### `viz_components.py`
Composants de visualisation réutilisables :
- Cartes de scores
- Graphiques d'évolution
- Graphiques en donut
- Cartes de chaleur
- Graphiques en barres

### `ui_components.py`
Composants d'interface utilisateur :
- Contrôles de la barre latérale
- Filtres de dates et granularité
- Sélecteurs de référentiels et tables
- Validation des données
