import os
import pandas as pd
import time
import warnings
from pandas.errors import PerformanceWarning

warnings.simplefilter(action="ignore", category=PerformanceWarning)

# Configuración
from use.config import DATA_PATH
from use.functions import elapsed_time_str, need_to_upload

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
CLEANING_DATA_3 = os.path.join(SILVER_DATA_PATH, "cleaning_3")

import silver.cleaning as cl
import silver.event_cleaning as ev
import silver.player_roles as rol
import silver.player_rating as rat
import silver.aggregation as agg

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL SILVER
# --------------------------------------------------------------------------------------
def main(print_info: bool = True) -> None:

    start_time = time.time()
    
    # Primera limpieza y aplicado de la limpieza del scraping
    team_df, player_df, manager_df, match_df, player_stats_df, team_stats_df = cl.main_cleaning(print_info=print_info)

    # Aplicamos limpieza de eventing (guardado dentro de la función)
    stats_3_path = os.path.join(CLEANING_DATA_3, "player_stats_clean_3.csv")
    if os.path.exists(stats_3_path) and not need_to_upload(stats_3_path, total_days=10):
        player_stats_df = pd.read_csv(stats_3_path, sep=";")
        pass_map_df = pd.read_csv(os.path.join(CLEANING_DATA_3, "pass_map_clean_3.csv"), sep=";")
        shot_map_df = pd.read_csv(os.path.join(CLEANING_DATA_3, "shot_map_clean_3.csv"), sep=";")
    else:
        player_stats_df = ev.main_silver_eventing_proc(player_stats_df=player_stats_df)
        pass_map_df = pd.read_csv(os.path.join(CLEANING_DATA_3, "pass_map_clean_3.csv"), sep=";")
        shot_map_df = pd.read_csv(os.path.join(CLEANING_DATA_3, "shot_map_clean_3.csv"), sep=";")

    # Aplicamos roles de jugadores
    player_3_path = os.path.join(CLEANING_DATA_3, "player_clean_3.csv")
    if os.path.exists(player_3_path) and not need_to_upload(player_3_path, total_days=10):
        player_df = pd.read_csv(player_3_path, sep=";")
    else:
        player_df = rol.main(player_info=player_df, player_stats_df=player_stats_df, match_info_df=match_df, print_info=print_info)
        player_df.to_csv(player_3_path, index=False, sep=";")

    # Aplicamos rating y potencial de jugadores
    player_3_2_path = os.path.join(CLEANING_DATA_3, "player_clean_3_2.csv")
    if os.path.exists(player_3_2_path) and not need_to_upload(player_3_2_path, total_days=10):
        player_df = pd.read_csv(player_3_2_path, sep=";")
        player_stats_df = pd.read_csv(os.path.join(CLEANING_DATA_3, "player_stats_clean_3_2.csv"), sep=";")
    else:
        player_stats_df, player_df = rat.main_players_rating(match_df=match_df, player_info_df=player_df, stats_player_df=player_stats_df, team_info_df=team_df)
        player_df.to_csv(player_3_2_path, index=False, sep=";")
        player_stats_df.to_csv(os.path.join(CLEANING_DATA_3, "player_stats_clean_3_2.csv"), index=False, sep=";")

    # Agregado de datos
    agg_team_path = os.path.join(CLEANING_DATA_3, "agg_team.csv")
    agg_player_path = os.path.join(CLEANING_DATA_3, "agg_player.csv")
    if os.path.exists(agg_team_path) and not need_to_upload(agg_team_path, total_days=10):
        agg_team = pd.read_csv(agg_team_path, sep=";")
        agg_player = pd.read_csv(agg_player_path, sep=";")
    else:
        agg_output = agg.main_aggregate_data(player_stats_df=player_stats_df, team_stats_df=team_stats_df, match_info_df=match_df)
        agg_team = agg_output[1]
        agg_player = agg_output[6]
        agg_team.to_csv(agg_team_path, sep=";", index=False)
        agg_player.to_csv(agg_player_path, sep=";", index=False)

    if print_info:
        print(f"Silver data processing finished in {elapsed_time_str(start_time=start_time)}.")