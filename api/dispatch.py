import json
import threading
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit
from backend import config
from backend.demos import demo, DEMO_LABELS
from backend.pipeline import investigate
from backend.net import canonical_url

_slots = threading.BoundedSemaphore(2)
_lock = threading.Lock()
_recent = {}


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def route(self):
        parsed = urlsplit(self.path)
        return parse_qs(parsed.query).get('route', [parsed.path.removeprefix('/api').strip('/')])[0].strip('/')

    def response_headers(self, status, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()

    def respond(self, data, status=200):
        self.response_headers(status)
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        route = self.route()
        if route == 'health':
            return self.respond({'ok': True, 'development': False, 'storage': 'browser', 'transport': 'stream', 'version': '2.0'})
        if route == 'demos':
            return self.respond([{'id': i, 'claim': c} for i, c in DEMO_LABELS])
        return self.respond({'error': 'Not found'}, 404)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.respond({'error': 'Cross-origin request refused'}, 403)
        if not self.headers.get('Content-Type', '').startswith('application/json'):
            return self.respond({'error': 'JSON required'}, 415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                return self.respond({'error': 'Request is too large or empty'}, 413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, OSError):
            return self.respond({'error': 'Invalid request'}, 400)
        route = self.route()
        if route.startswith('demos/'):
            report = demo(route.split('/')[-1])
            return self.respond(report or {'error': 'Demo not found'}, 200 if report else 404)
        if route not in ('investigate', 'verify'):
            return self.respond({'error': 'Not found'}, 404)
        text, urls = data.get('text'), data.get('urls', [])
        if not isinstance(text, str) or not 5 <= len(text.strip()) <= 2000:
            return self.respond({'error': 'Enter a claim between 5 and 2,000 characters'}, 400)
        if not isinstance(urls, list) or len(urls) > 5 or any(not isinstance(u, str) or len(u) > 2000 or not canonical_url(u) for u in urls):
            return self.respond({'error': 'Supply at most 5 public article URLs'}, 400)
        if text.lower().startswith(('http://', 'https://')) and not canonical_url(text):
            return self.respond({'error': 'Only public article URLs are allowed'}, 400)
        client = self.headers.get('x-forwarded-for', self.client_address[0]).split(',')[0].strip()
        with _lock:
            now = time.monotonic()
            for ip in list(_recent):
                if now - _recent[ip] > 60:
                    del _recent[ip]
            if now - _recent.get(client, -100) < 5 or not _slots.acquire(blocking=False):
                return self.respond({'error': 'Please wait a few seconds and try again'}, 429)
            _recent[client] = now
        def event(data):
            self.wfile.write((json.dumps(data) + '\n').encode())
            self.wfile.flush()
        try:
            self.response_headers(200, 'application/x-ndjson; charset=utf-8')
            result = investigate(text.strip(), urls, lambda stage, state: event({'type': 'stage', 'stage': stage, 'state': state}))
            result['services']['database'] = 'browser'
            event({'type': 'result', 'result': result})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            try:
                event({'type': 'error', 'error': 'Investigation failed. Check the service messages or retry a shorter claim.'})
            except OSError:
                pass
        finally:
            _slots.release()
