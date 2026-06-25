import os
import pandas as pd
import numpy as np
import time
from typing import Tuple

from use.config import DATA_PATH, COMPS
from use.functions import json_to_dict, create_slug, need_to_upload, elapsed_time_str

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
os.makedirs(BRONZE_DATA_PATH, exist_ok=True)

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE MANAGERS - Scoresway
# --------------------------------------------------------------------------------------
def managers_cleaning(print_info: bool = True) -> pd.DataFrame:

    squads_paths = []

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "scoresway", "squads.json")
            if os.path.exists(season_path):
                squads_paths.append(season_path)
    
    # Lista para concatenar información
    managers_info = []
    managers_team_dict = {}

    if print_info:
        i = 1
        total_tourns = len(squads_paths)

    # Concatenamos entrenadores
    for file in squads_paths:

        if print_info:
            print(f"            [{i}/{total_tourns}] Processing managers from tournament number {i}", flush=True, end="\r")
            i += 1

        try:
            squad_data = json_to_dict(json_path=file).get("squad")
            if squad_data:
                for squad in squad_data:
                    squad_persons = squad.get("person")
                    if squad_persons:
                        for person in squad_persons:
                            if person.get("type") and person.get("type") != "player":
                                managers_info.append(person)
                                managers_team_dict[person.get("id")] = squad.get("contestantId")
        except:
            continue

    # Limpieza del dataframe
    man_df = pd.DataFrame(managers_info)
    man_df = man_df.drop(columns=[col for col in ["gender", "nationalityId", "placeOfBirth", "startDate", "active", "endDate", "secondNationalityId", "secondNationality", "knownName", "shirtNumber"] if col in man_df.columns])
    man_df = man_df.rename(columns={"id": "IdSW", "firstName": "FirstName", "lastName": "LastName", "shortFirstName": "ShortFirstName", "shortLastName": "ShortLastName", 
                                    "matchName": "MatchName", "nationality": "Country", "type": "Type"})
    man_df.insert(1, "Name", man_df["FirstName"] + " " + man_df["LastName"])
    man_df.insert(2, "ShortName", man_df["ShortFirstName"] + " " + man_df["ShortLastName"])
    man_df.insert(1, "Slug", man_df["ShortName"].apply(create_slug))
    man_df["Team"] = man_df["IdSW"].map(managers_team_dict)

    return man_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE EQUIPOS - Scoresway
# --------------------------------------------------------------------------------------
def teams_cleaning(print_info: bool = True) -> pd.DataFrame:

    squads_paths = []

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "scoresway", "squads.json")
            if os.path.exists(season_path):
                squads_paths.append(season_path)
    
    # Lista para concatenar información
    teams_info = []

    if print_info:
        i = 1
        total_tourns = len(squads_paths)

    # Concatenamos equipos
    for file in squads_paths:

        if print_info:
            print(f"            [{i}/{total_tourns}] Processing teams from tournament number {i}", flush=True, end="\r")
            i += 1

        try:
            squad_data = json_to_dict(json_path=file).get("squad")
            if squad_data:
                for squad in squad_data:
                    squad.pop("person", None)      # Sacamos los jugadores

                    # Información sobre las camisetas de los jugadores
                    kits_info = squad.get("teamKits", {}).get("kit")
                    kits = {"home_col_1": np.nan, "home_col_2": np.nan, "home_shorts": np.nan, 
                            "away_col_1": np.nan, "away_col_2": np.nan, "away_shorts": np.nan}
                    if kits_info:
                        for kit in kits_info:
                            if kit.get("type") == "Home":
                                kits["home_col_1"] = kit.get("shirtColour1", np.nan)
                                kits["home_col_2"] = kit.get("shirtColour2", np.nan)
                                kits["home_shorts"] = kit.get("shortsColour1", np.nan)
                            elif kit.get("type") == "Away":
                                kits["away_col_1"] = kit.get("shirtColour1", np.nan)
                                kits["away_col_2"] = kit.get("shirtColour2", np.nan)
                                kits["away_shorts"] = kit.get("shortsColour1", np.nan)

                    # Añadimos información
                    teams_info.append({'id': squad.get("contestantId", np.nan),
                                       'name': squad.get("contestantName", np.nan),
                                       "shortName": squad.get("contestantShortName", np.nan),
                                       "clubName": squad.get("contestantClubName", np.nan),
                                       "code": squad.get("contestantCode", np.nan),
                                       'homeKitCol1': kits["home_col_1"],
                                       'homeKitCol2': kits["home_col_2"],
                                       'homeShorts': kits["home_shorts"],
                                       'awayKitCol1': kits["away_col_1"],
                                       'awayKitCol2': kits["away_col_2"],
                                       'awayShorts': kits["away_shorts"]})
        except:
            continue    
            
    # Limpieza del dataframe
    teams_df = pd.DataFrame(teams_info)
    teams_df = teams_df.rename(columns={"id": "IdSW", "name": "LongName", "shortName": "ShortName", "clubName": "Name", "code": "Abbreviation", "homeKitCol1": "HomeKitCol1", 
                                        "homeKitCol2": "HomeKitCol2", "homeShorts": "HomeShortsCol", "awayKitCol1": "AwayKitCol1", "awayKitCol2": "AwayKitCol2", "awayShorts": "AwayShortsCol"})
    teams_df.insert(1, "Slug", teams_df["Name"].apply(create_slug))

    return teams_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE PARTIDOS - Scoresway
# --------------------------------------------------------------------------------------
def matches_cleaning(print_info: bool = True) -> pd.DataFrame:

    matches_paths = {}

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "scoresway", "matches.json")
            if os.path.exists(season_path):
                matches_paths[f"{league_slug}-{season_key}"] = season_path

    if print_info:
        i = 1
        total_tourns = len(matches_paths)

    # Miramos la información de cada partido
    all_matches_info = []
    for league_id, matches in matches_paths.items():

        if print_info:
            print(f"            [{i}/{total_tourns}] Processing matches from tournament number {i}", flush=True, end="\r")
            i += 1

        try:
            if os.path.exists(matches):
                matches_dict = json_to_dict(json_path=matches).get("match")
                if matches_dict:
                    for match in matches_dict:
                        match_info = match.get("matchInfo")
                        if match_info:
                            all_matches_info.append({"match_id": match_info.get("id", np.nan), 
                                                    "league": league_id.split('-')[0],
                                                    "season": league_id.split('-')[1],
                                                    "date": match_info.get("date", np.nan), 
                                                    "time": match_info.get("time", np.nan),
                                                    "homeTeam": match_info.get("contestant", [])[0].get("id", np.nan),
                                                    "awayTeam": match_info.get("contestant", [])[1].get("id", np.nan)})
        except:
            continue

    # Transformación del dataframe
    matches_df = pd.DataFrame(all_matches_info)
    matches_df = matches_df.rename(columns = {"match_id":"IdSW", "league":"League", "season":"Season", "date":"Date_", 
                                              "time":"Time_", "homeTeam":"HomeTeam", "awayTeam":"AwayTeam"})

    # Tratado de las horas null
    matches_df["Time_"] = matches_df["Time_"].fillna("00:00:00Z")
    matches_df["Time_"] = matches_df["Time_"].replace("", "00:00:00Z")

    # Datetime y orden
    matches_df["Datetime"] = pd.to_datetime(matches_df["Date_"].str.replace("Z", "", regex=False) + " " + matches_df["Time_"].str.replace("Z", "", regex=False), utc=True)
    matches_df = matches_df[matches_df["Datetime"] <= pd.Timestamp.now(tz="Europe/Madrid")]         # Filtrado de fechas para no tener partidos futuros
    matches_df = matches_df.sort_values(by=["League", "Season", "Datetime"])
    matches_df["Date"] = matches_df["Datetime"].dt.strftime("%d/%m/%Y")
    matches_df["Time"] = matches_df["Datetime"].dt.strftime("%H:%M")
    matches_df = matches_df.drop(columns=["Datetime", "Date_", "Time_"])

    return matches_df.drop_duplicates()

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE JUGADORES - Scoresway
# --------------------------------------------------------------------------------------
def players_cleaning(print_info: bool = True) -> pd.DataFrame:

    squads_paths = {}

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "scoresway", "squads.json")
            if os.path.exists(season_path):
                squads_paths[f"{league_slug}-{season_key}"] = season_path

    if print_info:
        i = 1
        total_tourns = len(squads_paths)

    # Lista para añadir los jugadores
    players_info = []

    # Concatenación de información
    for league_id, squad in squads_paths.items():

        if print_info:
            print(f"            [{i}/{total_tourns}] Processing players from tournament number {i}", flush=True, end="\r")
            i += 1

        try:
            squad_data = json_to_dict(json_path=squad).get('squad')
            season = league_id.split("-")[1]
            league_slug = league_id.split("-")[0]
            if squad_data:
                for squad in squad_data:
                    team_name = squad.get("contestantId")
                    squad_persons = squad.get("person")
                    if squad_persons:
                        for person in squad_persons:
                            if person.get("type") and person.get("type") == "player":
                                person["season"] = season
                                person["league"] = league_slug
                                person["team"] = team_name
                                players_info.append(person)
        except:
            continue

    # Limpieza del dataframe
    players_df = pd.DataFrame(players_info)
    players_df = players_df.drop(columns=[col for col in ["gender", "nationalityId", "placeOfBirth", "startDate", "active", "endDate", "secondNationalityId", "secondNationality", "knownName", "type"] if col in players_df.columns])
    players_df = players_df.rename(columns={"id": "IdSW", "firstName": "FirstName", "lastName": "LastName", "shortFirstName": "ShortFirstName", "shortLastName": "ShortLastName", "matchName": "MatchName",
                                            "nationality": "Country", "position": "Position", "season": "Season", "league": "League", "team": "Team", "shirtNumber": "ShirtNumber"})
    players_df.insert(1, "Name", players_df["FirstName"] + " " + players_df["LastName"])
    players_df.insert(2, "ShortName", players_df["ShortFirstName"] + " " + players_df["ShortLastName"])
    players_df.insert(1, "Slug", players_df["ShortName"].apply(create_slug))
    players_df["ShirtNumber"] = players_df["ShirtNumber"].astype("Int64")

    return players_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE ESTADÍSTICAS DE JUGADORES - en un partido
# --------------------------------------------------------------------------------------
def lineups_single_match(path_sw: str, match_id: str, home_team_id: str, away_team_id: str) -> Tuple[pd.DataFrame, float, float, str, str]:

    # Lectura del JSON en formato diccionario
    dict_data = json_to_dict(json_path=path_sw).get("liveData")

    list_data = []

    # Información extra que vamos a obtener
    home_avg_age = np.nan
    home_manager = np.nan
    away_avg_age = np.nan
    away_manager = np.nan

    if dict_data:
        
        lineups = dict_data.get("lineUp")
        if lineups is not None and len(lineups) > 1:

            home_lineup = lineups[0]
            away_lineup = lineups[1]

            # Alineación local
            if home_lineup:
                home_avg_age = home_lineup.get("averageAge", np.nan)
                home_officials = home_lineup.get("teamOfficial", [])
                if len(home_officials) > 0:
                    home_manager = home_officials[0].get("id", np.nan)
                    players = home_lineup.get("player")

                    for player in players:
                        player_dict = {"team": home_team_id,
                                    "player": player.get("playerId", np.nan),
                                    "shirt_num": player.get("shirtNumber", np.nan),
                                    "position": player.get("position", np.nan),
                                    "position_side": player.get("positionSide", np.nan)}
                        
                        # Estadísticas del jugador
                        player_statistics = player.get("stat")
                        if player_statistics:
                            for stat in player_statistics:
                                stat_name = stat.get("type")
                                if stat_name:
                                    if stat_name not in ["formationPlace", "formationUsed", "gameStarted", "totalSubOn", "totalSubOff"]:
                                        player_dict[stat_name] = stat.get("value", np.nan)

                        list_data.append(player_dict)
                else:
                    home_avg_age = np.nan
                    home_manager = np.nan

            # Alineación visitante
            if away_lineup:
                away_avg_age = away_lineup.get("averageAge", np.nan)
                away_officials = away_lineup.get("teamOfficial", [])
                if len(away_officials) > 0:
                    away_manager = away_officials[0].get("id", np.nan)
                    players = away_lineup.get("player")

                    for player in players:
                        player_dict = {"team": away_team_id,
                                    "player": player.get("playerId", np.nan),
                                    "shirt_num": player.get("shirtNumber", np.nan),
                                    "position": player.get("position", np.nan),
                                    "position_side": player.get("positionSide", np.nan)}
                        
                        # Estadísticas del jugador
                        player_statistics = player.get("stat")
                        if player_statistics:
                            for stat in player_statistics:
                                stat_name = stat.get("type")
                                if stat_name:
                                    if stat_name not in ["formationPlace", "formationUsed", "gameStarted", "totalSubOn", "totalSubOff"]:
                                        player_dict[stat_name] = stat.get("value", np.nan)

                        list_data.append(player_dict)
                
                else:
                    away_avg_age = np.nan
                    away_manager = np.nan
    
    
    # Transformación a dataframe
    df_lineups = pd.DataFrame(list_data)

    # Quitar los jugadores sin estadisticas
    cols_base = ["team", "player", "shirt_num", "position", "position_side"]
    cols_stats = [col for col in df_lineups.columns if col not in cols_base]
    df_lineups[cols_stats] = df_lineups[cols_stats].replace(0, np.nan)              # Valores nulos primero si hay 0
    df_lineups = df_lineups.dropna(subset=cols_stats, how="all")
    df_lineups = df_lineups.reset_index(drop=True)

    # Añadimos match ID y equipos
    df_lineups.insert(0, "Match", match_id)

    return df_lineups, home_avg_age, away_avg_age, home_manager, away_manager

# --------------------------------------------------------------------------------------
# OBTENCIÓN DE LAS ESTADÍSTICAS DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def lineups_cleaning(matches_df: pd.DataFrame, print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Listas y diccionarios para concatenar información
    all_matches_lineups = []
    home_avg_age_dict = {}
    away_avg_age_dict = {}
    home_manager_dict = {}
    away_manager_dict = {}

    if print_info:
        i = 1
        total_matches = len(matches_df)

    for index, row in matches_df.iterrows():

        if print_info:
            print(f"            [{i}/{total_matches}] Processing match {row['IdSW']}", flush=True, end="\r")
            i += 1

        match_path = os.path.join(RAW_DATA_PATH, "competitions", row["League"], str(row["Season"]), "scoresway", "matches", f"{row['IdSW']}.json")
        if os.path.exists(match_path):
            df_lineups, home_avg_age, away_avg_age, home_manager, away_manager = lineups_single_match(path_sw=match_path, match_id=row["IdSW"], home_team_id=row["HomeTeam"], away_team_id=row["AwayTeam"])
            all_matches_lineups.append(df_lineups)
            home_avg_age_dict[row["IdSW"]] = home_avg_age
            away_avg_age_dict[row["IdSW"]] = away_avg_age
            home_manager_dict[row["IdSW"]] = home_manager
            away_manager_dict[row["IdSW"]] = away_manager

    # Dataframe de alineaciones y añadimos valores a matches df
    lineups_df = pd.concat(all_matches_lineups, ignore_index=True)
    matches_df["HomeAvgAge"] = matches_df["IdSW"].map(home_avg_age_dict)
    matches_df["AwayAvgAge"] = matches_df["IdSW"].map(home_avg_age_dict)
    matches_df["HomeManager"] = matches_df["IdSW"].map(home_avg_age_dict)
    matches_df["AwayManager"] = matches_df["IdSW"].map(home_avg_age_dict)
    
    return matches_df, lineups_df

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE LIMPIEZA DE SCORESWAY
# --------------------------------------------------------------------------------------
def main_cleaning(print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    start_time = time.time()

    if print_info:
        print(f"Scoresway bronze data cleaning                                                                                         ")

    # Carpeta de scoresway cleaning
    sw_cleaned_path = os.path.join(BRONZE_DATA_PATH, "scoresway_cleaned_data")
    os.makedirs(sw_cleaned_path, exist_ok=True)

    # Procesado de entrenadores
    if print_info:
        print(f"        1. Managers Scoresway cleaning.                                                                             ")

    # Información de managers
    sw_manager_cleaned_path = os.path.join(sw_cleaned_path, "manager.csv")
    if not os.path.exists(sw_manager_cleaned_path) or need_to_upload(path=sw_manager_cleaned_path, total_days=10):
        managers_df = managers_cleaning(print_info=print_info)
        managers_df.drop_duplicates().to_csv(sw_manager_cleaned_path, index=False, sep=";")
    else:
        managers_df = pd.read_csv(sw_manager_cleaned_path, sep=";")

    if print_info:
        print(f"        2. Teams Scoresway cleaning.                                                                             ")

    # Información de equipos
    sw_team_cleaned_path = os.path.join(sw_cleaned_path, "team.csv")
    if not os.path.exists(sw_team_cleaned_path) or need_to_upload(path=sw_team_cleaned_path, total_days=10):
        teams_df = teams_cleaning(print_info=print_info)
        teams_df.drop_duplicates().to_csv(sw_team_cleaned_path, index=False, sep=";")
    else:
        teams_df = pd.read_csv(sw_team_cleaned_path, sep=";")

    if print_info:
            print(f"        3. Players Scoresway cleaning.                                                                             ")

    # Información de jugadores
    sw_player_cleaned_path = os.path.join(sw_cleaned_path, "player.csv")
    if not os.path.exists(sw_player_cleaned_path) or need_to_upload(path=sw_player_cleaned_path, total_days=10):
        players_df = players_cleaning(print_info=print_info)
        players_df.drop_duplicates().to_csv(sw_player_cleaned_path, index=False, sep=";")
    else:
        players_df = pd.read_csv(sw_player_cleaned_path, sep=";")

    if print_info:
        print(f"        4. Matches Scoresway cleaning.                                                                             ")

    # Información de partidos
    sw_matches_cleaned_path = os.path.join(sw_cleaned_path, "matches.csv")
    if not os.path.exists(sw_matches_cleaned_path) or need_to_upload(path=sw_matches_cleaned_path, total_days=10):
        matches_df = matches_cleaning(print_info=print_info)
        matches_df.drop_duplicates().to_csv(sw_matches_cleaned_path, index=False, sep=";")
    else:
        matches_df = pd.read_csv(sw_matches_cleaned_path, sep=";")

    if print_info:
        print(f"        5. Lineups Scoresway cleaning.                                                                             ")

    # Información de partidos
    sw_lineups_cleaned_path = os.path.join(sw_cleaned_path, "lineups.csv")
    if not os.path.exists(sw_lineups_cleaned_path) or need_to_upload(path=sw_lineups_cleaned_path, total_days=10):
        matches_df, lineups_df = lineups_cleaning(matches_df=matches_df, print_info=print_info)
        lineups_df.drop_duplicates().to_csv(sw_lineups_cleaned_path, index=False, sep=";")
        matches_df.drop_duplicates().to_csv(sw_matches_cleaned_path, index=False, sep=";")
    else:
        lineups_df = pd.read_csv(sw_lineups_cleaned_path, sep=";")

    if print_info:
        print(f"Scoresway data cleaning finished in {elapsed_time_str(start_time=start_time)}.")

    return players_df.drop_duplicates(), teams_df.drop_duplicates(), managers_df.drop_duplicates(), matches_df.drop_duplicates(), lineups_df.drop_duplicates()