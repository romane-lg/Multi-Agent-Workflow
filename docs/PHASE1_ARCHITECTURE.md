# Repository inspection and Phase 1 design

## Existing implementation

The primary general workflow is scripts/run_intelligence.py ->
intelligence.workflow.run_workflow. It executes Planner -> Researcher -> Analyst ->
Reviewer -> deterministic output. Each role is a native CrewAI Agent/Task created
by intelligence/runtime.py; sequencing and artifact persistence are explicit Python.
Prompts are in planner/agent.py, researcher/general.py, analyst/general.py and
reviewer/general.py. No agents, prompts or research behavior are replaced by Phase 1.

The Researcher does not browse. It consumes frozen researcher.schema.Article records:
URL, publication date, retrieval timestamp/method, availability, exact paragraph IDs
and a SHA-256 of the body. researcher/general.py checks hashes, processes at most
five readable records per call, merges all supplied records and retains unavailable
records as explicit gaps. Acquisition remains news_scrapper/ plus corpus/access.py
and corpus/browser.py. Discovery metadata is not equivalent to article evidence.

The general Analyst keeps observations separate from interpretation, supports arbitrary
companies and optional supplied context, and cites findings and/or original paragraphs.
The Reviewer inspects every insight, recommendation and Planner task, checking exact
source excerpts and chronology/geography/causality/company constraints. Its runtime
pass/hold is not an independent experimental quality score.

The coordinator already stores validated user inputs, plans, batch outputs, merged
evidence, analysis, review, final JSON/Markdown, raw responses and per-stage timings.
The backend reports CrewAI token usage when available; missing data is not a
reliable zero. No seed is currently configured; temperature is zero and tools disabled.
Dependencies are the existing CrewAI, Pydantic, OpenAI/MLflow and corpus utilities.
The repository also contains extensive unittest suites using mocked output.

Preserved legacy paths: run_crewai.py compares a single versus three-role scaffold
over discovery metadata; analyst/workflow.py is the earlier Fizzera-specific flow,
with separate reviewer, optional one-cycle revision and executive-editor commands.
They are not silently used as the new benchmark baseline. scripts/evaluate_researcher.py
is a separate, paid MLflow LLM-judge pilot. Phase 1 never invokes it or its judges.
The supplied Fizzera PDF is optional company context, not public benchmark ground truth.

## Phase 1 implementation

A separate benchmarking/ package calls the existing general coordinator with an
ObservedBackend wrapper. The wrapper delegates the exact prompt/schema/payload and
returns the identical stage response; it only records timing and returned usage.
Two optional StageResult counters expose reported model calls and configured-disabled
tool executions; this instrumentation does not add calls or alter prompts.

The benchmark starts as 12 explicit draft questions, three per requested category.
Human-verified releases copy exact reference and workflow-input snapshots into a
new version directory, validate hashes/excerpts and attach a canonical manifest
checksum. Reference answers never enter agent inputs.

Independent manual scoring uses a versioned weighted 0-4 rubric and explicit claim,
component, verified-error and flag annotations. Precision/recall use those annotations,
not runtime Reviewer assertions. Saved evaluations bind exact run, task, report and
benchmark hashes. A whitelist export of pre-review evidence and initial analysis
supports future blinded human review without implementing that review workflow.

A baseline runner supports task subsets/all tasks and repeated runs. A --live gate
is mandatory for CLI paid execution. Config rejects recovery/human-review architectures
and unsupported temperature/seed/tool settings. Exceptions preserve run metrics
and artifacts; new output directories and exclusive writes prevent overwrites.

CSV exports and their data dictionary support joins by run_id/task_id/evaluation_id.
Recovery metrics and future-version evaluation labels exist, but neither Version 2
nor Version 3 execution is implemented. Tests use synthetic benchmark fixtures and
mock model usage, not live sources or paid calls.
