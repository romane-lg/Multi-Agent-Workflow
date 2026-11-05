# Phase 1: benchmarking and independent evaluation

Read [the architecture inspection and design](docs/PHASE1_ARCHITECTURE.md) for the
existing agents, source contracts, orchestration, logging and integration boundary.

This package benchmarks the existing User -> Planner -> Researcher -> Analyst ->
Reviewer -> Output baseline. It does not implement targeted recovery, human review,
extra agents or automatic LLM judges. It adds no dependencies.

## Benchmark status

benchmarks/ci_draft_v1.json contains exactly 12 concrete question designs: three each
for company information, competitor comparisons, market developments and evidence
challenges. Named companies and periods are fixed. ALL TWELVE ARE DRAFTS.
No reference facts, numerical expected answers, source URLs or retrieval dates
have been invented. Source authority and availability are not assumed.

Draft questions can be inspected but cannot be executed by the experiment runner
or marked frozen without independent source verification. Questions B04/B05 need
date-bound price/feature snapshots; D10 needs a deliberately unavailable input
record, not a claim that a real website is down; D11 needs two genuinely differing
source figures selected and verified; D12 needs a documented disclosure search,
not an unsupported assertion that a metric is private. C07 needs three verified
qualifying partnership announcements or a revised task in a new draft version.

This release is infrastructure and draft question design, not a frozen factual
benchmark or a measured architecture comparison.

## Verify and freeze

1. Review each question and required answer component for a reproducible scope.
2. Collect legitimate official sources within the question's date/window. Save exact
   UTF-8 reference text locally. Record URL, real retrieval timestamp, snapshot path
   and SHA-256 under reference_sources.
3. Populate reference_facts with factual statements and exact excerpts from the
   referenced snapshots; link every required component to verified reference fact IDs.
   For abstention tasks, verify the evidence scope and absence/availability conditions.
   A plausible statement or a model review is not verification.
4. Prepare a frozen Article JSON array for each task, with stable article/paragraph IDs,
   source URLs, retrieval metadata, body hashes and unavailable records where required.
   Use the existing source preparation/extraction pipeline; do not include answer keys.
5. Set input_snapshot and input_sha256, verification_status to verified, and record a
   human verified_by, verified_at and verification notes. Paths must stay within the
   draft benchmark directory. Each expected component needs an evidence-backed key.
6. Create a NEW release version. Freezing copies the exact verified inputs and references
   into a new assets directory. It never overwrites a release or edits the original draft.

```powershell
python -B -X utf8 -m benchmarking inspect benchmarks/ci_draft_v1.json
python -B -X utf8 -m benchmarking freeze benchmarks/verified_draft.json --releases-dir benchmarks/releases --version ci-1.0.0
```

The second command is a future example: verified_draft.json is NOT supplied.
Use a new version for changed questions, source inputs, components or reference answers.
Load checks detect content/asset drift. Hashes establish consistency, not factual truth
or protection against an adversary rewriting all manifests.

## Baseline experiments

Copy benchmarking/config.example.json and set benchmark_version to the exact frozen
release. task_ids=null selects every task; supply a list or repeated --task flags for
a subset. repetitions specifies independent full workflow executions. All models are
explicit; default configuration mirrors the general workflow's current defaults.
For a same-model experiment set all four names identically.

```powershell
python -B -X utf8 -m benchmarking run --benchmark benchmarks/releases/ci-1.0.0/benchmark.json --config benchmarking/config.example.json --task A01 --repetitions 2 --output-dir .researcher/experiments/study_001 --live
```

This is a paid-execution example, not a command run during implementation.
Omitting --live makes the CLI stop before reading inputs or making calls.
Programmatic tests inject a mock backend factory; normal execution needs live=True.
A fresh backend is created per run; no stage retry or recovery is scheduled.
A runtime Reviewer fail is a structurally completed run with a publication hold,
not a transport failure. A thrown exception is a failed execution, preserved in logs;
remaining selected task repetitions continue.

Temperature is currently fixed at 0, seed is unsupported/null, and tools are disabled,
matching the existing backend. Unsupported settings are rejected rather than silently
ignored. No deterministic-output guarantee is made. Configuration, package versions,
Git commit, source-code fingerprint, benchmark and exact input hashes are recorded.

## Usage and configurable cost

Agent rows record UTC start/end, measured duration, model name, reported tokens,
model/tool call counts when available, status and safe exception class.
Actual provider/framework usage is used; unknown values stay null.
CrewAI successful_requests is recorded as model_calls when returned; framework
structured-conversion calls may affect that value. Native external tools are explicitly
disabled; custom backends report tool counts or leave them unknown.

Workflow totals are null if ANY stage has unknown usage/cost. known_* sums are explicitly
partial. No API key or environment-variable dump is logged. Exception messages are
replaced by a safe generic summary; workflow raw responses remain in local artifacts.

benchmarking/pricing.example.json has NO rates. Supply a dated, currency-labelled,
versioned schedule to --pricing. Example shape with YOUR verified rates:

```json
{
  "currency": "USD",
  "pricing_version": "your-verified-schedule",
  "effective_date": "2026-11-04",
  "models": {}
}
```

Each models entry requires input_per_million and output_per_million; optional
cached_input_per_million requires actual cached token counts. Prices match exact model
names. Missing usage, prices, or necessary cache information yields null cost.
Configured token-rate costs are estimates, not invoices; taxes, tools and unreported
provider charges are not invented. Verify rates yourself before using a price schedule.

## Independent human evaluation

The runtime Reviewer never supplies the independent quality score. No second LLM is
called. benchmarking/rubric.py defines five criteria, with explicit anchors for every
integer score 0-4:

| Criterion | Weight |
| --- | ---: |
| Factual accuracy | 30 |
| Task completeness | 25 |
| Evidence quality | 20 |
| Claim support | 15 |
| Clarity and usefulness | 10 |

Quality = sum(weight * score / 4), already normalized to 0-100.
A complete set of 3s yields 75. The human must inspect the report and reference evidence;
merely copying the internal verdict is not an independent evaluation.

```powershell
python -B -X utf8 -m benchmarking evaluation-template --run-dir .researcher/experiments/study_001/runs/RUN_ID --stage final --output .researcher/manual_evaluation.json
python -B -X utf8 -m benchmarking score --run-dir .researcher/experiments/study_001/runs/RUN_ID --evaluation .researcher/manual_evaluation.json
```

Fill evaluator_id, scores, per-criterion comments, verified annotations and timestamp
before scoring. The template deliberately has null scores and a blank evaluator, so
it is invalid until filled. Scores require human identity and independence from the
internal Reviewer. Evaluations bind exact report/run/task/benchmark hashes; changed
artifacts are rejected. New evaluations get new IDs and never overwrite earlier ones.

For future blinded human review, export the pre-review Analyst report and evidence:

```powershell
python -B -X utf8 -m benchmarking blind-export --run-dir .researcher/experiments/study_001/runs/RUN_ID --output-dir .researcher/blind_packets/PACKET_ID
```

The whitelist includes query, Planner output, Researcher evidence and initial Analyst
JSON only. It does not copy AI feedback, final output, the run manifest's verdict or
ground-truth answers. It is an export facility, not a human-review execution workflow.

## Claim and error annotations

Accuracy (correct / incorrect / unverifiable) and citation support (supported /
unsupported / unverifiable) are separate dimensions. An unsupported claim may happen
to be true; a cited source may support a claim that is factually wrong. A missing
answer component is an omission, not an automatically fabricated factual claim.

Independently enumerate:
- claims with exact location/text, both labels, evidence notes and optional reference facts;
- every required component, labelled correct / incorrect / missing / unverifiable;
- verified errors with IDs and optional claim/component links;
- reviewer flags with human-verified matched_error_id, or null for a false positive.

Never import AI flags as verified errors automatically. The human asserts complete
claim, error/flag and component inventories separately. Rates using incomplete
inventories remain null. A complete error inventory must account for already annotated
incorrect/unsupported claims and missing components. Complete components must cover
every frozen required component exactly once.

Metrics:
- Unsupported claim rate: unsupported / all factual claims.
- Precision: true-positive flags / all flags. Each flag maps to at most one verified
  error; split bundled flags into atomic annotations. Duplicate flags do not inflate recall.
- Recall: distinct verified errors flagged / all verified errors.
- Completeness: correctly addressed / all frozen required components.
- Recovery success: cases where ALL target errors are resolved / all recovery cases.
- Error reduction: (before-after)/before; negative means errors increased.

A zero denominator is null, not zero or perfect accuracy. Recovery metrics are null
for baseline; schema rejects recovery data on sequential_v1. Counts of correct,
incorrect, unsupported, unverifiable claims, missed errors, detected errors, false-positive
flags and missing components remain available alongside rates. These are independently
annotated observations, not model judgments promoted to ground truth.

## Storage and CSV exports

Each experiment has immutable configuration and benchmark/pricing snapshots plus
runs/RUN_ID/. Each run stores benchmark_task.json, experiment_run.json, agent_metrics.json,
workflow/ (all original agent artifacts), and evaluations/EVALUATION_ID.json when scored.
Initial/final artifact hashes support future pre/post comparisons. Additional versions
may register pre_recovery/post_recovery reports later; Phase 1 does not create them.

```powershell
python -B -X utf8 -m benchmarking export --experiment-dir .researcher/experiments/study_001 --output-dir .researcher/exports/study_001
```

Outputs: experiment_runs.csv, agent_metrics.csv, quality_scores.csv,
claim_annotations.csv, error_detection.csv and benchmark_tasks.csv.
Every table is emitted with headers even if empty. UTF-8 CSV uses blank missing values
and JSON strings for lists/objects. Join using run_id/task_id/evaluation_id.
error_detection has verified_error rows (detected/missed) and reviewer_flag rows
(true_positive/false_positive); filter row_type before counting.

data_dictionary.json describes EVERY exported field and missing-value conventions.
The definitions also live in benchmarking/export.py's SCHEMAS.
Exports revalidate evaluation identity and recompute independent scores/metrics rather
than trusting cached totals. Export directories must be new.

## Offline validation and work before live experiments

```powershell
python -B -X utf8 -m unittest benchmarking.test_phase1 intelligence.test_workflow crew_ai.test_data
```

Tests use synthetic reference text, synthetic human attestations and mocked responses.
They do not verify public facts, run a live experiment or measure agent quality.
The earlier legacy agent suites additionally require the existing model/MLflow packages.

Before the first real run: verify the 12 task designs, collect and review source snapshots,
build the per-task frozen Article inputs, finalize reference answers, freeze a new version,
install the existing workflow dependencies, configure API credentials locally, explicitly
align model settings, and optionally supply verified pricing. Validate the live backend
separately before spending on all tasks/repetitions. The newly supplied Fizzera company PDF
can support a separate company-specific case, but is not automatically public benchmark
ground truth and does not substitute for these task-specific references.

Phase 1 infrastructure is testable independently of source curation. It is not a claim
that the draft benchmark is ready for live execution or that any architecture is better.
