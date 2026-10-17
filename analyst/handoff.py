"""Validate the Researcher output before allowing downstream company analysis."""
import hashlib
import json

from analyst.schema import CompanyBrief
from researcher.agent import validate_pack
from researcher.context import build_analyst_context
from researcher.schema import Article, EvidencePack


def make_handoff(researcher_output: dict, brief: CompanyBrief, as_of_date: str) -> tuple[dict, str]:
    articles = [Article.model_validate(a) for a in researcher_output["sources"]]
    if len({a.article_id for a in articles}) != len(articles):
        raise ValueError("Duplicate source IDs in Researcher handoff")
    for article in articles:
        if (article.availability == "full_text") != bool(article.paragraphs):
            raise ValueError("Source availability does not match text")
        if len({p.paragraph_id for p in article.paragraphs}) != len(article.paragraphs):
            raise ValueError("Duplicate source paragraph IDs")
    pack = EvidencePack.model_validate(researcher_output["evidence_pack"])
    validate_pack(pack, articles, pack.question)
    source_context = build_analyst_context(researcher_output)  # Includes hash validation and every paragraph.
    payload = {
        "schema_version": "researcher-to-analyst-v1",
        "as_of_date": as_of_date,
        "researcher_output": researcher_output,
        "company_brief": brief.model_dump(),
    }
    payload["handoff_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    sections = [
        f"ANALYSIS AS OF: {as_of_date}", source_context,
        "COMPANY BRIEF: supplied planning context, separate from competitive evidence",
        f"Company: {brief.company_name}; PDF SHA256: {brief.pdf_sha256}",
        "\n".join(brief.data_status_notes),
    ]
    sections.extend(f"[BRIEF p{page.page_number}]\n{page.text}" for page in brief.pages)
    return payload, "\n\n".join(sections)
