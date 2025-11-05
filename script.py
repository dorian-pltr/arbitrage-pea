# Importation des modules nécessaires
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from tqdm import tqdm
import yfinance as yf
import argparse
import io
from contextlib import redirect_stderr


# Télécharge les données historiques pour un ticker donné sur une période et transforme le format
def telecharger_donnees_histo(
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = None,
    interval: str = "1d",
    session=None,
) -> pd.DataFrame:
    # Téléchargement des données avec yfinance, en masquant les erreurs de téléchargement
    with io.StringIO() as f, redirect_stderr(f):
        kwargs = {
            "tickers": ticker,
            "interval": interval,
            "progress": False,
            "auto_adjust": True,
        }
        # Réutilise une session HTTP unique et désactive le multithreading pour limiter les descripteurs ouverts
        kwargs["session"] = session
        kwargs["threads"] = False
        if period is not None:
            kwargs["period"] = period
        else:
            kwargs["start"] = start
            kwargs["end"] = end
        df = yf.download(**kwargs)
    # Si aucun résultat, retourner un DataFrame vide avec le schéma attendu
    if df is None or df.empty:
        return pd.DataFrame(
            {
                "Ticker": pd.Series(dtype="object"),
                "Date": pd.Series(dtype="datetime64[ns]"),
                "Volume": pd.Series(dtype="float64"),
                "Open": pd.Series(dtype="float64"),
                "High": pd.Series(dtype="float64"),
                "Low": pd.Series(dtype="float64"),
                "Close": pd.Series(dtype="float64"),
                "Next_Open": pd.Series(dtype="float64"),
                "Delta": pd.Series(dtype="float64"),
                "High_Open_Ratio": pd.Series(dtype="float64"),
            }
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

    # Dictionnaire pour ajouter le suffixe Yahoo Finance selon la place (robuste aux variantes Growth/Access/Expand)
    market_suffix_map = {
        "PARIS": ".PA",
        "AMSTERDAM": ".AS",
        "BRUSSELS": ".BR",
        "MILAN": ".MI",
        "LISBON": ".LS",
        "OSLO": ".OL",
        "DUBLIN": ".IR",
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

        # Recherche du suffixe de marché (tolérant aux variantes de marché)
        suffix = None
        for market_key, sfx_val in market_suffix_map.items():
            if market_key in marche:
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
    mask = (df["Delta"] > 1.1) & (df["Volume_Euros"] > 1_000_000) & (df["Close"] > 0.1)
    df_filtered = df.loc[mask].copy()

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

# Affichage du nombre de tickers détectés
try:
    print(f"Tickers détectés: {len(tickers)}")
except Exception:
    pass

dfs = []
failed_downloads = 0

# Téléchargement et filtrage des données pour chaque ticker
for ticker in tqdm(tickers, desc=f"Téléchargement des données sur {args.jours} jours "):
    df = telecharger_donnees_histo(ticker, period=f"{args.jours + 2}d", interval="1d")
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

    # Alerte si des lignes passent les critères mais sont exclues car Next_Open est manquant
    if not df.empty:
        pre_filtre = (
            (df["Close"] > 0.1)
            & (df["Volume_Euros"] > 1_000_000)
            & (df["High_Open_Ratio"] > 1.1)
        )
        na_next_open_rows = df.loc[pre_filtre & df["Next_Open"].isna()]
        if not na_next_open_rows.empty:
            try:
                dates_missing = (
                    na_next_open_rows["Date"].dt.strftime("%Y-%m-%d").tolist()
                )
            except Exception:
                dates_missing = na_next_open_rows["Date"].astype(str).tolist()
            if len(dates_missing) > 3:
                dates_display = dates_missing[:3] + ["..."]
            else:
                dates_display = dates_missing
            print(
                f"Alerte: Next_Open manquant pour {ticker} aux dates: {dates_display}"
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

    # Calcul du delta moyen par ticker (utiliser la colonne "Ticker" pour uniformiser)
    ticker_means = df_total.groupby("Ticker")["Delta"].mean()

    # Recherche du ticker gagnant et perdant sur la période
    winner = ticker_means.idxmax()
    winner_delta = ticker_means.max()
    loser = ticker_means.idxmin()
    loser_delta = ticker_means.min()

    # Date correspondant au meilleur delta du gagnant
    best_row = (
        df_total.loc[df_total["Ticker"] == winner]
        .sort_values(by="Delta", ascending=False)
        .iloc[0]
    )
    best_date = best_row["Date"]
    # Date correspondant au moins bon delta du perdant
    worst_row = (
        df_total.loc[df_total["Ticker"] == loser].sort_values(by="Delta").iloc[0]
    )
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
