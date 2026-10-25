"""Resume small Researcher calls and merge every source without citation collisions."""
import hashlib
import json
import os
from pathlib import Path

import mlflow

from researcher.agent import research, SYSTEM_PROMPT, validate_pack
from researcher.schema import Article, ArticleAssessment, COMPANIES, Coverage, EvidencePack


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def merge_batches(articles, results, question):
    sources = [Article.model_validate(a) for a in articles]
    assessments, findings = [], []
    seen_sources = set()
    for number, result in enumerate(results, 1):
        batch_sources = [Article.model_validate(a) for a in result['sources']]
        pack = EvidencePack.model_validate(result['evidence_pack'])
        validate_pack(pack, batch_sources, question)
        ids = {a.article_id for a in batch_sources}
        if seen_sources & ids:
            raise ValueError('A source appears in multiple research batches')
        seen_sources |= ids
        assessments.extend(pack.article_assessments)
        for finding in pack.findings:
            findings.append(finding.model_copy(update={'finding_id':f'b{number:04d}__{finding.finding_id}'}))
    expected = {a.article_id for a in sources if a.availability == 'full_text'}
    if seen_sources != expected:
        raise ValueError('Research batches do not cover every accessible source exactly once')
    original = {a.article_id:a.model_dump() for a in sources}
    for result in results:
        if any(original[a['article_id']] != a for a in result['sources']):
            raise ValueError('Batch source differs from the frozen corpus')
    assessments.extend(ArticleAssessment(article_id=a.article_id,relevance='unavailable',summary='',
        reason=f'No article body supplied: {a.access_note}') for a in sources if a.availability=='unavailable')
    order = {a.article_id:i for i,a in enumerate(sources)}
    coverage = []
    for company in COMPANIES:
        ids = [f.finding_id for f in findings if company in f.companies]
        coverage.append(Coverage(company=company,finding_ids=ids,
            gap='' if ids else 'No usable findings for this company in accessible source text.'))
    pack = EvidencePack(question=question, article_assessments=sorted(assessments,key=lambda a:order[a.article_id]),
        findings=findings, company_coverage=coverage,
        limitations=['Full accepted discovery pool; inaccessible bodies remain explicit gaps.',
            'Small batches were researched separately; repeated events and syndicated releases are not independent corroboration.',
            'Publisher/executive metrics are reported claims. Observational stories do not establish causal ROI.',
            'Dates reflect the historical discovery snapshot, not a fresh comprehensive market scan.'])
    validate_pack(pack, sources, question)
    return {'evidence_pack':pack.model_dump(),'sources':[a.model_dump() for a in sources],
            'run':{'mode':'full_corpus_batched', 'batches':len(results),
                   'llm_calls':sum(r['run'].get('llm_calls',1) for r in results),
                   'batch_runs':[r['run'] for r in results], 'sources_digest':digest(articles)}}


@mlflow.trace(name='full_corpus_research', span_type='CHAIN')
def research_corpus(*, articles: list[dict], output_dir: Path, question: str, batch_size=5):
    if not 1 <= batch_size <= 5:
        raise ValueError('Research batches must contain 1-5 sources')
    sources = [Article.model_validate(a) for a in articles]
    if not sources or len({a.article_id for a in sources}) != len(sources):
        raise ValueError('Corpus must contain unique sources')
    for a in sources:
        text = '\n\n'.join(p.text for p in a.paragraphs)
        if hashlib.sha256(text.encode()).hexdigest() != a.text_sha256 or (a.availability=='full_text') != bool(a.paragraphs):
            raise ValueError('Corpus source integrity failure')
    accessible = [a.model_dump() for a in sources if a.availability=='full_text']
    if not accessible:
        raise ValueError('No accessible article bodies to research')
    output_dir.mkdir(parents=True,exist_ok=True)
    plan = {'sources_sha256':digest(articles),'question':question,'batch_size':batch_size,
            'model':os.getenv('RESEARCHER_MODEL','gpt-4o-mini'),
            'prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()}
    plan_path = output_dir/'research_plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError('Resume plan changed: corpus, model, question, prompt and batch size must match')
    plan_path.write_text(json.dumps(plan,indent=2))
    results = []
    for number, start in enumerate(range(0,len(accessible),batch_size),1):
        batch = accessible[start:start+batch_size]
        path = output_dir/f'batch_{number:04d}.json'
        if path.exists():
            saved = json.loads(path.read_text())
            if saved['input_sha256'] != digest(batch) or saved['result']['sources'] != batch:
                raise ValueError('Saved research batch does not match corpus input')
            result = saved['result']
            validate_pack(EvidencePack.model_validate(result['evidence_pack']),[Article.model_validate(a) for a in batch],question)
            print('Research batch reused:',number,flush=True)
        else:
            try:
                result = research(question=question,articles=batch)
            except ValueError as exc:
                (output_dir/f'batch_{number:04d}_failure.json').write_text(json.dumps(
                    {'error_type':type(exc).__name__,'message':str(exc),'batch_size':len(batch),
                     'recovery':'isolate each article; do not repair factual citations'},indent=2))
                if len(batch)==1:
                    raise
                isolated = []
                for index,article in enumerate(batch,1):
                    checkpoint = output_dir/f'batch_{number:04d}_article_{index:02d}.json'
                    if checkpoint.exists():
                        record = json.loads(checkpoint.read_text())
                        if record['input_sha256'] != digest([article]):
                            raise ValueError('Isolated article checkpoint mismatch')
                        item = record['result']
                    else:
                        item = research(question=question,articles=[article])
                        with checkpoint.open('x') as handle:
                            json.dump({'input_sha256':digest([article]),'result':item},handle,ensure_ascii=False,indent=2)
                    isolated.append(item)
                result = merge_batches(batch,isolated,question)
                result['run']['failed_batch_call'] = True
                result['run']['llm_calls'] += 1
                print('Research batch isolated after validation failure:',number,flush=True)
            except Exception as exc:
                (output_dir/f'batch_{number:04d}_failure.json').write_text(json.dumps(
                    {'error_type':type(exc).__name__,'message':str(exc),'batch_size':len(batch)},indent=2))
                raise
            with path.open('x') as handle:
                json.dump({'input_sha256':digest(batch),'result':result},handle,ensure_ascii=False,indent=2)
            print('Research batch completed:',number,'sources:',len(batch),flush=True)
        results.append(result)
    merged = merge_batches(articles,results,question)
    target = output_dir/'researcher_output.json'
    if target.exists() and json.loads(target.read_text()) != merged:
        raise ValueError('Completed corpus research changed on resume')
    target.write_text(json.dumps(merged,ensure_ascii=False,indent=2))
    return merged
