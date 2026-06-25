import os
import time

from scraping.scrapers import ScoreswayScraper
scraper = ScoreswayScraper()

from use.config import COMPS, ACT_SEASON, DATA_PATH
from use.functions import safe_json_dump, create_slug, need_to_upload, elapsed_time_str, json_to_dict

RAW_DATA_PATH = os.path.join(DATA_PATH, "raw")
os.makedirs(RAW_DATA_PATH, exist_ok=True)

# --------------------------------------------------------------------------------------
# Scraping de los partidos de una liga en una temporada
# --------------------------------------------------------------------------------------
def scrape_season_matches(season_code: str, season_path: str) -> dict:

    # Definición del output path
    output_path = os.path.join(season_path, "matches.json")

    # Comprovamos si es la temporada actual
    season_key = os.path.basename(season_path)
    is_act_season = 1 if str(season_key) == str(ACT_SEASON) else 0

    # Si no es la temporada actual, scraping en caso que no exista
    if not is_act_season:
        if os.path.exists(output_path):
            matches_dict = json_to_dict(json_path=output_path)
        else:
            matches_dict = scraper.scrape(f'https://api.performfeeds.com/soccerdata/match/ft1tiv1inq7v1sk3y9tv12yh5/?_rt=c&tmcl={season_code}&live=yes&_pgSz=400&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=cb')
            if matches_dict.get("match"):
                safe_json_dump(data=matches_dict, path=output_path)
            else:
                matches_dict = {}

    # Si es la temporada actual, comprovamos si se tiene que actualizar
    else:
        if os.path.exists(output_path) and not need_to_upload(path=output_path, total_days=3):
            matches_dict = json_to_dict(json_path=output_path)
        else:
            matches_dict = scraper.scrape(f'https://api.performfeeds.com/soccerdata/match/ft1tiv1inq7v1sk3y9tv12yh5/?_rt=c&tmcl={season_code}&live=yes&_pgSz=400&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=cb')
            if matches_dict.get("match"):
                safe_json_dump(data=matches_dict, path=output_path)
            else:
                matches_dict = {}
    
    return matches_dict

# --------------------------------------------------------------------------------------
# Scraping de las plantillas de una liga en una temporada
# --------------------------------------------------------------------------------------
def scrape_season_squads(season_code: str, season_path: str) -> dict:

    # Definición del output path
    output_path = os.path.join(season_path, "squads.json")

    # Comprovamos si es la temporada actual
    season_key = os.path.basename(season_path)
    is_act_season = 1 if str(season_key) == str(ACT_SEASON) else 0

    # Si no es la temporada actual, scraping en caso que no exista
    if not is_act_season:
        if os.path.exists(output_path):
            squads_dict = json_to_dict(json_path=output_path)
        else:
            squads_dict = scraper.scrape(f'https://api.performfeeds.com/soccerdata/squads/ft1tiv1inq7v1sk3y9tv12yh5/?_rt=c&tmcl={season_code}&live=yes&_pgSz=400&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=cb')
            if squads_dict.get("squad"):
                safe_json_dump(data=squads_dict, path=output_path)
            else:
                squads_dict = {}

    # Si es la temporada actual, comprovamos si se tiene que actualizar
    else:
        if os.path.exists(output_path) and not need_to_upload(path=output_path, total_days=3):
            squads_dict = json_to_dict(json_path=output_path)
        else:
            squads_dict = scraper.scrape(f'https://api.performfeeds.com/soccerdata/squads/ft1tiv1inq7v1sk3y9tv12yh5/?_rt=c&tmcl={season_code}&live=yes&_pgSz=400&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=cb')
            if squads_dict.get("squad"):
                safe_json_dump(data=squads_dict, path=output_path)
            else:
                squads_dict = {}
    
    return squads_dict

# --------------------------------------------------------------------------------------
# Scraping de la información de un simple partido
# --------------------------------------------------------------------------------------
def scrape_single_match(match_id: str, matches_path: str) -> dict:

    # Comprovamos que existe y lo registramos
    output_path = os.path.join(matches_path, f"{match_id}.json")
    if os.path.exists(output_path):
        match_dict = json_to_dict(json_path=output_path)
    else:
        match_dict = scraper.scrape(url=f'https://api.performfeeds.com/soccerdata/matchstats/ft1tiv1inq7v1sk3y9tv12yh5/{match_id}?_rt=c&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=cb')
        if match_dict.get("matchInfo"):
            safe_json_dump(data=match_dict, path=output_path)
        else:
            match_dict = {}

    return match_dict

# --------------------------------------------------------------------------------------
# Main scraping de una liga en Scoresway
# --------------------------------------------------------------------------------------
def main_league_scraping(league_id: int, print_info: bool = True) -> None:

    start_time = time.time()

    # Información de la liga y creación de una carpeta
    league_str = COMPS[COMPS["id"] == league_id]["tournament"].iloc[0]
    league_slug = create_slug(text=league_str)
    league_path = os.path.join(RAW_DATA_PATH, "competitions", league_slug)
    os.makedirs(league_path, exist_ok=True)

    # Obtenemos los identificadores de la liga según temporada, y los añadimos a un diccionairo
    league_id_dict = {"2425": str(COMPS[COMPS["tournament"] == league_str]["scoresway2425"].iloc[0]), 
                      "2526": str(COMPS[COMPS["tournament"] == league_str]["scoresway2526"].iloc[0])}

    # Para cada una de las dos temporadas
    for season_key, season_code in league_id_dict.items():

        start_time = time.time()

        if print_info:
            print(f"{league_str} main league Scoresway scraping (season {season_key})                                                                                         ")

        # Directorio y creación de la carpeta
        season_path = os.path.join(league_path, str(season_key), "scoresway")
        os.makedirs(season_path, exist_ok=True)

        # Obtención de los partidos (info) de la temporada
        if print_info:
            print(f"        1. Matches info scraping for league {league_str} season {season_key}.                                                                             ")
        matches = scrape_season_matches(season_code=season_code, season_path=season_path)

        # Obtención de las plantillas de la temporada
        if print_info:
            print(f"        2. Squads info scraping for league {league_str} season {season_key}.                                                                              ")
        squads = scrape_season_squads(season_code=season_code, season_path=season_path)

        # Obtención de los partidos individualmente
        if len(matches) > 0:

            if print_info:
                print(f"        3. Matches detailed info scraping for league {league_str} season {season_key}.                                                                ")

            # Creamos carpeta de partidos si no existe
            matches_path = os.path.join(season_path, "matches")

            # Obtenemos partidos jugados
            played_matches = {m.get('matchInfo', {}).get('id'):f"{m.get('matchInfo', {}).get('contestant', [{}])[0].get('name','')}-{m.get('matchInfo', {}).get('contestant', [{},{}])[1].get('name','')}".lower().replace(' ', '-')
                            for m in matches.get('match', []) if m.get('liveData', {}).get('matchDetails', {}).get('matchStatus')=='Played'}
            
            if print_info:
                i = 1
                total_matches = len(played_matches)
            
            # Para cada partido, aplicamos
            matches_info = {}
            for match_id, match_contestants in played_matches.items():
                if print_info:
                    print(f"            [{i}/{total_matches}] Scraping match {match_contestants} of league {league_str} season {season_key}", flush=True, end="\r")
                    i += 1

                match_scraped = scrape_single_match(match_id=match_id, matches_path=matches_path)
                if match_scraped.get("matchInfo"):
                    matches_info[match_id] = match_scraped

        if print_info:
            print(f"{league_str} main league Scoresway scraping (season {season_key}) finished in {elapsed_time_str(start_time=start_time)}.")