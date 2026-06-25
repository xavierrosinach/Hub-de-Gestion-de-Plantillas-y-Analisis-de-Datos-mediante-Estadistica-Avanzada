import os
import pandas as pd
import numpy as np
import re
from rapidfuzz import process, fuzz
import warnings
from typing import Tuple
import time

warnings.simplefilter(action='ignore', category=FutureWarning)      # Silenciar el warning de FutureWarning
warnings.filterwarnings("ignore", message="A value is trying to be set on a copy")

from use.config import DATA_PATH, COMPS, MAPPED_COLUMNS_PLAYERS, MAPPED_COLUMNS_TEAMS, ORDER_COLUMNS_TEAMS, MAPPED_POSITIONS                 # Añadimos aquí la lista con los ordenes de 
from use.functions import REPLACEMENTS, create_slug, generate_unique_ids, elapsed_time_str, need_to_upload

import bronze.scoresway_cleaning as sw
import bronze.sofascore_cleaning as ss

# Estructura de carpetas
RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
BRONZE_DATA_PATH = os.path.join(DATA_PATH, "bronze")
UNIFIED_DATA_PATH = os.path.join(BRONZE_DATA_PATH, "unified_data")
os.makedirs(UNIFIED_DATA_PATH, exist_ok=True)

import pandas as pd
from difflib import SequenceMatcher

# --------------------------------------------------------------------------------------
# Devuelve la similaridad entre A y B
# --------------------------------------------------------------------------------------
def _similar(a, b):
    if pd.isna(a) or pd.isna(b):
        return None
    a, b = str(a).strip().lower(), str(b).strip().lower()
    return 1.0 if a == b else SequenceMatcher(None, a, b).ratio()

# --------------------------------------------------------------------------------------
# Similaridad total en la fila
# --------------------------------------------------------------------------------------
def _row_similarity(r1, r2, cols):
    ratios = []
    for c in cols:
        s = _similar(r1[c], r2[c])
        if s is not None:
            ratios.append(s)
    return sum(ratios) / len(ratios) if ratios else 0.0

# --------------------------------------------------------------------------------------
# Devuelve True si alguna columna es clave
# --------------------------------------------------------------------------------------
def _conflict(r1, r2, key_cols):
    """True si alguna columna imprescindible esta en ambas y es distinta."""
    for c in key_cols:
        a, b = r1[c], r2[c]
        if not pd.isna(a) and not pd.isna(b) and str(a).strip() != str(b).strip():
            return True
    return False

# --------------------------------------------------------------------------------------
# COMPRUEVA LOS DATAFRAMES UNIFICADOS Y MIRA LOS DUPLICADOS SEGÚN UN THRESHOLD
# --------------------------------------------------------------------------------------
def merge_duplicates(df: pd.DataFrame, check_cols: list, threshold=0.9, key_cols=None) -> pd.DataFrame:
    key_cols = key_cols or []
    if threshold > 1:
        threshold /= 100

    df = df.reset_index(drop=True)
    rows = [df.iloc[i] for i in range(len(df))]
    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            if _conflict(rows[i], rows[j], key_cols):
                continue
            if _row_similarity(rows[i], rows[j], check_cols) >= threshold:
                parent[find(i)] = find(j)

    groups = {}
    for i in range(len(df)):
        groups.setdefault(find(i), []).append(i)

    merged = [df.iloc[idxs].bfill().iloc[0] for idxs in groups.values()]
    return pd.DataFrame(merged).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# NORMALIZACIÓN DE NOMBRES
# --------------------------------------------------------------------------------------
def normalize_name(text: str) -> str:
    if not isinstance(text, str):
        return ""

    for k, v in REPLACEMENTS.items():
        text = text.replace(k, v)

    text = text.lower()
    text = re.sub(r'\b(fc|cf|club|de|la|ud|cd|sd|fk|ac|sc)\b', '', text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# --------------------------------------------------------------------------------------
# MATCHING EQUIPOS DE UNA LIGA
# --------------------------------------------------------------------------------------
def matching_part_teams(ss_teams_part: pd.DataFrame, sw_teams_part: pd.DataFrame, threshold: int = 75) -> pd.DataFrame:

    ss_teams_part = ss_teams_part.copy()
    sw_teams_part = sw_teams_part.copy()

    # Normalizamos para matching
    for col in ["Slug", "Name", "ShortName", "LongName"]:
        ss_teams_part[col] = ss_teams_part[col].fillna("").apply(normalize_name)
        sw_teams_part[col] = sw_teams_part[col].fillna("").apply(normalize_name)

    # Siempre A -> B desde el mayor al menor
    if len(ss_teams_part) > len(sw_teams_part):
        df_A = ss_teams_part
        df_B = sw_teams_part
        cols_dict = {"SlugA":"SlugSS", "SlugB":"SlugSW",
                     "NameA":"NameSS", "NameB":"NameSW",
                     "ShortNameA":"ShortNameSS", "ShortNameB":"ShortNameSW",
                     "LongNameA":"LongNameSS", "LongNameB":"LongNameSW"}
    else:
        df_A = sw_teams_part
        df_B = ss_teams_part
        cols_dict = {"SlugA":"SlugSW", "SlugB":"SlugSS",
                     "NameA":"NameSW", "NameB":"NameSS",
                     "ShortNameA":"ShortNameSW", "ShortNameB":"ShortNameSS",
                     "LongNameA":"LongNameSW", "LongNameB":"LongNameSS"}

    choices_slug = [x for x in df_B["Slug"].dropna().unique().tolist() if x != ""]
    choices_name = [x for x in df_B["Name"].dropna().unique().tolist() if x != ""]
    choices_s_name = [x for x in df_B["ShortName"].dropna().unique().tolist() if x != ""]
    choices_l_name = [x for x in df_B["LongName"].dropna().unique().tolist() if x != ""]

    results = []

    for _, row in df_A.iterrows():

        row_slug = row["Slug"]
        row_name = row["Name"]
        row_s_name = row["ShortName"]
        row_l_name = row["LongName"]

        match_slug, score_slug = (np.nan, 0)
        match_name, score_name = (np.nan, 0)
        match_s_name, score_s_name = (np.nan, 0)
        match_l_name, score_l_name = (np.nan, 0)

        if row_slug and choices_slug:
            tmp = process.extractOne(row_slug, choices_slug, scorer=fuzz.token_set_ratio)
            if tmp:
                match_slug, score_slug, _ = tmp

        if row_name and choices_name:
            tmp = process.extractOne(row_name, choices_name, scorer=fuzz.token_set_ratio)
            if tmp:
                match_name, score_name, _ = tmp

        if row_s_name and choices_s_name:
            tmp = process.extractOne(row_s_name, choices_s_name, scorer=fuzz.token_set_ratio)
            if tmp:
                match_s_name, score_s_name, _ = tmp

        if row_l_name and choices_l_name:
            tmp = process.extractOne(row_l_name, choices_l_name, scorer=fuzz.token_set_ratio)
            if tmp:
                match_l_name, score_l_name, _ = tmp

        results.append({"SlugA": row_slug, "SlugB": match_slug if score_slug >= threshold else np.nan, "ScoreSlug": score_slug,
                        "NameA": row_name, "NameB": match_name if score_name >= threshold else np.nan, "ScoreName": score_name,
                        "ShortNameA": row_s_name, "ShortNameB": match_s_name if score_s_name >= threshold else np.nan, "ScoreShortName": score_s_name,
                        "LongNameA": row_l_name, "LongNameB": match_l_name if score_l_name >= threshold else np.nan, "ScoreLongName": score_l_name})

    matched_teams = pd.DataFrame(results).rename(columns=cols_dict)

    # Diccionarios de lookup SOLO con los part de la liga
    ss_slug_to_id = ss_teams_part.drop_duplicates("Slug").set_index("Slug")["IdSS"].to_dict()
    ss_name_to_id = ss_teams_part.drop_duplicates("Name").set_index("Name")["IdSS"].to_dict()
    ss_sname_to_id = ss_teams_part.drop_duplicates("ShortName").set_index("ShortName")["IdSS"].to_dict()
    ss_lname_to_id = ss_teams_part.drop_duplicates("LongName").set_index("LongName")["IdSS"].to_dict()

    sw_slug_to_id = sw_teams_part.drop_duplicates("Slug").set_index("Slug")["IdSW"].to_dict()
    sw_name_to_id = sw_teams_part.drop_duplicates("Name").set_index("Name")["IdSW"].to_dict()
    sw_sname_to_id = sw_teams_part.drop_duplicates("ShortName").set_index("ShortName")["IdSW"].to_dict()
    sw_lname_to_id = sw_teams_part.drop_duplicates("LongName").set_index("LongName")["IdSW"].to_dict()

    ids_results = []

    for _, row in matched_teams.iterrows():

        candidates = [("Slug", row["ScoreSlug"], row["SlugSS"], row["SlugSW"]), ("Name", row["ScoreName"], row["NameSS"], row["NameSW"]),
                      ("ShortName", row["ScoreShortName"], row["ShortNameSS"], row["ShortNameSW"]), ("LongName", row["ScoreLongName"], row["LongNameSS"], row["LongNameSW"])]

        # solo candidatos con ambos valores no nulos
        candidates = [c for c in candidates if pd.notna(c[2]) and pd.notna(c[3])]

        if len(candidates) == 0:
            ids_results.append({"IdSS": np.nan, "IdSW": np.nan})
            continue

        best_field, _, ss_value, sw_value = max(candidates, key=lambda x: x[1])

        if best_field == "Slug":
            id_ss = ss_slug_to_id.get(ss_value, np.nan)
            id_sw = sw_slug_to_id.get(sw_value, np.nan)
        elif best_field == "Name":
            id_ss = ss_name_to_id.get(ss_value, np.nan)
            id_sw = sw_name_to_id.get(sw_value, np.nan)
        elif best_field == "ShortName":
            id_ss = ss_sname_to_id.get(ss_value, np.nan)
            id_sw = sw_sname_to_id.get(sw_value, np.nan)
        else:
            id_ss = ss_lname_to_id.get(ss_value, np.nan)
            id_sw = sw_lname_to_id.get(sw_value, np.nan)

        ids_results.append({"IdSS": id_ss, "IdSW": id_sw})

    matched_teams_ids = pd.DataFrame(ids_results).drop_duplicates()

    # IDs no mapeados
    not_matched_ss_ids = [i for i in ss_teams_part["IdSS"] if i not in matched_teams_ids["IdSS"].dropna().tolist()]
    not_matched_sw_ids = [i for i in sw_teams_part["IdSW"] if i not in matched_teams_ids["IdSW"].dropna().tolist()]
    df_not_matched_ss = pd.DataFrame({"IdSS": not_matched_ss_ids, "IdSW": np.nan})
    df_not_matched_sw = pd.DataFrame({"IdSS": np.nan, "IdSW": not_matched_sw_ids})

    matched_teams_ids = pd.concat([matched_teams_ids, df_not_matched_ss, df_not_matched_sw], ignore_index=True).drop_duplicates()

    return matched_teams_ids

# --------------------------------------------------------------------------------------
# LIMPIEZA DEL DATAFRAME DE EQUIPOS MAPEADO
# --------------------------------------------------------------------------------------
def clean_matched_teams_df(df: pd.DataFrame) -> pd.DataFrame:

    # Dataframe y columnas
    df_cleaned = pd.DataFrame(index=df.index)
    cols_map = {"Name": ["NameSS", "NameSW"], "ShortName": ["ShortNameSS", "ShortNameSW"], "LongName": ["LongNameSS", "LongNameSW"], "Abbreviation": ["AbbreviationSW"], "Country": ["CountrySS"], 
                "FoundationDate": ["FoundationDateSS"], "Manager": ["ManagerSS"], "Venue": ["VenueSS"], "PrimaryColour": ["PrimaryColourSS"], "SecondaryColour": ["SecondaryColourSS"],
                "TextColour": ["TextColourSS"], "HomeKitCol1": ["HomeKitCol1SW"], "HomeKitCol2": ["HomeKitCol2SW"], "HomeShortsCol": ["HomeShortsColSW"], "AwayKitCol1": ["AwayKitCol1SW"], 
                "AwayKitCol2": ["AwayKitCol2SW"], "AwayShortsCol": ["AwayShortsColSW"], "IdSS": ["IdSS"], "IdSW": ["IdSW"]}

    # Para cada columna, la añadimos
    for new_col, possible_cols in cols_map.items():
        existing_cols = [col for col in possible_cols if col in df.columns]
        if existing_cols:
            df_cleaned[new_col] = df[existing_cols].bfill(axis=1).iloc[:, 0]
        else:
            df_cleaned[new_col] = np.nan

    df_cleaned.insert(0, "Slug", df_cleaned["Name"].apply(create_slug))
    df_cleaned.insert(0, "ID", generate_unique_ids(len(df_cleaned)))

    return df_cleaned.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# MATCHING EQUIPOS - Matching de todos los equipos a partir de los dataframes de equipos y partidos
# --------------------------------------------------------------------------------------
def matched_teams_df(ss_match: pd.DataFrame, sw_match: pd.DataFrame, ss_teams: pd.DataFrame, sw_teams: pd.DataFrame) -> pd.DataFrame:

    # Obtenemos equipos por competición
    ss_league_teams_dict = (pd.concat([ss_match[["League", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}), ss_match[["League", "AwayTeam"]].rename(columns={"AwayTeam": "Team"})]).drop_duplicates().groupby("League")["Team"].agg(list).to_dict())
    sw_league_teams_dict = (pd.concat([sw_match[["League", "HomeTeam"]].rename(columns={"HomeTeam": "Team"}), sw_match[["League", "AwayTeam"]].rename(columns={"AwayTeam": "Team"})]).drop_duplicates().groupby("League")["Team"].agg(list).to_dict())

    all_teams_matched = []

    # Para cada competición, subset de equipos
    for comp in COMPS["tournament"].tolist():

        league_slug = create_slug(text=comp)

        league_ss_team = ss_teams[ss_teams["IdSS"].isin(ss_league_teams_dict.get(league_slug, pd.DataFrame()))]
        league_sw_team = sw_teams[sw_teams["IdSW"].isin(sw_league_teams_dict.get(league_slug, pd.DataFrame()))].groupby("IdSW", as_index=False).first()

        # Obtenemos mapeo y añadimos a la lista
        if not league_ss_team.empty and not league_sw_team.empty:
            matched_codes_df = matching_part_teams(ss_teams_part=league_ss_team, sw_teams_part=league_sw_team)
            all_teams_matched.append(matched_codes_df)

    # Concatenamos
    all_teams_matched_df = pd.concat(all_teams_matched, ignore_index=True).drop_duplicates()

    # Resolver duplicados por IdSS
    all_teams_matched_df = (all_teams_matched_df.sort_values(by=["IdSS", "IdSW"], na_position="last").groupby("IdSS", dropna=False)["IdSW"]
                            .apply(lambda x: x.dropna().iloc[0] if x.dropna().any() else np.nan).reset_index())

    # Resolver duplicados por IdSW
    all_teams_matched_df = (all_teams_matched_df.sort_values(by=["IdSW", "IdSS"], na_position="last").groupby("IdSW", dropna=False)["IdSS"]
                            .apply(lambda x: x.dropna().iloc[0] if x.dropna().any() else np.nan).reset_index())

    # Para cada ID concatenamos la información
    list_teams_dfs = []
    for _, row in all_teams_matched_df.iterrows():

        id_ss = row["IdSS"]
        id_sw = row["IdSW"]

        team_ss = ss_teams[ss_teams["IdSS"] == id_ss].copy()
        team_sw = sw_teams[sw_teams["IdSW"] == id_sw].copy()

        if team_ss.empty:
            team_ss = pd.DataFrame([{"IdSS": id_ss}])
        else:
            team_ss = team_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS")

        if team_sw.empty:
            team_sw = pd.DataFrame([{"IdSW": id_sw}])
        else:
            team_sw = team_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW")

        team_ss = team_ss.reset_index(drop=True)
        team_sw = team_sw.reset_index(drop=True)

        team_df = pd.concat([team_ss, team_sw], axis=1)
        list_teams_dfs.append(team_df)

    # Concatenamos todos los equipos
    all_teams_df = pd.concat(list_teams_dfs, ignore_index=True)

    # Dataframes con equipos no mapeados
    not_matched_ss = ss_teams[~ss_teams["IdSS"].isin(all_teams_matched_df["IdSS"].unique().tolist())]
    not_matched_sw = sw_teams[~sw_teams["IdSW"].isin(all_teams_matched_df["IdSW"].unique().tolist())]

    # Añadir SS y SW a las columnas
    not_matched_ss = not_matched_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS")
    not_matched_sw = not_matched_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW")

    # Concatenamos con all teams
    all_teams_df = pd.concat([all_teams_df, not_matched_ss, not_matched_sw], ignore_index=True)

    return clean_matched_teams_df(all_teams_df) 

# --------------------------------------------------------------------------------------
# MATCHING DE JUGADORES DE UN EQUIPO
# --------------------------------------------------------------------------------------
def matching_part_players(ss_players_part: pd.DataFrame, sw_players_part: pd.DataFrame, threshold: int = 90) -> pd.DataFrame:

    ss_players_ = ss_players_part[["IdSS", "Slug", "Name", "ShortName"]].drop_duplicates().copy()
    sw_players_ = sw_players_part[["IdSW", "Slug", "Name", "MatchName"]].rename(columns={"MatchName": "ShortName"}).drop_duplicates().copy()

    # Normalizamos para matching
    for col in ["Name", "ShortName"]:
        ss_players_[col] = ss_players_[col].fillna("").apply(normalize_name)
        sw_players_[col] = sw_players_[col].fillna("").apply(normalize_name)

    # Siempre A -> B desde el mayor al menor
    if len(ss_players_) > len(sw_players_):
        df_A = ss_players_
        df_B = sw_players_
        cols_dict = {"SlugA":"SlugSS", "SlugB":"SlugSW",
                    "NameA":"NameSS", "NameB":"NameSW",
                    "ShortNameA":"ShortNameSS", "ShortNameB":"ShortNameSW"}
    else:
        df_A = sw_players_
        df_B = ss_players_
        cols_dict = {"SlugA":"SlugSW", "SlugB":"SlugSS",
                    "NameA":"NameSW", "NameB":"NameSS",
                    "ShortNameA":"ShortNameSW", "ShortNameB":"ShortNameSS"}
        
    choices_slug = [x for x in df_B["Slug"].dropna().unique().tolist() if x != ""]
    choices_name = [x for x in df_B["Name"].dropna().unique().tolist() if x != ""]
    choices_s_name = [x for x in df_B["ShortName"].dropna().unique().tolist() if x != ""]

    results = []

    # Para cada jugador del dataframe mas grande
    for _, row in df_A.iterrows():

        row_slug = row["Slug"]
        row_name = row["Name"]
        row_s_name = row["ShortName"]

        match_slug, score_slug = (np.nan, 0)
        match_name, score_name = (np.nan, 0)
        match_s_name, score_s_name = (np.nan, 0)

        if row_slug and choices_slug:
            tmp = process.extractOne(row_slug, choices_slug, scorer=fuzz.token_set_ratio)
            if tmp:
                match_slug, score_slug, _ = tmp

        if row_name and choices_name:
            tmp = process.extractOne(row_name, choices_name, scorer=fuzz.token_set_ratio)
            if tmp:
                match_name, score_name, _ = tmp

        if row_s_name and choices_s_name:
            tmp = process.extractOne(row_s_name, choices_s_name, scorer=fuzz.token_set_ratio)
            if tmp:
                match_s_name, score_s_name, _ = tmp

        results.append({"SlugA": row_slug, "SlugB": match_slug if score_slug >= threshold else np.nan, "ScoreSlug": score_slug,
                        "NameA": row_name, "NameB": match_name if score_name >= threshold else np.nan, "ScoreName": score_name,
                        "ShortNameA": row_s_name, "ShortNameB": match_s_name if score_s_name >= threshold else np.nan, "ScoreShortName": score_s_name})
        
    # Jugadores mapeados
    matched_players = pd.DataFrame(results).rename(columns=cols_dict)

    # Diccionarios de lookup SOLO con los part de la liga
    ss_slug_to_id = ss_players_.drop_duplicates("Slug").set_index("Slug")["IdSS"].to_dict()
    ss_name_to_id = ss_players_.drop_duplicates("Name").set_index("Name")["IdSS"].to_dict()
    ss_sname_to_id = ss_players_.drop_duplicates("ShortName").set_index("ShortName")["IdSS"].to_dict()

    sw_slug_to_id = sw_players_.drop_duplicates("Slug").set_index("Slug")["IdSW"].to_dict()
    sw_name_to_id = sw_players_.drop_duplicates("Name").set_index("Name")["IdSW"].to_dict()
    sw_sname_to_id = sw_players_.drop_duplicates("ShortName").set_index("ShortName")["IdSW"].to_dict()

    ids_results = []

    for _, row in matched_players.iterrows():

        candidates = [("Slug", row["ScoreSlug"], row["SlugSS"], row["SlugSW"]), 
                    ("Name", row["ScoreName"], row["NameSS"], row["NameSW"]),
                    ("ShortName", row["ScoreShortName"], row["ShortNameSS"], row["ShortNameSW"])]

        # solo candidatos con ambos valores no nulos
        candidates = [c for c in candidates if pd.notna(c[2]) and pd.notna(c[3])]

        if len(candidates) == 0:
            ids_results.append({"IdSS": np.nan, "IdSW": np.nan})
            continue

        best_field, _, ss_value, sw_value = max(candidates, key=lambda x: x[1])

        if best_field == "Slug":
            id_ss = ss_slug_to_id.get(ss_value, np.nan)
            id_sw = sw_slug_to_id.get(sw_value, np.nan)
        elif best_field == "Name":
            id_ss = ss_name_to_id.get(ss_value, np.nan)
            id_sw = sw_name_to_id.get(sw_value, np.nan)
        elif best_field == "ShortName":
            id_ss = ss_sname_to_id.get(ss_value, np.nan)
            id_sw = sw_sname_to_id.get(sw_value, np.nan)

        ids_results.append({"IdSS": id_ss, "IdSW": id_sw})

    matched_players_ids = pd.DataFrame(ids_results).drop_duplicates().dropna(subset=["IdSS", "IdSW"])
    return matched_players_ids

# --------------------------------------------------------------------------------------
# LIMPIEZA DEL DATAFRAME DE JUGADORES MAPEADO
# --------------------------------------------------------------------------------------
def clean_matched_players_df(df: pd.DataFrame) -> pd.DataFrame:

    # Dataframe y columnas
    df_cleaned = pd.DataFrame(index=df.index)
    cols_map = {"Name": ["NameSS", "NameSW"], "ShortName": ["ShortNameSW"], "FirstName": ["FirstNameSW"], "LastName": ["LastNameSW"], "ShortFirstName": ["ShortFirstNameSW"], 
                "ShortLastName": ["ShortLastNameSW"], "MatchName": ["ShortNameSS", "MatchNameSW"], "Country": ["CountrySS", "CountrySW"], "DateBirth": ["DateBirthSS"], 
                "Height": ["HeightSS"], "PrefFoot": ["PrefFootSS"], "Position": ["PositionSW"], "FirstPos": ["FirstPositionSS"], "SecondPos": ["SecondPositionSS"], 
                "ThirdPos": ["ThirdPositionSS"], "ContractUntil": ["ContractUntilSS"], "MarketValue": ["MarketValueSS"], "IdSS": ["IdSS"], "IdSW": ["IdSW"]}

    # Para cada columna, la añadimos
    for new_col, possible_cols in cols_map.items():
        existing_cols = [col for col in possible_cols if col in df.columns]
        if existing_cols:
            df_cleaned[new_col] = df[existing_cols].bfill(axis=1).iloc[:, 0]
        else:
            df_cleaned[new_col] = np.nan

    df_cleaned.insert(0, "Slug", df_cleaned["Name"].apply(create_slug))
    df_cleaned.insert(3, "LongName", df_cleaned["FirstName"] + " " + df_cleaned["LastName"])
    df_cleaned.insert(0, "ID", generate_unique_ids(len(df_cleaned)))

    # Tratado de posiciones
    df_cleaned["Position"] = df_cleaned["Position"].fillna("Unkwown").map(MAPPED_POSITIONS)
    df_cleaned["FirstPos"] = df_cleaned["FirstPos"].fillna("Unkwown").map(MAPPED_POSITIONS)
    df_cleaned["SecondPos"] = df_cleaned["SecondPos"].fillna("Unkwown").map(MAPPED_POSITIONS)
    df_cleaned["ThirdPos"] = df_cleaned["ThirdPos"].fillna("Unkwown").map(MAPPED_POSITIONS)
    
    return df_cleaned.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# MATCHING DE JUGADORES - Matching de todos los jugadores, concatenamos por equipo
# --------------------------------------------------------------------------------------
def matched_players_df(ss_players: pd.DataFrame, sw_players: pd.DataFrame, teams_df: pd.DataFrame) -> pd.DataFrame:
    
    all_players_matched = []

    for _, row in teams_df.iterrows():

        # Obtenemos los jugadores mapeados por equipo
        id_ss = row["IdSS"]
        id_sw = row["IdSW"]
        team_ss = ss_players[ss_players["Team"] == id_ss].copy()
        team_sw = sw_players[sw_players["Team"] == id_sw].copy()

        if team_ss.empty or team_sw.empty:
            continue
        else:
            matched_players = matching_part_players(ss_players_part=team_ss, sw_players_part=team_sw)
            all_players_matched.append(matched_players) 

    # Dataframe
    all_players_matched_df = pd.concat(all_players_matched, ignore_index=True)

    list_players_dfs = []
    for _, row in all_players_matched_df.iterrows():

        id_ss = row["IdSS"]
        id_sw = row["IdSW"]

        player_ss = ss_players[ss_players["IdSS"] == id_ss].copy()
        player_sw = sw_players[sw_players["IdSW"] == id_sw].drop_duplicates(subset="IdSW").copy()

        if player_ss.empty:
            player_ss = pd.DataFrame([{"IdSS": id_ss}])
        else:
            player_ss = player_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS")

        if player_sw.empty:
            player_sw = pd.DataFrame([{"IdSW": id_sw}])
        else:
            player_sw = player_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW")

        player_ss = player_ss.reset_index(drop=True)
        player_sw = player_sw.reset_index(drop=True)

        player_df = pd.concat([player_ss, player_sw], axis=1)
        list_players_dfs.append(player_df)

    # Dataframe
    players_df = pd.concat(list_players_dfs, ignore_index=True)

    # Dataframes con jugadores no mapeados
    not_matched_ss = ss_players[~ss_players["IdSS"].isin(all_players_matched_df["IdSS"].unique().tolist())]
    not_matched_sw = sw_players[~sw_players["IdSW"].isin(all_players_matched_df["IdSW"].unique().tolist())]

    # Añadir SS y SW a las columnas
    not_matched_ss = not_matched_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS").drop_duplicates(subset="IdSS")
    not_matched_sw = not_matched_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW").drop_duplicates(subset="IdSW")

    # Concatenación
    all_players_df = pd.concat([players_df, not_matched_ss, not_matched_sw], ignore_index=True)

    return clean_matched_players_df(all_players_df)

# --------------------------------------------------------------------------------------
# LIMPIEZA DEL DATAFRAME DE ENTRENADORES MAPEADO
# --------------------------------------------------------------------------------------
def clean_matched_managers_df(df: pd.DataFrame) -> pd.DataFrame:

    # Dataframe y columnas
    df_cleaned = pd.DataFrame(index=df.index)
    cols_map = {"Name": ["NameSS", "NameSW"], "ShortName": ["ShortNameSW"], "FirstName": ["FirstNameSW"], "LastName": ["LastNameSW"], "ShortFirstName": ["ShortFirstNameSW"], 
                "ShortLastName": ["ShortLastNameSW"], "MatchName": ["ShortNameSS", "MatchNameSW"], "Country": ["CountrySS", "CountrySW"], "DateBirth": ["DateBirthSS"], 
                "Type": ["TypeSW"], "Matches": ["MatchesSS"], "Wins": ["WinsSS"], "Draws": ["DrawsSS"], "Losses": ["LossesSS"], "GoalsFor": ["GoalsForSS"], 
                "GoalsAgainst": ["GoalsAgainstSS"], "Points": ["PointsSS"], "IdSS": ["IdSS"], "IdSW": ["IdSW"]}

    # Para cada columna, la añadimos
    for new_col, possible_cols in cols_map.items():
        existing_cols = [col for col in possible_cols if col in df.columns]
        if existing_cols:
            df_cleaned[new_col] = df[existing_cols].bfill(axis=1).iloc[:, 0]
        else:
            df_cleaned[new_col] = np.nan

    df_cleaned.insert(0, "Slug", df_cleaned["Name"].apply(create_slug))
    df_cleaned.insert(3, "LongName", df_cleaned["FirstName"] + " " + df_cleaned["LastName"])
    df_cleaned.insert(0, "ID", generate_unique_ids(len(df_cleaned)))

    return df_cleaned.sort_values(by="Slug").reset_index(drop=True)

# --------------------------------------------------------------------------------------
# MATCHING DE ENTRENADORES - Matching de todos los entrenadores
# --------------------------------------------------------------------------------------
def matched_managers_df(ss_managers: pd.DataFrame, sw_managers: pd.DataFrame) -> pd.DataFrame:

    # Obtenemos los entrenadores mapeados a partir de la función de jugadores - también se aplica
    matched_managers_ids = matching_part_players(ss_players_part=ss_managers, sw_players_part=sw_managers)

    list_managers_dfs = []
    for _, row in matched_managers_ids.iterrows():

        id_ss = row["IdSS"]
        id_sw = row["IdSW"]

        manager_ss = ss_managers[ss_managers["IdSS"] == id_ss].copy()
        manager_sw = sw_managers[sw_managers["IdSW"] == id_sw].drop_duplicates(subset="IdSW").copy()

        if manager_ss.empty:
            manager_ss = pd.DataFrame([{"IdSS": id_ss}])
        else:
            manager_ss = manager_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS")

        if manager_sw.empty:
            manager_sw = pd.DataFrame([{"IdSW": id_sw}])
        else:
            manager_sw = manager_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW")

        manager_ss = manager_ss.reset_index(drop=True)
        manager_sw = manager_sw.reset_index(drop=True)

        manager_df = pd.concat([manager_ss, manager_sw], axis=1)
        list_managers_dfs.append(manager_df)

    # Dataframe
    managers_df = pd.concat(list_managers_dfs)

    # Dataframes con jugadores no mapeados
    not_matched_ss = ss_managers[~ss_managers["IdSS"].isin(matched_managers_ids["IdSS"].unique().tolist())]
    not_matched_sw = sw_managers[~sw_managers["IdSW"].isin(matched_managers_ids["IdSW"].unique().tolist())]

    # Añadir SS y SW a las columnas
    not_matched_ss = not_matched_ss.rename(columns=lambda col: col if col == "IdSS" else f"{col}SS").drop_duplicates(subset="IdSS")
    not_matched_sw = not_matched_sw.rename(columns=lambda col: col if col == "IdSW" else f"{col}SW").drop_duplicates(subset="IdSW")

    # Concatenación
    all_managers_df = pd.concat([managers_df, not_matched_ss, not_matched_sw], ignore_index=True)

    return clean_matched_managers_df(all_managers_df)

# --------------------------------------------------------------------------------------
# LIMPIEZA DEL DATAFRAME DE PARTIDOS MAPEADOS
# --------------------------------------------------------------------------------------
def clean_matched_matches_df(df: pd.DataFrame) -> pd.DataFrame:

    # Dataframe y columnas
    df_cleaned = pd.DataFrame(index=df.index)
    cols_map = {"League": ["League"], "Season": ["Season"], "Round": ["RoundSS"], "HomeTeam": ["HomeTeamID"], "AwayTeam": ["AwayTeamID"], "Date": ["DateSS", "DateSW"], 
                "Time": ["TimeSS", "TimeSW"], "Venue": ["VenueSS"], "Referee": ["RefereeSS"], "HomeScore": ["HomeScoreSS"], "AwayScore": ["AwayScoreSS"],
                "IdSS": ["IdSS"], "IdSW": ["IdSW"]}

    # Para cada columna, la añadimos
    for new_col, possible_cols in cols_map.items():
        existing_cols = [col for col in possible_cols if col in df.columns]
        if existing_cols:
            df_cleaned[new_col] = df[existing_cols].bfill(axis=1).iloc[:, 0]
        else:
            df_cleaned[new_col] = np.nan

    df_cleaned.insert(0, "ID", generate_unique_ids(len(df_cleaned)))

    return df_cleaned.sort_values(by=["League", "Season", "Round", "Date", "Time"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# MATCHING DE PARTIDOS - A partir de equipos y partidos
# --------------------------------------------------------------------------------------
def matched_matches_df(ss_matches: pd.DataFrame, sw_matches: pd.DataFrame, teams_df: pd.DataFrame) -> pd.DataFrame:

    # Obtenemos diccionario con el Id de la fuente y el Id del equipo interno
    ss_to_id = teams_df.dropna(subset=["IdSS"]).drop_duplicates(subset="IdSS").set_index("IdSS")["ID"].to_dict()
    sw_to_id = teams_df.dropna(subset=["IdSW"]).drop_duplicates(subset="IdSW").set_index("IdSW")["ID"].to_dict()

    all_matches_list = []

    # Para cada liga y temporada
    for league in COMPS["tournament"].tolist():
        for season in ["2425", "2526"]:

            league_slug = create_slug(text=league)
            
            # Mapeamos equipo local y equipo visitante - SW
            sw_matches_ = sw_matches[(sw_matches["League"] == league_slug) & (sw_matches["Season"].astype(str) == str(season))].copy()
            sw_matches_["HomeTeamID"] = sw_matches_["HomeTeam"].map(sw_to_id) 
            sw_matches_["AwayTeamID"] = sw_matches_["AwayTeam"].map(sw_to_id) 
            sw_matches_ = sw_matches_.rename(columns=lambda col: col if col in ["IdSW", "HomeTeamID", "AwayTeamID"] else f"{col}SW")

            # SS
            ss_matches_ = ss_matches[(ss_matches["League"] == league_slug) & (ss_matches["Season"].astype(str) == str(season))].copy()
            ss_matches_["HomeTeamID"] = ss_matches_["HomeTeam"].map(ss_to_id) 
            ss_matches_["AwayTeamID"] = ss_matches_["AwayTeam"].map(ss_to_id)
            ss_matches_ = ss_matches_.rename(columns=lambda col: col if col in ["IdSS", "HomeTeamID", "AwayTeamID"] else f"{col}SS") 

            # Merge de los equipos
            matches_df = ss_matches_.merge(sw_matches_, on=["HomeTeamID", "AwayTeamID"], how="outer").drop_duplicates(subset="IdSS")
            matches_df["League"] = league_slug
            matches_df["Season"] = season
            all_matches_list.append(matches_df)

    # Dataframe con todos los partidos
    all_matches_df = pd.concat(all_matches_list)

    return clean_matched_matches_df(all_matches_df)

# --------------------------------------------------------------------------------------
# LIMPIEZA DE ESTADÍSTICAS DE EQUIPOS - Limpia uno a uno las estadísticas de los equipos en un partido
# --------------------------------------------------------------------------------------
def single_stats_cleaner(df: pd.DataFrame) -> pd.DataFrame:
    
    df = df.copy()

    # Rename a nomenclatura estándar
    df = df.rename(columns=MAPPED_COLUMNS_TEAMS)

    # Asegurar identificadores
    if "Match" not in df.columns:
        df["Match"] = np.nan
    if "Team" not in df.columns:
        df["Team"] = np.nan

    # Crear faltantes
    for col in ORDER_COLUMNS_TEAMS:
        if col not in df.columns:
            df[col] = np.nan

    # Columnas float
    float_cols = ["BallPossession", "DuelWonPercent", "GroundDuelsPercentage", "AerialDuelsPercentage", "DribblesPercentage", 
                  "WonTacklePercent", "ExpectedGoals", "GoalsPrevented", "KilometersCovered", "FinalThirdPhaseStatistic"]

    # Columnas int
    int_cols = [col for col in ORDER_COLUMNS_TEAMS if col not in ["Match", "Team"] + float_cols]

    # Conversión numérica
    for col in int_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in float_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Nan a 0
    df[int_cols] = df[int_cols].astype("Int64")
    df[float_cols] = df[float_cols].astype(float)

    # Orden final
    df = df[ORDER_COLUMNS_TEAMS]

    return df

# --------------------------------------------------------------------------------------
# LIMPIEZA DE ESTADÍSTICAS DE JUGADORES - Limpieza de estadísticas de jugadores
# --------------------------------------------------------------------------------------
def single_lineups_cleaner(df: pd.DataFrame) -> pd.DataFrame:

    df_cleaned = pd.DataFrame()
    list_columns = df.columns.tolist()

    if list_columns:

        # Identificadores del jugador
        df_cleaned["Match"] = df["Match"]
        df_cleaned["Team"] = df["team"]
        df_cleaned["Player"] = df["player"]
        df_cleaned["ShirtNumber"] = (df["shirt_numSS"] if "shirt_numSS" in list_columns else df["shirt_numSW"] if "shirt_numSW" in list_columns else np.nan).astype("Int64")

        # Posición
        df_cleaned["Position"] = df["positionSW"] if "positionSW" in list_columns else ""
        df_cleaned["PositionSide"] = df["position_sideSW"] if "position_sideSW" in list_columns else ""
        df_cleaned["Position"] = df_cleaned["Position"].astype(str).str.strip()
        df_cleaned["PositionSide"] = df_cleaned["PositionSide"].replace(0, "").fillna("").astype(str).str.strip()

        # Si Position SW es vacío o Substitute, usar fallback SS
        fallback_position = df["positionSS"] if "positionSS" in list_columns else np.nan
        mask_fallback = df_cleaned["Position"].isin(["", "Substitute"])

        # Solo concatenar lado cuando no haya que usar fallback
        df_cleaned["Position"] = np.where(mask_fallback, fallback_position, (df_cleaned["Position"] + " " + df_cleaned["PositionSide"]).str.strip())
        df_cleaned = df_cleaned.drop(columns=["PositionSide"])
        df_cleaned["Position"] = df_cleaned["Position"].fillna("Unknown")
        df_cleaned["Position"] = df_cleaned["Position"].map(MAPPED_POSITIONS)

        # Aplicamos valores numericos
        for col, list_values in MAPPED_COLUMNS_PLAYERS.items():
            existing_cols = [c for c in list_values if c in df.columns]
            if existing_cols:
                df_cleaned[col] = df[existing_cols].apply(pd.to_numeric, errors="coerce").max(axis=1)
            else:
                df_cleaned[col] = np.nan

        # A integer aquellos valores que se deben convertir
        not_int_cols = ["Match", "Team", "Player", "Position", "ShirtNumber", "Rating", "ExpectedGoals", "ExpectedGoalsOnTarget", "ExpectedAssists", "ShotValue", 
                        "KeeperSaveValue", "PassValue", "DribbleValue", "DefensiveValue", "GoalkeeperValue", "GoalsPrevented", "TotalBallCarriesDistance",
                        "TotalProgression", "BestBallCarryProgression", "TotalProgressiveBallCarriesDistance", "TopSpeed", "KilometersCovered",
                        "MetersCoveredWalkingKm", "MetersCoveredJoggingKm", "MetersCoveredRunningKm", "MetersCoveredHighSpeedRunningKm", "MetersCoveredSprintingKm"]
        for col in df_cleaned.columns:
            if col not in not_int_cols:
                df_cleaned[col] = df_cleaned[col].astype("Int64")
        for col in not_int_cols:
            if col not in ["Match", "Team", "Player", "Position", "ShirtNumber"]:
                df_cleaned[col] = df_cleaned[col]

        return df_cleaned.sort_values(by=["Match", "Team", "ShirtNumber"])
    
    else:
        return pd.DataFrame()
    
# --------------------------------------------------------------------------------------
# LIMPIEZA DE ESTADÍSTICAS DE JUGADORES - Limpieza de estadísticas de jugadores
# --------------------------------------------------------------------------------------
def matches_statistics_df(players_df: pd.DataFrame, teams_df: pd.DataFrame, matches_df: pd.DataFrame, managers_df: pd.DataFrame, ss_stats_player: pd.DataFrame, sw_stats_player: pd.DataFrame, ss_stats_team: pd.DataFrame, print_info: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # Listas a concatenar
    stats_list = []
    lineups_list = []

    # IdSS: float -> int -> str, dejando los NaN como están
    mask = players_df["IdSS"].notna()
    players_df["IdSS"] = players_df["IdSS"].astype(object)   # rompe el dtype float64
    players_df.loc[mask, "IdSS"] = (players_df.loc[mask, "IdSS"].astype(float).astype(int).astype(str))

    mask = matches_df["IdSS"].notna()
    matches_df["IdSS"] = matches_df["IdSS"].astype(object)   # rompe el dtype float64
    matches_df.loc[mask, "IdSS"] = (matches_df.loc[mask, "IdSS"].astype(float).astype(int).astype(str))

    mask = teams_df["IdSS"].notna()
    teams_df["IdSS"] = teams_df["IdSS"].astype(object)   # rompe el dtype float64
    teams_df.loc[mask, "IdSS"] = (teams_df.loc[mask, "IdSS"].astype(float).astype(int).astype(str))

    # Diccionario con IDs de codigos de jugadores
    ss_dict = players_df.dropna(subset="IdSS").set_index("IdSS")["ID"].to_dict()
    sw_dict = players_df.dropna(subset="IdSW").set_index("IdSW")["ID"].to_dict()

    # Diccionario con IDs de codigos de matches
    match_ss_dict = matches_df.dropna(subset="IdSS").set_index("IdSS")["ID"].to_dict()
    match_sw_dict = matches_df.dropna(subset="IdSW").set_index("IdSW")["ID"].to_dict()

    # Diccionario con IDs de codigos de matches
    team_ss_dict = teams_df.dropna(subset="IdSS").set_index("IdSS")["ID"].to_dict()
    team_sw_dict = teams_df.dropna(subset="IdSW").set_index("IdSW")["ID"].to_dict()

    # Diccionario de mapeo de equipos de ID a IdSS
    team_id_to_ss = teams_df.dropna(subset="ID").set_index("ID")["IdSS"].to_dict()
    team_id_to_ss = {k: str(int(v)) for k, v in team_id_to_ss.items() if pd.notna(v)}

    # Mismo con SW
    team_id_to_sw = teams_df.dropna(subset="ID").set_index("ID")["IdSW"].to_dict()
    team_id_to_sw = {k: str(v) for k, v in team_id_to_sw.items() if pd.notna(v)}

    # Diccionario de entrenadores
    managers_sw_dict = managers_df.dropna(subset="IdSW").set_index("IdSW")["ID"].to_dict()

    # Información a buscar
    leagues_to_look = COMPS["tournament"].unique().tolist()
    seasons_to_look = ["2425", "2526"]

    if print_info:
        i = 1
        total_matches = len(matches_df)

    # Para cada temporada, buscamos información
    for league in leagues_to_look:
        for season in seasons_to_look:

            # Partición del dataframe
            matches_to_look = matches_df[(matches_df["League"] == create_slug(league))&(matches_df["Season"].astype(str) == season)]
                        
            # Para cada partido, miramos de obtener información
            for _, row in matches_to_look.iterrows():
                if print_info:
                    print(f"                 [{i}/{total_matches}] Unifying data of the competition {league} (season {season}) - match {row['ID']}. ({round(i/total_matches * 100, 2)}%)                        ", flush=True, end="\r")
                    i += 1

                # Obtención de las estadísticas de los jugadores en aquel partido y estadísticas de los equipos
                try:
                    match_ss_player = ss_stats_player[ss_stats_player["Match"].astype(str) == str(int(row["IdSS"]))].copy()
                    match_ss_player["player"] = match_ss_player["player"].astype(str).map(ss_dict)
                    match_ss_player["Match"] = match_ss_player["Match"].astype(str).map(match_ss_dict)
                    match_ss_player["team"] = match_ss_player["team"].astype(str).map(team_ss_dict)
                    match_ss_player = match_ss_player.rename(columns=lambda col: col if col in ["Match", "team", "player"] else f"{col}SS")
                except:
                    match_ss_player = None
                try:
                    match_sw_player = sw_stats_player[sw_stats_player["Match"].astype(str) == str(row["IdSW"])].copy()
                    match_sw_player["player"] = match_sw_player["player"].map(sw_dict)
                    match_sw_player["Match"] = match_sw_player["Match"].map(match_sw_dict)
                    match_sw_player["team"] = match_sw_player["team"].map(team_sw_dict)
                    match_sw_player = match_sw_player.rename(columns=lambda col: col if col in ["Match", "team", "player"] else f"{col}SW")
                except:
                    match_sw_player = None
                try:
                    match_ss_team = ss_stats_team[ss_stats_team["Match"].astype(str) == str(int(row["IdSS"]))].copy()
                except:
                    match_ss_team = None

                # Concatenamos dataframe de alineaciones
                if match_ss_player is None and match_sw_player is None:
                    lineups_df = None
                elif match_ss_player is None:
                    lineups_df = match_sw_player
                elif match_sw_player is None:
                    lineups_df = match_ss_player
                else:
                    lineups_df = match_ss_player.merge(match_sw_player, on=["Match", "team", "player"], how="outer").drop_duplicates(subset="player")

                # Limpieza del dataframe de alineaciones
                if lineups_df is not None:
                    if not lineups_df.empty:
                        lineups_df = single_lineups_cleaner(df = lineups_df)
                        lineups_list.append(lineups_df)

                # Limpieza del dataframe de estadísticas del equipo
                if match_ss_team is not None and not match_ss_team.empty:
                    match_ss_team = single_stats_cleaner(match_ss_team)       # Limpieza de estadísticas

                    # Buscamos entrenadores, formaciones, y average age
                    path_sw = os.path.join(RAW_DATA_PATH, "competitions", row["League"], str(row["Season"]), "scoresway", "matches", f"{row['IdSW']}.json") if pd.notna(row["IdSW"]) else None
                    if path_sw is not None and os.path.exists(path_sw):
                        sw_lineups_df, home_avg_age, away_avg_age, home_manager, away_manager = sw.lineups_single_match(path_sw=path_sw, match_id=row["IdSW"], home_team_id=team_id_to_sw.get(row["HomeTeam"]), away_team_id=team_id_to_sw.get(row["AwayTeam"]))
                        home_manager = managers_sw_dict.get(home_manager, np.nan)
                        away_manager = managers_sw_dict.get(away_manager, np.nan)
                    else:
                        home_avg_age = np.nan
                        away_avg_age = np.nan
                        home_manager = np.nan
                        away_manager = np.nan

                    # Mismo método
                    path_lineups_ss = os.path.join(RAW_DATA_PATH, "competitions", row["League"], str(row["Season"]), "sofascore", "matches", str(int(row["IdSS"])), "lineups.json") if pd.notna(row["IdSS"]) else None
                    if path_lineups_ss is not None and os.path.exists(path_lineups_ss):
                        ss_lineups_df, home_formation, away_formation = ss.lineups_single_match(path_lineups_ss=path_lineups_ss, match_id=row["IdSS"], home_team_id=team_id_to_ss.get(row["HomeTeam"]), away_team_id=team_id_to_ss.get(row["AwayTeam"]))
                    else:
                        home_formation = np.nan
                        away_formation = np.nan

                    match_ss_team.insert(2, "Manager", [home_manager, away_manager])
                    match_ss_team.insert(3, "Formation", [home_formation, away_formation])
                    match_ss_team.insert(4, "AverageAge", [home_avg_age, away_avg_age])

                    # Mapeamos equipo y partido
                    match_ss_team["Team"] = match_ss_team["Team"].astype(str).map(team_ss_dict)
                    match_ss_team["Match"] = row["ID"]
                    stats_list.append(match_ss_team)

    # Obtenemos estadísticas de jugadores y de equipos
    teams_stats = pd.concat(stats_list, ignore_index=True)
    players_stats = pd.concat(lineups_list, ignore_index=True)

    return teams_stats, players_stats

# --------------------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL DE UNIFICACIÓN
# --------------------------------------------------------------------------------------
def main_data_unification(ss_player: pd.DataFrame, ss_team: pd.DataFrame, ss_manager: pd.DataFrame, ss_match: pd.DataFrame, ss_stats_player: pd.DataFrame, ss_stats_team: pd.DataFrame, sw_stats_player: pd.DataFrame, sw_player: pd.DataFrame, sw_team: pd.DataFrame, sw_manager: pd.DataFrame, sw_match: pd.DataFrame, print_info: bool=True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    start_time = time.time()

    if print_info:
        print(f"Bronze data unification                                                                                         ")

    # Obtenemos el dataframe de equipos matched
    if print_info:
        print(f"        1. Teams data unification.                                                                             ")
    teams_path = os.path.join(UNIFIED_DATA_PATH, "team.csv")
    if os.path.exists(teams_path) and not need_to_upload(teams_path, total_days=10):
        teams_df = pd.read_csv(teams_path, sep=";")
    else:
        teams_df = matched_teams_df(ss_match=ss_match, sw_match=sw_match, ss_teams=ss_team, sw_teams=sw_team)
        teams_df = merge_duplicates(teams_df, check_cols=["Slug","Name","ShortName","LongName","Country"], threshold=0.9, key_cols=["IdSS","IdSW"])
        teams_df.to_csv(teams_path, sep=";", index=False)

    # Obtenemos el dataframe de jugadores matched
    if print_info:
        print(f"        2. Players data unification.                                                                             ")
    players_path = os.path.join(UNIFIED_DATA_PATH, "player.csv")
    if os.path.exists(players_path) and not need_to_upload(players_path, total_days=10):
        players_df = pd.read_csv(players_path, sep=";")
    else:
        players_df = matched_players_df(ss_players=ss_player, sw_players=sw_player, teams_df=teams_df)
        # players_df = merge_duplicates(players_df, check_cols=["Slug","Name","ShortName","LongName","Country"], threshold=0.9, key_cols=["IdSS","IdSW"])
        players_df.to_csv(players_path, sep=";", index=False)


    # Obtenemos el dataframe de entrenadores matched
    if print_info:
        print(f"        3. Managers data unification.                                                                             ")
    managers_path = os.path.join(UNIFIED_DATA_PATH, "manager.csv")
    if os.path.exists(managers_path) and not need_to_upload(managers_path, total_days=10):
        managers_df = pd.read_csv(managers_path, sep=";")
    else:
        managers_df = matched_managers_df(ss_managers=ss_manager, sw_managers=sw_manager)
        managers_df = merge_duplicates(managers_df, check_cols=["Slug","Name","ShortName","LongName","Country"], threshold=0.9, key_cols=["IdSS","IdSW"])
        managers_df.to_csv(managers_path, sep=";", index=False)


    # Obtenemos el dataframe de partidos matched
    if print_info:
        print(f"        4. Matches data unification.                                                                             ")
    matches_path = os.path.join(UNIFIED_DATA_PATH, "matches.csv")
    if os.path.exists(matches_path) and not need_to_upload(matches_path, total_days=10):
        matches_df = pd.read_csv(matches_path, sep=";")
    else:
        matches_df = matched_matches_df(ss_matches=ss_match, sw_matches=sw_match, teams_df=teams_df)
        matches_df.to_csv(matches_path, sep=";", index=False)

    # Obtenemos las estadísticas de partidos
    if print_info:
        print(f"        5. Stats data unification.                                                                             ")

    team_stats_path = os.path.join(UNIFIED_DATA_PATH, "team_stats.csv")
    player_stats_path = os.path.join(UNIFIED_DATA_PATH, "player_stats.csv")
    need_update = False

    for path in [team_stats_path, player_stats_path]:
        if not os.path.exists(path) or need_to_upload(path, total_days=10):
            need_update = True
            break
    if need_update:
        team_stats_df, player_stats_df = matches_statistics_df(players_df=players_df, matches_df=matches_df, teams_df=teams_df, managers_df=managers_df, ss_stats_player=ss_stats_player, sw_stats_player=sw_stats_player, ss_stats_team=ss_stats_team)
        team_stats_df.to_csv(team_stats_path, sep=";", index=False)
        player_stats_df.to_csv(player_stats_path, sep=";", index=False)
    else:
        team_stats_df = pd.read_csv(team_stats_path, sep=";")
        player_stats_df = pd.read_csv(player_stats_path, sep=";")

    if print_info:
        print(f"Bronze data unification finished in {elapsed_time_str(start_time=start_time)}.")

    return teams_df, players_df, managers_df, matches_df, team_stats_df, player_stats_df