import asyncio
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
import yfinance as yf
import pandas as pd
import gc
import time
from datetime import date
from dateutil.relativedelta import relativedelta


# Charger la liste tickers depuis https://live.euronext.com/en/products/equities/regulated/list
df = pd.read_excel("input.xlsx")

marches_pea = ["Euronext Paris", "Euronext Growth Paris", "Euronext Brussels"]

df_pea = df[df["Market"].isin(marches_pea)]

tickers_raw = df_pea["Symbol"].dropna().unique()

# Construire la liste avec suffixe .PA pour Paris et Growth Paris
tickers = []
for ticker in tickers_raw:
    ticker = str(ticker).strip()
    market = df_pea[df_pea["Symbol"] == ticker]["Market"].values[0]
    if market in ["Euronext Paris", "Euronext Growth Paris"]:
        ticker_yf = ticker + ".PA"
    else:
        ticker_yf = ticker
    tickers.append(ticker_yf)

# tickers = tickers[:30]  # Limiter pour tests rapides

print(f"Nombre tickers récupérés : {len(tickers)}")

# Critères
prix_min = 0.1
volume_euros_min = 1_000_000
ratio_high_open_min = 1.1
end_date = (date.today() - relativedelta(days=1)).isoformat()
start_date = (date.today() - relativedelta(years=3)).isoformat()

# DataFrame finale pour stocker résultats
resultats = pd.DataFrame()

for ticker in tickers:
    print(f"Téléchargement données pour {ticker}")
    df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
    if df.empty:
        print(f"Aucune donnée pour {ticker}")
        continue

    open_col = ('Open', ticker)
    high_col = ('High', ticker)
    close_col = ('Close', ticker)
    volume_col = ('Volume', ticker)

    df = df.dropna(subset=[open_col, high_col, close_col, volume_col])
    df["Volume_Euros"] = df[volume_col] * df[close_col]

    # Créer colonne Next_Open en shiftant sur df complet avant filtrage
    df["Next_Open"] = df[open_col].shift(-1)

    # Appliquer filtres y compris "Next_Open" non null
    filtre = (
        (df[close_col] > prix_min) &
        (df["Volume_Euros"] > volume_euros_min) &
        ((df[high_col] / df[open_col]) > ratio_high_open_min) &
        (df["Next_Open"].notna())
    )
    df_filtre = df[filtre].copy()

    # Calcul delta en pourcentage
    df_filtre["Delta_%"] = 100 * (df_filtre["Next_Open"] - df_filtre[close_col]) / df_filtre[close_col]

    # Colonnes à exporter
    export_df = pd.DataFrame({
        "Ticker": ticker,
        "Date": df_filtre.index,
        "Close": df_filtre[close_col],
        "Next_Open": df_filtre["Next_Open"],
        "Delta_%": df_filtre["Delta_%"]
    })

    # Ajout des résultats au DataFrame global
    resultats = pd.concat([resultats, export_df])

    # Libération mémoire
    del df
    del export_df
    gc.collect()

    # Pause pour éviter surcharge
    time.sleep(0.1)

# Export en CSV avec séparateur virgule standard
resultats.to_csv("output.csv", sep=';', index=True)

print("Export terminé. Fichier output.csv créé.")