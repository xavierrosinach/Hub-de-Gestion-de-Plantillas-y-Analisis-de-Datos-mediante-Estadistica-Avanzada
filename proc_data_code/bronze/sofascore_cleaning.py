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
# LIMPIEZA DE DATAFRAME DE MANAGERS
# --------------------------------------------------------------------------------------
def managers_cleaning(print_info: bool = True) -> pd.DataFrame:

    # Path de carpeta con datos de entrenadores
    managers_path = os.path.join(RAW_DATA_PATH, "entities", "manager")

    # Lista para concatenar información
    managers_info = []

    if print_info:
        i = 1
        total_managers = len(os.listdir(managers_path))

    # Para cada entrenador
    for manager in os.listdir(managers_path):

        if print_info:
            print(f"            [{i}/{total_managers}] Processing manager {manager.replace('.json', '')}", flush=True, end="\r")
            i += 1

        manager_data = json_to_dict(json_path=os.path.join(managers_path, manager)).get('manager')
        if manager_data:
            try:
                managers_info.append({"id": manager_data.get("id", np.nan), 
                                      "name": manager_data.get("name", np.nan), 
                                      "short_name": manager_data.get("shortName", np.nan),
                                      "country": manager_data.get("country", {}).get("name", np.nan), 
                                      "date_birth": manager_data.get("dateOfBirthTimestamp", np.nan),
                                      "matches": manager_data.get("performance", {}).get("total", np.nan), 
                                      "wins": manager_data.get("performance", {}).get("wins", np.nan),
                                      "draws": manager_data.get("performance", {}).get("draws", np.nan), 
                                      "losses": manager_data.get("performance", {}).get("losses", np.nan),
                                      "goals_scored": manager_data.get("performance", {}).get("goalsScored", np.nan), 
                                      "goals_conceded": manager_data.get("performance", {}).get("goalsConceded", np.nan),
                                      "points": manager_data.get("performance", {}).get("totalPoints", np.nan)})
            except:
                continue

    # Limpieza básica del Dataframe
    man_df = pd.DataFrame(managers_info)
    man_df = man_df.rename(columns={"id": "IdSS", "name": "Name", "short_name": "ShortName", "country": "Country", "date_birth": "DateBirth", "matches": "Matches", "wins": "Wins",
                                    "draws": "Draws", "losses": "Losses", "goals_scored": "GoalsFor", "goals_conceded": "GoalsAgainst", "points": "Points"})
    man_df.insert(1, "Slug", man_df["Name"].apply(create_slug))

    # Fecha de nacimiento y columnas integer
    man_df["DateBirth"] = pd.to_datetime(man_df["DateBirth"], unit="s", errors="coerce").dt.strftime("%d/%m/%Y")
    for col in ["Matches", "Wins", "Draws", "Losses", "GoalsFor", "GoalsAgainst", "Points"]:
        man_df[col] = pd.to_numeric(man_df[col], errors="coerce").astype("Int64")

    return man_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE EQUIPOS
# --------------------------------------------------------------------------------------
def teams_cleaning(print_info: bool = True) -> pd.DataFrame:

    # Path de carpeta con datos de equipos
    teams_path = os.path.join(RAW_DATA_PATH, "entities", "team")

    # Lista para concatenar información
    teams_info = []

    if print_info:
        i = 1
        total_teams = len(os.listdir(teams_path))

    # Para cada entrenador
    for team in os.listdir(teams_path):

        if print_info:
            print(f"            [{i}/{total_teams}] Processing team {team.replace('.json', '')}", flush=True, end="\r")
            i += 1

        try:
            single_team_data = json_to_dict(json_path=os.path.join(teams_path, team)).get("team")
            if single_team_data:
                teams_info.append({"team_id": single_team_data.get("id", np.nan), 
                                   "name": single_team_data.get("name", np.nan), 
                                   "short_name": single_team_data.get("shortName", np.nan),
                                   "full_name": single_team_data.get("fullName", np.nan), 
                                   "manager": single_team_data.get("manager", {}).get("id", np.nan),
                                   "venue": single_team_data.get("venue", {}).get("id", np.nan), 
                                   "country": single_team_data.get("country", {}).get("name", np.nan),
                                   "foundation_date": single_team_data.get("foundationDateTimestamp", np.nan), 
                                   "primary_colour": single_team_data.get("teamColors", {}).get("primary", np.nan),
                                   "secondary_colour": single_team_data.get("teamColors", {}).get("secondary", np.nan), 
                                   "text_colour": single_team_data.get("teamColors", {}).get("text", np.nan)})
        except:
            continue

    # Limpieza del dataframe
    teams_df = pd.DataFrame(teams_info)
    teams_df = teams_df.rename(columns={"team_id": "IdSS", "name": "Name", "short_name": "ShortName", "full_name": "LongName", "manager": "Manager", "venue": "Venue", "country": "Country",
                                        "foundation_date": "FoundationDate", "primary_colour": "PrimaryColour", "secondary_colour": "SecondaryColour", "text_colour": "TextColour"})
    teams_df.insert(1, "Slug", teams_df["Name"].apply(create_slug))
    teams_df["FoundationDate"] = pd.to_datetime(teams_df["FoundationDate"], unit="s", errors="coerce").dt.strftime("%d/%m/%Y")

    return teams_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE JUGADORES
# --------------------------------------------------------------------------------------
def players_cleaning(print_info: bool = True) -> pd.DataFrame:

    # Path de carpeta con datos de jugadores
    players_path = os.path.join(RAW_DATA_PATH, "entities", "player")

    # Lista para concatenar información
    players_info = []

    if print_info:
        i = 1
        total_players = len(os.listdir(players_path))

    # Para cada entrenador
    for player in os.listdir(players_path):

        if print_info:
            print(f"            [{i}/{total_players}] Processing player {player.replace('.json', '')}", flush=True, end="\r")
            i += 1

        try:
            single_player_data = json_to_dict(json_path=os.path.join(players_path, player)).get("player")

            # Tratado de posiciones (hay distintas)
            positions_detailed = single_player_data.get("positionsDetailed", [])
            first_position = positions_detailed[0] if len(positions_detailed) > 0 else np.nan
            second_position = positions_detailed[1] if len(positions_detailed) > 1 else np.nan
            third_position = positions_detailed[2] if len(positions_detailed) > 2 else np.nan

            # Añadir más información
            players_info.append({"IdSS": single_player_data.get("id", np.nan), 
                                 "name": single_player_data.get("name", np.nan),
                                 "shortName": single_player_data.get("shortName", np.nan), 
                                 "team": single_player_data.get("team", {}).get("id", np.nan),
                                 "first_position": first_position,
                                 "second_position": second_position, 
                                 "third_position": third_position, 
                                 "shirt_num": single_player_data.get("shirtNumber", np.nan),
                                 "height": single_player_data.get("height", np.nan), 
                                 "pref_foot": single_player_data.get("preferredFoot", np.nan),
                                 "date_birth": single_player_data.get("dateOfBirthTimestamp", np.nan), 
                                 "country": single_player_data.get("country", {}).get("name", np.nan),
                                 "contract_until": single_player_data.get("contractUntilTimestamp", np.nan), 
                                 "market_value": single_player_data.get("proposedMarketValue", np.nan)})
        except:
            continue
    
    # Transformado a Df y merge con el otro dataframe
    players_df = pd.DataFrame(players_info)
    players_df = players_df.rename(columns={"name": "Name", "shortName": "ShortName", "team": "Team", "first_position": "FirstPosition", "second_position": "SecondPosition", 
                                            "third_position": "ThirdPosition", "shirt_num": "ShirtNum", "height": "Height", "pref_foot": "PrefFoot", 
                                            "date_birth": "DateBirth", "country": "Country", "contract_until": "ContractUntil", "market_value": "MarketValue"})
    
    # Tratado de columnas
    players_df.insert(1, "Slug", players_df["Name"].apply(create_slug))
    players_df["ShirtNum"] = players_df["ShirtNum"].astype("Int64")
    players_df["Height"] = players_df["Height"].astype("Int64")
    players_df["MarketValue"] = players_df["MarketValue"].astype("Int64")

    # Fechas
    players_df["DateBirth"] = pd.to_datetime(players_df["DateBirth"], unit="s", errors="coerce").dt.strftime("%d/%m/%Y")
    players_df["ContractUntil"] = pd.to_datetime(players_df["ContractUntil"], unit="s", errors="coerce").dt.strftime("%d/%m/%Y")

    return players_df.drop_duplicates().sort_values(by="Slug")

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE PARTIDOS
# --------------------------------------------------------------------------------------
def matches_cleaning(print_info: bool = True) -> pd.DataFrame:

    matches_dict_paths = {}

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "sofascore", "matches")
            for match_id in os.listdir(season_path):
                match_path_dict = os.path.join(season_path, match_id)
                if os.path.exists(match_path_dict):
                    matches_dict_paths[match_id] = match_path_dict

    all_matches_info = []

    if print_info:
        i = 1
        total_matches = len(matches_dict_paths)

    # Para cada path, obtenemos datos
    for match_id, match_path in matches_dict_paths.items():

        if print_info:
            print(f"            [{i}/{total_matches}] Processing match {match_id}", flush=True, end="\r")
            i += 1

        try:
            # Obtenemos liga y temporada
            tournament = match_path.split("\\")[4]
            season = match_path.split("\\")[5]

            # Concatenamos información
            dict_info = json_to_dict(json_path=os.path.join(match_path, "info.json")).get("event")
            if dict_info:
                all_matches_info.append({"match_id": dict_info.get("id", np.nan), 
                                         "league": tournament,
                                        "season": season,
                                        "round": dict_info.get("roundInfo", {}).get("round", np.nan), 
                                        "winner": dict_info.get("winnerCode", np.nan),
                                        "attendance": dict_info.get("attendance", np.nan), 
                                        "venue": dict_info.get("venue", {}).get("id", np.nan), 
                                        "referee": dict_info.get("referee", {}).get("name", np.nan),
                                        "home_team": dict_info.get("homeTeam", {}).get("id", np.nan), 
                                        "away_team": dict_info.get("awayTeam", {}).get("id", np.nan), 
                                        "home_score": dict_info.get("homeScore", {}).get("display", np.nan),
                                        "away_score": dict_info.get("awayScore", {}).get("display", np.nan), 
                                        "home_manager": dict_info.get("homeTeam", {}).get("manager", {}).get("id", np.nan),
                                        "away_manager": dict_info.get("homeTeam", {}).get("manager", {}).get("id", np.nan),
                                        "date_time": dict_info.get("startTimestamp", np.nan)})
        
        except:
            continue

    # Limpieza del dataframe
    matches_df = pd.DataFrame(all_matches_info)
    matches_df = matches_df.rename(columns={"match_id": "IdSS", "league": "League", "season": "Season", "round": "Round", "winner": "Winner", "attendance": "Attendance", "venue": "Venue",
                                            "referee": "Referee", "home_team": "HomeTeam", "away_team": "AwayTeam", "home_score": "HomeScore", "away_score": "AwayScore", "home_manager": "HomeManager",
                                            "away_manager": "AwayManager", "date_time": "DateTime"})

    # Otras transformaciones
    matches_df["Winner"] = np.where(matches_df["Winner"] == 1, "Home", np.where(matches_df["Winner"] == 2, "Away", "X"))
    for col in ["Attendance", "HomeScore", "AwayScore"]:
        matches_df[col] = matches_df[col].astype("Int64")

    # Ordenado antes de convertir horario
    matches_df = matches_df.sort_values(by=["League", "Season", "DateTime"])

    # Conversión a horario
    matches_df["DateTime"] = pd.to_datetime(matches_df["DateTime"], unit="s")
    matches_df["Date"] = matches_df["DateTime"].dt.strftime("%d/%m/%Y")
    matches_df["Time"] = matches_df["DateTime"].dt.strftime("%H:%M")
    matches_df = matches_df.drop(columns=["DateTime"])

    return matches_df

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE ESTADÍSTICAS DE EQUIPOS - en un partido
# --------------------------------------------------------------------------------------
def stats_single_match(path_stats_ss: str, match_id: str, home_team_id: str, away_team_id: str) -> pd.DataFrame:

    df_stats = pd.DataFrame()

    data = json_to_dict(json_path=path_stats_ss).get("statistics")
    if len(data) > 0:
        dict_data = data[0].get("groups")

        home_stats = {}
        away_stats = {}

        if dict_data:
            for group in dict_data:
                group_stats = group.get("statisticsItems")
                if group_stats:
                    for statistic_item in group_stats:
                        stat_key = statistic_item.get("key")
                        if stat_key:
                            home_stats[stat_key] = statistic_item.get("homeValue", np.nan)
                            away_stats[stat_key] = statistic_item.get("awayValue", np.nan)

        df_stats = pd.DataFrame([{"Match": match_id, "team": home_team_id, **home_stats},
                                {"Match": match_id, "team": away_team_id, **away_stats}])

    return df_stats

# --------------------------------------------------------------------------------------
# LIMPIEZA DE DATAFRAME DE ESTADÍSTICAS DE JUGADORES - en un partido
# --------------------------------------------------------------------------------------
def lineups_single_match(path_lineups_ss: str, match_id: str, home_team_id: str, away_team_id: str) -> pd.DataFrame:

    # Lectura del JSON en formato diccionario
    dict_data = json_to_dict(json_path=path_lineups_ss)

    list_data = []

    # Si se cumple la información obtenemos las alineaciones
    if dict_data:
        home_lineups = dict_data.get("home")
        away_lineups = dict_data.get("away")

        if home_lineups:
            home_formation = home_lineups.get("formation", np.nan)
            players = home_lineups.get("players")
            if players:
                for player in players:
                    player_dict = {"team": home_team_id,
                                   "player": player.get("player", {}).get("id", np.nan),
                                   "shirt_num": player.get("shirtNumber", np.nan),
                                   "position": player.get("position", np.nan)}
                    
                    # Estadísticas del jugador
                    player_statistics = player.get("statistics")
                    if player_statistics:
                        player_statistics = {k: v for k, v in player_statistics.items() if isinstance(v, (int, float))}        # Solo estadísticas numericas
                        player_dict.update(player_statistics)

                    list_data.append(player_dict)

        if away_lineups:
            away_formation = away_lineups.get("formation", np.nan)
            players = away_lineups.get("players")
            if players:
                for player in players:
                    player_dict = {"team": away_team_id,
                                   "player": player.get("player", {}).get("id", np.nan),
                                   "shirt_num": player.get("shirtNumber", np.nan),
                                   "position": player.get("position", np.nan)}
                    
                    # Estadísticas del jugador
                    player_statistics = player.get("statistics")
                    if player_statistics:
                        player_statistics = {k: v for k, v in player_statistics.items() if isinstance(v, (int, float))}        # Solo estadísticas numericas
                        player_dict.update(player_statistics)

                    list_data.append(player_dict)

    # Transformación a dataframe
    df_lineups = pd.DataFrame(list_data)

    # Quitar los jugadores sin estadisticas
    cols_base = ["team", "player", "shirt_num", "position"]
    cols_stats = [col for col in df_lineups.columns if col not in cols_base]
    df_lineups[cols_stats] = df_lineups[cols_stats].replace(0, np.nan)              # Valores nulos primero si hay 0
    df_lineups = df_lineups.dropna(subset=cols_stats, how="all")
    df_lineups = df_lineups.fillna(0).reset_index(drop=True)

    # Añadimos match ID y equipos
    df_lineups.insert(0, "Match", match_id)

    return df_lineups, home_formation, away_formation

# --------------------------------------------------------------------------------------
# OBTENEMOS LAS ESTADÍSTICAS DE LOS EQUIPOS Y LOS JUGADORES EN LOS PARTIDOS
# --------------------------------------------------------------------------------------
def stats_cleaning(matches_df: pd.DataFrame, print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:

    matches_dict_paths = {}

    # Para cada liga, obtenemos las carpetas
    for league in COMPS['tournament'].unique():
        league_slug = create_slug(league)
        league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)

        # Para cada temporada
        for season_key in ["2425", "2526"]:
            season_path = os.path.join(league_path, season_key, "sofascore", "matches")
            for match_id in os.listdir(season_path):
                match_path_dict = os.path.join(season_path, match_id)
                if os.path.exists(match_path_dict):
                    matches_dict_paths[match_id] = match_path_dict

    all_matches_stats = []
    all_matches_lineups = []
    matches_formations = {}

    if print_info:
        i = 1
        total_matches = len(matches_dict_paths)

    # Para cada partido
    for idx, row in matches_df.iterrows():

        if print_info:
            print(f"            [{i}/{total_matches}] Advanced processing match {row['IdSS']}", flush=True, end="\r")
            i += 1

        match_dir = matches_dict_paths.get(str(row["IdSS"]))
        if match_dir:
            stats_path = os.path.join(match_dir, "stats.json")
            if os.path.exists(stats_path):
                all_matches_stats.append(stats_single_match(path_stats_ss=stats_path, match_id=str(row["IdSS"]), home_team_id=str(row["HomeTeam"]), away_team_id=str(row["AwayTeam"])))
            
            lineups_path = os.path.join(match_dir, "lineups.json")
            if os.path.exists(lineups_path):
                match_lineups, home_formation, away_formation = lineups_single_match(path_lineups_ss=lineups_path, match_id=str(row["IdSS"]), home_team_id=str(row["HomeTeam"]), away_team_id=str(row["AwayTeam"]))
                all_matches_lineups.append(match_lineups)
                matches_formations[row["IdSS"]] = {str(row["HomeTeam"]): home_formation, str(row["AwayTeam"]): away_formation}

    # Convertimos a dataframes
    team_stats = pd.concat(all_matches_stats, ignore_index=True)
    player_stats = pd.concat(all_matches_lineups, ignore_index=True)

    # Diccionario todo a string limpio
    matches_formations_str = {str(int(match_id)): {str(int(team_id)): formation for team_id, formation in teams.items()} for match_id, teams in matches_formations.items()}

    # Columnas del dataframe a string limpio
    team_stats["Match"] = pd.to_numeric(team_stats["Match"], errors="coerce").astype("Int64").astype(str)
    team_stats["team"] = pd.to_numeric(team_stats["team"], errors="coerce").astype("Int64").astype(str)

    # Añadir formación
    team_stats["formation"] = team_stats.apply(lambda row: matches_formations_str.get(row["Match"], {}).get(row["team"], np.nan), axis=1)

    return team_stats, player_stats

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE LIMPIEZA DE SOFASCORE
# --------------------------------------------------------------------------------------
def main_cleaning(print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    start_time = time.time()

    if print_info:
        print(f"Sofascore bronze data cleaning                                                                                         ")

    # Carpeta de sofascore cleaning
    ss_cleaned_path = os.path.join(BRONZE_DATA_PATH, "sofascore_cleaned_data")
    os.makedirs(ss_cleaned_path, exist_ok=True)

    if print_info:
        print(f"        1. Managers Sofascore cleaning.                                                                             ")

    # Información de managers
    ss_manager_cleaned_path = os.path.join(ss_cleaned_path, "manager.csv")
    if not os.path.exists(ss_manager_cleaned_path) or need_to_upload(path=ss_manager_cleaned_path, total_days=10):
        managers_df = managers_cleaning(print_info=print_info)
        managers_df.drop_duplicates().to_csv(ss_manager_cleaned_path, index=False, sep=";")
    else:
        managers_df = pd.read_csv(ss_manager_cleaned_path, sep=";")

    if print_info:
        print(f"        2. Teams Sofascore cleaning.                                                                             ")

    # Información de equipos
    ss_team_cleaned_path = os.path.join(ss_cleaned_path, "team.csv")
    if not os.path.exists(ss_team_cleaned_path) or need_to_upload(path=ss_team_cleaned_path, total_days=10):
        teams_df = teams_cleaning(print_info=print_info)
        teams_df.drop_duplicates().to_csv(ss_team_cleaned_path, index=False, sep=";")
    else:
        teams_df = pd.read_csv(ss_team_cleaned_path, sep=";")

    if print_info:
        print(f"        3. Players Sofascore cleaning.                                                                             ")

    # Información de jugadores
    ss_player_cleaned_path = os.path.join(ss_cleaned_path, "player.csv")
    if not os.path.exists(ss_player_cleaned_path) or need_to_upload(path=ss_player_cleaned_path, total_days=10):
        players_df = players_cleaning(print_info=print_info)
        players_df.drop_duplicates().to_csv(ss_player_cleaned_path, index=False, sep=";")
    else:
        players_df = pd.read_csv(ss_player_cleaned_path, sep=";")

    if print_info:
        print(f"        4. Matches Sofascore cleaning.                                                                             ")

    # Información de jugadores
    ss_matches_cleaned_path = os.path.join(ss_cleaned_path, "match.csv")
    if not os.path.exists(ss_matches_cleaned_path) or need_to_upload(path=ss_matches_cleaned_path, total_days=10):
        matches_df = matches_cleaning(print_info=print_info)
        matches_df.drop_duplicates().to_csv(ss_matches_cleaned_path, index=False, sep=";")
    else:
        matches_df = pd.read_csv(ss_matches_cleaned_path, sep=";")

    if print_info:
        print(f"        5. Statistics Sofascore cleaning.                                                                             ")

    # Estadísticas de jugadores y de equipos
    ss_team_stats_path = os.path.join(ss_cleaned_path, "stats_team.csv")
    ss_player_stats_path = os.path.join(ss_cleaned_path, "stats_player.csv")
    if (not os.path.exists(ss_team_stats_path) or need_to_upload(path=ss_team_stats_path, total_days=10)) or (not os.path.exists(ss_player_stats_path) or need_to_upload(path=ss_player_stats_path, total_days=10)):
        stats_teams_df, stats_players_df = stats_cleaning(matches_df=matches_df, print_info=print_info)
        stats_teams_df.drop_duplicates().to_csv(ss_team_stats_path, index=False, sep=";")
        stats_players_df.drop_duplicates().to_csv(ss_player_stats_path, index=False, sep=";")
    else:
        stats_teams_df = pd.read_csv(ss_team_stats_path, sep=";")
        stats_players_df = pd.read_csv(ss_player_stats_path, sep=";")

    if print_info:
        print(f"Sofascore data cleaning finished in {elapsed_time_str(start_time=start_time)}.")

    return players_df.drop_duplicates(), teams_df.drop_duplicates(), managers_df.drop_duplicates(), matches_df.drop_duplicates(), stats_teams_df.drop_duplicates(), stats_players_df.drop_duplicates()