import pandas as pd
import os
import numpy as np
from typing import Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
import warnings
from pandas.errors import PerformanceWarning

warnings.simplefilter(action="ignore", category=PerformanceWarning)

from utils.functions import df_safe_div, json_to_dict
ACT_SEASON = "2526"
UTILS_DIR = r"C:\Users\ASUS\Desktop\V2-TFM\utils"

# Lista para ordenar el dataframe en un futuro
data = json_to_dict(os.path.join(UTILS_DIR, "proc", "gold_proc", "similarity_cols_order.json"))
list_to_order_df = data["columns_order"]

# --------------------------------------------------------------------------------------
# CREACIÓN DE NUEVAS MÉTRICAS POR JUGADORES
# --------------------------------------------------------------------------------------
def player_new_metrics(player_stats_df: pd.DataFrame) -> pd.DataFrame:

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

    # Precisión de pase por zona
    df["PassPercZoneBack"] = df_safe_div(df["PassAccZoneBack"], df["PassZoneBack"])
    df["PassPercZoneCenter"] = df_safe_div(df["PassAccZoneCenter"], df["PassZoneCenter"])
    df["PassPercZoneLeft"] = df_safe_div(df["PassAccZoneLeft"], df["PassZoneLeft"])
    df["PassPercZoneRight"] = df_safe_div(df["PassAccZoneRight"], df["PassZoneRight"])

    # Distribución de pases por zona
    total_zone_passes = (df["PassZoneBack"] + df["PassZoneCenter"] + df["PassZoneLeft"] + df["PassZoneRight"])
    df["PassShareZoneBack"] = df_safe_div(df["PassZoneBack"], total_zone_passes)
    df["PassShareZoneCenter"] = df_safe_div(df["PassZoneCenter"], total_zone_passes)
    df["PassShareZoneLeft"] = df_safe_div(df["PassZoneLeft"], total_zone_passes)
    df["PassShareZoneRight"] = df_safe_div(df["PassZoneRight"], total_zone_passes)

    # Precisión por dirección
    df["PassPercDirBackward"] = df_safe_div(df["PassAccDirBackward"], df["PassDirBackward"])
    df["PassPercDirBackwardLeft"] = df_safe_div(df["PassAccDirBackwardLeft"], df["PassDirBackwardLeft"])
    df["PassPercDirBackwardRight"] = df_safe_div(df["PassAccDirBackwardRight"], df["PassDirBackwardRight"])
    df["PassPercDirForward"] = df_safe_div(df["PassAccDirForward"], df["PassDirForward"])
    df["PassPercDirForwardLeft"] = df_safe_div(df["PassAccDirForwardLeft"], df["PassDirForwardLeft"])
    df["PassPercDirForwardRight"] = df_safe_div(df["PassAccDirForwardRight"], df["PassDirForwardRight"])
    df["PassPercDirLeft"] = df_safe_div(df["PassAccDirLeft"], df["PassDirLeft"])
    df["PassPercDirRight"] = df_safe_div(df["PassAccDirRight"], df["PassDirRight"])

    # Distribución por dirección
    total_dir_passes = (df["PassDirBackward"] + df["PassDirBackwardLeft"] + df["PassDirBackwardRight"] + df["PassDirForward"] + df["PassDirForwardLeft"] + df["PassDirForwardRight"] + df["PassDirLeft"] + df["PassDirRight"])
    df["PassShareDirBackward"] = df_safe_div(df["PassDirBackward"], total_dir_passes)
    df["PassShareDirBackwardLeft"] = df_safe_div(df["PassDirBackwardLeft"], total_dir_passes)
    df["PassShareDirBackwardRight"] = df_safe_div(df["PassDirBackwardRight"], total_dir_passes)
    df["PassShareDirForward"] = df_safe_div(df["PassDirForward"], total_dir_passes)
    df["PassShareDirForwardLeft"] = df_safe_div(df["PassDirForwardLeft"], total_dir_passes)
    df["PassShareDirForwardRight"] = df_safe_div(df["PassDirForwardRight"], total_dir_passes)
    df["PassShareDirLeft"] = df_safe_div(df["PassDirLeft"], total_dir_passes)
    df["PassShareDirRight"] = df_safe_div(df["PassDirRight"], total_dir_passes)
        
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

    # Distribución de resultados
    total_shots = df["MissedShots"] + df["ShotsOnPost"] + df["SavedShots"]
    df["MissedShotRate"] = df_safe_div(df["MissedShots"], total_shots)
    df["PostShotRate"] = df_safe_div(df["ShotsOnPost"], total_shots)
    df["SavedShotRate"] = df_safe_div(df["SavedShots"], total_shots)             

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
    cols_exclude = ["Match","Team","Player","ShirtNumber","Position","PassMeanAngle","PassMeanLength","PassMeanX","PassMeanY","ShotMeanX","ShotMeanY","MeanGoalY","MeanGoalZ","ShotMeanLength",
                    "GoalIniX","GoalIniY","GoalFinalY","GoalFinalZ","GoalMeanLength"]
    per90_cols = df.columns.difference(cols_exclude)
    per90_dict = {f"{col}Per90": df[col] * factor_90 for col in per90_cols}
    df = pd.concat([df, pd.DataFrame(per90_dict)], axis=1)

    return df

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA LA AGREGACIÓN DE DATOS
# --------------------------------------------------------------------------------------
def player_aggregate_data(player_stats_df: pd.DataFrame) -> pd.DataFrame:

    player_agg = player_stats_df.copy()

    # Sacamos columnas de información
    cols_to_drop = [c for c in ["Match", "Team", "Opponent"] if c in player_agg.columns]
    player_agg = player_agg.drop(columns=cols_to_drop)

    # Sacamos columnas per 90
    cols_per90 = [c for c in player_agg.columns if c.endswith("Per90")]
    player_agg = player_agg.drop(columns=cols_per90)

    ratio_cols = ["Match","Team","PassAccuracy","PassesPerTouch","TouchesPerPass","PossessionLossRate","UnsuccessfulTouchRate","DispossessedRate","OwnHalfPassAccuracy","OwnHalfPassShare",
                  "OppositionHalfPassAccuracy","OppositionHalfPassShare","LongBallAccuracy","LongBallShare","KeyPassesPerPass","AssistConversion","ExpectedAssistsPerKeyPass",
                  "ExpectedAssistsPerPass","CrossAccuracy","CrossShare","AccurateCrossShare","BigChanceMissRate","BigChancesPerKeyPass","ShotAccuracy","ShotsOnTargetRate",
                  "ShotsOffTargetRate","BlockedShotRate","GoalConversion","GoalsPerShotOnTarget","ExpectedGoalsPerShot","ExpectedGoalsOnTargetPerShotOnTarget","HitWoodworkRate",
                  "OffsideRate","DuelWinRate","AerialWinRate","ContestWinRate","ChallengesLostRate","TackleAccuracy","DefensiveActionSuccess","InterceptionShare","ClearanceShare",
                  "BlockShare","BallRecoveryRate","LastManTackleRate","ClearanceOffLineRate","ErrorsLeadToShotRate","ErrorsLeadToGoalRate","GoalsConcededPerDefAction","SaveRate",
                  "SavedShotsInsideBoxRate","CrossesNotClaimedRate","HighClaimRate","PunchRate","KeeperSweeperAccuracy","GoalKicksRate","PenaltySaveRate","PenaltyGoalConcededRate",
                  "CardsPerFoul","YellowCardsPerFoul","RedCardsPerFoul","FoulsPerDefAction","WasFouledRate","PenaltyWonRate","PenaltyMissRate","PenaltyConcededRate","OwnGoalRate",
                  "CornersWonRate","CornersLostRate","CornersTakenRate","GoalsMinusxG","GoalsMinusxGOT","GoalsMinusGoalsConceded","ShotsMinusGoals","PassPercZoneBack",
                  "PassPercZoneCenter","PassPercZoneLeft","PassPercZoneRight","PassPercDirBackward","PassPercDirBackwardLeft","PassPercDirBackwardRight","PassPercDirForward",
                  "PassPercDirForwardLeft","PassPercDirForwardRight","PassPercDirLeft","PassPercDirRight","TotalGoals"]
    ratio_cols = [c for c in ratio_cols if c in player_agg.columns]
    player_agg = player_agg.drop(columns=ratio_cols)

    # Añadimos partidos - para sumar
    player_agg["Matches"] = 1 

    # Diccionario de agregaciones
    agg_dict = {}

    for col in player_agg.columns:
        if col == "Player":
            continue
        elif col in ["PassMeanAngle","PassMeanLength","PassMeanX","PassMeanY","ShotMeanX","ShotMeanY","MeanGoalY","MeanGoalZ","ShotMeanLength","GoalIniX","Elo","OppElo",
                     "GoalIniY","GoalFinalY","GoalFinalZ","GoalMeanLength"]:
            agg_dict[col] = "mean"
        else:
            agg_dict[col] = "sum"

    # Agregación
    player_agg_df = player_agg.groupby("Player", as_index=False).agg(agg_dict)

    # Aplicamos la función de crear nuevas métricas al df
    final_df = player_new_metrics(player_stats_df=player_agg_df)

    return final_df

# --------------------------------------------------------------------------------------
# LIMPIEZA DEL DATAFRAME DE AGREGACIÓN DE DATOS
# --------------------------------------------------------------------------------------
def final_agg_df_cleaning(season_player_df: pd.DataFrame, min_minutes: int = 500) -> pd.DataFrame:

    df = season_player_df.copy()

    # Selección de aquellos jugadores con un minutaje mínimo
    df = df[df["MinutesPlayed"] >= min_minutes]

    # Filtrado de información que queremos sí o sí: si el jugador no tiene fecha de nacimiento, altura o pref foot no lo escogeremos
    df = df.dropna(subset=["DateBirth", "Height", "PrefFoot"])

    # Selección de columnas del dataframe final
    df = df[list_to_order_df]

    # Calculamos edad del jugador
    df["DateBirth"] = pd.to_datetime(df["DateBirth"], format="%d/%m/%Y", errors="coerce")
    today = pd.Timestamp.today()
    df.insert(2, "Age", (today - df["DateBirth"]).dt.days // 365)
    df = df.drop(columns="DateBirth")

    # Rol con la posición al lado para evitar duplicaciones
    df["Role"] = df["Position"] + " - " + df["Role"]

    # Posición general
    df.insert(5, "GeneralPos", np.where(df["Position"].isin(["LW","ST","RW"]), "Attacker", np.where(df["Position"].isin(["LB","CB","RB"]), "Defender", np.where(df["Position"].isin(["DM","AM"]), "Midfielder", "Goalkeeper"))))

    # Realizamos un "Fillna" imputando los valores medios POR POSICIÓN
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df.groupby("Position")[num_cols].transform(lambda x: x.fillna(x.mean()))

    # Aplicamos one-hot-encoding para transformar a numericas las columnas categoricas
    cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
    cat_cols = [c for c in cat_cols if c != "Player"]
    df_encoded = pd.get_dummies(df, columns=cat_cols, drop_first=False, dtype=int)

    return df_encoded.set_index("Player")

# --------------------------------------------------------------------------------------
# CREACIÓN DEL DATAFRAME CON INFORMACIÓN Y ESTADÍSTICAS DE LOS JUGADORES
# --------------------------------------------------------------------------------------
def similarity_score_processing(match_info_df: pd.DataFrame, player_stats_df: pd.DataFrame, player_info_df: pd.DataFrame, act_season: str) -> pd.DataFrame:

    # Filtrado de aquellos partidos de la temporada actual - también jugadores que hayan jugado durante aquella temporada
    season_matches = match_info_df[match_info_df["Season"].astype(str) == str(act_season)].reset_index(drop=True)
    season_player_stats = player_stats_df[player_stats_df["Match"].isin(season_matches["ID"].unique().tolist())].reset_index(drop=True)
    season_player_info = player_info_df[player_info_df["ID"].isin(player_stats_df["Player"].unique().tolist())].reset_index(drop=True)

    # Seleccionamos solo las columnas que necesitaremos de información
    season_player_info = season_player_info[["ID","DateBirth","Height","PrefFoot","Position","Role"]]
    season_player_stats = season_player_stats.drop(columns=["ShirtNumber", "Position"])
    season_matches = season_matches[["ID","HomeTeam","AwayTeam","HomeScore","AwayScore","HomeElo","AwayElo"]]

    # Cambio de índice en el dataframe de partido - una fila por equipo y partido
    home_season_matches = season_matches.rename(columns={"ID":"Match","HomeTeam":"Team","AwayTeam":"Opponent","HomeScore":"Score","AwayScore":"OppScore","HomeElo":"Elo","AwayElo":"OppElo"})
    away_season_matches = season_matches.rename(columns={"ID":"Match","AwayTeam":"Team","HomeTeam":"Opponent","AwayScore":"Score","HomeScore":"OppScore","AwayElo":"Elo","HomeElo":"OppElo"})
    season_matches = pd.concat([home_season_matches, away_season_matches]).sort_values(by=["Match", "Team"]).reset_index(drop=True)

    # Concatenamos la información del partido con las estadísticas del jugador para obtener información extra
    season_matches_stats = season_player_stats.merge(season_matches, on=["Match", "Team"], how="left")

    # Aplicamos agregación de datos
    season_player_agg_stats = player_aggregate_data(player_stats_df=season_matches_stats)

    # Merge de los datos agregados de la temporada con la información del jugador
    season_player_info = season_player_info.rename(columns={"ID":"Player"})
    season_player_df = season_player_info.merge(season_player_agg_stats, how="inner", on="Player")

    # Limpieza del dataframe
    final_player_df = final_agg_df_cleaning(season_player_df=season_player_df)

    return final_player_df

# --------------------------------------------------------------------------------------
# CÓMPUTO DE LA MATRIZ DE SIMILARIDAD PARA CADA POSICIÓN
# --------------------------------------------------------------------------------------
def compute_similarity_matrix(df: pd.DataFrame, metric: str ="cosine", scale: bool =True, weights: dict = None) -> pd.DataFrame:

    X = df.copy()

    # Pesos opcionales
    if weights is not None:
        for col, w in weights.items():
            if col in X.columns:
                X[col] = X[col] * w

    # Escalado de metricas
    if scale:
        scaler = StandardScaler()
        X_values = scaler.fit_transform(X)
    else:
        X_values = X.values

    # Matriz de similaridad
    if metric == "cosine":
        sim_matrix = cosine_similarity(X_values)
    elif metric == "euclidean":
        dist_matrix = euclidean_distances(X_values)
        sim_matrix = 1 / (1 + dist_matrix)

    # Convertimos a dataframe
    sim_df = pd.DataFrame(sim_matrix, index=df.index, columns=df.index)

    return sim_df

# --------------------------------------------------------------------------------------
# PROCESADO DE LA MATRIZ DE SIMILARIDAD
# --------------------------------------------------------------------------------------
def sim_matrix_proc(proc_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]: 

    final_player_df = proc_df.copy()

    # Aplicado de matriz de similitud en porteros
    only_goalkeepers = final_player_df[final_player_df["GeneralPos_Goalkeeper"] == 1]
    only_goalkeepers = only_goalkeepers.loc[:, only_goalkeepers.nunique(dropna=False) > 1]          # Eliminamos columnas sin variabilidad
    only_goalkeepers = only_goalkeepers.dropna(axis=1)
    sim_matrix_goalkeepers = compute_similarity_matrix(df=only_goalkeepers)
    sim_matrix_goalkeepers.index.name = None
    sim_matrix_goalkeepers.columns.name = None

    # Aplicado de matriz de similitud en defensas
    only_defenders = final_player_df[final_player_df["GeneralPos_Defender"] == 1]
    only_defenders = only_defenders.loc[:, only_defenders.nunique(dropna=False) > 1]                # Eliminamos columnas sin variabilidad
    only_defenders = only_defenders.dropna(axis=1)
    sim_matrix_defenders = compute_similarity_matrix(df=only_defenders)
    sim_matrix_defenders.index.name = None
    sim_matrix_defenders.columns.name = None

    # Aplicado de matriz de similitud en centrocampistas
    only_midfielders = final_player_df[final_player_df["GeneralPos_Midfielder"] == 1]
    only_midfielders = only_midfielders.loc[:, only_midfielders.nunique(dropna=False) > 1]          # Eliminamos columnas sin variabilidad
    only_midfielders = only_midfielders.dropna(axis=1)
    sim_matrix_midfielders = compute_similarity_matrix(df=only_midfielders)
    sim_matrix_midfielders.index.name = None
    sim_matrix_midfielders.columns.name = None

    # Aplicado de matriz de similitud en centrocampistas
    only_forward = final_player_df[final_player_df["GeneralPos_Attacker"] == 1]
    only_forward = only_forward.loc[:, only_forward.nunique(dropna=False) > 1]                      # Eliminamos columnas sin variabilidad
    only_forward = only_forward.dropna(axis=1)
    sim_matrix_attackers = compute_similarity_matrix(df=only_forward)
    sim_matrix_attackers.index.name = None
    sim_matrix_attackers.columns.name = None

    return sim_matrix_goalkeepers, sim_matrix_defenders, sim_matrix_midfielders, sim_matrix_attackers

# --------------------------------------------------------------------------------------
# PROCESO PRINCIPAL
# --------------------------------------------------------------------------------------
def main_proc_data_similarity(match_info_df: pd.DataFrame, player_stats_df: pd.DataFrame, player_info_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    # Aplicado de la función de similaridad
    proc_df = similarity_score_processing(match_info_df=match_info_df.copy(), player_stats_df=player_stats_df.copy(), player_info_df=player_info_df.copy(), act_season=ACT_SEASON)

    # Aplicamos la función para obtener las matrices de similitud entre pares de jugadores
    sim_matrix_goalkeepers, sim_matrix_defenders, sim_matrix_midfielders, sim_matrix_attackers = sim_matrix_proc(proc_df=proc_df.copy())

    # Las matrices de similitud tienen valores de -1 a 1, vamos a extrapolarlo a porcentage (0 a 100)
    corr_perc_goalkeepers = ((sim_matrix_goalkeepers + 1) / 2) * 100
    corr_perc_defenders = ((sim_matrix_defenders + 1) / 2) * 100
    corr_perc_midfielders = ((sim_matrix_midfielders + 1) / 2) * 100
    corr_perc_attackers = ((sim_matrix_attackers + 1) / 2) * 100

    return corr_perc_goalkeepers, corr_perc_defenders, corr_perc_midfielders, corr_perc_attackers

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA ENCONTRAR TOP N DE JUGADORES PARECIDOS AL DESEADO
# --------------------------------------------------------------------------------------
def get_similar_players(player_id: str, top_n: int, corr_perc_goalkeepers: pd.DataFrame, corr_perc_defenders: pd.DataFrame, corr_perc_midfielders: pd.DataFrame, corr_perc_attackers: pd.DataFrame) -> dict:

    # Comprovamos en que posición predomina el jugador
    if player_id in corr_perc_goalkeepers.columns:
        sim_df = corr_perc_goalkeepers
    elif player_id in corr_perc_defenders.columns:
        sim_df = corr_perc_defenders
    elif player_id in corr_perc_midfielders.columns:
        sim_df = corr_perc_midfielders
    elif player_id in corr_perc_attackers.columns:
        sim_df = corr_perc_attackers
    else:
        return {}

    # Serie de similitudes
    sim_series = sim_df[player_id].copy()
    sim_series = sim_series.drop(player_id)         # Eliminamos el propio jugador

    # Ordenar de mayor a menor y selección de top N
    sim_series = sim_series.sort_values(ascending=False)
    top_similar = sim_series.head(top_n)                    

    return top_similar.to_dict()

# --------------------------------------------------------------------------------------
# LO MISMO PARA LOS EQUIPOS - Procesado de la matriz de similitud
# --------------------------------------------------------------------------------------
def proc_teams_sim_matrix(matches_info_df: pd.DataFrame, team_season_agg_stats: pd.DataFrame, min_matches: int = 5) -> pd.DataFrame:

    match_info_df = matches_info_df.copy()
    aggregate_team_df = team_season_agg_stats.copy()

    # Obtenemos los partidos de la actual temporada
    matches_act_season = match_info_df[match_info_df["Season"].astype(str) == str(ACT_SEASON)]

    # Selección de columnas
    matches_act_season = matches_act_season[["HomeTeam", "AwayTeam", "HomeScore", "AwayScore", "HomeElo", "AwayElo"]]

    # Goles como local y goles como visitante
    home_team_scores = (matches_act_season.groupby("HomeTeam")[["HomeScore", "AwayScore"]].sum().reset_index())
    away_team_scores = (matches_act_season.groupby("AwayTeam")[["HomeScore", "AwayScore"]].sum().reset_index())

    # Reseteamos columnas y merge
    home_team_scores.columns = ["Team", "HomeGoals", "HomeOppGoals"]
    away_team_scores.columns = ["Team", "AwayOppGoals", "AwayGoals"]
    goals_df = home_team_scores.merge(away_team_scores, on="Team", how="inner")

    # Obtención del ELO medio por equipo y por rival, primero unificar
    home_elo = matches_act_season[["HomeTeam", "HomeElo", "AwayElo"]].rename(columns={"HomeTeam":"Team", "HomeElo":"Elo", "AwayElo":"OppElo"})
    away_elo = matches_act_season[["AwayTeam", "AwayElo", "HomeElo"]].rename(columns={"AwayTeam":"Team", "AwayElo":"Elo", "HomeElo":"OppElo"})
    elo_df = pd.concat([home_elo, away_elo]).groupby("Team")[["Elo", "OppElo"]].mean().reset_index()

    # Unimos
    teams_matches_df = goals_df.merge(elo_df, on="Team", how="inner")
    teams_matches_df = teams_matches_df.merge(aggregate_team_df, on="Team", how="inner").set_index("Team")
    teams_matches_df.index.name = None

    # Filtramos por un mínimo de partiros
    teams_matches_df = teams_matches_df[teams_matches_df["Matches"] >= min_matches]

    # Aplicamos one hot encoding para la columna "Formation"
    final_df = pd.get_dummies(teams_matches_df, columns=["Formation"], prefix="formation", dtype=int)
    final_df = final_df.fillna(0)

    # Aplicamos la función para obtener la matriz de similitud
    teams_sim_matrix = compute_similarity_matrix(df=final_df)
    teams_perc_corr = ((teams_sim_matrix + 1) / 2) * 100             # A porcentage

    return teams_perc_corr

# --------------------------------------------------------------------------------------
# OBTENER EQUIPOS SIMILARES
# --------------------------------------------------------------------------------------
def get_similar_teams(team_id: str, top_n: int, teams_perc_corr: pd.DataFrame) -> dict:

    if team_id in teams_perc_corr.columns:
        
        # Serie de similitudes
        sim_series = teams_perc_corr[team_id].copy()
        sim_series = sim_series.drop(team_id)         # Eliminamos el propio equipo

        # Ordenar de mayor a menor y selección de top N
        sim_series = sim_series.sort_values(ascending=False)
        top_similar = sim_series.head(top_n)                    

        return top_similar.to_dict()

    else:
        return {}

    