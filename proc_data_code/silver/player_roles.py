import pandas as pd
import os
import numpy as np
import json
import warnings

warnings.filterwarnings("ignore")

# Configuración
from use.config import DATA_PATH, UTILS_DIR
import silver.aggregation as agg

# Lectura del JSON con las columnas a tener en cuenta por posición
cols_json_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "cols_to_study_per_position.json")
with open(cols_json_path, "r", encoding="utf-8") as f:
    cols_to_study_per_position = json.load(f)

# Lectura del JSON con los nombres a asignar de PCA
all_positions_roles_averages_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "all_positions_roles_averages.json")
with open(all_positions_roles_averages_path, "r", encoding="utf-8") as f:
    all_positions_roles_averages = json.load(f)

# --------------------------------------------------------------------------------------
# OBTIENE EL MEJOR ROL POR UN JUGADOR COMPARANDO CON LAS MEDIAS DE CADA CLUSTER
# --------------------------------------------------------------------------------------
def best_role_for_player(player_last_games_stats: pd.DataFrame) -> str:

    player = player_last_games_stats.copy()

    # Información necesaria
    position = player["Position"].iloc[0]
    roles_dict = all_positions_roles_averages[position]

    # Columnas correctas = nombres métricas del primer rol
    cols_to_study = list(next(iter(roles_dict.values())).keys())

    # Selección columnas jugador
    player_row = player[cols_to_study].copy()

    # Vector jugador
    player_num_list = np.array(player_row.iloc[0].tolist(), dtype=float)

    # Distancias por rol
    roles_distance = {}

    for role, metrics in roles_dict.items():
        values_list = np.array(list(metrics.values()), dtype=float)
        dist = np.linalg.norm(player_num_list - values_list)
        roles_distance[role] = dist

    # Mejor rol
    best_role = min(roles_distance, key=roles_distance.get)

    return best_role

# --------------------------------------------------------------------------------------
# OBTIENE LOS ROLES DE TODOS LOS JUGADORES
# --------------------------------------------------------------------------------------
def obtain_player_role(last_matches_stats: pd.DataFrame, print_info: bool = True) -> pd.DataFrame:

    # Aplicamos posiciones generales e insertamos rol
    last_matches_stats["Position"] = np.where(last_matches_stats["Position"].isin(["LB", "RB", "LW", "RW", "CM"]), last_matches_stats["Position"].map({"LB":"FB", "RB":"FB", "LW":"WG", "RW":"WG", "CM":"DM"}), last_matches_stats["Position"])
    last_matches_stats.insert(2, "Role", None)

    total_players = len(last_matches_stats)
    i = 1

    # Para cada jugador
    for index, row in last_matches_stats.iterrows():

        # Obtenemos información necesaria y aplicamos función
        player = last_matches_stats.loc[[index]]
        player_role = best_role_for_player(player_last_games_stats=player)
        last_matches_stats.at[index, "Role"] = player_role        # Guardar resultado

        if print_info:
            print(f"          Obtaining the player role of player {player['Player'].iloc[0]} [{i}/{total_players}] ({round(100*(i/total_players), 2)}%)      ", flush=True, end="\r")
            i += 1

    # Return únicamente del jugador, posición y rol
    last_matches_stats = last_matches_stats.reset_index()
    return last_matches_stats[["Player", "Position", "Role"]].copy()

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE ROLES DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def main(player_info: pd.DataFrame, player_stats_df: pd.DataFrame, match_info_df: pd.DataFrame, print_info: bool = True) -> pd.DataFrame: 

    # Obtención de los datos de los jugadores en los últimos partidos
    stats_pl = player_stats_df.copy()
    match_info_needed = match_info_df[["ID", "League", "Season", "Date"]].copy().rename(columns={"ID":"Match"})
    stats_pl = stats_pl.merge(match_info_needed, on="Match", how="left")
    player_stats_last_5 = (stats_pl.assign(Date=pd.to_datetime(stats_pl["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Player", group_keys=False).head(5)).drop(columns=["Season", "League", "Date"])
    last_matches_stats = agg.player_aggregate_data(player_stats_df=player_stats_last_5)

    # Buscamos el perfil de cada jugador
    players_positions_roles = obtain_player_role(last_matches_stats=last_matches_stats, print_info=print_info)

    # Convertimos a diccionario
    dict_pos = dict(zip(players_positions_roles["Player"], players_positions_roles["Position"]))
    dict_role = dict(zip(players_positions_roles["Player"], players_positions_roles["Role"]))

    # Aplicar al dataframe
    player_info["Position"] = player_info["ID"].map(dict_pos)
    player_info.insert(15, "Role", player_info["ID"].map(dict_role))

    return player_info