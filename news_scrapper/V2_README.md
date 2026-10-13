# V2 discovery

V2 collects search metadata and URLs only. It makes requests solely to SerpAPI;
no publisher pages or article bodies are fetched. V1 and extraction artifacts are unchanged.

The default pilot gives each company one products and one business query against
the same beverage/food trade domain group: eight initial requests. All returned
leaf news results are evaluated, including nested stories. No pagination is used.
Search categories are discovery provenance, not article classifications.

Dates are required CLI inputs and checked inclusively against search-provided dates.
The experimental window is 2024-10-10 through 2026-10-09. Search after/before
operators are hints; the local date filter is authoritative. Unknown dates and
ambiguous Culture Pop matches require review. Publisher dates are not independently verified.

Set SERPAPI_KEY in the environment, or provide a real key file with --env-file.
Do not put credentials in the checkpoint or commit them. The existing .env in this
workspace is currently a directory, so it cannot be read as an environment file.

Example using the available Anaconda Python in PowerShell:

```powershell
& C:/Users/maria/anaconda3/python.exe -B news_scrapper/discover_v2.py --start-date 2024-10-10 --end-date 2026-10-09 --output news_scrapper/news_dataset_v2_pilot.json --max-requests 4
# Resume the remaining four requests using exactly the same run configuration:
& C:/Users/maria/anaconda3/python.exe -B news_scrapper/discover_v2.py --start-date 2024-10-10 --end-date 2026-10-09 --output news_scrapper/news_dataset_v2_pilot.json --max-requests 4 --resume
```

Add --env-file with a local credential-file path if necessary. A completed
checkpoint makes zero additional requests on resume. Checkpoints are atomically
replaced after each attempt. Requests interrupted while in flight remain
indeterminate and require inspection before retrying, avoiding automatic double charges.

Errors pause the run, preserve attempts, and set a retry time. Retry-After and
exponential backoff with jitter are respected by refusing an early resume.
Maximum three attempts per query; the CLI request budget applies per invocation.
Errors are never converted to zero results. Queries at the attempt cap remain
incomplete. Resume later rather than repeatedly spending requests during a quota limit.

The full schedule, available only with explicit --full, has 96 company queries
plus 16 interleaved industry queries: 112 initial requests, up to 336 with the
three-attempt cap. Do not execute the full collection until separately approved.

JSON contains run configuration, code hashes, query parameters without API keys,
query outcomes and attempt history, candidate decisions with reasons, and unique
URL records. Every URL preserves all discovery associations and matched companies.
Articles include rejected/review URL records; select eligibility_status=accepted
for the clean URL pool. Candidates count query-result occurrences; articles count
unique normalized URLs. Conflicting observed metadata remain in associations.

The source allowlist and exclusions are snapshotted. URL normalization removes
known tracking parameters and fragments but preserves meaningful parameters,
HTTP/HTTPS distinctions, paths and hostname differences. It does not follow redirects.
The run is reproducible from its manifest and captured candidate metadata; live
search rankings themselves can change. No equal-output-count guarantee is made.

Offline validation (mocked API responses, no network):

```powershell
& C:/Users/maria/anaconda3/python.exe -B news_scrapper/test_discover_v2.py
```