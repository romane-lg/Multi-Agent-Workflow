# General competitive intelligence workflow

User query -> Planner -> Researcher -> Analyst -> Reviewer -> Output

This is the general workflow entry point. Company names, industry dimensions,
research tasks, dates and optional company context come from the request.
There is no mandatory Fizzera PDF, soda competitor list, Ontario/BC focus,
currency, product concept, or budget. The existing Fizzera commands retain their
original behavior for compatibility; they do not automatically gain a Planner.
The older single/multi comparison scaffold in run_crewai.py also remains separate.

## Agents and handoffs

1. Planner decomposes the exact question into research tasks with stable IDs,
   evidence requirements, source priorities, suggested searches and completion criteria.
2. Researcher receives that plan and frozen source bodies, in batches of at most
   five. All supplied records remain accounted for. Findings cite source paragraph
   IDs and are namespaced before merging; unavailable bodies receive no model summary.
3. Analyst receives the plan, merged evidence, every source paragraph and optional
   named company context. It separates observations from interpretation and addresses
   each planned task with evidence or a gap. Recommendations are optional.
4. A fresh independent Reviewer receives the Analyst report and original evidence,
   checks every insight, recommendation and planned task, and records source anchors
   plus chronology, geography, causality and company-constraint checks.
5. Code renders output.md and output.json. There is no extra Writer or executive
   model call. Blocking review findings produce hold_for_human_review; a valid pass
   produces review_passed, which is not human approval or an accuracy benchmark.
   Failed validation or transport stops the workflow and preserves a hold.

Planner search suggestions do not run searches. The source acquisition layer remains
the existing scraper/extractor: this workflow researches the complete frozen Article
array supplied through --articles. Passing the discovery metadata JSON directly
is rejected. With a 255-record extracted corpus, all 255 are represented and every
readable body is researched. Extraction still needs to be performed separately if
no article corpus exists. No missing body is inferred from a title.

## Run

Install the existing requirements-corpus.txt dependencies in your project environment.
The general workflow reuses the existing CrewAI runtime, model configuration,
local MLflow configuration, frozen Article format and context-size guard.
No additional dependency is introduced.

Example PowerShell command (the question is an example, not verified market evidence):

```powershell
python -X utf8 scripts/run_intelligence.py --question "Compare the published product features of Acme and Beacon as of 2026-11-04." --company Acme --company Beacon --as-of 2026-11-04 --articles .researcher/articles.json --output-dir .researcher/general_runs/comparison_001 --live
```

--company is repeatable. If omitted, the Planner identifies companies named in the
question. Supply names explicitly for reproducibility.
--period passes the requested research window into the Planner.
--company-context accepts an optional UTF-8 JSON object mapping context IDs to
strings, such as {"planning_constraint": "Management has not authorized expansion."}.
These are user-supplied planning statements, not independently verified market facts.

--live is REQUIRED for the CLI to make paid model calls. It does not fetch new
articles. No live calls were made during implementation or testing.
Choose a new output directory for each attempt. Existing results cannot be overwritten.
Default models: Planner/Researcher gpt-4o-mini, Analyst/Reviewer gpt-4.1.
PLANNER_MODEL, RESEARCHER_MODEL, ANALYST_MODEL and REVIEWER_MODEL override these.
Align all four explicitly for same-model experiments. Unknown context-window
configurations fail before a stage call rather than truncating source text.
The workflow is a Python sequential coordinator around native CrewAI Agents/Tasks,
rather than an implicit CrewAI planning feature. There are exactly four roles.

## Saved outputs

- user_query.json and sources.json: exact validated request and frozen input.
- planner_output.json: task breakdown.
- research_batch_NNNN.json: individual Researcher batch results.
- researcher_output.json: combined findings, complete sources, task/company coverage.
- analyst_report.json: initial analysis, unchanged by the Reviewer.
- reviewer_output.json: independent review.
- output.json and output.md: Analyst content with derived review status and feedback.
- stage_NNNN_ROLE_input.json and stage_NNNN_ROLE_raw.txt: inputs and raw responses.
- run_manifest.json: stage order, source counts, hashes, durations, actual provider/
  framework usage when returned, model names and completion/publication status.

Unknown usage is null, never invented. API dollar cost is not estimated.
The manifest records no credentials or environment dumps. Default .researcher/
locations are already ignored by Git. Review the content before sharing.
No recovery loop or human-review workflow is added by this entry point. Independent Phase 1 benchmarking is provided separately; see the link below.

## Offline tests

```powershell
python -B -X utf8 -m unittest intelligence.test_workflow crew_ai.test_data
python -B -X utf8 news_scrapper/test_discover_v2.py
python -B -X utf8 news_scrapper/test_discover_v2_2.py
```

The new tests need only the existing Pydantic dependency, use fictitious companies
and source text, and do not import model SDKs or make network/model calls. The full
255-record fixture checks 146 readable and 109 unavailable records with 30 Researcher
batches. These numbers exercise accounting, not a fresh extraction measurement.
Live SDK integration and report quality still require separate verification.

## Independent benchmarking

Phase 1 infrastructure, twelve draft tasks, independent human scoring and baseline
experiment commands are in [BENCHMARKING_README.md](BENCHMARKING_README.md).
