# Template Repo + Existing Repo Sync

This repo can serve as your standard skeleton for all GitHub projects.

## A) Use for all NEW repos (GitHub Template)

1. Install and authenticate GitHub CLI:
   - `brew install gh`
   - `gh auth login`
2. From this folder, publish as a template repo:
   - `chmod +x scripts/publish_as_template.sh`
   - `scripts/publish_as_template.sh <owner> <template-repo-name> private`
3. Create new repos from template:
   - GitHub UI: **Use this template**
   - or CLI: `gh repo create <owner>/<new-repo> --template <owner>/<template-repo-name> --private`

## B) Apply to EXISTING repos (one command)

1. Make script executable:
   - `chmod +x scripts/sync_repo_skeleton.sh`
2. Sync missing structure into one or many repos:
   - `scripts/sync_repo_skeleton.sh ~/code/repo-a ~/code/repo-b`
3. Optional force mode (overwrite/update files from template):
   - `scripts/sync_repo_skeleton.sh --force ~/code/repo-a`

## Notes

- Default sync mode is non-destructive (`--ignore-existing`).
- `--force` mode updates files and can remove files absent from template due to `--delete-after`.
- `scripts/` and `.github/workflows/` in this template are excluded from default sync so you can choose where to adopt automation.
