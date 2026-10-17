# Fizzera executive output agent

The native CrewAI **Executive Brief Editor** follows the Analyst and independent Reviewer,
including a saved one-cycle revision when present. It turns the findings into a short
strategic outlook and five topic buckets: Ontario retail, pricing and margins, product
pipeline, marketing and demand, and BC expansion. Every bucket states the implication,
next action, proposed measure or decision gate, and material uncertainty.

The output starts with the strategic call, three ranked priorities and 2–3 market signals.
It ends with competitor coverage, confidence limits and linked sources. The HTML uses a
compact card layout, adapts to mobile, and includes print styles and collapsible source
details. Markdown provides the same content for easy reuse. No additional dependency is
needed beyond `requirements-analyst.txt`.

## Present the saved revision

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python scripts/write_fizzera_executive.py \
  --analysis-run .researcher/fizzera_revisions/pilot_v2 \
  --review-dir .researcher/fizzera_revisions/pilot_v2/review_retry \
  --output-dir .researcher/fizzera_executive/my_brief
```

This makes one editor model call and reuses the frozen analysis, original source texts,
company brief and review. It does not rerun Researcher, Analyst, corrections or Reviewer.
Output directories are exclusive. Raw output is preserved before validation; errors stop
the run, with no automatic retries or hidden repair calls configured.

## Include it in a fresh collaboration

Add `--executive` to the Analyst command. It implies `--review` and runs the editor after
a completed review. A failed review can produce a clearly labeled management working
brief, with the hold preserved; an incomplete or structurally invalid review cannot.

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python scripts/run_fizzera_analyst.py \
  --brief '/Users/iphonex/Downloads/Fizzera Sodas.pdf' \
  --research-output .researcher/evidence_pack_expanded.json \
  --output-dir .researcher/fizzera_runs/new_executive_run \
  --executive
```

CrewAI controls Researcher → Analyst → Reviewer → Executive Brief Editor. A correction
cycle remains an explicit separate step; after a revision, use the saved-revision command
above. Existing commands without `--executive` retain their prior behavior.

## Evidence and presentation boundaries

- Code verifies the exact analysis/review correspondence, source and brief hashes, review
  verdict consistency, revision lineage and feedback recheck when relevant.
- The complete review stays in the frozen input artifact. The editor's working context
  receives review targets/categories plus the original source paragraphs; this avoids
  presenting repeated, fallible Reviewer assertions as another factual summary.
- Prose targets 400–550 words and is capped at 650, with short individual fields. Labels,
  status, company coverage and source ledger are added by code. Source links are derived
  from validated IDs, never generated URLs. The model does not control approval labels.
- Market signals are qualitative, leaving numeric commercial metrics out of the short
  executive summary. Company decision measures may use existing targets, clearly labeled
  as proposed. This reduces the risk of losing denominators/periods while condensing.
- No new research, strategy, owner, deadline, budget, performance target or approval is
  authorized by the editor. Recommendations retain `Proposed decision`, `Test first` or
  `Evidence needed` labels derived from the Analyst. Missing competitor evidence stays
  visible, and a hold cannot become approval through formatting.
- Validation checks shape, length, references and some prohibited causal wording. It does
  not establish factual correctness. The editor must narrow or omit unsupported wording;
  it does not silently change upstream analysis. Human review is still needed.

The editor defaults to `gpt-4.1`, configurable with `EXECUTIVE_MODEL`. Other agents retain
their existing model settings. GPT-4.1 supports the structured output used here; see the
[official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1).
The smaller editor model repeated unsupported causal wording during the smoke check, so
it was replaced for this stage. This is not a controlled model comparison or benchmark.
For a same-model research comparison, explicitly align all agent model settings and rerun
the comparison with fixed sources, company context and prompts.

## Artifacts

- `executive_brief.html`: styled executive document, no external scripts/assets.
- `executive_brief.md`: readable text with source links.
- `executive_brief.json`: structured prose for future delivery channels.
- `executive_input.json`: exact frozen analysis, full review, state and input digest.
- `executive_raw.txt`: original editor response.
- `executive_manifest.json`: preserved review status, model, usage, latency, word count,
  prompt hash and verified MLflow trace ID.

Private company text and generated documents remain under ignored `.researcher/`.

## Offline functional checks

```bash
uv run --offline --cache-dir .cache/uv --with-requirements requirements-analyst.txt \
  python -m unittest executive.test_executive analyst.test_revision reviewer.test_reviewer \
  analyst.test_workflow researcher.test_agent crew_ai.test_data
```

These check orchestration, source binding, hold preservation, topic coverage, concise
fields, escaping, reference links and unchanged upstream artifacts. No quality benchmark
or evaluation judges run as part of this command.

## Saved example

The completed brief is `.researcher/fizzera_executive/pilot_v4/executive_brief.html`
(Markdown is beside it). Main generated prose is 360 words; code adds labels, the review
banner, coverage and source details. It preserves `hold_for_human_review` from the latest
Fizzera revision. The executive trace `tr-2c81936e7f008d98496760cc1dc07c9e` was read back
successfully with five spans. All 75 functional tests pass.

Desktop and mobile previews were visually inspected. Layout checks found five cards, no
horizontal overflow and no broken internal source references at 1180px and 390px widths.
Earlier local editor attempts are retained for inspection; `pilot_v4` is the current example.
This smoke check does not certify the underlying strategy or the Reviewer’s accuracy.
