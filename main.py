import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, unquote, urlparse
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
import json
import re
import time

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---- CONFIG ----
TARGET_DIR = "downloads"
DRIVE_FOLDER_ID = "19fu-mfAfTPBvXdjPVKdMdgOCq4neCDqy"
MANIFEST_PATH = "archive_manifest.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

ARCHIVE_URLS = [
    # This page currently exposes the most complete cross-year index.
    "https://ict.go.ke/index.php/mygov-issues",
    "https://www.mygov.go.ke/{year}-issues",
    "https://www.mygov.go.ke/mygov-newspaper-{year}",
    "https://mygov.go.ke/index.php/mygove-issue-{year}",
    "https://gaa.go.ke/index.php/mygov-newspaper-{year}",
    "https://ict.go.ke/node/941",
]

SWAHILI_MONTHS = [
    "Januari", "Februari", "Machi", "Aprili", "Mei", "Juni",
    "Julai", "Agosti", "Septemba", "Oktoba", "Novemba", "Desemba"
]
ENGLISH_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}

RETRIES = 3
TIMEOUT = 15
START_DATE = datetime(2022, 9, 1)
USER_AGENT = "Mozilla/5.0 (compatible; MyGovArchiveBot/1.0)"


def is_english_issue(filename):
    return not any(month.lower() in filename.lower() for month in SWAHILI_MONTHS)


def filename_from_url(url):
    name = unquote(urlparse(url).path.split('/')[-1])
    return re.sub(r"_\d+(?=\.pdf$)", "", name, flags=re.IGNORECASE)


def canonical_pdf_url(archive_url, href):
    """Build a usable PDF URL, repairing bad /index.php/sites links."""
    full_url = urljoin(archive_url, href)
    parsed = urlparse(full_url)
    path = parsed.path.replace('/index.php/sites/default/files/', '/sites/default/files/')
    return parsed._replace(path=path).geturl()


def parse_date_from_filename(filename):
    """Extract date from MyGov PDF filename."""
    patterns = [
        r"MyGov\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})",
        r"MyGov\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            groups = m.groups()
            try:
                if groups[0].isdigit():
                    day = int(groups[0])
                    month_str = groups[1].lower().strip()
                    year = int(groups[2])
                else:
                    month_str = groups[0].lower().strip()
                    day = int(groups[1])
                    year = int(groups[2])
                month = MONTH_MAP.get(month_str)
                if month:
                    return datetime(year, month, day)
            except Exception:
                continue
    return None


def is_actual_newspaper(filename):
    """Filter out non-newspaper PDFs (tenders, procurement docs, etc.)."""
    fname_lower = filename.lower()
    if not fname_lower.endswith('.pdf'):
        return False
    if 'mygov' not in fname_lower:
        return False
    exclude_keywords = ['provision', 'tender', 'procurement', 'monitoring', 'services']
    if any(kw in fname_lower for kw in exclude_keywords):
        return False
    if not any(month.lower() in fname_lower for month in ENGLISH_MONTHS + SWAHILI_MONTHS):
        return False
    return True


def issue_is_in_scope(file_date):
    return START_DATE.date() <= file_date.date() <= datetime.now().date()


def scrape_archive_links(backfill=False):
    """Return English MyGov issues keyed by publication date."""
    now = datetime.now()
    years = range(START_DATE.year, now.year + 1) if backfill else [now.year, now.year - 1]
    all_links = {}

    for url_template in ARCHIVE_URLS:
        urls_to_try = (
            [url_template.format(year=y) for y in years]
            if '{year}' in url_template else [url_template]
        )
        for archive_url in urls_to_try:
            for attempt in range(RETRIES):
                try:
                    logger.info(f"Scraping: {archive_url} (attempt {attempt + 1})")
                    resp = requests.get(
                        archive_url,
                        timeout=TIMEOUT,
                        verify=False,
                        headers={'User-Agent': USER_AGENT},
                    )
                    if resp.status_code != 200:
                        logger.warning(f"HTTP {resp.status_code} for {archive_url}")
                        break
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for anchor in soup.find_all('a', href=True):
                        href = anchor['href']
                        if '.pdf' not in href.lower():
                            continue
                        full_url = canonical_pdf_url(archive_url, href)
                        fname = filename_from_url(full_url)
                        if not is_actual_newspaper(fname) or not is_english_issue(fname):
                            continue
                        file_date = parse_date_from_filename(fname)
                        if not file_date or not issue_is_in_scope(file_date):
                            continue
                        key = file_date.strftime('%Y-%m-%d')
                        # Sources are ordered by preference; preserve the first valid URL.
                        if key not in all_links:
                            all_links[key] = (file_date, fname, full_url)
                    break
                except Exception as exc:
                    logger.error(f"Error scraping {archive_url}: {exc}")
                    if attempt < RETRIES - 1:
                        time.sleep(2)
            if backfill:
                time.sleep(0.25)

    logger.info(f"Found {len(all_links)} unique English MyGov issues")
    return all_links


def find_latest_pdf():
    """Scrape multiple sources to find the latest English MyGov newspaper PDF."""
    all_links = scrape_archive_links(backfill=False)

    if not all_links:
        logger.warning("No MyGov newspaper PDFs found on any source.")
        return None, None

    latest_key = max(all_links.keys())
    file_date, fname, url = all_links[latest_key]
    logger.info(f"Latest issue: {fname} ({file_date.strftime('%B %d, %Y')})")
    return fname, url


def find_all_pdfs():
    """Scrape all sources to find ALL available English MyGov newspaper PDFs."""
    return scrape_archive_links(backfill=True)


def download_pdf(url, filename):
    """Download a PDF file."""
    os.makedirs(TARGET_DIR, exist_ok=True)
    filepath = os.path.join(TARGET_DIR, filename)

    if os.path.exists(filepath):
        logger.info(f"Already downloaded: {filename}")
        return filepath

    try:
        logger.info(f"Downloading: {url}")
        resp = requests.get(
            url,
            stream=True,
            timeout=60,
            verify=False,
            headers={'User-Agent': USER_AGENT},
        )
        if resp.status_code != 200:
            logger.error(f"HTTP {resp.status_code} downloading {url}")
            return None
        if 'pdf' not in resp.headers.get('Content-Type', '').lower():
            logger.error(f"Non-PDF content at {url}")
            return None
        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Downloaded: {filename} ({os.path.getsize(filepath)/1024/1024:.1f} MB)")
        return filepath
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return None


def authenticate_google_drive():
    """Authenticate with Google Drive API."""
    creds = None

    try:
        if os.getenv('GOOGLE_TOKEN'):
            logger.info("Loading credentials from GOOGLE_TOKEN environment variable")
            token_data = json.loads(os.getenv('GOOGLE_TOKEN'))
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        elif os.getenv('GOOGLE_CREDENTIALS'):
            credential_data = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
            if credential_data.get('type') != 'service_account':
                raise RuntimeError(
                    "GOOGLE_CREDENTIALS must contain service-account JSON for headless runs"
                )
            creds = service_account.Credentials.from_service_account_info(
                credential_data, scopes=SCOPES
            )
        elif os.path.exists('token.json'):
            logger.info("Loading credentials from token.json")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
            else:
                if os.path.exists('credentials.json'):
                    logger.info("Running local server flow for authentication")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise Exception("No credentials.json found and no valid token available")

            if not os.getenv('GOOGLE_TOKEN') and creds:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logger.info("Saved new token to token.json")

        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise


def upload_to_drive(service, filepath):
    """Upload file to Google Drive."""
    try:
        filename = os.path.basename(filepath)
        logger.info(f"Preparing to upload {filename} to Google Drive")

        results = service.files().list(
            q=f"name='{filename}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()

        if results.get('files', []):
            logger.info(f"File '{filename}' already exists in Google Drive.")
            return

        file_metadata = {
            'name': filename,
            'parents': [DRIVE_FOLDER_ID]
        }

        media = MediaFileUpload(filepath, mimetype='application/pdf')
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        logger.info(f"Successfully uploaded '{filename}' to Drive with ID: {file.get('id')}")

    except Exception as e:
        logger.error(f"Error uploading to Drive: {str(e)}")
        raise


def list_drive_filenames(service):
    """List existing files once so backfill skips downloads already in Drive."""
    names = set()
    page_token = None
    while True:
        result = service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(name)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        names.update(item['name'] for item in result.get('files', []))
        page_token = result.get('nextPageToken')
        if not page_token:
            return names


def load_manifest_filenames():
    """Load the durable archive inventory tracked with the repository."""
    if not os.path.exists(MANIFEST_PATH):
        return set()
    with open(MANIFEST_PATH, encoding='utf-8') as manifest_file:
        payload = json.load(manifest_file)
    return set(payload.get('files', []))


def save_manifest_filenames(filenames):
    """Persist canonical PDF names after successful uploads."""
    payload = {
        'updated_at': datetime.now().isoformat(timespec='seconds'),
        'files': sorted(name for name in filenames if name.lower().endswith('.pdf')),
    }
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as manifest_file:
        json.dump(payload, manifest_file, indent=2)
        manifest_file.write('\n')


def main():
    """Download the latest MyGov PDF and upload to Google Drive."""
    logger.info("Starting MyGov PDF download and upload process...")

    try:
        fname, url = find_latest_pdf()
        if not fname or not url:
            logger.warning("No file to upload.")
            return

        std_name = fname
        date = parse_date_from_filename(fname)
        if date:
            std_name = f"MyGov {date.strftime('%B %d, %Y')}.pdf"

        filepath = download_pdf(url, std_name)
        if not filepath:
            logger.warning("Download failed.")
            return

        drive_service = authenticate_google_drive()
        upload_to_drive(drive_service, filepath)
        logger.info("Process completed successfully!")
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        raise


def backfill():
    """Download ALL available MyGov PDFs and upload them to Google Drive."""
    logger.info("Starting MyGov backfill process...")

    all_links = find_all_pdfs()
    if not all_links:
        logger.warning("No PDFs found.")
        return

    drive_service = authenticate_google_drive()
    existing_names = list_drive_filenames(drive_service) | load_manifest_filenames()

    uploaded = 0
    skipped = 0
    failed = 0

    for key in sorted(all_links.keys()):
        file_date, fname, url = all_links[key]
        std_name = f"MyGov {file_date.strftime('%B %d, %Y')}.pdf"

        if std_name in existing_names:
            logger.info(f"Already in Drive: {std_name}")
            skipped += 1
            continue

        filepath = download_pdf(url, std_name)
        if not filepath:
            failed += 1
            continue

        try:
            upload_to_drive(drive_service, filepath)
            uploaded += 1
            existing_names.add(std_name)
        except Exception as e:
            logger.error(f"Failed to upload {std_name}: {e}")
            failed += 1

        time.sleep(1)

    logger.info(f"Backfill complete: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    if uploaded:
        save_manifest_filenames(existing_names)
    if failed:
        raise RuntimeError(f"Backfill completed with {failed} failed issue(s)")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--backfill':
        backfill()
    else:
        main()
