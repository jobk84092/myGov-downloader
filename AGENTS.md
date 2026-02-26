# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Python-based MyGov Kenya Newspaper PDF downloader and archiver. Scripts scrape Kenyan government websites (`ict.go.ke`, `gaa.go.ke`, `mygov.go.ke`) for weekly MyGov newspaper PDFs and upload them to Google Drive folder `19fu-mfAfTPBvXdjPVKdMdgOCq4neCDqy`.

### Key scripts

| Script | Purpose | Auth required? |
|---|---|---|
| `main.py` | Downloads latest PDF + uploads to Google Drive. Also supports `--backfill` to upload ALL available issues. | Yes (`GOOGLE_TOKEN` env var or `token.json`) |
| `gha_mygov_downloader.py` | Downloads latest PDF from `mygov.go.ke` (used in GitHub Actions artifact workflow) | No |
| `auto_mygov_downloader.py` | Auto downloader with email/macOS notifications | No (email optional) |
| `crawl_gaa_pages.py` | Backfill crawler for GAA archive pages | No |
| `crawl_gaa2_pages.py` | Multi-source crawler with Google search fallback | No |
| `crawl_housing_pages.py` | Similar to crawl_gaa2 but for housing pages | No |
| `folder_watcher.py` | macOS-only folder watcher (hardcoded paths) | N/A |
| `import requests.py` | Simple batch PDF downloader | No |

### GitHub Actions workflows

| Workflow | Schedule | What it does |
|---|---|---|
| `mygov-downloader.yml` | Every Tuesday 9 AM EAT (6 AM UTC) | Downloads latest newspaper + uploads to Google Drive |
| `mygov-backfill.yml` | Every Tuesday 6 PM EAT (3 PM UTC) | Checks all sources for missing issues + uploads them |
| `mygov_download.yml` | Every Tuesday 9 AM EAT (6 AM UTC) | Downloads latest PDF + saves as GitHub artifact |

GitHub auto-disables scheduled workflows after 60 days of no repo activity. If workflows stop running, re-enable them from the Actions tab.

### Running scripts

- **Quick test (no auth):** `python3 gha_mygov_downloader.py` — scrapes and downloads the latest English MyGov PDF.
- **Full flow (requires Google creds):** `python3 main.py` — downloads latest + uploads to Google Drive.
- **Backfill all issues:** `python3 main.py --backfill` — downloads and uploads ALL available issues.
- `main.py` will hang on OAuth browser flow if no valid token is available. Set `GOOGLE_TOKEN` env var to skip interactive auth.

### Dependencies

Core dependencies are in `requirements.txt`. Additional packages used by secondary scripts but not listed in `requirements.txt`: `python-dateutil`, `watchdog`, `googlesearch-python`.

### Lint / Tests / Build

- No linter configuration, test framework, or build system exists in this codebase.
- Syntax checking: `python3 -m py_compile <script>.py`
- There is no `pyproject.toml`, `setup.py`, or `setup.cfg`.

### Gotchas

- `folder_watcher.py` has macOS-specific hardcoded paths and will not work on Linux.
- `auto_mygov_downloader.py` uses `osascript` for notifications (macOS-only; silently fails on Linux).
- The government websites use SSL certificates that sometimes fail verification; all scripts use `verify=False`.
- Downloaded PDFs land in `downloads/` directory (`main.py`, crawlers) or working directory (`gha_mygov_downloader.py`).
- Archive pages for 2022-2024 on `gaa.go.ke` and `mygov.go.ke` are offline (404). Only 2025+ and `ict.go.ke` are live. The owner has 2022-2024 issues locally already.
- The Google Drive folder ID (`19fu-mfAfTPBvXdjPVKdMdgOCq4neCDqy`) syncs to the owner's Mac at `/Users/jobkimani/Library/CloudStorage/GoogleDrive-jobkimani@gmail.com/My Drive/works/myGov Repository/MyGov Sept 2022-June 2025`.
