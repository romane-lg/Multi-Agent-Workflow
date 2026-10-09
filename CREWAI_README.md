# CrewAI Framework

This project compares two agent architectures using the same frozen dataset:

- Single-agent baseline
- Multi-agent CrewAI workflow

Both modes read:

`news_scrapper/news_dataset.json`

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

- same `news_dataset.json`
- same model
- same article limit, if using one
- same output rubric

The variable should be architecture only: single agent vs multi agent.
