import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen
from api.dispatch import handler, _recent
from backend.demos import demo


class VercelTests(unittest.TestCase):
    def setUp(self):
        _recent.clear()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)+'/api/dispatch?route='
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def test_health_advertises_browser_history_and_no_debug(self):
        response=json.load(urlopen(self.base+'health',timeout=3))
        self.assertEqual(response['storage'],'browser');self.assertFalse(response['development'])
    def test_demo_needs_no_database(self):
        r=Request(self.base+'demos/metro',data=b'{}',headers={'Content-Type':'application/json'})
        report=json.load(urlopen(r,timeout=3));self.assertTrue(report['demo'])
    def test_stream_contains_progress_and_result(self):
        def run(text,urls,emit):
            emit('Searching evidence','running');emit('Searching evidence','available')
            result=demo('metro');result['demo']=False;return result
        with patch('api.dispatch.investigate',side_effect=run):
            request=Request(self.base+'investigate',data=b'{"text":"A synthetic claim for testing"}',headers={'Content-Type':'application/json'})
            response=urlopen(request,timeout=3)
            events=[json.loads(line) for line in response.read().splitlines()]
        self.assertEqual([e['type'] for e in events],['stage','stage','result'])
        self.assertEqual(events[-1]['result']['services']['database'],'browser')
    def test_function_failure_stream_is_explicit_error(self):
        with patch('api.dispatch.investigate',side_effect=RuntimeError('test')):
            request=Request(self.base+'investigate',data=b'{"text":"Another synthetic claim for testing"}',headers={'Content-Type':'application/json'})
            result=json.loads(urlopen(request,timeout=3).read())
        self.assertEqual(result['type'],'error');self.assertNotIn('result',result)

if __name__=='__main__':unittest.main()
