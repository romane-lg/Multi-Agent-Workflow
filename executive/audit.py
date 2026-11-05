from executive.audit_contract import BriefAnchor, EditorialCheck, editorial_fields, audit_model, INSTRUCTIONS, validate_audit
"""Review the editor's actual prose, since upstream review cannot approve new wording."""
import hashlib
import json
import os
from typing import Literal

import mlflow
from pydantic import Field, create_model

from researcher.schema import StrictModel
from reviewer.evidence import Anchor














@mlflow.trace(name='executive_prose_evidence_audit', span_type='AGENT')
def audit_executive(brief, payload, output_dir):
    from crewai import Agent, Crew, LLM, Process, Task
    from reviewer.service import save_json
    from reviewer.handoff import digest
    upstream = payload['analysis']['upstream_handoff']
    # Keep complete original sources and explicit decision status. No reliance on
    # the executive's broad source ledger as a substitute for semantic checking.
    context = json.dumps({'executive': brief.model_dump(), 'analysis': payload['analysis']['analyst_report'],
        'company_brief': upstream['company_brief'], 'sources': upstream['researcher_output']['sources'],
        'review_state': payload['review']['assessment']}, ensure_ascii=False)
    llm = LLM(model=os.getenv('REVIEWER_MODEL', 'gpt-4.1'), temperature=0, max_tokens=11000, timeout=240, max_retries=0)
    from corpus.budget import check_context
    check_context(context, llm.model)
    agent = Agent(role='Executive evidence auditor', goal='Verify final wording without inheriting approval from upstream.',
        backstory='You verify exact evidence and preserve proposal and uncertainty labels.', llm=llm,
        tools=[], allow_delegation=False, max_iter=1, max_retry_limit=0, respect_context_window=False, verbose=False)
    model = audit_model(brief)
    task = Task(description=INSTRUCTIONS+'\n\nFROZEN INPUT:\n{context}', expected_output='Every required editorial check with exact evidence anchors.',
        agent=agent, response_model=model, output_pydantic=model, guardrail_max_retries=0)
    output = Crew(agents=[agent], tasks=[task], process=Process.sequential,
        memory=False, planning=False, cache=False, verbose=False, tracing=False).kickoff(inputs={'context': context})
    (output_dir/'editorial_audit_raw.txt').write_text(output.raw, encoding='utf-8')
    checks = validate_audit(output.pydantic.model_dump() if output.pydantic else json.loads(output.raw), brief, payload)
    result = {'checks': checks, 'passed': all(c['verdict'] == 'supported' for c in checks.values()),
        'executive_sha256': digest(brief.model_dump()), 'input_sha256': payload['executive_input_sha256'],
        'model': llm.model, 'prompt_sha256': hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(),
        'usage': output.token_usage.model_dump() if output.token_usage else {}}
    save_json(output_dir/'editorial_audit.json', result)
    return result
