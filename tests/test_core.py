import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.database import Database
from backend.demos import demo
from backend.extract import ArticleParser, date_value
from backend.net import canonical_url, request, ServiceError
from backend.pipeline import investigate
from backend.provenance import make_graph, verdict_for
from backend.structures import PriorityQueue, DirectedGraph, TTLCache


class CoreTests(unittest.TestCase):
    def test_database_roundtrip_and_foreign_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Database(Path(directory)/'test.db');report=demo('metro');db.save(report)
            self.assertEqual(db.get(report['id']),report)
            self.assertEqual(db.history()[0]['sourceCount'],6)
            with db.connect() as c:
                self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
                self.assertEqual(c.execute('SELECT COUNT(*) FROM graph_edges').fetchone()[0],12)
    def test_url_security(self):
        for u in ['file:///etc/passwd','http://127.0.0.1','http://[::1]','http://169.254.169.254/latest','http://10.0.0.1','http://localhost','http://user:pass@example.com','https://example.com:8080']:
            self.assertIsNone(canonical_url(u),u)
        with patch('backend.net.socket.getaddrinfo',return_value=[(2,1,6,'',('10.0.0.1',443))]):
            with self.assertRaises(ServiceError):request('https://public-domain.org/article')
        self.assertEqual(canonical_url('https://example.com/a?utm_source=x&x=1#anchor'),'https://example.com/a?x=1')
    def test_heap_bfs_cache(self):
        q=PriorityQueue();q.push('low',1);q.push('high',9);q.push('tie',9)
        self.assertEqual([q.pop(),q.pop(),q.pop()],['high','tie','low'])
        g=DirectedGraph()
        for a,b in [('a','b'),('b','c'),('c','a')]:g.add_edge(a,b)
        self.assertEqual(g.path('a','c'),['a','b','c']);self.assertEqual(g.path('a','z'),[])
        cache=TTLCache(capacity=1);cache.put('a',1);cache.put('b',2)
        self.assertIsNone(cache.get('a'));self.assertEqual(cache.get('b'),2)
    def test_extraction_ignores_navigation(self):
        p=ArticleParser();p.feed('<nav><a href="/nav">Navigation</a></nav><article><p>Evidence text</p><a href="/source">Source</a><script>bad()</script></article>')
        self.assertNotIn('bad()',p.article_parts)
        self.assertEqual([x['href'] for x in p.links if x['inArticle']],['/source'])
        self.assertIsNone(date_value('not a date'));self.assertIsNone(date_value('2999-01-01'))
    def test_no_artificial_edges(self):
        s={'id':'s0','title':'Story','publisher':'example.com','url':'https://example.com/a','publishedAt':None,'stance':'context','confidence':None,'excerpt':'Context','_text':'Unrelated text','_links':[],'domain':'example.com'}
        self.assertEqual(make_graph('The railway network is permanently closing.',[s],[])['edges'],[])
        self.assertEqual(verdict_for([s],{'s0':'s0'})[0],'NOT ENOUGH EVIDENCE')
    @patch('backend.pipeline.providers.classify',return_value=({},'not_configured',[]))
    @patch('backend.pipeline.providers.fact_checks',return_value=([],'unavailable',[]))
    @patch('backend.pipeline.providers.search',return_value=([],'unavailable',['Search unavailable']))
    def test_all_providers_down(self,*args):
        r=investigate('An unverified claim with no available sources.',[])
        self.assertEqual(r['verdict'],'NOT ENOUGH EVIDENCE');self.assertEqual(r['status'],'partial')
        self.assertEqual(r['graph']['edges'],[]);self.assertFalse(r['demo'])
    def test_quotes_and_citations(self):
        claim='The city railway is closing permanently.'
        text='The city railway is closing permanently. The authority has confirmed that this claim is incorrect.'
        quote='The authority has confirmed that this claim is incorrect.'
        rows=[{'url':'https://alpha.org/article','title':'A'},{'url':'https://beta.org/article','title':'B'}]
        article={'text':text,'title':'Source','publisher':'','publishedAt':'2026-01-01T00:00:00+00:00','links':[],'factChecks':[]}
        answers={f's{i}':{'stance':'refutes','confidence':.9,'quote':quote} for i in range(2)}
        with patch('backend.pipeline.providers.search',return_value=(rows,'available',[])),patch('backend.pipeline.providers.fact_checks',return_value=([],'available',[])),patch('backend.pipeline.extract',return_value=article),patch('backend.pipeline.providers.classify',return_value=(answers,'available',[])):
            r=investigate(claim,[])
            self.assertEqual(r['verdict'],'NOT ENOUGH EVIDENCE');self.assertEqual(r['sourceGroups'],1);self.assertEqual(len(r['graph']['edges']),2)
            self.assertEqual(r['earliestSourceId'],'s0')
        bad={'s0':{'stance':'supports','confidence':.99,'quote':'This fabricated passage has never appeared in the source text at all.'}}
        with patch('backend.pipeline.providers.search',return_value=(rows,'available',[])),patch('backend.pipeline.providers.fact_checks',return_value=([],'available',[])),patch('backend.pipeline.extract',return_value=article),patch('backend.pipeline.providers.classify',return_value=(bad,'available',[])):
            r=investigate(claim+' Today?',[])
            self.assertTrue(all(s['stance']=='context' for s in r['evidence']))
            self.assertEqual(r['verdict'],'NOT ENOUGH EVIDENCE')
    @patch('backend.providers.config.TAVILY_KEY','fake')
    @patch('backend.providers.json_request',side_effect=ServiceError('API key rejected'))
    def test_rejected_key(self,*args):
        from backend.providers import search
        rows,status,warnings=search('test claim')
        self.assertEqual(status,'unavailable');self.assertEqual(rows,[]);self.assertTrue(warnings)

if __name__=='__main__':unittest.main()
