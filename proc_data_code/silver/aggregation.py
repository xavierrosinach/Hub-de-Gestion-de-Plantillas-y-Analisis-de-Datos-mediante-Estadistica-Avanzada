import os
import pandas as pd
import warnings
from typing import Tuple
from pandas.errors import PerformanceWarning

warnings.simplefilter(action="ignore", category=PerformanceWarning)

# Configuración
from use.config import UTILS_DIR, ACT_SEASON, DATA_PATH
from use.functions import json_to_dict, df_safe_div

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
os.makedirs(SILVER_DATA_PATH, exist_ok=True)

# JSON con lista ordenada de columnas de team_stats
team_stats_order_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "team_stats_order_columns.json")
team_stats_order = json_to_dict(json_path=team_stats_order_path).get("cols_order")

# JSON con lista ordenada de columnas de player_stats
player_stats_order_path = os.path.join(UTILS_DIR, "proc", "silver_proc", "player_stats_order_columns.json")
player_stats_order = json_to_dict(json_path=player_stats_order_path).get("cols_order")

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
# FUNCIÓN PARA AGREGAR DATOS DE EQUIPOS
# --------------------------------------------------------------------------------------
def team_aggregate_data(team_stats_df: pd.DataFrame) -> pd.DataFrame:

    team_agg = team_stats_df.copy()

    # Sacamos columnas de información
    cols_to_drop = [c for c in ["Match", "Manager"] if c in team_agg.columns]
    team_agg = team_agg.drop(columns=cols_to_drop)

    # Sacamos columnas per 90
    cols_per90 = [c for c in team_agg.columns if c.endswith("Per90")]
    team_agg = team_agg.drop(columns=cols_per90)

    # Definimos columnas de ratio/división para quitarlas
    ratio_cols = ["PassAccuracy","PassesPerTouch","TouchesPerPass","PossessionLossRate","UnsuccessfulTouchRate","DispossessedRate","OwnHalfPassAccuracy","OwnHalfPassShare",
                  "OppositionHalfPassAccuracy","OppositionHalfPassShare","LongBallAccuracy","LongBallShare","ThroughBallAccuracy","BallPossessionPerPass","FinalThirdEntriesPerPass",
                  "FinalThirdEntriesPerTouch","TouchesInOppBoxPerFinalThirdEntry","KeyPassesPerFinalThirdEntry","KeyPassesPerShot","AssistConversion","ExpectedAssistsPerKeyPass",
                  "ExpectedAssistsPerPass","CrossAccuracy","CrossShare","AccurateCrossShare","BigChanceConversion","BigChanceMissRate","BigChanceRate","BigChancesPerKeyPass",
                  "FinalThirdEfficiency","ShotAccuracy","ShotsOnTargetRate","ShotsOffTargetRate","ShotsInsideBoxRate","ShotsOutsideBoxRate","BlockedShotRate","ShotsPerTouchInOppBox",
                  "GoalsPerShotOnTarget","GoalsPerTouchInOppBox","GoalConversion","ExpectedGoalsPerShot","ExpectedGoalsOnTargetPerShotOnTarget","HitWoodworkRate","OffsideRate",
                  "DuelWonPercent","DuelWinRate","AerialDuelsPercentage","AerialWinRate","GroundDuelsPercentage","ContestWinRate","ChallengesLostRate","DribblesPercentage",
                  "WonTacklePercent","TackleAccuracy","DefensiveActionSuccess","InterceptionShare","ClearanceShare","BlockShare","BallRecoveryRate","LastManTackleRate",
                  "ClearanceOffLineRate","ErrorsLeadToShotRate","ErrorsLeadToGoalRate","GoalsConcededPerDefAction","SaveRate","DiveSaveRate","SavedShotsInsideBoxRate",
                  "CrossesNotClaimedRate","HighClaimRate","PunchRate","KeeperSweeperAccuracy","PenaltySaveRate","PenaltyGoalConcededRate","CornersTakenRate","CornersWonRate",
                  "CornersLostRate","FreeKicksRate","ThrowInsRate","GoalKicksRate","CardsPerFoul","YellowCardsPerFoul","RedCardsPerFoul","FoulsPerDefAction","WasFouledRate",
                  "FouledFinalThirdRate","PenaltyWonRate","PenaltyMissRate","PenaltyConcededRate","OwnGoalRate"]
    ratio_cols = [c for c in ratio_cols if c in team_agg.columns]
    team_agg = team_agg.drop(columns=ratio_cols)

    # Añadimos partidos - para sumar
    team_agg["Matches"] = 1 

    # Función para calcular la moda
    def mode_or_nan(s):
        s = s.dropna()
        if s.empty:
            return pd.NA
        return s.mode().iloc[0]

    # Diccionario de agregaciones
    agg_dict = {}

    for col in team_agg.columns:
        if col == "Team":
            continue
        elif col == "Formation":
            agg_dict[col] = mode_or_nan
        elif col in ["BallPossession", "Rating"]:
            agg_dict[col] = "mean"
        else:
            agg_dict[col] = "sum"

    # Agregación
    team_agg_df = team_agg.groupby("Team", as_index=False).agg(agg_dict)

    # Aplicamos la función de crear nuevas métricas al df
    cols_exclude = ['Match','Manager','DuelWonPercent','AerialDuelsPercentage','GroundDuelsPercentage','DribblesPercentage','WonTacklePercent']
    list_to_order = [c for c in team_stats_order if c not in cols_exclude]
    list_to_order.insert(2, "Matches")
    final_df = team_new_metrics(team_stats_df=team_agg_df, list_to_order=list_to_order)

    return final_df.sort_values(by="Team").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA AGREGAR DATOS DE JUGADORES
# --------------------------------------------------------------------------------------
def player_aggregate_data(player_stats_df: pd.DataFrame) -> pd.DataFrame:

    player_agg = player_stats_df.copy()

    # Sacamos columnas de información
    cols_to_drop = [c for c in ["Match", "Team"] if c in player_agg.columns]
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

    # Función para calcular la moda
    def mode_or_nan(s):
        s = s.dropna()
        if s.empty:
            return pd.NA
        return s.mode().iloc[0]

    # Diccionario de agregaciones
    agg_dict = {}

    for col in player_agg.columns:
        if col == "Player":
            continue
        elif col == "Position":
            agg_dict[col] = mode_or_nan
        elif col == "ShirtNumber":
            agg_dict[col] = mode_or_nan
        elif col in ["Rating","PassMeanAngle","PassMeanLength","PassMeanX","PassMeanY","ShotMeanX","ShotMeanY","MeanGoalY","MeanGoalZ","ShotMeanLength","GoalIniX",
                     "GoalIniY","GoalFinalY","GoalFinalZ","GoalMeanLength"]:
            agg_dict[col] = "mean"
        else:
            agg_dict[col] = "sum"

    # Agregación
    player_agg_df = player_agg.groupby("Player", as_index=False).agg(agg_dict)

    # Aplicamos la función de crear nuevas métricas al df
    cols_exclude = ['Match','Team']
    list_to_order = [c for c in player_stats_order if c not in cols_exclude]
    list_to_order.insert(3, "Matches")
    final_df = player_new_metrics(player_stats_df=player_agg_df, list_to_order=list_to_order)

    return final_df

# --------------------------------------------------------------------------------------
# FUNCIÓN PARA APLICAR EL AGREGADO DE JUGADORES Y EQUIPOS Y GUARDAR
# --------------------------------------------------------------------------------------
def main_aggregate_data(player_stats_df: pd.DataFrame, team_stats_df: pd.DataFrame, match_info_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    stats_pl = player_stats_df.copy()
    stats_tm = team_stats_df.copy()

    # Selección de columnas que vamos a necesitar de match info
    match_info_needed = match_info_df[["ID", "League", "Season", "Date"]].copy().rename(columns={"ID":"Match"})

    # Cruzamos con equipo y con jugadores (estadísticas) para obtener la información extra
    stats_pl = stats_pl.merge(match_info_needed, on="Match", how="left")
    stats_tm = stats_tm.merge(match_info_needed, on="Match", how="left")
    
    # Añadimos rating medio de jugadores
    if "Rating" in stats_pl.columns:
        match_team_rating_df = stats_pl[["Match", "Team", "Rating"]].dropna()
        match_team_rating_agg_df = match_team_rating_df.groupby(["Match", "Team"], as_index=False).agg({"Rating": "mean"})
        stats_tm = stats_tm.merge(match_team_rating_agg_df, on=["Match", "Team"], how="left")
    
    # Obtención de los partidos de la última temporada
    player_stats_last_season = stats_pl[stats_pl["Season"].astype(str) == str(ACT_SEASON)].drop(columns=["Season", "League", "Date"])
    team_stats_last_season = stats_tm[stats_tm["Season"].astype(str) == str(ACT_SEASON)].drop(columns=["Season", "League", "Date"])

    # Obtención de los últimos diez partidos
    player_stats_last_10 = (stats_pl.assign(Date=pd.to_datetime(stats_pl["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Player", group_keys=False).head()).drop(columns=["Season", "League", "Date"])
    team_stats_last_10 = (stats_tm.assign(Date=pd.to_datetime(stats_tm["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Team", group_keys=False).head()).drop(columns=["Season", "League", "Date"])

    # Obtención de los últimos cinco partidos
    player_stats_last_5 = (stats_pl.assign(Date=pd.to_datetime(stats_pl["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Player", group_keys=False).head(5)).drop(columns=["Season", "League", "Date"])
    team_stats_last_5 = (stats_tm.assign(Date=pd.to_datetime(stats_tm["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Team", group_keys=False).head(5)).drop(columns=["Season", "League", "Date"])

    # Obtención de los ultimos 3 partidos
    player_stats_last_3 = (stats_pl.assign(Date=pd.to_datetime(stats_pl["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Player", group_keys=False).head(3)).drop(columns=["Season", "League", "Date"])
    team_stats_last_3 = (stats_tm.assign(Date=pd.to_datetime(stats_tm["Date"], format="%d/%m/%Y", errors="coerce")).sort_values("Date", ascending=False).groupby("Team", group_keys=False).head(3)).drop(columns=["Season", "League", "Date"])

    # Agregamos datos de equipos
    agg_team_all = team_aggregate_data(team_stats_df=stats_tm.drop(columns=["Season", "League", "Date"]))
    agg_team_season = team_aggregate_data(team_stats_df=team_stats_last_season)
    agg_team_last_10 = team_aggregate_data(team_stats_df=team_stats_last_10)
    agg_team_last_5 = team_aggregate_data(team_stats_df=team_stats_last_5)
    agg_team_last_3 = team_aggregate_data(team_stats_df=team_stats_last_3)

    # Agregamos datos de jugadores
    agg_player_all = player_aggregate_data(player_stats_df=stats_pl.drop(columns=["Season", "League", "Date"]))
    agg_player_season = player_aggregate_data(player_stats_df=player_stats_last_season)
    agg_player_last_10 = player_aggregate_data(player_stats_df=player_stats_last_10)
    agg_player_last_5 = player_aggregate_data(player_stats_df=player_stats_last_5)
    agg_player_last_3 = player_aggregate_data(player_stats_df=player_stats_last_3)
    
    return agg_team_all, agg_team_season, agg_team_last_10, agg_team_last_5, agg_team_last_3, agg_player_all, agg_player_season, agg_player_last_10, agg_player_last_5, agg_player_last_3