"""Paired architecture contracts; original benchmark release schema is unchanged."""
from datetime import datetime
from typing import Literal
from pydantic import Field, model_validator
from benchmarking.schema import Model, ExperimentConfig
from intelligence.schema import AnalystReport, Recommendation, ItemReview, ReviewAssessment

MAX_RETRIES = 1
VERSIONS = {
    "sequential_v1": {"reviewer_type": "ai", "recovery_enabled": False, "max_retries": 0},
    "targeted_recovery_v2": {"reviewer_type": "ai", "recovery_enabled": True, "max_retries": 1},
    "human_reviewer_v3": {"reviewer_type": "human", "recovery_enabled": False, "max_retries": 0}}
FOCUSES = ("ontario_retail", "pricing", "product_launch", "marketing", "bc_expansion")
class FizzeraRecommendation(Recommendation):
    focus: Literal["ontario_retail", "pricing", "product_launch", "marketing", "bc_expansion"]
    proposed_budget_cad: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    requires_additional_financing: bool = False
    launch_concept: Literal["Vanilla Cola", "Tropical Mango", "Ginger Lime", "postpone"] | None = None

class FizzeraReport(AnalystReport):
    recommendations: list[FizzeraRecommendation]

class ExperimentalItemReview(ItemReview):
    failure_type: Literal["missing_information", "unsupported_claim", "contradictory_evidence",
        "chronology", "geography", "company_constraints", "invalid_source", "grammar", "formatting"] | None = None
    severity: Literal["advisory", "high", "critical"] = "advisory"
    target_agent: Literal["researcher", "analyst"] | None = None
    information_status: Literal["available", "missing", "unavailable"] = "available"

class ExperimentalReview(ReviewAssessment):
    items: list[ExperimentalItemReview]

class Snapshot(Model):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

class PairedConfig(ExperimentConfig):
    brief: Snapshot
    supplemental_evidence: dict[str, Snapshot] = Field(default_factory=dict)
    presentation_models: dict[str, str] = Field(default_factory=lambda: {
        "executive": "gpt-4.1", "editorial_auditor": "gpt-4.1"})

    @model_validator(mode="after")
    def presentation_settings(self):
        if set(self.presentation_models) != {"executive", "editorial_auditor"}:
            raise ValueError("Explicit editor and final-auditor model settings are required")
        return self

class Resolution(Model):
    status: Literal["resolved", "unresolved", "disputed"]
    explanation: str = Field(min_length=1)

class HumanSubmission(Model):
    packet_id: str
    pair_id: str
    report_sha256: str
    evidence_sha256: str
    reviewer_id: str = Field(min_length=1)
    started_at: datetime
    ended_at: datetime
    verdict: Literal["pass", "fail"]
    assessment: ExperimentalReview
    hourly_rate: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    labor_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def time_and_labor(self):
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None or self.ended_at < self.started_at:
            raise ValueError("Human review needs timezone-aware start/end times in order")
        if (self.hourly_rate is None) != (self.labor_currency is None):
            raise ValueError("Supply both labor rate and currency or neither")
        if not self.reviewer_id.strip():
            raise ValueError("Human reviewer identity is required")
        return self
