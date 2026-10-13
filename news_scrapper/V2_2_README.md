# V2.2 discovery revision

The original V2 collector, configuration, tests, README, and pilot remain unchanged.
Use discover_v2_2.py with the new output news_dataset_v2_2_pilot.json.
Query and entity rules are versioned v2.2 in the run manifest.
All company queries retain the quoted company and add intitle:"{company}".
Products use (launch OR launches OR "new products" OR flavor OR flavour).
Company acceptance requires a title boundary match. Culture Pop title matches on
approved beverage/food trade domains have sufficient entity context; outside that
group the existing beverage-context requirement remains. URL-path-only and
snippet-only evidence require review. Other exclusion/date rules take precedence.
Dimensions remain discovery provenance, not verified article topics.
The same eight-query pilot, seed, trade domains, inclusive dates, URL normalization,
association retention, request pacing and checkpoint behavior are preserved.
No publisher pages or article bodies are requested. Full collection requires separate approval.

Run offline validation with python -B news_scrapper/test_discover_v2_2.py.
Run the pilot with python -B news_scrapper/discover_v2_2.py --start-date 2024-10-10 --end-date 2026-10-09 --output news_scrapper/news_dataset_v2_2_pilot.json --max-requests 8 --env-file .env.
A resumed completed checkpoint makes no additional requests.
