"""Fetch the five explicitly selected URLs once, respecting existing access checks."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from news_scrapper.extract_content import Fetcher
from researcher.runtime import LOCAL, ROOT
from researcher.schema import Article, Paragraph


def main():
    LOCAL.mkdir(exist_ok=True)
    target = LOCAL / "articles.json"
    if target.exists():
        raise SystemExit("Frozen articles already exist; inspect them rather than refetching.")
    manifest = json.loads((ROOT / "researcher/articles.json").read_text())
    fetcher = Fetcher(delay=2)
    articles = []
    for metadata in manifest:
        result = fetcher.extract({"link": metadata["url"]})
        text = result.get("article_text") or ""
        paragraphs = [Paragraph(paragraph_id=f"p{i}", text=p.strip())
                      for i, p in enumerate(text.split("\n\n"), 1) if p.strip()]
        normalized = "\n\n".join(p.text for p in paragraphs)
        article = Article(
            **metadata, availability="full_text" if text else "unavailable",
            access_note=result.get("extraction_error") or "Accessible HTML extracted; verify against publisher before benchmarking.",
            text_sha256=hashlib.sha256(normalized.encode()).hexdigest(), paragraphs=paragraphs,
        )
        articles.append(article.model_dump())
        print(metadata["article_id"], article.availability, result["word_count"], result.get("extraction_error"), flush=True)
        # Preserve progress without repeating previous publisher requests after failure.
        partial = LOCAL / "articles.partial.json"
        partial.write_text(json.dumps(articles, indent=2, ensure_ascii=False) + "\n")
    partial.replace(target)
    (LOCAL / "source_access.json").write_text(json.dumps(fetcher.robots_log, indent=2) + "\n")
    print("Saved frozen source input:", target)


if __name__ == "__main__":
    main()
