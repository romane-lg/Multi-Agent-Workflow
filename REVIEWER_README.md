# Independent Fizzera Reviewer

The workflow now supports **Researcher → Analyst → Reviewer** under CrewAI.
The Reviewer is a fresh CrewAI Agent/Task with its own prompt and no shared
conversation, tools, delegation, or memory. It can use the same base model while
independently inspecting the original evidence. Ordinary review stops after its verdict;
an explicit [single correction cycle](REVISION_README.md) is now available separately.

## Review the approved saved Analyst output

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-analyst.txt python scripts/review_fizzera_analysis.py \
  --analysis-run .researcher/fizzera_runs/pilot_v2 \
  --output-dir .researcher/fizzera_reviews/my_review
```

This reuses the frozen Analyst report, Researcher evidence and company brief from
the selected run. It makes a paid Reviewer call without rerunning either upstream
agent or altering the saved report. Choose a new output directory for each review.
No original PDF path is required: the frozen handoff contains its extracted pages.

For a new Analyst run followed immediately by review:

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-analyst.txt python scripts/run_fizzera_analyst.py \
  --brief "/path/to/Fizzera Sodas.pdf" \
  --research-output .researcher/evidence_pack_expanded.json \
  --output-dir .researcher/fizzera_runs/reviewed_run \
  --review
```

Use `--articles` instead of `--research-output` to run the existing Researcher
first. Omitting `--review` preserves the Analyst-only baseline for later comparisons.
`REVIEWER_MODEL` optionally overrides the default `gpt-4o-mini`. The same local
`OPENAI_API_KEY`, pinned dependencies and MLflow configuration are reused.

## Review contract

The Reviewer receives the exact structured Analyst report, all frozen article
paragraphs, every company brief page, provenance notes and any structural preflight
error. The handoff checksum, article text hashes and brief text hash are checked
before any model call. A structurally invalid Analyst draft can be reviewed and
flagged; corrupted upstream evidence stops the workflow.

Four criteria are checked:

| Criterion | What it checks |
| --- | --- |
| Source support | Claim scope, citation relevance, metrics, periods and attribution |
| Interpretation | Facts vs inference, association vs causation, historical context and geography |
| Company fit | Fizzera priorities, budgets, capacity, positioning and proposed tests |
| Completeness | Requested dimensions, competitor coverage, priority decisions and explicit gaps |

Every market insight, recommendation and competitor row must have an individual
review record. The model response schema requires a separate field for each item;
code attaches target IDs, issue IDs and item dispositions consistently in the saved review. Issues identify
the affected report IDs, blocking/advisory severity,
relevant source paragraphs or brief pages where available, and a concrete required
correction. Missing evidence must be identified honestly, without inventing a
replacement citation. Company-brief-led tests are distinguished from unsupported
commercial recommendations. An acknowledged gap in this five-article sample does
not automatically fail the report.

The model returns issues and criterion checks. **Code derives the verdict**:

- Any blocking issue → `fail`, with `hold_for_human_review`.
- Advisory issues only, or no issues → `pass`, with `review_passed`.

Contradictory item labels, omitted items, invalid references, or an ignored
structural preflight error cause a software validation failure; they do not become
a pass. A failed review is a valid completed review, so the CLI still exits
successfully when the review artifacts themselves are valid. Neither verdict
rewrites, publishes, or externally distributes the Analyst report.
An integrated run stays `pending_review` until the Reviewer produces a valid
assessment. A model/schema failure cannot leave the report marked as approved.

## Artifacts

Saved-run reviews write these files to the chosen directory. Integrated reviews
write them under `<analyst-run>/review/` and record the verdict in the parent run
manifest.

| File | Purpose |
| --- | --- |
| `review_report.md` | Readable decision, issues, corrections and item coverage |
| `review_report.json` | Structured verdict and complete assessment |
| `review_input.json` / `review_input.txt` | Exact frozen review input |
| `reviewer_raw.txt` | Raw model output before software validation |
| `review_manifest.json` | Saved-review mode, input hashes, usage, latency and MLflow trace |

The Reviewer checks the structured Analyst report. Deterministic Markdown
formatting is not treated as a second source of factual content. The original
Analyst Markdown remains a draft; consult the separate review status before
accepting it. Standalone review requests changes only: correction attempts remain zero.

## Functional checks and limits

```bash
uv run --cache-dir .cache/uv --with-requirements requirements-analyst.txt python -m unittest reviewer.test_reviewer analyst.test_workflow researcher.test_agent crew_ai.test_data
```

These tests cover pass/fail derivation, evidence integrity, per-item coverage,
reference validation, full CrewAI ordering and preservation of upstream outputs.
They do not establish Reviewer accuracy. No benchmark suite or separate automated
evaluation judges are run by these commands. This runtime Reviewer is itself a
model assessment and may miss errors or raise incorrect issues; inspect its first
reviews manually; the optional correction cycle can decline mistaken suggestions.

## First live sample

The completed sample is `.researcher/fizzera_reviews/pilot_v3/review_report.md`.
It inspected four insights, five recommendations and six competitor rows from
the unchanged `.researcher/fizzera_runs/pilot_v2` analysis. The Reviewer returned
`fail` / `hold_for_human_review`, with seven blocking and nine advisory issues.
One model request completed and its MLflow trace was read back successfully.

**Observed limitation:** several coverage-related flags, particularly issues
010 and 012–016, conflict with explicit missing-evidence rows and gaps already
present in the Analyst draft. These may be false positives; inspect them rather
than automatically following every requested correction. The other issues also
remain model judgments, not independently established errors. The sample is
preserved for your manual assessment; no correction was applied and no additional
benchmark evaluation was run. Earlier `pilot` and `pilot_v2` review directories
preserve responses rejected by software validation and contain no accepted verdict.

## Analyst correction cycle

To pass selected feedback back to the Analyst and independently recheck its revision,
see [REVISION_README.md](REVISION_README.md). This is an explicit, single-cycle command;
ordinary review commands continue to stop after the review.
