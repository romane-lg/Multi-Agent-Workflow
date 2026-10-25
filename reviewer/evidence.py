"""Required sentence checks with exact, source-validated evidence anchors."""
import json
import re
from typing import Literal

from pydantic import Field, create_model

from researcher.schema import StrictModel


class Anchor(StrictModel):
    article_id: str
    paragraph_id: str
    excerpt: str = Field(description='Exact nonempty substring copied from this original paragraph, not a generated summary.')


class FactDecision(StrictModel):
    verdict: Literal['supported', 'partial', 'unsupported']
    explanation: str = Field(description='Explain support for EVERY clause and brand in this sentence, preserving time, attribution, geography and metric scope.')
    anchors: list[Anchor]
    required_correction: str = Field(description='Concrete repair for partial/unsupported claims; empty only when fully supported.')


def sentence_checks(review_input):
    checks = {}
    for insight in review_input['analyst_report']['market_insights']:
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z“"\d])', insight['observed_fact'].strip())
        for sentence in sentences:
            if sentence:
                checks[f'fact_{len(checks)+1:03d}'] = {'insight_id': insight['insight_id'], 'claim': sentence}
    return checks


def fact_response_model(review_input):
    return create_model('RequiredSentenceEvidence', __base__=StrictModel, **{
        key: (FactDecision, Field(description=json.dumps(value, ensure_ascii=False)))
        for key, value in sentence_checks(review_input).items()})


def evidence_refs(insight, findings):
    refs = {(c['article_id'], c['paragraph_id']) for c in insight['evidence']['citations']}
    for fid in insight['evidence']['finding_ids']:
        refs.update((c['article_id'], c['paragraph_id']) for c in findings.get(fid, {}).get('citations', []))
    return refs


def validate_fact_checks(generated, review_input):
    checks = sentence_checks(review_input)
    if set(generated) != set(checks):
        raise ValueError('Every factual sentence requires a support check')
    researcher = review_input['upstream_handoff']['researcher_output']
    paragraphs = {(a['article_id'], p['paragraph_id']): p['text'] for a in researcher['sources'] for p in a['paragraphs']}
    findings = {f['finding_id']: f for f in researcher['evidence_pack']['findings']}
    insights = {i['insight_id']: i for i in review_input['analyst_report']['market_insights']}
    for key, value in generated.items():
        decision = FactDecision.model_validate(value)
        if not decision.explanation.strip():
            raise ValueError('Fact check needs an explanation')
        if decision.verdict == 'supported' and not decision.anchors:
            raise ValueError('Supported facts require exact original evidence anchors')
        if decision.verdict != 'supported' and not decision.required_correction.strip():
            raise ValueError('Unsupported or partial facts require a correction')
        allowed = evidence_refs(insights[checks[key]['insight_id']], findings)
        for anchor in decision.anchors:
            ref = (anchor.article_id, anchor.paragraph_id)
            if ref not in allowed:
                raise ValueError('Fact anchor must belong to the claim cited evidence')
            if len(anchor.excerpt.strip()) < 10 or anchor.excerpt not in paragraphs.get(ref, ''):
                raise ValueError('Fact anchor excerpt does not match original paragraph')


def focused_review_context(review_input):
    """Reduce summary repetition; retain full bodies of cited sources, not top-k alone."""
    upstream = review_input['upstream_handoff']
    researcher = upstream['researcher_output']
    findings = {f['finding_id']: f for f in researcher['evidence_pack']['findings']}
    refs = set()
    linked = set()
    for insight in review_input['analyst_report']['market_insights']:
        refs |= evidence_refs(insight, findings)
        linked.update(insight['evidence']['finding_ids'])
    cited = {a for a, _ in refs}
    from corpus.index import build_index, search
    index = build_index(researcher['sources'])
    supplements = {i['insight_id']: search(index, i['observed_fact'], limit=2, exclude_articles=cited)
                   for i in review_input['analyst_report']['market_insights']}
    context = {
        'analyst_draft_untrusted': review_input['analyst_report'],
        'required_sentence_checks': sentence_checks(review_input),
        'structural_preflight_error': review_input['structural_preflight_error'],
        'company_planning_context_not_external_evidence': upstream['company_brief'],
        'cited_finding_summaries_unverified': [f for fid, f in findings.items() if fid in linked],
        'original_sources': [a for a in researcher['sources'] if a['article_id'] in cited],
        'supplementary_search_hits_not_corroboration': supplements,
        'source_catalog': [{'article_id': a['article_id'], 'title': a['title'], 'availability': a['availability']}
                           for a in researcher['sources']],
        'exact_duplicate_bodies_not_independent_sources': index['duplicate_bodies'],
        'limits': 'Complete source corpus retained in frozen review_input.json. Working context contains full cited article bodies and limited supplementary lexical hits; retrieval is not exhaustive.',
    }
    if 'revision_feedback' in review_input:
        context['revision_feedback'] = review_input['revision_feedback']
    return json.dumps(context, ensure_ascii=False, indent=2)
