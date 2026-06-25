import pandas as pd
import os
import numpy as np
from typing import Tuple
import gold.similarity_score as sim
from sklearn.metrics.pairwise import cosine_similarity

# Configuración
from use.config import DATA_PATH, UTILS_DIR
from use.functions import elapsed_time_str, need_to_upload

SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")

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

# Computamos las matrices de similitud
TEAM_SIM_MATRIX = sim.proc_teams_sim_matrix(matches_info_df=MATCH.copy(), team_season_agg_stats=AGG_TEAM_SEASON.copy())
PLAYER_SIM_MATRIX_GK, PLAYER_SIM_MATRIX_DF, PLAYER_SIM_MATRIX_MD, PLAYER_SIM_MATRIX_ST = sim.main_proc_data_similarity(match_info_df=MATCH.copy(), player_stats_df=PLAYER_STATS, player_info_df=PLAYER.copy())

# OBTENCIÓN DE TODOS LOS DATOS
def obtain_all_data() -> dict:

    return_dict = {}

    # Añadimos datos al diccionario
    return_dict["CorrelationGK"] = PLAYER_SIM_MATRIX_GK
    return_dict["CorrelationDF"] = PLAYER_SIM_MATRIX_DF
    return_dict["CorrelationMD"] = PLAYER_SIM_MATRIX_MD
    return_dict["CorrelationFW"] = PLAYER_SIM_MATRIX_ST
    return_dict["CorrelationTeam"] = TEAM_SIM_MATRIX

    # Obtención de las estadísticas de los partidos de la temporada
    matches_to_look = MATCH[MATCH["Season"].astype(str) == "2526"]["ID"].unique().tolist()
    player_stats = PLAYER_STATS[PLAYER_STATS["Match"].isin(matches_to_look)]
    team_stats = TEAM_STATS[TEAM_STATS["Match"].isin(matches_to_look)]

    # Añadimos formaciones
    team_match_formation = team_stats[["Match", "Team", "Formation"]]
    player_stats = player_stats.merge(team_match_formation, on=["Match", "Team"], how="inner")

    # Lista de formaciones posibles por equipo y por jugador
    player_formations_dict = (player_stats.groupby("Player")["Formation"].agg(lambda x: list(x.unique())).to_dict())
    team_formations_dict = (team_stats.groupby("Team")["Formation"].agg(lambda x: list(x.unique())).to_dict())

    # Añadimos competición a los datos por equipo y por jugador
    season_matches = MATCH[MATCH["Season"].astype(str) == "2526"]
    matches_tourn_dict = dict(zip(season_matches["ID"], season_matches["League"]))
    player_stats["League"] = player_stats["Match"].map(matches_tourn_dict)
    team_stats["League"] = team_stats["Match"].map(matches_tourn_dict)

    # Lista de competiciones en la que ha jugado un equipo y un jugador
    player_tournaments_dict = (player_stats.groupby("Player")["League"].agg(lambda x: list(x.unique())).to_dict())
    team_tournaments_dict = (team_stats.groupby("Team")["League"].agg(lambda x: list(x.unique())).to_dict())

    # Añadimos datos al diccionario
    return_dict["PlayerFormations"] = player_formations_dict
    return_dict["TeamFormations"] = team_formations_dict
    return_dict["PlayerTournaments"] = player_tournaments_dict
    return_dict["TeamTournaments"] = team_tournaments_dict

    min_matches = 10         # Partidos mínimos
    min_minutes = 500        # Minutos mínimos

    metrics = ["TouchesPer90", "PassesPer90", "AccuratePassesPer90", "PassAccuracy", "OppositionHalfPassesPer90", "AccurateOppositionHalfPassesPer90", "OppositionHalfPassAccuracy",
              "LongBallsPer90", "AccurateLongBallsPer90", "LongBallAccuracy", "ProgressiveFieldTilt", "PossessionLostPer90", "DispossessedPer90", "UnsuccessfulTouchesPer90",
              "KeyPassesPer90", "ExpectedAssistsPer90", "GoalAssistsPer90", "BigChancesCreatedPer90", "CrossesPer90", "AccurateCrossesPer90", "CrossAccuracy", "ContestsPer90", 
              "ContestsWonPer90", "ContestWinRate", "TotalShotsPer90", "ShotsOnTargetPer90", "ShotAccuracy", "ExpectedGoalsPer90", "ExpectedGoalsPerShot", "GoalsPer90", 
              "GoalConversion", "BigChancesMissedPer90", "OffsidesPer90", "TacklesPer90", "TacklesWonPer90", "TackleAccuracy", "InterceptionsPer90", "ClearancesPer90",
              "OutfielderBlocksPer90", "BallRecoveriesPer90", "DefensiveActionsPer90", "DuelsWonPer90", "DuelWinRate", "AerialWonPer90", "AerialWinRate", "ErrorsLeadToShotPer90",
              "FoulsPer90", "WasFouledPer90", "YellowCardsPer90", "SavesPer90", "SaveRate", "GoalsConcededPer90", "GoalsPreventedPer90", "HighClaimsPer90", "CrossesNotClaimedPer90", 
              "KeeperSweeperActionsPer90", "KeeperSweeperAccuracy", "PenaltySavesPer90", "PenaltySaveRate", "CleanSheets"]

    # Obtención del dataframe de porcentiles por equipo
    team_percentiles = AGG_TEAM_SEASON.copy()
    team_percentiles = team_percentiles[team_percentiles["Matches"] >= min_matches].set_index("Team")[metrics].fillna(0)
    team_percentiles = team_percentiles.rank(pct=True)

    # Obtención del dataframde porcentiles por jugador
    player_percentiles = AGG_PLAYER_SEASON.copy()
    player_percentiles = player_percentiles[player_percentiles["MinutesPlayed"] >= min_minutes].set_index("Player")[metrics].fillna(0)

    # Asegurarse de que las columnas están alineadas
    common_cols = player_percentiles.columns.intersection(team_percentiles.columns)
    X_players = player_percentiles[common_cols].fillna(0)
    X_teams = team_percentiles[common_cols].fillna(0)

    # Similaridad jugador-equipo
    similarity_matrix = cosine_similarity(X_players, X_teams)
    similarity_df = pd.DataFrame(similarity_matrix, index=player_percentiles.index, columns=team_percentiles.index)
    return_dict["SimilarityPlayerTeam"] = similarity_df

    return return_dict

# Obtención de la similitud entre dos plantillas
def get_squads_similarity(dict_all_data: dict, player_id: str, act_team_squad: pd.DataFrame, new_team_squad: pd.DataFrame, exclude_player: bool = True) -> float:

    # Obtención de similitud entre dos jugadores
    def get_players_similarity(corr_gk: pd.DataFrame, corr_df: pd.DataFrame, corr_mf: pd.DataFrame, corr_fw: pd.DataFrame, p1: str, p2: str) -> float:
        if p1 in corr_gk.columns and p2 in corr_gk.columns:
            return float(corr_gk[p1][p2])
        elif p1 in corr_df.columns and p2 in corr_df.columns:
            return float(corr_df[p1][p2])
        elif p1 in corr_mf.columns and p2 in corr_mf.columns:
            return float(corr_mf[p1][p2])
        elif p1 in corr_fw.columns and p2 in corr_fw.columns:
            return float(corr_fw[p1][p2])
        else:
            return None

    # Dataframes de correlación
    corr_gk = dict_all_data.get("CorrelationGK")
    corr_df = dict_all_data.get("CorrelationDF")
    corr_mf = dict_all_data.get("CorrelationMD")
    corr_fw = dict_all_data.get("CorrelationFW")

    # Obtenemos una lista con todas las similitudes
    all_sim_scores = []
    for act_team_player_id in act_team_squad["ID"].unique().tolist():
        if exclude_player:
            if act_team_player_id != player_id:
                for new_team_player_id in new_team_squad["ID"].unique().tolist():
                    similarity = get_players_similarity(corr_gk=corr_gk, corr_df=corr_df, corr_mf=corr_mf, corr_fw=corr_fw, p1=act_team_player_id, p2=new_team_player_id)
                    if similarity:
                        all_sim_scores.append(similarity)
        else:
            for new_team_player_id in new_team_squad["ID"].unique().tolist():
                similarity = get_players_similarity(corr_gk=corr_gk, corr_df=corr_df, corr_mf=corr_mf, corr_fw=corr_fw, p1=act_team_player_id, p2=new_team_player_id)
                if similarity:
                    all_sim_scores.append(similarity)

    # Media de similitud
    mean_squads_similarity = sum(all_sim_scores) / len(all_sim_scores)
    return mean_squads_similarity

# Obtener la similiud de mapa de pases
def get_passes_similarity(player_id: str, list_team_ids: list) -> float:

    def obtain_heatmap(list_pairs: list, normalize: bool = True) -> np.ndarray:
        x = np.array([p[0] for p in list_pairs])
        y = np.array([p[1] for p in list_pairs])
        heatmap, _, _ = np.histogram2d(x, y, bins=(24, 16), range=[[0, 100], [0, 100]])

        if normalize and heatmap.sum() > 0:
            heatmap = heatmap / heatmap.sum()

        return heatmap

    def correlate_heatmaps(heatmap_a: np.ndarray, heatmap_b: np.ndarray) -> float:
        if heatmap_a.sum() == 0 or heatmap_b.sum() == 0:
            return np.nan

        corr = np.corrcoef(heatmap_a.flatten(), heatmap_b.flatten())[0, 1]
        return corr

    # Mapa de pases
    pass_map_positions = PASS_MAP[["Player", "IniX", "IniY"]]

    # Obtenemos pases del jugador y pases de los jugadores de la misma posición del nuevo equipo
    player_pass_map = pass_map_positions[pass_map_positions["Player"] == player_id]
    team_pass_map = pass_map_positions[pass_map_positions["Player"].isin(list_team_ids)]

    # Lista de pares
    heatmap_player = obtain_heatmap(list_pairs=list(zip(player_pass_map["IniX"], player_pass_map["IniY"])))
    heatmap_team = obtain_heatmap(list_pairs=list(zip(team_pass_map["IniX"], team_pass_map["IniY"])))

    # Obtenemos correlación
    return float(correlate_heatmaps(heatmap_a=heatmap_player, heatmap_b=heatmap_team))

# Función principal para obtener las medidas para obtener la suitability de un jugador en un equipo
def get_player_team_similarity_measurements(dict_all_data: dict, team_id: str, player_id: str) -> dict:

    # Obtenemos equipo actual, y plantilla del equipo actual y nuevo equipo
    act_player_team = PLAYER[PLAYER["ID"] == player_id]["Team"].unique().tolist()[0]
    act_team_squad = PLAYER[PLAYER["Team"] == act_player_team]
    new_team_squad = PLAYER[PLAYER["Team"] == team_id]

    # Correlación entre los dos equipos y plantillas (la correlación entre plantillas no tiene en cuenta el jugador)
    teams_correlation = float(dict_all_data.get("CorrelationTeam")[team_id][act_player_team])
    squads_correlation = get_squads_similarity(dict_all_data=dict_all_data, player_id=player_id, act_team_squad=act_team_squad, new_team_squad=new_team_squad)

    # Grupos de formaciones
    formation_group = {"4-2-3-1": "A", "4-1-4-1": "A", "4-3-2-1": "A", "4-4-1-1": "A", "4-5-1": "A", "4-4-2": "B", "4-2-2-2": "B", "4-1-3-2": "B", "4-3-1-2": "B", "4-3-3": "C", "3-4-3": "D", "3-2-4-1": "D", "3-3-3-1": "D",
                       "3-3-1-3": "D", "3-4-2-1": "D", "3-4-1-2": "D", "3-1-4-2": "D", "3-5-2": "E", "3-5-1-1": "E", "5-3-2": "E", "5-4-1": "E"}

    # Obtención de formaciones que ha jugado el jugador y el nuevo equipo
    player_posible_formations = set([formation_group[c] for c in dict_all_data["PlayerFormations"].get(player_id, [])])
    new_team_posible_formations = set([formation_group[c] for c in dict_all_data["TeamFormations"].get(team_id, [])])
    formation_match = int(bool(player_posible_formations & new_team_posible_formations))

    # Liga y grupo de liga para comparar
    competition_group = {"champions_league": "A", "premier_league": "A", "la_liga": "A", "bundesliga": "A", "serie_a": "A", "ligue_1": "A", "europa_league": "B", "liga_portugal": "B", "eredivise": "B", "super_lig": "B", "first_division_a": "B",
                        "championship": "B", "conference_league": "C", "copa_del_rey": "C", "la_liga_hypermotion": "C", "swiss_super_league": "C", "superligaen": "C", "saudi_pro_league": "C", "copa_libertadores": "D", "conmebol_sudamericana": "D",
                        "serie_a_brazil": "D", "liga_profesional": "D", "liga_mx": "D", "major_league_soccer": "D", "eliteserien": "E", "allvenskan": "E"}

    # Obtención de las competiciones que ha jugado el jugador y el nuevo equipo
    player_tournaments = set([competition_group[c] for c in dict_all_data["PlayerTournaments"].get(player_id, [])])
    new_team_tournaments = set([competition_group[c] for c in dict_all_data["TeamTournaments"].get(team_id, [])])
    tournaments_match = int(bool(player_tournaments & new_team_tournaments))

    # Booleano que mira si en el equipo hay un jugador del país del propio jugador
    player_country = PLAYER[PLAYER["ID"] == player_id]["Country"].unique().tolist()[0]
    new_team_countries = new_team_squad["Country"].unique().tolist()                        # Pondera 0.5 si es país que hay algun jugador
    new_team_country = TEAM[TEAM["ID"] == team_id]["Country"].unique().tolist()[0]          # Pondera 1 si es el país del equipo
    country_match = 1 if player_country == new_team_country else 0.5 if player_country in new_team_countries else 0

    # Lista de posiciones del jugador, y jugadores en sus mismas posiciones en el nuevo equipo
    player_positions = positions = [p for p in PLAYER.loc[PLAYER["ID"] == player_id, ["FirstPos", "SecondPos", "ThirdPos"]].values.flatten().tolist() if pd.notna(p)]
    same_position_new_team_players = new_team_squad[(new_team_squad["FirstPos"].isin(player_positions)) | (new_team_squad["SecondPos"].isin(player_positions)) | (new_team_squad["ThirdPos"].isin(player_positions))]
    same_position_mean_similarity = get_squads_similarity(dict_all_data=dict_all_data, player_id=player_id, act_team_squad=PLAYER.loc[PLAYER["ID"] == player_id], new_team_squad=same_position_new_team_players, exclude_player=False)

    # Fecha del jugador y media de jugadores del equipo
    act_player_timestamp = float(pd.to_datetime(PLAYER.loc[PLAYER["ID"] == player_id, "DateBirth"].iloc[0], format="%d/%m/%Y").timestamp())
    new_team_mean_timestamp = float(pd.to_datetime(PLAYER.loc[PLAYER["Team"] == team_id, "DateBirth"], format="%d/%m/%Y", errors="coerce").astype("int64").mean() / 1e9)

    # Elo de equipos
    act_team_elo = float(TEAM.loc[TEAM["ID"] == act_player_team, "EloRating"].iloc[0])
    new_team_elo = float(TEAM.loc[TEAM["ID"] == team_id, "EloRating"].iloc[0])

    # Rating del jugador y media del equipo
    player_rating = int(PLAYER.loc[PLAYER["ID"] == player_id, "Rating"].iloc[0]) 
    player_potential = int(PLAYER.loc[PLAYER["ID"] == player_id, "Potential"].iloc[0])
    new_team_rating = float(PLAYER.loc[PLAYER["Team"] == team_id, "Rating"].mean())
    new_team_potential = float(PLAYER.loc[PLAYER["Team"] == team_id, "Potential"].mean())

    # Obtención de la similitud con el mapa de pases
    pass_map_sim = get_passes_similarity(player_id=player_id, list_team_ids=same_position_new_team_players["ID"].unique().tolist())

    # Obtenemos la similaridad enttre el equipo y el jugador
    player_team_sim_dict = dict_all_data.get("SimilarityPlayerTeam")
    player_team_sim = float(player_team_sim_dict[team_id][player_id])

    # Diccionario de output
    output_dict = {"Player": player_id,
                  "Team": team_id,
                  "TeamsCorrelation": teams_correlation,
                  "SquadsCorrelation": squads_correlation, 
                  "FormationsMatch": formation_match,
                  "TournamentsMatch": tournaments_match,
                  "CountryMatch": country_match,
                  "SamePosCorrelation": same_position_mean_similarity,
                  "PassesCorrelation": pass_map_sim,
                  "TimestampDiff": new_team_mean_timestamp - act_player_timestamp,
                  "EloRatingDiff": new_team_elo - act_team_elo,
                  "RatingDiff": new_team_rating - player_rating,
                  "PotentialDiff": new_team_potential - player_potential,
                  "StatsCorrelation": player_team_sim}
    
    return output_dict

# Obtención de los jugadores a consultar
def get_part_players(min_matches: int = 10) -> list:

    # Selección de los jugadores
    matches_to_look = MATCH[MATCH["Season"].astype(str)=="2526"]["ID"].unique().tolist()                                    # Jugadores que hayan jugado durante la temporada
    players_with_stats = PLAYER_STATS[PLAYER_STATS["Match"].isin(matches_to_look)]["Player"].unique().tolist()              # Jugadores con estadísticas
    players_agg_stats = AGG_PLAYER_SEASON[AGG_PLAYER_SEASON["Player"].isin(players_with_stats)]                             # Estadísticas agregadas de jugadores
    players_min_matches = players_agg_stats[players_agg_stats["Matches"] >= min_matches]["Player"].unique().tolist()        # Mínimo de partidos

    # Selección de jugadores final
    players_to_look_df = PLAYER[PLAYER["ID"].isin(players_min_matches)].dropna(subset="Team").dropna(subset="Rating").dropna(subset="Potential")
    players_to_look_df = players_to_look_df.sort_values(by=["Rating", "Potential"], ascending=False).head(2000)                 # Selección de los 2000 mejores jugadores del mundo
    players_to_look = players_to_look_df["ID"].unique().tolist()

    return players_to_look

# Obtención del dataframe de similaridad de un jugador a un club
def get_team_players_adaptability(team_num: int, total_teams: int, team_id: str, players_to_look: list, dict_all_data: dict, print_info: bool = True) -> pd.DataFrame:

    # Filtramos para sacar el equipo
    players_ids = PLAYER[(PLAYER["Team"] != team_id) & (PLAYER["ID"].isin(players_to_look))]["ID"].unique().tolist()
    total_players = len(players_ids)
    i = 1

    # Nombre del equipo
    team_name = dict(zip(TEAM["ID"], TEAM["Name"])).get(team_id)

    list_info = []

    # Para cada jugador, concatenamos info
    for player_id in players_ids:
        if print_info:
            print(f"    Processing players adaptability for {team_name} [Team: {team_num}/{total_teams} - Player {i}/{total_players}]", flush=True, end="\r")
            i += 1

        try:
            measures = get_player_team_similarity_measurements(dict_all_data=dict_all_data, team_id=team_id, player_id=player_id)
            list_info.append(measures)
        except:
            continue

    # Buscamos la matriz de correlación del equipo
    correlation_df = pd.DataFrame(list_info)

    # Obtención de un score
    def player_match_score(df: pd.DataFrame, weights=None) -> pd.DataFrame:

        df = df.copy()
        corr_cols = ["TeamsCorrelation","SquadsCorrelation","SamePosCorrelation","PassesCorrelation"]      # 0-100
        bin_cols  = ["FormationsMatch","TournamentsMatch","CountryMatch","StatsCorrelation"]               # ya 0-1
        diff_cols = ["TimestampDiff","EloRatingDiff","RatingDiff","PotentialDiff"]                         # cerca de 0 = mejor

        score = pd.DataFrame(index=df.index)

        for c in corr_cols:
            score[c] = (df[c] / 100).clip(0, 1)

        for c in bin_cols:
            score[c] = df[c].clip(0, 1)

        for c in diff_cols:
            a = df[c].abs()
            rng = a.max() - a.min()
            if pd.isna(rng) or rng == 0:      # columna constante o toda NaN
                score[c] = pd.NA              # no aporta info -> se neutraliza abajo
            else:
                score[c] = 1 - (a - a.min()) / rng   # diff pequeño -> cerca de 1

        # NaN sueltos (p.ej. PassesCorrelation, TimestampDiff) -> neutro
        score = score.fillna(0.5)

        # pesos (default: todos igual). Sube/baja segun lo que te fies de cada medida
        if weights is None:
            weights = {c: 1.0 for c in score.columns}
        w = pd.Series(weights).reindex(score.columns).fillna(0)

        df["MatchScore"] = (score * w).sum(axis=1) / w.sum()
        return df

    # Normalización a estrellas
    def to_stars_minmax(df, col="MatchScore") -> pd.DataFrame:
        df = df.copy()
        s = df[col]
        lo, hi = s.min(), s.max()
        scaled = (s - lo) / (hi - lo)          # 0-1
        stars = (scaled * 9 + 1) / 2           # lleva a 0.5 - 5
        df["Stars"] = (stars * 2).round() / 2  # redondea al 0.5 mas cercano
        return df

    # Obtención del dataframe ponderado de jugadores con más adaptabilidad
    weights = {"TeamsCorrelation": 1.0, "SquadsCorrelation": 1.0, "EloRatingDiff": 1.0,
            "StatsCorrelation": 1.0, "RatingDiff": 1.0, "SamePosCorrelation": 0.8,
            "PassesCorrelation": 0.8, "PotentialDiff": 0.7, "FormationsMatch": 0.3,
            "TournamentsMatch": 0.2, "CountryMatch": 0.2, "TimestampDiff": 0.1}
    players_weighted = player_match_score(df=correlation_df, weights=weights)[["Player", "MatchScore"]]
    players_stars = to_stars_minmax(df=players_weighted)        # Aplicamos estrellas
    players_stars.columns = ["Player", "Score", "Stars"]        # Cambio de columnas

    return players_stars.sort_values(by=["Stars", "Score"], ascending=False)

# Función principal
def main(print_info: bool = True, only_saved: bool = False) -> dict:

    TEAMS_DATA_ADAPT_PATH = os.path.join(SILVER_DATA_PATH, "players_adaptability")
    os.makedirs(TEAMS_DATA_ADAPT_PATH, exist_ok=True)

    dict_output = {}

    # Si solo queremos lo ya guardado, leemos los CSV existentes y devolvemos
    if only_saved:
        for file in os.listdir(TEAMS_DATA_ADAPT_PATH):
            if file.endswith(".csv"):
                team_id = file.split(".")[0]
                team_adapt_path = os.path.join(TEAMS_DATA_ADAPT_PATH, file)
                dict_output[team_id] = pd.read_csv(team_adapt_path, sep=";")
        return dict_output

    # Obtenemos jugadores a mirar y diccionario con información
    players_to_look = get_part_players()
    dict_all_data = obtain_all_data()

    # Obtención de aquellos equipos a consultar (cinco grandes ligas)
    teams_tournaments = dict_all_data.get("TeamTournaments")
    target_leagues = {"la_liga", "premier_league", "serie_a", "ligue_1", "bundesliga", "eredivise", "liga_portugal", "super_lig", "championship"}
    selected_teams = [team_id for team_id, leagues in teams_tournaments.items() if any(league in target_leagues for league in leagues)]
    selected_teams = TEAM[TEAM["ID"].isin(selected_teams)].sort_values(by="EloRating", ascending=False).head(100)["ID"].unique().tolist()

    if print_info:
        print("Starting the processing of players adaptability                                                                        ")
    team_i = 1
    total_teams = len(selected_teams)

    # Para cada equipo
    for team_id in selected_teams:
        try:
            team_adapt_path = os.path.join(TEAMS_DATA_ADAPT_PATH, f"{team_id}.csv")
            if os.path.exists(team_adapt_path) and not need_to_upload(team_adapt_path, total_days=10):
                team_adapt_df = pd.read_csv(team_adapt_path, sep=";")
                dict_output[team_id] = team_adapt_df
                team_i += 1
            else:
                team_adapt_df = get_team_players_adaptability(team_num=team_i, total_teams=total_teams, team_id=team_id, players_to_look=players_to_look, dict_all_data=dict_all_data)
                dict_output[team_id] = team_adapt_df
                team_adapt_df.to_csv(team_adapt_path, index=False, sep=";")
                team_i += 1
        except:
            continue

    return dict_output