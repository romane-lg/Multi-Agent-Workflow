"""Offline extraction, access-accounting and full-corpus research contracts."""
import copy
from email.message import Message
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from corpus.access import public_text, RobustFetcher, summarize
from corpus.research import merge_batches, research_corpus
from corpus.budget import check_context
from corpus.browser import rendered_article_html
from news_scrapper.extract_content import ExtractionFailure, Fetcher
from researcher.schema import QUESTION
from analyst.test_workflow import evidence


BODY = ' '.join(f'Poppi announced beverage retail development number {i}, with distribution and consumer research context for the brand.' for i in range(20))


def document(extra='',article=True):
    container = 'article' if article else 'div'
    return f'<html><title>Poppi retail announcement</title><head><script type="application/ld+json">{{"isAccessibleForFree":false}}</script></head><body><{container}><h1>Poppi retail announcement</h1><p>{BODY}</p></{container}>{extra}</body></html>'.encode()


def batch(article_id):
    result = copy.deepcopy(evidence())
    result['sources'][0]['article_id'] = article_id
    pack = result['evidence_pack']
    pack['article_assessments'][0]['article_id'] = article_id
    for finding in pack['findings']:
        for citation in finding['citations']:
            citation['article_id'] = article_id
    result['run'] = {'llm_calls':1}
    return result


class CorpusTests(unittest.TestCase):
    def test_public_article_not_rejected_for_metadata_or_footer_subscription(self):
        text,method,restricted = public_text(document('<footer>Already a subscriber? Subscribe to continue reading.</footer>'),'https://example.com/story')
        self.assertIn('Poppi announced beverage',text)
        self.assertNotIn('Already a subscriber',text)
        self.assertTrue(restricted)

    def test_rendered_unicode_is_preserved(self):
        visible = BODY.replace('Poppi announced','Poppi’s café announced')
        text,_,_ = public_text(rendered_article_html('Poppi’s café',visible),'https://example.com/story')
        self.assertIn('Poppi’s café',text)
        self.assertNotIn('â€',text)

    def test_visible_subscription_gate_remains_blocked(self):
        body = document().replace(b'</article>',b'<p>Subscribe to continue reading.</p></article>')
        with self.assertRaisesRegex(ExtractionFailure,'subscription_gate'):
            public_text(body,'https://example.com/story')

    def test_hidden_article_and_challenge_not_extracted(self):
        for body in (b'<html><title>Just a moment</title>Verify you are human</html>',
                     f'<html><body><article style="display: none">{BODY}</article>Short teaser.</body></html>'.encode()):
            with self.assertRaises(ExtractionFailure):
                public_text(body,'https://example.com/story')

    def test_restricted_metadata_without_public_article_container_rejected(self):
        with self.assertRaisesRegex(ExtractionFailure,'restricted_metadata'):
            public_text(document(article=False),'https://example.com/story')

    def test_robots_redirect_and_explicit_disallow(self):
        with TemporaryDirectory() as folder:
            fetcher = RobustFetcher(0,folder)
            redirect = Message(); redirect['Location']='/robots-policy.txt'
            text = Message(); text['Content-Type']='text/plain'
            with patch.object(fetcher,'request',side_effect=[(301,redirect,b''),(200,text,b'User-agent: *\nDisallow: /private')]):
                self.assertEqual(fetcher.permission('https://example.com/story'),0)
                with self.assertRaisesRegex(ExtractionFailure,'robots_disallowed'):
                    fetcher.permission('https://example.com/private/story')

    def test_legacy_and_enhanced_share_responses_without_new_requests(self):
        headers = Message(); headers['Content-Type']='text/html'
        robots = Message(); robots['Content-Type']='text/plain'
        def request(url,delay):
            return (200,robots,b'User-agent: *\nAllow: /') if url.endswith('/robots.txt') else (200,headers,document())
        legacy = Fetcher(0)
        with patch.object(legacy,'request',side_effect=request):
            old = legacy.extract({'link':'https://example.com/story'})
        with TemporaryDirectory() as folder:
            enhanced = RobustFetcher(0,folder)
            with patch.object(enhanced,'request',side_effect=request):
                new = enhanced.extract({'link':'https://example.com/story'})
        self.assertEqual(old['extraction_error'],'paywall_detected')
        self.assertEqual(new['extraction_status'],'success')
        self.assertGreaterEqual(new['word_count'],100)

    def test_robots_failure_is_not_counted_as_confirmed_article_block(self):
        rows = [{'baseline':{'extraction_status':'failed'},'enhanced':{'extraction_status':'failed','extraction_error':reason}}
                for reason in ('robots_unavailable','access_denied','network_error')]
        stats = summarize(rows,4)
        self.assertEqual(stats['enhanced_unavailable'],3)
        self.assertEqual(stats['direct_article_access_barriers'],1)
        self.assertEqual(stats['remaining_urls'],1)
        self.assertEqual(stats['direct_barrier_percent_of_checked'],33.33)

    def test_merge_covers_all_sources_and_namespaces_duplicate_finding_ids(self):
        a,b = batch('a1'),batch('a2')
        missing = copy.deepcopy(a['sources'][0])
        missing.update(article_id='a3',availability='unavailable',paragraphs=[],text_sha256=hashlib.sha256(b'').hexdigest())
        result = merge_batches(a['sources']+b['sources']+[missing],[a,b],QUESTION)
        ids = [f['finding_id'] for f in result['evidence_pack']['findings']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(any(i.startswith('b0002__') for i in ids))
        self.assertEqual(len(result['evidence_pack']['article_assessments']),3)
        self.assertEqual(result['evidence_pack']['article_assessments'][-1]['relevance'],'unavailable')
        self.assertEqual(len(result['sources']),3)

    def test_merge_rejects_missing_accessible_source_or_changed_source(self):
        a,b = batch('a1'),batch('a2')
        with self.assertRaisesRegex(ValueError,'every accessible'):
            merge_batches(a['sources']+b['sources'],[a],QUESTION)
        changed = copy.deepcopy(a)
        changed['sources'][0]['paragraphs'][0]['text']+=' Altered.'
        with self.assertRaisesRegex(ValueError,'differs'):
            merge_batches(a['sources'],[changed],QUESTION)

    def test_resume_reuses_completed_research_calls_and_detects_plan_change(self):
        a,b = batch('a1'),batch('a2')
        articles = a['sources']+b['sources']
        with TemporaryDirectory() as folder:
            with patch('corpus.research.research',side_effect=[a,b]) as model:
                result = research_corpus.__wrapped__(articles=articles,output_dir=Path(folder),question=QUESTION,batch_size=1)
                self.assertEqual(model.call_count,2)
            with patch('corpus.research.research',side_effect=AssertionError('Must not call again')):
                self.assertEqual(research_corpus.__wrapped__(articles=articles,output_dir=Path(folder),question=QUESTION,batch_size=1),result)
            with self.assertRaisesRegex(ValueError,'Resume plan changed'):
                research_corpus.__wrapped__(articles=articles,output_dir=Path(folder),question='Changed question',batch_size=1)

    def test_corrupt_corpus_stops_before_paid_calls(self):
        articles = batch('a1')['sources']
        articles[0]['paragraphs'][0]['text']+=' Changed.'
        with TemporaryDirectory() as folder,patch('corpus.research.research') as model:
            with self.assertRaisesRegex(ValueError,'integrity'):
                research_corpus.__wrapped__(articles=articles,output_dir=Path(folder),question=QUESTION)
            model.assert_not_called()

    def test_context_limit_preserves_sources_or_stops_without_truncation(self):
        from unittest.mock import MagicMock
        encoder = MagicMock()
        encoder.encode.return_value = range(100001)
        with patch('tiktoken.get_encoding',return_value=encoder):
            with self.assertRaisesRegex(ValueError,'No source was truncated'):
                check_context('Complete original context','gpt-4o-mini')
            self.assertEqual(check_context('Complete original context','gpt-4.1'),100001)

    def test_invalid_multi_article_batch_is_isolated_and_cached(self):
        a,b = batch('a1'),batch('a2')
        with TemporaryDirectory() as folder:
            with patch('corpus.research.research',side_effect=[ValueError('Mixed publication dates'),a,b]) as model:
                result = research_corpus.__wrapped__(articles=a['sources']+b['sources'],output_dir=Path(folder),question=QUESTION)
                self.assertEqual(model.call_count,3)
            self.assertEqual(result['run']['llm_calls'],3)
            self.assertTrue((Path(folder)/'batch_0001_article_02.json').is_file())
            with patch('corpus.research.research',side_effect=AssertionError('Must reuse cache')):
                self.assertEqual(research_corpus.__wrapped__(articles=a['sources']+b['sources'],output_dir=Path(folder),question=QUESTION),result)

    def test_only_documented_company_aliases_are_normalized(self):
        from analyst.schema import CompanyBrief
        from analyst.test_workflow import brief,report
        from analyst.validation import canonicalize_documented_company_alias
        company = brief()
        company.pages[0].text += ' Fizzera Beverages Inc. and competitor Poppi.'
        value = report()
        value.company_name = 'Fizzera Beverages Inc.'
        normalized = canonicalize_documented_company_alias(value,company)
        self.assertEqual(normalized.company_name,'Fizzera')
        self.assertEqual(normalized.market_insights,value.market_insights)
        for bad in ('Poppi','Fizzera Unknown Company'):
            value.company_name = bad
            self.assertEqual(canonicalize_documented_company_alias(value,company).company_name,bad)

    def test_saved_raw_draft_can_resume_after_verified_alias_without_model_call(self):
        from analyst.handoff import make_handoff
        from analyst.test_workflow import report
        from reviewer.test_reviewer import company_brief
        from corpus.finalize_saved import finalize_saved_draft
        company = company_brief()
        company.pages[0].text += ' Fizzera Beverages Inc.'
        company.text_sha256 = hashlib.sha256('\n\f\n'.join(p.text for p in company.pages).encode()).hexdigest()
        handoff,_ = make_handoff(evidence(),company,'2026-10-16')
        draft = report()
        draft.company_name = 'Fizzera Beverages Inc.'
        with TemporaryDirectory() as folder:
            path = Path(folder)
            (path/'handoff.json').write_text(json.dumps(handoff))
            (path/'analyst_raw.txt').write_text(draft.model_dump_json())
            original = (path/'analyst_raw.txt').read_bytes()
            finalized = finalize_saved_draft(path)
            self.assertEqual(finalized.company_name,'Fizzera')
            self.assertEqual((path/'analyst_raw.txt').read_bytes(),original)
            self.assertFalse(json.loads((path/'run_manifest.json').read_text())['model_call_repeated'])


if __name__=='__main__':
    unittest.main()
