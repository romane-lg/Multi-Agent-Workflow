from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_DATASET_PATH = Path("news_scrapper/news_dataset_v2_2_full.json")


def selected_articles(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    articles = dataset.get("articles", [])
    if "schema_version" in dataset:
        return [article for article in articles if article.get("eligibility_status") == "accepted"]
    return articles


def load_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    return json.loads(dataset_path.read_text())


def domain_for(link: str | None) -> str:
    domain = urlparse(link or "").netloc.lower()
    return domain.removeprefix("www.")


def dataset_summary(dataset: dict[str, Any]) -> str:
    articles = selected_articles(dataset)
    if "schema_version" in dataset:
        company_counts = Counter(
            company for article in articles for company in confirmed_companies(article)
        )
        return "\n".join([
            f"Accepted articles: {len(articles)}",
            f"Excluded rejected/review records: {len(dataset.get('articles', [])) - len(articles)}",
            f"Confirmed company coverage (may overlap): {dict(company_counts)}",
            f"Articles with extracted text: {sum(bool(a.get('article_text')) for a in articles)}",
            f"Discovery run status: {dataset.get('run', {}).get('status', 'unknown')}",
            "Discovery dimensions are search provenance, not verified article topics.",
            "Records without article text provide title-level evidence only. Do not infer body facts.",
        ])
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
    if max_articles is not None and max_articles < 1:
        raise ValueError("max_articles must be positive")
    articles = selected_articles(dataset)
    if max_articles is not None:
        articles = articles[:max_articles]

    if "schema_version" in dataset:
        sections = [dataset_summary(dataset), f"\nARTICLES PROVIDED: {len(articles)}"]
        for index, article in enumerate(articles, start=1):
            associations = [a for a in article.get("discovery_associations", []) if a.get("decision") == "accepted"]
            dimensions = sorted({a["discovery_dimension"] for a in associations})
            sections.extend([
                f"\n{index}. {article.get('title')}",
                f"Source: {article.get('source') or article.get('publisher_domain')}",
                f"Date: {article.get('publication_date') or 'unknown date'}",
                f"URL: {article.get('normalized_url')}",
                f"Confirmed companies: {', '.join(confirmed_companies(article)) or 'none; industry context'}",
                f"Discovery dimensions (provenance only): {', '.join(dimensions)}",
                f"Article text: {article.get('article_text') or 'Unavailable; title-level evidence only.'}",
            ])
        return "\n".join(sections)

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


def confirmed_companies(article: dict[str, Any]) -> list[str]:
    return sorted({
        company
        for association in article.get("discovery_associations", [])
        if association.get("decision") == "accepted"
        for company in association.get("matched_companies", [])
    })
