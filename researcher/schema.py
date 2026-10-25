from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QUESTION = (
    "What is happening in the functional soda market, how are Olipop, Poppi, "
    "Culture Pop, and Zevia competing, and what evidence shows which strategies are working?"
)
COMPANIES = ("Olipop", "Poppi", "Culture Pop", "Zevia")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Paragraph(StrictModel):
    paragraph_id: str
    text: str


class Article(StrictModel):
    article_id: str
    title: str
    url: str
    publication_date: str
    availability: Literal["full_text", "unavailable"]
    access_note: str
    text_sha256: str
    paragraphs: list[Paragraph]
    retrieval_method: Literal["http_extractor", "public_web_reader", "manual_import", "browser_rendered"] = "http_extractor"
    retrieved_at: str | None = None


class Citation(StrictModel):
    article_id: str
    paragraph_id: str


class Finding(StrictModel):
    finding_id: str
    claim: str = Field(description="One short factual finding, with attribution and time context.")
    publication_date: str = Field(description="Exact ISO publication date of the cited article; not the event date.")
    companies: list[Literal["Olipop", "Poppi", "Culture Pop", "Zevia", "Cove Soda", "Crazy D's", "PepsiCo", "other"]]
    dimension: Literal["products", "pricing", "retail", "marketing", "business", "consumers", "market"]
    evidence_type: Literal["market_development", "competitor_action", "reported_outcome", "executive_opinion"]
    attribution: str
    effectiveness: Literal["not_measured", "reported_association"] = Field(
        description="This article-summary pilot cannot establish causality. Measured outcomes are reported associations."
    )
    limitations: str
    citations: list[Citation]


class ArticleAssessment(StrictModel):
    article_id: str
    relevance: Literal["high", "limited", "irrelevant", "unavailable"]
    summary: str = Field(description="A substantive research brief preserving relevant actions, context, metrics, and uncertainty. Shorter when relevance is limited.")
    reason: str


class Coverage(StrictModel):
    company: Literal["Olipop", "Poppi", "Culture Pop", "Zevia"]
    finding_ids: list[str]
    gap: str


class EvidencePack(StrictModel):
    question: str
    article_assessments: list[ArticleAssessment]
    findings: list[Finding]
    company_coverage: list[Coverage]
    limitations: list[str]
