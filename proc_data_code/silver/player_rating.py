import pandas as pd
import os
import numpy as np
from datetime import datetime
from typing import Tuple
import warnings

warnings.filterwarnings("ignore", message="Parsing dates in %d/%m/%Y format when dayfirst=False")

# Configuración
from use.config import DATA_PATH

# --------------------------------------------------------------------------------------
# PREPARACIÓN DE DATOS DE PARTIDOS
# --------------------------------------------------------------------------------------
def prepare_match_data(match_dataframe: pd.DataFrame) -> pd.DataFrame:

    match_df = match_dataframe.copy()

    # Añadimos peso de tournament
    tournament_k = {"la_liga": 40, "premier_league": 40, "bundesliga": 40, "serie_a": 40, "ligue_1": 40, "champions_league": 50, "europa_league": 30, "copa_del_rey": 30, "la_liga_hypermotion": 20,
                    "championship": 20, "eredivise": 30, "liga_portugal": 30, "conference_league": 30, "copa_libertadores": 20, "liga_mx": 20, "serie_a_brazil": 20, "liga_profesional": 20,
                    "first_division_a": 20, "major_league_soccer": 20, "saudi_pro_league": 20, "super_lig": 20, "superligaen": 20, "swiss_super_league": 20, "allvenskan": 20, "eliteserien": 20,
                    "conmebol_sudamericana": 20}
    match_df["TournamentWeight"] = match_df["League"].map(tournament_k)

    # Selección datos por equipo local y visitante
    match_df_home = match_df[["ID", "HomeTeam", "TournamentWeight", "HomeScore", "AwayScore", "HomeElo", "AwayElo"]]
    match_df_away = match_df[["ID", "AwayTeam", "TournamentWeight", "AwayScore", "HomeScore", "AwayElo", "HomeElo"]]

    # Nombres de columnas y concatenación
    match_df_home.columns = ["Match", "Team", "TournWeight", "Score", "OppScore", "Elo", "OppElo"]
    match_df_away.columns = ["Match", "Team", "TournWeight", "Score", "OppScore", "Elo", "OppElo"]
    match_df = pd.concat([match_df_home, match_df_away])

    # Añadimos diferencia de goles y si es victoria, empate o derrota
    match_df["ScoreDiff"] = match_df["Score"] - match_df["OppScore"]
    match_df["Result"] = np.where(match_df["ScoreDiff"] > 0, 1, np.where(match_df["ScoreDiff"] < 0, -1, 0))             # Victoria 1, derrota -1, empate 0

    return match_df

# --------------------------------------------------------------------------------------
# PREPARACIÓN DE DATOS DE JUGADORES (ESTADISTICAS)
# --------------------------------------------------------------------------------------
def prepare_stats_player(stats_dataframe: pd.DataFrame, match_dataframe: pd.DataFrame) -> dict:

    # Obtenemos los datos 
    stats_df = stats_dataframe.copy()
    match_df = prepare_match_data(match_dataframe=match_dataframe.copy())

    # Merge
    df = match_df.merge(stats_df, on=["Match", "Team"], how="inner")

    # Borramos columnas y sacamos valores nulos en jugador
    df = df.drop(columns=["ShirtNumber", "Team"]).dropna(subset="Player")

    # Diccionario para añadir informacion
    output_dict = {}

    # Para cada posición, buscamos jugadores
    for pos in ["GK", "FB", "CB", "DM", "AM", "WG", "ST"]:
        if pos == "FB":
            pos_df = df[df["Position"].isin(["RB", "LB"])].drop(columns="Position")
        elif pos == "WG":
            pos_df = df[df["Position"].isin(["RW", "LW"])].drop(columns="Position")
        else:
            pos_df = df[df["Position"]==pos].drop(columns="Position")

        # Ponemos jugador al principio e indexamos al diccionario
        pos_df = pos_df[["Player"] + [col for col in pos_df.columns if col != "Player"]]
        output_dict[pos] = pos_df.sort_values(by=["Player"]).reset_index(drop=True)

    return output_dict

# --------------------------------------------------------------------------------------
# NORMALIZACIÓN DE COLUMNAS - a partir de una row de un dataframe, y valores máximos y mínimos, normaliza la columna
# --------------------------------------------------------------------------------------
def normalize_column(series: pd.Series, min_value: float, max_value: float) -> pd.Series:

    # Evitar división por 0
    if max_value == min_value:
        return pd.Series(np.zeros(len(series)), index=series.index)
    normalized = (series - min_value) / (max_value - min_value)

    # Limitar entre 0 y 1
    normalized = normalized.clip(0, 1)

    return normalized

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE PORTEROS
# --------------------------------------------------------------------------------------
def get_gk_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["GK"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","SaveRate","GoalsPrevented","SavedShotsInsideBox","HighClaimRate","KeeperSweeperAccuracy",
                   "CrossesNotClaimed","Punches","PassAccuracy","LongBallAccuracy","KeeperSweeperActions","PenaltySaveRate","PenaltyConceded","ErrorsLeadToShot","ErrorsLeadToGoal",
                   "Goals","GoalAssists","YellowCards","RedCards"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["GoalsPrevented"] = normalize_column(series=stats_df["GoalsPrevented"], min_value=-3, max_value=3)
    stats_df["SavedShotsInsideBox"] = normalize_column(series=stats_df["SavedShotsInsideBox"], min_value=0, max_value=12)
    stats_df["CrossesNotClaimed"] = normalize_column(series=stats_df["CrossesNotClaimed"], min_value=0, max_value=3)
    stats_df["Punches"] = normalize_column(series=stats_df["Punches"], min_value=0, max_value=8)
    stats_df["KeeperSweeperActions"] = normalize_column(series=stats_df["KeeperSweeperActions"], min_value=0, max_value=8)
    stats_df["PenaltySaveRate"] = normalize_column(series=stats_df["PenaltySaveRate"], min_value=0, max_value=1.2)
    stats_df["PenaltyConceded"] = normalize_column(series=stats_df["PenaltyConceded"], min_value=0, max_value=1.2)
    stats_df["ErrorsLeadToShot"] = normalize_column(series=stats_df["ErrorsLeadToShot"], min_value=0, max_value=2)
    stats_df["ErrorsLeadToGoal"] = normalize_column(series=stats_df["ErrorsLeadToGoal"], min_value=0, max_value=1)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.75 * stats_df["SaveRate"] + 0.55 * stats_df["GoalsPrevented"] + 0.35 * stats_df["SavedShotsInsideBox"] +
                            0.45 * stats_df["HighClaimRate"] + 0.30 * stats_df["KeeperSweeperAccuracy"] + 0.20 * stats_df["Punches"] +
                            0.40 * stats_df["PassAccuracy"] + 0.25 * stats_df["LongBallAccuracy"] + 0.15 * stats_df["KeeperSweeperActions"] +
                            0.60 * stats_df["PenaltySaveRate"] +
                            0.30 * stats_df["Goals"] + 0.25 * stats_df["GoalAssists"])

    # Penalizaciones
    stats_df["Negative"] = (-0.40 * stats_df["CrossesNotClaimed"] - 0.30 * stats_df["PenaltyConceded"] - 0.60 * stats_df["ErrorsLeadToShot"] - 1.20 * stats_df["ErrorsLeadToGoal"] -
                            1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste contextual
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) *
                          stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE LATERALES
# --------------------------------------------------------------------------------------
def get_fb_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["FB"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","TackleAccuracy","Interceptions","DuelWinRate","BallRecoveries","PassAccuracy","OwnGoals",
                   "OppositionHalfPassAccuracy","ProgressiveFieldTilt","CrossAccuracy","KeyPasses","GoalAssists","WasFouledRate","YellowCards","RedCards","ErrorsLeadToGoal",
                   "Goals"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["Interceptions"] = normalize_column(series=stats_df["Interceptions"], min_value=0, max_value=8)
    stats_df["BallRecoveries"] = normalize_column(series=stats_df["BallRecoveries"], min_value=0, max_value=12)
    stats_df["ProgressiveFieldTilt"] = normalize_column(series=stats_df["ProgressiveFieldTilt"], min_value=0, max_value=10)
    stats_df["KeyPasses"] = normalize_column(series=stats_df["KeyPasses"], min_value=0, max_value=5)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)
    stats_df["ErrorsLeadToGoal"] = normalize_column(series=stats_df["ErrorsLeadToGoal"], min_value=0, max_value=2)
    stats_df["OwnGoals"] = normalize_column(series=stats_df["OwnGoals"], min_value=0, max_value=2)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.48 * stats_df["TackleAccuracy"] + 0.32 * stats_df["Interceptions"] + 0.32 * stats_df["DuelWinRate"] + 0.28 * stats_df["BallRecoveries"] +
                            0.48 * stats_df["PassAccuracy"] + 0.40 * stats_df["OppositionHalfPassAccuracy"] + 0.32 * stats_df["ProgressiveFieldTilt"] +
                            0.40 * stats_df["CrossAccuracy"] + 0.32 * stats_df["KeyPasses"] + 0.28 * stats_df["GoalAssists"] +
                            0.40 * stats_df["WasFouledRate"] +
                            0.30 * stats_df["Goals"])

    # Penalizaciones
    stats_df["Negative"] = (-3.00 * stats_df["ErrorsLeadToGoal"] - 2.00 * stats_df["OwnGoals"] -
                            1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste contextual
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) *
                          stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE DEFENSAS CENTRALES
# --------------------------------------------------------------------------------------
def get_cb_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["CB"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","DuelWinRate","AerialWinRate","TackleAccuracy","Interceptions","Clearances","OutfielderBlocks",
                   "LastManTackles","PassAccuracy","LongBallAccuracy","OwnHalfPassAccuracy","ErrorsLeadToShot","ErrorsLeadToGoal","OwnGoals","ClearanceOffLine",
                   "Goals","GoalAssists","YellowCards","RedCards"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["Interceptions"] = normalize_column(series=stats_df["Interceptions"], min_value=0, max_value=8)
    stats_df["Clearances"] = normalize_column(series=stats_df["Clearances"], min_value=0, max_value=8)
    stats_df["OutfielderBlocks"] = normalize_column(series=stats_df["OutfielderBlocks"], min_value=0, max_value=5)
    stats_df["LastManTackles"] = normalize_column(series=stats_df["LastManTackles"], min_value=0, max_value=2)
    stats_df["ErrorsLeadToShot"] = normalize_column(series=stats_df["ErrorsLeadToShot"], min_value=0, max_value=2)
    stats_df["ErrorsLeadToGoal"] = normalize_column(series=stats_df["ErrorsLeadToGoal"], min_value=0, max_value=1)
    stats_df["OwnGoals"] = normalize_column(series=stats_df["OwnGoals"], min_value=0, max_value=2)
    stats_df["ClearanceOffLine"] = normalize_column(series=stats_df["ClearanceOffLine"], min_value=0, max_value=2)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.48 * stats_df["DuelWinRate"] + 0.48 * stats_df["AerialWinRate"] + 0.32 * stats_df["TackleAccuracy"] + 0.32 * stats_df["Interceptions"] +
                            0.40 * stats_df["Clearances"] + 0.32 * stats_df["OutfielderBlocks"] + 0.28 * stats_df["LastManTackles"] +
                            0.48 * stats_df["PassAccuracy"] + 0.32 * stats_df["LongBallAccuracy"] + 0.20 * stats_df["OwnHalfPassAccuracy"] +
                            1.50 * stats_df["ClearanceOffLine"] +
                            0.30 * stats_df["Goals"] + 0.25 * stats_df["GoalAssists"])

    # Penalizaciones
    stats_df["Negative"] = (-1.50 * stats_df["ErrorsLeadToShot"] - 4.00 * stats_df["ErrorsLeadToGoal"] - 2.00 * stats_df["OwnGoals"] -
                            1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste contextual
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) *
                          stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE MEDIOCENTROS DEFENSIVOS
# --------------------------------------------------------------------------------------
def get_dm_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["DM"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","Interceptions","BallRecoveries","TackleAccuracy","DefensiveActionSuccess",
                   "PassAccuracy","OwnHalfPassAccuracy","PossessionLossRate","ProgressiveFieldTilt","LongBallAccuracy","KeyPasses","ExpectedAssists",
                   "DuelWinRate","AerialWinRate","YellowCards","RedCards","Goals","GoalAssists"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["Interceptions"] = normalize_column(series=stats_df["Interceptions"], min_value=0, max_value=8)
    stats_df["BallRecoveries"] = normalize_column(series=stats_df["BallRecoveries"], min_value=0, max_value=12)
    stats_df["ProgressiveFieldTilt"] = normalize_column(series=stats_df["ProgressiveFieldTilt"], min_value=0, max_value=10)
    stats_df["KeyPasses"] = normalize_column(series=stats_df["KeyPasses"], min_value=0, max_value=5)
    stats_df["ExpectedAssists"] = normalize_column(series=stats_df["ExpectedAssists"], min_value=0, max_value=1)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.48 * stats_df["Interceptions"] + 0.40 * stats_df["BallRecoveries"] + 0.32 * stats_df["TackleAccuracy"] + 0.20 * stats_df["DefensiveActionSuccess"] +
                            0.48 * stats_df["PassAccuracy"] + 0.32 * stats_df["OwnHalfPassAccuracy"] - 0.32 * stats_df["PossessionLossRate"] + 0.32 * stats_df["ProgressiveFieldTilt"] + 0.16 * stats_df["LongBallAccuracy"] +
                            0.32 * stats_df["KeyPasses"] + 0.28 * stats_df["ExpectedAssists"] +
                            0.24 * stats_df["DuelWinRate"] + 0.16 * stats_df["AerialWinRate"] +
                            0.30 * stats_df["Goals"] + 0.25 * stats_df["GoalAssists"])

    # Penalizaciones
    stats_df["Negative"] = (-1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste contextual
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) *
                          stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE MEDIOCENTROS OFENSIVOS
# --------------------------------------------------------------------------------------
def get_am_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["AM"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","KeyPasses","ExpectedAssists","GoalAssists","BigChancesCreated",
                   "Goals","ExpectedGoals","ShotsOnTarget","BigChancesMissed","PassAccuracy","OppositionHalfPassAccuracy","PossessionLossRate",
                   "Touches","ContestWinRate","YellowCards","RedCards"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["KeyPasses"] = normalize_column(series=stats_df["KeyPasses"], min_value=0, max_value=5)
    stats_df["ExpectedAssists"] = normalize_column(series=stats_df["ExpectedAssists"], min_value=0, max_value=1)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["BigChancesCreated"] = normalize_column(series=stats_df["BigChancesCreated"], min_value=0, max_value=4)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["ExpectedGoals"] = normalize_column(series=stats_df["ExpectedGoals"], min_value=0, max_value=1.5)
    stats_df["ShotsOnTarget"] = normalize_column(series=stats_df["ShotsOnTarget"], min_value=0, max_value=5)
    stats_df["BigChancesMissed"] = normalize_column(series=stats_df["BigChancesMissed"], min_value=0, max_value=3)
    stats_df["Touches"] = normalize_column(series=stats_df["Touches"], min_value=0, max_value=100)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.48 * stats_df["KeyPasses"] + 0.40 * stats_df["ExpectedAssists"] + 0.40 * stats_df["GoalAssists"] + 0.32 * stats_df["BigChancesCreated"] +              # Creación de juego: max +1.60
                            0.48 * stats_df["Goals"] + 0.32 * stats_df["ExpectedGoals"] + 0.24 * stats_df["ShotsOnTarget"] +                                                             # Contribución al gol: max +1.04
                            0.40 * stats_df["PassAccuracy"] + 0.32 * stats_df["OppositionHalfPassAccuracy"] - 0.08 * stats_df["PossessionLossRate"] +                                    # Circulación: max +0.72
                            0.20 * stats_df["Touches"] + 0.20 * stats_df["ContestWinRate"])                                                                                              # Participación: max +0.40

    # Penalizaciones
    stats_df["Negative"] = (-0.16 * stats_df["BigChancesMissed"] - 1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste por nivel del rival - ajuste +-5% por cada 400 puntos de diferencia
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Cálculo del rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) * stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    # Selección de las columnas a mostrar
    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE EXTREMOS
# --------------------------------------------------------------------------------------
def get_wg_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["WG"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","CrossAccuracy","ContestWinRate","AccurateCrosses",
                   "Goals","GoalAssists","ExpectedGoals","ExpectedAssists","KeyPasses","BigChancesCreated",
                   "BallRecoveries","WasFouled","DefensiveActions","PassAccuracy","PossessionLossRate",
                   "OppositionHalfPassShare","YellowCards","RedCards"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["AccurateCrosses"] = normalize_column(series=stats_df["AccurateCrosses"], min_value=0, max_value=8)
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["ExpectedGoals"] = normalize_column(series=stats_df["ExpectedGoals"], min_value=0, max_value=1.5)
    stats_df["ExpectedAssists"] = normalize_column(series=stats_df["ExpectedAssists"], min_value=0, max_value=1.5)
    stats_df["KeyPasses"] = normalize_column(series=stats_df["KeyPasses"], min_value=0, max_value=5)
    stats_df["BigChancesCreated"] = normalize_column(series=stats_df["BigChancesCreated"], min_value=0, max_value=5)
    stats_df["BallRecoveries"] = normalize_column(series=stats_df["BallRecoveries"], min_value=0, max_value=12)
    stats_df["WasFouled"] = normalize_column(series=stats_df["WasFouled"], min_value=0, max_value=8)
    stats_df["DefensiveActions"] = normalize_column(series=stats_df["DefensiveActions"], min_value=0, max_value=10)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.48 * stats_df["CrossAccuracy"] + 0.40 * stats_df["ContestWinRate"] + 0.32 * stats_df["AccurateCrosses"] +                                      # Desborde y centros: max +1.20
                            0.48 * stats_df["Goals"] + 0.40 * stats_df["GoalAssists"] + 0.32 * (stats_df["ExpectedGoals"] + stats_df["ExpectedAssists"]) + 0.20 * stats_df["KeyPasses"] +   # Contribución al gol: max +1.40
                            0.32 * stats_df["BallRecoveries"] + 0.24 * stats_df["WasFouled"] + 0.24 * stats_df["DefensiveActions"] +                                          # Presión y recuperación: max +0.80
                            0.32 * stats_df["PassAccuracy"] - 0.20 * stats_df["PossessionLossRate"] + 0.12 * stats_df["OppositionHalfPassShare"] +                          # Mantenimiento balón: max +0.24
                            1.00 * stats_df["BigChancesCreated"])                                                                                                               # Bonus creativo

    # Penalizaciones
    stats_df["Negative"] = (-1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste por nivel del rival - ajuste +-5% por cada 400 puntos de diferencia
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Cálculo del rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) * stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    # Selección de las columnas a mostrar
    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# DEFINE RATINGS DE DELANTEROS
# --------------------------------------------------------------------------------------
def get_st_ratings(dict_positions_df: dict) -> pd.DataFrame:

    df = dict_positions_df["ST"].copy()

    # Obtenemos estadísticas
    stats_df = df[["Player","Match","Elo","OppElo","ScoreDiff","MinutesPlayed","Goals","ExpectedGoalsOnTarget","ShotAccuracy","BigChancesMissed",
                   "AerialWinRate","DuelWinRate","ContestWinRate","GoalAssists","KeyPasses","BigChancesCreated","BallRecoveries","WasFouled",
                   "HitWoodwork","Offsides","PenaltyMissed","PassAccuracy","YellowCards","RedCards"]]
    stats_df = stats_df.fillna(0)

    # Aplicamos normalización de columnas para aquellas contada
    stats_df["Goals"] = normalize_column(series=stats_df["Goals"], min_value=0, max_value=3)
    stats_df["ExpectedGoalsOnTarget"] = normalize_column(series=stats_df["ExpectedGoalsOnTarget"], min_value=0, max_value=2)
    stats_df["BigChancesMissed"] = normalize_column(series=stats_df["BigChancesMissed"], min_value=0, max_value=3)
    stats_df["GoalAssists"] = normalize_column(series=stats_df["GoalAssists"], min_value=0, max_value=3)
    stats_df["KeyPasses"] = normalize_column(series=stats_df["KeyPasses"], min_value=0, max_value=5)
    stats_df["BigChancesCreated"] = normalize_column(series=stats_df["BigChancesCreated"], min_value=0, max_value=4)
    stats_df["BallRecoveries"] = normalize_column(series=stats_df["BallRecoveries"], min_value=0, max_value=8)
    stats_df["WasFouled"] = normalize_column(series=stats_df["WasFouled"], min_value=0, max_value=6)
    stats_df["HitWoodwork"] = normalize_column(series=stats_df["HitWoodwork"], min_value=0, max_value=2)
    stats_df["Offsides"] = normalize_column(series=stats_df["Offsides"], min_value=0, max_value=5)
    stats_df["PenaltyMissed"] = normalize_column(series=stats_df["PenaltyMissed"], min_value=0, max_value=1)
    stats_df["YellowCards"] = normalize_column(series=stats_df["YellowCards"], min_value=0, max_value=1.5)
    stats_df["RedCards"] = normalize_column(series=stats_df["RedCards"], min_value=0, max_value=1)

    # Rating inicial
    stats_df["InitialRating"] = 6.0

    # Bonus positivo
    stats_df["Positive"] = (0.64 * stats_df["Goals"] + 0.40 * stats_df["ExpectedGoalsOnTarget"] + 0.40 * stats_df["ShotAccuracy"] +                    # Gol y remate: max +1.44
                            0.40 * stats_df["AerialWinRate"] + 0.32 * stats_df["DuelWinRate"] + 0.28 * stats_df["ContestWinRate"] +                   # Juego de pivote: max +1.00
                            0.40 * stats_df["GoalAssists"] + 0.24 * stats_df["KeyPasses"] + 0.16 * stats_df["BigChancesCreated"] +                   # Creación: max +0.80
                            0.20 * stats_df["BallRecoveries"] + 0.20 * stats_df["WasFouled"] +                                                        # Presión: max +0.40
                            0.50 * stats_df["HitWoodwork"] + 0.30 * stats_df["PassAccuracy"])                                                       # Bonus añadido

    # Penalizaciones
    stats_df["Negative"] = (-1.50 * stats_df["BigChancesMissed"] - 0.50 * stats_df["Offsides"] - 2.00 * stats_df["PenaltyMissed"] -
                            1.50 * stats_df["YellowCards"] - 4.00 * stats_df["RedCards"])

    # Ajuste por nivel del rival - ajuste +-5% por cada 400 puntos de diferencia
    stats_df["EloMod"] = 1 + 0.05*((stats_df["OppElo"] - stats_df["Elo"]) / 400)
    stats_df["MinMod"] = (stats_df["MinutesPlayed"] / 60).clip(0.5, 1)
    stats_df["ScoreMod"] = 1 + 0.1*stats_df["ScoreDiff"]

    # Cálculo del rating
    stats_df["Rating"] = ((stats_df["InitialRating"] + stats_df["Positive"] + stats_df["Negative"]).clip(0, 10) * stats_df["EloMod"] * stats_df["MinMod"] * stats_df["ScoreMod"]).clip(0, 10)

    # Selección de las columnas a mostrar
    stats_df = stats_df[["Player", "Match", "Rating"]]

    return stats_df

# --------------------------------------------------------------------------------------
# OBTENCIÓN DEL DATAFRAME DE RATINGS PARA TODOS LOS JUGADORES
# --------------------------------------------------------------------------------------
def get_ratings_df(dict_positions_df: dict) -> pd.DataFrame:

    # Obtenemos los dataframes con los ratings
    gk_df = get_gk_ratings(dict_positions_df=dict_positions_df)
    fb_df = get_fb_ratings(dict_positions_df=dict_positions_df)
    cb_df = get_cb_ratings(dict_positions_df=dict_positions_df)
    dm_df = get_dm_ratings(dict_positions_df=dict_positions_df)
    am_df = get_am_ratings(dict_positions_df=dict_positions_df)
    wg_df = get_wg_ratings(dict_positions_df=dict_positions_df)
    st_df = get_st_ratings(dict_positions_df=dict_positions_df)

    # Append de los dataframes y aplicamos nombre del jugador
    ratings_df = pd.concat([gk_df, fb_df, cb_df, dm_df, am_df, wg_df, st_df], ignore_index=True)
    ratings_df = ratings_df.sort_values(by="Player").reset_index(drop=True)

    return ratings_df

# --------------------------------------------------------------------------------------
# OBTENCIÓN DEL DATAFRAME DE RATINGS PARA TODOS LOS JUGADORES
# --------------------------------------------------------------------------------------
def get_match_rating_df(match_dataframe: pd.DataFrame, ratings_df: pd.DataFrame) -> pd.DataFrame:

    match_df = match_dataframe.copy()

    # Preparación de datos del partido que queremos
    match_data = prepare_match_data(match_dataframe=match_df)           # Usamos la función anterior
    match_data = match_data[["Match", "TournWeight", "Elo"]]            # Seleccionamos métricas de entorno para ponderar según tournament o elo

    # Añadimos la fecha del partido
    match_date_dict = dict(zip(match_df["ID"], match_df["Date"]))
    match_data["Date"] = match_data["Match"].map(match_date_dict)

    # Cruzamos con ratings_df
    match_rating_df = ratings_df.merge(match_data, on="Match", how="left").dropna().sort_values(by="Date")

    # Normalizamos contexto competitivo
    match_rating_df["TournWeightNorm"] = normalize_column(series=match_rating_df["TournWeight"], min_value=20, max_value=50)
    match_rating_df["EloNorm"] = normalize_column(series=match_rating_df["Elo"], min_value=500, max_value=2500)

    # Modificador contextual
    match_rating_df["ContextMod"] = (0.85 + 0.10 * match_rating_df["TournWeightNorm"] + 0.10 * match_rating_df["EloNorm"]).clip(0.85, 1.05)

    # Rating ajustado por contexto competitivo
    match_rating_df["AdjustedRating"] = (match_rating_df["Rating"] * match_rating_df["ContextMod"]).clip(0, 10)

    # Orden final y selección de columnas
    match_rating_df = match_rating_df.sort_values(by=["Player", "Date"]).reset_index(drop=True)
    match_rating_df = match_rating_df[["Player", "Match", "Date", "AdjustedRating"]]

    return match_rating_df

# --------------------------------------------------------------------------------------
# OBTENCIÓN DEL DATAFRAME DE RATINGS DE JUGADORES CADA DOS SEMANAS
# --------------------------------------------------------------------------------------
def biweek_players_ratings(match_rating_df: pd.DataFrame) -> pd.DataFrame:

    df = match_rating_df.copy()

    # Formato fecha
    df["Date"] = pd.to_datetime(df["Date"])

    # Filtramos jugadores que hayan jugado un mínimo de 10 partidos
    players_valid = (df.groupby("Player")["Match"].nunique().loc[lambda x: x >= 10].index)
    df = df[df["Player"].isin(players_valid)].copy()

    # Periodo cada dos semanas
    df["BiWeek"] = df["Date"].dt.to_period("2W-MON")

    # Agrupación cada 2 semanas
    player_biweek_rating_df = (df.groupby(["Player", "BiWeek"]).agg(PLAYED_MATCHES=("Match", "nunique"), mean_rating=("AdjustedRating", "mean")).reset_index())

    # Completar periodos vacíos
    def fill_missing_biweeks(player_df: pd.DataFrame) -> pd.DataFrame:

        player_id = player_df.name
        player_df = player_df.sort_values("BiWeek").copy()

        full_biweek_range = pd.period_range(start=player_df["BiWeek"].min(), end=player_df["BiWeek"].max(), freq="2W-MON")
        player_df = (player_df.set_index("BiWeek").reindex(full_biweek_range))

        player_df.index.name = "BiWeek"
        player_df["Player"] = player_id

        player_df["PLAYED_MATCHES"] = (player_df["PLAYED_MATCHES"].fillna(0).astype(int))
        player_df["mean_rating"] = player_df["mean_rating"].ffill()

        return player_df.reset_index()

    player_biweek_rating_df = (player_biweek_rating_df.groupby("Player", group_keys=False).apply(fill_missing_biweeks).reset_index(drop=True))

    # Conversión del periodo a fecha inicial
    player_biweek_rating_df["BiWeek"] = player_biweek_rating_df["BiWeek"].dt.start_time

    # Redondeo
    player_biweek_rating_df["mean_rating"] = (player_biweek_rating_df["mean_rating"].round(2))

    # Orden final
    player_biweek_rating_df = (player_biweek_rating_df.sort_values(["Player", "BiWeek"]).reset_index(drop=True))

    return player_biweek_rating_df

# --------------------------------------------------------------------------------------
# OBTENCIÓN DEL DATAFRAME CON LA MEDIA DE CADA JUGADOR
# --------------------------------------------------------------------------------------
def obtain_player_value_df(match_data: pd.DataFrame, players_df: pd.DataFrame, player_stats: pd.DataFrame, team_df: pd.DataFrame, biweek_rating_df: pd.DataFrame) -> pd.DataFrame:

    # Obtención del inicio de temporada
    today = datetime.now()
    if today.month >= 9:
        season_year = today.year
    else:
        season_year = today.year - 1
    last_months = pd.Timestamp(f"{season_year}-08-01")

    # Obtención de un diccionario que nos muestra la normalización por 90 de los jugadores
    def obtain_dict_per90(match_data: pd.DataFrame, player_stats: pd.DataFrame, last_months) -> dict:

        # Merged dataframe y selección de columnas
        match_data = match_data.rename(columns={"ID":"Match"})
        merged_df = player_stats.merge(match_data, on="Match", how="inner")
        merged_df = merged_df[["Match", "Player", "MinutesPlayed", "Date"]]

        # Filtrado por fecha
        merged_df["Date"] = pd.to_datetime(merged_df["Date"])
        merged_df = merged_df[merged_df["Date"] >= last_months]

        # Factor por 90 y media por jugador
        merged_df["Per90Factor"] = merged_df["MinutesPlayed"] / 90
        player_per90factor_df = (merged_df.groupby("Player", as_index=False).agg(mean_per90factor=("Per90Factor", "mean")))

        # Diccionario
        dict_per90_factor = dict(zip(player_per90factor_df["Player"], player_per90factor_df["mean_per90factor"]))

        return dict_per90_factor

    # Obtención de un diccionario con el ELO del equipo normalizado
    def obtain_dict_elo(team_df: pd.DataFrame, players_df: pd.DataFrame) -> dict:

        # Obtenemos elo por equipo
        team_df = team_df[["ID", "EloRating"]].copy()

        elo_range = team_df["EloRating"].max() - team_df["EloRating"].min()

        if elo_range == 0:
            team_df["EloRatingNorm"] = 0.5
        else:
            team_df["EloRatingNorm"] = (0.5 + ((team_df["EloRating"] - team_df["EloRating"].min()) / elo_range) * (1 - 0.5))

        # Buscamos jugadores y club y aplicamos equipo
        players_df = players_df[["ID", "Name", "Team"]].copy()
        players_club_df = players_df.merge(team_df, left_on="Team", right_on="ID", how="inner")

        # Return del diccionario
        return dict(zip(players_club_df["ID_x"], players_club_df["EloRatingNorm"]))

    # Diccionario de mapeo según la importancia de los partidos jugados
    def obtain_dict_match_importance(match_data: pd.DataFrame, player_stats: pd.DataFrame, last_months) -> dict:

        # Merged dataframe y selección de columnas
        match_data = match_data.rename(columns={"ID":"Match"})
        merged_df = player_stats.merge(match_data, on="Match", how="inner")
        merged_df = merged_df[["Match", "Player", "MinutesPlayed", "Date", "League"]]

        # Filtrado por fecha
        merged_df["Date"] = pd.to_datetime(merged_df["Date"])
        merged_df = merged_df[merged_df["Date"] >= last_months]

        # Añadimos peso de tournament
        tournament_k = {"la_liga": 40, "premier_league": 40, "bundesliga": 40, "serie_a": 40, "ligue_1": 40, "champions_league": 50, "europa_league": 30,
                        "copa_del_rey": 30, "la_liga_hypermotion": 20, "championship": 20, "eredivise": 30, "liga_portugal": 30, "conference_league": 30,
                        "copa_libertadores": 20, "liga_mx": 20, "serie_a_brazil": 20, "liga_profesional": 20, "first_division_a": 20, "major_league_soccer": 20,
                        "saudi_pro_league": 20, "super_lig": 20, "superligaen": 20, "swiss_super_league": 20, "allvenskan": 20, "eliteserien": 20,
                        "conmebol_sudamericana": 20}
        merged_df["TournamentWeight"] = merged_df["League"].map(tournament_k)

        # Obtenemos métricas por jugador
        player_tournament_weight_df = (merged_df.groupby("Player", as_index=False).agg(MeanTournamentWeight=("TournamentWeight", "mean"),
                                                                                    MaxTournamentWeight=("TournamentWeight", "max"),
                                                                                    NumCompetitions=("League", "nunique"),
                                                                                    MatchesPlayed=("Match", "nunique"),
                                                                                    TotalMinutes=("MinutesPlayed", "sum")))

        # Score bruto: nivel medio * factor diversidad
        player_tournament_weight_df["CompetitionScore"] = (player_tournament_weight_df["MeanTournamentWeight"] * (1 + 0.10 * (player_tournament_weight_df["NumCompetitions"] - 1)))

        # Normalizamos
        min_score = player_tournament_weight_df["CompetitionScore"].min()
        max_score = player_tournament_weight_df["CompetitionScore"].max()
        score_range = max_score - min_score

        if score_range == 0:
            player_tournament_weight_df["NormWeight"] = 0.5
        else:
            player_tournament_weight_df["NormWeight"] = (0.5 + ((player_tournament_weight_df["CompetitionScore"] - min_score) / score_range) * 0.5)

        return dict(zip(player_tournament_weight_df["Player"], player_tournament_weight_df["NormWeight"]))

    # Aplicamos funciones
    dict_per90 = obtain_dict_per90(match_data=match_data, player_stats=player_stats, last_months=last_months)
    dict_elo = obtain_dict_elo(team_df=team_df, players_df=players_df)
    dict_match_imp = obtain_dict_match_importance(match_data=match_data, player_stats=player_stats, last_months=last_months)

    # Obtención del dataframe con el rating medio por jugador
    player_rating_base_df = (biweek_rating_df[biweek_rating_df["BiWeek"] >= last_months].groupby("Player", as_index=False).agg(Rating=("mean_rating", "mean"), Matches=("PLAYED_MATCHES", "sum")))

    # Ajuste bayesiano del rating para evitar sobrevalorar jugadores con pocos partidos
    global_rating = (biweek_rating_df[biweek_rating_df["BiWeek"] >= last_months]["mean_rating"].mean())
    player_rating_base_df["AdjustedRating"] = ((player_rating_base_df["Matches"] * player_rating_base_df["Rating"]) + (8 * global_rating)) / (player_rating_base_df["Matches"] + 8)
    last_rating_by_player_df = player_rating_base_df[["Player", "AdjustedRating"]].copy()
    last_rating_by_player_df.columns = ["Player", "Rating"]

    # Aplicamos normalización del rating por normalización de minutos
    last_rating_by_player_df["Per90Factor"] = last_rating_by_player_df["Player"].map(dict_per90)
    last_rating_by_player_df["EloFactor"] = last_rating_by_player_df["Player"].map(dict_elo)
    last_rating_by_player_df["MatchImpFactor"] = last_rating_by_player_df["Player"].map(dict_match_imp)

    # # Buscamos posición por jugador
    player_pos_dict = dict(zip(players_df["ID"], players_df["FirstPos"]))
    last_rating_by_player_df["Position"] = last_rating_by_player_df["Player"].map(player_pos_dict)
    last_rating_by_player_df = last_rating_by_player_df.dropna(subset="Position")

    # Obtención del dataframe con todos los datos
    player_rating_df = last_rating_by_player_df[["Player","Position","Rating","Per90Factor","EloFactor","MatchImpFactor"]].copy()

    # Cálculo del rating final - normalización inicial
    player_rating_df["RatingNorm"] = player_rating_df["Rating"] / 10
    player_rating_df["MediaRaw"] = (0.65 * player_rating_df["RatingNorm"] + 0.15 * player_rating_df["Per90Factor"] + 0.10 * player_rating_df["EloFactor"] + 0.10 * player_rating_df["MatchImpFactor"])
    player_rating_df["Rating"] = (65 + player_rating_df["MediaRaw"] * (95 - 65)).round(0)

    # Añadimos el nombre del jugador
    player_name_dict = dict(zip(players_df["ID"], players_df["Name"]))
    player_rating_df["Name"] = player_rating_df["Player"].map(player_name_dict)

    # Selección de columnas
    player_rating_df = (player_rating_df[["Player", "Name", "Position", "Rating", "Per90Factor", "EloFactor", "MatchImpFactor"]].sort_values(by="Rating", ascending=False))

    return player_rating_df

# --------------------------------------------------------------------------------------
# OBTENCIÓN DEL DATAFRAME CON EL POTENCIAL DEL JUGADOR
# --------------------------------------------------------------------------------------
def obtain_player_potential_df(player_df: pd.DataFrame, match_data: pd.DataFrame, player_stats:pd.DataFrame, players_value_df: pd.DataFrame) -> pd.DataFrame:

    # Obtención del inicio de temporada
    today = datetime.now()
    if today.month >= 9:
        season_year = today.year
    else:
        season_year = today.year - 1
    last_months = pd.Timestamp(f"{season_year}-08-01")

    # Obtención de la fecha de nacimiento del jugador y transformación a datetime
    player_date_birth = player_df[["ID", "DateBirth"]].dropna()
    player_date_birth["DateBirth"] = pd.to_datetime(player_date_birth["DateBirth"], errors="coerce")
    player_date_birth["Age"] = ((today - player_date_birth["DateBirth"]).dt.days / 365.25)

    # Factor de potencial por edad
    def get_age_potential(age: float) -> float:
        if pd.isna(age):
            return 0.50
        if age <= 18:
            return 1.00
        elif age <= 20:
            return 0.90
        elif age <= 22:
            return 0.80
        elif age <= 24:
            return 0.65
        elif age <= 26:
            return 0.45
        elif age <= 29:
            return 0.25
        elif age <= 31:
            return 0.10
        else:
            return 0.00
        
    player_date_birth["AgePotential"] = player_date_birth["Age"].apply(get_age_potential)

    # Obtención de los minutos jugados por jugador
    def dict_matches_played(match_data: pd.DataFrame, player_stats: pd.DataFrame) -> dict:

        # Merged dataframe y selección de columnas
        match_data = match_data.rename(columns={"ID":"Match"})
        merged_df = player_stats.merge(match_data, on="Match", how="inner")
        merged_df = merged_df[["Match", "Player", "Date"]]

        # Filtrado por fecha
        merged_df["Date"] = pd.to_datetime(merged_df["Date"])
        merged_df = merged_df[merged_df["Date"] >= last_months]

        # Número de partidos jugados por jugador
        player_matches_df = (merged_df.groupby("Player", as_index=False).agg(MatchesPlayed=("Match", "nunique")))

        # Diccionario
        dict_matches_played = dict(zip(player_matches_df["Player"],player_matches_df["MatchesPlayed"]))
        return dict_matches_played

    # Aplicamos los partidos jugados para cada jugador
    players_potential_df = players_value_df.copy()
    players_potential_df["PlayedMatches"] = players_potential_df["Player"].map(dict_matches_played(match_data=match_data, player_stats=player_stats))

    # Factor de muestra: más partidos = más fiabilidad
    players_potential_df["SampleFactor"] = (players_potential_df["PlayedMatches"] / 20).clip(0, 1)

    # Cruzamos para tener el potencial de edad
    player_date_birth = player_date_birth.rename(columns={"ID":"Player"})
    players_potential_df = players_potential_df.merge(player_date_birth, on="Player", how="inner")

    # Normalización de la media actual
    players_potential_df["MediaNorm"] = ((players_potential_df["Rating"] - 65) / (95 - 65)).clip(0, 1)

    # Score bruto de potencial
    players_potential_df["PotentialRaw"] = (0.45 * players_potential_df["MediaNorm"] + 0.25 * players_potential_df["AgePotential"] + 0.10 * players_potential_df["Per90Factor"] + 0.10 * players_potential_df["EloFactor"] +
                                            0.05 * players_potential_df["MatchImpFactor"] + 0.05 * players_potential_df["SampleFactor"])

    # Escala final 65-99
    players_potential_df["Potential"] = (65 + players_potential_df["PotentialRaw"] * (99 - 65)).round(0)

    return players_potential_df.reset_index(drop=True)

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------------------
def main_players_rating(match_df: pd.DataFrame, player_info_df: pd.DataFrame, stats_player_df: pd.DataFrame, team_info_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Borramos columnas de rating y de potencial a los dataframes que vamos a modificar
    if "Rating" in stats_player_df.columns:
        stats_player_df = stats_player_df.drop(columns="Rating")
    if "Rating" in player_info_df.columns and "Potential" in player_info_df.columns:
        player_info_df = player_info_df.drop(columns=["Rating", "Potential"])

    # Preparación de datos
    dict_positions_df = prepare_stats_player(stats_dataframe=stats_player_df.copy(), match_dataframe=match_df.copy())

    # Dataframe con los ratings de los jugadores por partido
    ratings_df = get_ratings_df(dict_positions_df=dict_positions_df)

    # Obtención del match rating de cada jugador
    match_rating_df = get_match_rating_df(match_dataframe=match_df.copy(), ratings_df=ratings_df.copy())

    # Obtención del dataframe agregado cada dos semanas de rating por jugador
    biweek_rating_df = biweek_players_ratings(match_rating_df=match_rating_df.copy())

    # Obtención de la media de los jugadores
    players_value_df = obtain_player_value_df(match_data=match_df.copy(), players_df=player_info_df.copy(), player_stats=stats_player_df.copy(), team_df=team_info_df.copy(), biweek_rating_df=biweek_rating_df)

    # Obtención del potencial de jugadores
    player_potential_df = obtain_player_potential_df(player_df=player_info_df.copy(), match_data=match_df.copy(), player_stats=stats_player_df.copy(), players_value_df=players_value_df)

    # Hacemos merge con los partidos y el rating obtenido para cada jugador en aquel partido
    stats_players_with_rating = stats_player_df.merge(ratings_df.drop_duplicates(subset=["Player", "Match"]), on=["Player", "Match"], how="left")

    # Aplicamos el rating y el potencial a la tabla de datos de información de jugadores - obtenemos diccionarios
    dict_rating = dict(zip(player_potential_df["Player"], player_potential_df["Rating"]))
    dict_potential = dict(zip(player_potential_df["Player"], player_potential_df["Potential"]))

    # Aplicamos diccionarios
    player_info_df["Rating"] = player_info_df["ID"].map(dict_rating)
    player_info_df["Potential"] = player_info_df["ID"].map(dict_potential)

    return stats_players_with_rating, player_info_df