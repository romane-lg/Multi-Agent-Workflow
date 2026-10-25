"""Validate a saved raw draft after a documented legal-name alias mismatch."""
import hashlib
import json
from pathlib import Path

from analyst.handoff import make_handoff
from analyst.render import render_report
from analyst.schema import AnalystReport, CompanyBrief
from analyst.validation import canonicalize_documented_company_alias, validate_report
from reviewer.service import save_json


def finalize_saved_draft(run_dir: Path):
    if (run_dir/'analyst_report.json').exists():
        raise ValueError('Analysis is already finalized')
    handoff = json.loads((run_dir/'handoff.json').read_text())
    brief = CompanyBrief.model_validate(handoff['company_brief'])
    verified,_ = make_handoff(handoff['researcher_output'],brief,handoff['as_of_date'])
    if verified['handoff_sha256'] != handoff['handoff_sha256']:
        raise ValueError('Saved handoff hash mismatch')
    text = '\n\f\n'.join(p.text for p in brief.pages)
    if hashlib.sha256(text.encode()).hexdigest()!=brief.text_sha256:
        raise ValueError('Company brief text hash mismatch')
    raw = (run_dir/'analyst_raw.txt').read_text()
    generated = AnalystReport.model_validate_json(raw)
    report = canonicalize_documented_company_alias(generated,brief)
    validate_report(report,handoff['researcher_output'],brief,handoff['as_of_date'])
    save_json(run_dir/'analyst_report.json',report.model_dump())
    (run_dir/'analyst_report.md').write_text(render_report(report,handoff['researcher_output'],brief))
    save_json(run_dir/'run_manifest.json',{
        'workflow':'CrewAI: saved Researcher -> Analyst (validated saved raw draft) -> independent Reviewer',
        'researcher_mode':'reuse_saved_output','handoff_sha256':handoff['handoff_sha256'],
        'as_of_date':handoff['as_of_date'],'review_requested':True,'reviewer_run':False,
        'publication_status':'pending_review','analyst_usage':None,
        'usage_note':'Original paid call is in MLflow; saved raw text has no standalone usage record.',
        'model_generated_company_name':generated.company_name,
        'company_alias_normalized':generated.company_name!=report.company_name,
        'raw_response_sha256':hashlib.sha256(raw.encode()).hexdigest(),
        'model_call_repeated':False,'quality_evaluation_run':False})
    return report
