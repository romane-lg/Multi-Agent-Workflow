"""CrewAI routes reviewed analysis to the final presentation agent."""
import hashlib
from pathlib import Path
import time

import mlflow
from crewai.flow.flow import Flow, listen, start

from executive.crew import build_executive_crew, EXECUTIVE_INSTRUCTIONS, FINAL_EDITORIAL_CHECK
from executive.handoff import make_executive_input
from executive.render import presentation_data, render_html, render_markdown
from executive.schema import ExecutiveBrief
from executive.validation import validate_brief
from reviewer.service import save_json


class ExecutiveOutputFlow(Flow):
    def __init__(self, *, analysis_run: Path, review_dir: Path, output_dir: Path):
        super().__init__(tracing=False)
        self.analysis_run, self.review_dir, self.output_dir = analysis_run, review_dir, output_dir

    @start()
    def reviewed_handoff(self):
        payload, context = make_executive_input(self.analysis_run, self.review_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        save_json(self.output_dir / "executive_input.json", payload)
        return payload, context

    @listen(reviewed_handoff)
    def executive_agent(self, handoff):
        payload, context = handoff
        return render_executive_output(payload, context, self.output_dir)


def present_reviewed_analysis(*, analysis_run: Path, review_dir: Path, output_dir: Path):
    # An existing CrewAI Flow can call the stage directly. Nested Flow.kickoff()
    # would create asyncio.run() inside CrewAI 1.6's already-running event loop.
    payload, context = make_executive_input(analysis_run, review_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    save_json(output_dir / "executive_input.json", payload)
    return render_executive_output(payload, context, output_dir)


def render_executive_output(payload, context, output_dir):
    started = time.monotonic()
    crew = build_executive_crew()
    output = crew.kickoff(inputs={"executive_context": context})
    (output_dir / "executive_raw.txt").write_text(output.raw, encoding="utf-8")
    brief = ExecutiveBrief.model_validate(output.pydantic.model_dump()) if output.pydantic else ExecutiveBrief.model_validate_json(output.raw)
    validate_brief(brief, payload)
    save_json(output_dir / "executive_brief.json", brief.model_dump())
    (output_dir / "executive_brief.md").write_text(render_markdown(brief, payload), encoding="utf-8")
    (output_dir / "executive_brief.html").write_text(render_html(brief, payload), encoding="utf-8")
    manifest = {
        "workflow": "CrewAI: frozen reviewed analysis -> Executive Brief Editor -> deterministic rendering",
        "executive_input_sha256": payload["executive_input_sha256"],
        "publication_status": payload["publication_status"], "presentation_status": "completed",
        "model": crew.agents[0].llm.model,
        "latency_seconds": round(time.monotonic() - started, 3),
        "usage": output.token_usage.model_dump() if output.token_usage else {},
        "prose_word_count": presentation_data(brief, payload)["prose_word_count"],
        "prompt_sha256": hashlib.sha256((EXECUTIVE_INSTRUCTIONS + FINAL_EDITORIAL_CHECK).encode()).hexdigest(),
        "upstream_agents_rerun": False, "benchmark_evaluation_run": False,
    }
    save_json(output_dir / "executive_manifest.json", manifest)
    print("Executive brief saved:", output_dir / "executive_brief.html", flush=True)
    print("Review status preserved:", manifest["publication_status"], flush=True)
    return manifest


@mlflow.trace(name="fizzera_executive_output", span_type="CHAIN")
def write_executive_brief(**kwargs):
    result = ExecutiveOutputFlow(**kwargs).kickoff()
    if not result or result.get("presentation_status") != "completed":
        raise RuntimeError("Executive presentation Flow did not finish")
    return result
