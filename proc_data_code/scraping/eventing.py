import os
import time
import zipfile
import shutil

from use.config import COMPS, DATA_PATH, EVENTING_ZIP_EUROPE, EVENTING_ZIP_ASIA, EVENTING_ZIP_NORTHAMERICA, EVENTING_ZIP_SOUTHAMERICA
from use.functions import elapsed_time_str, json_to_dict

EVENTING_PATH = os.path.join(DATA_PATH, "raw", "eventing")
TEMP_EVENTING_PATH = r"G:\temp_eventing"
os.makedirs(TEMP_EVENTING_PATH, exist_ok=True)

# Diccionarios para la información de los continentes
dict_zip = {"Europe": EVENTING_ZIP_EUROPE, "South-America": EVENTING_ZIP_SOUTHAMERICA, "North-America": EVENTING_ZIP_NORTHAMERICA, "Asia": EVENTING_ZIP_ASIA}
dict_temp_dir = {"Europe": os.path.join(TEMP_EVENTING_PATH, "temp_europe"), "South-America": os.path.join(TEMP_EVENTING_PATH, "temp_southamerica"), 
                 "North-America": os.path.join(TEMP_EVENTING_PATH, "temp_northamerica"), "Asia": os.path.join(TEMP_EVENTING_PATH, "temp_asia")}

# --------------------------------------------------------------------------------------
# Main data movement de eventing de una liga
# --------------------------------------------------------------------------------------
def main_league_eventing_data_move(league_id: int, print_info: bool = True) -> None:

    start_time = time.time()

    # Información de la liga y creación de una carpeta
    league_str = COMPS[COMPS["id"] == league_id]["tournament"].iloc[0]
    league_continent = COMPS[COMPS["id"] == league_id]["continent"].iloc[0]
    league_eventing_dir = COMPS[COMPS["id"] == league_id]["eventing_dir"].iloc[0]

    # Si no existe el directorio temporal, lo creamos y hazemos unzip del zip
    if not os.path.exists(dict_temp_dir.get(league_continent)):
        os.makedirs(dict_temp_dir.get(league_continent), exist_ok=True)
        with zipfile.ZipFile(dict_zip.get(league_continent), "r") as zip_ref:
            zip_ref.extractall(dict_temp_dir.get(league_continent))

    # Obtenemos el path de la liga
    temp_continent_dir = os.path.join(TEMP_EVENTING_PATH, dict_temp_dir.get(league_continent))
    temp_league_dir = os.path.join(temp_continent_dir, os.listdir(temp_continent_dir)[0], league_eventing_dir)

    # Buscamos la carpeta de partidos de las dos últimas temporadas
    matches_2425_path = os.path.join(temp_league_dir, "2024-2025", "partidos") if "2024-2025" in os.listdir(temp_league_dir) else os.path.join(temp_league_dir, "2025", "partidos") 
    matches_2526_path = os.path.join(temp_league_dir, "2025-2026", "partidos") if "2025-2026" in os.listdir(temp_league_dir) else os.path.join(temp_league_dir, "2026", "partidos") 

    if print_info:
        print(f"{league_str} main league eventing scraping (season 2425)                                                                                         ")
        total_matches = len(os.listdir(matches_2425_path))
        i = 1

    # Para cada partido en la temporada 2425
    for match in os.listdir(matches_2425_path):
        match_path = os.path.join(matches_2425_path, match)
        new_match_path = os.path.join(EVENTING_PATH, match.split("_")[-1])

        if print_info:
            print(f"        [{i}/{total_matches}] Moving match {match.split('_')[-1]} of league {league_str} season 2425", flush=True, end="\r")
            i += 1

        # Comprovamos si no existe
        if not os.path.exists(new_match_path) and match_path.endswith(".json"):
            if json_to_dict(json_path = match_path).get("matchInfo"):
                shutil.copy2(match_path, new_match_path)

    if print_info:
        print(f"{league_str} main league eventing scraping (season 2425) finished in {elapsed_time_str(start_time=start_time)}.")

    if print_info:
        print(f"{league_str} main league eventing scraping (season 2526)                                                                                         ")
        total_matches = len(os.listdir(matches_2526_path))
        i = 1

    start_time = time.time()

    # Para cada partido en la temporada 2425
    for match in os.listdir(matches_2526_path):
        match_path = os.path.join(matches_2526_path, match)
        new_match_path = os.path.join(EVENTING_PATH, match.split("_")[-1])

        if print_info:
            print(f"        [{i}/{total_matches}] Moving match {match.split('_')[-1]} of league {league_str} season 2526", flush=True, end="\r")
            i += 1

        # Comprovamos si no existe
        if not os.path.exists(new_match_path) and match_path.endswith(".json"):
            if json_to_dict(json_path = match_path).get("matchInfo"):
                try:
                    shutil.copy2(match_path, new_match_path)
                except:
                    continue
    
    if print_info:
        print(f"{league_str} main league eventing scraping (season 2525) finished in {elapsed_time_str(start_time=start_time)}.")