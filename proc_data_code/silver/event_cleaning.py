import os
import pandas as pd

# Configuración
from use.config import DATA_PATH

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
CLEANED_DATA_3 = os.path.join(SILVER_DATA_PATH, "cleaning_3")
os.makedirs(CLEANED_DATA_3, exist_ok=True)

# Lectura de los dataframes de mapa de pases
PASS_MAP = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "pass_map.csv"), sep=";")
SHOT_MAP = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "shots_map.csv"), sep=";")

# --------------------------------------------------------------------------------------
# AGREGADO DE DATOS DE PASES
# --------------------------------------------------------------------------------------
def aggregate_pass_data(pass_df: pd.DataFrame) -> pd.DataFrame:
    
    df = pass_df.copy()

    # Asegurar tipos correctos
    df["AccuratePass"] = df["AccuratePass"].astype(int)

    # Agregación por zona
    zone_agg = (df.groupby(["Match", "Team", "Player", "Zone"]).agg(total_passes=("AccuratePass", "count"), accurate_passes=("AccuratePass", "sum")).reset_index())
    zone_agg["accuracy_pct"] = (zone_agg["accurate_passes"] / zone_agg["total_passes"])

    # Pivot para tener columnas por zona
    zone_pivot = zone_agg.pivot(index=["Match", "Team", "Player"], columns="Zone")
    zone_pivot.columns = [f"zone_{col[1]}_{col[0]}" for col in zone_pivot.columns]

    # Agregación por dirección
    dir_agg = (df.groupby(["Match", "Team", "Player", "PassDirection"]).agg(total_passes=("AccuratePass", "count"), accurate_passes=("AccuratePass", "sum")).reset_index())
    dir_agg["accuracy_pct"] = (dir_agg["accurate_passes"] / dir_agg["total_passes"])
    dir_pivot = dir_agg.pivot(index=["Match", "Team", "Player"], columns="PassDirection")
    dir_pivot.columns = [f"dir_{col[1]}_{col[0]}" for col in dir_pivot.columns]

    # Variables continuas a obtener la media
    numeric_agg = (df.groupby(["Match", "Team", "Player"]).agg(mean_angle=("Angle", "mean"), mean_length=("Length", "mean"), total_length=("Length", "sum"), mean_iniX=("IniX", "mean"), mean_iniY=("IniY", "mean")))

    # Merge final
    final_df = (numeric_agg.join(zone_pivot, how="left").join(dir_pivot, how="left").reset_index())

    # Sacamos columnas que no nos interesan
    final_df = final_df.drop(columns=['dir_no clear direction_total_passes', 'dir_no clear direction_accurate_passes', 'dir_no clear direction_accuracy_pct'])

    # Nombres de las variables y aplicamos orden
    final_df.columns = ["Match", "Team", "Player", "PassMeanAngle", "PassMeanLength", "PassTotalLength", "PassMeanX", "PassMeanY", "PassZoneBack", "PassZoneCenter", 
                        "PassZoneLeft", "PassZoneRight", "PassAccZoneBack", "PassAccZoneCenter", "PassAccZoneLeft", "PassAccZoneRight", "PassPercZoneBack", "PassPercZoneCenter",
                        "PassPercZoneLeft", "PassPercZoneRight", "PassDirBackward", "PassDirBackwardLeft", "PassDirBackwardRight", "PassDirForward", "PassDirForwardLeft", 
                        "PassDirForwardRight", "PassDirLeft", "PassDirRight", "PassAccDirBackward", "PassAccDirBackwardLeft", "PassAccDirBackwardRight", "PassAccDirForward", 
                        "PassAccDirForwardLeft", "PassAccDirForwardRight", "PassAccDirLeft", "PassAccDirRight", "PassPercDirBackward", "PassPercDirBackwardLeft",
                        "PassPercDirBackwardRight", "PassPercDirForward", "PassPercDirForwardLeft", "PassPercDirForwardRight", "PassPercDirLeft", "PassPercDirRight"]
    
    # Fillna de columnas
    final_df = final_df.fillna(0)

    return final_df

# --------------------------------------------------------------------------------------
# AGREGADO DE DATOS DE TIROS (Match, Team, Player)
# --------------------------------------------------------------------------------------
def aggregate_shot_data(shot_df: pd.DataFrame) -> pd.DataFrame:
    
    df = shot_df.copy()

    # Corregir nombre de columna si viene como PLayer (procesado anterior)
    if "PLayer" in df.columns:
        df = df.rename(columns={"PLayer": "Player"})

    # Asegurar tipos numéricos
    numeric_cols = ["IniX", "IniY", "BlockX", "BlockY", "GoalY", "GoalZ", "Length"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    group_cols = ["Match", "Team", "Player"]

    # Agregación por tipo de tiro
    type_agg = (df.groupby(group_cols + ["Type"]).agg(total_shots=("Type", "count"), mean_ini_x=("IniX", "mean"), mean_ini_y=("IniY", "mean"), mean_goal_y=("GoalY", "mean"), mean_goal_z=("GoalZ", "mean"), total_length=("Length", "sum"), mean_length=("Length", "mean")).reset_index())
    type_pivot = type_agg.pivot(index=group_cols, columns="Type")
    type_pivot.columns = [f"type_{col[1]}_{col[0]}" for col in type_pivot.columns]
    type_pivot = type_pivot.reset_index()

    # Agregación específica de goles
    goals_df = df[df["Type"] == "Goal"].copy()
    goals_agg = (goals_df.groupby(group_cols).agg(goals=("Type", "count"), goals_mean_ini_x=("IniX", "mean"), goals_mean_ini_y=("IniY", "mean"), goals_mean_goal_y=("GoalY", "mean"), goals_mean_goal_z=("GoalZ", "mean"), goals_total_length=("Length", "sum"), goals_mean_length=("Length", "mean")).reset_index())

    # Agregación por zona
    zone_agg = (df.groupby(group_cols + ["Zone"]).agg(total_shots=("Zone", "count"), total_length=("Length", "sum"), mean_length=("Length", "mean")).reset_index())
    zone_pivot = zone_agg.pivot(index=group_cols, columns="Zone")
    zone_pivot.columns = [f"zone_{col[1]}_{col[0]}" for col in zone_pivot.columns]
    zone_pivot = zone_pivot.reset_index()

    # Agregación general
    general_agg = (df.groupby(group_cols).agg(total_shots=("Type", "count"), mean_ini_x=("IniX", "mean"), mean_ini_y=("IniY", "mean"), mean_goal_y=("GoalY", "mean"), mean_goal_z=("GoalZ", "mean"), total_length=("Length", "sum"), mean_length=("Length", "mean")).reset_index())

    # Unión final
    shot_agg = (general_agg.merge(type_pivot, on=group_cols, how="left").merge(goals_agg, on=group_cols, how="left").merge(zone_pivot, on=group_cols, how="left"))

    # Rellenar columnas con nan values
    shot_agg = shot_agg.fillna(0)

    # Drop de columnas
    cols_to_drop=["type_Goal_mean_ini_x","type_Miss_mean_ini_x","type_Post_mean_ini_x","type_Saved Shot_mean_ini_x","type_Goal_mean_ini_y",
                  "type_Miss_mean_ini_y","type_Post_mean_ini_y","type_Saved Shot_mean_ini_y","type_Goal_mean_goal_y","type_Miss_mean_goal_y",
                  "type_Post_mean_goal_y","type_Saved Shot_mean_goal_y","type_Goal_mean_goal_z","type_Miss_mean_goal_z","type_Post_mean_goal_z",
                  "type_Saved Shot_mean_goal_z","type_Goal_total_length","type_Miss_total_length","type_Post_total_length","type_Saved Shot_total_length",
                  "type_Goal_mean_length","type_Miss_mean_length","type_Post_mean_length","type_Saved Shot_mean_length", "goals", "goals_total_length",
                  "zone_Back_total_length", "zone_Center_total_length", "zone_Left_total_length", "zone_Right_total_length", "total_shots", "zone_Back_total_shots",
                  "zone_Left_total_shots", "zone_Right_total_shots", "zone_Back_mean_length", "zone_Left_mean_length", "zone_Right_mean_length",
                    "zone_Center_total_shots", "zone_Center_mean_length"]
    shot_agg = shot_agg.drop(columns=[c for c in cols_to_drop if c in shot_agg.columns])

    
    # Cambio de orden en las columnas
    shot_agg.columns = ["Match", "Team", "Player", "ShotMeanX", "ShotMeanY", "MeanGoalY", "MeanGoalZ", "ShotTotalLenght", "ShotMeanLength", "TotalGoals",
                        "MissedShots", "ShotsOnPost", "SavedShots", "GoalIniX", "GoalIniY", "GoalFinalY", "GoalFinalZ", "GoalMeanLength"]

    return shot_agg

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE TRATADO DE DATOS DE EVENTING
# --------------------------------------------------------------------------------------
def main_silver_eventing_proc(player_stats_df: pd.DataFrame) -> pd.DataFrame:

    # Agregación de datos de pases
    pass_map_df = PASS_MAP.copy()
    agg_pass_map = aggregate_pass_data(pass_df=pass_map_df)

    # Agregación de datos de tiros
    shot_map_df = SHOT_MAP.copy()
    agg_shot_data = aggregate_shot_data(shot_df=shot_map_df)

    # Merge de los datos para tener también los de pase y los de tiros
    player_stats_df = player_stats_df.merge(agg_pass_map, on=["Match", "Team", "Player"], how="left").merge(agg_shot_data, on=["Match", "Team", "Player"], how="left")

    # Lista de columnas
    pass_columns = [col for col in agg_pass_map.columns if col not in {"Match", "Team", "Player"}]
    shot_columns = [col for col in agg_shot_data.columns if col not in {"Match", "Team", "Player"}]

    # Columnas actuales
    cols = player_stats_df.columns.tolist()

    # PASES
    idx_pass = cols.index("AccurateCrossShare") + 1 if "AccurateCrossShare" in cols else len(cols)
    for col in pass_columns:
        if col in cols:  # evitar errores
            cols.insert(idx_pass, cols.pop(cols.index(col)))
            idx_pass += 1
    player_stats_df = player_stats_df[cols]

    # TIROS (recalcular columnas tras reorder)
    cols = player_stats_df.columns.tolist()
    idx_shot = cols.index("BlockedShotRate") + 1 if "BlockedShotRate" in cols else len(cols)
    for col in shot_columns:
        if col in cols:
            cols.insert(idx_shot, cols.pop(cols.index(col)))
            idx_shot += 1
    player_stats_df = player_stats_df[cols]

    # Guardado de los tres dataframes
    player_stats_df.to_csv(os.path.join(CLEANED_DATA_3, "player_stats_clean_3.csv"), index=False, sep=";")
    pass_map_df.to_csv(os.path.join(CLEANED_DATA_3, "pass_map_clean_3.csv"), index=False, sep=";")
    shot_map_df.to_csv(os.path.join(CLEANED_DATA_3, "shot_map_clean_3.csv"), index=False, sep=";")

    return player_stats_df