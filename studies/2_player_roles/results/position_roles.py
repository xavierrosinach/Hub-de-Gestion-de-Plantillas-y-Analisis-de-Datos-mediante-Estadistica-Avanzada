import numpy as np
import pandas as pd
import json

with open("all_positions_roles_averages.json", "r", encoding="utf-8") as f:
    ALL_POSITIONS_ROLES_AVG = json.load(f)

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA ENCONTRAR LA POSICIÓN ÓPTIMA POR JUGADOR SEGÚN SUS ESTADÍSTICAS EN SUS ÚLTIMOS N PARTIDOS
# --------------------------------------------------------------------------------------
def best_role_for_player(player_last_games_stats: pd.DataFrame) -> str:

    player = player_last_games_stats.copy()

    # Información necesaria
    position = player["Position"].iloc[0]
    roles_dict = ALL_POSITIONS_ROLES_AVG[position]

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