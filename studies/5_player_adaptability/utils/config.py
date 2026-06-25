from pathlib import Path
import json
import pandas as pd
import os

# --------------------------------------------------------------------------------------
# RUTA DE LOS DATOS
# --------------------------------------------------------------------------------------

DATA_PATH = r"D:\data"
ZIP_EVENTING_PATH = r"C:\Users\ASUS\Desktop\europa.zip"
TEMP_EVENTING_PATH = R"C:\Users\ASUS\Desktop\temp_eventing"
# DATA_PATH = r"c:\Users\xrosinach\Desktop\TFM\data"

# --------------------------------------------------------------------------------------
# RUTAS BASE DEL PROYECTO
# --------------------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
UTILS_DIR = BASE_DIR / "utils"

# --------------------------------------------------------------------------------------
# ARCHIVOS DE CONFIGURACIÓN
# --------------------------------------------------------------------------------------

COMPS_PATH = UTILS_DIR / "comps.csv"
DES_SEASONS_PATH = UTILS_DIR / "des_seasons.json"

# --------------------------------------------------------------------------------------
# CARGA DE DATOS DE CONFIGURACIÓN
# --------------------------------------------------------------------------------------

COMPS = pd.read_csv(COMPS_PATH, sep=";", encoding="latin1")

with open(DES_SEASONS_PATH, "r", encoding="utf-8") as f:
    DES_SEASONS = json.load(f)

if not isinstance(DES_SEASONS, list) or len(DES_SEASONS) == 0:
    raise ValueError("El archivo 'des_seasons.json' esta vacío (se necesita almenos una temporada).")

ACT_SEASON = DES_SEASONS[0]

# --------------------------------------------------------------------------------------
# CARGA DE LISTAS CON NOMBRES DE COLUMNAS PARA ESTADÍSTICAS DE EQUIPOS Y JUGADORES
# --------------------------------------------------------------------------------------

with open(os.path.join(UTILS_DIR, "proc", "bronze_proc", "mapped_columns_players.json"), "r", encoding="utf-8") as f:
    MAPPED_COLUMNS_PLAYERS = json.load(f)

with open(os.path.join(UTILS_DIR, "proc", "bronze_proc", "mapped_columns_teams.json"), "r", encoding="utf-8") as f:
    MAPPED_COLUMNS_TEAMS = json.load(f)

with open(os.path.join(UTILS_DIR, "proc", "bronze_proc", "order_columns_teams.json"), "r", encoding="utf-8") as f:
    ORDER_COLUMNS_TEAMS = json.load(f)

with open(os.path.join(UTILS_DIR, "proc", "bronze_proc", "mapped_positions.json"), "r", encoding="utf-8") as f:
    MAPPED_POSITIONS = json.load(f)