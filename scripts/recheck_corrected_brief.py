"""Independently check a corrected analysis and existing executive prose without regeneration."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyst
from analyst.runtime import prepare_crewai_runtime
from researcher.runtime import configure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-run', type=Path, required=True)
    parser.add_argument('--executive-json', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model', default='gpt-4.1')
    args = parser.parse_args()
    from executive.schema import ExecutiveBrief
    brief = ExecutiveBrief.model_validate_json(args.executive_json.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    os.environ['REVIEWER_MODEL'] = args.model
    prepare_crewai_runtime()
    configure()
    import mlflow
    mlflow.crewai.autolog()
    from reviewer.workflow import review_saved_analysis
    from reviewer.service import save_json
    from executive.handoff import make_executive_input
    from executive.audit import audit_executive
    from executive.validation import validate_brief
    from executive.render import render_html, render_markdown, presentation_data
    review_dir = args.output_dir/'review'
    review_saved_analysis(analysis_run=args.analysis_run, output_dir=review_dir)
    review_trace = mlflow.get_last_active_trace_id()
    payload, _ = make_executive_input(args.analysis_run, review_dir)
    validate_brief(brief, payload)
    output = args.output_dir/'executive'
    output.mkdir()
    save_json(output/'executive_input.json', payload)
    audit = audit_executive(brief, payload, output)
    audit_trace = mlflow.get_last_active_trace_id()
    rendered = dict(payload)
    if not audit['passed']:
        rendered['publication_status'] = 'hold_for_human_review'
    save_json(output/'executive_brief.json', brief.model_dump())
    (output/'executive_brief.html').write_text(render_html(brief, rendered), encoding='utf-8')
    (output/'executive_brief.md').write_text(render_markdown(brief, rendered), encoding='utf-8')
    mlflow.flush_trace_async_logging()
    for trace_id in (review_trace, audit_trace):
        trace = mlflow.get_trace(trace_id) if trace_id else None
        if trace is None or not trace.data.spans:
            raise RuntimeError('Live check completed but trace readback failed')
    manifest = {'publication_status': rendered['publication_status'], 'editorial_audit_passed': audit['passed'],
        'review_trace_id': review_trace, 'editorial_audit_trace_id': audit_trace,
        'prose_words': presentation_data(brief, payload)['prose_word_count'],
        'analyst_regenerated': False, 'executive_regenerated': False, 'benchmark_evaluation_run': False}
    save_json(args.output_dir/'recheck_manifest.json', manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
