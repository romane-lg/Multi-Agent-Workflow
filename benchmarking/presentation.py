"""Reuse the existing executive schema, validators, renderer and final evidence audit."""
import hashlib
import json
import re
from executive.schema import ExecutiveBrief
from executive.crew import EXECUTIVE_INSTRUCTIONS, FINAL_EDITORIAL_CHECK
from executive.validation import validate_brief
from executive.render import render_markdown, render_html
from executive.audit_contract import audit_model, validate_audit, INSTRUCTIONS as AUDIT_PROMPT
from benchmarking.experimental_schema import FOCUSES

FOCUS_PAGES = {"ontario_retail": [9], "pricing": [10, 11],
               "product_launch": [11, 12], "marketing": [12, 13], "bc_expansion": [13]}
def brief_keys(query):
    return {int(re.fullmatch(r"BRIEF p(\d+)", k)[1]): k for k in query.company_context
            if re.fullmatch(r"BRIEF p(\d+)", k)}

def validate_fizzera(report, query, brief):
    pages = brief_keys(query)
    for insight in report.insights:
        if not any(k in pages.values() for k in insight.context_keys):
            raise ValueError("Fizzera implications need actual brief-page context keys")
    focuses = [r.focus for r in report.recommendations]
    if len(focuses) != len(set(focuses)):
        raise ValueError("Duplicate recommendation focus")
    total, launch, concepts = 0, 0, set()
    for rec in report.recommendations:
        if not any(k in pages.values() for k in rec.context_keys):
            raise ValueError("Fizzera recommendation needs a brief-page context key")
        budget = rec.proposed_budget_cad
        if budget is not None and not rec.requires_additional_financing:
            total += budget
            if rec.focus == "product_launch":
                launch += budget
        if rec.launch_concept not in (None, "postpone"):
            if rec.focus != "product_launch":
                raise ValueError("Launch concepts belong to the product decision")
            concepts.add(rec.launch_concept)
    if len(concepts) > 1:
        raise ValueError("Fizzera permits one major product launch")
    if brief.investment_envelope_cad is None or brief.product_launch_budget_cad is None:
        raise ValueError("Fizzera budget ceilings could not be extracted; human review required")
    if total > brief.investment_envelope_cad or launch > brief.product_launch_budget_cad:
        raise ValueError("Fizzera budget ceiling exceeded")

def payload_for(report, evidence, review, brief, status, reviewer_type):
    def pages(keys):
        return [int(k.split("p")[-1]) for k in keys if re.fullmatch(r"BRIEF p\d+", k)]
    insights = [{"insight_id": i.insight_id, "observed_fact": i.observed_fact,
        "interpretation_for_fizzera": i.interpretation, "evidence": i.evidence.model_dump(),
        "brief_pages": pages(i.context_keys)} for i in report.insights]
    recs = []
    lookup = {r.focus: r for r in report.recommendations}
    for focus in FOCUSES:
        if focus in lookup:
            r = lookup[focus]
            recs.append({**r.model_dump(mode="json"), "rationale_for_fizzera": r.rationale,
                "proposed_action": r.action, "brief_pages": pages(r.context_keys),
                "success_measure": r.next_evidence})
        else:
            recs.append({"focus": focus, "recommendation_id": "gap_" + focus,
                "decision_status": "needs_evidence", "insight_ids": [],
                "brief_pages": [p for p in FOCUS_PAGES[focus] if p in {b.page_number for b in brief.pages}],
                "proposed_action": "No task-specific recommendation supplied; defer this decision.",
                "rationale_for_fizzera": "Outside this task's supported recommendations.",
                "success_measure": "Task-specific evidence and management review required."})
    finding_map = {f.finding_id: f for f in evidence.findings}
    competitors = []
    for company in ("Olipop", "Poppi", "Culture Pop", "Zevia", "Cove Soda", "Crazy D's"):
        ids = [i.insight_id for i in report.insights if any(
            company in finding_map[f].companies for f in i.evidence.finding_ids)]
        competitors.append({"company": company, "evidence_status": "covered" if ids else "no_evidence",
            "insight_ids": ids, "evidence_gap": "" if ids else "No supported task insight for this company."})
    mapped = {"company_name": "Fizzera", "research_question": report.question,
        "as_of_date": str(report.as_of_date), "market_insights": insights,
        "recommendations": recs, "competitor_comparison": competitors}
    researcher = {"evidence_pack": evidence.model_dump(mode="json"),
                  "sources": [s.model_dump(mode="json") for s in evidence.sources]}
    value = {"publication_status": status, "reviewer_type": reviewer_type,
        "analysis": {"analyst_report": mapped, "upstream_handoff": {
            "researcher_output": researcher, "company_brief": brief.model_dump(mode="json")}},
        "review": {"assessment": review.model_dump(mode="json")}}
    value["executive_input_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value

def present(*, report, evidence, review, brief, status, reviewer_type, call, save, folder):
    payload = payload_for(report, evidence, review, brief, status, reviewer_type)
    save("executive_input.json", payload)
    if not report.insights:
        save("executive_manifest.json", {"status": "blocked", "editorial_audit_passed": False,
            "publication_status": "hold_for_human_review", "reason": "No supported insights for required market signals."})
        return {"status": "blocked", "publication_status": "hold_for_human_review"}
    brief_output = call("executive", ExecutiveBrief, EXECUTIVE_INSTRUCTIONS + FINAL_EDITORIAL_CHECK,
                        {"executive_context": payload})
    save("executive_brief.json", brief_output)
    validate_brief(brief_output, payload)
    audit = call("editorial_auditor", audit_model(brief_output), AUDIT_PROMPT, {
        "executive": brief_output.model_dump(mode="json"), "analysis": payload["analysis"]["analyst_report"],
        "company_brief": brief.model_dump(mode="json"),
        "sources": [a.model_dump(mode="json") for a in evidence.sources],
        "review_state": review.model_dump(mode="json")})
    save("editorial_audit_raw.json", audit)
    checks = validate_audit(audit.model_dump(mode="json"), brief_output, payload)
    passed = all(c["verdict"] == "supported" for c in checks.values())
    if not passed:
        payload["publication_status"] = "hold_for_human_review"
    save("editorial_audit.json", {"checks": checks, "passed": passed,
        "executive_sha256": hashlib.sha256(brief_output.model_dump_json().encode()).hexdigest()})
    md, html = render_markdown(brief_output, payload), render_html(brief_output, payload)
    if reviewer_type == "human":
        md = md.replace("Model review completed", "Human review completed; final wording model-audited")
        html = html.replace("Model review completed", "Human review completed; final wording model-audited")
    (folder / "executive_brief.md").write_text(md, encoding="utf-8")
    (folder / "executive_brief.html").write_text(html, encoding="utf-8")
    result = {"status": "completed", "editorial_audit_passed": passed,
              "publication_status": payload["publication_status"]}
    save("executive_manifest.json", result)
    return result
