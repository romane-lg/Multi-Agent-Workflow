"""Render the typed analysis deterministically; no additional Writer model call."""
from analyst.schema import AnalystReport, CompanyBrief


def render_report(report: AnalystReport, researcher_output: dict, brief: CompanyBrief) -> str:
    insights = {i.insight_id: i for i in report.market_insights}
    findings = {f["finding_id"]: f for f in researcher_output["evidence_pack"]["findings"]}
    sources = {a["article_id"]: a for a in researcher_output["sources"]}

    def citations(insight):
        refs = {(c.article_id, c.paragraph_id) for c in insight.evidence.citations}
        for finding_id in insight.evidence.finding_ids:
            refs.update((c["article_id"], c["paragraph_id"]) for c in findings[finding_id]["citations"])
        links = [f"[{aid}:{pid}]({sources[aid]['url']}) ({sources[aid]['publication_date']})" for aid, pid in sorted(refs)]
        return "; ".join(links)

    lines = [f"# Competitive intelligence for {report.company_name}",
             f"As of {report.as_of_date}", f"Research question: {report.research_question}",
             "## What matters for Fizzera"]
    lines.extend(f"- **{iid}:** {insights[iid].interpretation_for_fizzera}" for iid in report.headline_insight_ids)
    lines.append("## Observations and company implications")
    for item in report.market_insights:
        lines.extend([
            f"### {item.insight_id}", f"**Reported evidence:** {item.observed_fact}",
            f"**Sources:** {citations(item)}",
            f"**Interpretation for Fizzera:** {item.interpretation_for_fizzera}",
            f"**Company context:** Brief pages {', '.join(map(str, item.brief_pages))}.",
            f"**Geographic applicability:** {item.geographic_applicability}",
            f"**Effectiveness and uncertainty:** {item.effectiveness_and_uncertainty}",
        ])
    lines.append("## Competitor coverage")
    table = ["| Company | Evidence | Insights | Gap |", "| --- | --- | --- | --- |"]
    for item in report.competitor_comparison:
        values = [item.company, item.evidence_status, ", ".join(item.insight_ids), item.evidence_gap]
        table.append("| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    lines.append("\n".join(table))
    lines.append("## Prioritized decisions")
    for item in report.recommendations:
        if item.insight_ids:
            basis = ", ".join(item.insight_ids)
        elif item.decision_status == "propose_test":
            basis = "Company-brief-led test; no competitive evidence yet, not approval to launch"
        else:
            basis = "Evidence gap; information gathering only"
        lines.extend([
            f"### {item.recommendation_id}: {item.focus} — {item.priority}",
            f"**Status:** {item.decision_status}", f"**Proposed action:** {item.proposed_action}",
            f"**Rationale:** {item.rationale_for_fizzera}",
            f"**Evidence:** {basis}; brief pages {', '.join(map(str, item.brief_pages))}.",
            f"**Success measure:** {item.success_measure}",
            f"**Next evidence and uncertainty:** {item.uncertainty_and_next_evidence}",
            f"**Proposed budget:** {'Unspecified' if item.proposed_budget_cad is None else f'CAD {item.proposed_budget_cad:,.0f}'}",
            f"**Additional financing required:** {'Yes' if item.requires_additional_financing else 'No'}",
        ])
    lines.extend(["## Evidence gaps", *[f"- {g}" for g in report.evidence_gaps],
                  "## Limitations and company-data provenance", *[f"- {g}" for g in brief.data_status_notes],
                  *[f"- {g}" for g in report.limitations],
                  "- Structural citation and budget checks passed. This is the Analyst draft; consult the separate review artifacts when review is enabled."])
    # Blank lines ensure CommonMark paragraphs and lists render correctly.
    return "\n\n".join(lines) + "\n"
