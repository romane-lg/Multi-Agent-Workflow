"""Enrich existing discovery records with publicly accessible source text only."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

import trafilatura
from lxml import html as lhtml

USER_AGENT = "AcademicEvidenceExtractor/1.0"
TIMEOUT = 20
MAX_BYTES = 5_000_000
MAX_REDIRECTS = 5
MIN_WORDS = 100
EXPECTED_PILOT_HASH = "a83029b75196ca6c2123121d6b729aefe26afab4cc5d6d0fc3441feb2974d2bf"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ExtractionFailure(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Fetcher:
    def __init__(self, delay):
        self.delay = delay
        self.opener = build_opener(NoRedirect())
        self.robots = {}
        self.last_request = {}
        self.blocked_origins = set()
        self.robots_log = []

    @staticmethod
    def origin(url):
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ExtractionFailure("invalid_url")
        return f"{parts.scheme}://{parts.netloc}"

    def request(self, url, delay):
        origin = self.origin(url)
        if origin in self.blocked_origins:
            raise ExtractionFailure("origin_rate_limited")
        remaining = delay - (time.monotonic() - self.last_request.get(origin, 0))
        if remaining > 0:
            time.sleep(remaining)
        self.last_request[origin] = time.monotonic()
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"})
        try:
            response = self.opener.open(request, timeout=TIMEOUT)
        except HTTPError as exc:
            response = exc
        with response:
            status = response.code
            headers = response.headers
            if status in (429, 503):
                self.blocked_origins.add(origin)
            # Error and redirect bodies are never extracted.
            body = response.read(MAX_BYTES + 1) if status == 200 else b""
            if len(body) > MAX_BYTES:
                raise ExtractionFailure("response_too_large")
            return status, headers, body

    def permission(self, url):
        origin = self.origin(url)
        if origin not in self.robots:
            robots_url = origin + "/robots.txt"
            record = {"origin": origin, "url": robots_url, "checked_at": utc_now(), "http_status": None}
            parser = None
            error = None
            try:
                status, headers, body = self.request(robots_url, self.delay)
                record["http_status"] = status
                if status in (404, 410):
                    parser = RobotFileParser()
                    parser.parse([])
                elif status == 200 and body.strip() and b"<html" not in body.lower() and b"<!doctype html" not in body.lower():
                    parser = RobotFileParser()
                    parser.parse(body.decode("utf-8-sig", errors="replace").splitlines())
                else:
                    error = "robots_unavailable"
                record["sha256"] = hashlib.sha256(body).hexdigest() if body else None
            except Exception as exc:
                error = "robots_unavailable"
                record["detail"] = f"{type(exc).__name__}: {exc}"
            record["error"] = error
            self.robots_log.append(record)
            self.robots[origin] = (parser, error)
        parser, error = self.robots[origin]
        if error:
            raise ExtractionFailure(error)
        if not parser.can_fetch(USER_AGENT, url):
            raise ExtractionFailure("robots_disallowed")
        delay = max(self.delay, parser.crawl_delay(USER_AGENT) or 0)
        rate = parser.request_rate(USER_AGENT)
        if rate and rate.requests:
            delay = max(delay, rate.seconds / rate.requests)
        return delay

    def extract(self, article):
        result = empty_result("failed")
        url = article.get("link")
        try:
            for hop in range(MAX_REDIRECTS + 1):
                delay = self.permission(url)
                status, headers, body = self.request(url, delay)
                result.update(resolved_url=url, http_status=status)
                if status in (301, 302, 303, 307, 308):
                    if hop == MAX_REDIRECTS:
                        raise ExtractionFailure("too_many_redirects")
                    location = headers.get("Location")
                    if not location:
                        raise ExtractionFailure("redirect_without_location")
                    url = urljoin(url, location)
                    continue
                if status != 200:
                    raise ExtractionFailure({401: "authentication_required", 403: "access_denied", 429: "rate_limited", 503: "service_unavailable"}.get(status, f"http_error_{status}"))
                if headers.get_content_type() not in ("text/html", "application/xhtml+xml"):
                    raise ExtractionFailure("unsupported_content_type")
                tree = lhtml.fromstring(body)
                # Treat explicit restricted-access metadata as a barrier; never mine hidden article bodies.
                scripts = " ".join(tree.xpath('//script[@type="application/ld+json"]/text()'))
                if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', scripts, re.I):
                    raise ExtractionFailure("paywall_detected")
                visible_tree = lhtml.fromstring(body)
                for node in visible_tree.xpath('//script|//style|//noscript|//*[@hidden]|//*[@aria-hidden="true"]'):
                    node.drop_tree()
                visible = " ".join(visible_tree.text_content().lower().split())
                title = " ".join(tree.xpath('//title/text()')).lower()
                barriers = ("verify you are human", "verify you're human", "complete the captcha", "enable javascript and cookies to continue", "subscribe to continue reading", "subscribe to read the full", "sign in to continue reading", "log in to continue reading", "this article is for subscribers", "already a subscriber?", "subscriber-only content")
                if any(marker in visible for marker in barriers) or any(marker in title for marker in ("access denied", "just a moment", "captcha")):
                    raise ExtractionFailure("access_barrier_detected")
                # Only extract visible HTML; do not fall back to embedded JSON or hidden content.
                for node in tree.xpath('//script|//style|//noscript|//*[@hidden]|//*[@aria-hidden="true"]|//*[contains(translate(@style," ",""),"display:none")]'):
                    node.drop_tree()
                text = trafilatura.extract(lhtml.tostring(tree), url=url, output_format="txt", include_comments=False, favor_precision=True)
                if not text:
                    raise ExtractionFailure("empty_text")
                text = "\n\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
                words = len(text.split())
                if words < MIN_WORDS:
                    raise ExtractionFailure("insufficient_text")
                result.update(article_text=text, word_count=words, extraction_status="success")
                break
        except ExtractionFailure as exc:
            result["extraction_error"] = str(exc)
        except Exception as exc:
            result["extraction_error"] = f"{type(exc).__name__}: {exc}"
        result["extracted_at"] = utc_now()
        return result


def empty_result(status):
    return dict(article_text=None, extraction_status=status, extraction_error=None,
                extracted_at=None, resolved_url=None, http_status=None, word_count=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="news_scrapper/news_dataset.json")
    parser.add_argument("--output", default="news_scrapper/news_dataset_enriched_test5.json")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()
    source, target = Path(args.input).resolve(), Path(args.output).resolve()
    if source == target or target.exists():
        parser.error("Output must be a new file distinct from the input.")
    if not 1 <= args.limit <= 5:
        parser.error("This pilot supports only 1 to 5 attempted articles.")
    if args.delay < 2 or not args.delay < float("inf"):
        parser.error("Delay must be finite and at least two seconds.")
    raw = source.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    dataset = json.loads(raw.decode("utf-8"))
    articles = dataset.get("articles")
    if not isinstance(articles, list) or not all(isinstance(row, dict) for row in articles):
        parser.error("Expected an articles list of objects.")
    started = utc_now()
    fetcher = Fetcher(args.delay)
    for index, row in enumerate(articles):
        if any(key in row for key in empty_result("not_attempted")):
            parser.error("Input already contains enrichment fields.")
    for index, row in enumerate(articles):
        row.update(fetcher.extract(row) if index < args.limit else empty_result("not_attempted"))
        if index < args.limit:
            print(f"{index + 1}: {row['extraction_status']} | words={row['word_count']} | error={row['extraction_error']}", flush=True)
    if source.read_bytes() != raw:
        raise RuntimeError("Source dataset changed during extraction; refusing output.")
    counts = Counter(row["extraction_status"] for row in articles)
    dataset["content_extraction"] = {
        "input_path": args.input, "input_sha256": source_hash,
        "extractor": "trafilatura", "extractor_version": version("trafilatura"),
        "python_version": __import__("platform").python_version(),
        "dependency_versions": {name: version(name) for name in ("trafilatura", "lxml", "justext", "htmldate", "courlan")},
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at": started, "finished_at": utc_now(),
        "settings": {"limit": args.limit, "selection": "first_n_in_input_order", "delay_seconds": args.delay,
                     "timeout_seconds": TIMEOUT, "max_response_bytes": MAX_BYTES, "max_redirects": MAX_REDIRECTS,
                     "minimum_words": MIN_WORDS, "user_agent": USER_AGENT,
                     "include_comments": False, "favor_precision": True, "output_format": "txt",
                     "access_policy": "robots checked before each URL; uncertain permissions and detected barriers skipped; no retries or bypass"},
        "total_records": len(articles), "attempted_count": min(args.limit, len(articles)),
        "success_count": counts["success"], "failed_count": counts["failed"],
        "not_attempted_count": counts["not_attempted"], "robots_checks": fetcher.robots_log,
        "limitations": "Heuristic extraction and barrier detection do not establish article completeness. Manually review successful text."
    }
    # Exclusive creation also protects against an output appearing during the run.
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(dataset, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Saved {len(articles)} records to {args.output}", flush=True)


if __name__ == "__main__":
    main()