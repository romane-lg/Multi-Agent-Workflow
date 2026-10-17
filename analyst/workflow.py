"""CrewAI controls Researcher -> validated handoff -> native Analyst Crew."""
import json
from pathlib import Path
import time

import mlflow
from crewai.flow.flow import Flow, listen, start

from analyst.brief import extract_brief
from analyst.crew import build_analyst_crew
from analyst.handoff import make_handoff
from analyst.render import render_report
from analyst.schema import AnalystReport
from analyst.validation import validate_report


def write_json(path: Path, value: dict):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


class ResearcherAnalystFlow(Flow):
    def __init__(self, *, brief_path: Path, output_dir: Path, as_of_date: str,
                 research_output_path: Path | None = None, articles_path: Path | None = None,
                 review: bool = False, executive: bool = False):
        super().__init__(tracing=False)
        self.brief_path = brief_path
        self.output_dir = output_dir
        self.as_of_date = as_of_date
        self.research_output_path = research_output_path
        self.articles_path = articles_path
        self.review_enabled = review or executive
        self.executive_enabled = executive

    @start()
    def researcher_stage(self):
        if self.research_output_path is not None:
            result = json.loads(self.research_output_path.read_text())
            self.state["researcher_mode"] = "reuse_saved_output"
        else:
            from researcher.agent import research
            from researcher.schema import QUESTION
            if self.articles_path is None:
                raise ValueError("Supply a saved Researcher output or a frozen article snapshot")
            result = research(question=QUESTION, articles=json.loads(self.articles_path.read_text()))
            span = mlflow.get_current_active_span()
            result["run"]["trace_id"] = span.trace_id if span else mlflow.get_last_active_trace_id()
            self.state["researcher_mode"] = "fresh_researcher_call"
        print("Researcher stage:", self.state["researcher_mode"], flush=True)
        return result

    @listen(researcher_stage)
    def handoff_stage(self, researcher_output):
        brief = extract_brief(self.brief_path)
        payload, context = make_handoff(researcher_output, brief, self.as_of_date)
        write_json(self.output_dir / "researcher_output.json", researcher_output)
        write_json(self.output_dir / "company_brief.json", brief.model_dump())
        write_json(self.output_dir / "handoff.json", payload)
        (self.output_dir / "handoff.txt").write_text(context, encoding="utf-8")
        self.state["handoff_sha256"] = payload["handoff_sha256"]
        self.state["source_count"] = len(researcher_output["sources"])
        print("Handoff validated:", self.state["source_count"], "articles;", len(brief.pages), "brief pages", flush=True)
        return researcher_output, brief, context

    @listen(handoff_stage)
    def analyst_stage(self, handoff):
        researcher_output, brief, context = handoff
        started = time.monotonic()
        crew = build_analyst_crew()
        output = crew.kickoff(inputs={"handoff_context": context})
        # Preserve raw output before validation so a failed response remains reviewable.
        (self.output_dir / "analyst_raw.txt").write_text(output.raw, encoding="utf-8")
        report = output.pydantic or AnalystReport.model_validate_json(output.raw)
        validate_report(report, researcher_output, brief, self.as_of_date)
        write_json(self.output_dir / "analyst_report.json", report.model_dump())
        (self.output_dir / "analyst_report.md").write_text(render_report(report, researcher_output, brief), encoding="utf-8")
        manifest = {
            "workflow": "CrewAI Flow: Researcher -> validated handoff -> Analyst Crew",
            "researcher_mode": self.state["researcher_mode"],
            "researcher_run": researcher_output.get("run", {}),
            "handoff_sha256": self.state["handoff_sha256"],
            "brief_pdf_sha256": brief.pdf_sha256,
            "as_of_date": self.as_of_date,
            "analyst_latency_seconds": round(time.monotonic() - started, 3),
            "analyst_usage": output.token_usage.model_dump() if output.token_usage else {},
            "reviewer_run": False, "quality_evaluation_run": False,
            "review_requested": self.review_enabled,
            "publication_status": "pending_review" if self.review_enabled else "unreviewed",
        }
        write_json(self.output_dir / "run_manifest.json", manifest)
        print("Analyst completed; artifacts:", self.output_dir, flush=True)
        return report.model_dump()

    @listen(analyst_stage)
    def completion_stage(self, analyst_result):
        if not self.review_enabled:
            return analyst_result
        from reviewer.workflow import review_completed_analysis
        reviewed = review_completed_analysis(self.output_dir, analyst_result)
        if not self.executive_enabled:
            return reviewed
        from executive.workflow import present_reviewed_analysis
        result = present_reviewed_analysis(analysis_run=self.output_dir, review_dir=self.output_dir / "review",
                                           output_dir=self.output_dir / "executive")
        path = self.output_dir / "run_manifest.json"
        manifest = json.loads(path.read_text())
        manifest.update(workflow=manifest["workflow"] + " -> Executive Brief Editor",
                        executive_run=True, executive_output_dir=str(self.output_dir / "executive"),
                        executive_run_details=result)
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        return result


@mlflow.trace(name="researcher_to_fizzera_analyst", span_type="CHAIN")
def run_workflow(*, review: bool = False, executive: bool = False, **kwargs):
    if executive:
        result = ResearcherAnalystFlow(review=True, executive=True, **kwargs).kickoff()
        if not result or result.get("presentation_status") != "completed":
            raise RuntimeError("Executive presentation did not complete")
        return result
    if review:
        from reviewer.schema import ReviewResult
        result = ResearcherAnalystFlow(review=True, **kwargs).kickoff()
        ReviewResult.model_validate(result)
        return result
    result = ResearcherAnalystFlow(**kwargs).kickoff()
    # Never mistake an intermediate Flow result for a completed analysis.
    AnalystReport.model_validate(result)
    return result
