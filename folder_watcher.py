import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
from datetime import datetime

WATCHED_DIR = "/Users/jobkimani/Library/CloudStorage/GoogleDrive-jobkimani@gmail.com/My Drive/works/myGov Repository/MyGov Sept 2022-June 2025"
SCRIPT_PATH = "/Users/jobkimani/Library/CloudStorage/GoogleDrive-jobkimani@gmail.com/My Drive/works/myGov Repository/auto_mygov_downloader.py"

class MyGovHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Check if a new week has started and no new issue is present
        today = datetime.today()
        week_str = today.strftime("%Y-%W")
        files = os.listdir(WATCHED_DIR)
        if not any(week_str in f for f in files):
            subprocess.run(["python3", SCRIPT_PATH])

if __name__ == "__main__":
    event_handler = MyGovHandler()
    observer = Observer()
    observer.schedule(event_handler, path=WATCHED_DIR, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()