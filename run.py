import json
import mimetypes
import os
import socket
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from backend import config
from backend.database import Database
from backend.demos import demo, DEMO_LABELS
from backend.pipeline import investigate, STAGES
from backend.net import canonical_url

jobs, jobs_lock = {}, threading.Lock()
slots = threading.BoundedSemaphore(2)
last_request = 0.0
database = None


def job_worker(job_id, text, urls):
    def emit(stage, state):
        with jobs_lock:
            jobs[job_id]['stages'][stage] = state
    try:
        result = investigate(text, urls, emit)
        try:
            if not database.get(result['id']):
                database.save(result)
            result['services']['database'] = 'available'
        except Exception:
            result['status'] = 'partial'
            result['services']['database'] = 'unavailable'
            result['warnings'].append('History could not be saved. This report is still available; export it before closing.')
        with jobs_lock:
            jobs[job_id].update(state='done', result=result)
    except Exception:
        with jobs_lock:
            jobs[job_id].update(state='error', error='The investigation could not be processed. Try a shorter claim; demos remain available.')
    finally:
        slots.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        super().end_headers()

    def respond(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def valid_host(self):
        return self.headers.get('Host', '') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.valid_host():
            return self.respond({'error':'Host not allowed'}, 403)
        path = urlsplit(self.path).path
        if path == '/api/history':
            try:
                return self.respond(database.history())
            except Exception:
                return self.respond({'error':'History is temporarily unavailable'}, 503)
        if path.startswith('/api/history/'):
            try:
                report = database.get(path.rsplit('/',1)[1])
                return self.respond(report or {'error':'Report not found'}, 200 if report else 404)
            except Exception:
                return self.respond({'error':'History is temporarily unavailable'},503)
        if path == '/api/demos':
            return self.respond([{'id':i,'claim':c} for i,c in DEMO_LABELS])
        if path.startswith('/api/jobs/'):
            with jobs_lock:
                job = jobs.get(path.rsplit('/',1)[1])
                return self.respond(job or {'error':'Job expired; check history'}, 200 if job else 404)
        if path == '/api/health':
            return self.respond({'ok':True, 'development':config.DEVELOPMENT})
        if path == '/api/diagnostics' and config.DEVELOPMENT:
            return self.respond({'search':'Configured; check latest report for connection status' if config.TAVILY_KEY else 'Not configured; encyclopedia fallback', 'factCheck':'Configured; not yet tested' if config.GOOGLE_KEY else 'Optional; not configured', 'llm':'Configured; not yet tested' if config.GROQ_KEY else 'Not configured; evidence-only mode', 'database':'Connected' if database else 'Failed'})
        allowed = {'/':'index.html','/history':'index.html','/index.html':'index.html','/style.css':'style.css','/favicon.svg':'favicon.svg'}
        if path.startswith('/assets/') and path.endswith('.js') and '/' not in path[8:]:
            allowed[path] = path.lstrip('/')
        if path not in allowed:
            return self.respond({'error':'Not found'},404)
        target = config.ROOT / 'web' / allowed[path]
        if not target.is_file():
            return self.respond({'error':'Asset not found'},404)
        data = target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/javascript' if target.suffix == '.js' else mimetypes.guess_type(target.name)[0] or 'text/plain')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        global last_request
        if not self.valid_host():
            return self.respond({'error':'Host not allowed'},403)
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.respond({'error':'Cross-origin request refused'},403)
        if not self.headers.get('Content-Type','').startswith('application/json'):
            return self.respond({'error':'JSON required'},415)
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 16000:
                return self.respond({'error':'Request is too large or empty'},413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise ValueError()
        except (ValueError, socket.timeout):
            return self.respond({'error':'Invalid request'},400)
        path = urlsplit(self.path).path
        if path.startswith('/api/demos/'):
            report = demo(path.rsplit('/',1)[1])
            if not report:
                return self.respond({'error':'Demo not found'},404)
            try:
                database.save(report)
            except Exception:
                report['warnings'].append('Demo could not be saved to history.')
            return self.respond(report)
        if path not in ('/api/investigate','/api/verify'):
            return self.respond({'error':'Not found'},404)
        text, urls = data.get('text'), data.get('urls',[])
        if not isinstance(text,str) or not 5 <= len(text.strip()) <= 2000:
            return self.respond({'error':'Enter a claim between 5 and 2,000 characters'},400)
        if not isinstance(urls,list) or len(urls)>5 or any(not isinstance(u,str) or len(u)>2000 or not canonical_url(u) for u in urls):
            return self.respond({'error':'Supply at most 5 public HTTP(S) article URLs'},400)
        if text.lower().startswith(('http://','https://')) and not canonical_url(text):
            return self.respond({'error':'Only public HTTP(S) article URLs are allowed'},400)
        with jobs_lock:
            if time.monotonic() - last_request < 5:
                return self.respond({'error':'Please wait 5 seconds between investigations'},429)
            if not slots.acquire(blocking=False):
                return self.respond({'error':'Two investigations are already running. Try again shortly.'},429)
            last_request = time.monotonic()
            for key in list(jobs):
                if jobs[key]['state'] != 'running' and time.time() - jobs[key]['created'] > 1800:
                    del jobs[key]
            job_id = str(uuid.uuid4())
            jobs[job_id] = {'state':'running','created':time.time(),'stages':{s:'waiting' for s in STAGES}}
        threading.Thread(target=job_worker,args=(job_id,text.strip(),urls),daemon=True).start()
        return self.respond({'jobId':job_id},202)


if __name__ == '__main__':
    if sys.version_info < (3,11):
        raise SystemExit('Please install Python 3.11 or newer.')
    try:
        database = Database()
    except Exception:
        print('SQLite unavailable. Live reports and demos still work, but history cannot be saved.')
    port = int(os.getenv('PORT','8000'))
    try:
        server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except OSError:
        raise SystemExit('Port is busy. Close the old server or set PORT=8001 in .env.')
    print(f'VeriTrace is ready: http://127.0.0.1:{port}\nKeep this terminal open. Press Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
