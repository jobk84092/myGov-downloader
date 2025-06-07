import os
import logging
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from datetime import datetime
from dateutil import parser as date_parser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

ARCHIVE_URLS = [
    "https://gaa.go.ke/index.php/mygov-newspaper-2024",
    "https://www.mygov.go.ke/mygov-newspaper-2024",
    "https://ict.go.ke/mygov-issues",
]
SWAHILI_MONTHS = [
    "Januari", "Februari", "Machi", "Aprili", "Mei", "Juni", "Julai", "Agosti", "Septemba", "Oktoba", "Novemba", "Desemba"
]
ENGLISH_MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
]

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
        try:
            logging.info(f"Scraping: {archive_url}")
            resp = requests.get(archive_url, timeout=30, verify=False)
            if resp.status_code != 200:
                continue
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
        except Exception as e:
            logging.error(f"Error scraping {archive_url}: {e}")
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
