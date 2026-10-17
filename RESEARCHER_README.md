# Functional soda Researcher pilot

Question: **What is happening in the functional soda market, how are Olipop,
Poppi, Culture Pop, and Zevia competing, and what evidence shows which strategies
are working?**

This standalone Researcher makes one OpenAI model call on one to five frozen
article records. It returns a structured JSON evidence pack. It does not run the
Planner, Analyst, Writer, or Reviewer. The existing CrewAI experiment is separate.

## Setup and run

Set `OPENAI_API_KEY` in your local `.env`. The existing key is loaded automatically;
never commit it. Optional overrides: `RESEARCHER_MODEL` (default `gpt-4o-mini`) and
`RESEARCHER_JUDGE_MODEL` for the optional evaluation script. No SerpAPI key is needed.

From the repository root, use the isolated pilot dependencies:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python scripts/prepare_researcher_articles.py
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python scripts/run_researcher.py --output .researcher/my_evidence_pack.json
```

The runner prefers `.researcher/articles_rechecked.json` when present, falling back
to the original `.researcher/articles.json`. Use `--articles` to pin a particular
snapshot explicitly. The refreshed five-article example is:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python scripts/run_researcher.py --articles .researcher/articles_rechecked.json --output .researcher/my_expanded_pack.json
```

Preparation fetches only the five URLs in `researcher/articles.json`, checks robots
and access barriers, and freezes paragraphs with stable IDs and a content hash.
It refuses to replace existing `.researcher/articles.json`. The runner also refuses
to replace existing output. Reuse frozen input when comparing prompts.

The five user-selected articles are used explicitly; the discovery run's date and
eligibility filters are not applied to this separate pilot. Access recheck:

| Article | Text now available to the agent |
| --- | --- |
| Modern Retail founder shopping profile, March 17, 2026 | 807 words; original HTML extraction |
| Food Dive acquisition denial, May 2, 2024 | 643 words; original HTML extraction |
| Retail Brew Pepsi prebiotic cola, July 28, 2025 | 883 words; public web reader |
| BevNET Alix Earle partnership, May 27, 2025 | 713 words; public web reader |
| Marketing Brew Olipop mocktails, February 6, 2024 | 878 words; original HTML extraction |

The original extractor's Retail Brew failure occurred at `/robots.txt`, before it
requested the article. Its BevNET failure was triggered by structured metadata,
without confirming a visible paywall. A fresh separate automated browser reached
HTTP 403 security-verification pages on both sites; no cookie dialog was reached.
The public reader exposed both article bodies. These different retrieval outcomes
must not be described as proof that the articles are inaccessible to a person.

Both recovered bodies were imported into a **new** snapshot using:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python scripts/import_researcher_articles.py --supplement .researcher/reader_import.json --output .researcher/articles_rechecked.json
```

The supplement is a local recorded reader export, not a committed article corpus
or an automatic web-fetch fallback. It retains the reader retrieval time and source
line ranges. Import strips no article paragraphs beyond the explicitly excluded
newsletter/navigation/footer lines, recomputes hashes and paragraph IDs, and leaves
the previous snapshot intact. No login, security challenge, or hidden article body
was bypassed. Reader snapshots are not independent proof of live page completeness.

Unavailable records are assessed in code with no generated summary. They are not
sent to the model. To use lawfully obtained text for either missing article, add
its paragraphs to a separate input JSON following `researcher/schema.py`, compute
`text_sha256` over `"\n\n".join(p["text"] for p in paragraphs)`, and pass `--articles`.
No unavailable article facts are inferred from its title or search snippets.
Extracted text still needs your manual review; HTML extraction does not prove completeness.

## Inspect the evidence

The output JSON contains:

- `article_assessments`: relevance, contextual research brief, and reason for each
  article. The former 45-word summary cap and four-finding cap have been removed.
- `findings`: dated factual claims, companies, dimension, attribution, limitations,
  and citations using `article_id` plus `paragraph_id`.
- `company_coverage`: findings for each tracked company and explicit evidence gaps.
- `sources`: source URLs, dates, availability, retrieval method, hashes, and **every
  frozen source paragraph**. Source text is not compressed to the generated summary.
- `run`: model, token usage, elapsed time, prompt hash, and persisted MLflow trace ID.

The runner also writes `<output>.analyst.txt`, containing the generated evidence
pack followed by every source paragraph with its citation ID. Use that file as the
next Analyst's context. This retains about 3,900 source words for these five articles,
even if a generated brief is short. `--analyst-context` overrides its output path.

Read each cited paragraph in the selected source snapshot alongside the finding.
The code checks citation existence, dates, source hashes, assessment coverage, and
company references. **Those checks do not establish that a claim follows from the
paragraph.** That is part of your quality evaluation. Sales associations are not
proof of causality; the pilot only permits `not_measured` and `reported_association`
labels. Narrative wording still needs review.

## Local functional checks

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python -m unittest researcher.test_agent crew_ai.test_data
```

These checks make no model calls and do not score summary quality. The initial
live output is `.researcher/evidence_pack.json`; it predates the stricter date and
effectiveness schema and should not be treated as validated final evidence.
The revised smoke-test output is `.researcher/evidence_pack_ready.json`: it passed
structural validation and persisted one trace with an agent span and a model span.
Its summary quality is left for your evaluation.
The newer `.researcher/evidence_pack_expanded.json` and accompanying
`.researcher/evidence_pack_expanded.analyst.txt` use all five bodies and the complete
source handoff. Earlier example outputs have not been overwritten.

## Optional evaluation, for you to run

The MLflow script follows the installed agent-evaluation dataset/evaluation
templates. It discovers/reuses native datasets, registers native judges, and uses
`mlflow.genai.evaluate()` on saved real output. It does not call the Researcher
again. It does make paid judge calls. Five criteria cover factual support,
relevance, effectiveness language, temporal precision, and coverage/abstention.

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt python scripts/evaluate_researcher.py --output .researcher/my_evidence_pack.json --label my_review
uv run --cache-dir .cache/uv --with-requirements requirements-researcher.txt mlflow ui --backend-store-uri sqlite:///.researcher/mlflow.db
```

One initial scoring run was started before you chose to handle evaluation yourself;
no further judge runs were made. This is one combined research task, not five
independent benchmark tasks. Automated judgments are provisional and do not replace
your assessment or provide a general accuracy rate.

By default MLflow uses local `.researcher/mlflow.db`. Existing MLflow environment
configuration takes precedence. Source snapshots, generated outputs, traces, and
local artifacts are ignored by Git. SDK requests have no automatic retries and a
180-second timeout. Dollar cost is not estimated because rates vary; token counts
are recorded for your calculation.
