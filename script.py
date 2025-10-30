# Importation des modules nécessaires
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import yfinance as yf
import argparse
import io
from contextlib import redirect_stderr


# Télécharge les données historiques pour un ticker donné sur une période et transforme le format
def telecharger_donnees_histo(
    ticker: str, start: str = None, end: str = None, interval: str = "1d"
) -> pd.DataFrame:
    # Téléchargement des données avec yfinance, en masquant les erreurs de téléchargement
    with io.StringIO() as f, redirect_stderr(f):
        df = yf.download(
            tickers=ticker,
            start=start,
            end=end,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
    # Transformation des données brutes en ajoutant des colonnes calculées
    return transformer_donnees(df, ticker)


# Transforme le DataFrame initial en ajoutant les colonnes utiles à l'analyse
def transformer_donnees(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    # Définition des colonnes à utiliser
    open_col = ("Open", ticker)
    high_col = ("High", ticker)
    low_col = ("Low", ticker)
    close_col = ("Close", ticker)
    volume_col = ("Volume", ticker)

    # Suppression des données manquantes
    df = df.dropna(subset=[open_col, high_col, close_col, volume_col])

    # Calcul du prix d'ouverture du jour suivant
    df["Next_Open"] = df[open_col].shift(-1)

    # Calcul du ratio High/Open (plus haut du jour / ouverture)
    df["High_Open_Ratio"] = df["High"] / df["Open"]

    # Calcul du delta entre la clôture et l'ouverture suivante en %
    df["Delta"] = 100 * (df["Next_Open"] - df[close_col]) / df[close_col]

    # Préparation du DataFrame final pour export/analyse
    export_df = pd.DataFrame(
        {
            "Ticker": ticker,
            "Date": df.index,
            "Volume": df[volume_col],
            "Open": df[open_col],
            "High": df[high_col],
            "Low": df[low_col],
            "Close": df[close_col],
            "Next_Open": df["Next_Open"],
            "Delta": df["Delta"],
            "High_Open_Ratio": df["High_Open_Ratio"],
        }
    )

    return export_df


# Crée la liste des tickers éligibles au PEA à partir d’un fichier CSV
def liste_actions_pea():
    liste = []

    # Dictionnaire pour ajouter le suffixe Yahoo Finance selon le marché
    market_suffix_map = {
        "EURONEXT PARIS": ".PA",
        "EURONEXT AMSTERDAM": ".AS",
        "EURONEXT BRUSSELS": ".BR",
        "EURONEXT MILAN": ".MI",
        "EURONEXT LISBON": ".LS",
        "OSLO BØRS": ".OL",
        "EURONEXT DUBLIN": ".IR",
    }

    # Lecture du fichier contenant la liste brute des actions
    df_liste_brute = pd.read_csv("input.csv", sep=";")
    df_liste = df_liste_brute.dropna(subset=["Symbol", "Market", "Currency"])

    for index, row in df_liste.iterrows():
        symbol_base = str(row["Symbol"]).strip()
        marche = str(row["Market"]).strip().upper()
        devise = str(row["Currency"]).strip().upper()

        # On ne garde que les actions en euros
        if devise != "EUR":
            continue

        # Recherche du suffixe de marché
        suffix = None
        for market_key, sfx_val in market_suffix_map.items():
            if market_key.upper() in marche:
                suffix = sfx_val
                break

        # Construction du ticker final compatible Yahoo Finance
        if suffix:
            if not symbol_base.endswith(suffix):
                ticker_final = symbol_base + suffix
            else:
                ticker_final = symbol_base
            liste.append(ticker_final)

    return liste


# Fonction de filtrage selon conditions de delta, volume et clôture
def check_conditions(df: pd.DataFrame) -> pd.DataFrame:
    # Filtre sur delta, volume et clôture minimale
    df_filtered = df[
        (df["Delta"] > 1.1) & (df["Volume_Euros"] > 1_000_000) & (df["Close"] > 0.1)
    ].copy()

    return df_filtered


# Définition de la période d’analyse : x derniers jours
parser = argparse.ArgumentParser(
    description="Script d'arbitrage PEA: nombre de jours à analyser"
)
parser.add_argument(
    "--jours", type=int, default=7, help="Nombre de jours à remonter (par défaut 7)"
)
args = parser.parse_args()

start = datetime.today() - timedelta(days=args.jours)
end = datetime.today()

# Récupération de la liste des tickers
tickers = liste_actions_pea()
# Exemple de tickers : ['ALKAL.PA', 'ADOC.PA','GNFT.PA']

dfs = []
failed_downloads = 0

# Téléchargement et filtrage des données pour chaque ticker
for ticker in tqdm(tickers, desc=f"Téléchargement des données sur {args.jours} jours "):
    df = telecharger_donnees_histo(
        ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d")
    )
    df["Volume_Euros"] = df["Volume"] * df["Close"]

    # On ignore les tickers sans données valides
    if df.empty:
        failed_downloads += 1
        continue

    # Application du filtre sur les conditions : clôture, volume, ratio high/open, présence de Next_Open
    filtre = (
        (df["Close"] > 0.1)
        & (df["Volume_Euros"] > 1_000_000)
        & (df["High_Open_Ratio"] > 1.1)
        & (df["Next_Open"].notna())
    )

    df = df[filtre].copy()

    # On ignore si aucun jour ne passe le filtre
    if df.empty:
        continue

    # Ajout de la colonne ticker pour l’analyse agrégée
    df["ticker"] = ticker

    # Stockage du DataFrame filtré
    dfs.append(df)

# Agrégation et analyse des résultats
if dfs:
    df_total = pd.concat(dfs, ignore_index=True)

    # Trie le tableau dans l'ordre chronologique
    df_total = df_total.sort_values(by="Date").reset_index(drop=True)

    # Calcul du delta moyen global toutes actions confondues
    mean_delta = df_total["Delta"].mean()
    # Calcul du nombre total de transactions retenues
    n_transactions = len(df_total)

    # Calcul du delta moyen par ticker
    ticker_means = df_total.groupby("ticker")["Delta"].mean()

    # Recherche du ticker gagnant et perdant sur la période
    winner = ticker_means.idxmax()
    winner_delta = ticker_means.max()
    loser = ticker_means.idxmin()
    loser_delta = ticker_means.min()

    # Date correspondant au meilleur delta du gagnant
    best_row = (
        df_total[df_total["ticker"] == winner]
        .sort_values("Delta", ascending=False)
        .iloc[0]
    )
    best_date = best_row["Date"]
    # Date correspondant au moins bon delta du perdant
    worst_row = df_total[df_total["ticker"] == loser].sort_values("Delta").iloc[0]
    worst_date = worst_row["Date"]

    # Affichage du DataFrame trié et des statistiques résumées avec dates
    colonnes_affichage = ["Ticker", "Date", "Close", "Next_Open", "Delta"]
    print(df_total[colonnes_affichage])
    print(
        f"\nDelta moyen : {mean_delta:.2f} % sur {n_transactions} transactions sur la période du {start.strftime('%Y-%m-%d')} au {end.strftime('%Y-%m-%d')}."
    )
    print(
        f"Gagnant : {winner} ({winner_delta:.2f} %), meilleure transaction le {best_date}"
    )
    print(f"Perdant : {loser} ({loser_delta:.2f} %), pire transaction le {worst_date}")

    # Top trade et pire trade sur la période (globaux)
    best_row = df_total.loc[df_total["Delta"].idxmax()]
    worst_row = df_total.loc[df_total["Delta"].idxmin()]
    print(
        f"Top trade : {best_row['Ticker']} ({best_row['Delta']:.2f} %) le {best_row['Date']}"
    )
    print(
        f"Pire trade : {worst_row['Ticker']} ({worst_row['Delta']:.2f} %) le {worst_row['Date']}"
    )

if failed_downloads > 0:
    print(f"\nDonnées non téléchargées pour {failed_downloads} tickers.")
