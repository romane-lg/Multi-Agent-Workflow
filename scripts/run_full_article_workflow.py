"""Run the existing Fizzera collaboration on every accessible audited article."""
import argparse
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import analyst
from analyst.runtime import prepare_crewai_runtime
from researcher.runtime import configure
from researcher.schema import QUESTION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--articles',type=Path,required=True)
    parser.add_argument('--brief',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--research-dir',type=Path,help='Reuse an existing compatible research checkpoint directory for a new downstream attempt')
    parser.add_argument('--as-of',default=datetime.now(ZoneInfo('America/Toronto')).date().isoformat())
    parser.add_argument('--research-only',action='store_true')
    parser.add_argument('--correct-once',action='store_true',help='Assess all Reviewer feedback in one bounded correction cycle before the final brief')
    args = parser.parse_args()
    from corpus.text import clean_articles, VERSION
    from corpus.index import build_index
    articles, cleanup_audit = clean_articles(json.loads(args.articles.read_text()))
    # Preserve all source bodies. Larger-context models are used only for this
    # corpus command; the small pilot's defaults remain unchanged.
    prepare_crewai_runtime()
    configure()
    os.environ.setdefault('ANALYST_MODEL','gpt-4.1')
    os.environ.setdefault('REVIEWER_MODEL','gpt-4.1')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    from researcher.agent import SYSTEM_PROMPT
    from analyst.crew import ANALYST_INSTRUCTIONS
    from reviewer.crew import REVIEWER_INSTRUCTIONS
    from executive.crew import EXECUTIVE_INSTRUCTIONS, FINAL_EDITORIAL_CHECK
    from executive.audit import INSTRUCTIONS as EDITORIAL_AUDIT_INSTRUCTIONS
    plan = {'articles_sha256':hashlib.sha256(args.articles.read_bytes()).hexdigest(),
            'text_preparation_version': VERSION,
            'quality_policy_version': 'sentence-anchors-and-editorial-audit-v1',
            'agent_prompts_sha256': hashlib.sha256('\n'.join([SYSTEM_PROMPT, ANALYST_INSTRUCTIONS,
                REVIEWER_INSTRUCTIONS, EXECUTIVE_INSTRUCTIONS, FINAL_EDITORIAL_CHECK, EDITORIAL_AUDIT_INSTRUCTIONS]).encode()).hexdigest(),
            'brief_sha256':hashlib.sha256(args.brief.read_bytes()).hexdigest(),
            'as_of':args.as_of,'correct_once':args.correct_once,
            'analyst_model':os.environ['ANALYST_MODEL'],'reviewer_model':os.environ['REVIEWER_MODEL'],
            'executive_model':os.getenv('EXECUTIVE_MODEL','gpt-4.1')}
    plan_path = args.output_dir/'workflow_plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text())!=plan:
        raise ValueError('Workflow input, company brief, date, models or correction policy changed; choose a new output directory')
    plan_path.write_text(json.dumps(plan,indent=2))
    prepared = args.output_dir/'prepared'
    prepared.mkdir(exist_ok=True)
    for name, value in [('articles.json', articles), ('cleanup_audit.json', cleanup_audit), ('text_index.json', build_index(articles))]:
        path = prepared/name
        if path.exists() and json.loads(path.read_text()) != value:
            raise ValueError('Prepared text changed; choose a new output directory')
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    import mlflow
    mlflow.crewai.autolog()
    from corpus.research import research_corpus
    research_dir = args.research_dir or args.output_dir/'research'
    research_corpus(articles=articles,output_dir=research_dir,question=QUESTION)
    if args.research_only:
        print('Full corpus research saved:',research_dir/'researcher_output.json')
        return
    from analyst.workflow import run_workflow
    run_dir = args.output_dir/'analysis'
    pointer = run_dir/'review_location.json'
    review_dir = Path(json.loads(pointer.read_text())['path']) if pointer.exists() else run_dir/'review'
    if not (review_dir/'review_report.json').exists() and not run_dir.exists():
        run_dir.mkdir(parents=True)
        run_workflow(brief_path=args.brief,output_dir=run_dir,as_of_date=args.as_of,
                     research_output_path=research_dir/'researcher_output.json',review=True)
    if not (review_dir/'review_report.json').exists():
        if not (run_dir/'analyst_report.json').exists() and (run_dir/'analyst_raw.txt').exists():
            from corpus.finalize_saved import finalize_saved_draft
            finalize_saved_draft(run_dir)
        if not (run_dir/'analyst_report.json').exists():
            raise ValueError('No validated Analyst draft; use a new output directory with --research-dir to preserve the failed attempt')
        from reviewer.workflow import review_saved_analysis
        index = 1
        while review_dir.exists():
            review_dir = run_dir/f'review_retry_{index:02d}'
            index+=1
        review_saved_analysis(analysis_run=run_dir,output_dir=review_dir)
    pointer.write_text(json.dumps({'path':str(review_dir)},indent=2))
    review = json.loads((review_dir/'review_report.json').read_text())
    manifest_path = run_dir/'run_manifest.json'
    analysis_manifest = json.loads(manifest_path.read_text())
    analysis_manifest.update(reviewer_run=True,reviewer_verdict=review['overall_verdict'],
        publication_status=review['publication_status'],review_dir=str(review_dir))
    manifest_path.write_text(json.dumps(analysis_manifest,indent=2))
    if args.correct_once and review['assessment']['issues']:
        from analyst.revision import revise_analysis
        revision = args.output_dir/'revision'
        if not (revision/'revision_manifest.json').exists():
            revise_analysis(analysis_run=run_dir,review_dir=review_dir,output_dir=revision,
                issue_ids=[i['issue_id'] for i in review['assessment']['issues']])
        manifest = json.loads((revision/'revision_manifest.json').read_text())
        if manifest['publication_status']=='pending_review':
            raise ValueError('Correction saved but recheck incomplete. Resume with scripts/recheck_fizzera_revision.py')
        run_dir,review_dir = revision,Path(manifest['review_dir'])
    executive_dir = args.output_dir/'executive'
    from executive.workflow import write_executive_brief
    if not executive_dir.exists():
        write_executive_brief(analysis_run=run_dir,review_dir=review_dir,output_dir=executive_dir)
    elif not (executive_dir/'executive_manifest.json').exists():
        from executive.workflow import finalize_saved_executive
        finalize_saved_executive(analysis_run=run_dir,review_dir=review_dir,output_dir=executive_dir,model=plan['executive_model'])
    manifest = json.loads((executive_dir/'executive_manifest.json').read_text())
    trace_id = mlflow.get_last_active_trace_id()
    mlflow.flush_trace_async_logging()
    trace = mlflow.get_trace(trace_id) if trace_id else None
    if trace is None or not trace.data.spans:
        raise RuntimeError('Saved output exists, but trace readback failed')
    print('Persisted final trace:',trace_id,'spans:',len(trace.data.spans))
    print('Executive brief:',executive_dir/'executive_brief.html')
    print('Publication status:',manifest['publication_status'])
    (args.output_dir/'workflow_manifest.json').write_text(json.dumps({
        'plan':plan,'sources':len(articles),'readable_sources':sum(a['availability']=='full_text' for a in articles),
        'researcher_output':str(research_dir/'researcher_output.json'),'analysis_run':str(run_dir),
        'review_dir':str(review_dir),'executive_output_dir':str(executive_dir),
        'publication_status':manifest['publication_status'],'last_verified_trace_id':trace_id,
        'benchmark_evaluation_run':False},indent=2))


if __name__=='__main__':
    main()
