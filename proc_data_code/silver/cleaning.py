import os
import pandas as pd
import numpy as np
from typing import Tuple
import warnings
from pandas.errors import PerformanceWarning
import time

warnings.simplefilter(action="ignore", category=PerformanceWarning)
warnings.filterwarnings("ignore")

# Configuración
from use.config import UTILS_DIR, ACT_SEASON, DATA_PATH
from use.functions import json_to_dict, df_safe_div, need_to_upload, elapsed_time_str

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
os.makedirs(SILVER_DATA_PATH, exist_ok=True)

# Lectura de todos los dataframes de bronze
MANAGER_INFO = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "manager.csv"), sep=";")
PLAYER_INFO = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "player.csv"), sep=";")
TEAM_INFO = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "team.csv"), sep=";")
MATCH_INFO = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "matches.csv"), sep=";")
PLAYER_STATS = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "player_stats.csv"), sep=";")
TEAM_STATS = pd.read_csv(os.path.join(BRONZE_DATA_PATH, "unified_data", "team_stats.csv"), sep=";")

# Lectura del diccionario de Elo rating medio por país al 2021
dict_elo_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "dict_elo.json")
dict_elo_country = json_to_dict(json_path=dict_elo_path) 

# Lectura de todos los diccionarios de formaciones
dict_formations = {}
dict_formations_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "dict_formations")
for formation_json in os.listdir(dict_formations_path):
    formation_dict_path = os.path.join(dict_formations_path, formation_json)
    formation_name = formation_json.replace(".json", "").replace("_", "-")
    dict_formations[formation_name] = json_to_dict(json_path=formation_dict_path)

# Diccionario con la formación y lista con las posibles posiciones donde se puede jugar
dict_formations_positions = {}
for formation in dict_formations.keys():
    dict_formations_positions[formation] = sorted(set(dict_formations[formation].values()))

# Lectura del dataframe de formaciones mapeado
mapped_formations_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "mapped_formations.json")
map_formations = json_to_dict(json_path=mapped_formations_path)

# JSON con lista ordenada de columnas de team_stats
team_stats_order_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "team_stats_order_columns.json")
team_stats_order = json_to_dict(json_path=team_stats_order_path).get("cols_order")

# JSON con lista ordenada de columnas de player_stats
player_stats_order_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "player_stats_order_columns.json")
player_stats_order = json_to_dict(json_path=player_stats_order_path).get("cols_order")

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE INFORMACIÓN DE LOS ENTRENADORES
# --------------------------------------------------------------------------------------
def manager_cleaning_1() -> pd.DataFrame:

    # Función para obtener el diccionario con el último entrenador de cada equipo
    def obtain_last_teams_manager() -> dict:

        manager_df_copy = MANAGER_INFO.dropna(subset="IdSS").copy()
        team_df_copy = TEAM_INFO.dropna(subset="Manager").copy()

        # Transformación de columnas a strings
        manager_df_copy["IdSS"] = manager_df_copy["IdSS"].astype(int).astype(str)
        team_df_copy["Manager"] = team_df_copy["Manager"].astype(int).astype(str)

        # Diccionario con el ID de manager de sofascore y ID interno
        manager_ss_to_id = dict(zip(manager_df_copy["IdSS"], manager_df_copy["ID"]))
        team_df_copy["Manager"] = team_df_copy["Manager"].map(manager_ss_to_id)

        return dict(zip(team_df_copy["ID"], team_df_copy["Manager"]))

    # Información necesaria
    df = MANAGER_INFO.copy()
    team_last_manager = obtain_last_teams_manager()

    # Invertimos diccionario de entrenadores - aplicamos para crear columna manager
    team_last_manager = {k: v for k, v in team_last_manager.items() if pd.notna(v)}
    manager_last_team = {v: k for k, v in team_last_manager.items()}                    # Invertimos para aplicar al df
    df["Team"] = df["ID"].map(manager_last_team)

    # Limpieza principal
    df = df[df["Type"] == "coach"]          # Sacar aquellos entrenadores que no son "coach"
    df = df[df["Team"].notna()]             # Evitar valores nulos en equipo

    # Sacamos estadísticas - solo queremos información aquí
    df = df.drop(columns=["Type","Matches","Wins","Draws","Losses","GoalsFor","GoalsAgainst","Points"])  

    # Sacamos columnas de nombres
    df = df.drop(columns=["ShortName", "LongName", "ShortFirstName", "ShortLastName"])

    return df.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE INFORMACIÓN DE LOS EQUIPOS
# --------------------------------------------------------------------------------------
def team_cleaning_1(team_manager_dict: dict) -> pd.DataFrame:

    df = TEAM_INFO.copy()

    # Sacar nombres y color de texto
    df = df.drop(columns=["ShortName", "LongName", "TextColour"])

    # Añadimos abreviación en caso de que no exista - tres primeras letras de slug
    df["Abbreviation"] = np.where(df["Abbreviation"].isna(), df["Slug"].fillna("").str[:3].str.upper(), df["Abbreviation"])

    # Fill nan con color principal equipación local y equipación visitante
    df["HomeKitCol1"] = np.where(df["HomeKitCol1"].isna(), df["PrimaryColour"], df["HomeKitCol1"])
    df["HomeShortsCol"] = np.where(df["HomeShortsCol"].isna(), df["PrimaryColour"], df["HomeShortsCol"])
    df["AwayKitCol1"] = np.where(df["AwayKitCol1"].isna(), df["PrimaryColour"], df["AwayKitCol1"])
    df["AwayShortsCol"] = np.where(df["AwayShortsCol"].isna(), df["PrimaryColour"], df["AwayShortsCol"])

    # En caso que el color primario sea blanco, lo cambiamos por el secundario
    mask = df["PrimaryColour"].str.lower() == "#ffffff"
    df.loc[mask, ["PrimaryColour", "SecondaryColour"]] = df.loc[mask, ["SecondaryColour", "PrimaryColour"]].values

    # En caso que siga siendo blanco, añadimos el primer color que encontramos en las siguientes columnas que tampoco lo sea
    colours_columns = ["PrimaryColour", "SecondaryColour", "HomeKitCol1", "HomeKitCol2", "HomeShortsCol", "AwayKitCol1", "AwayKitCol2", "AwayShortsCol"]

    # Función para obtener el primer color válido de la fila
    def get_first_non_white_colour(row, columns):
        for col in columns:
            value = row[col]
            if pd.notna(value) and value != "#ffffff":
                return value
        return row["PrimaryColour"] 

    # Solo para filas donde PrimaryColour sigue siendo blanco
    mask_white = df["PrimaryColour"].str.lower() == "#ffffff"
    df.loc[mask_white, "PrimaryColour"] = df.loc[mask_white].apply(lambda row: get_first_non_white_colour(row, colours_columns[1:]), axis=1)

    # En caso que siga blanco, ponemos un color oscuro
    df["PrimaryColour"] = np.where(df["PrimaryColour"]=="#ffffff", "#919191", df["PrimaryColour"])

    # Sacamos venue ya que no vamos a usarlo
    df = df.drop(columns="Venue")

    # Añadimos el manager
    df["Manager"] = df["ID"].map(team_manager_dict)

    return df.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE INFORMACIÓN DE PARTIDOS
# --------------------------------------------------------------------------------------
def match_info_cleaning_1() -> pd.DataFrame:

    df = MATCH_INFO.copy()
    stats_df = PLAYER_STATS.copy()

    # Sacamos columna "Round"
    df = df.drop(columns="Round")

    # Obtenemos los goles que ha marcado cada equipo
    team_goals = (stats_df.groupby(["Match", "Team"], as_index=False)["Goals"].sum())

    # A partir de aquí, aplicamos los goles si no se encuentran en nuestro dataframe
    mask_no_result = df[(df["HomeScore"].isna()) | (df["AwayScore"].isna())]
    for index, row in mask_no_result.iterrows():
        match_id = row["ID"]

        # Dataframe y goles por equipo
        home_df = team_goals[(team_goals["Match"] == match_id)&(team_goals["Team"] == row["HomeTeam"])]
        away_df = team_goals[(team_goals["Match"] == match_id)&(team_goals["Team"] == row["AwayTeam"])]
        home_score = home_df["Goals"].iloc[0] if not home_df.empty else np.nan
        away_score = away_df["Goals"].iloc[0] if not away_df.empty else np.nan

        # Asignar
        df.loc[index, "HomeScore"] = home_score
        df.loc[index, "AwayScore"] = away_score

    # Filtrado: si el partido no tiene los goles de algun equipo, lo sacamos
    df = df[(df["HomeScore"].notna()) & (df["AwayScore"].notna())]

    # Ordenamos por fecha nuestro dataframe
    df["Datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"], dayfirst=True, errors="coerce")
    df = df.sort_values("Datetime").reset_index(drop=True)
    df = df.drop(columns="Datetime")

    return df.sort_values(by=["Date","HomeTeam","AwayTeam"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE ESTADÍSTICAS DE EQUIPOS EN PARTIDOS
# --------------------------------------------------------------------------------------
def team_stats_cleaning_1() -> pd.DataFrame:

    df = TEAM_STATS.copy()
    match_info = MATCH_INFO.dropna(subset="IdSS").copy()
    player_stats = PLAYER_STATS.copy()

    # Comprovar que hay dos rows por partido
    df = df[df.groupby("Match")["Match"].transform("size") == 2].reset_index(drop=True)

    # Obtenemos los goles que ha marcado cada equipo y merge para tener los datos
    team_goals = (player_stats.groupby(["Match", "Team"], as_index=False)["Goals"].sum())
    df = df.merge(team_goals, on=["Match","Team"], how="left")

    # Borrado de columnas que no nos interesan
    df = df.drop(columns=["AverageAge", "FinalThirdPhaseStatistic", "KilometersCovered", "NumberOfSprints"])

    # Sacamos aquellas rows que no contienen posesión (faltaran más datos) y por formación
    df = df[df["BallPossession"].notna()]
    df = df[df["Formation"].notna()]

    return df.sort_values(by=["Match","Team"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE ESTADÍSTICAS DE JUGADORES EN PARTIDOS
# --------------------------------------------------------------------------------------
def player_stats_cleaning_1() -> pd.DataFrame:

    df = PLAYER_STATS.copy()
    team_stats = TEAM_STATS.copy()
    m_info_df = MATCH_INFO.dropna(subset="IdSS").copy()

    # Seleccionamos columnas de team stats para hacer merge con información posterior
    team_formations = team_stats[["Match", "Team", "Formation"]]

    # Drop de columnas que no nos interesan
    df = df.drop(columns=["ShotValue", "SecondYellowRedCards", "RescindedRedCards", "Rating", "KeeperSaveValue", "PassValue", "DribbleValue", "DefensiveValue", "GoalkeeperValue", "TotalBallCarriesDistance", "BallCarriesCount", "TotalProgression",
                          "BestBallCarryProgression", "TotalProgressiveBallCarriesDistance", "ProgressiveBallCarriesCount", "TopSpeed", "KilometersCovered", "NumberOfSprints", "MetersCoveredWalkingKm", "MetersCoveredJoggingKm", "MetersCoveredRunningKm", 
                          "MetersCoveredHighSpeedRunningKm", "MetersCoveredSprintingKm"])
    
    # Merge para tener la información de la formación
    df = df.merge(team_formations, on=["Match", "Team"], how="inner")

    # Para cada formación, añadimos posiciones
    for formation in df["Formation"].dropna().unique():
        mask = df["Formation"] == formation
        df.loc[mask, "Position"] = (df.loc[mask, "Position"].map(dict_formations[formation]))
    
    # Mapeo de formaciones (y movemos)
    df["Formation"] = df["Formation"].map(map_formations)
    col = df.pop("Formation")
    df.insert(5, "Formation", col)

    # Movemos minutos jugados y sacamos jugadores con no minutaje, o 0 minutos
    col = df.pop("MinutesPlayed")
    df.insert(6, "MinutesPlayed", col)
    df = df[~df["MinutesPlayed"].isna()]
    df = df[df["MinutesPlayed"]>0]

    # Añadimos fecha del partido
    m_info_df = m_info_df[m_info_df["Season"].astype(str)==str(ACT_SEASON)]             # Solo partidos temporada actual para seleccionar el equipo del jugador
    match_date_dict = dict(zip(m_info_df["ID"], m_info_df["Date"]))
    df.insert(1, "Date", df["Match"].map(match_date_dict))

    return df.sort_values(by=["Match","Team","Player"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# CLEANING BÁSICO DE INFORMACIÓN DE JUGADORES
# --------------------------------------------------------------------------------------
def player_cleaning_1(stats_clean_1: pd.DataFrame) -> pd.DataFrame:

    df = PLAYER_INFO.copy()
    stats_df = stats_clean_1.copy()

    # Creación de un diccionario con las posiciones en donde un jugador se ha alineado - las ordenamos por apariciones
    positions_players_df = stats_df[["Player", "Position"]].dropna()
    counts = (positions_players_df.groupby("Player")["Position"].value_counts())
    positions_dict = (counts.groupby(level=0).apply(lambda x: x.index.get_level_values(1).tolist()).to_dict())

    # Añadimos equipo del jugador a partir del último partido jugado en la temporada actual
    player_last_team_df_aux = stats_df.dropna(subset=["Date"]).copy()
    player_last_team_df = player_last_team_df_aux.loc[player_last_team_df_aux.groupby("Player")["Date"].idxmax()]
    player_last_team_dict = dict(zip(player_last_team_df["Player"], player_last_team_df["Team"]))
    player_last_number_dict = dict(zip(player_last_team_df["Player"], player_last_team_df["ShirtNumber"]))
    df["Team"] = df["ID"].map(player_last_team_dict)
    df["ShirtNumber"] = df["ID"].map(player_last_number_dict)

    # Creación de Main Pos
    df["MainPos"] = np.nan
    df["MainPos"] = df["MainPos"].astype(str)

    # Dividimos entre jugadores que tenemos estadísticas, y jugadores que no
    df_with_stats = df[df["ID"].isin(positions_dict.keys())]
    df_without_stats = df[~df["ID"].isin(positions_dict.keys())]

    # Para cada jugador (con estadísticas), vamos a añadir su posición primaria, secundaria y tericiaria - y posición principal
    for index, row in df_with_stats.iterrows():
        player_positions = positions_dict.get(row["ID"], [])

        # Elección de posiciones
        first_position = player_positions[0] if len(player_positions) > 0 else np.nan
        second_position = player_positions[1] if len(player_positions) > 1 else np.nan
        third_position = player_positions[2] if len(player_positions) > 2 else np.nan

        # Posición principal según la posición primaria
        if first_position in ["GK", "CB", "DM", "AM", "ST"]:
            main_position = first_position
        elif first_position in ["LB", "RB"]:
            main_position = "FB"
        elif first_position in ["LW", "RW"]:
            main_position = "WG"
        else:
            main_position = np.nan
        
        # Añadir al dataframe   
        df.loc[index, "FirstPos"] = first_position                     # Añadimos al índice del dataframe principal
        df.loc[index, "SecondPos"] = second_position
        df.loc[index, "ThirdPos"] = third_position
        df.loc[index, "MainPos"] = main_position

    # Diccionario para mapear posiciones
    map_pos = {'Attacking Midfielder': "AM", 'Center-Back': "CB", 'Central Midfielder': "DM", 'Defensive Midfielder': "DM", 'Goalkeeper': "GK", 'Left Full-Back': "LB", 'Left Wing-Midfielder': "LW", 
               'Left Winger': "LW", 'Right Full-Back': "RB", 'Right Wing-Midfielder': "RW", 'Right Winger': "RW", 'Striker': "ST", 'Attacker': "ST", 'Defender': "CB", 'Midfielder': "DM"}

    # Para cada jugador sin estadísticas, vamos a mirar sus posibles posiciones
    for index, row in df_without_stats.iterrows():

        # Mapeamos posiciones
        first_position = map_pos[row["FirstPos"]] if pd.notna(row["FirstPos"]) else np.nan
        second_position = map_pos[row["SecondPos"]] if pd.notna(row["SecondPos"]) else np.nan
        third_position = map_pos[row["ThirdPos"]] if pd.notna(row["ThirdPos"]) else np.nan

        # Posición principal según la posición primaria
        if first_position in ["GK", "CB", "DM", "AM", "ST"]:
            main_position = first_position
        elif first_position in ["LB", "RB"]:
            main_position = "FB"
        elif first_position in ["LW", "RW"]:
            main_position = "WG"
        else:
            main_position = np.nan

        # Añadir al dataframe   
        df.loc[index, "FirstPos"] = first_position                     # Añadimos al índice del dataframe principal
        df.loc[index, "SecondPos"] = second_position
        df.loc[index, "ThirdPos"] = third_position
        df.loc[index, "MainPos"] = main_position

    # # Sacamos aquellos jugadores que no tienen ninguna posición asignada
    df = df[~((df["MainPos"].isna())&(df["FirstPos"].isna())&(df["Position"].isna()))]

    # Para aquellas columnas que "FirstPos" sigue siendo nan, aplicamos el mapeado para obtener la primera posición a partir de position (si existe) - y generamos MainPos
    df["FirstPos"] = np.where(df["FirstPos"].isna(), np.where(df["Position"].isna(), np.nan, df["Position"].map(map_pos)), df["FirstPos"])
    df["MainPos"] = np.where(df["MainPos"].isna(), df["FirstPos"], df["MainPos"])

    # Tratado de aquellos jugadores que no encontramos el nombre
    mask = df["FirstName"].isna() & df["LastName"].isna()
    split_names = df.loc[mask, "Name"].str.split()
    df.loc[mask, "LastName"] = split_names.str[-1]
    df.loc[mask, "FirstName"] = split_names.str[:-1].str.join(" ")

    # Drop de columnas que no vamos a necesitar y reordenado
    df = df.drop(columns=["ShortName", "LongName", "ShortFirstName", "ShortLastName", "Position"])
    df = df.rename(columns={"MainPos":"Position"})

    return df.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# SEGUNDO CLEANING DE ESTADÍSTICAS DE JUGADORES POR PARTIDO
# --------------------------------------------------------------------------------------
def player_stats_cleaning_2(player_stats_df: pd.DataFrame, player_info_df: pd.DataFrame) -> pd.DataFrame:

    df = player_stats_df.copy()
    pl_info = player_info_df.copy()

    # Sacamos columna "Date"
    df = df.drop(columns=["Date"])

    # Diccionario con las posiciones disponibles por jugador
    player_pos_dict = (pl_info.set_index("ID")[["FirstPos", "SecondPos", "ThirdPos"]].apply(lambda x: [v for v in x if pd.notna(v)], axis=1).to_dict())

    # Máscara de aquellos jugadores sin posición asignada
    mask_no_position = df[df["Position"].isna()]
    for index, row in mask_no_position.iterrows():
        formation_posible_positions = dict_formations_positions[row["Formation"]]                   # Lista de posiciones por formación
        player_posible_positions = player_pos_dict.get(row["Player"], [])                           # Lista de posiciones donde puede jugar el jugador

        # Buscar primera coincidencia
        if len(player_posible_positions):
            opt_position = next((pos for pos in player_posible_positions if pos in formation_posible_positions), player_posible_positions[0] if player_posible_positions else np.nan)
            df.loc[index, "Position"] = opt_position

    # Drop de jugadores de los que no hemos encontrado posición
    df = df[~df["Position"].isna()]

    # Sacar columna de formación
    df = df.drop(columns=["Formation"])

    # Fillna de todas las estadísticas
    cols_exclude = ["Match", "Team", "Player", "ShirtNumber", "Position", "MinutesPlayed"]
    cols_to_fill = df.columns.difference(cols_exclude)
    df[cols_to_fill] = df[cols_to_fill].fillna(0)

    return df.sort_values(by=["Match","Team","Player"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# SEGUNDO CLEANING DE ESTADÍSTICAS DE EQUIPOS POR PARTIDO
# --------------------------------------------------------------------------------------
def team_stats_cleaning_2(team_stats_df: pd.DataFrame, player_stats_df: pd.DataFrame) -> pd.DataFrame:

    df = team_stats_df.copy()
    player_df = player_stats_df.copy()

    # Selección de columnas de estadísticas de jugadores que vamos a necesitar (drop)
    player_df = player_df.drop(columns=["Player", "ShirtNumber", "Position"])
    agg_dict = {col: "sum" for col in player_df.columns if col not in ["Match", "Team", "MinutesPlayed"]}
    agg_dict["MinutesPlayed"] = "max"      # Esto nos permite la duración real de los partidos (y partidos con proroga)
    agg_dict["GoalsConceded"] = "max"      # Ya que nos muestra los goles recibidos en cada jugador          
    player_df = player_df.groupby(["Match", "Team"], as_index=False).agg(agg_dict)

    # Merge de los datos de forma que obtenemos un dataframe con datos repetidos
    df = df.merge(player_df, how="inner", on=["Match", "Team"])

    # Buscamos aquellas columnas duplicadas, imposamos el MAXIMO
    cols_x = df.columns[df.columns.str.endswith("_x")]
    for col in cols_x:
        col_y = col.replace("_x", "_y")
        col_base = col.replace("_x", "")
        df[col_base] = np.maximum(df[col], df[col_y])
        df = df.drop(columns=[col, col_y])                      # De esta forma, hemos ampliado datos de partido de equipos con más estadísticas de jugadores

    # Fillna de todas las estadísticas
    cols_exclude = ["Match", "Team", "Manager", "Formation", "BallPossession"]
    cols_to_fill = df.columns.difference(cols_exclude)
    df[cols_to_fill] = df[cols_to_fill].fillna(0)

    return df.sort_values(by=["Match", "Team"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# EXTENSIÓN DEL DATAFRAME DE ESTADÍSTICAS AVANZADAS DE EQUIPOS
# --------------------------------------------------------------------------------------
def team_new_metrics(team_stats_df: pd.DataFrame, list_to_order: list) -> pd.DataFrame:

    df = team_stats_df.copy()

    # Factor x90
    factor_90 = 90 / df["MinutesPlayed"]

    # Eficiencia ofensiva
    df["ShotAccuracy"] = df_safe_div(df["ShotsOnTarget"], df["TotalShots"])
    df["GoalConversion"] = df_safe_div(df["Goals"], df["TotalShots"])
    df["BigChanceConversion"] = df_safe_div(df["BigChanceScored"], df["BigChanceCreated"])
    df["BigChanceMissRate"] = df_safe_div(df["BigChanceMissed"], df["BigChanceCreated"])
    df["ExpectedGoalsPerShot"] = df_safe_div(df["ExpectedGoals"], df["TotalShots"])
    df["ExpectedGoalsOnTargetPerShotOnTarget"] = df_safe_div(df["ExpectedGoalsOnTarget"], df["ShotsOnTarget"])
    df["GoalsMinusxG"] = df["Goals"] - df["ExpectedGoals"]      
    df["GoalsMinusxGOT"] = df["Goals"] - df["ExpectedGoalsOnTarget"]                         
    df["ShotsInsideBoxRate"] = df_safe_div(df["TotalShotsInsideBox"], df["TotalShots"])        
    df["ShotsOutsideBoxRate"] = df_safe_div(df["TotalShotsOutsideBox"], df["TotalShots"])      
    df["BlockedShotRate"] = df_safe_div(df["BlockedShots"], df["TotalShots"])                   
    df["ShotsOnTargetRate"] = df_safe_div(df["ShotsOnTarget"], df["TotalShots"])            
    df["ShotsOffTargetRate"] = df_safe_div(df["ShotsOffTarget"], df["TotalShots"])           
    df["BigChanceRate"] = df_safe_div(df["BigChanceCreated"], df["TotalShots"])                
    df["GoalsPerShotOnTarget"] = df_safe_div(df["Goals"], df["ShotsOnTarget"])                   
    df["HitWoodworkRate"] = df_safe_div(df["HitWoodwork"], df["TotalShots"])     

    # Creación
    df["FinalThirdEfficiency"] = df_safe_div(df["BigChanceCreated"], df["FinalThirdEntries"])   
    df["TouchesInOppBoxPerFinalThirdEntry"] = df_safe_div(df["TouchesInOppBox"], df["FinalThirdEntries"])
    df["KeyPassesPerFinalThirdEntry"] = df_safe_div(df["KeyPasses"], df["FinalThirdEntries"])
    df["KeyPassesPerShot"] = df_safe_div(df["KeyPasses"], df["TotalShots"]) 
    df["AssistConversion"] = df_safe_div(df["GoalAssists"], df["KeyPasses"])                     
    df["ExpectedAssistsPerKeyPass"] = df_safe_div(df["ExpectedAssists"], df["KeyPasses"])            
    df["ExpectedAssistsPerPass"] = df_safe_div(df["ExpectedAssists"], df["Passes"])                  
    df["CrossAccuracy"] = df_safe_div(df["AccurateCrosses"], df["Crosses"])                       
    df["CrossShare"] = df_safe_div(df["Crosses"], df["Passes"])                              
    df["AccurateCrossShare"] = df_safe_div(df["AccurateCrosses"], df["Passes"])                   
    df["ThroughBallAccuracy"] = df_safe_div(df["AccurateThroughBall"], df["Passes"])               
    df["BigChancesPerKeyPass"] = df_safe_div(df["BigChanceCreated"], df["KeyPasses"])               
    df["ShotsPerTouchInOppBox"] = df_safe_div(df["TotalShots"], df["TouchesInOppBox"])
    df["GoalsPerTouchInOppBox"] = df_safe_div(df["Goals"], df["TouchesInOppBox"])         

    # Posesión y pase
    df["PassAccuracy"] = df_safe_div(df["AccuratePasses"], df["Passes"])                        
    df["OwnHalfPassAccuracy"] = df_safe_div(df["AccurateOwnHalfPasses"], df["OwnHalfPasses"])        
    df["OppositionHalfPassAccuracy"] = df_safe_div(df["AccurateOppositionHalfPasses"], df["OppositionHalfPasses"]) 
    df["LongBallAccuracy"] = df_safe_div(df["AccurateLongBalls"], df["LongBalls"])                  
    df["OwnHalfPassShare"] = df_safe_div(df["OwnHalfPasses"], df["Passes"])                         
    df["OppositionHalfPassShare"] = df_safe_div(df["OppositionHalfPasses"], df["Passes"])          
    df["LongBallShare"] = df_safe_div(df["LongBalls"], df["Passes"])                               
    df["ProgressiveFieldTilt"] = df_safe_div(df["OppositionHalfPasses"], df["OppositionHalfPasses"] + df["OwnHalfPasses"])  
    df["PassesPerTouch"] = df_safe_div(df["Passes"], df["Touches"])                                
    df["TouchesPerPass"] = df_safe_div(df["Touches"], df["Passes"])                                
    df["PossessionLossRate"] = df_safe_div(df["PossessionLost"], df["Touches"])           
    df["UnsuccessfulTouchRate"] = df_safe_div(df["UnsuccessfulTouches"], df["Touches"])         
    df["DispossessedRate"] = df_safe_div(df["Dispossessed"], df["Touches"])                    
    df["BallPossessionPerPass"] = df_safe_div(df["BallPossession"], df["Passes"])             
    df["FinalThirdEntriesPerPass"] = df_safe_div(df["FinalThirdEntries"], df["Passes"])           
    df["FinalThirdEntriesPerTouch"] = df_safe_div(df["FinalThirdEntries"], df["Touches"])       

    # Defensa
    df["DefensiveActions"] = df["Tackles"] + df["Interceptions"] + df["Clearances"] + df["OutfielderBlocks"]  
    df["DefensiveActionSuccess"] = df_safe_div(df["TacklesWon"] + df["Interceptions"] + df["Clearances"], df["DefensiveActions"])  
    df["TackleAccuracy"] = df_safe_div(df["TacklesWon"], df["Tackles"])                        
    df["InterceptionShare"] = df_safe_div(df["Interceptions"], df["DefensiveActions"])           
    df["ClearanceShare"] = df_safe_div(df["Clearances"], df["DefensiveActions"])                  
    df["BlockShare"] = df_safe_div(df["OutfielderBlocks"], df["DefensiveActions"])             
    df["BallRecoveryRate"] = df_safe_div(df["BallRecoveries"], df["DefensiveActions"])           
    df["LastManTackleRate"] = df_safe_div(df["LastManTackles"], df["Tackles"])                   
    df["ClearanceOffLineRate"] = df_safe_div(df["ClearanceOffLine"], df["Clearances"])             
    df["ErrorsLeadToShotRate"] = df_safe_div(df["ErrorsLeadToShot"], df["DefensiveActions"])     
    df["ErrorsLeadToGoalRate"] = df_safe_div(df["ErrorsLeadToGoal"], df["DefensiveActions"])      
    df["GoalsConcededPerDefAction"] = df_safe_div(df["GoalsConceded"], df["DefensiveActions"])      

    # Duelos
    df["DuelWinRate"] = df_safe_div(df["DuelsWon"], df["DuelsWon"] + df["DuelsLost"])                
    df["AerialWinRate"] = df_safe_div(df["AerialWon"], df["AerialWon"] + df["AerialLost"])      
    df["ContestWinRate"] = df_safe_div(df["ContestsWon"], df["Contests"])                      
    df["ChallengesLostRate"] = df_safe_div(df["ChallengesLost"], df["Contests"])                

    # Portero
    df["SaveRate"] = df_safe_div(df["Saves"], df["Saves"] + df["GoalsConceded"])                   
    df["DiveSaveRate"] = df_safe_div(df["DiveSaves"], df["Saves"])                                  
    df["SavedShotsInsideBoxRate"] = df_safe_div(df["SavedShotsInsideBox"], df["Saves"])       
    df["CrossesNotClaimedRate"] = df_safe_div(df["CrossesNotClaimed"], df["CrossesNotClaimed"] + df["HighClaims"])  
    df["HighClaimRate"] = df_safe_div(df["HighClaims"], df["HighClaims"] + df["Punches"] + df["CrossesNotClaimed"]) 
    df["PunchRate"] = df_safe_div(df["Punches"], df["HighClaims"] + df["Punches"] + df["CrossesNotClaimed"])  
    df["KeeperSweeperAccuracy"] = df_safe_div(df["AccurateKeeperSweeperActions"], df["KeeperSweeperActions"])   
    df["PenaltySaveRate"] = df_safe_div(df["PenaltySaves"], df["PenaltyFaced"])                   
    df["PenaltyGoalConcededRate"] = df_safe_div(df["PenaltyGoalsConceded"], df["PenaltyFaced"])   
    df["GoalsPreventedDiff"] = df["GoalsPrevented"] - df["GoalsConceded"]                    

    # Disciplina
    df["CardsPerFoul"] = df_safe_div(df["YellowCards"] + df["RedCards"], df["Fouls"])
    df["YellowCardsPerFoul"] = df_safe_div(df["YellowCards"], df["Fouls"])           
    df["RedCardsPerFoul"] = df_safe_div(df["RedCards"], df["Fouls"])      
    df["FoulsPerDefAction"] = df_safe_div(df["Fouls"], df["DefensiveActions"])        
    df["WasFouledRate"] = df_safe_div(df["WasFouled"], df["Touches"])                           
    df["FouledFinalThirdRate"] = df_safe_div(df["FouledFinalThird"], df["FinalThirdEntries"])        
    df["OffsideRate"] = df_safe_div(df["Offsides"], df["TotalShots"])      

    # Balones parados
    df["CornersWonRate"] = df_safe_div(df["CornersWon"], df["TotalShots"])                   
    df["CornersLostRate"] = df_safe_div(df["CornersLost"], df["DefensiveActions"])              
    df["CornersTakenRate"] = df_safe_div(df["CornersTaken"], df["TotalShots"])                    
    df["FreeKicksRate"] = df_safe_div(df["FreeKicks"], df["Touches"])                               
    df["ThrowInsRate"] = df_safe_div(df["ThrowIns"], df["Touches"])                            
    df["GoalKicksRate"] = df_safe_div(df["GoalKicks"], df["Touches"])           

    # Penalitis
    df["PenaltyWonRate"] = df_safe_div(df["PenaltyWon"], df["TouchesInOppBox"])                    
    df["PenaltyMissRate"] = df_safe_div(df["PenaltyMissed"], df["PenaltyWon"])          
    df["PenaltyConcededRate"] = df_safe_div(df["PenaltyConceded"], df["DefensiveActions"])      

    # Diferencias
    df["GoalsMinusGoalsConceded"] = df["Goals"] - df["GoalsConceded"]                           
    df["ShotsMinusGoals"] = df["TotalShots"] - df["Goals"]                                      
    df["BigChanceDelta"] = df["BigChanceCreated"] - df["BigChanceMissed"]                   
    df["OwnGoalRate"] = df_safe_div(df["OwnGoals"], df["GoalsConceded"])                         

    # Métricas por 90
    # Fillna de todas las estadísticas
    cols_exclude = ["Match", "Team", "Manager", "Formation"]
    per90_cols = df.columns.difference(cols_exclude)
    per90_dict = {f"{col}Per90": df[col] * factor_90 for col in per90_cols}
    df = pd.concat([df, pd.DataFrame(per90_dict)], axis=1)

    # Aplicamos orden
    list_to_order = [col for col in list_to_order if col in df.columns]
    df = df[list_to_order].reset_index(drop=True)

    return df

# --------------------------------------------------------------------------------------
# EXTENSIÓN DEL DATAFRAME DE ESTADÍSTICAS AVANZADAS DE JUGADORES
# --------------------------------------------------------------------------------------
def player_new_metrics(player_stats_df: pd.DataFrame, list_to_order: list) -> pd.DataFrame:

    df = player_stats_df.copy()

    # Factor x90
    factor_90 = df_safe_div(90, df["MinutesPlayed"])

    # Pase y posesión
    df["PassAccuracy"] = df_safe_div(df["AccuratePasses"], df["Passes"])
    df["OwnHalfPassAccuracy"] = df_safe_div(df["AccurateOwnHalfPasses"], df["OwnHalfPasses"])        
    df["OppositionHalfPassAccuracy"] = df_safe_div(df["AccurateOppositionHalfPasses"], df["OppositionHalfPasses"]) 
    df["LongBallAccuracy"] = df_safe_div(df["AccurateLongBalls"], df["LongBalls"]) 
    df["OwnHalfPassShare"] = df_safe_div(df["OwnHalfPasses"], df["Passes"]) 
    df["OppositionHalfPassShare"] = df_safe_div(df["OppositionHalfPasses"], df["Passes"])            
    df["LongBallShare"] = df_safe_div(df["LongBalls"], df["Passes"])                                          
    df["ProgressiveFieldTilt"] = df_safe_div(df["OppositionHalfPasses"], df["OppositionHalfPasses"] + df["OwnHalfPasses"]) 
    df["PassesPerTouch"] = df_safe_div(df["Passes"], df["Touches"])                                
    df["TouchesPerPass"] = df_safe_div(df["Touches"], df["Passes"])                                     
    df["PossessionLossRate"] = df_safe_div(df["PossessionLost"], df["Touches"])                           
    df["UnsuccessfulTouchRate"] = df_safe_div(df["UnsuccessfulTouches"], df["Touches"])                   
    df["DispossessedRate"] = df_safe_div(df["Dispossessed"], df["Touches"])                               

    # Creación
    df["KeyPassesPerPass"] = df_safe_div(df["KeyPasses"], df["Passes"])                                   
    df["AssistConversion"] = df_safe_div(df["GoalAssists"], df["KeyPasses"])                             
    df["ExpectedAssistsPerKeyPass"] = df_safe_div(df["ExpectedAssists"], df["KeyPasses"])               
    df["ExpectedAssistsPerPass"] = df_safe_div(df["ExpectedAssists"], df["Passes"])               
    df["CrossAccuracy"] = df_safe_div(df["AccurateCrosses"], df["Crosses"])                                 
    df["CrossShare"] = df_safe_div(df["Crosses"], df["Passes"])                                              
    df["AccurateCrossShare"] = df_safe_div(df["AccurateCrosses"], df["Passes"])                  
    df["BigChancesPerKeyPass"] = df_safe_div(df["BigChancesCreated"], df["KeyPasses"])   
      
    # Finalización
    df["ShotAccuracy"] = df_safe_div(df["ShotsOnTarget"], df["TotalShots"])                                  
    df["GoalConversion"] = df_safe_div(df["Goals"], df["TotalShots"])                                 
    df["BigChanceMissRate"] = df_safe_div(df["BigChancesMissed"], df["BigChancesCreated"])                     
    df["ExpectedGoalsPerShot"] = df_safe_div(df["ExpectedGoals"], df["TotalShots"])                     
    df["ExpectedGoalsOnTargetPerShotOnTarget"] = df_safe_div(df["ExpectedGoalsOnTarget"], df["ShotsOnTarget"])
    df["GoalsMinusxG"] = df["Goals"] - df["ExpectedGoals"]                                               
    df["GoalsMinusxGOT"] = df["Goals"] - df["ExpectedGoalsOnTarget"]                               
    df["BlockedShotRate"] = df_safe_div(df["BlockedShots"], df["TotalShots"])                              
    df["ShotsOnTargetRate"] = df_safe_div(df["ShotsOnTarget"], df["TotalShots"])         
    df["ShotsOffTargetRate"] = df_safe_div(df["ShotsOffTarget"], df["TotalShots"])                     
    df["GoalsPerShotOnTarget"] = df_safe_div(df["Goals"], df["ShotsOnTarget"])                          
    df["HitWoodworkRate"] = df_safe_div(df["HitWoodwork"], df["TotalShots"])                       

    # Duelos
    df["DuelWinRate"] = df_safe_div(df["DuelsWon"], df["DuelsWon"] + df["DuelsLost"])                      
    df["AerialWinRate"] = df_safe_div(df["AerialWon"], df["AerialWon"] + df["AerialLost"])                
    df["ContestWinRate"] = df_safe_div(df["ContestsWon"], df["Contests"])                                 
    df["ChallengesLostRate"] = df_safe_div(df["ChallengesLost"], df["Contests"])                       

    # Defensa
    df["DefensiveActions"] = df["Tackles"] + df["Interceptions"] + df["Clearances"] + df["OutfielderBlocks"]
    df["DefensiveActionSuccess"] = df_safe_div(df["TacklesWon"] + df["Interceptions"] + df["Clearances"], df["DefensiveActions"])
    df["TackleAccuracy"] = df_safe_div(df["TacklesWon"], df["Tackles"])                                    
    df["InterceptionShare"] = df_safe_div(df["Interceptions"], df["DefensiveActions"])              
    df["ClearanceShare"] = df_safe_div(df["Clearances"], df["DefensiveActions"])                         
    df["BlockShare"] = df_safe_div(df["OutfielderBlocks"], df["DefensiveActions"])                  
    df["BallRecoveryRate"] = df_safe_div(df["BallRecoveries"], df["DefensiveActions"])                 
    df["LastManTackleRate"] = df_safe_div(df["LastManTackles"], df["Tackles"])                          
    df["ClearanceOffLineRate"] = df_safe_div(df["ClearanceOffLine"], df["Clearances"])                       
    df["ErrorsLeadToShotRate"] = df_safe_div(df["ErrorsLeadToShot"], df["DefensiveActions"])         
    df["ErrorsLeadToGoalRate"] = df_safe_div(df["ErrorsLeadToGoal"], df["DefensiveActions"])             
    df["GoalsConcededPerDefAction"] = df_safe_div(df["GoalsConceded"], df["DefensiveActions"])

    # Portero
    df["SaveRate"] = df_safe_div(df["Saves"], df["Saves"] + df["GoalsConceded"])          
    df["SavedShotsInsideBoxRate"] = df_safe_div(df["SavedShotsInsideBox"], df["Saves"])                    
    df["CrossesNotClaimedRate"] = df_safe_div(df["CrossesNotClaimed"], df["CrossesNotClaimed"] + df["HighClaims"])
    df["HighClaimRate"] = df_safe_div(df["HighClaims"], df["HighClaims"] + df["Punches"] + df["CrossesNotClaimed"]) 
    df["PunchRate"] = df_safe_div(df["Punches"], df["HighClaims"] + df["Punches"] + df["CrossesNotClaimed"])     
    df["KeeperSweeperAccuracy"] = df_safe_div(df["AccurateKeeperSweeperActions"], df["KeeperSweeperActions"])    
    df["PenaltySaveRate"] = df_safe_div(df["PenaltySaves"], df["PenaltyFaced"])              
    df["PenaltyGoalConcededRate"] = df_safe_div(df["PenaltyGoalsConceded"], df["PenaltyFaced"])     
    df["GoalsPreventedDiff"] = df["GoalsPrevented"] - df["GoalsConceded"]                         

    # Disciplina
    df["CardsPerFoul"] = df_safe_div(df["YellowCards"] + df["RedCards"], df["Fouls"])                        
    df["YellowCardsPerFoul"] = df_safe_div(df["YellowCards"], df["Fouls"])                                  
    df["RedCardsPerFoul"] = df_safe_div(df["RedCards"], df["Fouls"])                                       
    df["FoulsPerDefAction"] = df_safe_div(df["Fouls"], df["DefensiveActions"])                               
    df["WasFouledRate"] = df_safe_div(df["WasFouled"], df["Touches"])                                         
    df["OffsideRate"] = df_safe_div(df["Offsides"], df["TotalShots"])                                        

    # Balones parados
    df["CornersWonRate"] = df_safe_div(df["CornersWon"], df["Touches"])                                      
    df["CornersLostRate"] = df_safe_div(df["CornersLost"], df["DefensiveActions"])                          
    df["CornersTakenRate"] = df_safe_div(df["CornersTaken"], df["Touches"])                                  
    df["GoalKicksRate"] = df_safe_div(df["GoalKicks"], df["Touches"])                                         

    # Penalitis
    df["PenaltyWonRate"] = df_safe_div(df["PenaltyWon"], df["Touches"])                                      
    df["PenaltyMissRate"] = df_safe_div(df["PenaltyMissed"], df["PenaltyWon"])                              
    df["PenaltyConcededRate"] = df_safe_div(df["PenaltyConceded"], df["DefensiveActions"])                    
    # Diferencias
    df["GoalsMinusGoalsConceded"] = df["Goals"] - df["GoalsConceded"]                                    
    df["ShotsMinusGoals"] = df["TotalShots"] - df["Goals"]                                                 
    df["OwnGoalRate"] = df_safe_div(df["OwnGoals"], df["GoalsConceded"])                                 
    
    # Métricas por 90
    cols_exclude = ["Match", "Team", "Player", "ShirtNumber", "Position"]
    per90_cols = df.columns.difference(cols_exclude)
    per90_dict = {f"{col}Per90": df[col] * factor_90 for col in per90_cols}
    df = pd.concat([df, pd.DataFrame(per90_dict)], axis=1)

    # Aplicamos orden
    cols_existing = ["Match", "Team"] + [c for c in list_to_order if c in df.columns and c not in ["Match", "Team"]]
    df = df[cols_existing].reset_index(drop=True)

    return df

# --------------------------------------------------------------------------------------
# OBTIENE EL DICCIONARIO CON VARIACIONES DE JUGADORES
# --------------------------------------------------------------------------------------
def player_names_variations(player_df: pd.DataFrame) -> dict:

    # Lista para apendar datos
    dict_player_variations = {}

    for _, row in player_df[["ID", "other"]].iterrows():
        main_id = row["ID"]
        other_ids = row["other"]

        # El principal se apunta a sí mismo
        dict_player_variations[main_id] = main_id

        # Si other es lista y tiene valores
        if isinstance(other_ids, list) and len(other_ids) > 0:
            for alt_id in other_ids:
                dict_player_variations[alt_id] = main_id

    return dict_player_variations

# --------------------------------------------------------------------------------------
# LIMPIEZA DE JUGADORES - A partir de los datos de los jugadores en sus partidos, obtenemos su equipo
# --------------------------------------------------------------------------------------
def players_team(stats_player_df: pd.DataFrame, match_df: pd.DataFrame, player_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:

    stats_player = stats_player_df.copy()
    match = match_df.copy()
    player = player_df.copy()

    # 1. Obtener último equipo conocido por jugador
    stats_player = stats_player[["Match", "Team", "Player"]].copy()

    # Diccionario
    match_date_dict = dict(zip(match["ID"], match["Date"]))
    match_season_dict = dict(zip(match["ID"], match["Season"]))
    stats_player["Date"] = stats_player["Match"].map(match_date_dict)
    stats_player["Season"] = stats_player["Match"].map(match_season_dict)

    # Solo jugadores de la temporada actual
    stats_player = stats_player[stats_player["Season"].astype(str) == ACT_SEASON].copy()

    stats_player["Date"] = pd.to_datetime(stats_player["Date"], errors="coerce")
    stats_player = stats_player.dropna(subset=["Date", "Player", "Team"])

    stats_player_last = (stats_player.sort_values(["Player", "Date"], ascending=[True, True]).drop_duplicates(subset="Player", keep="last").reset_index(drop=True))
    player_last_team_dict = dict(zip(stats_player_last["Player"], stats_player_last["Team"]))
    player["Team"] = player["ID"].map(player_last_team_dict).fillna(player["Team"])

    # 2. Crear claves de duplicado
    def clean_text(x):
        if pd.isna(x):
            return ""
        return str(x).strip().lower()

    # Generar claves
    player["_slug_key"] = (player["Slug"].apply(clean_text) + "|" + player["Team"].apply(clean_text) + "|" + player["Country"].apply(clean_text))
    player["_matchname_key"] = (player["MatchName"].apply(clean_text) + "|" + player["Team"].apply(clean_text) + "|" + player["Country"].apply(clean_text))

    # Priorizamos MatchName + Team + Country porque detecta casos como:
    player["_dup_key"] = player["_matchname_key"]
    mask_empty_matchname = (player["MatchName"].isna() | (player["MatchName"].astype(str).str.strip() == ""))
    player.loc[mask_empty_matchname, "_dup_key"] = player.loc[mask_empty_matchname, "_slug_key"]

    # 3. Prioridades para elegir la mejor fila
    player["_row_order"] = range(len(player))
    player["_has_contract"] = player["ContractUntil"].notna().astype(int)
    player["_has_shirt"] = player["ShirtNumber"].notna().astype(int)
    player["_info_count"] = player.notna().sum(axis=1)

    player_sorted = player.sort_values(by=["_dup_key", "_has_contract", "_has_shirt", "_info_count", "_row_order"],
                                       ascending=[True, False, False, False, True])

    # 4. Fila ganadora por grupo
    player_best = (player_sorted.drop_duplicates(subset="_dup_key", keep="first").copy())

    # IDs duplicados restantes -> columna other
    other_ids = (player_sorted.groupby("_dup_key")["ID"].apply(list).reset_index(name="_all_ids"))
    player_best = player_best.merge(other_ids, on="_dup_key", how="left")
    player_best["other"] = player_best.apply(lambda row: [x for x in row["_all_ids"] if x != row["ID"]], axis=1)

    # 5. Crear diccionario de variaciones de IDs
    dict_player_names = player_names_variations(player_df=player_best)

    # 6. Limpieza player_unif
    player_unif = (player_best.drop(columns=["_slug_key", "_matchname_key", "_dup_key", "_row_order", "_has_contract", "_has_shirt", "_info_count", "_all_ids", "other"]).reset_index(drop=True))

    # 7. Reasignar IDs duplicados en stats_player_df
    stats_player_df = stats_player_df.copy()
    stats_player_df["Player"] = (stats_player_df["Player"].map(dict_player_names).fillna(stats_player_df["Player"]))

    return player_unif, stats_player_df

# --------------------------------------------------------------------------------------
# APLICADO DEL ELO RATING - Aplicamos el algoritmo del estudio para obtener la valoración de cada equipo según el calendario
# --------------------------------------------------------------------------------------
def apply_elo_ranking(match_df: pd.DataFrame, team_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:

    matches_data = match_df.copy()

    # Añadimos el factor K por competición
    tournament_k = {"la_liga": 40, "premier_league": 40, "bundesliga": 40, "serie_a": 40, "ligue_1": 40, "champions_league": 50, "europa_league": 30, "copa_del_rey": 30, "la_liga_hypermotion": 20,
                    "championship": 20, "eredivise": 30, "liga_portugal": 30, "conference_league": 30, "copa_libertadores": 20, "liga_mx": 20, "serie_a_brazil": 20, "liga_profesional": 20,
                    "first_division_a": 20, "major_league_soccer": 20, "saudi_pro_league": 20, "super_lig": 20, "superligaen": 20, "swiss_super_league": 20, "allvenskan": 20, "eliteserien": 20,
                    "conmebol_sudamericana": 20}
    matches_data["TournamentWeight"] = matches_data["League"].map(tournament_k)
    matches_data["TournamentWeight"] = np.where(matches_data["TournamentWeight"].isna(), 20, matches_data["TournamentWeight"])

    # Convertios fecha
    try:
        matches_data["Date"] = pd.to_datetime(matches_data["Date"], format="%d/%m/%Y")
    except:
        matches_data["Date"] = pd.to_datetime(matches_data["Date"], format="mixed", dayfirst=True)
    matches_data = matches_data.sort_values(by=["Date", "ID"]).reset_index(drop=True)

    # Aplicamos a los equipos según su país
    team_elo_df = team_df.copy()
    team_elo_df["EloRating"] = team_elo_df["Country"].map(dict_elo_country)
    team_elo_df["EloRating"] = np.where(team_elo_df["EloRating"].isna(), 1000, team_elo_df["EloRating"])
    team_elo_dict = dict(zip(team_elo_df["ID"], team_elo_df["EloRating"]))

    # Añadimos home elo y away elo al dataframe
    matches_data["HomeElo"] = None
    matches_data["AwayElo"] = None

    # Para cada partido según nuestro orden, vamos a calcular el ELO de los dos equipos
    for index, row in matches_data.iterrows():

        # Información que necesitaremos
        home_team = row["HomeTeam"]
        away_team = row["AwayTeam"]
        home_elo = team_elo_dict[home_team]
        away_elo = team_elo_dict[away_team]
        home_score = row["HomeScore"]
        away_score = row["AwayScore"]
        k = row["TournamentWeight"]

        # Calculamos la diferencia de goles para K - Home
        home_diff_goals = home_score - away_score
        if home_diff_goals <= 1:
            home_k = k
        elif home_diff_goals == 2:
            home_k = 1.5*k
        elif home_diff_goals == 3:
            home_k = 1.75*k
        else:
            home_k = k*(1.75 + (home_diff_goals - 3)/8)

        # Calculamos la diferencia de goles para K - Away
        away_diff_goals = away_score - home_score
        if away_diff_goals <= 1:
            away_k = k
        elif away_diff_goals == 2:
            away_k = 1.5*k
        elif away_diff_goals == 3:
            away_k = 1.75*k
        else:
            away_k = k*(1.75 + (away_diff_goals - 3)/8)

        # Resultado del partido
        home_w = 1 if home_score > away_score else 0.5 if home_score == away_score else 0
        away_w = 1 if home_score < away_score else 0.5 if home_score == away_score else 0

        # Diferencia de Elo por equipo
        home_dr = (home_elo - away_elo) + 100  
        away_dr = (away_elo - home_elo)

        # Resultado esperado por equipo
        home_we = 1 / (1 + 10**(-home_dr/400))
        away_we = 1 / (1 + 10**(-away_dr/400))

        # Nuevos Elo
        home_new_elo = home_elo + home_k * (home_w - home_we)
        away_new_elo = away_elo + away_k * (away_w - away_we)

        # Añadimos al diccionario
        team_elo_dict[home_team] = home_new_elo
        team_elo_dict[away_team] = away_new_elo

        # Añadimos al dataframe
        matches_data.at[index, "HomeElo"] = home_new_elo
        matches_data.at[index, "AwayElo"] = away_new_elo

    # Aplicamos al dataframe
    team_df_copy = team_df.copy()
    team_df_copy.insert(8, "EloRating", team_df_copy["ID"].map(team_elo_dict))

    # Sacamos tournament weight del partido
    matches_data = matches_data.drop(columns="TournamentWeight")

    return matches_data, team_df_copy

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE LINMPIEZA
# --------------------------------------------------------------------------------------
def main_cleaning(print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    start_time = time.time()

    if print_info:
        print("Starting the cleaning process number 1")

    # Carpeta 1 de datos procesados
    cleaning_1_path = os.path.join(SILVER_DATA_PATH, "cleaning_1")
    os.makedirs(cleaning_1_path, exist_ok=True)

    # Entrenadores
    manager_1_path = os.path.join(cleaning_1_path, "manager_clean_1.csv")
    if os.path.exists(manager_1_path) and not need_to_upload(manager_1_path, total_days=10):
        manager_clean_1 = pd.read_csv(manager_1_path, sep=";")
    else:
        manager_clean_1 = manager_cleaning_1()
        manager_clean_1.to_csv(manager_1_path, sep=";", index=False)

    # Equipos
    team_1_path = os.path.join(cleaning_1_path, "team_clean_1.csv")
    if os.path.exists(team_1_path) and not need_to_upload(team_1_path, total_days=10):
        team_clean_1 = pd.read_csv(team_1_path, sep=";")
    else:
        team_clean_1 = team_cleaning_1(team_manager_dict=dict(zip(manager_clean_1["Team"], manager_clean_1["ID"])))
        team_clean_1.to_csv(team_1_path, sep=";", index=False)

    # Partidos (info)
    match_1_path = os.path.join(cleaning_1_path, "match_clean_1.csv")
    if os.path.exists(match_1_path) and not need_to_upload(match_1_path, total_days=10):
        match_clean_1 = pd.read_csv(match_1_path, sep=";")
    else:
        match_clean_1 = match_info_cleaning_1()
        match_clean_1.to_csv(match_1_path, sep=";", index=False)

    # Estadísticas de equipo
    team_stats_1_path = os.path.join(cleaning_1_path, "team_stats_clean_1.csv")
    if os.path.exists(team_stats_1_path) and not need_to_upload(team_stats_1_path, total_days=10):
        team_stats_clean_1 = pd.read_csv(team_stats_1_path, sep=";")
    else:
        team_stats_clean_1 = team_stats_cleaning_1()
        team_stats_clean_1.to_csv(team_stats_1_path, sep=";", index=False)

    # Estadísticas de jugador
    player_stats_1_path = os.path.join(cleaning_1_path, "player_stats_clean_1.csv")
    if os.path.exists(player_stats_1_path) and not need_to_upload(player_stats_1_path, total_days=10):
        player_stats_clean_1 = pd.read_csv(player_stats_1_path, sep=";")
    else:
        player_stats_clean_1 = player_stats_cleaning_1()
        player_stats_clean_1.to_csv(player_stats_1_path, sep=";", index=False)

    # Jugadores
    player_1_path = os.path.join(cleaning_1_path, "player_clean_1.csv")
    if os.path.exists(player_1_path) and not need_to_upload(player_1_path, total_days=10):
        player_clean_1 = pd.read_csv(player_1_path, sep=";")
    else:
        player_clean_1 = player_cleaning_1(stats_clean_1=player_stats_clean_1)
        player_clean_1.to_csv(player_1_path, sep=";", index=False)

    if print_info:
        print("Starting the cleaning process number 2")

    # Carpeta 2 de datos procesados
    cleaning_2_path = os.path.join(SILVER_DATA_PATH, "cleaning_2")
    os.makedirs(cleaning_2_path, exist_ok=True)

    # Limpieza de estadísticas 2
    player_stats_2_path = os.path.join(cleaning_2_path, "player_stats_clean_2.csv")
    if os.path.exists(player_stats_2_path) and not need_to_upload(player_stats_2_path, total_days=10):
        player_stats_clean_2 = pd.read_csv(player_stats_2_path, sep=";")
        player_clean_2 = pd.read_csv(os.path.join(cleaning_2_path, "player_clean_2.csv"), sep=";")
    else:
        player_stats_clean_2 = player_stats_cleaning_2(player_stats_df=player_stats_clean_1.copy(), player_info_df=player_clean_1.copy())
        player_stats_clean_2 = player_new_metrics(player_stats_df=player_stats_clean_2.copy(), list_to_order=player_stats_order)

        # Comprovamos que en los nombres de jugadores no haya duplicados
        player_clean_2, player_stats_clean_2 = players_team(stats_player_df=player_stats_clean_2.copy(), match_df=match_clean_1.copy(), player_df=player_clean_1.copy())

        # Guardado
        player_stats_clean_2.to_csv(player_stats_2_path, sep=";", index=False)
        player_clean_2.to_csv(os.path.join(cleaning_2_path, "player_clean_2.csv"), sep=";", index=False)

    # Estadísticas de equipos 2
    team_stats_2_path = os.path.join(cleaning_2_path, "team_stats_clean_2.csv")
    if os.path.exists(team_stats_2_path) and not need_to_upload(team_stats_2_path, total_days=10):
        team_stats_clean_2 = pd.read_csv(team_stats_2_path, sep=";")
    else:
        team_stats_clean_2 = team_stats_cleaning_2(player_stats_df=player_stats_clean_2.copy(), team_stats_df=team_stats_clean_1.copy())
        team_stats_clean_2 = team_new_metrics(team_stats_df=team_stats_clean_2.copy(), list_to_order=team_stats_order)

        # Guardado
        team_stats_clean_2.to_csv(team_stats_2_path, sep=";", index=False)

    # APLICAMOS ELO
    match_2_path = os.path.join(cleaning_2_path, "match_clean_2.csv")
    team_2_path = os.path.join(cleaning_2_path, "team_clean_2.csv")
    if all(os.path.exists(p) for p in [match_2_path, team_2_path]) and not any(need_to_upload(p, total_days=10) for p in [match_2_path, team_2_path]):
        match_clean_2 = pd.read_csv(match_2_path, sep=";")
        team_clean_2  = pd.read_csv(team_2_path, sep=";")
    else:
        match_clean_2, team_clean_2 = apply_elo_ranking(match_df=match_clean_1.copy(), team_df=team_clean_1.copy())
        match_clean_2.to_csv(match_2_path, sep=";", index=False)
        team_clean_2.to_csv(team_2_path, sep=";", index=False)

    if print_info:
            print(f"First silver data cleaning finished in {elapsed_time_str(start_time=start_time)}.")

    return team_clean_2, player_clean_2, manager_clean_1, match_clean_2, player_stats_clean_2, team_stats_clean_2