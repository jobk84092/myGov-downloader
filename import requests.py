import os
import requests
from datetime import datetime, timedelta

# Directory to save downloads
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to generate all Tuesdays between start and end dates
def generate_tuesdays(start, end):
    current = start
    # Adjust to next Tuesday if start_date is not Tuesday
    if current.weekday() != 1:
        current += timedelta(days=(1 - current.weekday()) % 7)
    while current <= end:
        yield current
        current += timedelta(weeks=1)

# Download function
def download_pdf(date):
    month = date.strftime("%B")
    day = date.day
    year = date.year
    url = f"https://gaa.go.ke/sites/default/files/{year}/MyGov%20{month}%20{day}%2C%20{year}.pdf"
    local_filename = os.path.join(DOWNLOAD_DIR, f"MyGov_{date.strftime('%Y_%m_%d')}.pdf")
    try:
        print(f"Downloading {url} ...")
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(response.content)
            print(f"Saved to {local_filename}")
        else:
            print(f"File not found for date {date.strftime('%B %d, %Y')} (HTTP {response.status_code})")
    except Exception as e:
        print(f"Error downloading {date.strftime('%B %d, %Y')}: {e}")

if __name__ == "__main__":
    start_date = datetime(2022, 9, 6)  # First Tuesday in Sept 2022
    end_date = datetime(2025, 5, 27)   # Last Tuesday in May 2025
    for issue_date in generate_tuesdays(start_date, end_date):
        download_pdf(issue_date)

# List all downloaded MyGov files
def list_downloaded_files():
    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith('.pdf') and 'mygov' in f.lower()]
    print(f"Total MyGov files in downloads/: {len(files)}")
    for f in sorted(files):
        print(f)

if __name__ == "__main__":
    list_downloaded_files()
