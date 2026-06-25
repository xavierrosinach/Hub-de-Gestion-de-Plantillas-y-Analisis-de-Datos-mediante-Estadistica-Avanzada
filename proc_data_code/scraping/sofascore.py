import os
import time

from scraping.scrapers import SofascoreScraper
scraper = SofascoreScraper(warmup_url="https://www.sofascore.com/")

from use.config import COMPS, DATA_PATH
from use.functions import safe_json_dump, create_slug, need_to_upload, elapsed_time_str, json_to_dict

RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
os.makedirs(RAW_DATA_PATH, exist_ok=True)

# --------------------------------------------------------------------------------------
# Obtención de las temporadas disponibles por liga
# --------------------------------------------------------------------------------------
def get_league_available_seasons(league_ss_id: int, league_path: str) -> dict:

    # Obtención del JSON con las temporadas disponibles de la liga
    season_path = os.path.join(league_path, "seasons.json")
    if os.path.exists(season_path) and not need_to_upload(path=season_path, total_days=30):
        season_dict = json_to_dict(json_path=season_path)
    else:
        season_dict = scraper.scrape(url=f"https://api.sofascore.com/api/v1/unique-tournament/{league_ss_id}/seasons/")
        if not season_dict.get("seasons"):
            if os.path.exists(season_path):
                season_dict = json_to_dict(json_path=season_path)
            else:
                season_dict = {}
        else:
            safe_json_dump(data=season_dict, path=season_path)
    
    return season_dict

# --------------------------------------------------------------------------------------
# Otbtenemos la información de los partidos
# --------------------------------------------------------------------------------------
def get_season_matches(league_id: int, season_id: int, matches_path: str) -> dict:

    # URL base
    url_base = f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/events/last/"

    # Vamos a ir iterando hasta que no encontramos información
    block_id = 0
    blocks_dict = {}
    while True:
        out_path = os.path.join(matches_path, f"{block_id}.json")
        url = f"{url_base}{block_id}"

        # Procedemos a hacer el scraping
        scraped_url = scraper.scrape(url=url)
        if not scraped_url.get("events"):
            if os.path.exists(out_path):
                match_dict = json_to_dict(json_path=out_path)
            else:
                break
        else:
            safe_json_dump(data=scraped_url, path=out_path)
            match_dict = scraped_url

        # Añadimos al diccionario y iteramos
        blocks_dict[block_id] = match_dict
        block_id += 1

    return blocks_dict

# --------------------------------------------------------------------------------------
# Otbtenemos la información de la liga
# --------------------------------------------------------------------------------------
def get_season_info(league_id: int, season_id: int, info_path: str) -> dict:

    # Diccionario con los URLs a scrapear
    info_urls = {"players": f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/players",
                 "teams": f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/teams",
                 "venues": f"https://api.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/venues"}
    
    output_dict = {}

    # Para cada tipo, obtenemos la información
    for entity, ent_url in info_urls.items():
        output_path = os.path.join(info_path, f"{entity}.json")

        # Actualizamos a los 30 días
        if os.path.exists(output_path) and not need_to_upload(path=output_path, total_days=30):
            entity_dict = json_to_dict(json_path=output_path)
        else:
            entity_dict = scraper.scrape(url=ent_url)
            if not entity_dict.get(entity):
                if os.path.exists(output_path):
                    entity_dict = json_to_dict(json_path=output_path)
                else:
                    entity_dict = {}
            else:
                safe_json_dump(data=entity_dict, path=output_path)
        
        # Añadimos al diccionario
        if len(entity_dict) > 0:
            output_dict[entity] = entity_dict
    
    return output_dict

# --------------------------------------------------------------------------------------
# Otbtenemos información de un partido
# --------------------------------------------------------------------------------------
def get_single_match_info(match_id: int, match_out_path: str) -> dict:

    # Creación de la carpeta si no existe
    os.makedirs(match_out_path, exist_ok=True)

    # Obtenemos el URL de distintos ámbitos
    dict_urls = {"info": f"https://api.sofascore.com/api/v1/event/{match_id}",
                 "lineups": f"https://api.sofascore.com/api/v1/event/{match_id}/lineups",
                 "stats": f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"}
    
    # Claves a comprovar para guardar JSONS
    dict_info_to_check = {"info": "event",
                          "lineups": "confirmed",
                          "stats": "statistics"}
    
    output_dict = {}
    for type_info, url in dict_urls.items():
        output_path = os.path.join(match_out_path, f"{type_info}.json")
        if os.path.exists(output_path):
            output_dict[type_info] = json_to_dict(json_path=output_path)
        else:
            scraped_dict = scraper.scrape(url=url)
            if scraped_dict.get(dict_info_to_check[type_info]):
                output_dict[type_info] = scraped_dict
                safe_json_dump(data=scraped_dict, path=output_path)
    
    return output_dict

# --------------------------------------------------------------------------------------
# Otbtenemos información de una entidad (equipo, jugador o manager)
# --------------------------------------------------------------------------------------
def get_entity_info(entity_id: int, entity_type: str, output_path: str) -> dict:

    # Obtenemos el url
    info_url = f"https://api.sofascore.com/api/v1/{entity_type}/{entity_id}"

    # Actualizamos a los 30 días
    if os.path.exists(output_path) and not need_to_upload(path=output_path, total_days=30):
        entity_dict = json_to_dict(json_path=output_path)
    else:
        entity_dict = scraper.scrape(url = info_url)
        if not entity_dict.get(entity_type):
            if os.path.exists(output_path):
                entity_dict = json_to_dict(json_path=output_path)
            else:
                entity_dict = {}
        else:
            safe_json_dump(data=entity_dict, path=output_path)

    return entity_dict

# --------------------------------------------------------------------------------------
# Main scraping de una liga en Sofascore
# --------------------------------------------------------------------------------------
def main_league_scraping(league_id: int, print_info: bool = True) -> None:

    start_time = time.time()

    # Información de la liga y creación de una carpeta
    league_str = COMPS[COMPS["id"] == league_id]["tournament"].iloc[0]
    league_sofascore_id = COMPS[COMPS["id"] == league_id]["sofascore"].iloc[0]
    league_slug = create_slug(text=league_str)
    league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)
    os.makedirs(league_path, exist_ok=True)

    # Obtenemos temporadas disponibles
    available_seasons = get_league_available_seasons(league_ss_id=league_sofascore_id, league_path=league_path)

    # Obtenemos los IDs de las dos temporadas que buscamos
    season_id_dict = {"2526": available_seasons.get("seasons", [])[0].get("id", None), 
                      "2425": available_seasons.get("seasons", [])[1].get("id", None)}

    # Entramos dentro de cada temporada
    for season_id, season_code in season_id_dict.items():

        start_time = time.time()

        if print_info:
            print(f"{league_str} main league Sofascore scraping (season {season_id})                                                                                         ")

        # Creamos carpeta
        season_path = os.path.join(league_path, season_id, "sofascore")
        os.makedirs(season_path, exist_ok=True)

        # Carpeta de partidos y de información
        matches_path = os.path.join(season_path, "matches")
        info_path = os.path.join(season_path, "info")
        os.makedirs(matches_path, exist_ok=True)
        os.makedirs(info_path, exist_ok=True)

        if print_info:
            print(f"        1. Season info scraping for league {league_str} season {season_id}.                                                                             ")

        # Obtenemos información de la temporada
        season_info = get_season_info(league_id=league_sofascore_id, season_id=season_code, info_path=info_path) 
        players_ids = [player.get("playerId") for player in season_info.get("players", {}).get("players", [])]
        teams_ids = [player.get("id") for player in season_info.get("teams", {}).get("teams", [])]
        venues_ids = [player.get("id") for player in season_info.get("venues", {}).get("venues", [])]

        if print_info:
            print(f"        2. Matches info scraping for league {league_str} season {season_id}.                                                                             ")

        # Obtenemos los partidos de la temporada
        season_matches = get_season_matches(league_id=league_sofascore_id, season_id=season_code, matches_path=matches_path)
        matches_ids = list({event.get("id") for block in season_matches.values() for event in block.get("events", [])})

        if print_info:
            print(f"        3. Matches detailed info scraping for league {league_str} season {season_id}.                                                                             ")
            i = 1
            total_matches = len(matches_ids)
            

        # Para cada partido, obtenemos información
        if len(matches_ids) > 0:
            matches_info_dict = {}
            for match_id in matches_ids:

                if print_info:
                    print(f"            [{i}/{total_matches}] Scraping match {match_id} of league {league_str} season {season_id}", flush=True, end="\r")
                    i += 1

                match_info = get_single_match_info(match_id=int(match_id), match_out_path=os.path.join(matches_path, str(match_id)))
                if len(match_info) > 0:
                    matches_info_dict[match_id] = match_info

        # Listado de entrenadores de la liga
        managers_ids = []
        for match_info in matches_info_dict.values():
            home_manager_id = (match_info.get("info", {}).get("event", {}).get("homeTeam", {}).get("manager", {}).get("id"))
            away_manager_id = (match_info.get("info", {}).get("event", {}).get("awayTeam", {}).get("manager", {}).get("id"))
            managers_ids.extend([manager_id for manager_id in [home_manager_id, away_manager_id] if manager_id is not None])

        # Carpetas de entidades
        entities_path = os.path.join(RAW_DATA_PATH, "entities")
        manager_ent_path = os.path.join(entities_path, "manager")
        player_ent_path = os.path.join(entities_path, "player")
        team_ent_path = os.path.join(entities_path, "team")
        for path in [entities_path, manager_ent_path, player_ent_path, team_ent_path]:
            os.makedirs(path, exist_ok=True)

        if print_info:
            print(f"        4. Players info scraping for league {league_str} season {season_id}.                                                                             ")
            i = 1
            total_players = len(players_ids)

        # Obtenemos información de jugadores
        if len(players_ids):
            players_info_dict = {}
            for player_id in players_ids:

                if print_info:
                    print(f"            [{i}/{total_players}] Scraping player {player_id} of league {league_str} season {season_id}", flush=True, end="\r")
                    i += 1

                player_info = get_entity_info(entity_id=int(player_id), entity_type="player", output_path=os.path.join(player_ent_path, f"{player_id}.json"))
                if len(player_info) > 0:
                    players_info_dict[player_id] = player_info

        if print_info:
            print(f"        5. Teams info scraping for league {league_str} season {season_id}.                                                                             ")
            i = 1
            total_teams = len(teams_ids)

        # Obtenemos información de equipos
        if len(teams_ids):
            teams_info_dict = {}
            for team_id in teams_ids:

                if print_info:
                    print(f"            [{i}/{total_teams}] Scraping team {team_id} of league {league_str} season {season_id}", flush=True, end="\r")
                    i += 1

                team_info = get_entity_info(entity_id=int(team_id), entity_type="team", output_path=os.path.join(team_ent_path, f"{team_id}.json"))
                if len(team_info) > 0:
                    teams_info_dict[team_id] = team_info

        if print_info:
            print(f"        6. Managers info scraping for league {league_str} season {season_id}.                                                                             ")
            i = 1
            total_managers = len(managers_ids)

        # Obtenemos información de entrenadores
        if len(managers_ids):
            managers_info_dict = {}
            for manager_id in managers_ids:

                if print_info:
                    print(f"            [{i}/{total_managers}] Scraping manager {manager_id} of league {league_str} season {season_id}", flush=True, end="\r")
                    i += 1

                manager_info = get_entity_info(entity_id=int(manager_id), entity_type="manager", output_path=os.path.join(manager_ent_path, f"{manager_id}.json"))
                if len(manager_info) > 0:
                    managers_info_dict[manager_id] = manager_info
        
        if print_info:
            print(f"{league_str} main league Sofascore scraping (season {season_id}) finished in {elapsed_time_str(start_time=start_time)}.")