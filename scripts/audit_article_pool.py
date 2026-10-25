"""Audit every accepted discovery URL; resume captured requests and save frozen text."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus.access import CapturedFetcher, RobustFetcher, summarize
from news_scrapper.extract_content import utc_now
from researcher.schema import Article


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('news_scrapper/news_dataset_v2_2_full.json'))
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error('Use 1-4 publisher workers')
    raw = args.input.read_bytes()
    data = json.loads(raw)
    selected = [a for a in data['articles'] if a.get('eligibility_status') == 'accepted']
    urls = [a['normalized_url'] for a in selected]
    if not selected or len(set(urls)) != len(urls):
        raise ValueError('Expected nonempty unique accepted URLs')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'selected_count':len(selected), 'delay_seconds':2,
              'selection':'accepted_only', 'code_sha256':hashlib.sha256(Path('corpus/access.py').read_bytes()).hexdigest()}
    config_path = args.output_dir / 'audit_config.json'
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise ValueError('Audit input/code changed; choose a new output directory')
    config_path.write_text(json.dumps(config, indent=2))
    groups = defaultdict(list)
    for article in selected:
        groups[urlsplit(article['normalized_url']).netloc].append(article)

    def publisher(items):
        fetcher = RobustFetcher(2, args.output_dir / 'http_cache')
        for item in items:
            target = args.output_dir / 'records' / (item['article_id'] + '.json')
            if target.exists():
                yield json.loads(target.read_text())
                continue
            enhanced = fetcher.extract({'link': item['normalized_url']})
            legacy = CapturedFetcher(2, args.output_dir / 'http_cache', replay=True).extract({'link':item['normalized_url']})
            record = {'article_id':item['article_id'],'url':item['normalized_url'],'publisher':urlsplit(item['normalized_url']).netloc,
                      'baseline':legacy,'enhanced':enhanced, 'robots_checks':fetcher.robots_log.copy()}
            target.write_text(json.dumps(record, indent=2, ensure_ascii=False))
            print(item['article_id'], enhanced['extraction_status'], enhanced['word_count'], enhanced['extraction_error'], flush=True)
            yield record

    (args.output_dir / 'records').mkdir(exist_ok=True)
    records = []
    def collect(items):
        return list(publisher(items))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(collect, items) for items in groups.values()]
        for future in as_completed(futures):
            records.extend(future.result())
            progress = summarize(records,len(selected))
            (args.output_dir / 'progress.json').write_text(json.dumps(progress, indent=2))
    by_id = {r['article_id']:r for r in records}
    frozen = []
    for item in selected:
        result = by_id[item['article_id']]['enhanced']
        paragraphs = [{'paragraph_id':f'p{i}', 'text':text} for i,text in enumerate((result['article_text'] or '').split('\n\n'),1) if text.strip()]
        text = '\n\n'.join(p['text'] for p in paragraphs)
        article = Article(article_id=item['article_id'], title=item['title'], url=item['normalized_url'],
            publication_date=item['publication_date'], availability='full_text' if paragraphs else 'unavailable',
            access_note=result['extraction_error'] or f"Public HTML via {result['method']}; completeness not manually certified.",
            text_sha256=hashlib.sha256(text.encode()).hexdigest(), paragraphs=paragraphs, retrieved_at=result['extracted_at'])
        frozen.append(article.model_dump())
    report = summarize(records,len(selected))
    report.update(finished_at=utc_now(), discovery_status_counts=dict(Counter(a.get('eligibility_status') for a in data['articles'])),
                  publisher_breakdown={domain:summarize([r for r in records if r['publisher']==domain],len(items)) for domain,items in groups.items()})
    (args.output_dir / 'articles.json').write_text(json.dumps(frozen,indent=2,ensure_ascii=False))
    (args.output_dir / 'access_report.json').write_text(json.dumps(report,indent=2))
    lines = ['# Full article access audit','',f"Checked {len(records)}/{len(selected)} accepted URLs across {len(groups)} publishers.",'',
             f"Extracted: {report['enhanced_success']}; unavailable: {report['enhanced_unavailable']} ({report['unavailable_percent_of_checked']}%).",'',
             f"Recovered vs legacy extractor on identical captured responses: {report['recovered_vs_legacy']}.",'',
             '| Publisher | URLs | Extracted | Unavailable |','| --- | ---: | ---: | ---: |']
    for domain,stats in sorted(report['publisher_breakdown'].items()):
        lines.append(f"| {domain} | {stats['checked_urls']} | {stats['enhanced_success']} | {stats['enhanced_unavailable']} |")
    lines.extend(['','## Failure reasons','',*[f'- {k}: {v}' for k,v in sorted(report['failure_reasons'].items()) if k!='success'],'',report['limitation']])
    (args.output_dir / 'access_report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='publisher_breakdown'},indent=2))


if __name__ == '__main__':
    main()
