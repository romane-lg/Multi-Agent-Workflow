"""Formatting and reference contracts; these do not establish factual accuracy."""
import re
from executive.schema import ExecutiveBrief, TITLES


def word_count(text: str) -> int:
    return len(text.split())


def prose_fields(brief: ExecutiveBrief):
    yield brief.strategic_outlook, 80
    for signal in brief.market_signals:
        if re.search(r"\d|%", signal.text):
            raise ValueError("Market signals must be qualitative; dates and source details are rendered separately")
        yield signal.text, 40
    for card in brief.topics.model_dump().values():
        for field, limit in (("implication", 25), ("action", 25), ("metric_or_gate", 20), ("caveat", 20)):
            yield card[field], limit


def validate_brief(brief: ExecutiveBrief, payload: dict):
    priorities = brief.priority_focuses
    if len(priorities) != 3 or len(set(priorities)) != 3 or priorities[0] != "ontario_retail":
        raise ValueError("Select three unique priorities with Ontario retail first")
    if not 2 <= len(brief.market_signals) <= 3:
        raise ValueError("Executive brief must contain two or three market signals")
    report = payload["analysis"]["analyst_report"]
    insights = {i["insight_id"] for i in report["market_insights"]}
    for signal in brief.market_signals:
        if not signal.insight_ids or len(set(signal.insight_ids)) != len(signal.insight_ids) or not set(signal.insight_ids) <= insights:
            raise ValueError("Market signal must cite known, unique Analyst insight IDs")
    for text, limit in prose_fields(brief):
        if not text.strip() or word_count(text) > limit:
            raise ValueError(f"Executive field must contain 1-{limit} words")
        if "http://" in text or "https://" in text:
            raise ValueError("Source links are rendered from the validated handoff, not generated")
        if re.search(r"\b(proven effective|led to|drove sales)\b", text, re.I):
            raise ValueError("Executive copy must preserve association rather than assert causal effectiveness")
    if sum(word_count(text) for text, _ in prose_fields(brief)) > 650:
        raise ValueError("Executive prose exceeds 650 words")
    focuses = [r["focus"] for r in report["recommendations"]]
    if len(focuses) != len(TITLES) or set(focuses) != set(TITLES):
        raise ValueError("Presentation requires exactly one recommendation per topic")
