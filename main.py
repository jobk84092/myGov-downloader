import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request  # This was missing!
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ---- CONFIG ----
BASE_URL = "https://ict.go.ke"
KEYWORD = "MyGov"
TARGET_DIR = "downloads"
DRIVE_FOLDER_ID = "1bu5FMiNkc1B4RKYIKM9PZTsIKgPUCaN1"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ---- AUTH ----
def authenticate_google_drive():
    creds = None
    
    # Try to load from environment variable (for GitHub Actions)
    if os.getenv('GOOGLE_TOKEN'):
        import json
        token_data = json.loads(os.getenv('GOOGLE_TOKEN'))
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save updated token back to environment for GitHub Actions
            if os.getenv('GOOGLE_TOKEN'):
                print("Token refreshed successfully")
        else:
            # For initial setup - run this locally first
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_console()
            else:
                raise Exception("No credentials.json found and no valid token available")
        
        # Save token locally for initial setup
        if not os.getenv('GOOGLE_TOKEN') and creds:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

# ---- DOWNLOAD LATEST PDF ----
def download_latest_mygov():
    print("Checking website for latest MyGov issue...")
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        mygov_links = [
            link['href'] for link in links
            if KEYWORD.lower() in link['href'].lower() and link['href'].endswith(".pdf")
        ]
        
        if not mygov_links:
            print("No MyGov PDFs found.")
            return None
        
        # Get the latest link (assuming the last one is most recent)
        latest_link = mygov_links[-1]
        if not latest_link.startswith("http"):
            latest_link = BASE_URL + latest_link
        
        filename = latest_link.split("/")[-1]
        os.makedirs(TARGET_DIR, exist_ok=True)
        filepath = os.path.join(TARGET_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"{filename} already exists.")
            return filepath
        
        print(f"Downloading: {latest_link}")
        r = requests.get(latest_link)
        r.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(r.content)
        
        print(f"Downloaded: {filename}")
        return filepath
        
    except requests.RequestException as e:
        print(f"Error downloading: {e}")
        return None

# ---- UPLOAD TO GOOGLE DRIVE ----
def upload_to_drive(service, filepath):
    try:
        filename = os.path.basename(filepath)
        
        # Check if file already exists in Drive folder
        results = service.files().list(
            q=f"name='{filename}' and '{DRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        if results.get('files', []):
            print(f"File '{filename}' already exists in Google Drive.")
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
        
        print(f"Uploaded '{filename}' to Drive with ID: {file.get('id')}")
        
    except Exception as e:
        print(f"Error uploading to Drive: {e}")

# ---- MAIN ----
def main():
    print("Starting MyGov PDF download and upload process...")
    
    file_path = download_latest_mygov()
    if not file_path:
        print("No file to upload.")
        return
    
    try:
        drive_service = authenticate_google_drive()
        upload_to_drive(drive_service, file_path)
        print("Process completed successfully!")
    except Exception as e:
        print(f"Error with Google Drive operations: {e}")

if __name__ == '__main__':
    main()
