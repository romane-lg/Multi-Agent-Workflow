"""Lazy native CrewAI backend; importing the workflow makes no model calls."""
import json
import os
from dataclasses import dataclass

@dataclass
class StageResult:
    data: dict | None
    raw: str
    model: str
    usage: dict | None = None
    model_calls: int | None = None
    tool_calls: int | None = None

class CrewAIBackend:
    def __init__(self, models=None):
        self.models = models or {}

    def generate(self, stage, schema, instructions, payload):
        import analyst
        from analyst.runtime import prepare_crewai_runtime
        from researcher.runtime import configure
        prepare_crewai_runtime()
        configure()
        from crewai import Agent, Crew, LLM, Process, Task
        from corpus.budget import check_context
        default = "gpt-4o-mini" if stage in ("planner", "researcher") else "gpt-4.1"
        model = self.models.get(stage) or os.getenv(stage.upper() + "_MODEL", default)
        context = json.dumps(payload, ensure_ascii=False)
        check_context(instructions + context + json.dumps(schema.model_json_schema()), model)
        llm = LLM(model=model, temperature=0, max_tokens=12000, timeout=240, max_retries=0)
        agent = Agent(role=f"Competitive intelligence {stage}", goal=instructions,
            backstory="You separate evidence, assumptions, interpretation and uncertainty.",
            llm=llm, tools=[], allow_delegation=False, max_iter=1, max_retry_limit=0,
            respect_context_window=False, verbose=False)
        task = Task(description=instructions + "\n\nFROZEN INPUT:\n{context}",
            expected_output=f"Only a complete {schema.__name__}.",
            agent=agent, response_model=schema, output_pydantic=schema, guardrail_max_retries=0)
        output = Crew(agents=[agent], tasks=[task], process=Process.sequential,
            memory=False, planning=False, cache=False, tracing=False, verbose=False).kickoff(
                inputs={"context": context})
        # Parsing and validation happen after raw output is saved by the coordinator.
        return StageResult(data=output.pydantic.model_dump(mode="json") if output.pydantic else None,
            raw=output.raw, model=model,
            usage=output.token_usage.model_dump() if output.token_usage else None,
            model_calls=getattr(output.token_usage, 'successful_requests', None) if output.token_usage else None,
            tool_calls=0)
