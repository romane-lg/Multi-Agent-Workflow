"""Validate review references/coverage and derive a consistent decision in code."""
from reviewer.schema import CRITERIA, ReviewAssessment, ReviewResult


def expected_targets(review_input: dict) -> dict[str, set[str]]:
    report = review_input["analyst_report"]
    return {
        "market_insight": {i["insight_id"] for i in report["market_insights"]},
        "recommendation": {r["recommendation_id"] for r in report["recommendations"]},
        "competitor": {c["company"] for c in report["competitor_comparison"]},
    }


def finalize_review(assessment: ReviewAssessment, review_input: dict, run: dict) -> ReviewResult:
    if run.get('evidence_policy') == 'sentence-anchors-and-item-risks-v1':
        from reviewer.evidence import sentence_checks, validate_fact_checks
        from reviewer.schema import item_slots, RiskChecks
        checks = run['evidence_checks']
        validate_fact_checks(checks['fact_checks'], review_input)
        for key, claim in sentence_checks(review_input).items():
            if checks['fact_checks'][key]['verdict'] != 'supported' and not any(
                i.severity == 'blocking' and i.target_type == 'market_insight' and claim['insight_id'] in i.target_ids
                and claim['claim'] in i.problem for i in assessment.issues):
                raise ValueError('A failed sentence check cannot be omitted from blocking issues')
        slots = item_slots(review_input)
        if set(checks['risk_checks']) != set(slots):
            raise ValueError('Every item requires risk checks')
        categories = {'chronology': 'temporal_context', 'geography': 'geography', 'causality': 'causality', 'company_constraints': 'company_fit'}
        for slot, risks in checks['risk_checks'].items():
            for name, risk in RiskChecks.model_validate(risks).model_dump().items():
                kind, target = slots[slot]
                if risk['status'] == 'issue' and not any(i.severity == 'blocking' and i.target_type == kind
                    and target in i.target_ids and i.category == categories[name] for i in assessment.issues):
                    raise ValueError('A failed risk check cannot be omitted from blocking issues')
    upstream = review_input["upstream_handoff"]
    researcher = upstream["researcher_output"]
    targets = expected_targets(review_input)
    findings = {f["finding_id"] for f in researcher["evidence_pack"]["findings"]}
    paragraphs = {(a["article_id"], p["paragraph_id"]) for a in researcher["sources"]
                  if a["availability"] == "full_text" for p in a["paragraphs"]}
    pages = {p["page_number"] for p in upstream["company_brief"]["pages"] if p["text"].strip()}
    checks = [c.criterion for c in assessment.criteria]
    if len(checks) != len(CRITERIA) or set(checks) != set(CRITERIA):
        raise ValueError("Review must check each of the four criteria once")
    issues = {i.issue_id: i for i in assessment.issues}
    if len(issues) != len(assessment.issues):
        raise ValueError("Duplicate review issue IDs")
    for issue in assessment.issues:
        if not issue.problem.strip() or not issue.required_correction.strip():
            raise ValueError("Issue must explain the problem and required correction")
        if issue.target_type == "report":
            if issue.target_ids:
                raise ValueError("Report-level issue must not invent a target ID")
        elif not issue.target_ids or not set(issue.target_ids) <= targets[issue.target_type]:
            raise ValueError("Issue references unknown or missing Analyst target")
        if not set(issue.evidence.finding_ids) <= findings:
            raise ValueError("Review references unknown Researcher finding")
        if any((c.article_id, c.paragraph_id) not in paragraphs for c in issue.evidence.citations):
            raise ValueError("Review references unknown or unavailable source paragraph")
        if not set(issue.brief_pages) <= pages:
            raise ValueError("Review references unknown company brief page")
    for check in assessment.criteria:
        expected = {i.issue_id for i in assessment.issues if i.criterion == check.criterion}
        if set(check.issue_ids) != expected:
            raise ValueError("Criterion check omits or misattributes an issue")
    expected_items = {(kind, item_id) for kind, ids in targets.items() for item_id in ids}
    actual_items = [(item.target_type, item.target_id) for item in assessment.reviewed_items]
    if len(actual_items) != len(expected_items) or set(actual_items) != expected_items:
        raise ValueError("Reviewer must inspect every Analyst insight, recommendation and competitor once")
    for item in assessment.reviewed_items:
        relevant = {i.issue_id for i in assessment.issues
                    if i.target_type == item.target_type and item.target_id in i.target_ids}
        if set(item.issue_ids) != relevant:
            raise ValueError("Reviewed item omits or misattributes an issue")
        blocking = any(issues[i].severity == "blocking" for i in relevant)
        if blocking != (item.disposition == "needs_correction"):
            raise ValueError("Item disposition conflicts with its blocking issues")
    preflight = review_input["structural_preflight_error"]
    if preflight and not any(i.severity == "blocking" and i.category == "structural" for i in assessment.issues):
        raise ValueError("Structural preflight failure cannot be approved by the Reviewer")
    verdicts = {criterion: "fail" if any(i.severity == "blocking" and i.criterion == criterion
                                        for i in assessment.issues) else "pass" for criterion in CRITERIA}
    failed = "fail" in verdicts.values()
    return ReviewResult(
        company_name=upstream["company_brief"]["company_name"],
        research_question=researcher["evidence_pack"]["question"], as_of_date=upstream["as_of_date"],
        overall_verdict="fail" if failed else "pass",
        publication_status="hold_for_human_review" if failed else "review_passed",
        criterion_verdicts=verdicts, assessment=assessment, structural_preflight_error=preflight,
        input_hashes=review_input["input_hashes"], run=run,
    )
