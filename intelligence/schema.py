"""Company-neutral contracts; frozen article and citation formats are reused."""
from datetime import date
from typing import Literal
from pydantic import Field, field_validator
from researcher.schema import StrictModel, Article, Citation, ArticleAssessment

class Query(StrictModel):
    question: str = Field(min_length=1)
    companies: list[str] = Field(default_factory=list)
    as_of_date: date
    period: str | None = None
    company_context: dict[str, str] = Field(default_factory=dict)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value

    @field_validator("companies")
    @classmethod
    def unique_names(cls, values):
        if any(not c.strip() for c in values) or len(set(values)) != len(values):
            raise ValueError("Company names must be nonblank and unique")
        return values

class ResearchTask(StrictModel):
    task_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    evidence_requirements: list[str] = Field(min_length=1)
    preferred_source_types: list[str] = Field(min_length=1)
    suggested_search_queries: list[str]
    completion_criteria: list[str] = Field(min_length=1)

class ResearchPlan(StrictModel):
    question: str
    as_of_date: date
    period: str | None
    companies: list[str] = Field(min_length=1)
    tasks: list[ResearchTask] = Field(min_length=1)
    limitations: list[str]

class Finding(StrictModel):
    finding_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    publication_date: date
    companies: list[str]
    dimension: str
    task_ids: list[str] = Field(min_length=1)
    attribution: str
    effectiveness: Literal["not_measured", "reported_association"]
    limitations: str
    citations: list[Citation] = Field(min_length=1)

class ResearchBatch(StrictModel):
    article_assessments: list[ArticleAssessment]
    findings: list[Finding]
    limitations: list[str]

class TaskCoverage(StrictModel):
    task_id: str
    finding_ids: list[str]
    gap: str

class CompanyCoverage(StrictModel):
    company: str
    finding_ids: list[str]
    gap: str

class EvidencePack(ResearchBatch):
    question: str
    task_coverage: list[TaskCoverage]
    company_coverage: list[CompanyCoverage]
    sources: list[Article]

class EvidenceReference(StrictModel):
    finding_ids: list[str]
    citations: list[Citation]

class Insight(StrictModel):
    insight_id: str = Field(min_length=1)
    task_ids: list[str] = Field(min_length=1)
    observed_fact: str = Field(min_length=1)
    interpretation: str
    evidence: EvidenceReference
    context_keys: list[str]
    uncertainty: str

class Recommendation(StrictModel):
    recommendation_id: str = Field(min_length=1)
    task_ids: list[str] = Field(min_length=1)
    action: str
    rationale: str
    decision_status: Literal["recommend", "propose_test", "needs_evidence"]
    insight_ids: list[str]
    context_keys: list[str]
    next_evidence: str

class AnswerComponent(StrictModel):
    task_id: str
    insight_ids: list[str]
    gap: str

class AnalystReport(StrictModel):
    question: str
    companies: list[str]
    as_of_date: date
    headline_insight_ids: list[str]
    insights: list[Insight]
    recommendations: list[Recommendation]
    answer_components: list[AnswerComponent]
    limitations: list[str]

class Anchor(Citation):
    excerpt: str = Field(min_length=10)

class RiskCheck(StrictModel):
    criterion: Literal["chronology", "geography", "causality", "company_constraints"]
    status: Literal["clear", "issue", "not_applicable"]
    explanation: str = Field(min_length=1)

class ItemReview(StrictModel):
    target_type: Literal["insight", "recommendation", "task"]
    target_id: str
    disposition: Literal["supported", "qualified", "gap_acknowledged", "needs_correction"]
    explanation: str = Field(min_length=1)
    anchors: list[Anchor]
    risks: list[RiskCheck]
    required_correction: str

class ReviewAssessment(StrictModel):
    items: list[ItemReview]
    blocking_issues: list[str]
    limitations: list[str]
