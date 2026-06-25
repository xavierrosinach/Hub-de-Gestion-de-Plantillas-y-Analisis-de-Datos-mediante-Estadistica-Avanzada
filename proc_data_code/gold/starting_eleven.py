import pandas as pd
import os

from use.functions import json_to_dict
from use.config import ACT_SEASON, UTILS_DIR

# --------------------------------------------------------------------------------------
# NORMALIZACIÓN DE COORDENADAS
# --------------------------------------------------------------------------------------
def normalize_positionsloc(positionsloc: dict) -> dict:

    normalized = {}
    for formation, positions in positionsloc.items():
        normalized[formation] = {}
        for position, coords in positions.items():
            if (isinstance(coords, list) and len(coords) == 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float))):
                normalized[formation][position] = [coords]
            else:
                normalized[formation][position] = coords

    return normalized

# Lista para ordenar el dataframe en un futuro
all_formations_dict = json_to_dict(os.path.join(UTILS_DIR, "proc", "gold_proc", "formations_positions.json"))
all_formations_main_pos = json_to_dict(os.path.join(UTILS_DIR, "proc", "gold_proc", "formations_main_loc.json"))
all_formations_main_pos = normalize_positionsloc(positionsloc=all_formations_main_pos)

# --------------------------------------------------------------------------------------
# ALINEACIÓN TIITULAR
# --------------------------------------------------------------------------------------
def obtain_squad_formation(squad_df: pd.DataFrame, dict_formation: dict) -> pd.DataFrame:

    # Obtención del dataframe de minutos
    df = squad_df[["Player", "Name", "Position", "MinutesPlayed", "TotalMinutes"]].sort_values(by=["TotalMinutes", "MinutesPlayed"], ascending=False).copy()

    # Ponderamos según haver jugado más minutos totales que la posición
    df["Score"] = (0.7 * df["TotalMinutes"] + 0.3 * df["MinutesPlayed"])

    # Jugadores seleccionados y alineación
    selected_players = set()
    lineup = []

    # Para cada posición en la formación
    for position, n_players in dict_formation.items():
        candidates = (df[(df["Position"] == position) & (~df["Name"].isin(selected_players))].sort_values("Score", ascending=False).head(n_players))
        lineup.append(candidates)
        selected_players.update(candidates["Name"].tolist())

    # Concatenamos y selección de columnas
    lineup_df = pd.concat(lineup)[["Player", "Name", "Position"]].reset_index(drop=True)

    return lineup_df

# --------------------------------------------------------------------------------------
# LISTA DE JUGADORES CON MÁS MINUTOS JUGADOS POR POSICION
# --------------------------------------------------------------------------------------
def get_team_lineup(squad: pd.DataFrame, formation: str) -> list:

    formation_players = all_formations_dict.get(formation)
    dict_position_mean_xy = all_formations_main_pos.get(formation)

    # Obtenemos lineup dataframe y dataframe con las medias por posición - después mergeamos
    lineup_df = obtain_squad_formation(squad_df=squad.copy(), dict_formation=formation_players)
    mean_pos_df = squad[["Player", "Name", "Position", "PassMeanX", "PassMeanY"]]
    final_lineup_df = lineup_df.merge(mean_pos_df, on=["Player", "Name", "Position"], how="inner")

    # Crear contador acumulado por posición y asignamos mean x, y en la posición
    final_lineup_df["PositionIdx"] = (final_lineup_df.groupby("Position").cumcount())
    final_lineup_df[["MeanX", "MeanY"]] = final_lineup_df.apply(lambda row: pd.Series(dict_position_mean_xy[row["Position"]][row["PositionIdx"]]), axis=1)
    final_lineup_df.drop(columns="PositionIdx", inplace=True)

    # Generamos diccionario
    list_players_lineup = []
    for index, row in final_lineup_df.iterrows():
        list_players_lineup.append({"Player": row["Player"], "Name": row["Name"], "Position": row["Position"],
                                    "PositionCoords": {"X": row["MeanX"], "Y": row["MeanY"]}, "PlayerCoords": {"X": row["PassMeanX"], "Y": row["PassMeanY"]}})
       
    return list_players_lineup

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# --------------------------------------------------------------------------------------
def main_team_lineup(team_id: str, match_info_df: pd.DataFrame, player_info_df: pd.DataFrame, player_stats_df: pd.DataFrame, team_stats_df: pd.DataFrame) -> list:
    
    match = match_info_df.copy()
    player = player_info_df.copy()
    player_stats = player_stats_df.copy()
    team_stats = team_stats_df.copy()

    try:

        # Obtenemos los partidos de la temporada actual
        match = match[match["Season"].astype(str) == ACT_SEASON]

        # Obtenemos las estadísticas que deseamos - jugador, posición, minutos, y posición media de pases
        player_stats = player_stats[["Match", "Team", "Player", "Position", "MinutesPlayed", "PassMeanX", "PassMeanY"]]

        # Completar NaN de PassMeanX y PassMeanY con la media por posición
        player_stats["PassMeanX"] = player_stats["PassMeanX"].fillna(player_stats.groupby("Position")["PassMeanX"].transform("mean"))
        player_stats["PassMeanY"] = player_stats["PassMeanY"].fillna(player_stats.groupby("Position")["PassMeanY"].transform("mean"))

        # Filtramos por equipo
        match = match[(match["HomeTeam"] == team_id) | (match["AwayTeam"] == team_id)]
        team_stats = team_stats[(team_stats["Match"].isin(match["ID"].unique().tolist())) & (team_stats["Team"] == team_id)]
        player_stats = player_stats[(player_stats["Match"].isin(match["ID"].tolist())) & (player_stats["Team"] == team_id)]
        player = player[player["ID"].isin(player_stats["Player"].tolist())]
        player = player.rename(columns={"ID":"Player"})

        # Concatenamos jugador para distinguirlo y obtenemos el dataframe final para realizar el estudio
        player_stats = player_stats.merge(player, on="Player", how="inner")
        player_stats = player_stats[["Player", "Name", "Position_x", "MinutesPlayed", "PassMeanX", "PassMeanY"]]
        player_stats = player_stats.rename(columns={"Position_x": "Position"})

        # Obtención de la tabla de datos agregada
        player_agg_df = (player_stats.groupby(["Player", "Name", "Position"], as_index=False)
                        .agg({"MinutesPlayed": "sum", "PassMeanX": "mean", "PassMeanY": "mean"}))

        # Obtenemos diccionario con los minutos totales por jugador
        minutes_dict = (player_agg_df.groupby("Name")["MinutesPlayed"].sum().to_dict())
        player_agg_df["TotalMinutes"] = player_agg_df["Name"].map(minutes_dict)

        # Obtención de la formación más usada por el equipo
        most_used_formation = team_stats["Formation"].mode().iloc[0]

        return get_team_lineup(squad=player_agg_df.copy(), formation=most_used_formation)
    
    except:
        return []