# MyGov downloader

Downloads English MyGov newspaper PDFs and uploads missing issues to the configured Google Drive archive.

## Source discovery

The scheduled sync checks the known ICT, MyGov and GAA archive pages first. When the newest issue found is more than seven days old, it searches Google for the latest Tuesday issues and checks the result pages. It only accepts PDF URLs hosted on official government domains.

Verified archive pages and dated PDF URLs from search are saved in the source_discovery.json file. Later runs scan those saved URLs along with the built-in source list. If search cannot find a recent issue, the workflow fails with the latest date it found instead of reporting an empty successful run.

Google search is a best-effort fallback. Search results can be delayed or blocked, so the freshness check remains the signal that the source set needs attention.
