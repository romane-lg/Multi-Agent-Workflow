# Functional soda article dataset

This is the frozen **25 October 2026** extraction snapshot used for the full article
workflow. It contains **255 accepted article URLs**, of which **146 have recovered
readable text** and **109 remain unavailable**. It is not a fresh November crawl.
The wider discovery dataset contains 576 URLs; rejected and review-pending candidates
remain in `news_scrapper/news_dataset_v2_2_full.json` rather than this accepted pool.

## Files

| File | Contents |
| --- | --- |
| `articles_cleaned.json` | Recommended workflow input: links, titles, dates, retrieval metadata and cleaned source paragraphs for all 255 accepted records. |
| `articles_recovered.json` | Original recovered text before the latest encoding and boilerplate cleanup. Preserved for comparison. |
| `researcher_evidence_pack.json` | Existing Researcher output: 255 article assessments and 136 model-generated findings, with source paragraph references. This is not the private Fizzera analysis or executive brief. |
| `cleanup_audit.json` | Original and cleaned text hashes, removed paragraphs and normalization changes, preserving original paragraph IDs. |
| `access_report.md` / `.json` | Retrieval results, publisher breakdown and reasons articles remain unavailable. |
| `manifest.json` | Snapshot counts, provenance and SHA-256 checksums for the exported files. |

Each article record includes `article_id`, `title`, `url`, `publication_date`,
`availability`, `access_note`, `text_sha256`, `paragraphs`, `retrieval_method` and
`retrieved_at`. Each paragraph has a stable `paragraph_id` and its text. Unavailable
records retain the link and access explanation but have an empty paragraph list.
`text_sha256` hashes the UTF-8 paragraph texts joined with two newlines.

The cleaned snapshot removed 484 boilerplate paragraphs and normalized 335 paragraphs.
All existing Researcher citations still resolve to their original paragraph IDs. The
Researcher findings were not regenerated after cleanup; they remain unverified model
summaries and must be checked against the cited source paragraphs.

Readable extraction does not guarantee that the entire original article was recovered.
Brand statements, forecasts and opinions remain attributed source material, not verified
market facts. Repeated events and syndicated stories are not independent corroboration.
The access report distinguishes HTTP denials, network problems, extraction limitations
and robots policies; the 109 unavailable records are not all confirmed paywalls.

## Use

Supply `data/article_pool/articles_cleaned.json` to the full workflow's `--articles`
argument. The workflow prepares its paragraph vector index and requires a separate
company brief and a configured model API key for agent calls. See `FULL_CORPUS_README.md`.
`researcher_evidence_pack.json` contains the evidence pack only, rather than a complete
Researcher runtime checkpoint with attached sources.

Private Fizzera documents, company-specific analysis and executive outputs, API keys,
cookies, browser sessions, raw HTTP caches and MLflow traces are excluded from this export.
