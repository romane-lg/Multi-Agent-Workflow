from typing import Literal

from pydantic import Field, create_model

from analyst.schema import EvidenceReference
from researcher.schema import StrictModel


CRITERIA = ("source_support", "interpretation", "company_fit", "completeness")
TargetType = Literal["market_insight", "recommendation", "competitor"]
Criterion = Literal["source_support", "interpretation", "company_fit", "completeness"]


class ReviewIssue(StrictModel):
    issue_id: str
    severity: Literal["blocking", "advisory"]
    criterion: Criterion
    category: Literal[
        "unsupported_claim", "citation_mismatch", "metric_context", "causality",
        "temporal_context", "geography", "company_fit", "budget_or_capacity",
        "coverage", "assumption_status", "incomplete_answer", "structural",
    ]
    target_type: Literal["market_insight", "recommendation", "competitor", "report"]
    target_ids: list[str]
    problem: str
    evidence: EvidenceReference
    brief_pages: list[int]
    required_correction: str


class CriterionCheck(StrictModel):
    criterion: Criterion
    explanation: str
    issue_ids: list[str]


class ReviewedItem(StrictModel):
    target_type: TargetType
    target_id: str
    disposition: Literal["supported", "qualified", "needs_correction", "gap_acknowledged"]
    issue_ids: list[str]
    explanation: str = ""


class ReviewAssessment(StrictModel):
    criteria: list[CriterionCheck]
    reviewed_items: list[ReviewedItem]
    issues: list[ReviewIssue]
    limitations: list[str]


class ReviewResult(StrictModel):
    company_name: str
    research_question: str
    as_of_date: str
    overall_verdict: Literal["pass", "fail"]
    publication_status: Literal["review_passed", "hold_for_human_review"]
    criterion_verdicts: dict[str, Literal["pass", "fail"]]
    assessment: ReviewAssessment
    structural_preflight_error: str | None
    input_hashes: dict[str, str]
    run: dict


class LocalIssue(StrictModel):
    severity: Literal["blocking", "advisory"]
    criterion: Criterion
    category: Literal[
        "unsupported_claim", "citation_mismatch", "metric_context", "causality",
        "temporal_context", "geography", "company_fit", "budget_or_capacity",
        "coverage", "assumption_status", "incomplete_answer", "structural",
    ]
    problem: str
    evidence: EvidenceReference
    brief_pages: list[int]
    required_correction: str


class ItemDecision(StrictModel):
    explanation: str
    issues: list[LocalIssue]


class CriterionExplanations(StrictModel):
    source_support: str
    interpretation: str
    company_fit: str
    completeness: str


class FeedbackResolution(StrictModel):
    status: Literal["resolved", "unresolved", "disputed"]
    explanation: str


def item_slots(review_input: dict) -> dict[str, tuple[str, str]]:
    report = review_input["analyst_report"]
    items = [("market_insight", i["insight_id"]) for i in report["market_insights"]]
    items += [("recommendation", r["recommendation_id"]) for r in report["recommendations"]]
    items += [("competitor", c["company"]) for c in report["competitor_comparison"]]
    return {f"check_{i:03d}": item for i, item in enumerate(items, 1)}


def build_review_response_model(review_input: dict):
    # Required object fields prevent an otherwise valid response from silently
    # omitting recommendation or competitor checks in an open-ended list.
    fields = {slot: (ItemDecision, Field(description=f"Review {kind} {item_id}"))
              for slot, (kind, item_id) in item_slots(review_input).items()}
    checks = create_model("RequiredItemChecks", __base__=StrictModel, **fields)
    extra = {}
    if "revision_feedback" in review_input:
        resolutions = create_model("RequiredFeedbackResolutions", __base__=StrictModel,
            **{i["issue_id"]: (FeedbackResolution, ...) for i in review_input["revision_feedback"]["selected_issues"]})
        extra["feedback_resolution"] = (resolutions, ...)
    return create_model("CompleteReviewResponse", __base__=StrictModel,
                        criteria=(CriterionExplanations, ...), item_reviews=(checks, ...),
                        report_issues=(list[LocalIssue], ...), limitations=(list[str], ...), **extra)


def normalize_assessment(generated: dict, review_input: dict) -> ReviewAssessment:
    if "item_reviews" in generated:
        slots = item_slots(review_input)
        if set(generated["item_reviews"]) != set(slots):
            raise ValueError("Required per-item review slots are missing or unknown")
        issues = []
        items = []

        def add_issues(local_issues, kind, target_ids):
            ids = []
            for issue in local_issues:
                issue_id = f"issue_{len(issues) + 1:03d}"
                issues.append({**issue, "issue_id": issue_id, "target_type": kind, "target_ids": target_ids})
                ids.append(issue_id)
            return ids

        for slot, (kind, item_id) in slots.items():
            decision = generated["item_reviews"][slot]
            if not decision["explanation"].strip():
                raise ValueError("Each item review needs an explanation")
            ids = add_issues(decision["issues"], kind, [item_id])
            if any(i["severity"] == "blocking" for i in decision["issues"]):
                disposition = "needs_correction"
            elif decision["issues"]:
                disposition = "qualified"
            elif kind == "competitor" and next(c for c in review_input["analyst_report"]["competitor_comparison"] if c["company"] == item_id)["evidence_status"] == "no_evidence":
                disposition = "gap_acknowledged"
            elif kind == "recommendation" and next(r for r in review_input["analyst_report"]["recommendations"] if r["recommendation_id"] == item_id)["decision_status"] == "needs_evidence":
                disposition = "gap_acknowledged"
            else:
                disposition = "supported"
            items.append({"target_type": kind, "target_id": item_id, "disposition": disposition,
                          "issue_ids": ids, "explanation": decision["explanation"]})
        add_issues(generated["report_issues"], "report", [])
        return ReviewAssessment.model_validate({
            "criteria": [{"criterion": c, "explanation": generated["criteria"][c],
                          "issue_ids": [i["issue_id"] for i in issues if i["criterion"] == c]} for c in CRITERIA],
            "reviewed_items": items, "issues": issues, "limitations": generated["limitations"],
        })
    value = dict(generated)
    return ReviewAssessment.model_validate(value)
