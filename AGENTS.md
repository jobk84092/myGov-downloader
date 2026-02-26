# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Python-based MyGov Kenya Newspaper PDF downloader and archiver. Scripts scrape Kenyan government websites (`ict.go.ke`, `gaa.go.ke`, `mygov.go.ke`) for weekly MyGov newspaper PDFs and optionally upload them to Google Drive.

### Key scripts

| Script | Purpose | Auth required? |
|---|---|---|
| `gha_mygov_downloader.py` | Downloads latest PDF from `mygov.go.ke` (used in GitHub Actions) | No |
| `main.py` | Downloads latest PDF + uploads to Google Drive | Yes (`GOOGLE_TOKEN` env var or `token.json`) |
| `auto_mygov_downloader.py` | Auto downloader with email/macOS notifications | No (email optional) |
| `crawl_gaa_pages.py` | Backfill crawler for GAA archive pages | No |
| `crawl_gaa2_pages.py` | Multi-source crawler with Google search fallback | No |
| `crawl_housing_pages.py` | Similar to crawl_gaa2 but for housing pages | No |
| `folder_watcher.py` | macOS-only folder watcher (hardcoded paths) | N/A |
| `import requests.py` | Simple batch PDF downloader | No |

### Running scripts

- **Quick test (no auth):** `python3 gha_mygov_downloader.py` — scrapes and downloads the latest English MyGov PDF.
- **Full flow (requires Google creds):** `python3 main.py` — downloads + uploads to Google Drive. Needs `GOOGLE_TOKEN` env var or `credentials.json` + `token.json`.
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
- Downloaded PDFs land in the working directory (`gha_mygov_downloader.py`) or in `downloads/` (`main.py`, crawlers).
