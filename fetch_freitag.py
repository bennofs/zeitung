#!/usr/bin/env python3
import os
import datetime
import json
import os.path
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class FreitagFetcher:
    def __init__(self, *, target_dir, username, password):
        self.target_dir = target_dir
        self.username = username
        self.password = password

        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options, service_log_path=os.devnull)

    def do_login(self):
        self.driver.get("https://mein.freitag.de/login")
        frame = self.driver.find_element(By.XPATH, '//iframe[contains(@src, "plenigo")]')
        self.driver.switch_to.frame(frame)

        self.driver.find_element(By.ID, "login_form__username").send_keys(self.username)
        self.driver.find_element(By.ID, "login_form__password").send_keys(self.password)
        submit = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        submit.click()

        self.driver.switch_to.default_content()
        WebDriverWait(self.driver, 20).until(expected_conditions.url_contains("https://www.freitag.de"))

    def fetch_freitag(self, slug, ext=".epub"):
        cookies = self.driver.get_cookies()
        s = requests.Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        fname = f'der-freitag-{slug}.{ext}'
        r = s.get(
            f"https://www.freitag.de/ausgaben/{quote(slug)}/digital-download",
            params={'format': ext},
            allow_redirects=True
        )
        r.raise_for_status()

        path = os.path.join(self.target_dir, fname)
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1<<20):
                f.write(chunk)

        return fname

    def do_logout(self):
        self.driver.get('https://www.freitag.de/logout')


def main():
    target_dir = os.path.abspath(os.getcwd())
    auth = json.loads(Path(os.getenv("FREITAG_AUTH_FILE", "freitag-auth.json")).read_text())
    fetcher = FreitagFetcher(target_dir=target_dir, username=auth['user'], password=auth['pass'])

    d = datetime.datetime.now().isocalendar()
    week = d.week
    if d.weekday <= 3:
        week -= 1
    slug = f"{week:02}{d.year % 1000:02}"
    fetcher.do_login()

    exts = ["epub"]
    if len(sys.argv) > 1:
        exts = sys.argv[1:]
    for ext in exts:
        print(fetcher.fetch_freitag(slug, ext=ext))

    fetcher.do_logout()
    fetcher.driver.quit()

if __name__ == '__main__':
    main()
