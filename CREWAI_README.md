# CrewAI Framework

For the new company-aware Researcher → Analyst collaboration, see
[ANALYST_README.md](ANALYST_README.md). It preserves the approved Researcher output
and uses a CrewAI Flow plus a native Analyst Agent/Task. The commands below remain
the older single-versus-multi-agent experiment scaffold.
The downstream independent Reviewer is documented in [REVIEWER_README.md](REVIEWER_README.md).
The expanded, resumable workflow and measured website-access results are documented in
[FULL_CORPUS_README.md](FULL_CORPUS_README.md).
The optional single Analyst revision and independent recheck are documented in
[REVISION_README.md](REVISION_README.md).
The final executive presentation agent and styled short brief are documented in
[EXECUTIVE_README.md](EXECUTIVE_README.md). Add `--executive` to the Analyst command
to run Reviewer and the editor after analysis, or present an existing reviewed revision.

This project compares two agent architectures using the same frozen dataset:

- Single-agent baseline
- Multi-agent CrewAI workflow

Both modes read:

`news_scrapper/news_dataset_v2_2_full.json` (Lau's V2.2 discovery dataset).

Only the 255 accepted URLs are supplied; rejected and review records are excluded
before applying `--max-articles`. Company associations are retained, including
multi-company articles and industry context. Discovery dimensions remain search
provenance rather than verified topic labels.

This frozen dataset currently contains titles, source URLs, and dates, with no
article bodies. Both modes receive an explicit title-only evidence limitation.
Full article analysis still requires content extraction. The discovery checkpoint
is incomplete: 90 queries completed and 22 ended in errors.

Use `--dataset news_scrapper/news_dataset.json` to explicitly run the older dataset.

Do not let either architecture scrape new articles for Experiment 1. The whole point is that both architectures receive the same evidence.

## Setup

Create `.env` from `.env.example`:

```bash
SERPAPI_KEY=your_serpapi_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Multi-Agent Crew

```bash
python3 run_crewai.py --mode multi
```

Output:

`outputs/multi_agent_report.md`

## Run Single-Agent Baseline

```bash
python3 run_crewai.py --mode single
```

Output:

`outputs/single_agent_report.md`

## Quick Smoke Test

Use a small article sample before spending tokens on the full dataset:

```bash
python3 run_crewai.py --mode multi --max-articles 25
python3 run_crewai.py --mode single --max-articles 25
```

## Multi-Agent Roles

The CrewAI workflow uses three sequential agents:

- Beverage Market Researcher: extracts the fact base from articles.
- Competitive Intelligence Analyst: compares companies across competitive dimensions.
- Strategy Report Writer: writes the final Markdown report.

## Fairness Rule

For Experiment 1, keep these constant:

- same dataset path (defaults to `news_dataset_v2_2_full.json`)
- same model
- same article limit, if using one
- same output rubric

The variable should be architecture only: single agent vs multi agent.
