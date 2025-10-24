# Analyseur de tickers Euronext avec yfinance

Ce projet Python automatise l’analyse des actions cotées sur **Euronext** (Paris, Growth, et Bruxelles).  
En s’appuyant sur les données **Yahoo Finance**, il applique des filtres de volume et de variation journalière, puis calcule la performance entre la **clôture d’un jour et l’ouverture du lendemain**.  
Les résultats sont exportés automatiquement dans un fichier CSV nommé selon la période d’analyse.

## Fonctionnalités

- Télécharge la liste des tickers depuis le site officiel **Euronext**.
- Filtre les actions éligibles au **PEA** (Euronext Paris, Growth Paris, Bruxelles).
- Récupère les cotations via **yfinance** sur une période de trois ans.
- Applique des critères personnalisables :
  - Prix de clôture minimal (`prix_min`)
  - Volume quotidien en euros minimal (`volume_euros_min`)
  - Ratio entre le plus haut et le prix d’ouverture (`ratio_high_open_min`)
- Calcule le **delta en pourcentage** entre la clôture et l’ouverture suivante.
- Exporte automatiquement les résultats dans un fichier **CSV daté**.

## Prérequis

Avant d’exécuter le script, installer les dépendances nécessaires :

```bash
pip install yfinance pandas python-dateutil openpyxl
```

S'assurer d’avoir également **Python 3.8+** minimum installé.

## Préparation des données

1. Aller sur la page officielle Euronext :  
   [https://live.euronext.com/en/products/equities/regulated/list](https://live.euronext.com/en/products/equities/regulated/list)

2. Télécharger la liste complète des actions.

3. Placer le fichier téléchargé à la racine du projet sous le nom :

```
input.xlsx
```

## Utilisation

Exécuter simplement le script :

```bash
python script.py
```

Le script :

- Télécharge les données pour chaque symbole identifié.
- Applique les filtres.
- Calcule le delta journalier entre `Close` et `Next_Open`.
- Enregistre les résultats dans un fichier CSV nommé :

```
output_YYYY-MM-DD_to_YYYY-MM-DD.csv
```

Ce fichier contient les colonnes suivantes :

| Ticker           | Date           | Close           | Next_Open          | Delta\_%       |
| ---------------- | -------------- | --------------- | ------------------ | -------------- |
| Code de l’action | Date boursière | Prix de clôture | Ouverture suivante | Variation en % |

## Structure du projet

```
📁 projet/
├── script.py # Script principal
├── input.xlsx # Liste des actions Euronext
└── output_YYYY-MM-DD_to_YYYY-MM-DD.csv # Résultats générés
```

## Personnalisation

Ajuster les critères principaux dans le code :

```python
prix_min = 0.1
volume_euros_min = 1_000_000
ratio_high_open_min = 1.1
end_date = (date.today() - relativedelta(days=1)).isoformat() # days, months, years
start_date = (date.today() - relativedelta(years=3)).isoformat() # days, months, years
```

Augmenter ou diminuer ces seuils selon le profil d’analyse.

## Résultat attendu

L’exécution génère un CSV contenant uniquement les jours où :

- Le volume échangé dépasse le seuil.
- Le ratio **High / Open > ratio_high_open_min**.
- Le prix > `prix_min`.
- Les données du jour suivant sont disponibles pour calculer la performance.

## Licence

Ce projet est mis à disposition sous licence **MIT**.  
Libre de modification, adaptation ou intégration dans des outils d’analyse boursière.
