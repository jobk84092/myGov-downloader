import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
import json
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---- CONFIG ----
BASE_URL = "https://ict.go.ke"
KEYWORD = "MyGov"
TARGET_DIR = "downloads"
DRIVE_FOLDER_ID = "1bu5FMiNkc1B4RKYIKM9PZTsIKgPUCaN1"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def extract_date_from_url(url):
    """Extract date from MyGov PDF URL."""
    patterns = [
        r'(\d{4})-(\d{2})',  # YYYY-MM format
        r'(\d{1,2})(?:st|nd|rd|th)?%20(\w+)%20(\d{4})',  # Day Month Year with %20
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(\d{4})'   # Day Month Year with spaces
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 2:  # YYYY-MM format
                    year, month = int(match.group(1)), int(match.group(2))
                    return datetime(year, month, 1)
                else:  # Day Month Year format
                    day = int(match.group(1))
                    month_str = match.group(2).lower()
                    year = int(match.group(3))
                    
                    month_map = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12
                    }
                    month = month_map.get(month_str, 1)
                    return datetime(year, month, day)
            except:
                continue
    return datetime(1900, 1, 1)  # Very old date as fallback

def authenticate_google_drive():
    """Authenticate with Google Drive API."""
    creds = None
    
    try:
        # Try to load from environment variable (for GitHub Actions)
        if os.getenv('GOOGLE_TOKEN'):
            logger.info("Attempting to load credentials from GOOGLE_TOKEN environment variable")
            token_data = json.loads(os.getenv('GOOGLE_TOKEN'))
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        elif os.path.exists('token.json'):
            logger.info("Loading credentials from token.json")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
                if os.getenv('GOOGLE_TOKEN'):
                    logger.info("Token refreshed successfully")
            else:
                if os.path.exists('credentials.json'):
                    logger.info("Running local server flow for authentication")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise Exception("No credentials.json found and no valid token available")
            
            # Save token locally for initial setup
            if not os.getenv('GOOGLE_TOKEN') and creds:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logger.info("Saved new token to token.json")
        
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise

def download_latest_mygov():
    """Download the latest MyGov PDF from the website."""
    logger.info("Checking website for latest MyGov issue...")
    try:
        # Disable SSL warnings for this specific case
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(BASE_URL, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for MyGov PDF links
        links = soup.find_all('a', href=True)
        mygov_links = []
        
        for link in links:
            href = link['href']
            if KEYWORD.lower() in href.lower() and href.endswith(".pdf"):
                mygov_links.append(href)
        
        if not mygov_links:
            logger.warning("No MyGov PDFs found.")
            return None
        
        logger.info(f"Found {len(mygov_links)} MyGov PDFs")
        
        # Sort by extracting dates from filenames
        dated_links = [(link, extract_date_from_url(link)) for link in mygov_links]
        dated_links.sort(key=lambda x: x[1], reverse=True)
        
        latest_link = dated_links[0][0]
        latest_date = dated_links[0][1]
        
        logger.info(f"Latest PDF found: {latest_link}")
        logger.info(f"Date extracted: {latest_date.strftime('%B %d, %Y')}")
        
        if not latest_link.startswith("http"):
            latest_link = BASE_URL + latest_link
        
        filename = latest_link.split("/")[-1]
        os.makedirs(TARGET_DIR, exist_ok=True)
        filepath = os.path.join(TARGET_DIR, filename)
        
        if os.path.exists(filepath):
            logger.info(f"{filename} already exists.")
            return filepath
        
        logger.info(f"Downloading: {latest_link}")
        r = requests.get(latest_link, verify=False)
        r.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(r.content)
        
        logger.info(f"Downloaded: {filename}")
        return filepath
        
    except requests.RequestException as e:
        logger.error(f"Error downloading: {str(e)}")
        return None

def upload_to_drive(service, filepath):
    """Upload file to Google Drive."""
    try:
        filename = os.path.basename(filepath)
        logger.info(f"Preparing to upload {filename} to Google Drive")
        
        # Check if file already exists in Drive folder
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

def main():
    """Main function to orchestrate the download and upload process."""
    logger.info("Starting MyGov PDF download and upload process...")
    
    try:
        file_path = download_latest_mygov()
        if not file_path:
            logger.warning("No file to upload.")
            return
        
        drive_service = authenticate_google_drive()
        upload_to_drive(drive_service, file_path)
        logger.info("Process completed successfully!")
    except Exception as e:
        logger.error(f"Process failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()
