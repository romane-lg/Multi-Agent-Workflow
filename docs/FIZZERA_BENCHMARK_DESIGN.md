# Fizzera benchmark design and validation

Design date: 2026-11-09 (America/Toronto). Status: **DRAFT / NOT READY FOR LIVE EXPERIMENTS**.

## Deliverables and compatibility

New study draft: [fizzera_ci_draft_v1.json](../benchmarks/fizzera_ci_draft_v1.json), version `fizzera-ci-draft-v1`. The original [ci_draft_v1.json](../benchmarks/ci_draft_v1.json) remains byte-for-byte unchanged as the generic archive; existing tests and baseline examples still reference it. Nothing automatically switches execution to the new file. Select the new file explicitly for inspection and use a later verified release/configuration for experiments.

The existing `ci-benchmark-v1` schema is unchanged: question carries the operational objective, companies the competitor scope, expected_components the observable scoring requirements, allowed_source_types the evidence requirements, and known_challenges the objective/context/curation/scoring notes. No unsupported fields were added. Category A=bounded retrieval (F01-F03), B=comparisons (F04-F06), C=business interpretation (F07-F09), D=evidence challenges (F10-F12), preserving three tasks/category. Difficulty is independently assigned: 3 easy, 5 medium, 4 hard.

All 12 tasks have verification_status=draft, empty reference_sources/reference_facts/component reference_fact_ids, null verification/input_snapshot/input_sha256, and the benchmark has status=draft and sha256=null. These are designs, not verified answers. No benchmark was frozen and no real source was fetched or sent to a model.

## Inspected infrastructure

Inspected benchmarks/ci_draft_v1.json; benchmarking/benchmark.py, schema.py, experimental_schema.py, rubric.py, metrics.py, paired.py, test_phase1.py and test_paired.py; and all 18 pages of the local Fizzera PDF using analyst/brief.py:extract_brief. The existing loader requires verified assets and a frozen checksum for execution. Freezing requires every component to link verified reference facts, exact excerpts in local snapshots, Article input hashes and human attestation. None of those factual prerequisites is asserted here.

The schema accepts F01-F12 identifiers directly. No architecture, prompt, evaluation logic, schema, existing tests or generic benchmark was modified. Reversible draft-data changes are checked directly against the loader; a new test module is unnecessary.

## Temporal scope and factual boundaries

Evidence event window is 2024-10-10 through 2026-10-09, matching the documented full discovery window. Company context is dated 2026-10-16; task as_of_date is 2026-10-16. This deliberately separates the evidence cutoff from brief date and current design date. Product snapshots in F02/F06 must be dated on or before the cutoff and have their actual age recorded. F04/F10 require a curator-selected common Ontario price capture date within 2026-10-03 through 2026-10-09; none is claimed to exist. A later retrieval of a current webpage is not a historical capture. If lawful historical snapshots cannot be verified, revise the dates in a new draft version before freezing; never backdate retrieval.

Comparisons are bounded to supplied frozen evidence, not an exhaustive market census. A source-backed statement means the source actually makes that statement; it does not automatically certify independent truth or commercial success. Geographic gaps, unknown currency, temporary promotions and unsupported causal effects must remain explicit.

## Fizzera brief constraints verified locally

Source: [Fizzera Sodas.pdf](../Fizzera%20Sodas.pdf), dated October 16, 2026, 18 pages. SHA-256: `0360a4768d7268bed7ef00092d381556e1d6a13ffcc7eb157723cf62b42643c0`. Page references below are physical PDF page numbers, matching `BRIEF pN` context keys in paired execution.

| Pages | Planning context / constraint | Use in tasks |
| --- | --- | --- |
| 2-3 | Taste-first, accessible premium and social positioning; no unsupported medical claims; current 355 mL caffeine-free products | F01/F02/F06/F09 |
| 3-5 | Four flavors; suggested single-can CAD 2.99 and multipack architecture; fictional survey explicitly not national market estimates; three unapproved concepts | F02/F04/F06/F09/F10 |
| 6-7 | Fictional internal discovery/repeat research; 2026 performance forecasts differ from 2025 actuals | F05/F07/F12; never use these as competitor truth or causal campaign results |
| 8-9 | 285 Ontario stores, Ontario-first; 14 cans/store/week baseline; targets 450 stores and 19 cans/store/week; no national grocery agreement | F03/F07/F08 |
| 10-11 | CAD 2.99 suggested-price position; sustained >=10% comparable Canadian reduction triggers review; below-CAD-2.40 comparable multipack per-can signal; a temporary promotion is insufficient | F04/F10 |
| 5, 11-12 | One 2027 major launch; choose Vanilla Cola, Tropical Mango, Ginger Lime or postpone; CAD 250000 launch preparation ceiling; existing 355 mL equipment; caffeine-free; preferred <=5g sugar; new claims require review | F01/F06/F09 |
| 11-12 | Concept selection Jan 31, testing Mar 31, launch by August 2027 are objectives | F09; not completed milestones |
| 12-13 | Local campaigns/smaller creators; preference for 20 small creators over one expensive celebrity; trial/repeat more important than impressions | F05/F12 |
| 13 | BC: 40 test locations, evaluate 125; positive contribution after regional logistics; Ontario-first | F08; 125 is not an approved expansion or achieved count |
| 14-15 | CAD 1.2m discretionary envelope over next 12 months; allocations provisional, including CAD 250000 marketing/CAD 150000 BC; around 4m cans contracted capacity vs 3.1m expected 2026 sales; products compete for slots | F07/F08/F09/F12; do not infer free usable capacity or approved feasibility |
| 15-16 | PDF names Olipop, Poppi, Cove Soda and Crazy D's as direct competitors | This benchmark follows the user's specified four-brand scope: Olipop, Poppi, Culture Pop and Zevia; no claim PDF lists all four as direct competitors |
| 18 | Final question is incomplete | Do not supply missing wording |

This fictional planning brief is supplied company context, not independent external market evidence. Forecasts, proposed budgets, targets and survey findings retain those labels. Budget allocations may be reallocated within the envelope; an additional-financing scenario must be labelled. No scientific or regulatory clearance is asserted.

## Task specifications

Each task below states the exact JSON question, objective, required components, source types, context and evidence gaps. Component IDs are stable within this draft. The bullets are requirements, not reference answers. Required abstention can earn completeness credit after human verification of evidence scope; a missing source is not automatically a model error.

### F01 — easy — Retrieve dated competitor product launches and separate announcements from availability.

Competitors: Olipop, Poppi. Category: A.

**Question:** Using only the supplied frozen sources published from 2024-10-10 through 2026-10-09, identify one distinct soda product launch or relaunch reported for Olipop and one for Poppi. For each, give product/flavor, publication and announcement or launch date, stated market and retailer/channel, and whether availability is announced or demonstrated. Cite exact passages. State any missing brand coverage rather than substituting an unrelated brand, and give one brief, conditional relevance statement for Fizzera's 2027 product decision using the supplied brief.

**Required answer components / scoring checks:**

- **F01_C1:** Identify one supported launch/relaunch per named brand, or explicitly report the missing brand evidence; do not treat syndicated coverage as a distinct launch.
- **F01_C2:** Record product/flavor, publication date, stated event date, market, channel and announcement-versus-availability status with exact source citations.
- **F01_C3:** Explain one conditional Fizzera relevance statement grounded in cited brief pages; do not infer demand, sales success or a preferred launch from announcement alone.

**Suggested source types:** dated official launch announcement; dated beverage-trade article with readable launch passages.

**Applicable brief context:** pp. 2-5, 11-12: taste-first accessible positioning, current portfolio and one 2027 launch; no concept approved.

**Missing evidence / verification:** Existing five-body pilot contains Olipop launch reporting, not a Poppi body. Curate a qualifying Poppi source; verify product, dates, market and attribution before creating a key.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F02 — easy — Retrieve a bounded four-brand product/positioning comparison without treating functional claims as proven efficacy.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: A.

**Question:** For one curator-selected soda SKU per brand from Olipop, Poppi, Culture Pop and Zevia, use the frozen product labels and positioning passages dated on or before 2026-10-09 to tabulate serving volume, sugar, sweeteners, functional ingredients and the brand's stated benefits/positioning. Preserve each SKU's market and snapshot date, mark undisclosed fields, and distinguish advertised benefits from demonstrated health effects. Briefly identify a positioning consideration for Fizzera's taste-first, non-medical promise; do not assume all four brands contain prebiotics.

**Required answer components / scoring checks:**

- **F02_C1:** Name exactly the four supplied SKUs with market, snapshot date and serving basis, or list explicit missing SKU evidence.
- **F02_C2:** Extract sugar, sweeteners, functional ingredients and stated benefits/positioning with label or source citations; preserve undisclosed fields.
- **F02_C3:** Attribute marketing claims rather than endorsing efficacy or inferring common ingredients across brands; identify a bounded Fizzera positioning consideration from the brief.

**Suggested source types:** dated official product label or nutrition/ingredient panel; dated official brand positioning page.

**Applicable brief context:** pp. 2-4: taste-first positioning, no unsupported medical claims, 355 mL caffeine-free portfolio and ingredient transparency.

**Missing evidence / verification:** Curate one SKU/market per brand; verify labels separately from promotional benefits. Difficulty is easy only for bounded extraction; comparison complexity needs empirical calibration.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F03 — easy — Retrieve distribution announcements while preserving geography and implementation status.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: A.

**Question:** From the supplied frozen sources published from 2024-10-10 through 2026-10-09, identify at most one distinct retail distribution announcement per brand for Olipop, Poppi, Culture Pop and Zevia. Record brand, retailer/distributor, announcement date, stated country/province, store count if disclosed, and planned versus implemented status. Give an explicit gap for any uncovered brand and flag which announcements actually mention Ontario. Explain briefly why national or US distribution cannot establish Ontario availability for Fizzera's retail monitoring.

**Required answer components / scoring checks:**

- **F03_C1:** List no more than one supported distinct announcement per brand with exact citation, or record a brand-specific gap.
- **F03_C2:** Preserve partner, dates, geography, disclosed store count and planned/implemented status without filling missing numbers.
- **F03_C3:** Identify explicit Ontario coverage and distinguish US, Canadian national and province-specific evidence; link relevance to the brief without inferring local sales.

**Suggested source types:** dated official retailer or distributor announcement; dated competitor distribution announcement; dated independent retail or beverage-trade reporting.

**Applicable brief context:** pp. 8-9: Ontario is the core priority; no national grocery agreement; provincial retail evidence is needed.

**Missing evidence / verification:** No distribution Article pack is supplied. Verify retailer/brand scope and province rather than relying on discovery titles; no minimum of four announcements is assumed.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F04 — medium — Produce a reproducible Ontario price comparison and apply Fizzera thresholds only when justified.

Competitors: Olipop, Poppi. Category: B.

**Question:** Compare one Olipop soda SKU and one Poppi soda SKU at the same Ontario retailer, using a curator-verified common price snapshot date within 2026-10-03 through 2026-10-09. Record CAD price, can volume, pack size, regular/promotional status, tax/deposit/shipping treatment and date. Compute per-can and per-355-mL prices only from compatible documented inputs. Compare cautiously with Fizzera's CAD 2.99 suggested 355 mL single-can price and assess its below-CAD-2.40 comparable-multipack review threshold. Do not infer a sustained 10% reduction from a single snapshot; report missing comparability instead.

**Required answer components / scoring checks:**

- **F04_C1:** Record both SKU/retailer/province/date/currency/pack/volume/price entries and treatment of promotions, tax, deposit and shipping, citing exact snapshots.
- **F04_C2:** Show per-can and per-355-mL arithmetic with units and denominators; refuse a numeric ranking where inputs are incompatible or missing.
- **F04_C3:** Apply only supported brief thresholds; distinguish Fizzera suggested price from observed competitor price and a single promotion from a sustained reduction.
- **F04_C4:** State missing evidence and bounded pricing implications without inventing currency conversions, sales response or margin effects.

**Suggested source types:** dated Ontario retailer price capture; dated SKU pack-size and volume documentation.

**Applicable brief context:** pp. 4, 10-11: suggested versus observed prices, CAD 2.99 single can, below-CAD-2.40 comparable multipack signal; sustained >=10% reductions require a time series.

**Missing evidence / verification:** No comparable Ontario price snapshots are supplied. Human curator must select a common capture date in the fixed window; if none exists, revise dates in a new draft rather than backdating a capture.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F05 — medium — Compare documented campaign tactics without confusing engagement with causal commercial performance.

Competitors: Olipop, Poppi. Category: B.

**Question:** Compare one documented Olipop campaign and one documented Poppi campaign announced from 2024-10-10 through 2026-10-09 using a dated campaign source and an independent reporting source per campaign where available. Identify target audience, message, creator/partner, channel and activation. Separate reported reach/engagement from measured trial, repeat purchase or incremental sales; mark absent outcomes. Propose one conditional adaptation for Fizzera's local Ontario marketing, respecting its preference for smaller creators and measurable purchasing rather than celebrity-scale spend.

**Required answer components / scoring checks:**

- **F05_C1:** Describe each selected campaign's date, market, audience, message, partner/channel and activation with source citations and source-type distinctions.
- **F05_C2:** Separate documented tactics and attributed engagement from conversion, incremental sales and causal ROI; disclose absent outcome data and non-independent coverage.
- **F05_C3:** Compare tactics and propose one bounded Fizzera adaptation tied to brief pages, with a measurement plan and stated transferability limits.

**Suggested source types:** dated official campaign or partnership materials; independent dated marketing-trade reporting.

**Applicable brief context:** pp. 5-7, 12-14: target/customer context is fictional planning input; local campaigns, smaller creators, trial/repeat measurement and provisional marketing allocation.

**Missing evidence / verification:** Olipop campaign passages exist in the five-body pilot but lack a complete matched campaign pack. Poppi campaign text and independent corroboration need curation; do not assume campaign success.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F06 — medium — Compare bounded market-specific portfolios and formats without inferring completeness or demand.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: B.

**Question:** Using the supplied frozen Canadian-market portfolio lists and SKU/packaging records dated on or before 2026-10-09, compare Olipop, Poppi, Culture Pop and Zevia on listed flavors, permanent versus seasonal status, can volumes, pack formats and documented differentiation. Label US-only or market-uncertain records separately and do not treat the supplied lists as a complete global catalogue. Identify evidence-based overlaps or gaps relative to Fizzera's four-flavor 355 mL portfolio; do not infer consumer preference from flavor counts.

**Required answer components / scoring checks:**

- **F06_C1:** List supplied flavor and format evidence per brand with dates, market, permanent/seasonal status and explicit missing fields.
- **F06_C2:** Compare documented differentiation and portfolio overlap on a consistent market/serving basis without claiming an exhaustive global catalogue.
- **F06_C3:** Relate supported similarities/gaps to Fizzera's actual portfolio and format, separating factual differentiation from untested demand assumptions.

**Suggested source types:** dated official market-specific portfolio or product catalogue; dated packaging/label captures; dated retailer SKU listings.

**Applicable brief context:** pp. 2-5, 11-12: four-flavor portfolio, taste/accessibility positioning, existing 355 mL format; proposed concepts are not approved.

**Missing evidence / verification:** Existing roundups cover only selected launches, not four Canadian portfolios. Curate finite product lists with their scope and capture dates; missing Canada evidence remains a gap.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F07 — medium — Assess competitor developments against an Ontario-specific retail decision.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: C.

**Question:** From frozen sources published from 2024-10-10 through 2026-10-09, select up to three distinct developments involving Olipop, Poppi, Culture Pop or Zevia that have explicit relevance to Ontario retail distribution, shelf assortment or pricing. Separate direct Ontario evidence from Canadian national or US context. Assess whether the evidence supports a conditional priority for Fizzera: new Ontario doors, productivity in existing stores, or a bounded promotional test. If Ontario-specific evidence is absent, state that the choice cannot be established rather than inventing local results.

**Required answer components / scoring checks:**

- **F07_C1:** Select up to three distinct cited developments with dates, named competitor, retailer/market and explicit Ontario connection, or acknowledge absent provincial evidence.
- **F07_C2:** Distinguish door count, assortment, velocity and promotions; do not infer provincial sales or shelf share from national listings.
- **F07_C3:** Present a conditional choice or justified deferral tied to Ontario objectives and brief constraints, specifying missing economics or local performance inputs.

**Suggested source types:** dated Ontario retailer or distributor announcements; dated Ontario product/price/assortment snapshots; independent Canadian retail-trade reporting.

**Applicable brief context:** pp. 8-10, 14-15: Ontario-first; 285 Ontario stores and 14 cans/store/week are brief baselines; 450/19 are targets, not achieved outcomes; margin/capacity/budget constraints.

**Missing evidence / verification:** No Ontario-specific body pack is available. US retailer mentions in existing roundups cannot establish provincial coverage; verify baselines versus targets in the brief.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F08 — medium — Assess BC expansion evidence without substituting national listings for local economics.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: C.

**Question:** Using frozen evidence published from 2024-10-10 through 2026-10-09, assess documented Olipop, Poppi, Culture Pop and Zevia distribution or retailer assortment in British Columbia. Name up to two potential regional retail partners only where the evidence establishes BC operations and relevant assortment; label prospect fit as a hypothesis. Compare conditional expansion, maintaining the test footprint, and deferral for Fizzera. State what is unknown about regional demand, logistics and contribution margin; do not invent sales, shipping costs or an expansion return.

**Required answer components / scoring checks:**

- **F08_C1:** Extract BC-specific competitor/retailer evidence with market, dates and citations, distinguishing current listings from announcements and national context.
- **F08_C2:** Identify up to two evidence-supported BC partner prospects or an explicit shortfall; separate retailer presence from willingness to list Fizzera.
- **F08_C3:** Assess expansion/hold/defer conditionally against the brief and enumerate missing regional demand, costs, capacity and contribution inputs; no invented return.

**Suggested source types:** dated BC retailer assortment or store-location records; dated BC distribution announcements; independent Western Canadian retail reporting.

**Applicable brief context:** pp. 8-9, 13-15: 40 BC test locations, evaluate 125 (not approved), Ontario-first, positive contribution after logistics and provisional BC allocation; finite manufacturing capacity.

**Missing evidence / verification:** No BC body pack or logistics economics supplied. Curate actual provincial evidence; fewer than two supported prospects is a reportable shortfall, not permission to invent partners.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F09 — hard — Make a constrained product decision while preserving uncertainty and separating trends from demand.

Competitors: Olipop, Poppi, Culture Pop, Zevia. Category: C.

**Question:** Using verified-source competitor activity from 2024-10-10 through 2026-10-09 and the supplied Fizzera brief, recommend conditionally one of Vanilla Cola, Tropical Mango, Ginger Lime or postponement for 2027. Compare all four options, separating documented competitor launches/positioning from evidence of consumer demand. Respect one major launch, the CAD 250000 development/launch-preparation ceiling, existing 355 mL equipment compatibility, caffeine-free requirement, preferred <=5 g sugar and review of new functional claims. Preserve the brief's decision/testing/launch deadlines and total investment constraint. Identify tests and decision gates; do not fabricate forecasts, demand or returns.

**Required answer components / scoring checks:**

- **F09_C1:** Compare Vanilla Cola, Tropical Mango, Ginger Lime and postponement against cited competitor activity and brief context; distinguish announcements from demand evidence.
- **F09_C2:** Give one conditional selection or justified postponement, acknowledge contrary/absent evidence and explain why alternatives are not selected without inventing forecasts.
- **F09_C3:** Check one-launch, CAD 250000, 355 mL, co-manufacturing, caffeine-free, preferred sugar and claim-review constraints; flag unverified feasibility rather than asserting approval.
- **F09_C4:** Preserve January 31 concept choice, March 31 testing and August 2027 launch objectives; propose measurable gates and respect total envelope/provisional allocations without invented ROI.

**Suggested source types:** dated competitor launch and positioning evidence; independently documented consumer-demand evidence if available; supplied Fizzera Sodas.pdf planning context.

**Applicable brief context:** pp. 2-5, 11-12, 14-15: one concept, budget/format/manufacturing/claims/sugar constraints, milestones and total CAD 1.2 million envelope.

**Missing evidence / verification:** All options require independent reference criteria, not a single predetermined winning flavor. Competitor announcements do not establish Canadian demand or manufacturing feasibility; scientific/regulatory reviews are future gates, not completed checks.

**Scenario:** Ordinary retrieval/comparison/interpretation. A natural material error may trigger normal V2 correction, but none is injected.

### F10 — hard — Test honest abstention on unavailable/outdated prices and optional scoped recovery.

Competitors: Olipop, Poppi. Category: D.

**Question:** Assess an Ontario price comparison for one Olipop and one Poppi SKU using the frozen common-date condition within 2026-10-03 through 2026-10-09. The initial pack deliberately marks one required matching source unavailable and may include a clearly dated older price as a distractor. Report only readable, date/geography/currency/pack-compatible prices, identify the unsupported comparison and request the exact missing evidence. Do not infer price from a title, silently substitute the older price or assume a supplemental source exists. Explain the limited implication for Fizzera's price review; a correct abstention is acceptable.

**Required answer components / scoring checks:**

- **F10_C1:** Inventory readable, unavailable and any stale pricing records with source/date/market/pack labels; distinguish controlled unavailability from a real website outage.
- **F10_C2:** Calculate only supported comparable figures and explicitly withhold the missing current price/ranking; no title-based or stale substitution.
- **F10_C3:** Specify the exact source/date/retailer/SKU information needed and the conditional Fizzera implication; correct abstention satisfies the requirement.
- **F10_C4:** Record whether matching additional evidence was actually supplied. If supplied in a permitted correction, update only the supported comparison with new citations; otherwise preserve the justified abstention and unresolved gap. Recovery is not required for this component to be correct.

**Suggested source types:** dated matching Ontario retailer price snapshots; dated pack-volume records; explicit frozen unavailable Article record.

**Applicable brief context:** pp. 4, 10-11: CAD price architecture/review thresholds; no automatic response to a temporary promotion.

**Missing evidence / verification:** Curate and hash initial unavailable record and optional old-price distractor. Predefine a verified matching supplement before runs only if obtainable; otherwise preserve missing-evidence status. Do not choose it after seeing model outputs or force recovery.

**Scenario:** Controlled missing/stale/unavailable evidence with an optional predefined verified supplement; not a guaranteed recovery trigger.

### F11 — hard — Test reconciliation of genuine differences in reported competitor figures.

Competitors: Poppi. Category: D.

**Question:** Examine two genuinely differing, curator-verified source statements about Poppi retail distribution, both published from 2024-10-10 through 2026-10-09. Report each figure with exact citation, publication/event date, market, unit and definition, including whether counts describe stores, chains or potential availability. Determine whether scope, dates or definitions explain the difference; reconcile only when supported and otherwise retain the unresolved discrepancy. Explain the bounded implication for Fizzera's Ontario monitoring without treating US or national figures as Ontario store counts.

**Required answer components / scoring checks:**

- **F11_C1:** Reproduce both genuinely differing source statements with exact citations, figures, units/definitions, dates and geography, preserving attribution.
- **F11_C2:** Check whether period, market, count definition or planned/implemented status explains the difference; do not average, cherry-pick or invent a reconciliation.
- **F11_C3:** State a supported reconciliation or explicit unresolved discrepancy, and a bounded Ontario/Fizzera implication with needed follow-up evidence.

**Suggested source types:** dated official Poppi or retail-partner distribution statements; dated independent retail/beverage reporting with attributable figures.

**Applicable brief context:** pp. 8-9, 16: Ontario retail relevance; competitor national scale is not provincial coverage or local sales.

**Missing evidence / verification:** No differing pair is selected or verified. Both statements must be present initially and genuinely differ in the source, not be edited into contradiction. If no qualifying pair exists, revise this task before freezing; differences need not be factual errors.

**Scenario:** Genuinely differing source statements both initially available; analyst reconciliation or justified unresolved conflict; no fabricated contradiction.

### F12 — hard — Test refusal to invent marketing ROI/conversion and propose a bounded measurement decision.

Competitors: Olipop, Poppi. Category: D.

**Question:** Assess whether the supplied dated Olipop and Poppi campaign evidence supports investing Fizzera's provisional CAD 250000 incremental-marketing allocation. Separate documented campaign activities/reach/engagement from measured incremental trial, repeat purchasing, conversion and financial returns. Calculate an outcome or ROI only if the matching numerator, denominator, attribution/comparison basis and costs are explicitly supported; otherwise state it cannot be established. Recommend a conditional local test, deferral or staged spend with measurement gates, not a guaranteed return, respecting Fizzera's smaller-creator preference, Ontario priority and total envelope.

**Required answer components / scoring checks:**

- **F12_C1:** Separate cited competitor activities and any measured outcomes from unsupported ROI/conversion/return claims, recording dates, scope, denominators and attribution limits.
- **F12_C2:** Provide no numeric ROI, conversion rate or investment return without compatible outcome/cost/attribution inputs; explain exactly what is missing and avoid turning impressions/followers/internal fictional research into conversion evidence.
- **F12_C3:** Propose a conditional local test/deferral/staged investment, with baseline/comparison, incremental trial/repeat and cost measurement plus explicit go/no-go gates.
- **F12_C4:** Treat CAD 250000 as provisional rather than compulsory spend, respect total envelope and smaller-creator/Ontario priorities; label all proposed thresholds as proposals, not observed results.

**Suggested source types:** dated official competitor campaign disclosures; independent marketing reporting including measurement limitations; supplied Fizzera Sodas.pdf planning context.

**Applicable brief context:** pp. 6-7, 12-14: fictional customer survey/repeat measures are planning context, not campaign conversions; smaller creators, measurable trial/repeat, provisional CAD 250000 marketing/CAD 1.2 million total.

**Missing evidence / verification:** Public campaign data may lack cost or incremental sales. Curators must verify the actual disclosure/search scope rather than assert universal nondisclosure. No positive ROI or numerical conversion key is invented.

**Scenario:** Unsupported-return/causal-attribution challenge; appropriate refusal and measurement design are valid outcomes.

## Scoring and difficulty

Use existing independent-human-v1 rubric: factual accuracy 30%, completeness 25%, evidence quality 20%, claim support 15%, clarity/usefulness 10%. Each criterion receives anchored integer 0-4; weighted score = sum(weight*score/4), range 0-100. Score the report against verified sources/components, not the runtime Reviewer verdict. Enumerate claims, support/accuracy separately, omissions, verified errors and Reviewer flags for existing metrics. Undefined denominators/incomplete inventories remain null under existing logic.

F01-F03 are easy only as bounded, curated retrieval/label extraction; they make no exhaustive census or business-performance requirement. F02's four-brand breadth may prove harder empirically. F04-F08 require comparison or constrained interpretation. F09-F12 require uncertainty/synthesis/abstention. These labels need empirical calibration; no task has been demonstrated easy or hard by this design exercise.

F09 has no uniquely correct winning flavor. Its key must specify acceptable evidence-based options, supported reasons, counterevidence, constraints and testing gates. F10_C4 is satisfied by an explicit no-additional-evidence/no-correction outcome preserving justified abstention; it must not require V2 to recover for a perfect score. F11 may correctly conclude differing scopes or unresolved discrepancy. F12 may correctly report no support for numeric returns; missing public disclosure is scoped to inspected sources, not a claim that nobody knows the number. Do not reward fabricated completeness or force a numerical investment recommendation.

## Evidence readiness and questions needing curation

All 12 tasks need human curation. The available five-body BevNET pilot provides candidate Olipop launch/campaign/flavor passages and one Culture Pop passage; it supplies no Poppi or Zevia bodies and no balanced Canadian/provincial price/distribution pack. The historical 146-body corpus is still unavailable locally based on the prior recovery investigation. No evidence has been restored or re-extracted in this task.

| Tasks | Required before verification / potential revision |
| --- | --- |
| F01 | Verify one dated Olipop and one Poppi launch; source-backed gaps allowed, but easy pilot should have both brands represented |
| F02/F06 | Verify bounded market-specific SKU labels/portfolio scope for all four; do not assume Zevia has prebiotic ingredients |
| F03 | Verify retailer/geography/status; uncovered brands remain explicit gaps |
| F04/F10 | Actual comparable Ontario historical snapshots/pack units needed; revise date window if unavailable rather than use fabricated historical captures |
| F05 | Matched dated campaign evidence plus source-independence/measurement checks; no engagement-to-sales inference |
| F07/F08 | Ontario/BC evidence required; US or national listings do not establish local presence/performance; prospective partners need real BC operations |
| F09 | Evidence-backed option/constraint matrix, demand and feasibility gaps; revise scope if too broad for reliable scoring |
| F11 | Two actual differing Poppi distribution statements not yet identified; revise metric/brand/date window in a new draft if no qualifying pair is available |
| F12 | Verify what outcomes/costs/attribution are and are not disclosed; approve scope and acceptable abstention/measurement key |

These are feasibility risks, not permission to mark tasks verified with incomplete or invented keys. No reference fact/source URL was populated from memory or search metadata.

## Proposed pilot: F01, F10, F11

1. **F01:** One launch per Olipop/Poppi from a small verified source pack. Tests basic chronology, citations, market scope and conditional brief relevance.
2. **F10:** Freeze a comparable price condition before observing outputs. Include readable initial evidence and a separate unavailable Article record for a needed source; optionally include a clearly labelled old price. If a matching supplemental source can be independently verified, freeze its exact body/hash before any runs and bind it in PairedConfig.supplemental_evidence under F10. Use a distinct stable supplemental article_id and document the mapping to the initial unavailable record: current recovery excludes IDs already in initial evidence, even if unavailable. Preserve original record/URL/provenance, avoid changing original source content, and mark the supplement as a linked new capture rather than independent corroboration. If no lawful matching supplement is obtainable, keep the abstention-only condition and do not claim retrieval-recovery success.
3. **F11:** Put both genuine differing statements in the initial evidence, with independently verified exact excerpts, definitions and dates. Do not alter figures or introduce artificial errors. A correct reconciliation or justified unresolved conflict may pass without correction.

Use prepare_pair once per task/repetition, then run_variant for sequential_v1 and targeted_recovery_v2 using identical shared inputs/report/review. V1 never corrects; V2 corrects only eligible failed reviews and at most once. Correct abstention/no-recovery is valid. Do not modify artifacts/verdicts or force an error to fill a recovery denominator. Freeze supplementary selection independently of observed mistakes; report that V2-only added evidence is part of the intervention.

Predeclare initial/post-review Analyst quality as primary or choose another endpoint explicitly; executive/audit stages add model calls and should be scored separately if secondary. Detection metrics must match the report actually reviewed. Preserve pairing, failures/holds, missing usage and separate shared from recovery/presentation costs. Known export/analysis issues in PRE_EXPERIMENT_READINESS_AUDIT.md remain outside this draft-only change.

## Manual checklist before any freeze or pilot

- Approve task wording, historical dates/market/SKU/event selection, difficulty hypotheses and scoring scope; resolve the feasibility risks above. Future changes get a new draft/release identity.
- Restore lawful historical corpus artifacts or separately authorize targeted acquisition. Validate readable text rather than counting URLs; check dates, completeness, boilerplate, source attribution, duplication and source independence.
- Prepare exact per-task Article arrays with stable IDs/paragraph IDs, original URLs, actual retrieval timestamp/method, publication dates, availability and text hashes. Include honest unavailable records where designed.
- Save exact legitimate UTF-8 reference snapshots. Record reference_sources URL/retrieved_at/path/hash and reference_facts with exact supporting excerpts. Reference facts may verify scope/absence/constraints, not just numerical facts. Link every component to appropriate verified reference facts.
- For F09/F12, create human-approved acceptable-answer/abstention criteria rather than inventing one winning strategy or return. For F11 verify both statements and adjudicate their relationship; neither statement automatically becomes true ground truth.
- Extract/hash the exact real brief snapshot for PairedConfig; check page numbering/ceilings and fictional/forecast/provisional labels manually. Context in this Markdown is design documentation; paired execution must still supply the real brief.
- Freeze F10 condition and optional supplement/mapping before runs. Keep reference keys, expected components, known_challenges and this design document out of agent inputs; only task question/scope, brief and intended Articles enter runtime. Inspect all input text for accidental curator-answer leakage.
- Assign independent evaluators, calibration/disagreement procedure, completeness/claim/error inventories and report-stage binding. Approve denominators, failures, no-recovery cases, supplemental-access interpretation and a pilot cash cap.
- Resolve dependency/environment and paired-run/analysis readiness separately; verify dated prices/model configuration without making paid calls during preparation.
- Only after human verification populate task verification_status/verification identity/time/notes and input_snapshot/hash. With approval, freeze a NEW release using the existing mechanism; never overwrite this design or the generic archive. Re-run asset/hash checks and explicitly configure that release. Live experiments need separate approval.

## Validation record

Validation results are appended below after the actual offline checks. Loading a draft proves schema compatibility only; it does not verify evidence, answer correctness, difficulty or readiness for paid execution.

### Actual results — 2026-11-09

- Existing loader accepted all **12 tasks and 40 required components** in the new draft.
- Direct checks confirmed IDs F01-F12, three tasks per category, difficulty split **3 easy / 5 medium / 4 hard**, requested ID-to-difficulty mapping, allowed four-brand scope, unique/schema-valid components and Fizzera-specific questions.
- Every task remains unverified draft, with empty reference/source/fact links and null input/verification fields. Benchmark checksum remains null. Requiring a frozen release rejected the new file with `ValueError: Live experiments require a frozen, verified benchmark`.
- Every question and required component in this document matched the saved JSON exactly.
- Command: `python -B -X utf8 -m unittest benchmarking.test_phase1 benchmarking.test_paired` — **43 tests passed in 6.090 seconds**. These use synthetic fixtures and mock agents; synthetic freeze tests do not freeze the new real draft. No paid/provider calls occurred.
- Original generic file unchanged: SHA-256 `a9fce7c303f6f32a25b05a34d0ed5af47c1c26f76c0b8ef907f2318b514a968b` before and after.
- New draft file SHA-256: `a8807ac90186823ae585ef2161e4e02caf2c53c5f97a28f64ac2b3ecd0cc0151`. This external file-integrity digest is not a frozen benchmark checksum or factual verification.
- `git diff --check` passed. Because both deliverables are new/untracked, their contents were also explicitly checked for trailing whitespace: none. No tracked file changes were present.
- Files created: benchmarks/fizzera_ci_draft_v1.json and docs/FIZZERA_BENCHMARK_DESIGN.md. No existing file was modified; the prior audit and unrelated pre-existing untracked file remain untouched.
- Environment: existing local Python/Pydantic loader and mock benchmark suites were sufficient. No dependency installation or live-backend validation was performed; prior runtime/dependency limitations remain unresolved.

**Decision:** schema-compatible design complete; factual/pilot readiness remains NO-GO. All tasks need curation; F04/F10 historical captures, F07/F08 provincial sources and F11 differing statements are the main scope-revision risks. Next: approve wording/dates and evidence selection; recover/curate and independently verify F01/F10/F11 packs and optional F10 supplement; fill reference/component/verification/input bindings; approve scoring/environment/budget; then request approval for a new frozen release and, separately, live execution. No freeze or live experiment is authorized by this validation record.
