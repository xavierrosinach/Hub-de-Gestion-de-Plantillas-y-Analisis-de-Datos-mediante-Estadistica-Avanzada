from datetime import timedelta
import pandas as pd

import scraping.sofascore as ss
import scraping.scoresway as sw
import scraping.eventing as ev

from use.config import COMPS, COMPS_PATH

# --------------------------------------------------------------------------------------
# Función main de scraping
# --------------------------------------------------------------------------------------
def main(print_info: bool = True) -> None:

    if print_info:
        print("_" * 100)

    # Copia del dataframe y conversión de fechas
    comps_copy = COMPS.copy()

    for col in ["last_scraping_ss", "last_scraping_sw", "last_eventing"]:
        comps_copy[col] = pd.to_datetime(comps_copy[col], errors="coerce")

    # Ejecutamos para cada competición
    for idx, row in comps_copy.iterrows():

        if print_info:
            print(f"MAIN SCRAPING OF '{row['tournament'].upper()}'")
            print("_" * 100)
            
        now = pd.Timestamp.now().floor("s")

        # ------------------------------------------------------------------
        # SOFASCORE
        # ------------------------------------------------------------------
        try:
            if (pd.isna(row["last_scraping_ss"]) or now - row["last_scraping_ss"] > timedelta(days=30)):
                ss.main_league_scraping(league_id=row["id"], print_info=print_info)
                now = pd.Timestamp.now().floor("s")
                comps_copy.loc[idx, "last_scraping_ss"] = now
                comps_copy.to_csv(COMPS_PATH, index=False, encoding="latin-1", sep=";")
        except:
            continue

        # ------------------------------------------------------------------
        # SCORESWAY
        # ------------------------------------------------------------------
        try:
            if (pd.isna(row["last_scraping_sw"]) or now - row["last_scraping_sw"] > timedelta(days=30)):
                sw.main_league_scraping(league_id=row["id"], print_info=print_info)
                now = pd.Timestamp.now().floor("s")
                comps_copy.loc[idx, "last_scraping_sw"] = now
                comps_copy.to_csv(COMPS_PATH, index=False, encoding="latin-1", sep=";")
        except:
            continue

        # ------------------------------------------------------------------
        # EVENTING
        # ------------------------------------------------------------------
        try:
            if (pd.isna(row["last_eventing"]) or now - row["last_eventing"] > timedelta(days=30)):
                ev.main_league_eventing_data_move(league_id=row["id"], print_info=print_info)
                now = pd.Timestamp.now().floor("s")
                comps_copy.loc[idx, "last_eventing"] = now
                comps_copy.to_csv(COMPS_PATH, index=False, encoding="latin-1", sep=";")
        except:
            continue

        if print_info:
            print("_" * 100)

    if print_info:
        print("_"*100)

    # Guardado
    comps_copy.to_csv(COMPS_PATH, index=False, encoding="latin-1", sep=";")