"""Conservative, auditable cleanup. Never rewrite source claims or renumber citations."""
import copy
import hashlib
import json
import re
import unicodedata


VERSION = 'visible-text-v1'
# Exact standalone UI labels only: short quotations/headings are legitimate evidence.
UI = re.compile(r'^(?:share|license|add (?:us|this) on google|listen to the article|email:?|sign up|learn more|for more information:?|for immediate release|source|advertisement|\d+ min|###)$', re.I)
TAIL = re.compile(r'^(?:recommended reading|stay informed, stay competitive|media contact:?|press contact:?)$', re.I)
BOILERPLATE = re.compile(r'^(?:keep up with the story\. subscribe to |become an insider to unlock |unlock the articles, expert interviews|filed under:)', re.I)


def repair_encoding(text):
    # Repair only reversible UTF-8 decoded as Windows-1252 sequences. Do not
    # strip accents, currencies, negatives, or unrecognized replacement chars.
    pattern = re.compile(r'(?:[\u00c2\u00c3][\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013-\u2026\u2030\u2039\u203a\u20ac\u2122]|\u00e2.{1,2}|\u00f0.{3})')
    def fix(match):
        value = match.group()
        try:
            return value.encode('cp1252').decode('utf-8')
        except (UnicodeError, ValueError):
            return value
    for _ in range(2):
        text = pattern.sub(fix, text)
    # Some old HTML snapshots already lost the undefined CP1252 closing-quote
    # byte. Repair that known punctuation artifact only, and log the alteration.
    text = re.sub('â€(?=\\s|[,.!?;:)\\]]|$)', '”', text)
    text = text.replace('â€[', '“[')
    text = re.sub('Â(?=\\s)', '', text)
    return unicodedata.normalize('NFC', ' '.join(text.replace('\u200b', '').split()))


def clean_articles(articles):
    cleaned, records = [], []
    for original in articles:
        article = copy.deepcopy(original)
        kept, changes, tail = [], [], False
        original_text = '\n\n'.join(p['text'] for p in original['paragraphs'])
        if hashlib.sha256(original_text.encode()).hexdigest() != original['text_sha256']:
            raise ValueError('Cannot clean corrupt source text')
        for paragraph in original['paragraphs']:
            text = repair_encoding(paragraph['text'])
            if TAIL.fullmatch(text):
                tail = True
            reason = 'article_tail' if tail else 'ui_label' if UI.fullmatch(text) else 'newsletter_or_footer' if BOILERPLATE.match(text) else None
            if not text:
                reason = 'empty'
            if reason:
                changes.append({'paragraph_id': paragraph['paragraph_id'], 'action': 'removed', 'reason': reason, 'original_text': paragraph['text']})
                continue
            kept.append({**paragraph, 'text': text})
            if text != paragraph['text']:
                changes.append({'paragraph_id': paragraph['paragraph_id'], 'action': 'normalized', 'original_text': paragraph['text'], 'cleaned_text': text})
        if original['availability'] == 'full_text' and not kept:
            raise ValueError('Cleanup removed every paragraph; manual source inspection required')
        article['paragraphs'] = kept
        article['text_sha256'] = hashlib.sha256('\n\n'.join(p['text'] for p in kept).encode()).hexdigest()
        cleaned.append(article)
        records.append({'article_id': article['article_id'], 'original_text_sha256': original['text_sha256'],
                        'cleaned_text_sha256': article['text_sha256'], 'changes': changes,
                        'unresolved_encoding': any('\ufffd' in p['text'] or 'â€' in p['text'] for p in kept)})
    return cleaned, {'version': VERSION, 'articles': records,
        'policy': 'Mechanical visible-text cleanup only; retained statements remain attributed source claims, not verified facts.'}


def refresh_research_sources(result, articles):
    """Reuse claims only when this exact cleanup preserved every cited paragraph."""
    from researcher.agent import validate_pack
    from researcher.schema import Article, EvidencePack
    expected, _ = clean_articles(result['sources'])
    if expected != articles:
        raise ValueError('Replacement sources must be the exact mechanical cleanup of saved sources')
    refreshed = copy.deepcopy(result)
    refreshed['sources'] = articles
    validate_pack(EvidencePack.model_validate(refreshed['evidence_pack']), [Article.model_validate(a) for a in articles],
                  refreshed['evidence_pack']['question'])
    refreshed['run']['source_preparation'] = {'version': VERSION,
        'original_sources_sha256': hashlib.sha256(json.dumps(result['sources'], sort_keys=True).encode()).hexdigest(),
        'cleaned_sources_sha256': hashlib.sha256(json.dumps(articles, sort_keys=True).encode()).hexdigest(),
        'researcher_claims_regenerated': False, 'cited_paragraphs_preserved': True,
        'note': 'Existing model findings remain unverified; downstream review checks original cleaned paragraphs independently.'}
    return refreshed
