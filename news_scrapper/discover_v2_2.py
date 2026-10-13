"""Checkpointed URL-only V2 discovery. No publisher requests or article bodies."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from email.utils import parsedate_to_datetime

from config import SERPAPI_ENDPOINT, SERPAPI_ENGINE
from config_v2_2 import (COMPANIES, SOURCE_GROUPS, INDUSTRY_QUERIES, EXCLUDED_TITLE_TERMS,
    EXCLUDED_LINK_TERMS, DIMENSIONS, PILOT_SOURCE_GROUP, ENTITY_RULE_VERSION,
    BEVERAGE_CONTEXT, NON_ARTICLE_PATHS, QUERY_RULE_VERSION, BEVERAGE_TRADE_DOMAINS)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def make_config(start, end, pilot=True, seed=42):
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end:
        raise ValueError('Start date must not follow end date')
    return {'start_date': start.isoformat(), 'end_date': end.isoformat(), 'inclusive': True,
        'companies': COMPANIES, 'dimensions': {k:v for k,v in DIMENSIONS.items() if not pilot or k in ('products','business')},
        'source_groups': [g for g in SOURCE_GROUPS if not pilot or g['name'] == PILOT_SOURCE_GROUP],
        'allowed_domains': [d for g in SOURCE_GROUPS for d in g['domains']],
        'industry_queries': [] if pilot else INDUSTRY_QUERIES,
        'excluded_title_terms': EXCLUDED_TITLE_TERMS, 'excluded_link_terms': EXCLUDED_LINK_TERMS,
        'non_article_paths': NON_ARTICLE_PATHS, 'entity_rules_version': ENTITY_RULE_VERSION,
        'beverage_context': BEVERAGE_CONTEXT, 'pilot': pilot, 'seed': seed,
        'query_rules_version': QUERY_RULE_VERSION, 'entity_policy': 'title confirmed; URL/snippet only requires review',
        'beverage_trade_domains': BEVERAGE_TRADE_DOMAINS,
        'dimension_policy': 'discovery provenance, not verified article topic',
        'engine': SERPAPI_ENGINE, 'gl': 'us', 'hl': 'en',
        'result_policy': 'all returned leaf news results; no pagination',
        'delay_seconds': 3, 'max_attempts_per_query': 3, 'backoff_base_seconds': 30,
        'timeout_seconds': 30}


def make_run(config):
    rng = random.Random(config['seed'])
    companies = list(config['companies']); rng.shuffle(companies)
    dimensions = list(config['dimensions']); rng.shuffle(dimensions)
    groups = list(config['source_groups']); rng.shuffle(groups)
    queries = []
    # Each block gives one identical dimension/source opportunity to every company.
    for gi, group in enumerate(groups):
        sites = '(' + ' OR '.join('site:' + d for d in group['domains']) + ')'
        for di, dimension in enumerate(dimensions):
            rotation = (gi + di) % len(companies)
            for company in companies[rotation:] + companies[:rotation]:
                add_query(queries, config, company, dimension, group['name'], f'"{company}" intitle:"{company}" {config["dimensions"][dimension]} {sites}')
            if config['industry_queries'] and di < len(config['industry_queries']):
                topic = config['industry_queries'][di]
                add_query(queries, config, 'industry', 'industry', group['name'], f'"{topic}" {sites}')
    return {'schema_version':'2.0', 'run': {'run_id':digest(config), 'status':'pending',
        'created_at':now(), 'updated_at':now(), 'config':config, 'api_requests':0,
        'code_hashes': {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('discover_v2_2.py','config_v2_2.py','config.py')}},
        'queries':queries, 'articles':[], 'candidates':[]}


def add_query(queries, config, company, dimension, group, text):
    # Query operators are a search hint; local inclusive date filtering is authoritative.
    lower = date.fromisoformat(config['start_date']) - timedelta(days=1)
    upper = date.fromisoformat(config['end_date']) + timedelta(days=1)
    params = {'engine':config['engine'], 'q':f'{text} after:{lower} before:{upper}', 'gl':config['gl'], 'hl':config['hl']}
    queries.append({'query_id':digest(params), 'execution_position':len(queries)+1,
        'target_company':company, 'discovery_dimension':dimension, 'source_group':group,
        'request_parameters':params, 'status':'pending', 'outcome':None, 'attempts':[],
        'returned_count':None, 'accepted_count':None, 'rejected_count':None, 'review_count':None})


def canonical_url(url):
    p = urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('invalid_url')
    tracking = {'gclid','fbclid','msclkid','mc_cid','mc_eid'}
    query = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in tracking]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, urlencode(query), ''))


def entity_match(company, title, snippet, pattern=BEVERAGE_CONTEXT, domain=None,
                 trade_domains=BEVERAGE_TRADE_DOMAINS, url=''):
    if company == 'industry':
        text = title + ' ' + snippet
        return ('matched', ['beverage_context']) if re.search(r'\b(?:soda|beverages?)\b', text, re.I) else ('rejected', [])
    expression = r'(?<!\w)culture[ -]+pop(?!\w)' if company == 'Culture Pop' else r'(?<!\w)' + re.escape(company) + r'(?!\w)'
    if re.search(expression, title, re.I):
        trade = domain and any(domain == d or domain.endswith('.'+d) for d in trade_domains)
        if company == 'Culture Pop' and not trade and not re.search(pattern, title + ' ' + snippet, re.I):
            return 'review', ['exact_phrase_without_beverage_context']
        evidence = ['entity_title_boundary_match']
        if company == 'Culture Pop' and trade:
            evidence.append('approved_beverage_trade_domain_context')
        return 'matched', evidence
    if re.search(expression, snippet, re.I):
        return 'review', ['snippet_only_company_evidence']
    # Inspect only the decoded URL path: hostname/query strings do not confirm an entity.
    from urllib.parse import unquote
    if re.search(expression, unquote(urlsplit(url).path), re.I):
        return 'review', ['url_only_company_evidence']
    return 'rejected', []


def parse_date(raw, anchor):
    if not raw or not isinstance(raw, str):
        return None, 'unresolved'
    value = raw.strip()
    try:
        return date.fromisoformat(value[:10]), 'day'
    except ValueError:
        pass
    for fmt in ('%m/%d/%Y', '%b %d, %Y', '%B %d, %Y'):
        try:
            part = value.split(',')[0] if fmt == '%m/%d/%Y' else value
            return datetime.strptime(part, fmt).date(), 'day'
        except ValueError:
            pass
    match = re.fullmatch(r'(\d+)\s+(minute|hour|day|week)s?\s+ago', value, re.I)
    if match:
        unit = match[2].lower() + 's'
        return (datetime.fromisoformat(anchor) - timedelta(**{unit:int(match[1])})).date(), 'relative_approximate'
    return None, 'unresolved'


def decision(result, query, config, anchor):
    reasons=[]; review=[]
    title=str(result.get('title') or ''); snippet=str(result.get('snippet') or '')
    try:
        normalized=canonical_url(result.get('link') or '')
        domain=urlsplit(normalized).hostname.removeprefix('www.')
        if not any(domain == d or domain.endswith('.'+d) for d in config['allowed_domains']):
            reasons.append('domain_not_allowed')
    except ValueError:
        normalized=None; domain=None; reasons.append('invalid_url')
    if any(t in title.lower() for t in config['excluded_title_terms']): reasons.append('excluded_title_term')
    url=(result.get('link') or '').lower()
    if any(t in url for t in config['excluded_link_terms']): reasons.append('excluded_url_pattern')
    if any(t in urlsplit(url).path for t in config['non_article_paths']): reasons.append('unsupported_page_type')
    matched=[]; evidence={}
    for company in config['companies']:
        status, why=entity_match(company,title,snippet,config['beverage_context'],domain,config['beverage_trade_domains'],normalized or '')
        if status=='matched': matched.append(company); evidence[company]=why
    status, why=entity_match(query['target_company'],title,snippet,config['beverage_context'],domain,config['beverage_trade_domains'],normalized or '')
    if status=='rejected': reasons.append('entity_not_confirmed')
    elif status=='review': review.extend(why)
    published, precision=parse_date(result.get('date'),anchor)
    if published is None: review.append('date_unresolved')
    elif not date.fromisoformat(config['start_date']) <= published <= date.fromisoformat(config['end_date']): reasons.append('outside_date_window')
    return {'decision':'rejected' if reasons else 'review' if review else 'accepted',
        'filter_reasons':reasons+review, 'normalized_url':normalized, 'publisher_domain':domain,
        'publication_date':published.isoformat() if published else None, 'date_precision':precision,
        'matched_companies':matched, 'entity_match_evidence':evidence}


def leaf_results(results):
    for result in results:
        if not isinstance(result, dict): continue
        if result.get('link'): yield result
        for key in ('stories','news_results'):
            children=result.get(key,[])
            if isinstance(children,list): yield from leaf_results(children)


def ingest(state, query, payload, anchor):
    config=state['run']['config']; counts=Counter()
    results=list(leaf_results(payload['news_results']))
    by_url={a['normalized_url']:a for a in state['articles']}
    for position, result in enumerate(results,1):
        verdict=decision(result,query,config,anchor); counts[verdict['decision']]+=1
        metadata={k:result.get(k) for k in ('title','source','date','link','snippet')}
        association={'query_id':query['query_id'], 'target_company':query['target_company'],
            'discovery_dimension':query['discovery_dimension'], 'result_position':position,
            'observed_metadata':metadata, **verdict}
        state['candidates'].append(association)
        normalized=verdict['normalized_url']
        if normalized:
            article=by_url.get(normalized)
            if article is None:
                article={'article_id':digest(normalized),'normalized_url':normalized,'original_urls':[],
                    'title':result.get('title'),'source':result.get('source'), 'publication_date':verdict['publication_date'],
                    'publication_date_raw':result.get('date'),'date_precision':verdict['date_precision'],
                    'publisher_domain':verdict['publisher_domain'],'matched_companies':[],
                    'eligibility_status':'rejected','discovery_associations':[]}
                state['articles'].append(article); by_url[normalized]=article
            article['discovery_associations'].append(association)
            if result['link'] not in article['original_urls']: article['original_urls'].append(result['link'])
            article['matched_companies']=sorted(set(article['matched_companies'])|set(verdict['matched_companies']))
            rank={'rejected':0,'review':1,'accepted':2}
            if rank[verdict['decision']] > rank[article['eligibility_status']]:
                article.update(eligibility_status=verdict['decision'],title=result.get('title'),source=result.get('source'),
                    publication_date=verdict['publication_date'],publication_date_raw=result.get('date'),date_precision=verdict['date_precision'])
    query.update(status='completed',outcome='zero_results' if not results else 'all_filtered' if counts['rejected']==len(results) else 'results',
        returned_count=len(results),accepted_count=counts['accepted'],rejected_count=counts['rejected'],review_count=counts['review'])


class ApiFailure(Exception):
    def __init__(self, reason, http_status=None, retry_after=None):
        super().__init__(reason); self.http_status=http_status; self.retry_after=retry_after


def request_api(params, key, timeout):
    # The only network endpoint in V2 is SerpAPI. Never log the key-bearing URL.
    req=Request(SERPAPI_ENDPOINT+'?'+urlencode({**params,'api_key':key}),headers={'User-Agent':'academic-discovery-v2/1.0'})
    try:
        with urlopen(req,timeout=timeout) as response:
            raw=response.read(10_000_001)
            if len(raw)>10_000_000: raise ApiFailure('response_too_large',response.status)
            payload=json.loads(raw)
    except HTTPError as exc:
        retry=None
        header=exc.headers.get('Retry-After')
        if header:
            try: retry=float(header)
            except ValueError:
                try: retry=max(0,(parsedate_to_datetime(header)-datetime.now(timezone.utc)).total_seconds())
                except (ValueError,TypeError): pass
        raise ApiFailure(f'http_error_{exc.code}',exc.code,retry) from None
    except (URLError,TimeoutError,OSError,json.JSONDecodeError):
        raise ApiFailure('network_or_invalid_response') from None
    if payload.get('error'):
        message=str(payload['error']).replace(key,'[REDACTED]')
        raise ApiFailure('api_error: '+message,200)
    # Missing results are not silently interpreted as a valid zero-result response.
    if not isinstance(payload.get('news_results'),list): raise ApiFailure('invalid_payload_missing_news_results',200)
    return payload


def checkpoint(state,path):
    state['run']['updated_at']=now()
    state['run']['counts']={'queries':dict(Counter(q['status'] for q in state['queries'])),
        'candidates':dict(Counter(c['decision'] for c in state['candidates'])),
        'unique_urls':dict(Counter(a['eligibility_status'] for a in state['articles']))}
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8') as handle:
        json.dump(state,handle,ensure_ascii=False,indent=2); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    os.replace(temp,path)


def execute(state,path,key,max_requests,request_fn=request_api,sleep=time.sleep):
    config=state['run']['config']; made=0
    for query in state['queries']:
        if query['status'] not in ('pending','error'): continue
        if len(query['attempts'])>=config['max_attempts_per_query']: continue
        if made>=max_requests: break
        retry_at=query.get('retry_at')
        if retry_at and datetime.fromisoformat(retry_at)>datetime.now(timezone.utc):
            state['run']['status']='paused_retry_wait'; checkpoint(state,path); return made
        if made: sleep(config['delay_seconds'])
        attempt={'attempt':len(query['attempts'])+1,'started_at':now(),'finished_at':None,'http_status':None,'error':None}
        query['attempts'].append(attempt); query['status']='in_flight'
        state['run']['api_requests']+=1; made+=1
        state['run']['status']='running'; checkpoint(state,path)
        try:
            payload=request_fn(query['request_parameters'],key,config['timeout_seconds'])
            ingest(state,query,payload,attempt['started_at'])
            attempt['http_status']=200
        except ApiFailure as exc:
            attempt.update(http_status=exc.http_status,error=str(exc))
            query.update(status='error',outcome='error')
            wait=max(exc.retry_after or 0,config['backoff_base_seconds']*2**(len(query['attempts'])-1))
            wait+=random.Random(config['seed']+state['run']['api_requests']).uniform(0,3)
            query['retry_at']=(datetime.now(timezone.utc)+timedelta(seconds=wait)).isoformat()
            state['run']['status']='paused_error'
        attempt['finished_at']=now(); checkpoint(state,path)
        print(query['target_company'],query['discovery_dimension'],query['status'],query['returned_count'],flush=True)
        if query['status']=='error': return made
    state['run']['status']='completed' if all(q['status']=='completed' for q in state['queries']) else 'incomplete'
    checkpoint(state,path); return made


def load_key(path):
    key=os.environ.get('SERPAPI_KEY')
    env=Path(path)
    if not key and env.is_file():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if line.strip().startswith('SERPAPI_KEY='):
                key=line.strip().split('=',1)[1].strip().strip('\"').strip("'")
    if not key or key.startswith('your_'): raise ValueError('SERPAPI_KEY missing; use the environment or --env-file with a real file')
    return key


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-date',required=True); parser.add_argument('--end-date',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--resume',action='store_true')
    parser.add_argument('--full',action='store_true',help='Explicitly opt into the 112-query schedule; default is eight-query pilot')
    parser.add_argument('--seed',type=int,default=42); parser.add_argument('--max-requests',type=int,default=8)
    parser.add_argument('--env-file',default='.env'); parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.max_requests<0: parser.error('max-requests must be nonnegative')
    try: config=make_config(args.start_date,args.end_date,not args.full,args.seed)
    except ValueError as exc: parser.error(str(exc))
    path=Path(args.output).resolve()
    # Prevent any V1, extraction, or source-file output, even on resume.
    if not path.name.startswith('news_dataset_v2') or path.suffix!='.json': parser.error('Output filename must start with news_dataset_v2 and end with .json')
    if args.resume:
        if not path.is_file(): parser.error('Resume checkpoint does not exist')
        state=json.loads(path.read_text(encoding='utf-8'))
        if state['run']['config']!=json.loads(json.dumps(config)): parser.error('Resume configuration differs from checkpoint')
        if any(q['status']=='in_flight' for q in state['queries']): parser.error('Indeterminate interrupted request: inspect checkpoint before retrying to avoid duplicate charges')
    else:
        if path.exists(): parser.error('Output exists; use --resume or a new output')
        state=make_run(config)
    if args.dry_run:
        print(json.dumps({'planned_queries':len(state['queries']),'opportunities':dict(Counter(q['target_company'] for q in state['queries']))},indent=2)); return
    if all(q['status']=='completed' for q in state['queries']):
        print('Checkpoint complete; zero additional API requests'); return
    checkpoint(state,path)
    try: key=load_key(args.env_file)
    except ValueError as exc: parser.error(str(exc))
    made=execute(state,path,key,args.max_requests)
    print(f'API requests this invocation: {made}; total: {state["run"]["api_requests"]}; status: {state["run"]["status"]}')


if __name__=='__main__': main()