import re
import time
import json as jsonlib
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Scraper de Scoresway
class ScoreswayScraper:

    DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " 
                  "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
    JSONP_RE = re.compile(r"^[\w$]+\((.*)\)\s*;?\s*$", flags=re.DOTALL)

    # Inicialización del scraper
    def __init__(self, referer: str = "https://www.scoresway.com/", sleep_time: int = 3):
        self.referer = referer
        self.sleep_time = sleep_time
        self.session = requests.Session()
        self.session.headers.update({"user-agent": self.DEFAULT_UA,
                                     "referer": referer,
                                     "accept": "*/*",
                                     "accept-language": "en-US,en;q=0.9",
                                     "connection": "keep-alive"})
        self._warmed_up = False

    # Visita al referer para establecer las cookies de la sesión
    def _warmup(self):
        try:
            self.session.get(self.referer, timeout=20)
            self._warmed_up = True
        except requests.RequestException:
            pass

    # Scraping
    def scrape(self, url: str, referer: str | None = None) -> dict:
        if not self._warmed_up:
            self._warmup()
        headers = {"referer": referer} if referer else None
        r = self.session.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return {}
        match = self.JSONP_RE.match(r.text.strip())
        if not match:
            return {}
        json_str = match.group(1)
        time.sleep(self.sleep_time)
        return jsonlib.loads(json_str)

    # Cierre
    def close(self):
        self.session.close()

    # Soporte para 'with ScoreswayScraper() as s:'
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.close()


# Scraper de Sofascore (páginas JSON renderizadas vía Selenium)
class SofascoreScraper:

    # Inicialización del scraper
    def __init__(self, sleep_time: int = 3, timeout: int = 10,
                 warmup_url: str | None = None, headless: bool = True):
        self.sleep_time = sleep_time
        self.timeout = timeout

        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=options)

        # "Warmup": carga inicial para establecer la sesión del navegador
        if warmup_url:
            self.driver.get(warmup_url)
            time.sleep(5)

    # Scraping: accede a la URL y devuelve el JSON renderizado dentro del <pre>
    def scrape(self, url: str, sleep_time: int | None = None,
               timeout: int | None = None) -> dict:
        sleep_time = self.sleep_time if sleep_time is None else sleep_time
        timeout = self.timeout if timeout is None else timeout

        try:
            self.driver.get(url)
            pre = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            data_json = jsonlib.loads(pre.text)
            time.sleep(sleep_time)
            return data_json
        except Exception:
            return {}

    # Cierre del navegador
    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    # Soporte para 'with SofascoreScraper() as s:'
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.close()