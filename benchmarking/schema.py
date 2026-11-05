"""Strict contracts for benchmark releases, experiments and independent annotations."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StrictInt, model_validator

class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

class ReferenceSource(Model):
    source_id: str = Field(min_length=1)
    url: HttpUrl
    retrieved_at: datetime
    snapshot_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

class ReferenceFact(Model):
    fact_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_id: str
    excerpt: str = Field(min_length=1)

class AnswerComponent(Model):
    component_id: str = Field(min_length=1)
    requirement: str = Field(min_length=1)
    reference_fact_ids: list[str]

class Verification(Model):
    verified_by: str = Field(min_length=1)
    verified_at: datetime
    notes: str = Field(min_length=1)

class BenchmarkTask(Model):
    task_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    category: Literal["A", "B", "C", "D"]
    question: str = Field(min_length=1)
    companies: list[str] = Field(min_length=1)
    as_of_date: date
    period: str
    expected_components: list[AnswerComponent] = Field(min_length=1)
    allowed_source_types: list[str] = Field(min_length=1)
    reference_facts: list[ReferenceFact]
    reference_sources: list[ReferenceSource]
    difficulty: Literal["easy", "medium", "hard"]
    known_challenges: list[str]
    verification_status: Literal["draft", "verified"]
    verification: Verification | None = None
    input_snapshot: str | None = None
    input_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def references(self):
        def unique(values):
            return len(values) == len(set(values))
        if not unique(self.companies) or any(not s.strip() for s in self.companies):
            raise ValueError("Company names must be nonblank and unique")
        if not self.question.strip():
            raise ValueError("Blank benchmark question")
        if not unique([c.component_id for c in self.expected_components]):
            raise ValueError("Duplicate required component IDs")
        if not unique([s.source_id for s in self.reference_sources]):
            raise ValueError("Duplicate reference source IDs")
        if not unique([f.fact_id for f in self.reference_facts]):
            raise ValueError("Duplicate reference fact IDs")
        sources = {s.source_id for s in self.reference_sources}
        facts = {f.fact_id for f in self.reference_facts}
        if any(f.source_id not in sources for f in self.reference_facts):
            raise ValueError("Reference fact has unknown source")
        if any(not set(c.reference_fact_ids) <= facts for c in self.expected_components):
            raise ValueError("Component references an unknown fact")
        if self.verification_status == "verified":
            if not self.verification or not self.reference_sources or not self.reference_facts:
                raise ValueError("Verified task needs human attestation and reference evidence")
            if any(not c.reference_fact_ids for c in self.expected_components):
                raise ValueError("Every verified component needs reference facts")
            if not self.input_snapshot or not self.input_sha256:
                raise ValueError("Verified task needs a hashed input snapshot")
        return self

class Benchmark(Model):
    schema_version: Literal["ci-benchmark-v1"] = "ci-benchmark-v1"
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    status: Literal["draft", "frozen"]
    created_at: datetime
    description: str
    tasks: list[BenchmarkTask] = Field(min_length=1)
    sha256: str | None = None

    @model_validator(mode="after")
    def release(self):
        if len({t.task_id for t in self.tasks}) != len(self.tasks):
            raise ValueError("Duplicate benchmark task IDs")
        if self.status == "frozen" and (
                any(t.verification_status != "verified" for t in self.tasks) or not self.sha256):
            raise ValueError("Frozen benchmark requires verified tasks and a checksum")
        return self

STAGES = {"planner", "researcher", "analyst", "reviewer"}

class ExperimentConfig(Model):
    benchmark_version: str
    architecture_version: Literal["sequential_v1"] = "sequential_v1"
    task_ids: list[str] | None = None
    repetitions: int = Field(default=1, ge=1, le=100)
    batch_size: int = Field(default=5, ge=1, le=5)
    models: dict[str, str] = Field(default_factory=lambda: {
        "planner": "gpt-4o-mini", "researcher": "gpt-4o-mini",
        "analyst": "gpt-4.1", "reviewer": "gpt-4.1"})
    temperature: Literal[0] = 0
    seed: None = None
    tools: Literal["disabled"] = "disabled"

    @model_validator(mode="after")
    def settings(self):
        if set(self.models) != STAGES or any(not m.strip() for m in self.models.values()):
            raise ValueError("Configure all four agent models explicitly")
        if self.task_ids is not None and (
                not self.task_ids or len(set(self.task_ids)) != len(self.task_ids)):
            raise ValueError("Task selection must be nonempty and unique")
        return self

class TokenPrice(Model):
    input_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_per_million: float = Field(ge=0, allow_inf_nan=False)
    cached_input_per_million: float | None = Field(default=None, ge=0, allow_inf_nan=False)

class Pricing(Model):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    pricing_version: str = Field(min_length=1)
    effective_date: date | None
    models: dict[str, TokenPrice]

    @model_validator(mode="after")
    def dated_prices(self):
        if self.models and self.effective_date is None:
            raise ValueError("Configured prices require an effective date")
        return self

class ClaimAnnotation(Model):
    claim_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    text: str = Field(min_length=1)
    accuracy: Literal["correct", "incorrect", "unverifiable"]
    support: Literal["supported", "unsupported", "unverifiable"]
    evidence_notes: str = Field(min_length=1)
    reference_fact_ids: list[str] = Field(default_factory=list)

class ComponentAnnotation(Model):
    component_id: str
    verdict: Literal["correct", "incorrect", "missing", "unverifiable"]
    notes: str = Field(min_length=1)

class VerifiedError(Model):
    error_id: str = Field(min_length=1)
    category: Literal["incorrect_claim", "unsupported_claim", "missing_component", "other"]
    description: str = Field(min_length=1)
    claim_id: str | None = None
    component_id: str | None = None
    evidence_notes: str = Field(min_length=1)

class ReviewerFlag(Model):
    flag_id: str = Field(min_length=1)
    reviewer_type: Literal["ai", "human"]
    description: str = Field(min_length=1)
    matched_error_id: str | None
    verification_notes: str = Field(min_length=1)

class RecoveryCase(Model):
    case_id: str
    target_error_ids: list[str] = Field(min_length=1)
    resolved_error_ids: list[str]
    verified_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def resolved_targets(self):
        if not set(self.resolved_error_ids) <= set(self.target_error_ids):
            raise ValueError("Resolved recovery errors must be target errors")
        return self

CRITERIA = {"factual_accuracy", "task_completeness", "evidence_quality",
            "claim_support", "clarity_usefulness"}

class IndependentEvaluation(Model):
    evaluation_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    run_id: str
    task_id: str
    architecture_version: Literal["sequential_v1", "targeted_recovery_v2", "human_reviewer_v3"]
    report_stage: Literal["initial", "final", "pre_recovery", "post_recovery"]
    report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    benchmark_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    evaluator_id: str = Field(min_length=1)
    evaluator_type: Literal["human"] = "human"
    independent_of_internal_reviewer: Literal[True] = True
    evaluated_at: datetime
    scores: dict[str, StrictInt]
    criterion_comments: dict[str, str]
    comments: str
    claim_inventory_complete: bool
    error_inventory_complete: bool
    component_inventory_complete: bool
    claims: list[ClaimAnnotation]
    components: list[ComponentAnnotation]
    verified_errors: list[VerifiedError]
    reviewer_flags: list[ReviewerFlag]
    recovery_cases: list[RecoveryCase] = Field(default_factory=list)
    pre_recovery_errors: int | None = Field(default=None, ge=0)
    post_recovery_errors: int | None = Field(default=None, ge=0)
    review_time_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def annotations(self):
        if set(self.scores) != CRITERIA or any(not 0 <= s <= 4 for s in self.scores.values()):
            raise ValueError("All five independent scores must be integers from 0 to 4")
        if set(self.criterion_comments) != CRITERIA:
            raise ValueError("Comments are required for each criterion")
        for collection, key in ((self.claims, "claim_id"), (self.components, "component_id"),
                                (self.verified_errors, "error_id"), (self.reviewer_flags, "flag_id"),
                                (self.recovery_cases, "case_id")):
            ids = [getattr(x, key) for x in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate annotation IDs")
        claims = {c.claim_id for c in self.claims}
        components = {c.component_id for c in self.components}
        errors = {e.error_id for e in self.verified_errors}
        for e in self.verified_errors:
            if e.claim_id is not None and e.claim_id not in claims:
                raise ValueError("Verified error references unknown claim")
            if e.component_id is not None and e.component_id not in components:
                raise ValueError("Verified error references unknown component")
        if any(f.matched_error_id is not None and f.matched_error_id not in errors for f in self.reviewer_flags):
            raise ValueError("Reviewer flag references an unverified error")
        if (self.pre_recovery_errors is None) != (self.post_recovery_errors is None):
            raise ValueError("Provide both pre/post counts or neither")
        if self.architecture_version == "sequential_v1" and (
                self.recovery_cases or self.pre_recovery_errors is not None):
            raise ValueError("Sequential baseline cannot contain recovery measurements")
        return self
