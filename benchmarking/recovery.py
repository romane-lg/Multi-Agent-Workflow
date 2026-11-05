"""One targeted correction, reusing the legacy revision contract and exact diff."""
import json
from pydantic import create_model
from analyst.correction import revision_response_model, report_diff
from analyst.general import INSTRUCTIONS as ANALYST_PROMPT, validate_report
from researcher.general import research_all
from reviewer.general import INSTRUCTIONS as REVIEW_PROMPT, validate_review
from intelligence.schema import EvidencePack, ResearchPlan, TaskCoverage, CompanyCoverage
from benchmarking.experimental_schema import MAX_RETRIES, ExperimentalReview, FizzeraReport, Resolution

MATERIAL = {"missing_information", "unsupported_claim", "contradictory_evidence",
            "chronology", "geography", "company_constraints", "invalid_source"}
REVIEW_ROUTING = """
For each needs_correction item classify failure_type, severity, target_agent and
information_status. Material failures are missing information, unsupported material
facts, contradictory evidence, chronology/geography, company constraints or invalid
important sources. Use high/critical only for material problems. Grammar/formatting
are advisory. Researcher is appropriate only for a specific missing evidence gap;
use analyst when existing sources suffice. Genuinely unavailable facts remain gaps.
Do not assert external retrieval or human verification. These fields are proposals;
code controls whether one correction is permitted."""
FIZZERA_RULES = """
Use only documented Fizzera context. Recommendations may cover the relevant
subset of ontario_retail, pricing, product_launch, marketing, bc_expansion.
Assign each recommendation its focus, optional proposed_budget_cad,
requires_additional_financing and optional launch_concept. Preserve the total and
product ceilings, one-launch rule, dates, manufacturing caveats and provisional
budget labels. Cite actual BRIEF pN context keys; no guessed brief pages.
Do not treat fictional surveys, forecasts, targets or company plans as market facts.
Do not force unrelated recommendations to fill the five topics."""

def targeted_issues(review, report):
    insight_tasks = {i.insight_id: i.task_ids for i in report.insights}
    rec_tasks = {r.recommendation_id: r.task_ids for r in report.recommendations}
    issues = []
    for n, item in enumerate(review.items, 1):
        failed = item.disposition == "needs_correction" or any(r.status == "issue" for r in item.risks)
        if not failed or item.failure_type not in MATERIAL or item.severity not in {"high", "critical"}:
            continue
        if item.target_agent not in {"researcher", "analyst"}:
            continue
        tasks = ([item.target_id] if item.target_type == "task" else
                 insight_tasks.get(item.target_id, rec_tasks.get(item.target_id, [])))
        issues.append({"issue_id": f"E{n:03d}", "target_type": item.target_type,
            "target_id": item.target_id, "task_ids": tasks, "failure_type": item.failure_type,
            "severity": item.severity, "target_agent": item.target_agent,
            "information_status": item.information_status, "problem": item.explanation,
            "required_correction": item.required_correction})
    return issues

def merge_evidence(original, addition):
    old = {a.article_id: a for a in original.sources}
    for a in addition.sources:
        if a.article_id in old and a.model_dump() != old[a.article_id].model_dump():
            raise ValueError("Recovery cannot replace an original source")
    sources = list(original.sources) + [a for a in addition.sources if a.article_id not in old]
    findings = list(original.findings) + [
        f.model_copy(update={"finding_id": "recovery__" + f.finding_id}) for f in addition.findings]
    if len({f.finding_id for f in findings}) != len(findings):
        raise ValueError("Recovery finding IDs collide")
    assessments = list(original.article_assessments) + [
        a for a in addition.article_assessments if a.article_id not in old]
    tasks = [TaskCoverage(task_id=t.task_id,
        finding_ids=[f.finding_id for f in findings if t.task_id in f.task_ids],
        gap="" if any(t.task_id in f.task_ids for f in findings) else t.gap)
        for t in original.task_coverage]
    companies = [CompanyCoverage(company=c.company,
        finding_ids=[f.finding_id for f in findings if c.company in f.companies],
        gap="" if any(c.company in f.companies for f in findings) else c.gap)
        for c in original.company_coverage]
    return original.model_copy(update={"sources": sources, "findings": findings,
        "article_assessments": assessments, "task_coverage": tasks, "company_coverage": companies,
        "limitations": list(dict.fromkeys(original.limitations + addition.limitations))})

def correct_once(*, query, plan, evidence, report, review, supplemental, call, save, validate_fizzera, attempt=1):
    if attempt != 1 or MAX_RETRIES != 1:
        raise ValueError("MAX_RETRIES=1; nested or second corrections are forbidden")
    issues = targeted_issues(review, report)
    if not issues:
        raise ValueError("No permitted material target for recovery")
    save("recovery_instructions.json", {"attempt": 1, "maximum_attempts": 1, "issues": issues})
    updated = evidence
    research_targets = [i for i in issues if i["target_agent"] == "researcher"
                        and i["information_status"] == "missing"]
    research_note = "Existing evidence is sufficient for Analyst-only correction."
    if research_targets:
        # Frozen local evidence only. No discovery/network tool or entire-corpus rerun.
        task_ids = {tid for i in research_targets for tid in i["task_ids"]}
        tasks = [t for t in plan.tasks if t.task_id in task_ids]
        used = {a.article_id for a in evidence.sources}
        pool = [a for a in supplemental if a.availability == "full_text" and a.article_id not in used]
        if pool and tasks:
            from corpus.index import build_index, search
            index = build_index([a.model_dump() for a in pool])
            text = " ".join(i["problem"] + " " + i["required_correction"] for i in research_targets)
            text += " " + " ".join(t.question for t in tasks)
            ranked = []
            for hit in search(index, text, limit=len(index["chunks"])):
                if hit["article_id"] not in ranked:
                    ranked.append(hit["article_id"])
            # No lexical match is a gap, not permission to choose unrelated evidence.
            selected = [next(a for a in pool if a.article_id == aid) for aid in ranked[:5]]
            if selected:
                subplan = plan.model_copy(update={"tasks": tasks})
                addition = research_all(selected, subplan, call, save, batch_size=5)
                save("additional_evidence.json", addition)
                updated = merge_evidence(evidence, addition)
                research_note = "Targeted extraction from at most five pre-supplied frozen sources; no live search."
            else:
                research_note = "No relevant supplemental source matched; preserve the information gap."
        else:
            research_note = "No new readable frozen evidence supplied; qualify/remove the claim instead of inventing data."
    if any(i["information_status"] == "unavailable" for i in issues):
        research_note += " Genuinely unavailable information is not researched again."
    save("research_recovery_status.json", {"note": research_note, "targeted_requests": research_targets})
    save("updated_evidence.json", updated)
    schema = revision_response_model(issues, report_model=FizzeraReport)
    revision = call("analyst", schema, ANALYST_PROMPT + FIZZERA_RULES + """
Revise the ORIGINAL report against selected feedback, which may be mistaken.
Preserve insight/recommendation IDs and unaffected content. Respond to EVERY selected
issue as addressed, declined or needs_evidence, with rationale and change description.
Use the exact updated evidence; remove or qualify unsupported scope rather than inventing facts.
This is the only allowed revision. Do not delegate or request another correction.""",
        {"query": query.model_dump(mode="json"), "plan": plan.model_dump(mode="json"),
         "evidence": updated.model_dump(mode="json"), "original_report": report.model_dump(mode="json"),
         "selected_issues": issues})
    revised = revision.report
    validate_report(revised, query, plan, updated)
    validate_fizzera(revised, query)
    if {i.insight_id for i in revised.insights} != {i.insight_id for i in report.insights}:
        raise ValueError("Revision changed stable insight IDs")
    if {r.recommendation_id for r in revised.recommendations} != {r.recommendation_id for r in report.recommendations}:
        raise ValueError("Revision changed stable recommendation IDs")
    for value in revision.feedback_responses.model_dump().values():
        if not value["rationale"].strip() or not value["change_description"].strip():
            raise ValueError("Every selected issue needs a reasoned response")
    save("post_recovery_report.json", revised)
    save("revision_changes.json", revision.feedback_responses.model_dump())
    save("analysis_diff.json", {"unified_diff": report_diff(report.model_dump(mode="json"), revised.model_dump(mode="json"))})
    responses = create_model("RequiredResolutions", **{i["issue_id"]: (Resolution, ...) for i in issues})
    model = create_model("RecoveryReview", __base__=ExperimentalReview, feedback_resolution=(responses, ...))
    second = call("reviewer", model, REVIEW_PROMPT + REVIEW_ROUTING + """
Review the ENTIRE revised report, including possible newly introduced errors.
Independently resolve every selected issue; do not trust the Analyst change log.
resolved includes a demonstrably mistaken original criticism. Explain the decision.
Unresolved/disputed material feedback preserves a hold. No further recovery.""",
        {"query": query.model_dump(mode="json"), "plan": plan.model_dump(mode="json"),
         "evidence": updated.model_dump(mode="json"), "analyst_report": revised.model_dump(mode="json"),
         "original_report": report.model_dump(mode="json"), "selected_issues": issues,
         "analyst_responses": revision.feedback_responses.model_dump()})
    save("second_review.json", second)
    verdict = validate_review(second, revised, updated)
    resolutions = second.feedback_resolution.model_dump()
    unresolved = [key for key, value in resolutions.items() if value["status"] != "resolved"]
    if unresolved:
        verdict["publication_status"] = "hold_for_human_review"
    old_flags = {(i["target_type"], i["target_id"], i["failure_type"]) for i in issues}
    new_flags = [i for i in targeted_issues(second, revised)
                 if (i["target_type"], i["target_id"], i["failure_type"]) not in old_flags]
    save("recovery_result.json", {"attempts": 1, "unresolved_issue_ids": unresolved,
        "reviewer_resolution": resolutions, "new_reviewer_flags": new_flags,
        "independently_verified_recovery_metrics": None,
        "note": "Reviewer judgments are not ground truth; independent before/after annotations are required."})
    return revised, updated, second, verdict
