"""Readable review report without a Writer call or changes to the Analyst draft."""
from reviewer.schema import ReviewResult


def render_review(result: ReviewResult, review_input: dict) -> str:
    upstream = review_input["upstream_handoff"]["researcher_output"]
    sources = {a["article_id"]: a for a in upstream["sources"]}
    findings = {f["finding_id"]: f for f in upstream["evidence_pack"]["findings"]}
    lines = [
        f"# Independent review for {result.company_name}",
        f"**Verdict: {result.overall_verdict.upper()}** — {result.publication_status}",
        f"Analysis date: {result.as_of_date}",
        ("This reviews the Analyst's saved revision after one correction cycle. The Reviewer makes no further edits."
         if "revision_feedback" in review_input else
         "The Analyst draft is unchanged. Required corrections below have not been executed."),
        "## Criteria",
    ]
    table = ["| Criterion | Verdict | Issues |", "| --- | --- | --- |"]
    for check in result.assessment.criteria:
        table.append(f"| {check.criterion} | {result.criterion_verdicts[check.criterion]} | {', '.join(check.issue_ids) or 'None'} |")
    lines.append("\n".join(table))
    for check in result.assessment.criteria:
        lines.append(f"**{check.criterion}:** {check.explanation}")
    lines.append("## Issues and requested corrections")
    if not result.assessment.issues:
        lines.append("The Reviewer identified no blocking or advisory issues in this pass.")
    for issue in result.assessment.issues:
        refs = {(c.article_id, c.paragraph_id) for c in issue.evidence.citations}
        for finding_id in issue.evidence.finding_ids:
            refs.update((c["article_id"], c["paragraph_id"]) for c in findings[finding_id]["citations"])
        links = [f"[{aid}:{pid}]({sources[aid]['normalized_url'] if 'normalized_url' in sources[aid] else sources[aid]['url']}) ({sources[aid]['publication_date']})"
                 for aid, pid in sorted(refs)]
        lines.extend([
            f"### {issue.issue_id}: {issue.severity} — {issue.category}",
            f"**Criterion:** {issue.criterion}",
            f"**Affected item:** {issue.target_type}: {', '.join(issue.target_ids) or 'whole report'}",
            f"**Problem:** {issue.problem}",
            f"**Relevant source evidence:** {'; '.join(links) or 'No supporting source identified; see the stated evidence gap.'}",
            f"**Company brief pages:** {', '.join(map(str, issue.brief_pages)) or 'Not applicable'}",
            f"**Required correction:** {issue.required_correction}",
        ])
    lines.append("## Item coverage")
    table = ["| Type | Item | Assessment | Issues |", "| --- | --- | --- | --- |"]
    for item in result.assessment.reviewed_items:
        values = [item.target_type, item.target_id, item.disposition, ", ".join(item.issue_ids) or "None"]
        table.append("| " + " | ".join(v.replace("|", "\\|") for v in values) + " |")
    lines.append("\n".join(table))
    for item in result.assessment.reviewed_items:
        if item.explanation:
            lines.append(f"**{item.target_type} {item.target_id}:** {item.explanation}")
    lines.append("## Limitations")
    lines.extend(f"- {note}" for note in result.assessment.limitations)
    lines.append("- The Reviewer is a separate model assessment, not ground truth. This review makes no edits and performs no additional research.")
    lines.append(f"Analyst input SHA256: `{result.input_hashes['analyst_report_sha256']}`")
    return "\n\n".join(lines) + "\n"
