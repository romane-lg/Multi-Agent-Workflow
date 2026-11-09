# Pre-experiment readiness audit

Date: 2026-11-08 (America/Toronto). HEAD: `a6735d693b8d0d9268dc769072ded2ed281aa9ea`.

## Executive assessment

**NO-GO for paid pilot or full experiments.** V1/V2 control flow is substantially implemented and should be retained. Blockers are an unrelated unverified benchmark, insufficient reproducible evidence, missing dependencies and paired analysis/export gaps.

All twelve tasks are drafts, predominantly about technology companies. None explicitly addresses Fizzera/functional soda; all lack verified reference and input packs. Only five distinct article bodies are available here. The 255 accepted discovery URLs are not 255 usable articles. Historical claims of 146 readable articles cannot be verified because their ignored corpus directory is absent.

No production code changed, dependencies installed, credentials tested, external sources fetched, paid calls or live experiments run. Only this report is intended to change. The pre-existing untracked file beginning `tructure and V1 V2 architecture experiments` was untouched. No sub-agents were used; no AGENTS.md was found in the workspace search.

PASS means a bounded property supported by code/tests; PARTIAL means material gaps; FAIL means unmet readiness; NOT VERIFIED means unavailable evidence. Offline success does not demonstrate report accuracy.

| Requirement | Status | Evidence |
| --- | --- | --- |
| Local evidence sufficient for benchmark | FAIL | Five narrow bodies; no frozen task packs. |
| Historical full-corpus extraction | NOT VERIFIED | FULL_CORPUS_README references absent .researcher/full_pool/. |
| Provenance/extraction safeguards | PARTIAL | researcher/general.py, corpus/access.py, corpus/text.py; quality unverified. |
| V1 no recovery / V2 one correction maximum | PASS | paired.py:run_variant, recovery.py:correct_once; paired tests. |
| Semantic routing correctness | PARTIAL | Model classifications control routing. |
| Failed review/audit preserves hold | PASS | reviewer/general.py:validate_review, presentation.py:present. |
| Current architecture documentation | FAIL | Phase 1 documents still say V2 unimplemented. |
| Fizzera verified frozen benchmark | FAIL | Twelve drafts; no easy task/release. |
| Answer keys excluded from agent inputs | PASS | paired.py:prepare_pair, runner.py:run_experiments. |
| Independent scoring foundations | PASS | evaluation.py, schema.py, rubric.py, metrics.py. |
| Complete metrics/export | PARTIAL | New-error/failure aggregation incomplete; CSV drops paired fields/F1. |
| Identical initial paired conditions | PASS | Shared generation and hashed evidence/report/review reuse. |
| End-to-end comparison protocol | PARTIAL | Added presentation calls; policies unfrozen. |
| Reproducible installed environment | FAIL | Packages missing; suites cannot import. |
| Accounting/resume | PARTIAL | Unknown accounting explicit; prices and paired stage resume missing. |
| Publisher redistribution authority | NOT VERIFIED | Access checks do not establish redistribution rights. |

## Method and limits

Inspected actual implementations/contracts/prompts, tests, requirements, configuration/benchmark JSON, discovery/extraction artifacts, ignore rules and documentation. Counted JSON records; used temporary injected backends for export checks; extracted PDF locally with existing code. No reference answer was invented/certified. .env exists; .env.example names OPENAI_API_KEY/SERPAPI_KEY. Secret values were not read or printed. Credential validity, provider access, live schema compatibility and billing remain NOT VERIFIED.

## Audit 1 — Data and evidence

| Artifact | Verified local inventory | Usability |
| --- | --- | --- |
| news_scrapper/news_dataset.json | 307 records, no bodies | Discovery only. |
| news_scrapper/news_dataset_enriched_test5.json | Same 307: 5 success, 0 failed attempts, 302 not attempted | Five readable candidates, not verified facts. |
| news_scrapper/news_dataset_v2_2_full.json | 1,436 candidate occurrences, 576 normalized URLs: 255 accepted, 309 rejected, 12 review | No bodies. |
| V2 / V2.2 pilot discovery files | 244 / 67 records, no bodies | Overlapping snapshots; do not sum. |
| researcher/articles.json | Five URL/title/date descriptors without paragraphs/hashes | Not executable Article evidence. |
| Historical full corpus | README claims 146 readable / 109 unavailable of 255 | NOT VERIFIED: .researcher/ absent. |
| benchmarks/ | Only ci_draft_v1.json | Zero verified frozen task packs. |

The enriched legacy pool has 307 distinct exact URLs. Its five bodies have distinct URLs and SHA-256 hashes: zero exact body duplicates among those five. Three URLs occur in the accepted full V2.2 pool; two do not. Full discovery has 860 repeated URL occurrences (1,436 minus 576), not extraction failures. Semantic/event/syndication duplication is unquantified. corpus/index.py and corpus/test_text.py:test_duplicate_bodies_flagged_without_dropping_articles provide infrastructure, not an available full-corpus audit.

Accepted confirmed-company counts: Olipop42, Poppi69, Culture Pop16, Zevia29 (overlap). Summary identifies 151 URLs with tracked companies and 104 industry URLs without one. Cove Soda/Crazy D's are not confirmed-company categories in this discovery configuration, although presentation includes them.

Accepted dimensions: products108, pricing85, retail128, marketing127, business102, consumers111, industry126. These overlap and represent query provenance, not validated topics. Source groups overlap: beverage/food trade119, retail/marketing59, business/financial40, announcements37. Evidence: news_dataset_v2_2_full_summary.json and V2_2_FULL_REPORT.md.

Directly counted accepted domains: BevNET87, FoodBev22, PR Newswire20, AdAge19, Food Dive18, Marketing Dive14, Forbes13, Business Wire12, FoodNavigator-USA10, Bloomberg8, CNBC7, WSJ7, Modern Retail6, GlobeNewswire5, Reuters4, Marketing Brew/ Retail Brew/ Morning Brew1 each. These are metadata URLs, not readable-source counts.

Accepted dates span 2024-10-10 through 2026-10-09. Quarterly counts from 2024 Q4 through 2026 Q4: 19,71,23,29,15,27,25,39,7; boundary quarters partial. Dates are not independently publisher-verified. The five saved bodies are all BevNET new-product roundups concentrated on Olipop, including other brands. Recorded dates: 2023-09-01, 2025-05-02, 2025-08-08, 2026-05-01, 2026-09-11; lengths471–1,083 words. One predates the full discovery window. No validated body-level topic/company matrix exists.

### Quality, traceability and bias

news_scrapper/extract_content.py:Fetcher.extract records original/resolved URL, timestamp, status/error and word count; checks robots, barriers, bounded redirects/response size and minimum100 words. corpus/access.py:public_text adds captured-response replay/visible-container extraction; corpus/browser.py:browser_extract reads ordinary visible browser text. corpus/text.py:clean_articles preserves paragraph IDs and logs edits. Retain these safeguards.

The extraction pilot is not the frozen Article schema. researcher/general.py:validate_sources checks hashes, availability, IDs and nonblank text; validate_batch checks citations/source dates. Internal consistency does not prove completeness, correct publication date, relevance, entailment or truth. No independent quality sign-off exists. Roundups particularly need brand-attribution/omission checks.

Discovery attempted112 queries but remains incomplete:22 exhausted queries,156 attempts,44 retries. Culture Pop lacks accepted company-query URLs in retail/marketing and financial groups; Zevia financial coverage includes a stock quote. Accessibility, search ranking, English/trade-news concentration, brand size, promotional material and syndication can bias evidence. Preserve unavailable records; stratify quality/access by company/publisher rather than substituting titles.

**Benchmark sufficiency: FAIL.** Neither the current technology benchmark nor a full Fizzera study has verified per-task evidence. Assess required answer components, not pool size.

Publisher text is tracked in the enriched pilot, while richer captures/raw outputs/company snapshots belong under ignored .researcher/. Repository LICENSE does not establish rights to third-party text. No publisher-specific redistribution permission or retention register was found. This is an evidence gap, not a legal conclusion. Human curators should decide storage/sharing; shared packages may need references/hashes/lawful access instructions instead of full text. Public names do not establish sensitive research data, but raw artifacts need review before sharing. .env/MLflow stores are ignored.

## Audit 2 — Architecture and workflow

intelligence/workflow.py:run_workflow executes Planner → Researcher → Analyst → Reviewer. Planner creates ResearchPlan from Query; Researcher converts frozen Articles to EvidencePack in batches≤5; Analyst separates observations/interpretations/recommendations/task coverage; Reviewer checks every insight/recommendation/task against original paragraphs. Contracts: intelligence/schema.py, researcher/schema.py. Validators: analyst/general.py, researcher/general.py, reviewer/general.py.

benchmarking/paired.py:prepare_pair runs the initial trajectory once with FizzeraReport, ExperimentalReview, company context and Fizzera rules. It snapshots configuration/supplement/shared artifacts with hashes. load_pair verifies hashes and revalidates objects. run_variant reuses identical initial evidence/report/review.

- V1 has no recovery branch.
- V2 requires failed initial review plus eligible material targets. Pass, formatting-only issues and failures without eligible targets do not trigger correction.
- recovery.py:correct_once enforces MAX_RETRIES=1 and attempt=1: one Analyst revision, one full Reviewer re-evaluation, no recursive loop.
- Analyst-only correction reuses evidence without Planner/Researcher reruns.
- Researcher targets with information_status=missing search only frozen supplements for relevant Planner tasks, selecting≤5 new readable articles. No live browsing or whole-corpus rerun. Absent supplements/unavailable facts remain gaps for qualification/removal.
- Shared originals, pre/post reports, new evidence, responses, exact diff, second review and recovery result are preserved. Stable insight/recommendation IDs enforced.
- Exceptions record failed/hold and preserve prior artifacts. Second review failure and editorial-audit failure preserve publication holds; empty-insight reports block presentation.

Passing paired tests include test_v2_stops_after_second_failed_review, test_targeted_research_uses_only_new_scoped_sources, test_missing_supplement_does_not_repeat_entire_corpus, test_formatting_failure_never_triggers_recovery, test_second_correction_is_rejected_before_any_call, test_final_audit_failure_holds_initial_pass and tamper detection (benchmarking/test_paired.py).

Routing is PARTIAL: ExperimentalItemReview validates values but defaults to advisory/available/no target. targeted_issues trusts model severity/type/agent proposals; no deterministic semantic check proves missing evidence. Cross-cutting blocking_issues without eligible items hold without correction. Publication remains safe, but detection and eligibility can be confounded. Independently annotate routing.

Unaffected-content preservation is prompted; stable IDs, not equality of every unaffected field, are enforced. Diff/full re-review do not certify zero new errors. merge_evidence preserves originals/rejects source mutation; new findings remain unverified.

Completed and publication-approved are distinct. Executive JSON can exist before validation/audit fails; artifact presence/score-template eligibility is not approval. Prespecify partial/failed-output scoring.

Documentation discrepancy: docs/PHASE1_ARCHITECTURE.md, docs/PHASE1_VALIDATION.md and BENCHMARKING_README.md still describe V2 as unimplemented. Paired V2 exists; both variants add Executive/editorial-auditor calls, unlike deterministic general-baseline output. benchmarking/cli.py exposes baseline commands only; no paired CLI/config example. Schema advertises V3 but referenced benchmarking.human is absent; V3 is outside this study.

## Audit 3 — Benchmark validity

| ID | Actual objective in benchmarks/ci_draft_v1.json | Difficulty | Status |
| --- | --- | --- | --- |
| A01 | Microsoft FY2024 products/services/segments | medium | Draft |
| A02 | Shopify2024 geography | medium | Draft |
| A03 | PepsiCo2025 beverage announcements | medium | Draft |
| B04 | Slack Pro / Teams Essentials prices | hard | Draft |
| B05 | Zoom Pro / Teams Essentials meeting features | medium | Draft |
| B06 | Shopify / Wix facilities | medium | Draft |
| C07 | PepsiCo/Coca-Cola/Danone partnerships | hard | Draft |
| C08 | PepsiCo/Coca-Cola acquisitions2020–2025 | hard | Draft |
| C09 | AWS / Microsoft cloud expansion | hard | Draft |
| D10 | Slack/Teams controlled missing pricing source | hard | Draft |
| D11 | Differing Microsoft revenue figures | hard | Draft |
| D12 | Microsoft undisclosed contract economics | hard | Draft |

All twelve inspected:5 medium,7 hard,0 easy; none explicitly Fizzera/functional soda. A03/C07/C08 are beverage-related but broader than target market. Objectives generally specify dates/units/abstention; inventories/three-partnership requirement need verified source scope. Difficulty uncalibrated.

All reference_facts/reference_sources empty; input_snapshot/input_sha256 and verification null. Expected components are scoring designs, not verified keys. D10 unavailable record, D11 actual differing figures and D12 disclosure-search evidence absent. No question certified here.

analyst/brief.py:extract_brief extracted the18-page Fizzera PDF and CAD1,200,000 investment/CAD250,000 launch ceilings. Notes flag fictional research, forecasts and incomplete final question. Context is not market truth. No real paired brief JSON supplied; test context synthetic.

benchmarking/benchmark.py:freeze_benchmark, verify_assets and load_benchmark implement immutable new releases, exact-byte assets, excerpt/hash checks and path boundaries. Direct require_frozen=True load rejected draft: ValueError: Live experiments require a frozen, verified benchmark. Git-versioned design is not frozen ground truth.

Agent payloads omit reference_facts/expected components; task reference files remain on disk for scoring. Humans must still inspect Articles/brief/supplements for embedded curator answers. Hashes cannot detect semantic leakage.

## Audit 4 — Evaluation metrics

schema.py:IndependentEvaluation validates annotations; evaluation.py:validate_saved_evaluation binds run/task/report/benchmark hashes. save_evaluation persists metric JSON. Runtime review is separate from independent scoring; complete inventories/independence still require a real procedure. Paths below are under benchmarking/ unless otherwise stated.

| Metric / definition | Calculation and required inputs | Completeness, validation, edge cases, storage |
| --- | --- | --- |
| Factual accuracy | rubric.py human0–4 score; metrics.py:incorrect_claim_rate=incorrect/all claims | Rubric/incorrect rate implemented, correct counts stored; explicit correct/all rate absent. Human source adjudication. Zero/incomplete inventory→null rate. JSON counts/rate; CSV rubric/claims but omits incorrect rate. |
| Completeness=correct components/required components | metrics.py:task_completeness; frozen key/human labels | Implemented, exact inventory checked. Zero/incomplete→null. Separate rubric; JSON/CSV. |
| Evidence quality | rubric.py anchored human0–4, weight20 | Implemented subjective criterion, not automatic certification. Missing score invalidates evaluation. JSON/CSV; no rater-agreement calculation. |
| Composite=sum(weight×score/4) | rubric.py:quality_score; weights accuracy30/completeness25/evidence20/support15/clarity10 | Implemented0–100, five integer scores required, no imputation. Recomputable; JSON/CSV. |
| Unsupported rate=unsupported/all factual claims | metrics.py:unsupported_claim_rate; support labels | Implemented separately from truth. Zero/incomplete→null; human paragraph adjudication; JSON/CSV. |
| Precision=matched flags/all flags | error_detection_precision; verified errors/flag mappings | Implemented; zero flags/incomplete error inventory→null. Atomic flags needed; JSON/CSV. |
| Recall=distinct detected errors/all verified errors | error_detection_recall; exhaustive errors/mappings | Implemented; duplicates do not inflate recall; zero/incomplete→null; JSON/CSV. |
| F1=2PR/(P+R) | error_detection_f1; P/R | Implemented; undefined input→null, defined both0→0. JSON stored; CSV omits. |
| Recovery success=cases with all targets resolved/cases | recovery_success_rate; human target/resolved IDs | Implemented; zero cases→null, V1 recovery data rejected. JSON/CSV; target IDs not bound to complete aligned pre/post inventories, needs human verification. |
| Error reduction=(before−after)/before | error_reduction_rate; supplied human counts | Implemented; zero before→null, negative allowed. Counts not automatically aligned/derived; JSON/CSV. |
| New errors=size(after IDs minus before IDs), after semantic alignment | newly_introduced_errors helper | Helper only; annotation_metrics always emits null. No integrated alignment, CSV omits. Not operational. |
| Quality improvement=post−pre | quality_improvement helper | Helper only; missing input→null, no integrated paired join/persisted comparison. Requires independent matched scores. |
| Latency | logging.py:ObservedBackend.generate monotonic stage timing | JSON/CSV; paired duration_seconds sums shared+incremental backend times, unlike CSV dictionary wall-time claim. Preparation wall time/incremental_wall_seconds JSON-only. Not full end-to-end latency. |
| Tokens/calls | normalized_usage, aggregate; returned usage | JSON/CSV; unknown row→null total, known_* partial. Total inferred only from known input/output. Failed calls may consume unreported tokens; successful_requests need not equal physical attempts. |
| Estimated cost=((input−cache)×input rate+cache×cache rate+output×output rate)/1e6 | logging.py:api_cost; exact-model dated rates/usage | Implemented; unknown usage/rates/cache→null. Accounting errors do not alter result. JSON/CSV stage/overall, paired incremental JSON-only. Recomputable, not invoice-verified. |
| Failure rate=failed/scheduled; separate hold/recovery-failure rates | Run statuses; no aggregate rate calculator | Partial: scheduled-pair denominator/interruption/preparation-failure aggregation absent. Zero scheduled denominator should be null; no implemented policy. Raw status JSON/CSV partly available. |

Invalid counts reject input; zero denominators are not perfect performance. Failed/unscored quality is missing, not automatic zero. Do not silently exclude failures.

export.py:export_results uses fixed SCHEMAS and extrasaction=ignore. A temporary synthetic pair exported one run/six stage rows, confirming no pair_id/error_detection_f1 headers. Shared/incremental totals, cost_allocation, recovery_attempts, editorial audit status and newer metrics are omitted. experiment_id currently equals pair_id in paired JSON, permitting reconstruction by convention, but dictionary does not document this. Multi-pair combined analysis is absent. Retain exporter foundations and close integration gaps.

## Audit 5 — Experimental validity

Verified: exact initial query/plan/evidence/Analyst/review reuse with hashes; shared prompts/models execute once. V2 adds revision/re-evaluation instructions to same base roles. Tools disabled, temperature0, seed unsupported. This is conditional comparison from a shared trajectory, not two independently generated workflows.

Both variants use presentation.py:present and identical executive schema/validators/renderer/auditor. Added calls may change quality after recovery and create variation even without correction. Choose Analyst pre/post quality as primary and executive secondary, or explicitly study entire pipeline. Do not compare standalone baseline deterministic output against paired V2 executive output.

V2-only supplementary evidence estimates recovery plus extra access, not collaboration alone. Freeze supplements independently of observed outputs, record hashes/visibility policy. Lexical overlap is not semantic relevance certification.

Independent scoring entry exists, but no randomized/blinded paired-final campaign, calibration or disagreement procedure supplied. Baseline export_blind_packet exports initial Analyst material, not full paired evaluation. Precision/recall must address errors in the report actually reviewed, not downstream executive wording.

JSON preserves pair_id/run_id/repetition/hashes/shared_metrics/incremental_metrics. Shared cost is allocated to both variants for standalone comparison but physically incurred once. Incremental V2−V1 includes editorial variation; isolate correction-stage cost as needed.

runner.py:environment_fingerprint excludes executive/, corpus/ and acquisition code used in paired flow. Standard StageResult lacks model_version, leaving observer field null. Requested aliases recorded; actual provider snapshot identity unverified. Temperature0 does not guarantee deterministic output.

Prespecify task inclusion, repetitions, order/counterbalancing, endpoints, abstention/hold/failure handling and undefined/missing metrics. Repetitions of one task and syndicated articles are not independent task samples. Uncertainty and academic interpretation require human decisions.

## Audit 6 — Reliability and costs

Observed Python3.13.5; installed Pydantic2.10.3/trafilatura2.0.0. CrewAI, OpenAI SDK, MLflow, Playwright and tiktoken absent. requirements-researcher.txt pins Pydantic2.14.1/OpenAI2.54.0/MLflow3.17.1/trafilatura2.0.0; analyst requirements add CrewAI1.6.1; corpus adds Playwright1.64.0/tiktoken0.12.0. Root requirements use looser CrewAI minimum. No lockfile/clean resolution verified. Pin availability/compatibility not checked online. PDF extraction worked; Poppler/PyMuPDF is another reproduction prerequisite.

intelligence/runtime.py:CrewAIBackend.generate sets timeout240s, max_tokens12000, max_retries0, one iteration, no tools/delegation/memory/cache/planning/tracing. corpus/budget.py rejects excessive context rather than truncating evidence but needs tiktoken. Live schema/conversion/retry/billing behavior unverified.

Acquisition handles robots/rate limits/timeouts. discover_v2.py:execute checkpoints/backoffs; resume rejects ambiguous in-flight requests. corpus/access.py replays captures; corpus/research.py:research_corpus reuses completed batches. This is not paired stage resume: preparation requires new directories, variants cannot restart midway, process termination may leave unregistered billable work. Completed pair reuse avoids regenerating shared stages, but failed-variant restarts may repeat paid work.

JSON/baseline CSV use exclusive writes/hashes. Another student needs exact task/brief/supplement/reference archives, environment and prices. Git alone lacks them; .researcher/ and MLflow stores ignored. Historical ignored artifacts are not supplied evidence.

### Actual offline checks

| Command/check | Actual result | Limits |
| --- | --- | --- |
| python -B -X utf8 -m unittest benchmarking.test_phase1 benchmarking.test_paired intelligence.test_workflow crew_ai.test_data | **68 passed**,7.399s | Synthetic references/briefs, mock agents/usage. |
| python -B -X utf8 -m unittest corpus.test_corpus corpus.test_text news_scrapper.test_discover_v2 news_scrapper.test_discover_v2_2 researcher.test_agent analyst.test_workflow analyst.test_revision reviewer.test_reviewer reviewer.test_evidence executive.test_executive | **10 loader errors** | Eight imports blocked by missing MLflow; two discovery imports need their directory on import path. No substantive tests in those modules executed; not ten assertion failures. |
| python -B -X utf8 -m unittest discover -s news_scrapper -p 'test_discover*.py' | **24 passed**,0.201s | Corrected discovery invocation; mocked HTTP/API. Other eight modules remain unverified. |
| Temporary injected-backend paired/export | One run/six stage rows; pair_id/F1 headers absent | No real benchmark/prices. |
| Inventory/frozen gate | Counts above; draft rejected | Not truth certification. |
| Existing local PDF extraction | 18 pages/both ceilings extracted | Not manual certification of every page. |

Total substantive passes:92 across successful commands. Full-suite success is not claimed. No dependency was installed/stubbed to manufacture a pass. Offline success does not establish factual report accuracy.

### Cost estimates without paid calls

benchmarking/pricing.example.json has models={} and effective_date=null. No measured live tokens or numerical pilot budget supplied. A defensible current USD forecast is NOT VERIFIED. Following hypothetical assumptions document scale, not current prices.

Let R be initial Researcher batches. Shared preparation uses R+3 stages; both variants add four presentation/audit stages. Recovery adds zero, two Analyst/review stages, or three including scoped Researcher retrieval. Total R+7 to R+10. For1–5 readable initial articles R=1:8–11 stages/pair. All-unavailable inputs can skip research/block output. Conversion/failed requests may increase billable attempts.

Illustration only:20,000 input/2,000 output tokens per stage; $1/M input/$4/M output gives $0.028/stage. These are NOT current model prices or quotes.

| Scope | Planned stages | Hypothetical USD | 2x contingency, same assumptions |
| --- | --- | --- | --- |
| Three pilot tasks, one pair/task | 24–33 | $0.672–$0.924 | $1.344–$1.848 |
| Twelve tasks, one pair/task | 96–132 | $2.688–$3.696 | $5.376–$7.392 |
| Twelve tasks, three pairs/task (assumed full design) | 288–396 | $8.064–$11.088 | $16.128–$22.176 |

Not authorization ceilings. Replace rates with dated verified stage-specific prices and token-counted frozen-payload estimates. Output cap12000 exceeds assumed average; bodies/brief/history enlarge context. Each extra initial batch adds one shared stage/pair. Actual spend=shared preparation once/pair+both incremental costs; summing allocated full totals double-counts shared generation. Acquisition/SerpAPI, taxes, storage, unreported failed requests and human labor excluded. Reuse lawful local evidence rather than restarting discovery for volume.

## Critical blockers

1. No domain-specific verified frozen benchmark, easy tasks or reference/input packs.
2. Reproducible evidence absent beyond five narrow bodies; extraction quality unverified.
3. Required backend dependencies absent; multiple offline suites blocked.
4. Endpoint/scoring/supplement/failure policies not approved/frozen.
5. Paired runbook, complete analysis/export and dated budget missing. A validated manual JSON procedure could substitute for coding every analysis feature in a tiny pilot, but none is supplied.

## Important nonblocking improvements

After those gates: provider-version logging/full code fingerprints, safe stage resume before scaling, counterbalanced order, failed-request accounting, semantic-event deduplication, extraction/access bias tables and rater agreement. V3 is outside V1/V2 scope.

## Correct implementations to retain

Role prompts/contracts/coordinator; bounded research/paragraph provenance; immutable shared pairing/answer-key isolation; one correction with originals/diff/full re-review; review/audit holds; independent rubric/accuracy-support distinction; null-denominator/unknown-usage policy; exclusive artifacts/baseline exporter; access safeguards/replay/acquisition and corpus caches. No architecture rebuild indicated.

## Prioritized action plan

| Priority | Action | Responsibility | Effort |
| --- | --- | --- | --- |
| P0 | Approve Fizzera scope/difficulty/hypotheses, report endpoint, abstention/failure rules | Human academic judgment; Codex drafts for review | Medium |
| P0 | Restore/curate lawful bodies, verify dates/completeness, select challenges, verify keys/attestations | Human factual verification; Codex inventory/hash/package support | High |
| P0 | Isolated dependency setup, validate pins, rerun blocked suites | Codex implementation, install permission as required | Medium |
| P0 | Paired runbook/CLI, shared/incremental export, aligned new-error/failure analysis, stale docs | Codex within approved design | Medium |
| P0 | Scoring/prices/cash-cap approval, frozen packs/brief/supplement/config, offline rehearsal | Human evaluation/budget judgment; Codex packaging/rehearsal | Medium |
| P1 | Permitted reproducibility archive/sharing-retention policy | Human sharing decisions; Codex manifests | Medium |
| P1 | Safe resume and broader fingerprints before scaling | Codex | Medium |
| P1 | Bias/duplicate events/rater disagreement/uncertainty | Human interpretation; Codex analysis support | Medium–High |

Effort labels are relative sizes, not timing promises. No fixes performed in this audit.

## Proposed three-task pilot

These are designs, NOT verified questions/reference answers. Assign new Fizzera IDs/release assets. One shared trajectory and both variants/task gives three pairs/six final outputs. Independently score initial/selected post-review Analyst artifacts; executive output is secondary unless explicitly preregistered otherwise.

| Task | Frozen objective/condition | Intended observation |
| --- | --- | --- |
| F-P01, easy | One verified functional-soda competitor announcement: product/date/launch market/availability and constrained Fizzera implication;1–2 readable sources/relevant brief pages | Traceability, baseline/presentation; no correction if review passes. |
| F-P02, medium | Two competitor soda price/pack snapshots matched by currency/volume/pack/retailer/geography/date; withhold one necessary snapshot initially, freeze it in V2 supplement | Scoped missing evidence, abstention, incremental evidence cost. |
| F-P03, hard | Two genuinely differing soda market/competitor figures both supplied initially; preserve scope/date/units, allow supported unresolved conflict; constrained Fizzera implication | Analyst-only correction if warranted, full re-review/new errors/persistent hold where needed. |

Do not alter reports/verdicts after observing outcomes to force correction. A correct report can trigger no recovery, a valid outcome. Synthetic fixtures already exercise guaranteed branches. An injected-error study would require a separately declared condition.

Exit gates: human-verified frozen packs/brief; working dependencies; no answer leakage; shared hashes match; at most one correction; valid holds; complete pair/cost/failure artifacts; independent inventories on corresponding stages; explicit undefined/missing treatment; verified cash cap. Three tasks establish feasibility, not architecture superiority; review variability before choosing full repetitions.

**NO-GO now for paid execution. GO for offline curation, environment validation and synthetic rehearsal.** Reassess P0 against concrete pilot assets/budget. Live calls remain subject to explicit authorization.

## Five highest-priority next actions

1. **You — academic judgment:** approve Fizzera objectives/difficulty, primary report stage and missing/conflicting-evidence/failure policy.
2. **You — verification; Codex — preparation:** restore/curate lawful bodies, inspect completeness/dates, verify keys and sign off frozen conditions.
3. **Codex — implementation:** establish reproducible dependencies and rerun blocked suites without paid calls.
4. **Codex — implementation:** complete paired operation/export, aligned recovery/failure metrics and incremental accounting; correct stale docs while retaining architecture.
5. **You — scoring/budget approval; Codex — packaging:** approve independent evaluation/dated prices, freeze three pilot packs/configuration, review offline rehearsal before authorizing capped live pilot.
