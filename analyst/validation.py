"""Structural and budget checks; these are not an independent quality Reviewer."""
import math

from analyst.schema import AnalystReport, CompanyBrief, COMPETITORS, FOCUSES


def validate_report(report: AnalystReport, researcher_output: dict, brief: CompanyBrief, as_of_date: str):
    if report.company_name != brief.company_name or report.research_question != researcher_output["evidence_pack"]["question"]:
        raise ValueError("Analyst changed the company or research question")
    if report.as_of_date != as_of_date:
        raise ValueError("Analyst changed the analysis date")
    findings = {f["finding_id"]: f for f in researcher_output["evidence_pack"]["findings"]}
    source_paragraphs = {
        (a["article_id"], p["paragraph_id"])
        for a in researcher_output["sources"] if a["availability"] == "full_text"
        for p in a["paragraphs"]
    }
    pages = {p.page_number for p in brief.pages if p.text.strip()}
    insights = {i.insight_id: i for i in report.market_insights}
    if not insights or len(insights) != len(report.market_insights):
        raise ValueError("Missing or duplicate insight IDs")

    def check_brief_refs(refs):
        if not refs or not set(refs) <= pages:
            raise ValueError("Missing or unknown company brief page reference")

    for insight in report.market_insights:
        refs = insight.evidence
        if not refs.finding_ids and not refs.citations:
            raise ValueError("Uncited competitive observation")
        if not set(refs.finding_ids) <= findings.keys():
            raise ValueError("Unknown Researcher finding ID")
        if any((c.article_id, c.paragraph_id) not in source_paragraphs for c in refs.citations):
            raise ValueError("Unknown or unavailable source paragraph")
        check_brief_refs(insight.brief_pages)
    if not report.headline_insight_ids or not set(report.headline_insight_ids) <= insights.keys():
        raise ValueError("Headline references unknown or missing insights")
    competitor_names = [c.company for c in report.competitor_comparison]
    if len(competitor_names) != len(COMPETITORS) or set(competitor_names) != set(COMPETITORS):
        raise ValueError("Competitor coverage must include the research and company-brief competitors once")
    for competitor in report.competitor_comparison:
        if not set(competitor.insight_ids) <= insights.keys():
            raise ValueError("Competitor references unknown insight")
        if competitor.evidence_status == "no_evidence" and (competitor.insight_ids or not competitor.evidence_gap.strip()):
            raise ValueError("Missing competitor evidence must remain an explicit gap")
        if competitor.evidence_status == "covered" and not competitor.insight_ids:
            raise ValueError("Covered competitor has no supporting insight")
    ids = [r.recommendation_id for r in report.recommendations]
    if len(ids) != len(set(ids)) or {r.focus for r in report.recommendations} != set(FOCUSES):
        raise ValueError("Recommendations must address all five company priority areas with unique IDs")
    total_budget = 0.0
    launch_budget = 0.0
    chosen_launches = set()
    for recommendation in report.recommendations:
        check_brief_refs(recommendation.brief_pages)
        if not set(recommendation.insight_ids) <= insights.keys():
            raise ValueError("Recommendation references unknown insight")
        if recommendation.decision_status == "recommend" and not recommendation.insight_ids:
            raise ValueError("Strategic recommendation requires competitive evidence")
        if recommendation.decision_status == "propose_test" and not recommendation.uncertainty_and_next_evidence.strip():
            raise ValueError("Proposed test must identify uncertainty and next evidence")
        budget = recommendation.proposed_budget_cad
        if budget is not None:
            if not math.isfinite(budget) or budget < 0:
                raise ValueError("Budget must be finite and nonnegative")
            if not recommendation.requires_additional_financing:
                total_budget += budget
                if recommendation.focus == "product_launch":
                    launch_budget += budget
        if recommendation.launch_concept not in (None, "postpone"):
            if recommendation.focus != "product_launch":
                raise ValueError("Launch concept belongs only to the product decision")
            chosen_launches.add(recommendation.launch_concept)
    if len(chosen_launches) > 1:
        raise ValueError("Company brief permits only one major launch")
    if brief.investment_envelope_cad is not None and total_budget > brief.investment_envelope_cad:
        raise ValueError("Recommendations exceed the company investment envelope")
    if brief.product_launch_budget_cad is not None and launch_budget > brief.product_launch_budget_cad:
        raise ValueError("Recommendations exceed the product launch budget")
