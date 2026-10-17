"""Import a recorded public-reader article body without altering older snapshots."""
import hashlib
import re

from researcher.schema import Article, Paragraph


def apply_reader_supplement(articles: list[dict], supplement: list[dict]) -> list[dict]:
    sources = {a.article_id: a for a in map(Article.model_validate, articles)}
    if len(sources) != len(articles):
        raise ValueError("Duplicate source IDs")
    seen = set()
    for item in supplement:
        article_id = item["article_id"]
        if article_id not in sources or article_id in seen:
            raise ValueError("Unknown or duplicate supplement article ID")
        seen.add(article_id)
        if sources[article_id].availability != "unavailable":
            raise ValueError("Supplement may only fill previously unavailable text")
        paragraphs = [Paragraph(paragraph_id=f"p{i}", text=p["text"].strip())
                      for i, p in enumerate(item["paragraphs"], 1) if p["text"].strip()]
        text = "\n\n".join(p.text for p in paragraphs)
        if len(text.split()) < 100:
            raise ValueError("Reader supplement is too short to establish article-body availability")
        if re.search(r"cite|^L\d+:", text, flags=re.M):
            raise ValueError("Reader formatting must be removed before import")
        if item.get("retrieval_method") != "public_web_reader":
            raise ValueError("Expected documented public-reader retrieval")
        sources[article_id] = sources[article_id].model_copy(update={
            "availability": "full_text", "paragraphs": paragraphs,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "retrieval_method": "public_web_reader", "retrieved_at": item["retrieved_at"],
            "access_note": (
                "Article body exposed by the public web reader; navigation, newsletter forms, and footer excluded. "
                "Local browser separately encountered a security-verification page. "
                "This is a reader snapshot, not a claim of successful direct browser access."
            ),
        })
    return [sources[a["article_id"]].model_dump() for a in articles]
