"""Freeze a reviewed analysis and preserve the actual approval state."""
import json
from pathlib import Path

from reviewer.handoff import digest, make_review_input
from reviewer.schema import ReviewResult
from reviewer.validation import finalize_review


def make_executive_input(analysis_run: Path, review_dir: Path):
    current, context = make_review_input(analysis_run)
    if current["structural_preflight_error"]:
        raise ValueError("Repair the structurally invalid Analyst report before presentation")
    frozen = json.loads((review_dir / "review_input.json").read_text())
    review = ReviewResult.model_validate_json((review_dir / "review_report.json").read_text())
    if any(frozen.get(k) != current[k] for k in ("analyst_report", "upstream_handoff", "structural_preflight_error")):
        raise ValueError("Review does not belong to the exact analysis and evidence being presented")
    if any(frozen.get("input_hashes", {}).get(k) != value for k, value in current["input_hashes"].items()):
        raise ValueError("Review input hashes do not match the current draft")
    if review.input_hashes != frozen["input_hashes"]:
        raise ValueError("Saved review/input hash mismatch")
    if finalize_review(review.assessment, frozen, review.run).model_dump() != review.model_dump():
        raise ValueError("Saved review verdict is inconsistent with its issues")
    status = review.publication_status
    unresolved = []
    if (analysis_run / "revision_lineage.json").exists():
        lineage = json.loads((analysis_run / "revision_lineage.json").read_text())
        revision_input = json.loads((analysis_run / "revision_input.json").read_text())
        if digest(revision_input) != lineage["revision_input_sha256"]:
            raise ValueError("Revision input hash mismatch")
        feedback = frozen.get("revision_feedback")
        if not feedback or digest(feedback) != frozen["input_hashes"].get("revision_feedback_sha256"):
            raise ValueError("Revision requires a verified feedback recheck")
        if feedback["selected_issues"] != revision_input["selected_issues"] or feedback["original_report"] != revision_input["original_review_input"]["analyst_report"]:
            raise ValueError("Recheck feedback does not match the correction lineage")
        resolutions = review.run.get("feedback_resolution", {})
        if set(resolutions) != {i["issue_id"] for i in revision_input["selected_issues"]}:
            raise ValueError("Recheck has missing feedback resolutions")
        unresolved = [i["issue_id"] for i in revision_input["selected_issues"]
                      if i["severity"] == "blocking" and resolutions[i["issue_id"]]["status"] != "resolved"]
        if unresolved:
            status = "hold_for_human_review"
    payload = {
        "schema_version": "reviewed-analysis-to-executive-v1",
        "analysis": current, "review": review.model_dump(), "publication_status": status,
        "unresolved_blocking_feedback": unresolved,
        "review_dir": str(review_dir.resolve()),
    }
    payload["executive_input_sha256"] = digest(payload)
    # Keep the complete review in the frozen artifact, but avoid repeating its
    # fallible assertions beside source facts in the editor's working context.
    # The editor receives issue targets/categories, not a second competing summary.
    context = json.dumps({
        "company_planning_context": current["upstream_handoff"]["company_brief"],
        "analyst_draft_unverified": current["analyst_report"],
        "review_state": {"publication_status": status, "unresolved_blocking_feedback": unresolved,
            "issues": [{"severity": i.severity, "category": i.category,
                        "target_type": i.target_type, "target_ids": i.target_ids}
                       for i in review.assessment.issues]},
        "original_sources_check_these_before_repeating_draft_claims": current["upstream_handoff"]["researcher_output"]["sources"],
    }, ensure_ascii=False, indent=2)
    return payload, context
