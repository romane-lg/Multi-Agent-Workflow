from typing import Literal

from researcher.schema import Citation, StrictModel


COMPETITORS = ("Olipop", "Poppi", "Culture Pop", "Zevia", "Cove Soda", "Crazy D's")
FOCUSES = ("ontario_retail", "pricing", "product_launch", "marketing", "bc_expansion")


class BriefPage(StrictModel):
    page_number: int
    text: str


class CompanyBrief(StrictModel):
    company_name: str
    source_filename: str
    pdf_sha256: str
    text_sha256: str
    pages: list[BriefPage]
    data_status_notes: list[str]
    investment_envelope_cad: float | None
    product_launch_budget_cad: float | None


class EvidenceReference(StrictModel):
    finding_ids: list[str]
    citations: list[Citation]


class Insight(StrictModel):
    insight_id: str
    observed_fact: str
    evidence: EvidenceReference
    interpretation_for_fizzera: str
    brief_pages: list[int]
    geographic_applicability: str
    effectiveness_and_uncertainty: str


class CompetitorView(StrictModel):
    company: str
    evidence_status: Literal["covered", "no_evidence"]
    insight_ids: list[str]
    evidence_gap: str


class Recommendation(StrictModel):
    recommendation_id: str
    focus: Literal["ontario_retail", "pricing", "product_launch", "marketing", "bc_expansion"]
    priority: Literal["critical", "high", "medium"]
    decision_status: Literal["recommend", "propose_test", "needs_evidence"]
    proposed_action: str
    rationale_for_fizzera: str
    insight_ids: list[str]
    brief_pages: list[int]
    success_measure: str
    uncertainty_and_next_evidence: str
    proposed_budget_cad: float | None
    requires_additional_financing: bool
    launch_concept: Literal["Vanilla Cola", "Tropical Mango", "Ginger Lime", "postpone"] | None


class AnalystReport(StrictModel):
    company_name: str
    research_question: str
    as_of_date: str
    headline_insight_ids: list[str]
    market_insights: list[Insight]
    competitor_comparison: list[CompetitorView]
    recommendations: list[Recommendation]
    evidence_gaps: list[str]
    limitations: list[str]
