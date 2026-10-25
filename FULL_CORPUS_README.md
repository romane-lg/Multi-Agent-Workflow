# Full article workflow

This branch applies the existing Fizzera Researcher → Analyst → Reviewer → executive
presentation workflow to the **255 accepted unique article URLs** in the discovery snapshot.
There are 576 discovery URLs: 255 accepted, 309 rejected, and 12 awaiting review.
Rejected/review-pending candidates are excluded, not counted as blocked. No new discovery
search is performed.

## Access measured on 25 October 2026

| Method | URLs with usable visible text | Share of 255 |
| --- | ---: | ---: |
| Legacy extraction replayed on the same captured HTTP responses | 105 | 41.18% |
| Improved public HTML extraction | 115 | 45.10% |
| Improved extraction plus ordinary browser rendering | 146 | 57.25% |
| Still unavailable to this workflow | 109 | 42.75% |

The changes recovered **41 additional articles**: 10 through improved extraction and 31
through ordinary browser rendering. Food Dive and Marketing Dive account for the browser
recoveries. Browser probes made 38 attempts across eight publishers. A failed representative
stops further probes for that publisher/failure category; siblings were not individually
tested in the browser. HTTP access checks covered every selected URL.

Nine of 18 publishers have at least one readable article. This does not mean the other
nine websites are inaccessible to humans. Article URLs and publisher domains are separate
denominators. Extraction success does not certify complete text.

| Remaining reason | URLs | Share of full pool |
| --- | ---: | ---: |
| HTTP access denied, not recovered by sampled browser probes | 45 | 17.65% |
| Insufficient visible article text | 24 | 9.41% |
| Restricted metadata with no confidently identified public article container | 15 | 5.88% |
| Network failures after bounded retry | 12 | 4.71% |
| Explicit robots disallow | 11 | 4.31% |
| Robots endpoint unavailable; article fetch skipped | 2 | 0.78% |

Per-URL results, captured HTTP responses, publisher counts, extracted text and browser
attempts are local in `.researcher/full_pool/access_v1/` and `recovered_v1/`.
The final readable audit is `recovered_v1/access_report.md`. Public article bodies and
company documents remain ignored by Git.

## Stronger extraction

- Bounded robots redirects, permission caching and publisher crawl delays.
- One retry for transient network failures, preserving errors. Rate-limited origins stop.
- Captured responses allow replaying the old extractor without refetching articles.
- Subscription links in footers do not automatically block an otherwise visible article.
  Restricted-access metadata alone does not discard substantial public article text.
  Hidden/JSON article bodies are never mined, and visible subscription gates remain barriers.
- Precision/recall extraction and visible article-paragraph fallbacks preserve fuller context.
- Optional fresh normal-browser rendering reads visible DOM text. It may dismiss an ordinary
  cookie dialog, but never logs in, solves CAPTCHAs, or bypasses verification/subscriptions.
  Robots permissions are checked for document navigation and redirects.

Results describe this environment and capture date; extraction quality still needs review.

## Commands

Run from the repository root. Install ordinary Playwright Chromium once if necessary:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python -m playwright install chromium
```

Audit accepted URLs with up to four publisher workers and a two-second per-origin delay:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python scripts/audit_article_pool.py --output-dir .researcher/full_pool/access_v1
```

Try browser recovery on eligible failures:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python scripts/recover_article_pool.py \
  --audit-dir .researcher/full_pool/access_v1 \
  --output-dir .researcher/full_pool/recovered_v1
```

`--browser-executable` can select an existing compatible Chromium. This machine used its
cached headless Chromium without stealth settings.

Run the complete collaboration, optionally including one correction cycle:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python scripts/run_full_article_workflow.py \
  --articles .researcher/full_pool/recovered_v1/articles.json \
  --brief '/Users/iphonex/Downloads/Fizzera Sodas.pdf' \
  --output-dir .researcher/full_pool/workflow_v2 \
  --as-of 2026-10-25 --correct-once
```

Omit `--correct-once` to present the first reviewed draft. The editor preserves every hold.
`--research-only` builds the merged evidence pack without downstream calls. Agent runs use
the existing API key and make paid model calls; extraction does not use an LLM.

## Larger-pool handoff and resume

Researcher calls remain limited to five articles. The coordinator researches each readable
body exactly once, caches successful batches, namespaces finding IDs, derives mechanical
coverage references in code and validates citations before merging. All 255 source records
remain attached: 146 readable bodies and 109 unavailable assessments. Missing bodies are
never summarized from titles. Cove Soda and Crazy D's findings can be labeled directly.

Resume reuses completed batches when corpus, model, question, prompt and batch size match.
Mechanical coverage links and single-source publication dates are derived in code from
the findings' references and catalog metadata; original model values are retained for audit.
An invalid multi-article batch is isolated into individually checkpointed article calls
once. Invalid single-article output still stops the run; citations and claims are never
invented to pass validation. Cross-date findings are not silently assigned a replacement date.
Failed calls are preserved rather than silently excluded. Incomplete research cannot pass
downstream. `--research-dir` reuses a compatible completed checkpoint in a fresh downstream
attempt without repeating Researcher calls.

Workflow-level resume also binds corpus, company PDF, date, model settings and correction
policy. A raw Analyst draft rejected solely for a documented legal-name alias can be
validated against the exact handoff and resumed without repeating its model call. Unknown
company names and all other structural failures remain errors. Original raw output and
normalization provenance are retained. Incomplete reviews resume in a new review directory.

Full source snapshots remain in the saved handoffs. Analyst and editor receive source
paragraphs; the Reviewer uses full bodies of cited articles, the company brief, a source
catalog and supplementary TF-IDF hits. It does not receive every uncited body in its working
prompt, so its completeness check is limited. Actual token counts are checked before
downstream calls; included source bodies are not silently truncated. The corpus
command defaults Analyst/Reviewer to `gpt-4.1` for larger context while respecting explicit
environment settings. Reviewer and editor also default to `gpt-4.1` outside that command;
the Researcher and pilot Analyst retain their defaults. Align all model variables explicitly
for same-model experiments.

This is a historical discovery snapshot, not a fresh market census. Syndicated releases and
repeated events are not independent corroboration. No quality benchmark is run here.

## Completed run

`.researcher/full_pool/workflow_v1/` contains the completed collaboration:

- `research/researcher_output.json`: 255 source assessments, 136 findings and all frozen
  source paragraphs, produced by 30 completed small research batches.
- `analysis/analyst_report.md`: Fizzera-specific strategy across all five priority areas.
- `analysis/review/review_report.md`: the independent Reviewer returned `pass`, with no
  issues. The optional correction cycle therefore did not run.
- `executive/executive_brief.html` and `.md`: the 512-word executive presentation, with
  coverage for Olipop, Poppi, Culture Pop, Zevia and Cove Soda, and an explicit Crazy D's gap.
- `workflow_manifest.json`: source counts, paths, input bindings, review state and a verified
  final cached-validation trace. Original paid calls remain in local MLflow.

The first saved Analyst draft used Fizzera's documented legal name instead of its short
name. It was finalized after verifying that alias in the brief and passing all remaining
checks; the paid Analyst call was not repeated. The editor's original response was also
finalized without another call after allowing a 25-word caveat rather than a rigid 20-word
limit, while keeping the overall 650-word prose cap. Raw responses and provenance remain.
Usage for these finalized raw drafts is marked unavailable in their standalone manifests,
rather than inventing token totals; the original generation traces retain their records.

The original run passed 94 functional tests. Desktop/mobile layout checks found five cards, no horizontal
overflow and no broken internal references. A model review pass is not human approval or
a claim that factual quality has been independently benchmarked.

Offline functional tests:

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python -m unittest corpus.test_corpus corpus.test_text reviewer.test_evidence \
  executive.test_executive analyst.test_revision reviewer.test_reviewer \
  analyst.test_workflow researcher.test_agent crew_ai.test_data
```

## Text preparation and evidence reliability update

The full-corpus command now prepares a new immutable snapshot before Researcher batching.
It repairs known encoding artifacts, normalizes whitespace, removes exact UI labels and
recognized newsletter/related-story/contact tails, and preserves original paragraph IDs.
Every removal and changed string is recorded in `prepared/cleanup_audit.json`; original
snapshots remain untouched. Unknown encoding damage is flagged rather than guessed away.
These are conservative text operations, not factual verification. Reported brand claims,
forecasts and opinions must remain attributed and labelled in the evidence pack.

`prepared/text_index.json` contains sparse TF-IDF vectors with a maximum 240-word chunk,
article and paragraph IDs, date, URL, source-body hash and word offset. Numbers, negations
and currency tokens remain searchable. The index provides lexical retrieval without a
paid embedding call or a separate database. Similarity does not establish support. Exact
duplicate bodies are flagged; this does not detect all syndicated events or near-duplicates.

Standalone preparation (no model calls):

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python scripts/prepare_article_text.py \
  --articles .researcher/full_pool/recovered_v1/articles.json \
  --output-dir .researcher/full_pool/new_clean_snapshot
```

Optional `--researcher-output PATH` reuses prior findings only when the replacement sources
are the exact mechanical cleanup of their saved sources and every citation survives. It
explicitly records that claims were not regenerated. Removed cited evidence requires a new
Researcher run, not silently relinking citations. Full-run plans bind the preparation
version and agent prompts, preventing an older reviewed result from resuming under a new
policy unnoticed; use a fresh output directory after policy changes.

The Reviewer now requires a support decision for every observed-fact sentence, with exact
excerpts checked against that insight's cited paragraphs. Partial or unsupported decisions
automatically produce blocking issues, even if the model's separate issue list is empty.
Every insight, recommendation and competitor also requires explicit chronology, geography,
causality and company-constraint checks. Material risk flags automatically block a pass.
Saved checks are revalidated with the saved verdict; raw model output remains available.

The executive's final wording receives a separate native CrewAI evidence audit with exact
source/brief anchors. It cannot inherit the Analyst's pass for newly introduced claims.
A failed or absent final audit preserves a hold. These controls make omissions and invented
references harder to accept; they do not guarantee that a model's entailment judgment is
correct. Functional tests are not a quality benchmark.

The local update cleaned all 255 records (146 readable), removed 484 boilerplate paragraphs,
normalized 335 paragraphs and indexed 2,826 chunks. No known encoding flags remain under
the implemented detector; this is not a claim that all noise or extraction omissions are gone.
Every existing finding citation survived. No exact duplicate complete body was detected;
repeated events and partial syndication still require care.

Source-inspected corrections are in `.researcher/full_pool/quality_v2/corrected/`, including
an analysis diff, provenance manifest and a 431-word executive draft. Corrections narrow
Poppi messaging attribution, separate Zevia periods and causal uncertainty, distinguish
Canadian listings from provincial results and US formats, remove unsupported strategy
success claims, qualify multipack discounts, and replace the weak Berry Social launch gate.
The original model output is preserved. These are coding-assistant corrections, not a newly
generated or independently approved agent report; the draft remains on hold.

The live recheck was rejected by automatic approval review because transmitting the private
Fizzera brief/analysis and article text to the configured external API requires explicit
approval. No API call from that rejected command ran. After authorization, this command
checks both corrected artifacts without regenerating them:

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-corpus.txt \
  python scripts/recheck_corrected_brief.py \
  --analysis-run .researcher/full_pool/quality_v2/corrected \
  --executive-json .researcher/full_pool/quality_v2/corrected/executive/executive_brief.json \
  --output-dir .researcher/full_pool/quality_v2/live_recheck
```

This uses the configured OpenAI key for paid Reviewer and final-prose audit calls, records
MLflow traces and preserves a hold if either check fails. It is a production verification
run, not a controlled quality benchmark. The local suite currently passes 109 tests.
