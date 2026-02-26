"""
MyGov Newspaper Downloader Script

This script downloads MyGov newspaper PDF issues from the Government Advertising Agency (GAA) website.

Main Features:
1. Download all Tuesday issues between a date range (historical download)
2. Download specific missing issues from a hardcoded list (August-October 2025)
3. List all downloaded MyGov files

The script uses the download_pdf(date) function which constructs URLs based on the date
and downloads PDFs to the 'downloads' directory.
"""

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

# List all downloaded MyGov files
def list_downloaded_files():
    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith('.pdf') and 'mygov' in f.lower()]
    print(f"Total MyGov files in downloads/: {len(files)}")
    for f in sorted(files):
        print(f)

# Download missing MyGov issues from August to October 2025
def download_missing_issues():
    """
    Download specific missing MyGov newspaper issues from August to October 2025.
    
    This function attempts to download the following missing issues:
    - August 5, 12, 19, 26, 2025
    - September 2, 9, 16, 23, 30, 2025
    - October 7, 2025
    
    Status of each download (success/failure) is printed to console.
    """
    print("\n" + "="*60)
    print("DOWNLOADING MISSING MYGOV ISSUES (AUGUST - OCTOBER 2025)")
    print("="*60 + "\n")
    
    # Hardcoded list of missing issue dates
    missing_dates = [
        datetime(2025, 8, 5),   # August 5, 2025
        datetime(2025, 8, 12),  # August 12, 2025
        datetime(2025, 8, 19),  # August 19, 2025
        datetime(2025, 8, 26),  # August 26, 2025
        datetime(2025, 9, 2),   # September 2, 2025
        datetime(2025, 9, 9),   # September 9, 2025
        datetime(2025, 9, 16),  # September 16, 2025
        datetime(2025, 9, 23),  # September 23, 2025
        datetime(2025, 9, 30),  # September 30, 2025
        datetime(2025, 10, 7),  # October 7, 2025
    ]
    
    success_count = 0
    failure_count = 0
    
    for date in missing_dates:
        print(f"\nAttempting to download: {date.strftime('%B %d, %Y')}")
        try:
            download_pdf(date)
            # Check if file was actually created
            expected_filename = os.path.join(DOWNLOAD_DIR, f"MyGov_{date.strftime('%Y_%m_%d')}.pdf")
            if os.path.exists(expected_filename):
                success_count += 1
                print(f"✓ SUCCESS: {date.strftime('%B %d, %Y')}")
            else:
                failure_count += 1
                print(f"✗ FAILED: {date.strftime('%B %d, %Y')}")
        except Exception as e:
            failure_count += 1
            print(f"✗ FAILED: {date.strftime('%B %d, %Y')} - {e}")
    
    print("\n" + "="*60)
    print(f"DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total attempts: {len(missing_dates)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Download missing issues from August to October 2025
    download_missing_issues()
    
    # Optionally list all downloaded files to verify
    print("\n" + "="*60)
    print("LISTING ALL DOWNLOADED MYGOV FILES")
    print("="*60 + "\n")
    list_downloaded_files()
