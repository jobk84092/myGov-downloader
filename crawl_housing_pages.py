import os
import re
import sys
import asyncio
import requests
import logging
import time
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from googlesearch import search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
RATE_LIMIT_DELAY = 2  # seconds between requests

# GAA MyGov archive pages for 2022-2025
ARCHIVE_URLS = [
    "https://gaa.go.ke/index.php/mygov-newspaper-2022",
    "https://gaa.go.ke/index.php/mygov-newspaper-2023",
    "https://gaa.go.ke/index.php/mygov-newspaper-2024",
    "https://gaa.go.ke/index.php/mygov-newspaper-2025",
]

# mygov.go.ke archive pages for 2022-2025
MYGOV_ARCHIVE_URLS = [
    "https://www.mygov.go.ke/mygov-newspaper-2022",
    "https://www.mygov.go.ke/mygov-newspaper-2023",
    "https://www.mygov.go.ke/mygov-newspaper-2024",
    "https://www.mygov.go.ke/mygov-newspaper-2025",
]

# ict.go.ke archive pages
ICT_ARCHIVE_URLS = [
    "https://ict.go.ke/mygov-issues",
]

# Swahili month names to exclude
SWAHILI_MONTHS = ["Januari", "Februari", "Machi", "Aprili", "Mei"]

# Date range for missing issues
START_DATE = datetime(2022, 9, 6)
END_DATE = datetime(2025, 5, 27)

def generate_tuesdays(start, end):
    current = start
    if current.weekday() != 1:
        current += timedelta(days=(1 - current.weekday()) % 7)
    while current <= end:
        yield current
        current += timedelta(weeks=1)

def get_existing_english_files():
    files = set()
    for f in os.listdir(DOWNLOAD_DIR):
        if f.lower().endswith('.pdf') and 'mygov' in f.lower():
            if not any(month.lower() in f.lower() for month in SWAHILI_MONTHS):
                files.add(f)
    return files

def is_english_issue(filename):
    return not any(month.lower() in filename.lower() for month in SWAHILI_MONTHS)

def download_pdf(url, filename):
    try:
        logger.info(f"Downloading {url} ...")
        response = requests.get(url, stream=True, timeout=30, verify=False)
        if response.status_code != 200:
            logger.error(f"Error: {url} returned status code {response.status_code}")
            return False
        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" not in content_type:
            logger.error(f"Error: {url} returned non-PDF Content-Type: {content_type}")
            return False
        out_filename = os.path.join(DOWNLOAD_DIR, filename)
        with open(out_filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Downloaded: {url} -> {out_filename}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

def extract_pdf_links_from_archive(archive_url):
    try:
        logger.info(f"Scraping archive page: {archive_url}")
        response = requests.get(archive_url, verify=False)
        if response.status_code != 200:
            logger.error(f"Failed to fetch {archive_url}: Status code {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf') and 'mygov' in href.lower():
                if is_english_issue(href):
                    links.append(urljoin(archive_url, href))
        logger.info(f"Found {len(links)} PDF links on {archive_url}")
        for link in links:
            logger.debug(f"PDF link: {link}")
        return links
    except Exception as e:
        logger.error(f"Error extracting links from {archive_url}: {e}")
        return []

def extract_pdf_links_from_mygov(archive_url):
    try:
        logger.info(f"Scraping mygov.go.ke page: {archive_url}")
        response = requests.get(archive_url, verify=False)
        if response.status_code != 200:
            logger.error(f"Failed to fetch {archive_url}: Status code {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf') and 'mygov' in href.lower():
                if is_english_issue(href):
                    links.append(urljoin(archive_url, href))
        logger.info(f"Found {len(links)} PDF links on {archive_url}")
        return links
    except Exception as e:
        logger.error(f"Error extracting links from {archive_url}: {e}")
        return []

def extract_pdf_links_from_ict(archive_url):
    try:
        logger.info(f"Scraping ict.go.ke page: {archive_url}")
        response = requests.get(archive_url, verify=False)
        if response.status_code != 200:
            logger.error(f"Failed to fetch {archive_url}: Status code {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf') and 'mygov' in href.lower():
                if is_english_issue(href):
                    links.append(urljoin(archive_url, href))
        logger.info(f"Found {len(links)} PDF links on {archive_url}")
        return links
    except Exception as e:
        logger.error(f"Error extracting links from {archive_url}: {e}")
        return []

def filename_from_url(url):
    name = unquote(url.split('/')[-1])
    return name.replace('%20', ' ')

def google_search_pdf_link(date):
    """Search Google for a MyGov PDF for a specific date."""
    query = f"MyGov Digital Newspaper {date.strftime('%B %d, %Y')} pdf"
    logger.info(f"Google searching for: {query}")
    try:
        for url in search(query, num_results=10, lang="en"):
            if url.lower().endswith('.pdf') and 'mygov' in url.lower():
                logger.info(f"Google found PDF: {url}")
                return url
    except Exception as e:
        logger.error(f"Google search failed for {query}: {e}")
    return None

def main():
    # Get all expected Tuesday filenames
    expected_filenames = set()
    date_map = {}
    for date in generate_tuesdays(START_DATE, END_DATE):
        fname = f"MyGov {date.strftime('%B %d, %Y')}.pdf"
        expected_filenames.add(fname)
        date_map[fname] = date
    # Get already downloaded English files
    existing_files = get_existing_english_files()
    # Scrape all sources for English MyGov PDFs
    found_links = {}
    # GAA
    for archive_url in ARCHIVE_URLS:
        links = extract_pdf_links_from_archive(archive_url)
        for link in links:
            fname = filename_from_url(link)
            if is_english_issue(fname):
                found_links[fname] = link
        logger.info(f"Total unique English PDF links found so far: {len(found_links)}")
        time.sleep(RATE_LIMIT_DELAY)
    # mygov.go.ke
    for archive_url in MYGOV_ARCHIVE_URLS:
        links = extract_pdf_links_from_mygov(archive_url)
        for link in links:
            fname = filename_from_url(link)
            if is_english_issue(fname) and fname not in found_links:
                found_links[fname] = link
        logger.info(f"Total unique English PDF links found so far: {len(found_links)}")
        time.sleep(RATE_LIMIT_DELAY)
    # ict.go.ke
    for archive_url in ICT_ARCHIVE_URLS:
        links = extract_pdf_links_from_ict(archive_url)
        for link in links:
            fname = filename_from_url(link)
            if is_english_issue(fname) and fname not in found_links:
                found_links[fname] = link
        logger.info(f"Total unique English PDF links found so far: {len(found_links)}")
        time.sleep(RATE_LIMIT_DELAY)
    # Download missing files
    missing = expected_filenames - existing_files
    logger.info(f"Total missing English MyGov issues: {len(missing)}")
    missing_no_link = 0
    for fname in sorted(missing):
        if fname in found_links:
            download_pdf(found_links[fname], fname)
            time.sleep(RATE_LIMIT_DELAY)
        else:
            # Try Google search fallback
            try:
                date_obj = date_map.get(fname)
                if date_obj:
                    pdf_url = google_search_pdf_link(date_obj)
                    if pdf_url:
                        download_pdf(pdf_url, fname)
                        time.sleep(RATE_LIMIT_DELAY)
                        continue
            except Exception as e:
                logger.error(f"Error in Google search fallback for {fname}: {e}")
            logger.warning(f"No link found for {fname}")
            missing_no_link += 1
    logger.info(f"Done. {missing_no_link} missing issues had no link found.")

if __name__ == "__main__":
    main()
