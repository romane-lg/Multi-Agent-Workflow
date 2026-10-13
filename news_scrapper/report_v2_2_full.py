from pathlib import Path
import json,collections,hashlib
root=Path('news_scrapper')
s=json.loads((root/'news_dataset_v2_2_full.json').read_text(encoding='utf-8'))
assert all(q['status']=='completed' or (q['status']=='error' and len(q['attempts'])>=s['run']['config']['max_attempts_per_query']) for q in s['queries']), 'Full schedule has not finished'
qs={q['query_id']:q for q in s['queries']}
arts=s['articles']; candidates=s['candidates']; companies=s['run']['config']['companies']; dimensions=list(s['run']['config']['dimensions'])
accepted=[a for a in arts if a['eligibility_status']=='accepted']
review=[a for a in arts if a['eligibility_status']=='review']
def aa(a): return [c for c in a['discovery_associations'] if c['decision']=='accepted']
def company_evidence(a): return {co for c in aa(a) for co in c['matched_companies']}
def target_evidence(a): return {c['target_company'] for c in aa(a)}
def dim_evidence(a): return {c['discovery_dimension'] for c in aa(a)}
def group_evidence(a): return {qs[c['query_id']]['source_group'] for c in aa(a)}
def counter(items): return dict(sorted(collections.Counter(items).items(),key=lambda x:str(x[0])))
requests=sum(len(q['attempts']) for q in s['queries'])
assert requests==s['run']['api_requests']
assert len(candidates)==sum(len(a['discovery_associations']) for a in arts)
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in s['run']['code_hashes'].items())
protected=json.loads((root/'v2_2_full_preservation_manifest.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
import sys
sys.path.insert(0,str(root))
import discover_v2_2 as d
assert d.load_key('.env') not in (root/'news_dataset_v2_2_full.json').read_text(encoding='utf-8')
matrix={co:{dim:sum(any(c['target_company']==co and c['discovery_dimension']==dim for c in aa(a)) for a in accepted) for dim in dimensions} for co in companies}
groups={}
for group in s['run']['config']['source_groups']:
    name=group['name']; groupqs=[q for q in s['queries'] if q['source_group']==name]
    groups[name]={'queries':len(groupqs),'returned':sum(q['returned_count'] or 0 for q in groupqs),
        'candidate_counts':counter(c['decision'] for c in candidates if qs[c['query_id']]['source_group']==name),
        'accepted_unique_urls':sum(name in group_evidence(a) for a in accepted),
        'accepted_company_query_unique_urls':sum(any(qs[c['query_id']]['source_group']==name and c['target_company']!='industry' for c in aa(a)) for a in accepted),
        'accepted_industry_query_unique_urls':sum(any(qs[c['query_id']]['source_group']==name and c['target_company']=='industry' for c in aa(a)) for a in accepted)}
domains={domain:{'returned':sum(c['publisher_domain']==domain for c in candidates),'accepted_unique_urls':sum(a['publisher_domain']==domain for a in accepted),'review_unique_urls':sum(a['publisher_domain']==domain for a in review)} for domain in s['run']['config']['allowed_domains']}
out={'run_id':s['run']['run_id'],'status':s['run']['status'],'requests':requests,
    'scheduled_queries':len(s['queries']),'retry_attempts':sum(max(0,len(q['attempts'])-1) for q in s['queries']),
    'http_status_counts':counter(str(a['http_status']) for q in s['queries'] for a in q['attempts']),
    'attempt_errors':[{'company':q['target_company'],'dimension':q['discovery_dimension'],'source_group':q['source_group'],'query_id':q['query_id'],'attempt':a} for q in s['queries'] for a in q['attempts'] if a['error']],
    'query_outcomes':counter(q['outcome'] for q in s['queries']),
    'candidate_counts':counter(c['decision'] for c in candidates), 'unique_url_counts':counter(a['eligibility_status'] for a in arts),
    'accepted_unique_by_confirmed_company':{co:sum(co in company_evidence(a) for a in accepted) for co in companies},
    'accepted_unique_by_target_query':{co:sum(co in target_evidence(a) for a in accepted) for co in companies+['industry']},
    'accepted_unique_by_dimension':{dim:sum(dim in dim_evidence(a) for a in accepted) for dim in dimensions+['industry']},
    'company_dimension_matrix':matrix,'source_groups':groups,'publishers':domains,
    'multi_associations':{'all_unique_urls':len(arts),'multiple_queries':sum(len({c['query_id'] for c in a['discovery_associations']})>1 for a in arts),
        'multiple_dimensions':sum(len({c['discovery_dimension'] for c in a['discovery_associations']})>1 for a in arts),
        'multiple_company_query_targets':sum(len({c['target_company'] for c in a['discovery_associations'] if c['target_company']!='industry'})>1 for a in arts),
        'multiple_confirmed_companies_accepted_urls':sum(len(company_evidence(a))>1 for a in accepted),
        'extra_occurrences':len(candidates)-len(arts),
        'accepted_urls_multiple_queries':sum(len({c['query_id'] for c in a['discovery_associations']})>1 for a in accepted)},
    'accepted_dates_by_month':counter(a['publication_date'][:7] if a['publication_date'] else 'unknown' for a in accepted),
    'accepted_date_precision':counter(a['date_precision'] for a in accepted),
    'accepted_date_range':[min(a['publication_date'] for a in accepted if a['publication_date']),max(a['publication_date'] for a in accepted if a['publication_date'])] if accepted else [],
    'review_dates_by_month':counter(a['publication_date'][:7] if a['publication_date'] else 'unknown' for a in review),
    'filter_reason_incidence':counter(r for c in candidates for r in c['filter_reasons']),
    'out_of_window_occurrences':[{'title':c['observed_metadata']['title'],'date':c['publication_date'],'company':c['target_company'],'dimension':c['discovery_dimension'],'source_group':qs[c['query_id']]['source_group']} for c in candidates if 'outside_date_window' in c['filter_reasons']],
    'zero_return_queries':[q for q in s['queries'] if q['returned_count']==0],
    'zero_accepted_queries':[{'company':q['target_company'],'dimension':q['discovery_dimension'],'source_group':q['source_group'],'returned':q['returned_count'],'review':q['review_count'],'outcome':q['outcome']} for q in s['queries'] if q['accepted_count']==0],
    'queries_with_no_completed_outcome':[q for q in s['queries'] if q['status']!='completed'],
    'extraction_estimate':{'accepted':len(accepted),'review_pending_human_decision':len(review),'maximum_if_all_review_approved':len(accepted)+len(review),
        'accepted_with_confirmed_company':sum(bool(company_evidence(a)) for a in accepted),'accepted_industry_without_confirmed_company':sum(not company_evidence(a) for a in accepted)},
    'preservation_verified':True,'credential_absence_verified':True,
    'accepted_titles':[{'title':a['title'],'domain':a['publisher_domain'],'companies':sorted(company_evidence(a)),'target_queries':sorted(target_evidence(a)),'dimensions':sorted(dim_evidence(a))} for a in accepted]}
assert all(not a['publication_date'] or s['run']['config']['start_date']<=a['publication_date']<=s['run']['config']['end_date'] for a in accepted)
(root/'news_dataset_v2_2_full_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Frozen V2.2 full discovery report','','Inclusive dates: 2024-10-10 through 2026-10-09. No article bodies fetched. Methodology unchanged.','',
    f"Requests/attempts: {requests}; retry attempts: {out['retry_attempts']}; HTTP statuses: {out['http_status_counts']}.",
    f"Query outcomes: {out['query_outcomes']}",f"Before URL deduplication: {out['candidate_counts']}",f"After URL deduplication: {out['unique_url_counts']}",'',
    'Company counts use confirmed entities on accepted associations; the matrix uses accepted associations from that company/dimension query. Dimension and group counts overlap; industry provenance is separate.','',
    '| Company | '+' | '.join(dimensions)+' | Confirmed company URLs |', '|---|'+'---:|'*(len(dimensions)+1)]
for co in companies: lines.append('| '+co+' | '+' | '.join(str(matrix[co][dim]) for dim in dimensions)+' | '+str(out['accepted_unique_by_confirmed_company'][co])+' |')
lines += ['',f"Accepted unique URLs by dimension: {out['accepted_unique_by_dimension']}",'', '| Source group | Returned | Accepted unique | Company query accepted | Industry query accepted |','|---|---:|---:|---:|---:|']
for name,g in groups.items(): lines.append(f"| {name} | {g['returned']} | {g['accepted_unique_urls']} | {g['accepted_company_query_unique_urls']} | {g['accepted_industry_query_unique_urls']} |")
lines += ['', '| Domain | Returned | Accepted unique | Review unique |','|---|---:|---:|---:|']
for name,g in domains.items(): lines.append(f"| {name} | {g['returned']} | {g['accepted_unique_urls']} | {g['review_unique_urls']} |")
lines += ['',f"Multi-association behavior: {out['multi_associations']}",f"Accepted date range: {out['accepted_date_range']}",f"Accepted date precision: {out['accepted_date_precision']}",f"Filter reason incidence (overlapping): {out['filter_reason_incidence']}",'', '| Accepted publication month | Unique URLs |','|---|---:|']
for month,count in out['accepted_dates_by_month'].items(): lines.append(f'| {month} | {count} |')
lines += ['',f"Extraction estimate: {out['extraction_estimate']}", '', 'All attempt errors, zero-return and zero-accepted queries, out-of-window occurrences, publisher coverage and accepted titles are enumerated in news_dataset_v2_2_full_summary.json.',
    '', 'Limits: rule acceptance is not ground-truth relevance. Dimensions are discovery provenance, not verified topics. Secondary brand/investor/executive mentions can pass title matching. Industry acceptance is category context and does not require a tracked company. Publisher-provided dates are not independently verified. Search date operators are hints, with authoritative local inclusive filtering.',
    '', 'Pre-existing discovery/CrewAI file hashes and frozen code hashes verified. Credential absence checked without exposing its value. No commit/push or body extraction.']
(root/'V2_2_FULL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('requests','retry_attempts','http_status_counts','query_outcomes','candidate_counts','unique_url_counts','accepted_unique_by_confirmed_company','accepted_unique_by_target_query','accepted_unique_by_dimension','company_dimension_matrix','source_groups','multi_associations','accepted_date_range','accepted_date_precision','filter_reason_incidence','extraction_estimate')},indent=2))

