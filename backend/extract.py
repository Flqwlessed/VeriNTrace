import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
from .net import request, canonical_url, ServiceError


def date_value(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        try:
            d = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError:
            d = parsedate_to_datetime(value)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        if d > datetime.now(timezone.utc):
            return None
        return d.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.article_parts, self.links, self.meta, self.jsonld = [], [], [], {}, []
        self.skip, self.article, self.script, self.in_title = 0, 0, False, False
        self.title, self.script_data = '', ''
        self.stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg'):
            self.skip += 1
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.script, self.script_data = True, ''
        if tag in ('article', 'main'):
            self.article += 1
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            self.meta[a.get('property', a.get('name', ''))] = a.get('content', '')
        if tag == 'a' and a.get('href') and not self.skip:
            self.links.append({'href': a['href'], 'inArticle': self.article > 0})

    def handle_endtag(self, tag):
        if tag == 'script' and self.script:
            try:
                self.jsonld.append(json.loads(self.script_data))
            except (ValueError, TypeError):
                pass
            self.script = False
        if tag in ('script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg'):
            self.skip = max(0, self.skip - 1)
        if tag in ('article', 'main'):
            self.article = max(0, self.article - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.script:
            self.script_data += data
        if self.in_title:
            self.title += data
        if not self.skip:
            self.parts.append(data)
            if self.article:
                self.article_parts.append(data)


def walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def extract(url):
    html, content_type, final_url = request(url)
    if 'html' not in content_type.lower():
        raise ServiceError('Only HTML articles are supported')
    p = ArticleParser()
    p.feed(html)
    text = re.sub(r'\s+', ' ', ' '.join(p.article_parts or p.parts)).strip()[:45000]
    if len(text) < 80:
        raise ServiceError('Article text unavailable or page requires JavaScript')
    published, publisher, reviews = p.meta.get('article:published_time'), '', []
    for obj in walk(p.jsonld):
        types = obj.get('@type', [])
        types = [types] if isinstance(types, str) else types
        if any(t in types for t in ('NewsArticle', 'Article', 'ReportageNewsArticle')):
            published = obj.get('datePublished', published)
            identity = obj.get('publisher', {})
            if isinstance(identity, dict):
                publisher = identity.get('name', '')
        if 'ClaimReview' in types and isinstance(obj.get('claimReviewed'), str):
            rating = obj.get('reviewRating', {})
            author = obj.get('author', {})
            reviews.append({'reviewedClaim': obj['claimReviewed'], 'rating': str(rating.get('alternateName', rating.get('ratingValue', 'Unspecified'))) if isinstance(rating, dict) else 'Unspecified', 'publisher': author.get('name', '') if isinstance(author, dict) else '', 'publishedAt': date_value(obj.get('datePublished')), 'url': final_url, 'match': 'Candidate — check claim wording'})
    links = []
    for item in p.links:
        link = canonical_url(urljoin(final_url, item['href']))
        if link and item['inArticle']:
            links.append(link)
    return {'title': p.meta.get('og:title') or p.title.strip(), 'text': text, 'publishedAt': date_value(published), 'publisher': publisher, 'url': final_url, 'links': list(dict.fromkeys(links)), 'factChecks': reviews}
