from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from config import (
    CATEGORY_KEYWORDS,
    COMPANY_ALIASES,
    COMPANIES,
    EXCLUDED_LINK_TERMS,
    EXCLUDED_TITLE_TERMS,
    INDUSTRY_QUERIES,
    OUTPUT_PATH,
    RESULTS_PER_QUERY,
    SERPAPI_ENDPOINT,
    SERPAPI_ENGINE,
    SOURCE_GROUPS,
)


def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_queries() -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for company in COMPANIES:
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                base_query = f"{company} {keyword}"
                queries.extend(source_scoped_queries(company, category, base_query))

    for query in INDUSTRY_QUERIES:
        queries.extend(source_scoped_queries("industry", "industry", query))

    return queries


def source_scoped_queries(company: str, category: str, base_query: str) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []
    for group in SOURCE_GROUPS:
        source_filter = " OR ".join(f"site:{domain}" for domain in group["domains"])
        seeds.append(
            {
                "company": company,
                "category": category,
                "query": base_query,
                "source_group": group["name"],
                "serpapi_query": f"{base_query} ({source_filter})",
            }
        )
    return seeds


def request_serpapi(query: str, api_key: str) -> dict[str, Any]:
    params = {
        "engine": SERPAPI_ENGINE,
        "q": query,
        "api_key": api_key,
        "gl": "us",
        "hl": "en",
        "num": RESULTS_PER_QUERY,
    }
    url = f"{SERPAPI_ENDPOINT}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "news-scrapper/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_with_retries(query: str, api_key: str, retries: int, retry_backoff: float) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return request_serpapi(query, api_key)
        except Exception as exc:
            attempt += 1
            if attempt > retries or "429" not in str(exc):
                raise
            sleep_seconds = retry_backoff * attempt
            print(f"Rate limited. Retrying in {sleep_seconds:.1f}s.", flush=True)
            time.sleep(sleep_seconds)


def source_name(source: Any) -> str | None:
    if isinstance(source, dict):
        return source.get("name") or source.get("title")
    if isinstance(source, str):
        return source
    return None


def link_domain(link: str | None) -> str:
    domain = urlparse(link or "").netloc.lower()
    return domain.removeprefix("www.")


def allowed_domains() -> set[str]:
    return {domain for group in SOURCE_GROUPS for domain in group["domains"]}


def is_allowed_domain(link: str | None) -> bool:
    domain = link_domain(link)
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains())


def is_noise_title(title: str | None) -> bool:
    lowered = (title or "").lower()
    return any(term in lowered for term in EXCLUDED_TITLE_TERMS)


def is_noise_link(link: str | None) -> bool:
    lowered = (link or "").lower()
    return any(term in lowered for term in EXCLUDED_LINK_TERMS)


def is_relevant(row: dict[str, str | None]) -> bool:
    title_and_link = f"{row.get('title') or ''} {row.get('link') or ''}".lower()
    company = row.get("company")

    if company == "industry":
        query_terms = (row.get("query") or "").lower().split()
        return "soda" in title_and_link and any(term in title_and_link for term in query_terms)

    return any(alias in title_and_link for alias in COMPANY_ALIASES.get(company or "", []))


def normalize_result(seed: dict[str, str], result: dict[str, Any]) -> dict[str, str | None]:
    return {
        "company": seed["company"],
        "category": seed["category"],
        "query": seed["query"],
        "title": result.get("title"),
        "source": source_name(result.get("source")),
        "date": result.get("date"),
        "link": result.get("link"),
    }


def dedupe(rows: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    seen: set[str] = set()
    unique_rows: list[dict[str, str | None]] = []

    for row in rows:
        key = row.get("link") or f"{row.get('title')}|{row.get('source')}"
        if not key or key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    return unique_rows


def quality_filter(rows: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    return [
        row
        for row in rows
        if is_allowed_domain(row.get("link"))
        and not is_noise_title(row.get("title"))
        and not is_noise_link(row.get("link"))
        and is_relevant(row)
    ]


def scrape(
    delay_seconds: float,
    query_seeds: list[dict[str, str]] | None = None,
    retries: int = 2,
    retry_backoff: float = 5.0,
) -> dict[str, Any]:
    load_env()
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is missing. Add it to .env or the environment.")

    queries = query_seeds or build_queries()
    rows: list[dict[str, str | None]] = []
    errors: list[dict[str, str]] = []

    for index, seed in enumerate(queries, start=1):
        print(f"[{index}/{len(queries)}] {seed['serpapi_query']}", flush=True)
        try:
            payload = request_with_retries(seed["serpapi_query"], api_key, retries, retry_backoff)
            for result in payload.get("news_results", []):
                rows.append(normalize_result(seed, result))
        except Exception as exc:
            errors.append({"query": seed["serpapi_query"], "error": str(exc)})

        if index < len(queries) and delay_seconds:
            time.sleep(delay_seconds)

    quality_rows = quality_filter(rows)
    unique_rows = dedupe(quality_rows)
    return {
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "engine": SERPAPI_ENGINE,
            "source_strategy": "quality_source_domain_allowlist",
            "companies": COMPANIES,
            "industry_queries": INDUSTRY_QUERIES,
            "source_groups": SOURCE_GROUPS,
            "excluded_title_terms": EXCLUDED_TITLE_TERMS,
            "excluded_link_terms": EXCLUDED_LINK_TERMS,
            "query_count": len(queries),
            "raw_result_count": len(rows),
            "quality_filtered_count": len(quality_rows),
            "deduped_result_count": len(unique_rows),
            "error_count": len(errors),
            "errors": errors,
        },
        "queries": queries,
        "articles": unique_rows,
    }


def load_retry_seeds(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    previous = json.loads(path.read_text())
    failed_queries = {error["query"] for error in previous["metadata"].get("errors", [])}
    seeds = [
        seed
        for seed in previous.get("queries", [])
        if seed.get("serpapi_query") in failed_queries
    ]
    return previous, seeds


def merge_datasets(previous: dict[str, Any], retry_dataset: dict[str, Any]) -> dict[str, Any]:
    merged_articles = dedupe(previous.get("articles", []) + retry_dataset.get("articles", []))
    unresolved = retry_dataset["metadata"].get("errors", [])
    metadata = previous["metadata"] | {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "retry_query_count": retry_dataset["metadata"]["query_count"],
        "retry_raw_result_count": retry_dataset["metadata"]["raw_result_count"],
        "retry_quality_filtered_count": retry_dataset["metadata"]["quality_filtered_count"],
        "deduped_result_count": len(merged_articles),
        "error_count": len(unresolved),
        "errors": unresolved,
    }

    return {
        "metadata": metadata,
        "queries": previous.get("queries", []),
        "articles": merged_articles,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape a frozen news dataset with SerpApi.")
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=5.0)
    parser.add_argument("--retry-errors-from")
    args = parser.parse_args()

    previous = None
    query_seeds = None
    if args.retry_errors_from:
        previous, query_seeds = load_retry_seeds(Path(args.retry_errors_from))
        print(f"Retrying {len(query_seeds)} failed queries from {args.retry_errors_from}", flush=True)

    dataset = scrape(
        delay_seconds=args.delay,
        query_seeds=query_seeds,
        retries=args.retries,
        retry_backoff=args.retry_backoff,
    )
    if previous is not None:
        dataset = merge_datasets(previous, dataset)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))

    metadata = dataset["metadata"]
    print(
        f"Saved {metadata['deduped_result_count']} deduped articles "
        f"from {metadata['query_count']} queries to {output_path}"
    )
    if metadata["error_count"]:
        print(f"Finished with {metadata['error_count']} query errors. See metadata.errors.")


if __name__ == "__main__":
    main()
