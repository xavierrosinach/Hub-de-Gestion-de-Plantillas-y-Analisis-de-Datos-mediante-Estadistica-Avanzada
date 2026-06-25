import shutil
import pandas as pd
import os
import time
import numpy as np
from PIL import Image
from rembg import remove
from collections import deque
import cv2

# Configuración
from use.config import DATA_PATH, UTILS_DIR
from use.functions import elapsed_time_str, json_to_dict

# Estructura de carpetas de imagenes - input y output
INPUT_IMAGES_PATH = os.path.join(DATA_PATH, "raw", "images")
OUTPUT_IMAGES_PATH = os.path.join(DATA_PATH, "gold", "images")
os.makedirs(OUTPUT_IMAGES_PATH, exist_ok=True)

# Imagenes default
DEFAULT_IMAGES_PATH = os.path.join(UTILS_DIR, "default_images")
DEFAULT_MANAGER = os.path.join(DEFAULT_IMAGES_PATH, "managers.png")
DEFAULT_PLAYER = os.path.join(DEFAULT_IMAGES_PATH, "players.png")
DEFAULT_TEAM = os.path.join(DEFAULT_IMAGES_PATH, "teams.png")
DEFAULT_VENUE = os.path.join(DEFAULT_IMAGES_PATH, "venues.png")

# Carpetas con ficheros JSON con la información gold
GOLD_DATA_PATH = os.path.join(DATA_PATH, "gold")
GOLD_MANAGER = os.path.join(GOLD_DATA_PATH, "manager")
GOLD_PLAYER = os.path.join(GOLD_DATA_PATH, "player")
GOLD_TEAM = os.path.join(GOLD_DATA_PATH, "team")
GOLD_VENUE = os.path.join(GOLD_DATA_PATH, "venue")

# Dataframes silver con los IDs
SILVER_DATA_PATH = os.path.join(DATA_PATH, "silver")
silver_manager = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_1", "manager_clean_1.csv"), sep=";")
silver_player = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_3", "player_clean_3_2.csv"), sep=";")
silver_team = pd.read_csv(os.path.join(SILVER_DATA_PATH, "cleaning_2", "team_clean_2.csv"), sep=";")

# Carpeta con imagenes con los backgrounds removed
REMOVED_BACKGROUND_DIR = os.path.join(INPUT_IMAGES_PATH, "background_removed")
os.makedirs(REMOVED_BACKGROUND_DIR, exist_ok=True)

# Para todas las entidades
PLAYER_REM_BACK = os.path.join(REMOVED_BACKGROUND_DIR, "player")
os.makedirs(PLAYER_REM_BACK, exist_ok=True)
MANAGER_REM_BACK = os.path.join(REMOVED_BACKGROUND_DIR, "manager")
os.makedirs(MANAGER_REM_BACK, exist_ok=True)
TEAM_REM_BACK = os.path.join(REMOVED_BACKGROUND_DIR, "team")
os.makedirs(TEAM_REM_BACK, exist_ok=True)

# --------------------------------------------------------------------------------------
# COMRPOBACIÓN DE IMAGENES CORRECTAS
# --------------------------------------------------------------------------------------
def is_valid_image(image_path: str) -> bool:

    # Comprobamos que exista
    if not os.path.exists(image_path):
        return False

    try:
        # Verificación interna del fichero
        with Image.open(image_path) as img:
            img.verify()

        # Reabrimos para acceder al contenido
        with Image.open(image_path) as img:
            width, height = img.size

            # Dimensiones válidas
            if width <= 0 or height <= 0:
                return False

            # Comprobamos que realmente tenga contenido
            img.load()
        return True
    except Exception:
        return False

# --------------------------------------------------------------------------------------
# ELIMINACIÓN DE FONDO NORMAL
# --------------------------------------------------------------------------------------
def remove_normal_background(image_path: str, output_image_path: str, tolerance: int = 18) -> None:

    # Lectura de la imagen
    img = Image.open(image_path).convert("RGBA")
    arr = np.array(img)

    # Convertimos a BGR para OpenCV
    bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)

    # Escala de grises
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Máscara de todo lo que no sea fondo negro
    _, mask = cv2.threshold(gray, 8, 255, cv2.THRESH_BINARY)

    # Cerramos pequeños huecos
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Buscamos contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Si no hay contornos, copiamos la original
    if not contours:
        shutil.copy2(image_path, output_image_path)
        return

    # Nos quedamos con el contorno más grande
    largest_contour = max(contours, key=cv2.contourArea)

    # Creamos máscara limpia del escudo
    clean_mask = np.zeros_like(mask)
    cv2.drawContours(clean_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # Suavizamos un poco el borde
    clean_mask = cv2.GaussianBlur(clean_mask, (3, 3), 0)

    # Aplicamos alpha
    arr[:, :, 3] = clean_mask

    # Guardado de la imagen procesada
    Image.fromarray(arr).save(output_image_path)

# --------------------------------------------------------------------------------------
# MOVER TODAS LAS IMAGENES
# --------------------------------------------------------------------------------------
def move_all_images(entity: str, output_dir: str, silver_df: pd.DataFrame, list_entities: list, input_images_path: str, default_image_path: str, remove_background: bool, removed_back_dir: str, print_info: bool = True) -> None:

    # Creación del path output
    os.makedirs(output_dir, exist_ok=True)

    # Diccionario con los IDs internos y de Sofascore
    dict_players_ids = dict(zip(silver_df["ID"], silver_df["IdSS"].fillna(0).astype(int)))

    total_len = len(list_entities)
    i = 1

    # Para cada item, buscamos
    for id in list_entities:

        # Validación
        if id not in dict_players_ids.keys():
            i += 1
            continue

        # Buscamos paths
        input_raw_image_path = os.path.join(input_images_path, f"{dict_players_ids[id]}.png")
        rem_back_image_path = os.path.join(removed_back_dir, f"{dict_players_ids[id]}.png") if removed_back_dir else ""
        output_image_path = os.path.join(output_dir, f"{id}.png")

        # Si existe el output path no procesamos
        if os.path.exists(output_image_path):
            i += 1
            continue

        # Si existe el background removed path, movemos
        elif rem_back_image_path and os.path.exists(rem_back_image_path): 
            shutil.copy2(rem_back_image_path, output_image_path)
            i += 1
            continue

        else:
            # Si es valida, usamos la original, sino la default
            if is_valid_image(input_raw_image_path):
                is_valid = True
                image_to_use = input_raw_image_path
            else:
                is_valid = False
                image_to_use = default_image_path

            # Si se debe eliminar el fondo
            if remove_background and is_valid:

                try:
                    # Eliminación del fondo con IA para jugadores y entrenadores
                    if entity in ["player", "manager"]:

                        # Lectura de la imagen
                        with open(image_to_use, "rb") as f:
                            input_bytes = f.read()

                        # Eliminación del fondo
                        output_bytes = remove(input_bytes)

                        # Guardado de la imagen procesada
                        with open(output_image_path, "wb") as f:
                            f.write(output_bytes)
                        with open(rem_back_image_path, "wb") as f:
                            f.write(output_bytes)

                    # Eliminación del fondo normal para equipos
                    elif entity == "team":

                        # Guardado de la imagen procesada
                        shutil.copy2(output_image_path, rem_back_image_path)

                    # En venues nunca se elimina el fondo
                    else:
                        shutil.copy2(image_to_use, output_image_path)

                # En caso de error copiamos la imagen original
                except Exception:
                    shutil.copy2(image_to_use, output_image_path)
                    if rem_back_image_path:
                        shutil.copy2(image_to_use, rem_back_image_path)

            # Si no se elimina el fondo simplemente copiamos
            else:
                shutil.copy2(image_to_use, output_image_path)

        # Imprimimos información
        if print_info:
            perc = 0 if total_len == 0 else round((i/total_len) * 100, 2)
            print(f"            [{i}/{total_len}] Image of the {entity} {id} transfered ({perc} %)         ", end="\r", flush=True)

        i += 1

# --------------------------------------------------------------------------------------
# PROCESADO DE IMAGENES
# --------------------------------------------------------------------------------------
def main_image_transfer(manager_dict: dict, player_dict: dict, team_dict: dict, print_info: bool = True) -> None:

    start_time = time.time()

    if print_info:
        print(f"    6. Starting the image transfer part.")

    # Jugadores
    if print_info:
        print("         1. Starting the images transfer of players     ", flush=True, end="\r")
    move_all_images(entity="player", output_dir=os.path.join(OUTPUT_IMAGES_PATH, "player"), silver_df=silver_player, list_entities=player_dict.keys(), 
                    input_images_path=os.path.join(INPUT_IMAGES_PATH, "players"), default_image_path=DEFAULT_PLAYER, remove_background=True,
                    removed_back_dir=PLAYER_REM_BACK, print_info=print_info)
    
    # Equipos
    if print_info:
        print("         2. Starting the images transfer of teams     ", flush=True, end="\r")
    move_all_images(entity="team", output_dir=os.path.join(OUTPUT_IMAGES_PATH, "team"), silver_df=silver_team, list_entities=team_dict.keys(), 
                    input_images_path=os.path.join(INPUT_IMAGES_PATH, "teams"), default_image_path=DEFAULT_TEAM, remove_background=True,
                    removed_back_dir=TEAM_REM_BACK, print_info=print_info)
    
    # Entrenadores
    if print_info:
        print("         3. Starting the images transfer of managers     ", flush=True, end="\r")
    move_all_images(entity="manager", output_dir=os.path.join(OUTPUT_IMAGES_PATH, "manager"), silver_df=silver_manager, list_entities=manager_dict.keys(), 
                    input_images_path=os.path.join(INPUT_IMAGES_PATH, "managers"), default_image_path=DEFAULT_MANAGER, remove_background=True,
                    removed_back_dir=MANAGER_REM_BACK, print_info=print_info)