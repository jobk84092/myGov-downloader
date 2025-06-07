# auto_mygov_downloader.py
import os
import logging
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from datetime import datetime
from dateutil import parser as date_parser
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DOWNLOAD_DIR = "myGov Sept 2022-June 2025"
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_mygov_downloader.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def is_english_issue(filename):
    return not any(month.lower() in filename.lower() for month in SWAHILI_MONTHS)

def filename_from_url(url):
    name = unquote(url.split('/')[-1])
    return name.replace('%20', ' ')

def extract_date_from_filename(filename):
    # Try to extract a date from the filename using common MyGov patterns
    # e.g. MyGov April 29, 2025.pdf or MyGov 29th May 2023.pdf
    patterns = [
        r"MyGov ([A-Za-z]+ \d{1,2}, \d{4})",
        r"MyGov (\d{1,2}(?:st|nd|rd|th)? [A-Za-z]+ \d{4})"
    ]
    for pat in patterns:
        m = re.search(pat, filename)
        if m:
            try:
                # Remove ordinal suffixes (st, nd, rd, th)
                date_str = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', m.group(1))
                return date_parser.parse(date_str, fuzzy=True)
            except Exception:
                continue
    return None

def send_notification(title, message):
    try:
        subprocess.run([
            'osascript', '-e', f'display notification "{message}" with title "{title}"'
        ], check=True)
        logger.info("Desktop notification sent.")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def send_email(subject, body, to_email):
    gmail_user = os.environ.get('jobkimani@gmail.com')
    gmail_password = os.environ.get('ttyq hukc yxyq tium')
    if not gmail_user or not gmail_password:
        logger.error('GMAIL_USER or GMAIL_APP_PASSWORD environment variable not set.')
        return
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        logger.info(f"Notification email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def find_latest_pdf():
    latest = None
    latest_date = None
    for archive_url in ARCHIVE_URLS:
        try:
            logger.info(f"Scraping: {archive_url}")
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
                pdf_links.sort(reverse=True)  # Sort by date descending
                if not latest_date or pdf_links[0][0] > latest_date:
                    latest_date, latest_fname, latest_url = pdf_links[0]
                    latest = (latest_fname, latest_url)
        except Exception as e:
            logger.error(f"Error scraping {archive_url}: {e}")
    if latest:
        return latest
    return None, None

def download_pdf(url, filename):
    try:
        logger.info(f"Downloading {url} ...")
        resp = requests.get(url, stream=True, timeout=30, verify=False)
        if resp.status_code != 200:
            logger.error(f"Failed to download {url}: {resp.status_code}")
            return False
        if "pdf" not in resp.headers.get("Content-Type", "").lower():
            logger.error(f"Non-PDF content at {url}")
            return False
        out_path = os.path.join(DOWNLOAD_DIR, filename)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Saved to {out_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

def main():
    fname, url = find_latest_pdf()
    if not fname or not url:
        logger.warning("No current MyGov issue found.")
        send_notification("MyGov Downloader", "No current MyGov issue found.")
        return
    out_path = os.path.join(DOWNLOAD_DIR, fname)
    if os.path.exists(out_path):
        logger.info(f"Latest issue already downloaded: {fname}")
        send_notification("MyGov Downloader", f"Already downloaded: {fname}")
        return
    if download_pdf(url, fname):
        send_notification("MyGov Downloader", f"Downloaded: {fname}")
        send_email(
            subject="MyGov Downloader: New Issue Downloaded",
            body=f"Downloaded: {fname}",
            to_email="jobkimani@gmail.com"
        )
    else:
        send_notification("MyGov Downloader", f"Failed to download: {fname}")

if __name__ == "__main__":
    main()
