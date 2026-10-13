# Frozen V2.2 full discovery report

Inclusive dates: 2024-10-10 through 2026-10-09. No article bodies fetched. Methodology unchanged.

Requests/attempts: 156; retry attempts: 44; HTTP statuses: {'200': 156}.
Query outcomes: {'all_filtered': 2, 'error': 22, 'results': 88}
Before URL deduplication: {'accepted': 820, 'rejected': 567, 'review': 49}
After URL deduplication: {'accepted': 255, 'rejected': 309, 'review': 12}

Company counts use confirmed entities on accepted associations; the matrix uses accepted associations from that company/dimension query. Dimension and group counts overlap; industry provenance is separate.

| Company | products | pricing | retail | marketing | business | consumers | Confirmed company URLs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Olipop | 26 | 19 | 33 | 34 | 29 | 30 | 42 |
| Poppi | 47 | 37 | 58 | 57 | 49 | 46 | 69 |
| Culture Pop | 16 | 7 | 12 | 11 | 10 | 11 | 16 |
| Zevia | 20 | 23 | 27 | 27 | 16 | 26 | 29 |

Accepted unique URLs by dimension: {'products': 108, 'pricing': 85, 'retail': 128, 'marketing': 127, 'business': 102, 'consumers': 111, 'industry': 126}

| Source group | Returned | Accepted unique | Company query accepted | Industry query accepted |
|---|---:|---:|---:|---:|
| beverage_and_food_trade | 556 | 119 | 56 | 67 |
| retail_and_marketing_trade | 449 | 59 | 38 | 27 |
| business_and_financial | 236 | 40 | 29 | 17 |
| company_announcements | 195 | 37 | 26 | 15 |

| Domain | Returned | Accepted unique | Review unique |
|---|---:|---:|---:|
| bevnet.com | 435 | 87 | 0 |
| foodbev.com | 87 | 22 | 0 |
| foodnavigator-usa.com | 34 | 10 | 1 |
| beverageindustry.com | 0 | 0 | 0 |
| fooddive.com | 130 | 18 | 0 |
| grocerydive.com | 0 | 0 | 0 |
| retaildive.com | 11 | 0 | 0 |
| marketingdive.com | 83 | 14 | 0 |
| modernretail.co | 74 | 6 | 0 |
| adage.com | 134 | 19 | 10 |
| retailbrew.com | 3 | 1 | 0 |
| marketingbrew.com | 14 | 1 | 0 |
| reuters.com | 18 | 4 | 0 |
| bloomberg.com | 32 | 8 | 0 |
| cnbc.com | 55 | 7 | 1 |
| forbes.com | 84 | 13 | 0 |
| wsj.com | 42 | 7 | 0 |
| morningbrew.com | 4 | 1 | 0 |
| businesswire.com | 50 | 12 | 0 |
| prnewswire.com | 120 | 20 | 0 |
| globenewswire.com | 24 | 5 | 0 |

Multi-association behavior: {'all_unique_urls': 576, 'multiple_queries': 233, 'multiple_dimensions': 202, 'multiple_company_query_targets': 7, 'multiple_confirmed_companies_accepted_urls': 5, 'extra_occurrences': 860, 'accepted_urls_multiple_queries': 154}
Accepted date range: ['2024-10-10', '2026-10-09']
Accepted date precision: {'day': 255}
Filter reason incidence (overlapping): {'entity_not_confirmed': 280, 'exact_phrase_without_beverage_context': 1, 'excluded_title_term': 36, 'excluded_url_pattern': 46, 'outside_date_window': 218, 'unsupported_page_type': 29, 'url_only_company_evidence': 55}

| Accepted publication month | Unique URLs |
|---|---:|
| 2024-10 | 7 |
| 2024-11 | 3 |
| 2024-12 | 9 |
| 2025-01 | 3 |
| 2025-02 | 27 |
| 2025-03 | 41 |
| 2025-04 | 8 |
| 2025-05 | 9 |
| 2025-06 | 6 |
| 2025-07 | 14 |
| 2025-08 | 7 |
| 2025-09 | 8 |
| 2025-10 | 6 |
| 2025-11 | 3 |
| 2025-12 | 6 |
| 2026-01 | 6 |
| 2026-02 | 8 |
| 2026-03 | 13 |
| 2026-04 | 6 |
| 2026-05 | 11 |
| 2026-06 | 8 |
| 2026-07 | 12 |
| 2026-08 | 17 |
| 2026-09 | 10 |
| 2026-10 | 7 |

Extraction estimate: {'accepted': 255, 'review_pending_human_decision': 12, 'maximum_if_all_review_approved': 267, 'accepted_with_confirmed_company': 151, 'accepted_industry_without_confirmed_company': 104}

All attempt errors, zero-return and zero-accepted queries, out-of-window occurrences, publisher coverage and accepted titles are enumerated in news_dataset_v2_2_full_summary.json.

Limits: rule acceptance is not ground-truth relevance. Dimensions are discovery provenance, not verified topics. Secondary brand/investor/executive mentions can pass title matching. Industry acceptance is category context and does not require a tracked company. Publisher-provided dates are not independently verified. Search date operators are hints, with authoritative local inclusive filtering.

Pre-existing discovery/CrewAI file hashes and frozen code hashes verified. Credential absence checked without exposing its value. No commit/push or body extraction.

## Run completion and technical incident

All 112 scheduled queries were attempted. 90 completed (88 with results, two all-filtered); 22 exhausted the three-attempt cap. No pending/in-flight queries remain. The frozen checkpoint correctly retains status incomplete; no errors were reclassified as successful zero-result searches.
156 API attempts = 112 first attempts + 44 retries. All 156 responses were HTTP 200; 66 attempts carried the same SerpAPI no-result error. No 429/rate-limit responses occurred.
One Windows WinError 5 interrupted atomic checkpoint replacement at attempt 114. The complete temporary checkpoint was validated and promoted without repeating an API call. Its snapshot and incident record are preserved separately.

## Exhausted query failures

| Source group | Target | Dimensions or industry phrase |
|---|---|---|
| company_announcements | industry | non alcoholic soda |
| company_announcements | Olipop | pricing |
| company_announcements | Culture Pop | pricing |
| retail_and_marketing_trade | Culture Pop | products, retail, business, consumers, pricing |
| retail_and_marketing_trade | industry | non alcoholic soda |
| business_and_financial | Zevia | marketing, products, retail, business, consumers |
| business_and_financial | Culture Pop | marketing, products, retail, business, consumers, pricing |
| business_and_financial | industry | health soda, non alcoholic soda |

Each failed query has three HTTP 200 attempts with: Google News has not returned any results for this query. Exact original errors and query parameters are retained in the dataset/summary.

The two successful all-filtered queries were Culture Pop marketing in retail/marketing sources (an old Star Wars movie-marketing result), and the non alcoholic soda industry query in beverage/food trade (four excluded or unconfirmed results).

## Company coverage by source group

| Company | Beverage/food trade | Retail/marketing | Business/financial | Announcements |
|---|---:|---:|---:|---:|
| Olipop | 13 | 12 | 12 | 2 |
| Poppi | 20 | 20 | 18 | 10 |
| Culture Pop | 12 | 0 | 0 | 4 |
| Zevia | 11 | 7 | 1 | 10 |

## Accepted dates by quarter

| Quarter | Accepted unique URLs |
|---|---:|
| 2024 Q4 | 19 |
| 2025 Q1 | 71 |
| 2025 Q2 | 23 |
| 2025 Q3 | 29 |
| 2025 Q4 | 15 |
| 2026 Q1 | 27 |
| 2026 Q2 | 25 |
| 2026 Q3 | 39 |
| 2026 Q4 | 7 |

Boundary quarters are partial: Oct 10-Dec 31, 2024 and Oct 1-9, 2026. The full monthly distribution is included above and in the JSON summary.

## Human-review findings

- 22 queries exhausted three attempts on HTTP 200 no-result API errors; frozen status remains incomplete with zero pending queries.
- Culture Pop has zero accepted company-query URLs in retail/marketing and financial source groups; Zevia financial coverage is one stock quote page.
- Non-article paths are not exhaustive: a WSJ stock quote, a BevNET podcast replay under /news/, awards pages and nomination pages pass existing rules.
- Secondary-company executive/investor references pass entity matching; they need human relevance review.
- Dimensions heavily overlap and must remain provenance, not topic labels.
- All snippets are empty; body-only company mentions remain unconfirmed or URL-only review.
- Exact URL deduplication does not merge syndicated press releases or multiple reports of the same event.
- Industry acceptance needs category context, not a tracked company; 104 accepted URLs have no confirmed tracked company.
- 218 out-of-window occurrences on 92 URLs demonstrate unreliable search date hints; local filtering rejected all such occurrences.
- Publisher dates and substantive relevance have not been independently verified.

Examples requiring human review: Zevia PBC (ZVIA) Stock Price Today - The Wall Street Journal; Episode 787: Replay: Inside Poppi?s Early Playbook & The Moves That Led To A Big Exit; BevNET Best of 2025 Awards: Nominate the Brands, People, and Innovations Driving the Beverage Industry Forward; Crooked Pop Taps Former Zevia Exec Lee Schill as CCO; Investors of Poppi, Goodles raise seed round for powdered beverage startup.

No records were removed or reclassified in response to these findings. No additional API requests or article extraction are authorized by this report.
