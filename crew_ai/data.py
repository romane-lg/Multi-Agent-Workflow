from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_DATASET_PATH = Path("news_scrapper/news_dataset.json")


def load_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    return json.loads(dataset_path.read_text())


def domain_for(link: str | None) -> str:
    domain = urlparse(link or "").netloc.lower()
    return domain.removeprefix("www.")


def dataset_summary(dataset: dict[str, Any]) -> str:
    articles = dataset.get("articles", [])
    company_counts = Counter(article["company"] for article in articles)
    category_counts = Counter(article["category"] for article in articles)
    source_counts = Counter(domain_for(article.get("link")) for article in articles)

    return "\n".join(
        [
            f"Total articles: {len(articles)}",
            f"Companies: {dict(company_counts)}",
            f"Categories: {dict(category_counts)}",
            f"Top sources: {dict(source_counts.most_common(15))}",
            f"Dataset created at: {dataset.get('metadata', {}).get('created_at')}",
            f"Dataset updated at: {dataset.get('metadata', {}).get('updated_at')}",
        ]
    )


def build_article_context(dataset: dict[str, Any], max_articles: int | None = None) -> str:
    articles = dataset.get("articles", [])
    if max_articles is not None:
        articles = articles[:max_articles]

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for article in articles:
        grouped[article["company"]][article["category"]].append(article)

    sections: list[str] = [dataset_summary(dataset), "\nARTICLES"]
    for company in sorted(grouped):
        sections.append(f"\n## {company}")
        for category in sorted(grouped[company]):
            sections.append(f"\n### {category}")
            for index, article in enumerate(grouped[company][category], start=1):
                source = article.get("source") or domain_for(article.get("link"))
                date = article.get("date") or "unknown date"
                sections.append(
                    f"{index}. {article.get('title')} | {source} | {date} | "
                    f"query={article.get('query')} | {article.get('link')}"
                )

    return "\n".join(sections)
