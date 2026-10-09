from __future__ import annotations

from pathlib import Path

from crew_ai.data import build_article_context, load_dataset


DEFAULT_MODEL = "gpt-4o-mini"


def import_crewai():
    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError as exc:
        raise RuntimeError(
            "CrewAI is not installed. Run `pip install -r requirements.txt` first."
        ) from exc

    return Agent, Crew, Process, Task


def load_env(path: str = ".env") -> None:
    import os

    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_multi_agent_crew(article_context: str, model: str = DEFAULT_MODEL):
    Agent, Crew, Process, Task = import_crewai()

    market_researcher = Agent(
        role="Beverage Market Researcher",
        goal="Extract reliable competitive facts from the frozen news dataset.",
        backstory=(
            "You are a careful CPG researcher. You only use the provided dataset, "
            "and you preserve article titles, sources, dates, and links when citing evidence."
        ),
        llm=model,
        verbose=True,
    )

    competitor_analyst = Agent(
        role="Competitive Intelligence Analyst",
        goal="Compare Olipop, Poppi, Culture Pop, and Zevia using the same evidence base.",
        backstory=(
            "You specialize in beverage category strategy, retail expansion, launches, "
            "marketing signals, partnerships, and company momentum."
        ),
        llm=model,
        verbose=True,
    )

    strategy_writer = Agent(
        role="Strategy Report Writer",
        goal="Turn the analysis into a clear competitive insights report with evidence.",
        backstory=(
            "You write concise executive-style reports. You separate facts from "
            "interpretation and avoid claims that are not supported by the dataset."
        ),
        llm=model,
        verbose=True,
    )

    research_task = Task(
        description=(
            "Using only the frozen article dataset below, create a fact table by company. "
            "Track product launches, flavor news, retail expansion, marketing campaigns, "
            "funding/partnership/acquisition signals, and consumer/sales signals.\n\n"
            "{article_context}"
        ),
        expected_output=(
            "A structured fact base grouped by company and category. Include article title, "
            "source, date, and link for each important fact."
        ),
        agent=market_researcher,
    )

    comparison_task = Task(
        description=(
            "Compare the competitors using the fact base. Identify which brands appear "
            "strongest in product innovation, retail/distribution, marketing momentum, "
            "business momentum, and evidence quality. Use cautious wording when article "
            "coverage is uneven."
        ),
        expected_output=(
            "A competitive comparison with ranked strengths, weaknesses, and evidence-backed "
            "insights for each company."
        ),
        agent=competitor_analyst,
        context=[research_task],
    )

    report_task = Task(
        description=(
            "Write the final competitive insights report. Include: executive summary, "
            "company-by-company insights, cross-company trends, opportunities/threats, "
            "evidence limitations, and recommended next questions for the human team."
        ),
        expected_output=(
            "A polished Markdown report with citations using article title, source, date, "
            "and link. Do not cite anything outside the frozen dataset."
        ),
        agent=strategy_writer,
        context=[research_task, comparison_task],
    )

    return Crew(
        agents=[market_researcher, competitor_analyst, strategy_writer],
        tasks=[research_task, comparison_task, report_task],
        process=Process.sequential,
        verbose=True,
    )


def build_single_agent_crew(article_context: str, model: str = DEFAULT_MODEL):
    Agent, Crew, Process, Task = import_crewai()

    analyst = Agent(
        role="Single-Agent Competitive Insights Analyst",
        goal="Create a full competitive insights report from the frozen dataset.",
        backstory=(
            "You are a generalist CPG analyst doing research extraction, comparison, "
            "and report writing alone. You only use the supplied dataset."
        ),
        llm=model,
        verbose=True,
    )

    task = Task(
        description=(
            "Using only the frozen article dataset below, produce a competitive insights "
            "report comparing Olipop, Poppi, Culture Pop, and Zevia. Cover product launches, "
            "retail/distribution, marketing, partnerships/business momentum, consumer/sales "
            "signals, limitations, and next questions. Cite article titles, sources, dates, "
            "and links.\n\n{article_context}"
        ),
        expected_output="A polished Markdown competitive insights report with evidence.",
        agent=analyst,
    )

    return Crew(
        agents=[analyst],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )


def run_experiment(
    mode: str,
    dataset_path: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    max_articles: int | None = None,
) -> str:
    load_env()
    dataset = load_dataset(dataset_path)
    article_context = build_article_context(dataset, max_articles=max_articles)

    if mode == "multi":
        crew = build_multi_agent_crew(article_context, model=model)
    elif mode == "single":
        crew = build_single_agent_crew(article_context, model=model)
    else:
        raise ValueError("mode must be 'single' or 'multi'")

    result = crew.kickoff(inputs={"article_context": article_context})
    output = str(result)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output)
    return output
