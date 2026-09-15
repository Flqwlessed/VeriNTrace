import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import run
from backend.database import Database


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        run.database=Database(Path(self.temp.name)/'test.db')
        run.last_request=0
        self.server=run.ThreadingHTTPServer(('127.0.0.1',0),run.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def get(self,path):
        return json.load(urlopen(self.base+path,timeout=3))
    def post(self,path,data):
        return json.load(urlopen(Request(self.base+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=3))
    def test_demo_history_and_static_assets(self):
        report=self.post('/api/demos/metro',{})
        self.assertTrue(report['demo']);self.assertEqual(len(report['evidence']),6)
        self.assertEqual(len(self.get('/api/history')),1)
        self.assertEqual(self.get('/api/history/'+report['id'])['graph'],report['graph'])
        for path in ['/','/assets/app.js','/assets/graph.js','/style.css']:
            self.assertEqual(urlopen(self.base+path,timeout=3).status,200)
        for path in ['/.env','/run.py','/data/veritrace.db','/assets/../../.env']:
            with self.assertRaises(HTTPError) as error:self.get(path)
            self.assertEqual(error.exception.code,404)
    def test_invalid_urls_and_origin(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/investigate',{'text':'A valid claim goes here','urls':['http://127.0.0.1/admin']})
        self.assertEqual(error.exception.code,400)
        request=Request(self.base+'/api/investigate',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://untrusted.example'})
        with self.assertRaises(HTTPError) as error:urlopen(request,timeout=3)
        self.assertEqual(error.exception.code,403)
    @patch('backend.pipeline.providers.search',return_value=([],'unavailable',[]))
    @patch('backend.pipeline.providers.fact_checks',return_value=([],'unavailable',[]))
    @patch('backend.pipeline.providers.classify',return_value=({},'unavailable',[]))
    def test_job_completes_during_provider_outage(self,*args):
        job=self.post('/api/investigate',{'text':'This HTTP test claim has no evidence.'})
        result=None
        for _ in range(100):
            state=self.get('/api/jobs/'+job['jobId'])
            if state['state']!='running':result=state;break
            time.sleep(.01)
        self.assertIsNotNone(result);self.assertEqual(result['state'],'done')
        self.assertEqual(result['result']['verdict'],'NOT ENOUGH EVIDENCE')
        self.assertEqual(result['result']['services']['database'],'available')
        self.assertEqual(len(self.get('/api/history')),1)

if __name__=='__main__':unittest.main()
