"""Try a normal rendered browser on eligible failures, stop after a blocked publisher sample."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corpus.access import RobustFetcher
from corpus.browser import browser_extract
from researcher.schema import Article


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--browser-executable',type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows = [json.loads(p.read_text()) for p in sorted((args.audit_dir/'records').glob('*.json'))]
    articles = json.loads((args.audit_dir/'articles.json').read_text())
    groups = defaultdict(list)
    eligible = {'access_denied','browser_challenge','insufficient_visible_text','restricted_metadata_no_public_article_container'}
    for row in rows:
        if row['enhanced']['extraction_error'] in eligible:
            groups[(row['publisher'],row['enhanced']['extraction_error'])].append(row)
    fetcher = RobustFetcher(2,args.audit_dir/'http_cache',replay=True)
    attempts = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,**({'executable_path':str(args.browser_executable)} if args.browser_executable else {}))
        for (publisher,failure_kind),items in sorted(groups.items()):
            for index,row in enumerate(items):
                path = args.output_dir/(row['article_id']+'.browser.json')
                result = json.loads(path.read_text()) if path.exists() else browser_extract(browser,row['url'],fetcher.permission)
                path.write_text(json.dumps(result,indent=2,ensure_ascii=False))
                attempts.append({'article_id':row['article_id'],'publisher':publisher,**result})
                print(publisher,row['article_id'],result['extraction_error'] or f"success {result['word_count']} words",flush=True)
                if not result['article_text']:
                    # The same challenge/rate gate should not be hammered across
                    # every article from this publisher in the same run.
                    break
                time.sleep(2)
        browser.close()
    recovered = {r['article_id']:r for r in attempts if r['article_text']}
    for i,article in enumerate(articles):
        if article['article_id'] in recovered:
            result = recovered[article['article_id']]
            paragraphs = [{'paragraph_id':f'p{j}','text':t} for j,t in enumerate(result['article_text'].split('\n\n'),1) if t.strip()]
            articles[i] = Article.model_validate({**article,'availability':'full_text','paragraphs':paragraphs,
                'text_sha256':hashlib.sha256('\n\n'.join(p['text'] for p in paragraphs).encode()).hexdigest(),
                'retrieval_method':'browser_rendered','retrieved_at':result['extracted_at'],
                'access_note':'Public text visible in a normal browser; no authentication or challenge bypass.'}).model_dump()
    report = json.loads((args.audit_dir/'access_report.json').read_text())
    report['http_extraction_success'] = report['enhanced_success']
    report['browser_attempts'] = len(attempts)
    report['browser_publishers_sampled'] = len({a['publisher'] for a in attempts})
    report['browser_recovered'] = len(recovered)
    report['final_success'] = sum(a['availability']=='full_text' for a in articles)
    report['final_unavailable'] = len(articles)-report['final_success']
    report['final_unavailable_percent'] = round(100*report['final_unavailable']/len(articles),2)
    report['http_failure_reasons'] = report.pop('failure_reasons')
    report['final_unavailable_reasons'] = dict(Counter(row['enhanced']['extraction_error'] for row in rows
        if row['article_id'] not in recovered and row['enhanced']['extraction_status']!='success'))
    report['browser_failures'] = [{'publisher':a['publisher'],'article_id':a['article_id'],'reason':a['extraction_error']} for a in attempts if not a['article_text']]
    (args.output_dir/'articles.json').write_text(json.dumps(articles,indent=2,ensure_ascii=False))
    (args.output_dir/'access_report.json').write_text(json.dumps(report,indent=2))
    lines = ['# Full article pool: final access report','',
        f"Denominator: {len(articles)} accepted unique article URLs (not all discovery candidates).",'',
        f"Legacy extractor: {report['legacy_success_on_same_captured_responses']}/{len(articles)} readable bodies.",
        f"Improved public HTML extractor: {report['enhanced_success']}/{len(articles)}.",
        f"Normal-browser recoveries: {report['browser_recovered']} from {report['browser_attempts']} attempts across {report['browser_publishers_sampled']} publishers.",
        f"Final usable text: {report['final_success']}/{len(articles)}; unavailable: {report['final_unavailable']} ({report['final_unavailable_percent']}%).",'',
        '## Remaining HTTP/policy failure categories','',
        *[f'- {reason}: {count}' for reason,count in sorted(report['final_unavailable_reasons'].items())],'',
        'Browser probes stop after a failed representative for each publisher/failure category; unprobed siblings remain unavailable, not individually browser-verified.',
        'Robots checks, network failures and insufficient extraction are distinct from a confirmed human-access restriction. Visible text extraction does not certify complete article coverage.',
        'No login, subscription, CAPTCHA or verification gate was bypassed.']
    (args.output_dir/'access_report.md').write_text('\n'.join(lines)+'\n')
    print('Final extraction:',report['final_success'],'/',len(articles),'unavailable:',report['final_unavailable_percent'],'%')


if __name__=='__main__':
    main()
