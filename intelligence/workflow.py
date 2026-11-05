"""Persisted sequential coordinator. No correction loop or extra Writer agent."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from intelligence.schema import Query, ResearchPlan, AnalystReport, ReviewAssessment
from planner.agent import INSTRUCTIONS as PLAN_PROMPT, validate_plan
from researcher.general import research_all, validate_sources
from analyst.general import INSTRUCTIONS as ANALYST_PROMPT, validate_report
from reviewer.general import INSTRUCTIONS as REVIEW_PROMPT, validate_review

def save_json(path, value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")

def render_output(report, evidence, review, state):
    sources = {a.article_id: a for a in evidence.sources}
    from analyst.general import resolve_refs
    lines = ["# Competitive intelligence report", f"**Review status: {state['publication_status']}**",
             "This is an AI-reviewed draft, not human approval or independent factual verification.",
             f"Question: {report.question}", f"As of: {report.as_of_date}",
             "Companies: " + ", ".join(report.companies)]
    for insight in report.insights:
        refs = resolve_refs(insight, evidence)
        links = "; ".join(f"[{aid}:{pid}]({sources[aid].url}) ({sources[aid].publication_date})"
                          for aid, pid in sorted(refs))
        lines += [f"## {insight.insight_id}", f"Reported evidence: {insight.observed_fact}",
                  f"Interpretation: {insight.interpretation}", f"Sources: {links}",
                  f"Uncertainty: {insight.uncertainty}"]
    for rec in report.recommendations:
        lines += [f"## {rec.recommendation_id}: {rec.decision_status}", rec.action,
                  rec.rationale, f"Next evidence: {rec.next_evidence}"]
    lines += ["## Task coverage"]
    lines += [f"- {c.task_id}: " + (", ".join(c.insight_ids) if c.insight_ids else c.gap)
              for c in report.answer_components]
    lines += ["## Reviewer findings"]
    lines += [f"- {i.target_type} {i.target_id}: {i.disposition}. {i.explanation} "
              f"{i.required_correction}" for i in review.items]
    lines += [f"- {issue}" for issue in review.blocking_issues]
    lines += ["## Limitations", *[f"- {s}" for s in
              report.limitations + evidence.limitations + review.limitations]]
    return "\n\n".join(lines) + "\n"

def run_workflow(*, query, articles, output_dir, backend=None, live=False, batch_size=5,
                 report_schema=AnalystReport, review_schema=ReviewAssessment,
                 analyst_instructions=ANALYST_PROMPT, reviewer_instructions=REVIEW_PROMPT,
                 analysis_validator=None):
    query = Query.model_validate(query)
    sources = validate_sources(articles)
    if not 1 <= batch_size <= 5:
        raise ValueError("Research batch size must be between 1 and 5")
    if backend is None:
        if not live:
            raise ValueError("Live model calls require explicit live=True / --live")
        from intelligence.runtime import CrewAIBackend
        backend = CrewAIBackend()
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    save = lambda name, value: save_json(directory / name, value)
    save("user_query.json", query)
    save("sources.json", [a.model_dump() for a in sources])
    metrics, sequence = [], []
    start = time.monotonic()
    state = {"architecture": "user -> planner -> researcher -> analyst -> reviewer -> output",
             "schema_version": "general-intelligence-v1", "status": "running",
             "publication_status": "pending_review", "source_count": len(sources),
             "readable_sources": sum(a.availability == "full_text" for a in sources),
             "batch_size": batch_size, "correction_attempts": 0,
             "query_sha256": hashlib.sha256(query.model_dump_json().encode()).hexdigest(),
             "source_sha256": hashlib.sha256(json.dumps([a.model_dump() for a in sources],
                                                        sort_keys=True).encode()).hexdigest()}
    def call(stage, schema, instructions, payload):
        number = len(metrics) + 1
        began = time.monotonic()
        metric = {"agent": stage, "start_time": datetime.now(timezone.utc).isoformat(),
                  "model": None, "usage": None, "status": "failed"}
        try:
            sequence.append(stage)
            save(f"stage_{number:04d}_{stage}_input.json", payload)
            result = backend.generate(stage, schema, instructions, payload)
            metric.update(model=result.model, usage=result.usage)
            (directory / f"stage_{number:04d}_{stage}_raw.txt").write_text(result.raw, encoding="utf-8")
            parsed = schema.model_validate(result.data) if result.data is not None else schema.model_validate_json(result.raw)
            metric["status"] = "completed"
            return parsed
        except Exception as exc:
            metric["error_type"] = type(exc).__name__
            raise
        finally:
            metric.update(end_time=datetime.now(timezone.utc).isoformat(),
                          duration_seconds=round(time.monotonic() - began, 6))
            metrics.append(metric)
    try:
        plan = call("planner", ResearchPlan, PLAN_PROMPT, {"query": query.model_dump(mode="json")})
        save("planner_output.json", plan)
        validate_plan(plan, query)
        evidence = research_all(sources, plan, call, save, batch_size)
        save("researcher_output.json", evidence)
        analyst_input = {"query": query.model_dump(mode="json"), "plan": plan.model_dump(mode="json"),
                         "evidence": evidence.model_dump(mode="json")}
        report = call("analyst", report_schema, analyst_instructions, analyst_input)
        save("analyst_report.json", report)
        validate_report(report, query, plan, evidence)
        if analysis_validator is not None:
            analysis_validator(report, query)
        review = call("reviewer", review_schema, reviewer_instructions,
                      {**analyst_input, "analyst_report": report.model_dump(mode="json")})
        save("reviewer_output.json", review)
        state.update(validate_review(review, report, evidence))
        save("output.json", {"report": report.model_dump(mode="json"),
                            "review": review.model_dump(mode="json"),
                            "publication_status": state["publication_status"]})
        (directory / "output.md").write_text(render_output(report, evidence, review, state), encoding="utf-8")
        state["status"] = "completed"
        return state
    except Exception as exc:
        state.update(status="failed", publication_status="hold_for_human_review",
                     error_type=type(exc).__name__)
        raise
    finally:
        state.update(stage_sequence=sequence, duration_seconds=round(time.monotonic() - start, 6),
                     agent_executions=metrics)
        save("run_manifest.json", state)
