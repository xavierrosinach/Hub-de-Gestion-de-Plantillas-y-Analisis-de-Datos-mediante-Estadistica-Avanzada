import os
import pandas as pd
import numpy as np
from typing import Tuple

from use.config import DATA_PATH, UTILS_DIR
from use.functions import json_to_dict, need_to_upload

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
EVENTING_PATH = os.path.join(RAW_DATA_PATH, "eventing")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")

# Medidas de campo
FIELD_LENGTH = 105
FIELD_WIDTH = 68

# Lectura de los CSV de mapeo de Opta
silver_proc_utils_path = os.path.join(UTILS_DIR, "proc", "silver_proc")
event_types = pd.read_csv(os.path.join(silver_proc_utils_path, "opta_event_types.csv"), sep=",")
qualifier_types = pd.read_csv(os.path.join(silver_proc_utils_path, "opta_qualifier_types.csv"), sep=",")

# Creamos diccionarios para el mapeo
event_types_dict = dict(zip(event_types["eventTypeId"], event_types["eventTypeName"]))
event_types_dict = {k: v for k, v in event_types_dict.items() if pd.notna(k)}
qualifier_types_dict = dict(zip(qualifier_types["qualifierTypeId"], qualifier_types["qualifierTypeName"]))
qualifier_types_dict = {k: v for k, v in qualifier_types_dict.items() if pd.notna(k)}

# --------------------------------------------------------------------------------------
# CREACIÓN DEL MAPA DE PASES A PARTIR DE LOS DATOS DE EVENTING
# --------------------------------------------------------------------------------------
def pass_map_creator(eventing_df: pd.DataFrame, team_ids_dict: dict, player_ids_dict: dict) -> pd.DataFrame:

    # Selección de los pases
    pass_df = eventing_df[eventing_df["Type"] == "Pass"]
    pass_df = pass_df.dropna(axis=1, how='all')
    pass_df = pass_df.dropna(subset="next_player")

    # Aplicamos diccionario para obtener jugadores y equipos
    pass_df["team"] = pass_df["team"].map(team_ids_dict)
    pass_df["player"] = pass_df["player"].map(player_ids_dict)
    pass_df["next_player"] = pass_df["next_player"].map(player_ids_dict)

    # Seleccionamos datos que nos interesan y nombres columnas
    pass_df = pass_df[["team", "player", "next_player", "outcome", "x", "y", "Pass End X", "Pass End Y", "Angle", "Length", "Zone"]]
    pass_df = pass_df.rename(columns={"team":"Team", "player":"Player", "next_player":"PassReceiver", "outcome":"AccuratePass", "x":"IniX", "y":"IniY",
                                    "Pass End X":"EndX", "Pass End Y":"EndY", "Angle":"Angle", "Length":"Length", "Zone":"Zone"})

    # Sacamos recividor si el passe no es acurado
    pass_df["PassReceiver"] = np.where(pass_df["AccuratePass"]==0, np.nan, pass_df["PassReceiver"])

    # Columnas de coordneadas
    num_cols = ["IniX", "IniY", "EndX", "EndY", "Angle", "Length"]
    pass_df[num_cols] = pass_df[num_cols].apply(pd.to_numeric, errors="coerce")

    # Aplicamos direccionado del pase
    dx = pass_df["EndX"] - pass_df["IniX"]
    dy = pass_df["EndY"] - pass_df["IniY"]
    conditions = [(dx > 5) & (dy > 5), (dx > 5) & (dy < -5), (dx > 5) & (dy.abs() <= 5), (dx.abs() <= 5) & (dy > 5), (dx.abs() <= 5) & (dy < -5), (dx < -5) & (dy > 5), (dx < -5) & (dy < -5), (dx < -5) & (dy.abs() <= 5)]
    choices = ["Forward Right", "Forward Left", "Forward", "Right", "Left", "Backward Right", "Backward Left", "Backward"]
    pass_df["PassDirection"] = np.select(conditions, choices, default="no clear direction")

    # Aplicamos un nuevo calculo de longitud de pase (en metros a nuestra escala)
    pass_df["Length"] = round(np.sqrt((FIELD_LENGTH * (pass_df["EndX"] - pass_df["IniX"]) / 100)**2 + (FIELD_WIDTH * (pass_df["EndY"] - pass_df["IniY"]) / 100)**2), 2)

    return pass_df

# --------------------------------------------------------------------------------------
# CREACIÓN DEL MAPA DE TIROS A PARTIR DE LOS DATOS DE EVENTING
# --------------------------------------------------------------------------------------
def shot_map_creator(eventing_df: pd.DataFrame, team_ids_dict: dict, player_ids_dict: dict) -> pd.DataFrame:

    # Seleccionamos datos
    shot_df = eventing_df[eventing_df["Type"].isin(["Saved Shot", "Goal", "Miss", "Post"])]
    shot_df = shot_df.dropna(axis=1, how='all')

    # Aplicamos diccionario para obtener jugadores y equipos
    shot_df["team"] = shot_df["team"].map(team_ids_dict)
    shot_df["player"] = shot_df["player"].map(player_ids_dict)

    # Seleccionamos datos que nos interesan y nombres columnas
    shot_df = shot_df[["team", "player", "Type", "x", "y", "Blocked X Coordinate", "Blocked Y Coordinate", "Goal Mouth Y Coordinate", "Goal Mouth Z Coordinate", "Zone"]]
    shot_df = shot_df.rename(columns={"team":"Team", "player":"Player", "x":"IniX", "y":"IniY", "Type": "Type", "Blocked X Coordinate":"BlockX", "Blocked Y Coordinate":"BlockY", 
                                    "Goal Mouth Y Coordinate":"GoalY", "Goal Mouth Z Coordinate":"GoalZ", "Zone":"Zone"})
    
    # Convertir coordenadas a numérico
    num_cols = ["IniX", "IniY", "BlockX", "BlockY", "GoalY", "GoalZ"]
    shot_df[num_cols] = shot_df[num_cols].apply(pd.to_numeric, errors="coerce")

    # Añadimos longitud
    goal_y = shot_df["GoalY"].fillna(50)
    shot_df["Length"] = round(np.sqrt((FIELD_LENGTH * (100 - shot_df["IniX"]) / 100)**2 + (FIELD_WIDTH * (goal_y - shot_df["IniY"]) / 100)**2), 2)

    return shot_df

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA PROCESAR LOS DATOS DE EVENTING Y EXTRAER MAPAS DE TIRO Y DE PASE
# --------------------------------------------------------------------------------------
def single_match_eventing_proc(match_dict: dict, match_id: int, team_ids_dict: dict, player_ids_dict: dict) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Para añadir datos
    eventing = []
    qualifiers = []

    # Buscamos datos
    match_live_data = match_dict.get("liveData")
    if match_live_data:

        # Obtenemos eventing
        match_eventing_data = match_live_data.get("event")
        if match_eventing_data:

            # Match eventing a añadir datos - vamos a concatenar
            for event in match_eventing_data:
                try: 
                    event_id = event.get("id", np.nan)
                    eventing.append({"eventId": event_id,
                                    "typeId": event.get("typeId", np.nan),
                                    "periodId": event.get("periodId", np.nan),
                                    "timeMin": event.get("timeMin", np.nan),
                                    "timeSec": event.get("timeSec", np.nan),
                                    "team": event.get("contestantId", np.nan),
                                    "player": event.get("playerId", np.nan),
                                    "outcome": event.get("outcome", np.nan),
                                    "x": event.get("x", np.nan),
                                    "y": event.get("y", np.nan)})
                
                    # Observamos qualifiers
                    qualifiers_data = event.get("qualifier")
                    if qualifiers_data:
                        for q in qualifiers_data:
                            qualifiers.append({"eventId": event_id,
                                            "qualifierId": q.get("qualifierId", np.nan),
                                            "value": q.get("value", np.nan)})
                except:
                    continue
                    
    # Transformamos a dataframe - eventing
    eventing_df = pd.DataFrame(eventing)
    eventing_df["Type"] = eventing_df["typeId"].map(event_types_dict)

    # Sacamos aquellos tipos que no son eventos futbolísticos
    non_stat_events = ['Start delay','End delay','End','Start','Team setp up','Player changed position','Player changed Jersey number','Collection End','Temp_Goal','Temp_Attempt',
                    'Formation change','Deleted event','Rescinded card','Condition change','Official change','Player Off','Player on','Player retired','Player returns',
                    'Player becomes goalkeeper','Goalkeeper becomes player','Contentious referee decision','Possession Data','Referee Drop Ball','Injury Time Announcement',
                    'Coach Setup','Delayed Start','Early end','Player Off Pitch','Resume']
    eventing_df = eventing_df[~eventing_df["Type"].isin(non_stat_events)]

    # Comprovamos que el dataframe contiene jugador y equipo
    eventing_df = eventing_df[(eventing_df["team"].notna())&(eventing_df["player"].notna())]

    # Qualifier
    qualifier_df = pd.DataFrame(qualifiers)
    qualifier_df["Type"] = qualifier_df["qualifierId"].map(qualifier_types_dict)

    # Nos quedamos solo con qualifiers válidos
    qualifier_clean = qualifier_df.dropna(subset=["Type"]).copy()

    # Pasamos qualifiers a formato ancho: una fila por evento, una columna por qualifier
    qualifier_wide = (qualifier_clean.pivot_table(index="eventId", columns="Type", values="value", aggfunc="first").reset_index())

    # Añadimos los qualifiers al dataframe de eventos
    eventing_df = eventing_df.merge(qualifier_wide, on="eventId", how="left")
    eventing_df["next_player"] = eventing_df["player"].shift(-1)                    # Siguiente jugador que realiza acción; por ejemplo, jugador que recibe el pase

    # Creamos el mapa de pases y de tiros
    try:
        pass_map_df = pass_map_creator(eventing_df=eventing_df.copy(), team_ids_dict=team_ids_dict, player_ids_dict=player_ids_dict)
        pass_map_df.insert(0, "Match", match_id)
    except:
        pass_map_df = None
    try:
        shot_map_df = shot_map_creator(eventing_df=eventing_df.copy(), team_ids_dict=team_ids_dict, player_ids_dict=player_ids_dict)
        shot_map_df.insert(0, "Match", match_id)
    except:
        shot_map_df = None
        
    return pass_map_df, shot_map_df 

# --------------------------------------------------------------------------------------
# FUNCIÓN MAIN DE LIMPIEZA DE EVENTING DATA
# --------------------------------------------------------------------------------------
def main_eventing_cleaning(team_df: pd.DataFrame, player_df: pd.DataFrame, match_df: pd.DataFrame, print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Selección de aquellos partidos que tienen IdSW
    matches_df = match_df.dropna(subset="IdSW")[["ID", "IdSW", "Season", "HomeTeam", "AwayTeam"]].copy()

    # Selección de aquellos partidos que se encuentren en EVENTING PATH
    matches_with_data = [match.split(".")[0] for match in os.listdir(EVENTING_PATH)]
    matches_df = matches_df[matches_df["IdSW"].isin(matches_with_data)]

    # Inserción del nombre de los equipos para identificar
    teams_dict = dict(zip(team_df["ID"], team_df["Abbreviation"]))
    matches_df["HomeTeam"] = matches_df["HomeTeam"].map(teams_dict)
    matches_df["AwayTeam"] = matches_df["AwayTeam"].map(teams_dict)

    # Diccionarios que vamos a usar para procesar la información y unificar datos
    team_ids_dict = dict(zip(team_df["IdSW"], team_df["ID"]))
    player_ids_dict = dict(zip(player_df["IdSW"], player_df["ID"]))
    matches_ids_dict = dict(zip(matches_df["IdSW"], matches_df["ID"]))

    # Obtenemos las estadísticas de partidos
    if print_info:
        print(f"        1. Matches eventing data processing.                                                                             ")
        i = 1
        total_matches = len(matches_ids_dict)

    # Miramos que no existan
    passes_path = os.path.join(BRONZE_DATA_PATH, "unified_data", "pass_map.csv")
    shots_path = os.path.join(BRONZE_DATA_PATH, "unified_data", "shots_map.csv")
    if (os.path.exists(passes_path) and not need_to_upload(passes_path, total_days=10)) or (os.path.exists(shots_path) and not need_to_upload(shots_path, total_days=10)):
        passes_df = pd.read_csv(passes_path, sep=";")
        shots_df = pd.read_csv(shots_path, sep=";")
        return passes_df, shots_df
    
    # Listas para concatenar
    list_passes = []
    list_shots = []

    for index, row in matches_df.iterrows():

        match_id = row["ID"]
        sw_id = row["IdSW"]

        # Procesado de partidos
        match_eventing_path = os.path.join(EVENTING_PATH, f"{sw_id}.json")
        if os.path.exists(match_eventing_path):
            if print_info:
                print(f"                 [{i}/{total_matches}] Processing match {match_id} ({round(i/total_matches * 100, 2)}%) - [{row['HomeTeam']} - {row['AwayTeam']} (season {row['Season']})]", flush=True, end="\r")
                i += 1

            # Procesado del partido
            match_dict = json_to_dict(json_path = match_eventing_path)
            if match_dict.get("liveData"):
                pass_map, shot_map = single_match_eventing_proc(match_dict=match_dict, match_id=match_id, team_ids_dict=team_ids_dict, player_ids_dict=player_ids_dict)
                if pass_map is not None:
                    list_passes.append(pass_map)
                if shot_map is not None:
                    list_shots.append(shot_map)

    # Concatenado
    passes_df = pd.concat(list_passes, ignore_index=True)
    shots_df = pd.concat(list_shots, ignore_index=True)

    # Guardado de información
    passes_df.to_csv(passes_path, sep=";", index=False)
    shots_df.to_csv(shots_path, sep=";", index=False)

    return passes_df, shots_df