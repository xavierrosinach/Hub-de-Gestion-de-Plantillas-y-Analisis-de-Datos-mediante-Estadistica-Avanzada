import os
import pandas as pd
import time
import copy
import numpy as np
from typing import Tuple
import warnings
from pandas.errors import PerformanceWarning

warnings.simplefilter(action="ignore", category=PerformanceWarning)

# Configuración
from use.config import DATA_PATH, UTILS_DIR
from use.functions import elapsed_time_str, safe_json_dump, json_to_dict, df_safe_div

# Importamos funciones de similitud y once titular
import gold.similarity_score as sim 
import gold.starting_eleven as st_eleven
import gold.player_adaptability as adapt
import gold.image_transfer as ima_transf
import gold.r2_uploader as r2

# Creación de un uploader
r2_upl = r2.R2Uploader()

# Diccionarios con columnas a tratar
counted_stats_list = json_to_dict(json_path=os.path.join(UTILS_DIR, "proc", "gold_proc", "counted_stats_cols.json")).get("counted_stats")
position_stats_dict = json_to_dict(json_path=os.path.join(UTILS_DIR, "proc", "gold_proc", "position_relevant_cols.json"))

# Estructura de carpetas
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
GOLD_DATA_PATH = os.path.join(DATA_PATH, "gold")
os.makedirs(GOLD_DATA_PATH, exist_ok=True)

# Lectura de todos los dataframes (basicos)
MANAGER = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_1", "manager_clean_1.csv"), sep=";")
PLAYER = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "player_clean_3_2.csv"), sep=";")
TEAM = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_2", "team_clean_2.csv"), sep=";")
MATCH = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_2", "match_clean_2.csv"), sep=";")

# Estadísticas
PLAYER_STATS = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "player_stats_clean_3_2.csv"), sep=";")
TEAM_STATS = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_2", "team_stats_clean_2.csv"), sep=";")

# Mapas de pases y tiros
PASS_MAP = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "pass_map_clean_3.csv"), sep=";")
SHOT_MAP = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "shot_map_clean_3.csv"), sep=";")

# Dataframes con estadísticas agregadas de la temporada
AGG_PLAYER_SEASON = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "agg_player.csv"), sep=";")
AGG_TEAM_SEASON = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "agg_team.csv"), sep=";")

# Computamos las matrices de similitud y el diccionario con adaptabilidades de jugadores en equipos
TEAM_SIM_MATRIX = sim.proc_teams_sim_matrix(matches_info_df=MATCH.copy(), team_season_agg_stats=AGG_TEAM_SEASON.copy())
PLAYER_SIM_MATRIX_GK, PLAYER_SIM_MATRIX_DF, PLAYER_SIM_MATRIX_MD, PLAYER_SIM_MATRIX_ST = sim.main_proc_data_similarity(match_info_df=MATCH.copy(), player_stats_df=PLAYER_STATS, player_info_df=PLAYER.copy())
PLAYER_ADAPTABILITY = adapt.main(print_info = False, only_saved=True)

# --------------------------------------------------------------------------------------
# Devuelve True si el valor debe eliminarse del JSON
# --------------------------------------------------------------------------------------
def is_empty_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if pd.isna(value) if not isinstance(value, (list, dict, np.ndarray)) else False:
        return True
    if isinstance(value, (list, tuple, set)) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    if isinstance(value, np.ndarray) and value.size == 0:
        return True
    return False

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA EL GUARDADO SEGURO DE UN FICHERO JSON - Función recursiva
# --------------------------------------------------------------------------------------
def clean_json_values(json_obj):

    if isinstance(json_obj, dict):
        cleaned_dict = {}
        for key, value in json_obj.items():
            cleaned_value = clean_json_values(value)
            if not is_empty_value(cleaned_value):
                cleaned_dict[key] = cleaned_value
        return cleaned_dict

    elif isinstance(json_obj, list):
        cleaned_list = []
        for item in json_obj:
            cleaned_item = clean_json_values(item)
            if not is_empty_value(cleaned_item):
                cleaned_list.append(cleaned_item)
        return cleaned_list

    elif isinstance(json_obj, np.ndarray):
        return clean_json_values(json_obj.tolist())
    elif pd.isna(json_obj):
        return None
    else:
        return json_obj
    
# --------------------------------------------------------------------------------------
# OBTENCIÓN DE LOS DICCIONARIOS PRINCIPALES A PARTIR DE LOS DATAFRAMES
# --------------------------------------------------------------------------------------
def get_principal_dicts(match_df: pd.DataFrame, manager_df: pd.DataFrame, player_df: pd.DataFrame, team_df: pd.DataFrame) -> Tuple[dict, dict, dict]:

    def get_raw_managers_dict(managers_df: pd.DataFrame, teams_list: list) -> dict:
        managers_df = managers_df[["ID", "Name", "FirstName", "LastName", "Country", "DateBirth", "Team"]]
        managers_df = managers_df[managers_df["Team"].isin(teams_list)].set_index("ID", drop=False)
        managers_dict = managers_df.to_dict(orient="index")
        return clean_json_values(json_obj=managers_dict)

    def get_raw_players_dict(players_df: pd.DataFrame, teams_list: list) -> dict:
        players_df = players_df[["ID", "Name", "FirstName", "LastName", "DateBirth", "Country", "Team", "Rating", "Potential", "Height", "PrefFoot", "ShirtNumber", 
                                "FirstPos", "SecondPos", "ThirdPos", "Role", "ContractUntil", "MarketValue"]]
        players_df = players_df[players_df["Team"].isin(teams_list)].set_index("ID", drop=False)
        players_dict = players_df.to_dict(orient="index")
        return clean_json_values(json_obj=players_dict)

    def get_raw_teams_dict(teams_df: pd.DataFrame, teams_list: list) -> dict:
        teams_df = teams_df[['ID', 'Name', 'Abbreviation', 'Country', 'FoundationDate', 'Manager', 'EloRating', 'PrimaryColour', 'SecondaryColour', 'HomeKitCol1', 
                            'HomeKitCol2','HomeShortsCol', 'AwayKitCol1', 'AwayKitCol2', 'AwayShortsCol']]
        teams_df = teams_df[teams_df["ID"].isin(teams_list)].set_index("ID", drop=False)
        teams_dict = teams_df.to_dict(orient="index")
        return clean_json_values(json_obj=teams_dict)

    def get_team_tournaments(matches_df: pd.DataFrame) -> dict:

        TOP_LEAGUES = ["la_liga", "premier_league", "bundesliga", "serie_a", "ligue_1", "la_liga_hypermotion", "championship", "eredivise", "liga_portugal"]
        LEAGUES_NAMES_DICT = {"la_liga": "La Liga", "premier_league": "Premier League", "bundesliga": "Bundesliga", "serie_a": "Serie A", 
                              "ligue_1": "Ligue 1", "la_liga_hypermotion": "La Liga Hypermotion", "championship": "EFL Championship", 
                              "eredivise": "Eredivise", "liga_portugal": "Liga Portugal", "champions_league": "Champions League", 
                              "conference_league": "Conference League", "europa_league": "Europa League", "copa_del_rey": "Copa del Rey"}

        # Preparación del dataframe de entorno
        matches_df = matches_df[matches_df["Season"].astype(str) == "2526"]
        matches_df = pd.concat([matches_df[["HomeTeam", "League"]].rename(columns={"HomeTeam": "Team"}),
                                matches_df[["AwayTeam", "League"]].rename(columns={"AwayTeam": "Team"})],
                                ignore_index=True)
        matches_df = matches_df.drop_duplicates().sort_values(by="League")

        # Preparación del diccionario con las ligas
        teams_competitions = {}
        for team in matches_df["Team"].unique():
            list_comps = matches_df.loc[matches_df["Team"] == team, "League"].unique().tolist()

            # Debe participar en al menos una top league
            if not any(comp in TOP_LEAGUES for comp in list_comps):
                continue
            
            list_comps = [LEAGUES_NAMES_DICT.get(comp, comp) for comp in list_comps]
            teams_competitions[team] = list_comps

        return teams_competitions

    def add_team_to_dict(raw_dict: dict, raw_team_dict: dict) -> dict:

        new_dict = copy.deepcopy(raw_dict)
        for id, info in new_dict.items():

            team_id = info.get("Team")
            if isinstance(team_id, dict):
                continue

            if team_id and team_id in raw_team_dict:
                team_info = {k: raw_team_dict[team_id][k] for k in ("ID", "Name", "Abbreviation") if k in raw_team_dict[team_id]}
                info["Team"] = team_info

        return new_dict

    def add_manager(raw_dict: dict, raw_manager_dict: dict) -> dict:

        new_dict = copy.deepcopy(raw_dict)
        for id, info in new_dict.items():

            manager_id = info.get("Manager")
            if manager_id and manager_id in raw_manager_dict:
                manager_info = {k: raw_manager_dict[manager_id][k] for k in ("ID", "Name", "Country") if k in raw_manager_dict[manager_id]}
                info["Manager"] = manager_info

        return new_dict

    # Competiciones por equipo
    team_tourn_dict = get_team_tournaments(matches_df=match_df.copy())

    # Obtenemos diccionarios de información
    raw_manager_dict = get_raw_managers_dict(managers_df=manager_df.copy(), teams_list=team_tourn_dict.keys())
    raw_player_dict = get_raw_players_dict(players_df=player_df.copy(), teams_list=team_tourn_dict.keys())
    raw_team_dict = get_raw_teams_dict(teams_df=team_df.copy(), teams_list=team_tourn_dict.keys())

    # Añadimos información principal de las entidades a cada diccionario
    new_manager_dict = add_team_to_dict(raw_dict=raw_manager_dict, raw_team_dict=raw_team_dict)
    new_player_dict = add_team_to_dict(raw_dict=raw_player_dict, raw_team_dict=raw_team_dict)
    new_team_dict = add_manager(raw_dict=raw_team_dict, raw_manager_dict=raw_manager_dict)

    # Añadimos tournaments a los equipos
    team_tournaments = get_team_tournaments(matches_df=match_df)
    for team_id, team_values in new_team_dict.items():
        team_tourns_list = team_tournaments.get(team_id, [])
        if len(team_tourns_list) > 0:
            team_values["Tournaments"] = team_tourns_list

    return new_manager_dict, new_player_dict, new_team_dict

# --------------------------------------------------------------------------------------
# MEJORA DEL DICCIONARIO DE EQUIPOS
# --------------------------------------------------------------------------------------
def update_teams_dict(team_dict: dict, players_info_df: pd.DataFrame, match_info_df: pd.DataFrame, player_stats_df: pd.DataFrame, team_stats_df: pd.DataFrame, team_agg_stats: pd.DataFrame) -> dict:

    # Filtramos
    proc_teams_list = list(team_dict.keys())
    players_info_df = players_info_df[players_info_df["Team"].isin(proc_teams_list)]
    match_info_df = match_info_df[(match_info_df["HomeTeam"].isin(proc_teams_list)) | (match_info_df["AwayTeam"].isin(proc_teams_list))]
    player_stats_df = player_stats_df[player_stats_df["Team"].isin(proc_teams_list)]
    team_stats_df = team_stats_df[team_stats_df["Team"].isin(proc_teams_list)]
    team_agg_stats = team_agg_stats[team_agg_stats["Team"].isin(proc_teams_list)]

    # Función para obtener la plantilla de un equipo
    def get_team_squad(player_df: pd.DataFrame, team_id: str) -> list:
        team_player_df = player_df[player_df["Team"] == team_id]
        team_player_df = team_player_df[["ID", "Name", "Country", "DateBirth", "Height", "PrefFoot", "FirstPos", "Role"]]
        return list(team_player_df.to_dict(orient="index").values())

    # Aplicamos para cada equipo
    new_team_dict = team_dict.copy()
    for team_id, team_info in new_team_dict.items():
        team_squad = get_team_squad(player_df=players_info_df, team_id=team_id)
        team_lineup = st_eleven.main_team_lineup(team_id=team_id, match_info_df=match_info_df.copy(), player_info_df=players_info_df.copy(), player_stats_df=player_stats_df.copy(), team_stats_df=team_stats_df.copy())
        
        # Estadisticas agregadas del equipo
        single_team_agg_stats = team_agg_stats[team_agg_stats["Team"] == team_id].drop(columns=["Team"])
        single_team_agg_stats_list = list(single_team_agg_stats.to_dict(orient="index").values())

        if len(team_squad) > 0:
            team_info["Squad"] = team_squad
        if len(team_lineup) > 0:
            team_info["Lineup"] = team_lineup
        if len(single_team_agg_stats_list) > 0:
            team_info["AggregatedStats"] = {k: v for k, v in single_team_agg_stats_list[0].items() if v != 0}

    return clean_json_values(new_team_dict)

# --------------------------------------------------------------------------------------
# AÑADIMOS ESTADÍSTICAS DE JUGADORES
# --------------------------------------------------------------------------------------
def update_players_dict(player_dict: dict, agg_stats_player: pd.DataFrame) -> dict:

    # Filtramos
    list_players = list(player_dict.keys())
    agg_stats_player = agg_stats_player[agg_stats_player["Player"].isin(list_players)]
    agg_stats_player = agg_stats_player.drop(columns=["ShirtNumber", "Position"]).fillna(0)

    new_players_dict = player_dict.copy()
    for player_id, player_info in new_players_dict.items():
        single_player_agg_stats = agg_stats_player[agg_stats_player["Player"] == player_id].drop(columns=["Player"])
        single_player_agg_stats_list = list(single_player_agg_stats.to_dict(orient="index").values())
        if len(single_player_agg_stats_list) > 0:
            stats_row = single_player_agg_stats_list[0]

            # Estadísticas contadas (se mantienen los ceros)
            player_info["Stats"] = {k: v for k, v in stats_row.items() if k in counted_stats_list}

            # Columnas relevantes según las posiciones del jugador
            player_positions = [player_info.get("FirstPos", ""), player_info.get("SecondPos", ""), player_info.get("ThirdPos", "")]
            cols_to_lookup = list({c for pos in player_positions for c in position_stats_dict.get(pos, [])})

            # Estadísticas agregadas (se descartan los ceros)
            player_info["AggregatedStats"] = {k: v for k, v in stats_row.items() if k in cols_to_lookup and v != 0}

    return new_players_dict

# --------------------------------------------------------------------------------------
# AÑADIMOS JUGADORES Y EQUIPOS SIMILARES
# --------------------------------------------------------------------------------------
def add_similars(team_dict: dict, player_dict: dict, match_df: pd.DataFrame, agg_team: pd.DataFrame, player_stats: pd.DataFrame, player_info: pd.DataFrame) -> Tuple[dict, dict]:

    # Filtramos
    proc_teams_list = list(team_dict.keys())
    agg_team = agg_team[agg_team["Team"].isin(proc_teams_list)]
    match_df = match_df[(match_df["HomeTeam"].isin(proc_teams_list)) | (match_df["AwayTeam"].isin(proc_teams_list))]
    player_info = player_info[player_info["Team"].isin(proc_teams_list)]
    player_stats = player_stats[player_stats["Team"].isin(proc_teams_list)]

    # Obtenemos las matrices de correlación
    team_corr_matrix = sim.proc_teams_sim_matrix(matches_info_df=match_df.copy(), team_season_agg_stats=agg_team.copy())
    gk_corr, df_corr, md_corr, fw_corr = sim.main_proc_data_similarity(match_info_df=match_df.copy(), player_stats_df=player_stats.copy(), player_info_df=player_info.copy())

    # Lista con equipos similares (50)
    def team_similar_list(team_id: str) -> list:

        sim_teams = sim.get_similar_teams(team_id=team_id, top_n=50, teams_perc_corr=team_corr_matrix)
        sim_teams_list = []
        i = 1
        for sim_team_id, similarity in sim_teams.items():
            sim_team_info = team_dict.get(sim_team_id)
            if sim_team_info:
                sim_teams_list.append({"Num": i,
                                    "Team": sim_team_info.get("ID"),
                                    "Name": sim_team_info.get("Name", ""),
                                    "EloRating": sim_team_info.get("EloRating", 0),
                                    "Similarity": similarity})
                i += 1
        return sim_teams_list

    # Lista con jugadores similares (50)
    def player_similar_list(player_id: str) -> list: 

        sim_players = sim.get_similar_players(player_id=player_id, top_n=50, corr_perc_goalkeepers=gk_corr, corr_perc_midfielders=md_corr, corr_perc_attackers=fw_corr, corr_perc_defenders=df_corr)
        sim_players_list = []
        i = 1
        for sim_player_id, similarity in sim_players.items():
            sim_player_info = player_dict.get(sim_player_id)
            if sim_player_info:
                sim_players_list.append({"Num": i,
                                         "Player": sim_player_info.get("ID"),
                                         "Name": sim_player_info.get("Name"),
                                         "Rating": sim_player_info.get("Rating", 0),
                                         "Potential": sim_player_info.get("Potential"),
                                         "Position": sim_player_info.get("FirstPos"),
                                         "Role": sim_player_info.get("Role", ""),
                                         "Team": sim_player_info.get("Team", {}),
                                         "Similarity": similarity})
                i += 1
        return sim_players_list

    # Añadimos equipos similares
    new_teams_dict = team_dict.copy()
    for team_id, team_info in new_teams_dict.items():
        list_sim_teams = team_similar_list(team_id=team_id)
        if len(list_sim_teams) > 0:
            team_info["SimilarTeams"] = list_sim_teams

    # Añadimos jugadores similares
    new_players_dict = player_dict.copy()
    for player_id, player_info in new_players_dict.items():
        list_sim_players = player_similar_list(player_id=player_id)
        if len(list_sim_players) > 0:
            player_info["SimilarPlayers"] = list_sim_players

    return new_teams_dict, new_players_dict

# --------------------------------------------------------------------------------------
# FUNCION PARA AÑADIR MAPA DE PASES Y DE TIROS POR EQUIPO Y JUGADOR
# --------------------------------------------------------------------------------------
def add_passes_and_shots(player_dict: dict, team_dict: dict, matches_df: pd.DataFrame, shots_df: pd.DataFrame, passes_df: pd.DataFrame) -> Tuple[dict, dict]:

    # Partidos de la temporada y filtramos
    season_matches = matches_df[matches_df["Season"].astype("str") == str("2526")]["ID"].unique().tolist()
    shots_df = shots_df[shots_df["Match"].isin(season_matches)]
    passes_df = passes_df[passes_df["Match"].isin(season_matches)]

    # Información que nos interesa
    shots_df = shots_df.drop(columns=["Zone", "Length", "Match"])
    passes_df = passes_df.drop(columns=["Match", "AccuratePass", "Angle", "Length", "Zone", "PassDirection"])

    # Obtiene la lista con los pases de un jugador
    def get_player_passes(player_id: str) -> list:
        player_passes_df = passes_df[passes_df["Player"] == player_id].drop(columns="Team")
        player_passes_df = player_passes_df[["IniX", "IniY", "EndX", "EndY", "PassReceiver"]]
        player_passes_list = list(player_passes_df.to_dict(orient="index").values())
        player_passes_list = clean_json_values(json_obj=player_passes_list)
        return player_passes_list

    # Obtiene la lista de los pases de un equipo
    def get_team_passes(team_id: str) -> list:
        team_passes_df = passes_df[passes_df["Team"] == team_id].drop(columns="Team")
        team_passes_df = team_passes_df[["IniX", "IniY", "EndX", "EndY", "Player", "PassReceiver"]]
        team_passes_list = list(team_passes_df.to_dict(orient="index").values())
        team_passes_list = clean_json_values(json_obj=team_passes_list)
        return team_passes_list

    # Obtiene la lista con los tiros de un jugador
    def get_player_shots(player_id: str) -> list:
        player_shots_df = shots_df[shots_df["Player"] == player_id].drop(columns="Team")
        player_shots_df = player_shots_df[["Type", "IniX", "IniY", "BlockX", "BlockY", "GoalY", "GoalZ"]]
        player_shots_list = list(player_shots_df.to_dict(orient="index").values())
        player_shots_list = clean_json_values(json_obj=player_shots_list)
        return player_shots_list

    # Obtiene la lsta con los tiros de un equipo
    def get_team_shots(team_id: str) -> list:
        team_shots_df = shots_df[shots_df["Player"] == team_id].drop(columns="Team")
        team_shots_df = team_shots_df[["Type", "IniX", "IniY", "BlockX", "BlockY", "GoalY", "GoalZ", "Player"]]
        team_shots_list = list(team_shots_df.to_dict(orient="index").values())
        team_shots_list = clean_json_values(json_obj=team_shots_list)
        return team_shots_list

    # Añadimos tiros y pases al equipo
    new_team_dict = team_dict.copy()
    for team_id, team_info in new_team_dict.items():
        team_passes = get_team_passes(team_id=team_id)
        team_shots = get_team_shots(team_id=team_id)
        if len(team_passes) > 0:
            team_info["Passes"] = team_passes
        if len(team_shots) > 0:
            team_info["Shots"] = team_shots

    # Añadimos tros y pases al jugador
    new_player_dict = player_dict.copy()
    for player_id, player_info in new_player_dict.items():
        player_passes = get_player_passes(player_id=player_id)
        player_shots = get_player_shots(player_id=player_id)
        if len(player_passes) > 0:
            player_info["Passes"] = player_passes
        if len(player_shots) > 0:
            player_info["Shots"] = player_shots

    return new_team_dict, new_player_dict

# --------------------------------------------------------------------------------------
# DIVISIÓN DE LAS ENTIDADES
# --------------------------------------------------------------------------------------
def part_entities(entity_dict: dict, entity: str) -> None:
    entity_path = os.path.join(GOLD_DATA_PATH, "entities", entity)
    os.makedirs(entity_path, exist_ok=True)
    for id, info_dict in entity_dict.items():
        single_path = os.path.join(entity_path, f"{id}.json")
        if not os.path.exists(single_path):
            safe_json_dump(data=info_dict, path=single_path)

# --------------------------------------------------------------------------------------
# AÑADIMOS LA ADAPTABILIDAD DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def add_players_adaptability(team_dict: dict, player_df: pd.DataFrame) -> dict:

    # Diccionario con los nombres de los jugadores y id
    players_id_dict = dict(zip(player_df["ID"], player_df["Name"]))

    # Para cada equipo
    team_dict_copy = team_dict.copy()
    for team_id, team_info in team_dict.items():

        # Consultamos que se encuentre en los equipos buscados
        if team_id not in PLAYER_ADAPTABILITY.keys():
            continue
        else:
            players_adapt = PLAYER_ADAPTABILITY.get(team_id)
            players_adapt["Name"] = players_adapt["Player"].map(players_id_dict)
            players_adapt = players_adapt[["Player", "Name", "Score", "Stars"]].set_index("Player", drop=False)
            players_adapt = players_adapt.to_dict(orient="index")

            # Añadimos players adapt a la nformación
            team_info["PlayersAdaptability"] = players_adapt

    return team_dict_copy

# --------------------------------------------------------------------------------------
# PREPARACIÓN DE LOS DATAFRAMES CON ESTADÍSTICAS DE EQUIPOS Y JUGADORES EN PARTIDOS PARA OBTENER EL DICCIONARIO POSTERIORMENTE
# --------------------------------------------------------------------------------------
def get_player_and_team_matches_to_look(match_df: pd.DataFrame, player_stats_df: pd.DataFrame, team_stats_df: pd.DataFrame, team_df: pd.DataFrame, manager_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:

    def matches_df_special_cleaning(match_df: pd.DataFrame, team_df: pd.DataFrame) -> pd.DataFrame:
        
        TOP_LEAGUES = ["la_liga", "premier_league", "bundesliga", "serie_a", "ligue_1", "la_liga_hypermotion", "championship", "eredivise", "liga_portugal"]
        LEAGUES_NAMES_DICT = {"la_liga": "La Liga", "premier_league": "Premier League", "bundesliga": "Bundesliga", "serie_a": "Serie A", 
                            "ligue_1": "Ligue 1", "la_liga_hypermotion": "La Liga Hypermotion", "championship": "EFL Championship", 
                            "eredivise": "Eredivise", "liga_portugal": "Liga Portugal", "champions_league": "Champions League", 
                            "conference_league": "Conference League", "europa_league": "Europa League", "copa_del_rey": "Copa del Rey"}

        # Selección de liga y temporada
        match_df = match_df[(match_df["Season"].astype(str) == "2526") & (match_df["League"].isin(TOP_LEAGUES))]
        match_df["League"] = match_df["League"].map(LEAGUES_NAMES_DICT)

        # Partidos del equipo local
        home_match_df = match_df[["ID", "League", "Date", "HomeTeam", "HomeScore", "HomeElo", "AwayTeam", "AwayScore", "AwayElo"]].rename(columns={"HomeTeam":"Team", "HomeScore":"Score", "HomeElo":"Elo", "AwayTeam":"Opponent", "AwayScore":"OpponentScore", "AwayElo":"OpponentElo"})
        home_match_df["HomeAway"] = "Home"
        away_match_df = match_df[["ID", "League", "Date", "AwayTeam", "AwayScore", "AwayElo", "HomeTeam", "HomeScore", "HomeElo"]].rename(columns={"HomeTeam":"Opponent", "HomeScore":"OpponentScore", "HomeElo":"OpponentElo", "AwayTeam":"Team", "AwayScore":"Score", "AwayElo":"Elo"})
        away_match_df["HomeAway"] = "Away"
        def_match_df = pd.concat([home_match_df, away_match_df]).sort_values(by=["League", "ID"])

        # Mapeo de los equipos (visitantes)
        def_match_df["OpponentName"] = def_match_df["Opponent"].map(dict(zip(team_df["ID"], team_df["Name"])))
        def_match_df["OpponentAbb"] = def_match_df["Opponent"].map(dict(zip(team_df["ID"], team_df["Abbreviation"])))

        # Diferencia de goles y diferencia de Elo
        def_match_df["ScoreDifference"] = def_match_df["Score"] - def_match_df["OpponentScore"]
        def_match_df["EloDifference"] = def_match_df["Elo"] - def_match_df["OpponentElo"]
        def_match_df["Result"] = np.where(def_match_df["ScoreDifference"] > 0, "Win", np.where(def_match_df["ScoreDifference"] < 0, "Loss", "Draw"))

        # Ordenado de columnas
        def_match_df = def_match_df[["ID", "Team", "League", "Date", "HomeAway", "Opponent", "OpponentName", "OpponentAbb", "Score", "OpponentScore", "ScoreDifference", "Result", "Elo", "OpponentElo", "EloDifference"]]
        return def_match_df

    # Arreglo del dataframe de partidos
    match_df = matches_df_special_cleaning(match_df=match_df.copy(), team_df=team_df.copy())
    matches_to_look = match_df["ID"].unique().tolist()
    match_df = match_df.rename(columns={"ID":"Match"})

    # Selección de aquellos partidos que estamos interesados
    team_stats_df = team_stats_df[team_stats_df["Match"].isin(matches_to_look)]
    player_stats_df = player_stats_df[player_stats_df["Match"].isin(matches_to_look)]

    # Selección de columnas y merge con partidos
    team_stats_df = team_stats_df.merge(match_df, on=["Match", "Team"], how="inner")
    IMPORTANT_TEAM_STATS = ["Match","Team","Manager","League","Date","HomeAway","Opponent","OpponentName","OpponentAbb","Score","OpponentScore","ScoreDifference","Result","Elo","OpponentElo","EloDifference",
                            "Formation","BallPossession","PassAccuracy","ProgressiveFieldTilt","FinalThirdEntries","TouchesInOppBox","PossessionLost","KeyPasses","ExpectedAssists",
                            "BigChancesCreated","BigChancesMissed","Crosses","CrossAccuracy","TotalShots","ShotsOnTarget","ShotAccuracy","ExpectedGoals","ExpectedGoalsOnTarget","Goals","GoalConversion",
                            "GoalsMinusxG","DuelWinRate","AerialWinRate","ContestWinRate","Tackles","TackleAccuracy","Interceptions","Clearances","BallRecoveries","DefensiveActionSuccess","ErrorsLeadToShot",
                            "GoalsConceded","Saves","SaveRate","GoalsPrevented","CleanSheets","Fouls","YellowCards","Offsides","CornerKicks"]
    team_stats_df = team_stats_df[IMPORTANT_TEAM_STATS]

    # Ordenamos por fecha y equipo
    team_stats_df["Date"] = pd.to_datetime(team_stats_df["Date"])
    team_stats_df = team_stats_df.sort_values(["Team", "Date"]).reset_index(drop=True)
    team_stats_df["Date"] = team_stats_df["Date"].dt.strftime("%d/%m/%Y")

    # Añadimos nombre de entrenador
    manager_id_to_name = dict(zip(manager_df["ID"], manager_df["Name"]))
    team_stats_df.insert(3, "ManagerName", team_stats_df["Manager"].map(manager_id_to_name))

    # Concatenamos partidos con información del partido
    player_stats_df = player_stats_df.merge(match_df, on=["Match", "Team"], how="inner")
    player_stats_df["Date"] = pd.to_datetime(player_stats_df["Date"])
    player_stats_df = player_stats_df.sort_values(["Team", "Player", "Date"]).reset_index(drop=True)
    player_stats_df["Date"] = player_stats_df["Date"].dt.strftime("%d/%m/%Y")

    return team_stats_df, player_stats_df

# --------------------------------------------------------------------------------------
# AÑADIMOS PARTIDOS A JUGADORES Y A EQUIPOS
# --------------------------------------------------------------------------------------
def add_matches(match_df: pd.DataFrame, player_stats_df: pd.DataFrame, team_stats_df: pd.DataFrame, team_df: pd.DataFrame, manager_df: pd.DataFrame, player_dict: dict, team_dict: dict) -> Tuple[dict, dict]:

    team_stats_df, player_stats_df = get_player_and_team_matches_to_look(match_df=match_df.copy(), player_stats_df=player_stats_df.copy(), team_stats_df=team_stats_df.copy(), team_df=team_df.copy(), manager_df=manager_df.copy())

    # Obtención de los partidos de un equipo
    def get_single_team_matches(team_stats_df: pd.DataFrame, team_id: str, min_matches: int = 5) -> dict:

        # Filtrado por equipo
        df = team_stats_df[team_stats_df["Team"] == team_id].copy()
        df = df.drop(columns="Team")

        if len(df) < min_matches:
            return None

        # Columnas anidadas
        match_info_cols = ["League", "Date", "HomeAway", "Score", "ScoreDifference", "Result", "Elo", "EloDifference", "Formation"]
        manager_cols = ["Manager", "ManagerName"]
        opponent_cols = ["Opponent", "OpponentName", "OpponentAbb", "OpponentScore", "OpponentElo"]

        # El resto (todo lo que no es id, info ni anidado) son stats del equipo
        fixed_cols = ["Match"] + match_info_cols + manager_cols + opponent_cols
        team_stats_cols = [c for c in df.columns if c not in fixed_cols]

        matches = {}
        for _, row in df.iterrows():
            d = row.to_dict()
            match_dict = {"ID": d["Match"],
                        "Info": {col: d[col] for col in match_info_cols},
                        "Manager": {"Manager": d["Manager"], "Name": d["ManagerName"]},
                        "Opponent": {"Opponent": d["Opponent"], "Name": d["OpponentName"], "Abb": d["OpponentAbb"], "Score": d["OpponentScore"], "Elo": d["OpponentElo"]},
                        "Stats": {col: d[col] for col in team_stats_cols}}
            matches[d["Match"]] = match_dict

        return matches

    # Obtención de los partidos de un jugador
    def get_single_player_matches(player_stats_df: pd.DataFrame, player_id: str, team_id: str, min_matches: int = 5) -> dict:
        
        # Columnas de información (siempre)
        match_info_cols = ["League", "Date", "HomeAway", "Score", "ScoreDifference", "Result", "Elo", "EloDifference", "ShirtNumber", "Position", "MinutesPlayed", "Rating"]

        # Bloques temáticos reutilizables
        POSSESSION = ["Touches", "Passes", "AccuratePasses", "PassAccuracy", "PassesPerTouch", "PossessionLost", "PossessionLossRate", "UnsuccessfulTouches", "UnsuccessfulTouchRate", "OwnHalfPassAccuracy", "OppositionHalfPassAccuracy", "OppositionHalfPassShare", "ProgressiveFieldTilt", "PassPercDirForward", "LongBalls", "AccurateLongBalls", "LongBallAccuracy", "LongBallShare"]
        CREATION = ["KeyPasses", "KeyPassesPerPass", "ExpectedAssists", "ExpectedAssistsPerKeyPass", "BigChancesCreated", "GoalAssists", "AssistConversion"]
        CROSSING = ["Crosses", "AccurateCrosses", "CrossAccuracy", "CrossShare"]
        DRIBBLING = ["Contests", "ContestsWon", "ContestWinRate", "Dispossessed", "DispossessedRate", "WasFouled", "WasFouledRate"]
        SHOOTING = ["TotalShots", "ShotsOnTarget", "ShotAccuracy", "ShotsOnTargetRate", "Goals", "ExpectedGoals", "ExpectedGoalsPerShot", "ExpectedGoalsOnTargetPerShotOnTarget", "GoalConversion", "GoalsPerShotOnTarget", "GoalsMinusxG", "GoalsMinusxGOT", "BigChancesMissed", "BigChanceMissRate", "HitWoodworkRate", "OffsideRate"]
        AERIAL = ["AerialWon", "AerialLost", "AerialWinRate"]
        DEFENDING = ["DefensiveActions", "DefensiveActionSuccess", "Tackles", "TacklesWon", "TackleAccuracy", "Interceptions", "InterceptionShare", "Clearances", "ClearanceShare", "OutfielderBlocks", "BlockShare", "BallRecoveries", "BallRecoveryRate", "DuelsWon", "DuelsLost", "DuelWinRate", "LastManTackles", "ErrorsLeadToShot", "ErrorsLeadToShotRate", "ErrorsLeadToGoal", "ErrorsLeadToGoalRate", "ClearanceOffLine", "ClearanceOffLineRate"]
        DISCIPLINE = ["Fouls", "CardsPerFoul", "YellowCards", "PenaltyConceded", "PenaltyConcededRate"]
        GK_PASSING = ["Touches", "Passes", "AccuratePasses", "PassAccuracy", "PassesPerTouch", "OwnHalfPassAccuracy", "OppositionHalfPassShare", "ProgressiveFieldTilt", "LongBalls", "AccurateLongBalls", "LongBallAccuracy", "LongBallShare"]
        GK_KEEPING = ["Saves", "SaveRate", "SavedShotsInsideBox", "SavedShotsInsideBoxRate","GoalsConceded", "GoalsPrevented", "GoalsPreventedDiff", "CleanSheets", "KeeperSweeperActions", "AccurateKeeperSweeperActions", "KeeperSweeperAccuracy", "HighClaims", "HighClaimRate", "CrossesNotClaimed", "CrossesNotClaimedRate", "Punches", "PunchRate", "GoalKicks", "GoalKicksRate", "PenaltyFaced", "PenaltySaves", "PenaltySaveRate", "PenaltyGoalsConceded", "PenaltyGoalConcededRate", "ErrorsLeadToShot", "ErrorsLeadToShotRate", "ErrorsLeadToGoal", "ErrorsLeadToGoalRate"]

        # Diccionario final: posición -> columnas
        COLUMNS_BY_POSITION = {"GK": GK_PASSING + GK_KEEPING, "CB": POSSESSION + AERIAL + DEFENDING + DISCIPLINE, "LB": POSSESSION + CROSSING + CREATION + DRIBBLING + AERIAL + DEFENDING + DISCIPLINE, 
                            "RB": POSSESSION + CROSSING + CREATION + DRIBBLING + AERIAL + DEFENDING + DISCIPLINE, "DM": POSSESSION + CREATION + DRIBBLING + AERIAL + DEFENDING + DISCIPLINE,
                            "AM": POSSESSION + CREATION + DRIBBLING + SHOOTING + DEFENDING + DISCIPLINE, "LW": POSSESSION + DRIBBLING + CROSSING + CREATION + SHOOTING + DEFENDING,
                            "RW": POSSESSION + DRIBBLING + CROSSING + CREATION + SHOOTING + DEFENDING, "ST": POSSESSION + CREATION + DRIBBLING + SHOOTING + AERIAL + DEFENDING}

        # Selección del dataframe
        df = player_stats_df[(player_stats_df["Player"] == player_id) & (player_stats_df["Team"] == team_id)].copy()
        df = df.drop(columns=["Team", "Player"])

        if len(df) < min_matches:
            return None

        matches = {}
        for _, row in df.iterrows():
            d = row.to_dict()
            match_dict = {"ID": d["Match"], "Info": {col: d[col] for col in match_info_cols},
                        "Opponent": {"Opponent": d["Opponent"], "Name": d["OpponentName"], "Abb": d["OpponentAbb"], "Score": d["OpponentScore"], "Elo": d["OpponentElo"]},
                        "Stats": {col: d[col] for col in COLUMNS_BY_POSITION[d["Position"]]}}
            matches[d["Match"]] = match_dict

        return matches
    
    # Añadimos partidos al equipo
    new_team_dict = team_dict.copy()
    for team_id, team_info in new_team_dict.items():
        try:
            team_matches = get_single_team_matches(team_stats_df=team_stats_df, team_id=team_id)
        except:
            team_matches = None
        if team_matches is not None:
            team_info["Matches"] = clean_json_values(team_matches)

    # Añadimos partidos al jugador
    new_player_dict = player_dict.copy()
    for player_id, player_info in new_player_dict.items():
        try:
            player_matches = get_single_player_matches(player_stats_df=player_stats_df, player_id=player_id, team_id=player_info.get("Team", {}).get("ID", None))
        except:
            player_matches = None
        if player_matches is not None:
            player_info["Matches"] = clean_json_values(player_matches)

    return new_team_dict, new_player_dict

# --------------------------------------------------------------------------------------
# DICCIONARIO CON LOS PERCENTILES DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def calculate_players_percentiles(players_dict: dict, player_df: pd.DataFrame, agg_season: pd.DataFrame, min_minutes: int = 300) -> dict:

    from scipy.stats import percentileofscore

    negative_cols = ["PossessionLostPer90", "PossessionLossRate", "UnsuccessfulTouchRate", "AerialLostPer90", "DispossessedPer90",
                    "DispossessedRate", "GoalsConcededPer90", "CrossesNotClaimedRate", "PenaltyGoalConcededRate", "ErrorsLeadToShotRate",
                    "ErrorsLeadToGoalRate", "FoulsPer90", "CardsPerFoul", "YellowCardsPer90", "PenaltyConcededRate", "BigChancesMissedPer90",
                    "BigChanceMissRate", "HitWoodworkRate", "OffsideRate"]

    # Selección solo de aquellos jugadores en nuestros datos y con un mínimo de minutos
    agg_season = agg_season[agg_season["Player"].isin(players_dict.keys())]
    agg_season = agg_season[agg_season["MinutesPlayed"]>= min_minutes]

    # Diccionario con la posición principal del jugador
    player_pos_dict = dict(zip(player_df["ID"], player_df["FirstPos"]))
    agg_season["Position"] = agg_season["Player"].map(player_pos_dict)

    # Diccionario con el nombre del jugador
    player_name_dict = dict(zip(player_df["ID"], player_df["Name"]))
    agg_season["Name"] = agg_season["Player"].map(player_name_dict)
    cols = agg_season.columns.tolist()
    cols.insert(1, cols.pop(cols.index("Name")))
    agg_season = agg_season[cols]

    # Subset de posiciones
    pos_dict = {}
    for pos in ["GK", "LB", "CB", "RB", "DM", "AM", "LW", "RW", "ST"]:

        # Buscamos dataframes
        pos_df = agg_season[agg_season["Position"] == pos]
        pos_counted_stats_df = pos_df[["Player", "Name"] + counted_stats_list]
        pos_agg_stats_df = pos_df[["Player", "Name"] + position_stats_dict.get(pos)]

        # Calculo de porcentiles por stats agregadas
        metric_cols = [col for col in pos_agg_stats_df.columns if col not in ["Player", "Name"]]
        perc_df = pos_agg_stats_df.copy()
        for col in metric_cols:
            values = perc_df[col]
            if col in negative_cols:
                perc_df[col] = values.rank(pct=True, ascending=False) * 100
            else:
                perc_df[col] = values.rank(pct=True, ascending=True) * 100
        perc_df[metric_cols] = perc_df[metric_cols].round(1)

        # Transformación a diccionarios
        pos_counted_stats_df = pos_counted_stats_df.set_index("Player", drop=False)
        metrics_dict = pos_counted_stats_df.to_dict(orient="index")
        perc_df = perc_df.set_index("Player", drop=False)
        perc_dict = perc_df.to_dict(orient="index")

        # # Añadimos al diccionario
        pos_dict[pos] = {"Metrics": metrics_dict,
                        "Percentiles": perc_dict}

    # Guardado del diccionario
    safe_json_dump(data=pos_dict, path=os.path.join(GOLD_DATA_PATH, "player_stats_comparison.json"))

    return pos_dict

# --------------------------------------------------------------------------------------
# DICCIONARIO CON LOS PERCENTILES DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def calculate_teams_percentiles(teams_dict: dict, team_df: pd.DataFrame, agg_season: pd.DataFrame, min_matches: int = 5) -> dict:

    from scipy.stats import percentileofscore

    # Selección de aquellas stats de los equipos que se encuentran en nuestros datos y mínimo de partidos
    agg_season = agg_season[(agg_season["Team"].isin(teams_dict.keys())) & (agg_season["Matches"] >= min_matches)]

    # Columnas de métricas y de porcentiles
    metrics = ["ExpectedGoalsPer90", "GoalsPer90", "TotalShotsPer90", "ShotsOnTargetPer90", "BigChancesCreatedPer90", "BigChanceConversion", "FinalThirdEntriesPer90", "TouchesInOppBoxPer90",
            "KeyPassesPer90", "ExpectedAssistsPer90", "BallPossession", "ProgressiveFieldTilt", "PassAccuracy", "LongBallShare", "CrossesPer90", "CrossAccuracy", "TacklesPer90", "InterceptionsPer90",
            "DuelWinRate", "AerialWinRate", "GoalsConcededPer90"]
    radar_cols = ["GoalsPer90", "ExpectedGoalsPer90", "TotalShotsPer90", "ShotsOnTargetPer90", "ShotAccuracy", "GoalConversion", "BigChanceConversion", "TouchesInOppBoxPer90", "KeyPassesPer90", 
                "ExpectedAssistsPer90", "BigChancesCreatedPer90", "FinalThirdEntriesPer90", "CrossesPer90", "CrossAccuracy", "ProgressiveFieldTilt", "FinalThirdEfficiency", "BallPossession", 
                "PassAccuracy", "PassesPer90", "OppositionHalfPassAccuracy", "OppositionHalfPassShare", "LongBallAccuracy", "BallPossessionPerPass", "PossessionLossRate", "TacklesPer90", 
                "InterceptionsPer90", "BallRecoveriesPer90", "ClearancesPer90", "DuelWinRate", "AerialWinRate", "DefensiveActionSuccess", "ChallengesLostRate", "SaveRate", "SavedShotsInsideBoxRate", 
                "GoalsPreventedPer90", "CleanSheets", "HighClaimRate", "KeeperSweeperAccuracy", "PenaltySaveRate", "GoalsConcededPer90"]

    # Añadimos el nombre del equipo
    agg_season["Name"] = agg_season["Team"].map(dict(zip(team_df["ID"], team_df["Name"])))

    # Creación de dos dataframes para cada tipo
    metrics_df = agg_season[["Team", "Name"]+metrics]
    radar_df = agg_season[["Team", "Name"]+radar_cols]

    # Columnas negativas
    negative_cols = ["PossessionLossRate", "ChallengesLostRate", "GoalsConcededPer90"]

    # Calculo de percentil
    metric_cols = [col for col in radar_df.columns if col not in ["Team", "Name"]]
    perc_df = radar_df.copy()
    for col in metric_cols:
        values = perc_df[col]
        if col in negative_cols:
            perc_df[col] = values.rank(pct=True, ascending=False) * 100
        else:
            perc_df[col] = values.rank(pct=True, ascending=True) * 100
    perc_df[metric_cols] = perc_df[metric_cols].round(1)


    # Transformación a diccionarios
    metrics_df = metrics_df.set_index("Team", drop=False)
    metrics_dict = metrics_df.to_dict(orient="index")
    perc_df = perc_df.set_index("Team", drop=False)
    perc_dict = perc_df.to_dict(orient="index")

    final_dict = clean_json_values({"Metrics": metrics_dict, "Percentiles": perc_dict})
    safe_json_dump(data=final_dict, path=os.path.join(GOLD_DATA_PATH, "team_stats_comparison.json"))

    return final_dict

# --------------------------------------------------------------------------------------
# UPLOAD DE LA INFORMACIÓN
# --------------------------------------------------------------------------------------
def upload_information_to_cloudflare(print_info: bool = True) -> None:

    entities_path = os.path.join(GOLD_DATA_PATH, "entities")
    images_path = os.path.join(GOLD_DATA_PATH, "images")

    # Subimos el JSON de información de manager, player y team
    l = r2_upl.upload(path=os.path.join(GOLD_DATA_PATH, "player.json"), folder="info")
    l = r2_upl.upload(path=os.path.join(GOLD_DATA_PATH, "team.json"), folder="info")
    l = r2_upl.upload(path=os.path.join(GOLD_DATA_PATH, "manager.json"), folder="info")
    l = r2_upl.upload(path=os.path.join(GOLD_DATA_PATH, "player_stats_comparison.json"), folder="info")
    l = r2_upl.upload(path=os.path.join(GOLD_DATA_PATH, "team_stats_comparison.json"), folder="info")

    # Subido de entidades - jugadores
    if print_info:
        print("     1. Uploading entities - players                                 ")
        i = 1
        total = len(os.listdir(os.path.join(entities_path, "player")))
    for player in os.listdir(os.path.join(entities_path, "player")):
        l = r2_upl.upload(path=os.path.join(entities_path, "player", player), folder="entities/player")
        if print_info:
            print(f"         [{i}/{total}] Upgraded info of player {player.split('.')[0]}                ", flush=True, end="\r")
            i += 1

    # Subido de entidades - equipos
    if print_info:
        print("     2. Uploading entities - teams                                 ")
        i = 1
        total = len(os.listdir(os.path.join(entities_path, "team")))
    for team in os.listdir(os.path.join(entities_path, "team")):
        l = r2_upl.upload(path=os.path.join(entities_path, "team", team), folder="entities/team")
        if print_info:
            print(f"         [{i}/{total}] Upgraded info of team {team.split('.')[0]}                ", flush=True, end="\r")
            i += 1

    # Subido de entidades - managers
    if print_info:
        print("     3. Uploading entities - managers                                 ")
        i = 1
        total = len(os.listdir(os.path.join(entities_path, "manager")))
    for manager in os.listdir(os.path.join(entities_path, "manager")):
        l = r2_upl.upload(path=os.path.join(entities_path, "manager", manager), folder="entities/manager")
        if print_info:
            print(f"         [{i}/{total}] Upgraded info of manager {manager.split('.')[0]}                ", flush=True, end="\r")
            i += 1

    # Subido de imagenes - jugadores
    if print_info:
        print("     4. Uploading images - players                                 ")
        i = 1
        total = len(os.listdir(os.path.join(images_path, "player")))
    for player in os.listdir(os.path.join(images_path, "player")):
        l = r2_upl.upload(path=os.path.join(images_path, "player", player), folder="images/player")
        if print_info:
            print(f"         [{i}/{total}] Upgraded image of player {player.split('.')[0]}                ", flush=True, end="\r")
            i += 1

    # Subido de imagenes - equipos
    if print_info:
        print("     5. Uploading images - teams                                 ")
        i = 1
        total = len(os.listdir(os.path.join(images_path, "team")))
    for team in os.listdir(os.path.join(images_path, "team")):
        l = r2_upl.upload(path=os.path.join(images_path, "team", team), folder="images/team")
        if print_info:
            print(f"         [{i}/{total}] Upgraded image of team {team.split('.')[0]}                ", flush=True, end="\r")
            i += 1

    # Subido de imagenes - managers
    if print_info:
        print("     6. Uploading images - managers                                 ")
        i = 1
        total = len(os.listdir(os.path.join(images_path, "manager")))
    for manager in os.listdir(os.path.join(images_path, "manager")):
        l = r2_upl.upload(path=os.path.join(images_path, "manager", manager), folder="images/manager")
        if print_info:
            print(f"         [{i}/{total}] Upgraded image of manager {manager.split('.')[0]}                ", flush=True, end="\r")
            i += 1

# --------------------------------------------------------------------------------------
# FUNCIÓN MAIN
# --------------------------------------------------------------------------------------
def main(next_step: bool = False, print_info: bool = True) -> None:

    start_time = time.time()

    if print_info:
        print(f"Starting the gold processing of all the information.")

    # Paths de output
    manager_path = os.path.join(GOLD_DATA_PATH, "manager.json")
    player_path = os.path.join(GOLD_DATA_PATH, "player.json")
    team_path = os.path.join(GOLD_DATA_PATH, "team.json")

    if (not os.path.exists(manager_path)) and (not os.path.exists(player_path)) and (not os.path.exists(team_path)):

        # Búsqueda de los diccionarios iniciales
        manager_dict, player_dict, team_dict = get_principal_dicts(match_df=MATCH.copy(), manager_df=MANAGER.copy(), player_df=PLAYER.copy(), team_df=TEAM.copy())

        if print_info:
            print(f"    1. First dicts obtained.")

        # Mejoramos el diccionario de equipos y de jugadores añadiendo plantillas, onces iniciales, o estadísticas
        team_dict = update_teams_dict(team_dict=team_dict, players_info_df=PLAYER.copy(), match_info_df=MATCH.copy(), player_stats_df=PLAYER_STATS.copy(), team_stats_df=TEAM_STATS.copy(), team_agg_stats=AGG_TEAM_SEASON.copy())
        player_dict = update_players_dict(player_dict=player_dict, agg_stats_player=AGG_PLAYER_SEASON.copy())

        if print_info:
            print(f"    2. Player and team data upgrading.")


        # Añadimos mapa de pases y mapa de tiros a los equipos
        team_dict, player_dict = add_passes_and_shots(player_dict=player_dict, team_dict=team_dict, matches_df=MATCH.copy(), shots_df=SHOT_MAP.copy(), passes_df=PASS_MAP.copy())

        if print_info:
            print(f"    3. Shots and passes aded.")

        # Añadimos jugadores y equipos similares (solo entre los que tenemos a nuestros datos)
        team_dict, player_dict = add_similars(team_dict=team_dict, player_dict=player_dict, match_df=MATCH.copy(), agg_team=AGG_TEAM_SEASON.copy(), player_stats=PLAYER_STATS.copy(), player_info=PLAYER.copy())

        if print_info:
            print(f"    4. Similar players and teams added.")

        # Añadimos partidos
        team_dict, player_dict = add_matches(team_dict=team_dict, player_dict=player_dict, match_df=MATCH.copy(), player_stats_df=PLAYER_STATS.copy(), team_stats_df=TEAM_STATS.copy(), team_df=TEAM.copy(), manager_df=MANAGER.copy())

        if print_info:
            print(f"    5. Matches added.")


        # Añadimos la adaptabilidad de los jugadores
        team_dict = add_players_adaptability(team_dict=team_dict, player_df=PLAYER.copy())

        if print_info:
            print(f"    5. Players' adaptability added.")

        # Guardado
        safe_json_dump(data=clean_json_values(manager_dict), path=manager_path)
        safe_json_dump(data=clean_json_values(player_dict), path=player_path)
        safe_json_dump(data=clean_json_values(team_dict), path=team_path)

    else:
        manager_dict = json_to_dict(manager_path)
        player_dict = json_to_dict(player_path)
        team_dict = json_to_dict(team_path)

    # Càlculo de percentiles
    if next_step:
        print("A")
        players_perc_dict = calculate_players_percentiles(players_dict=player_dict, player_df=PLAYER.copy(), agg_season=AGG_PLAYER_SEASON.copy())
        team_perc_dict = calculate_teams_percentiles(teams_dict=team_dict, team_df=TEAM.copy(), agg_season=AGG_TEAM_SEASON.copy())

    # Partimos entidades
    if next_step:
        part_entities(entity_dict=manager_dict, entity="manager")
        part_entities(entity_dict=player_dict, entity="player")
        part_entities(entity_dict=team_dict, entity="team")

    # Transferencia de imagenes
    if next_step:
        ima_transf.main_image_transfer(manager_dict=manager_dict, player_dict=player_dict, team_dict=team_dict, print_info=print_info)

    # Guardado de datos en cloudflare
    if next_step:
        upload_information_to_cloudflare(print_info=print_info)

    if print_info:
        print(f"Finished the gold processing part of all the information {elapsed_time_str(start_time=start_time)}.")

