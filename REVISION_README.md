# One Analyst correction cycle

CrewAI now routes a frozen Analyst draft and selected Reviewer issues back to a native
Analyst Crew, then sends the complete revision to a fresh independent Reviewer Crew.
The Researcher does not run again. The original analysis and review stay unchanged.

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python scripts/revise_fizzera_analysis.py \
  --analysis-run .researcher/fizzera_runs/pilot_v2 \
  --review-dir .researcher/fizzera_reviews/pilot_v3 \
  --output-dir .researcher/fizzera_revisions/new_revision \
  --all-issues
```

Alternatively replace `--all-issues` with `--issue-ids issue_001 issue_005` to select
specific feedback. Selection authorizes assessing the feedback, not accepting it blindly.
This performs two model calls with the existing API key: one Analyst revision and one
Reviewer recheck. Models use `ANALYST_MODEL` and `REVIEWER_MODEL` (default `gpt-4o-mini`).
There are no automatic retries, additional research, or benchmark evaluations.

The Analyst must respond to every selected issue as `addressed`, `declined`, or
`needs_evidence`, with a rationale and description of changes. Incorrect criticisms may
be declined. Missing competitor coverage stays an explicit gap. All original sources,
company context, question, dates, and report item IDs are preserved. Code checks citations,
budgets, source integrity, exact feedback/draft correspondence, and required response slots.

The Reviewer checks the entire revised report for new problems and independently resolves
each selected issue as `resolved`, `unresolved`, or `disputed`. `resolved` includes a
demonstrably mistaken original criticism; the Reviewer must explain why. It does not
assume the Analyst's claimed changes are correct. The final revision manifest stays on
hold if the revised report fails review or any selected blocking issue remains unresolved
or disputed. The report review verdict and feedback-resolution status are separate checks;
use `revision_manifest.json` for the combined publication status. A failed recheck leaves
the run pending/held, never approved.

Artifacts in the new output directory:

- `analyst_report.md` / `.json`: complete revised analysis.
- `revision_changes.md` / `.json`: Analyst's response to each selected issue.
- `analyst_report.diff`: code-generated exact comparison, independent of the Analyst's claims.
- `review/review_report.md`: independent review of the revision.
- `review/feedback_resolution.md` / `.json`: independent issue-resolution check.
- `revision_input.json`, `revision_lineage.json`, and `revision_manifest.json`: frozen
  original draft/evidence/selected issues, parent hashes, usage, latency, and final status.
- Raw model responses and a verified local MLflow trace support inspection.

Exactly one correction is permitted per lineage. Passing a revision directory back as
`--analysis-run` is rejected. Output directories cannot be overwritten. This is a prototype
runtime collaboration loop, not proof of improved quality; model judgments still need
human assessment. The initial Reviewer has shown false positive coverage flags.

If the Analyst revision succeeds but the Reviewer transport fails, resume just the recheck
in a new directory. This neither reruns the Analyst nor consumes another correction cycle:

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python scripts/recheck_fizzera_revision.py \
  --revision-dir .researcher/fizzera_revisions/new_revision \
  --review-output-dir .researcher/fizzera_revisions/new_revision/review_retry
```

Resume is allowed only while the revision manifest is `pending_review`; existing failed
review artifacts are preserved. It verifies saved revision/source hashes before a model call.

## Saved Fizzera run

The first completed revision is `.researcher/fizzera_revisions/pilot_v2/`.
It reuses the approved `fizzera_runs/pilot_v2` draft and `fizzera_reviews/pilot_v3`
feedback. The Analyst responded to all 16 suggestions. An API transport failure during
review was resumed into `review_retry/` without rerunning the Analyst. The verified
recheck trace is `tr-fb40e1d42f7d52819baff1ab2efc4bbc` (four spans).

The combined status is **hold_for_human_review**. The Reviewer again flags acknowledged
competitor gaps, and some feedback-resolution explanations refer to different issues or
claim fixes while its full review repeats the criticism. The Analyst also claims some
implementation details were added where the revised wording remains general. Inspect
`analyst_report.diff` and original evidence rather than treating either model's account
as verified improvement. No second correction or benchmark evaluation was run.

Offline functional checks:

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python -m unittest analyst.test_revision reviewer.test_reviewer analyst.test_workflow \
  researcher.test_agent crew_ai.test_data
```
