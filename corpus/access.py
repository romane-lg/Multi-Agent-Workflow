"""Public HTML extraction with captured responses and replayable legacy comparison."""
from collections import Counter
from email.message import Message
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from lxml import html as lhtml
import trafilatura

from news_scrapper.extract_content import (
    Fetcher, ExtractionFailure, MAX_REDIRECTS, MIN_WORDS, USER_AGENT,
    empty_result, utc_now,
)


def normalize_text(text):
    return "\n\n".join(" ".join(line.split()) for line in (text or "").splitlines() if line.strip())


def visible_tree(body):
    tree = lhtml.fromstring(body)
    for node in tree.xpath('//script|//style|//noscript|//template|//*[@hidden]|//*[@aria-hidden="true"]'):
        if node.getparent() is not None:
            node.drop_tree()
    for node in list(tree.xpath('//*[@style]')):
        if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', node.get('style', ''), re.I) and node.getparent() is not None:
            node.drop_tree()
    return tree


CHALLENGES = re.compile(r'verify (?:you are|you.re) human|complete the captcha|enable javascript and cookies to continue|checking your browser|performing security verification', re.I)
GATES = re.compile(r'subscribe to (?:continue reading|read the full)|sign in to continue reading|log in to continue reading|this article is for subscribers|subscriber.only content', re.I)


def public_text(body, url):
    """Extract rendered article text; never read hidden/JSON article bodies."""
    raw = lhtml.fromstring(body)
    title = " ".join(raw.xpath('//title/text()')).lower()
    tree = visible_tree(body)
    visible = " ".join(tree.text_content().split())
    if CHALLENGES.search(visible) or any(s in title for s in ('access denied', 'just a moment', 'captcha')):
        raise ExtractionFailure('browser_challenge')
    # Real visible access restrictions remain a barrier. A subscription link in
    # navigation/footer alone is not evidence that the article itself is gated.
    article_nodes = tree.xpath('//article|//*[@itemprop="articleBody"]|//main')
    content = max(article_nodes, key=lambda n: len(n.text_content()), default=tree)
    if GATES.search(" ".join(content.text_content().split())):
        raise ExtractionFailure('subscription_gate')
    if not article_nodes and GATES.search(visible):
        raise ExtractionFailure('subscription_gate')
    for node in list(tree.xpath('//nav|//footer|//header|//aside|//form|//dialog')):
        if node.getparent() is not None:
            node.drop_tree()
    candidates = []
    for precision in (True, False):
        candidate = normalize_text(trafilatura.extract(lhtml.tostring(tree), url=url, output_format='txt',
            include_comments=False, include_tables=False, favor_precision=precision, favor_recall=not precision))
        if candidate:
            candidates.append((candidate, 'trafilatura_precision' if precision else 'trafilatura_recall'))
    # A visible article container often survives extractor heuristics that discard
    # short paragraphs. Keep only paragraph text from that actual container.
    for node in tree.xpath('//article|//*[@itemprop="articleBody"]'):
        paragraphs = [' '.join(p.text_content().split()) for p in node.xpath('.//p') if p.text_content().strip()]
        if paragraphs:
            candidates.append(('\n\n'.join(paragraphs), 'visible_article_paragraphs'))
    candidates = [(text, method) for text, method in candidates if len(text.split()) >= MIN_WORDS]
    if not candidates:
        raise ExtractionFailure('insufficient_visible_text')
    # Prefer the coherent paragraph container when present; otherwise retain the
    # longer extractor candidate for context. Raw HTML is frozen for inspection.
    text, method = max(candidates, key=lambda item: len(item[0].split()))
    restricted = bool(re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', ' '.join(raw.xpath('//script[@type="application/ld+json"]/text()')), re.I))
    if restricted and not tree.xpath('//article|//*[@itemprop="articleBody"]'):
        raise ExtractionFailure('restricted_metadata_no_public_article_container')
    return text, method, restricted


class CapturedFetcher(Fetcher):
    def __init__(self, delay, cache_dir, replay=False):
        super().__init__(delay)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.replay = replay

    def request(self, url, delay):
        key = hashlib.sha256(url.encode()).hexdigest()
        meta = self.cache_dir / (key + '.json')
        body_path = self.cache_dir / (key + '.html.gz')
        if meta.exists():
            data = json.loads(meta.read_text())
            if data.get('error'):
                raise ExtractionFailure(data['error'])
            headers = Message()
            for name, value in data['headers']:
                headers[name] = value
            return data['status'], headers, gzip.decompress(body_path.read_bytes())
        if self.replay:
            raise ExtractionFailure('not_requested_by_enhanced_fetcher')
        if self.origin(url) in self.blocked_origins:
            raise ExtractionFailure('origin_rate_limited')
        attempts = []
        for attempt in range(2):
            try:
                status, headers, body = super().request(url, delay)
                attempts.append({'http_status': status})
                data = {'url': url, 'status': status, 'headers': list(headers.items()), 'fetched_at': utc_now(), 'attempts': attempts}
                body_path.write_bytes(gzip.compress(body))
                meta.write_text(json.dumps(data, indent=2))
                return status, headers, body
            except ExtractionFailure:
                raise
            except Exception as exc:
                attempts.append({'error_type': type(exc).__name__, 'detail': str(exc)})
                if attempt == 0:
                    time.sleep(max(delay, 2))
        error = 'network_error'
        meta.write_text(json.dumps({'url': url, 'error': error, 'attempts': attempts, 'fetched_at': utc_now()}, indent=2))
        raise ExtractionFailure(error)


class RobustFetcher(CapturedFetcher):
    def permission(self, url):
        origin = self.origin(url)
        if origin not in self.robots:
            record = {'origin': origin, 'url': origin + '/robots.txt', 'checked_at': utc_now(), 'http_status': None}
            parser, error = None, None
            robots_url = record['url']
            try:
                for hop in range(MAX_REDIRECTS + 1):
                    status, headers, body = self.request(robots_url, self.delay)
                    record.update(http_status=status, resolved_url=robots_url)
                    if status in (301, 302, 303, 307, 308) and headers.get('Location') and hop < MAX_REDIRECTS:
                        robots_url = urljoin(robots_url, headers['Location'])
                        self.origin(robots_url)
                        continue
                    if status in (404, 410) or (status == 200 and not re.search(br'<(?:html|!doctype)', body, re.I)):
                        parser = RobotFileParser()
                        parser.parse(body.decode('utf-8-sig', errors='replace').splitlines() if status == 200 else [])
                    else:
                        error = 'robots_unavailable'
                    break
            except Exception as exc:
                error = 'robots_unavailable'
                record['detail'] = str(exc)
            record['error'] = error
            self.robots_log.append(record)
            self.robots[origin] = (parser, error)
        parser, error = self.robots[origin]
        if error or parser is None:
            raise ExtractionFailure(error or 'robots_unavailable')
        if not parser.can_fetch(USER_AGENT, url):
            raise ExtractionFailure('robots_disallowed')
        rate = parser.request_rate(USER_AGENT)
        return max(self.delay, parser.crawl_delay(USER_AGENT) or 0, rate.seconds / rate.requests if rate and rate.requests else 0)

    def extract(self, article):
        result = empty_result('failed')
        result['method'] = None
        url = article['link']
        try:
            for hop in range(MAX_REDIRECTS + 1):
                delay = self.permission(url)
                status, headers, body = self.request(url, delay)
                result.update(http_status=status, resolved_url=url)
                if status in (301, 302, 303, 307, 308):
                    if hop == MAX_REDIRECTS or not headers.get('Location'):
                        raise ExtractionFailure('invalid_redirect_chain')
                    url = urljoin(url, headers['Location'])
                    continue
                if status != 200:
                    raise ExtractionFailure({401:'authentication_required',403:'access_denied',429:'rate_limited',503:'service_unavailable'}.get(status, f'http_error_{status}'))
                if headers.get_content_type() not in ('text/html', 'application/xhtml+xml'):
                    raise ExtractionFailure('unsupported_content_type')
                text, method, restricted = public_text(body, url)
                result.update(article_text=text, word_count=len(text.split()), extraction_status='success', method=method,
                              restricted_metadata=restricted, extraction_error=None)
                break
        except Exception as exc:
            result['extraction_error'] = str(exc) if isinstance(exc, ExtractionFailure) else f'{type(exc).__name__}: {exc}'
        result['extracted_at'] = utc_now()
        return result


def summarize(rows, total):
    n = len(rows)
    good = sum(r['enhanced']['extraction_status'] == 'success' for r in rows)
    baseline = sum(r['baseline']['extraction_status'] == 'success' for r in rows)
    reasons = Counter(r['enhanced']['extraction_error'] or 'success' for r in rows)
    confirmed = {'access_denied', 'authentication_required', 'browser_challenge', 'subscription_gate', 'rate_limited'}
    blocked = sum(count for reason, count in reasons.items() if reason in confirmed)
    return {'selected_urls': total, 'checked_urls': n, 'remaining_urls': total - n,
            'denominator': 'unique accepted article URLs; not publisher domains and not all discovery candidates',
            'legacy_success_on_same_captured_responses': baseline, 'enhanced_success': good,
            'enhanced_unavailable': n-good, 'unavailable_percent_of_checked': round(100*(n-good)/n,2) if n else None,
            'direct_article_access_barriers': blocked, 'direct_barrier_percent_of_checked': round(100*blocked/n,2) if n else None,
            'recovered_vs_legacy': sum(r['baseline']['extraction_status'] != 'success' and r['enhanced']['extraction_status']=='success' for r in rows),
            'failure_reasons': dict(reasons),
            'limitation': 'Robots failures and network failures do not prove that an article is blocked for a human reader. Extraction success is not a completeness guarantee.'}
