#!/usr/bin/env python3
import argparse
import os
import datetime
import json
import os.path
import sys
import shutil
from pathlib import Path
import time

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ZeitFetcher:
    def __init__(self, *, target_dir, username, password):
        self.target_dir = Path(target_dir)
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None

        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        options.binary_location = shutil.which("firefox-esr") or shutil.which("firefox")
        service = webdriver.FirefoxService(executable_path=shutil.which("geckodriver"))

        print("Initializing WebDriver...")
        self.driver = webdriver.Firefox(options=options, service=service)
        self.wait = WebDriverWait(self.driver, 20) # 20 second timeout for waits
        print("WebDriver initialized.")

    def do_login(self):
        """Logs into the ZEIT account."""
        print("Navigating to login page...")
        self.driver.get("https://meine.zeit.de/anmelden")

        try:
            user_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            user_field.send_keys(self.username)

            pass_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            pass_field.send_keys(self.password)

            submit_button = self.wait.until(EC.element_to_be_clickable((By.ID, "kc-login")))
            submit_button.click()
            print("Login submitted. Waiting for confirmation...")

            print("Waiting for login confirmation (URL change)... Requires manual CAPTCHA solving.")
            # Increased timeout to allow for manual CAPTCHA interaction.
            long_wait = WebDriverWait(self.driver, 120)
            long_wait.until(lambda d: 'zeit.de/konto' in d.current_url)
        except NoSuchElementException|TimeoutException as e:
            print(f"Login failed: Could not find login elements. Check selectors. {e}")
            self.driver.save_screenshot('zeit_login_error.png')
            raise
        except Exception as e:
            print(f"An unexpected error occurred during login: {e}")
            self.driver.save_screenshot('zeit_login_error.png')
            raise


    def fetch_zeit_issue(self, year, issue_number, ext=".pdf"):
        """Fetches a specific ZEIT edition by year and issue number (PDF by default)."""
        print(f"Attempting to fetch ZEIT issue {issue_number}/{year}...")

        # need to go to main page first before filter works
        self.driver.get("https://epaper.zeit.de/abo/diezeit") 

        if year is not None and issue_number is not None:
            filter_url = f"https://epaper.zeit.de/abo/diezeit?title=diezeit&issue={issue_number:02}&year={year}"
            self.driver.get(filter_url)

            issue_link_xpath = f"//section[contains(@class, 'archives')]//a[contains(@href, 'abo/diezeit')]"
        else:
            issue_link_xpath = f"//a[contains(text(), 'ZUR AKTUELLEN AUSGABE')]"

        issue_page_link_element = self.wait.until(EC.presence_of_element_located((By.XPATH, issue_link_xpath)))
        issue_page_url = issue_page_link_element.get_attribute('href')
        print(f"Found issue page URL: {issue_page_url}")

        print(f"Navigating to issue page: {issue_page_url}")
        self.driver.get(issue_page_url)

        title_xpath = "//p[contains(@class, 'epaper-info-title') and contains(text(), 'DIE ZEIT')]"
        title_element = self.wait.until(EC.presence_of_element_located((By.XPATH, title_xpath)))
        title_text = title_element.text

        if issue_number is None or year is None:
            edition = title_text.split(" ")[-1]
            issue_number, year = map(int, edition.split('/'))

        date_str_from_url = issue_page_url.split('/')[-1]
        parsed_date = None
        parsed_date = datetime.datetime.strptime(date_str_from_url, "%d.%m.%Y").date()
        fname = f"{parsed_date.isoformat()} Die Zeit {(year%2000):02}-{issue_number:02}{ext}"
        print(f"Determined filename: {fname}")

        download_link_xpath = f"//a[(contains(@href, 'download') or contains(@href, 'delivery')) and (contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{ext[1:].lower()}'))]"
        download_link_element = self.wait.until(EC.presence_of_element_located((By.XPATH, download_link_xpath)))
        download_url = download_link_element.get_attribute('href')
        print(f"Found download link: {download_url}")

        print(f"Attempting to download '{fname}' from {download_url}...")
        cookies = self.driver.get_cookies()
        s = requests.Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])
            
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'} # Mimic browser
        r = s.get(download_url, allow_redirects=True, stream=True, headers=headers)
        r.raise_for_status() # Check for download errors (4xx, 5xx)

        self.target_dir.mkdir(parents=True, exist_ok=True) # Ensure target dir exists
        path = self.target_dir / fname

        print(f"Saving to: {path}")
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        print("Download complete.")
        return fname

    def quit(self):
        """Closes the WebDriver."""
        if self.driver:
            print("Closing WebDriver...")
            self.driver.quit()
            self.driver = None
            print("WebDriver closed.")

def main():
    parser = argparse.ArgumentParser(description="Fetch a specific issue of DIE ZEIT e-paper.")
    parser.add_argument("--year", type=int, required=False, help="Year of the issue (e.g., 2025)")
    parser.add_argument("--issue", type=int, required=False, help="Issue number (e.g., 16)")
    parser.add_argument("--formats", default="pdf", help="Download formats, separated by spaces (pdf, epub)")
    parser.add_argument("--target-dir", default=os.getenv("TARGET_DIR", os.getcwd()), help="Directory to save the downloaded file.")
    parser.add_argument("--auth-file", default=os.getenv("ZEIT_AUTH_FILE", "zeit-auth.json"), help="Path to the JSON file containing 'user' and 'pass'.")

    args = parser.parse_args()

    target_dir = os.path.abspath(args.target_dir)
    auth_file = Path(args.auth_file)

    print(f"Target directory: {target_dir}")
    print(f"Auth file: {auth_file.resolve()}")

    if not auth_file.exists():
        print(f"Error: Auth file not found at '{auth_file.resolve()}'")
        print("Please create it with your ZEIT credentials in JSON format:")
        print('{\n  "user": "your_email@example.com",\n  "pass": "your_password"\n}')
        sys.exit(1)

    try:
        auth = json.loads(auth_file.read_text())
        if 'user' not in auth or 'pass' not in auth:
            raise ValueError("Auth file must contain 'user' and 'pass' keys.")
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from auth file '{auth_file.resolve()}'.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid auth file content: {e}")
        sys.exit(1)

    fetcher = None
    try:
        fetcher = ZeitFetcher(target_dir=target_dir, username=auth['user'], password=auth['pass'])
        fetcher.do_login()

        for fmt in args.formats.split(" "):
            print(f"Fetching issue: {args.issue}/{args.year}, Format: {fmt.upper()}")
            file_ext = "." + fmt

            downloaded_file = fetcher.fetch_zeit_issue(year=args.year, issue_number=args.issue, ext=file_ext)
            print(f"Successfully downloaded: {downloaded_file}")
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        # Error details should be printed within methods
        sys.exit(1) # Exit with error status
    finally:
        if fetcher:
            fetcher.quit()

if __name__ == '__main__':
    main()
