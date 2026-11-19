#!/usr/bin/env python3
import os
import datetime
import json
import os.path
import sys
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


class SpiegelFetcher:
    def __init__(self, *, target_dir, username, password):
        self.target_dir = target_dir
        self.username = username
        self.password = password

        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.binary_location = shutil.which("firefox-esr") or shutil.which("firefox")
        service = webdriver.FirefoxService(executable_path=shutil.which("geckodriver"))
        self.driver = webdriver.Firefox(options=options, service=service)

    def do_login(self):
        wait = WebDriverWait(self.driver, 30)
        self.driver.get("https://gruppenkonto.spiegel.de/anmelden.html")
        wait.until(expected_conditions.element_to_be_clickable((By.ID, "username"))).send_keys(self.username)
        self.driver.find_element(By.ID, "kc-login").click()
        wait.until(expected_conditions.element_to_be_clickable((By.ID, "password"))).send_keys(self.password)
        self.driver.find_element(By.ID, "kc-login").click()
        # The callback sets the session cookie; wait before handing it to requests.
        wait.until(lambda driver: (
            urlsplit(driver.current_url).hostname == "gruppenkonto.spiegel.de"
            and urlsplit(driver.current_url).path.startswith("/meinkonto/")
        ))

    def fetch_spiegel(self, heft):
        cookies = self.driver.get_cookies()
        _, year, number = heft.split('/')
        start_of_year = datetime.date(int(year), 1, 1)
        released_date = start_of_year  + datetime.timedelta(weeks=int(number)-2, days=(4 + (-start_of_year.weekday()) % 7) % 7)
        fname = f'{released_date.isoformat()} Der Spiegel {year[2:]}-{number}.pdf'
        path = os.path.join(self.target_dir, fname)
        with requests.Session() as session:
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'],
                                    domain=cookie['domain'], path=cookie['path'])
            with session.get(
                "https://gruppenkonto.spiegel.de/download/download.html",
                params={"heft": heft}, stream=True, timeout=60,
            ) as response:
                response.raise_for_status()
                chunks = response.iter_content(chunk_size=1 << 20)
                first_chunk = next(chunks, b"")
                if not first_chunk.startswith(b"%PDF-"):
                    raise RuntimeError("SPIEGEL did not return a PDF; check login and issue availability")
                with open(path, 'wb') as f:
                    f.write(first_chunk)
                    for chunk in chunks:
                        f.write(chunk)

        return fname

def main():
    target_dir = os.path.abspath(os.getcwd())
    auth = json.loads(Path(os.getenv("SPIEGEL_AUTH_FILE", "spiegel-auth.json")).read_text())
    fetcher = SpiegelFetcher(target_dir=target_dir, username=auth['user'], password=auth['pass'])

    d = datetime.datetime.now().isocalendar()
    year = d.year
    week = d.week
    if d.weekday >= 5:
        week += 1
    if week > 53:
        week = 1
        year += 1

    name = f"SP/{year}/{week}" if len(sys.argv) < 2 else "SP/" + sys.argv[1]
    try:
        fetcher.do_login()
        print(fetcher.fetch_spiegel(name))
    finally:
        fetcher.driver.quit()

if __name__ == '__main__':
    main()
