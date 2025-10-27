# Analyse des Actions Éligibles au PEA sur 3 Ans avec yfinance

Ce script Python télécharge et analyse les données historiques boursières des actions éligibles au PEA (Plan d’Épargne en Actions) cotées sur différents marchés européens, filtrées selon des critères précis de volume, variation de prix et ratio, sur une période voulue.

## Fonctionnalités principales

- Télécharge les données historiques (prix et volume) pour une liste d’actions européennes en EUR à partir de Yahoo Finance via yfinance.
- Calcule des indicateurs personnalisés : ratio High/Open, delta % entre clôture et ouverture du jour suivant.
- Filtre les données selon des seuils : delta > 1.1%, volume en euros > 1 million, prix de clôture > 0.1€, ratio High/Open > 1.1.
- Agrège les données filtrées sur toute la période (1095 jours environ).
- Calcule des statistiques clés : delta moyen global, delta moyen par ticker, meilleur et pire ticker selon delta.
- Affiche le tableau des transactions retenues et les statistiques avec dates correspondantes.

## Structure du script

### Fonctions principales

- `telecharger_donnees_histo(ticker, start, end, interval)`: télécharge et formate les données historiques pour un ticker donné.
- `transformer_donnees(df, ticker)`: ajoute des colonnes calculées (Next_Open, High_Open_Ratio, Delta) au DataFrame historique.
- `liste_actions_pea()`: lit un fichier CSV `input.csv` et construit la liste des tickers Yahoo Finance pour les actions PEA en EUR.
- `check_conditions(df)`: applique des filtres sur delta, volume et clôture (fonction utilisée dans la boucle principale).

### Flux de la donnée

1. Lecture du fichier CSV des actions PEA.
2. Construction des tickers Yahoo Finance avec suffixes marché.
3. Boucle sur chaque ticker : téléchargement, transformation, calcul volume en euros, filtrage, ajout au DataFrame final.
4. Agrégation et calcul des statistiques finales.

## Fichier requis

- Le fichier `input.csv` doit contenir au moins les colonnes `Symbol`, `Market`, et `Currency`, et doit être téléchargé depuis la page [Euronext - All Equities](https://live.euronext.com/en/products/equities/list), puis placé à la racine du script sous le nom `input.csv`.

## Dépendances

- Python 3.x
- pandas
- tqdm
- yfinance

Installer via pip :

```bash
pip install pandas tqdm yfinance
```

## Paramètres à ajuster

- Période d’analyse dans les variables `start` et `end` (défaut : les 3 dernières années).
- Seuils de filtrage dans la fonction `check_conditions` et boucle principale (delta, volume, ratio, prix).

## Utilisation

Lancer simplement le script. Le résultat affichera :

- Le détail des transactions retenues selon critères.
- Le delta moyen global sur la période.
- Le ticker le plus performant (gagnant) et le moins performant (perdant) avec leurs meilleures et pires dates.

## Exemple de sortie

```
Ticker      Date        Volume    Open    High    Low     Close   ...
XX.PA    2022-01-03  1200000   50.12   55.50   49.00   54.00   ...
...

Delta moyen : 1.54 % sur 1234 transactions sur la période du 2022-10-27 au 2025-10-27.
Gagnant : XX.PA (3.25 %), meilleure transaction le 2024-06-15
Perdant : XX.PA (-2.50 %), pire transaction le 2023-11-10
```

## Avertissements

- Les données du marché peuvent comporter des manques ou des anomalies.
- L’analyse ne constitue pas un conseil financier.
- Vérifier la disponibilité et la mise à jour du fichier `input.csv`.
