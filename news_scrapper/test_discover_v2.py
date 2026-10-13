"""Offline checks: no real API or publisher requests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import discover_v2 as d

START='2024-10-10'; END='2026-10-09'; ANCHOR='2026-10-10T12:00:00+00:00'

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.config=d.make_config(START,END)
        self.state=d.make_run(self.config)
        self.query=next(q for q in self.state['queries'] if q['target_company']=='Poppi')
        self.result={'title':'Poppi soda partnership launch','date':'10/10/2024, 07:00 AM, +0000 UTC','link':'https://www.bevnet.com/news/poppi'}

    def test_equal_opportunity(self):
        from collections import Counter
        self.assertEqual(len(self.state['queries']),8)
        self.assertEqual(Counter((q['target_company'],q['discovery_dimension']) for q in self.state['queries']),Counter((c,dim) for c in d.COMPANIES for dim in ('products','business')))
        self.assertEqual(len(d.make_run(d.make_config(START,END,False))['queries']),112)

    def test_poppi_not_poppies(self):
        self.assertEqual(d.entity_match('Poppi','Opium poppies bloom','')[0],'rejected')
        self.assertEqual(d.entity_match('Poppi',"Poppi's soda launch",'')[0],'matched')

    def test_culture_pop_ambiguous(self):
        self.assertEqual(d.entity_match('Culture Pop','CULTURE POP: STAR WARS MOVIE MARKETING','')[0],'review')
        self.assertEqual(d.entity_match('Culture Pop','Culture-Pop launches soda','')[0],'matched')

    def test_date_boundaries(self):
        for raw,expected in [('10/10/2024','accepted'),('10/09/2026','accepted'),('10/09/2024','rejected'),('10/10/2026','rejected'),('unknown','review')]:
            result={**self.result,'date':raw}
            self.assertEqual(d.decision(result,self.query,self.config,ANCHOR)['decision'],expected)

    def test_multi_dimension_and_company_associations(self):
        product=next(q for q in self.state['queries'] if q['target_company']=='Poppi' and q['discovery_dimension']=='products')
        business=next(q for q in self.state['queries'] if q['target_company']=='Poppi' and q['discovery_dimension']=='business')
        olipop=next(q for q in self.state['queries'] if q['target_company']=='Olipop')
        result={**self.result,'title':'Poppi and Olipop soda partnership'}
        for q in (product,business,olipop): d.ingest(self.state,q,{'news_results':[result]},ANCHOR)
        self.assertEqual(len(self.state['articles']),1)
        article=self.state['articles'][0]
        self.assertEqual(len(article['discovery_associations']),3)
        self.assertEqual(set(article['matched_companies']),{'Olipop','Poppi'})
        self.assertEqual({a['discovery_dimension'] for a in article['discovery_associations']},{'products','business'})

    def test_nested_results(self):
        self.assertEqual(len(list(d.leaf_results([{'stories':[self.result]}]))),1)

    def test_conservative_normalization(self):
        self.assertEqual(d.canonical_url('https://BEVNET.com/news?utm_source=x&id=1#part'),'https://bevnet.com/news?id=1')
        self.assertNotEqual(d.canonical_url('http://bevnet.com/news'),d.canonical_url('https://bevnet.com/news'))

    def test_resume_no_repeats(self):
        calls=[]
        def fake(params,key,timeout): calls.append(params); return {'news_results':[]}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'news_dataset_v2_test.json'
            self.assertEqual(d.execute(self.state,path,'test',4,fake,lambda seconds:None),4)
            restored=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(d.execute(restored,path,'test',4,fake,lambda seconds:None),4)
            self.assertEqual(d.execute(restored,path,'test',8,fake,lambda seconds:None),0)
            self.assertEqual(len(calls),8)
            self.assertEqual(len({json.dumps(p,sort_keys=True) for p in calls}),8)

    def test_rate_limit_recorded_then_retry(self):
        def limited(*args): raise d.ApiFailure('http_error_429',429,60)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'news_dataset_v2_test.json'
            self.assertEqual(d.execute(self.state,path,'test',8,limited,lambda seconds:None),1)
            q=self.state['queries'][0]
            self.assertEqual(q['status'],'error'); self.assertIsNone(q['returned_count'])
            self.assertEqual(q['attempts'][0]['http_status'],429)
            self.assertEqual(d.execute(self.state,path,'test',8,limited,lambda seconds:None),0)
            q['retry_at']='2000-01-01T00:00:00+00:00'
            d.execute(self.state,path,'test',1,lambda *args:{'news_results':[]},lambda seconds:None)
            self.assertEqual(q['outcome'],'zero_results'); self.assertEqual(len(q['attempts']),2)
            self.assertEqual(q['attempts'][0]['error'],'http_error_429')

    def test_api_error_http_200_is_not_zero(self):
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return b'{"error":"quota exhausted"}'
        with patch.object(d,'urlopen',return_value=Response()):
            with self.assertRaises(d.ApiFailure) as error: d.request_api({},'test',30)
        self.assertEqual(error.exception.http_status,200)
        self.assertIn('quota exhausted',str(error.exception))

if __name__=='__main__': unittest.main(verbosity=2)