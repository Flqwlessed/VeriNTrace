import http.client
import ipaddress
import json
import socket
import ssl
import time
import queue
import threading
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qsl, urlencode


class ServiceError(Exception):
    pass


def canonical_url(raw):
    try:
        u = urlsplit(raw.strip())
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
            return None
        if u.port not in (None, 80, 443):
            return None
        host = u.hostname.lower().rstrip('.')
        if host == 'localhost' or '.' not in host or host.endswith(('.local', '.internal', '.localhost', '.test', '.invalid', '.example')):
            return None
        try:
            if not ipaddress.ip_address(host.strip('[]')).is_global:
                return None
        except ValueError:
            pass
        query = urlencode([(k, v) for k, v in parse_qsl(u.query) if not k.startswith('utm_') and k not in ('fbclid', 'gclid')])
        return urlunsplit((u.scheme, u.netloc.lower(), u.path or '/', query, ''))
    except (ValueError, AttributeError):
        return None


def resolve(host, port, timeout):
    result = queue.Queue(maxsize=1)
    def lookup():
        try:
            result.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)
    threading.Thread(target=lookup, daemon=True).start()
    try:
        addresses = result.get(timeout=max(.1, timeout))
    except queue.Empty:
        raise ServiceError('DNS lookup timed out') from None
    if not addresses:
        raise ServiceError('DNS lookup failed')
    return addresses


def request(url, payload=None, headers=None, limit=2_000_000, timeout=12):
    deadline = time.monotonic() + timeout
    for _ in range(4):
        if not canonical_url(url):
            raise ServiceError('Unsafe or unsupported URL blocked')
        u = urlsplit(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ServiceError('Request timed out')
        try:
            addresses = resolve(u.hostname, u.port or (443 if u.scheme == 'https' else 80), remaining)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise ServiceError('Private network URL blocked')
            # Pin the checked address; a second DNS lookup could permit DNS rebinding.
            sock = None
            for family, kind, protocol, _, address in addresses[:4]:
                candidate = socket.socket(family, kind, protocol)
                candidate.settimeout(min(4, max(.1, deadline - time.monotonic())))
                try:
                    candidate.connect(address)
                    if u.scheme == 'https':
                        candidate = ssl.create_default_context().wrap_socket(candidate, server_hostname=u.hostname)
                    sock = candidate
                    break
                except OSError:
                    candidate.close()
                    if time.monotonic() >= deadline:
                        break
            if sock is None:
                raise ServiceError('Network unavailable, timeout, or TLS error')
            sock.settimeout(max(.1, deadline - time.monotonic()))
            conn = http.client.HTTPConnection(u.hostname, u.port, timeout=remaining)
            conn.sock = sock
            try:
                body = json.dumps(payload).encode() if payload is not None else None
                h = {'User-Agent': 'VeriTrace/1.0 (research prototype)', 'Accept-Encoding': 'identity', **(headers or {})}
                if body:
                    h['Content-Type'] = 'application/json'
                conn.request('POST' if body else 'GET', urlunsplit(('', '', u.path or '/', u.query, '')), body, h)
                response = conn.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    if payload is not None:
                        raise ServiceError('Provider redirect refused')
                    url = urljoin(url, response.getheader('Location', ''))
                    continue
                if response.status >= 400:
                    message = {400: 'Provider rejected request; check the configured model and settings', 401: 'API key rejected', 403: 'Access denied or page blocked', 429: 'Free quota or rate limit reached'}.get(response.status, 'Provider unavailable')
                    raise ServiceError(message)
                chunks, size = [], 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ServiceError('Request timed out')
                    sock.settimeout(remaining)
                    chunk = response.read1(min(65536, limit + 1 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise ServiceError('Response too large')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8', errors='replace'), response.getheader('Content-Type', ''), url
            finally:
                conn.close()
        except ServiceError:
            raise
        except (OSError, ValueError, http.client.HTTPException):
            raise ServiceError('Network unavailable, timeout, or TLS error') from None
    raise ServiceError('Too many redirects')


def json_request(url, payload=None, headers=None, timeout=12):
    try:
        text, _, _ = request(url, payload, headers, timeout=timeout)
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        raise ServiceError('Provider returned invalid data') from None
