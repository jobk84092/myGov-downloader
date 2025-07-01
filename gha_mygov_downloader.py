import os
import logging
import requests
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

ARCHIVE_URLS = [
    "https://www.mygov.go.ke/mygov-newspaper-2025"
]
SWAHILI_MONTHS = [
    "Januari", "Februari", "Machi", "Aprili", "Mei", "Juni", "Julai", "Agosti", "Septemba", "Oktoba", "Novemba", "Desemba"
]
ENGLISH_MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
]

RETRIES = 3
TIMEOUT = 10

def is_english_issue(filename):
    return not any(month.lower() in filename.lower() for month in SWAHILI_MONTHS)

def filename_from_url(url):
    name = unquote(url.split('/')[-1])
    return name.replace('%20', ' ')

def extract_date_from_filename(filename):
    patterns = [
        r"MyGov ([A-Za-z]+ \d{1,2}, \d{4})",
        r"MyGov (\d{1,2}(?:st|nd|rd|th)? [A-Za-z]+ \d{4})"
    ]
    for pat in patterns:
        m = re.search(pat, filename)
        if m:
            try:
                date_str = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', m.group(1))
                return date_parser.parse(date_str, fuzzy=True)
            except Exception:
                continue
    return None

def find_latest_pdf():
    latest = None
    latest_date = None
    for archive_url in ARCHIVE_URLS:
        for attempt in range(RETRIES):
            try:
                logging.info(f"Scraping: {archive_url} (attempt {attempt+1})")
                resp = requests.get(archive_url, timeout=TIMEOUT, verify=False)
                if resp.status_code != 200:
                    logging.warning(f"Failed to fetch {archive_url}: {resp.status_code}")
                    break
                soup = BeautifulSoup(resp.text, 'html.parser')
                pdf_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.lower().endswith('.pdf') and 'mygov' in href.lower():
                        fname = filename_from_url(href)
                        if is_english_issue(fname) and any(month in fname for month in ENGLISH_MONTHS):
                            file_date = extract_date_from_filename(fname)
                            if file_date:
                                pdf_links.append((file_date, fname, urljoin(archive_url, href)))
                if pdf_links:
                    pdf_links.sort(reverse=True)
                    if not latest_date or pdf_links[0][0] > latest_date:
                        latest_date, latest_fname, latest_url = pdf_links[0]
                        latest = (latest_fname, latest_url)
                    break  # Success, don't retry this URL
                else:
                    logging.warning(f"No PDF links found at {archive_url} (attempt {attempt+1})")
            except Exception as e:
                logging.error(f"Error scraping {archive_url} (attempt {attempt+1}): {e}")
                time.sleep(2)
    # Fallback: try to guess the direct PDF link for today (Tuesday) or the most recent Tuesday
    if not latest:
        today = datetime.today()
        # Find the most recent Tuesday (weekday=1)
        days_ago = (today.weekday() - 1) % 7
        last_tuesday = today if today.weekday() == 1 else today - timedelta(days=days_ago)
        fallback_month = last_tuesday.strftime('%B')
        fallback_day = last_tuesday.day
        fallback_year = last_tuesday.year
        fallback_fname = f"MyGov {fallback_day} {fallback_month} {fallback_year}.pdf"
        # Try all base URLs for a direct PDF link
        for base_url in [
            "https://www.mygov.go.ke/sites/default/files/",
            "https://gaa.go.ke/sites/default/files/",
            "https://ict.go.ke/sites/default/files/"
        ]:
            fallback_url = f"{base_url}{last_tuesday.strftime('%Y-%m')}/MyGov%20{fallback_day}%20{fallback_month}%20{fallback_year}.pdf"
            try:
                logging.info(f"Trying fallback direct PDF: {fallback_url}")
                resp = requests.get(fallback_url, timeout=TIMEOUT, verify=False)
                if resp.status_code == 200 and 'pdf' in resp.headers.get('Content-Type', '').lower():
                    return fallback_fname, fallback_url
            except Exception as e:
                logging.error(f"Error trying fallback direct PDF: {e}")
    if latest:
        return latest
    return None, None

def download_pdf(url, filename):
    try:
        logging.info(f"Downloading {url} ...")
        resp = requests.get(url, stream=True, timeout=30, verify=False)
        if resp.status_code != 200:
            logging.error(f"Failed to download {url}: {resp.status_code}")
            return False
        if "pdf" not in resp.headers.get("Content-Type", "").lower():
            logging.error(f"Non-PDF content at {url}")
            return False
        with open(filename, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
        logging.info(f"Saved to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        return False

def main():
    fname, url = find_latest_pdf()
    if not fname or not url:
        logging.warning("No current MyGov issue found.")
        return
    if os.path.exists(fname):
        logging.info(f"Latest issue already downloaded: {fname}")
        return
    if download_pdf(url, fname):
        logging.info(f"Downloaded: {fname}")
    else:
        logging.error(f"Failed to download: {fname}")

if __name__ == "__main__":
    main()
