#!/usr/bin/env python3
import os
import datetime
import json
import os.path
import shutil
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


class SpiegelFetcher:
    def __init__(self, *, target_dir, username, password):
        self.target_dir = target_dir
        self.username = username
        self.password = password

        options = webdriver.FirefoxOptions()
        options.headless = True
        self.driver = webdriver.Firefox(options=options, service_log_path=os.devnull)

    def do_login(self):
        self.driver.get("https://gruppenkonto.spiegel.de/anmelden.html")
        self.driver.find_element(By.ID, "loginname").click()
        self.driver.find_element(By.ID, "loginname").send_keys(self.username)
        self.driver.find_element(By.ID, "password").send_keys(self.password)
        self.driver.find_element(By.ID, "submit").click()

    def fetch_spiegel(self, heft):
        cookies = self.driver.get_cookies()
        s = requests.Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        fname = heft.replace('/', '_') + ".pdf"
        r = s.get("https://gruppenkonto.spiegel.de/download/download.html?heft=" + quote(heft), allow_redirects=True)
        r.raise_for_status()

        path = os.path.join(self.target_dir, fname)

        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1<<20):
                f.write(chunk)

        return fname

def main():
    target_dir = os.path.abspath(os.getcwd())
    auth = json.loads(Path(os.getenv("SPIEGEL_AUTH_FILE", "spiegel-auth.json")).read_text())
    fetcher = SpiegelFetcher(target_dir=target_dir, username=auth['user'], password=auth['pass'])

    d = datetime.datetime.now().isocalendar()
    name = f"SP/{d.year}/{d.week + 1}"
    fetcher.do_login()
    print(fetcher.fetch_spiegel(name))
    fetcher.driver.quit()

if __name__ == '__main__':
    main()
