import copy
import hashlib
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlsplit
from . import providers, config
from .extract import extract, date_value
from .net import canonical_url, ServiceError
from .provenance import make_graph, evidence_groups
from .decision import publisher_role, analysis_window, verified_quote, match_checks, decide
from .structures import PriorityQueue, TTLCache

cache = TTLCache()
STAGES = ['Extracting claim', 'Searching evidence', 'Checking fact-check databases', 'Reading sources', 'Comparing evidence', 'Building provenance graph', 'Generating verdict']


def source_from(row, index):
    url = canonical_url(row.get('url', ''))
    domain = urlsplit(url).hostname or ''
    publisher, role = publisher_role(url)
    return {'id': 's' + str(index), 'url': url, 'domain': domain, 'publisher': publisher, 'title': str(row.get('title') or url), 'publishedAt': date_value(row.get('published_date')), 'sourceType': role, 'stance': 'context', 'confidence': None, 'excerpt': ' '.join(str(row.get('content') or '').split()[:24]), 'extraction': 'Search snippet only', 'signals': ['Publisher independence not verified'], '_text': '', '_links': [], '_raw': row.get('raw_content') if isinstance(row.get('raw_content'), str) else '', 'directEvidence': False}


def investigate(text, extra_urls, emit=lambda *args: None):
    key = hashlib.sha256((text.strip().casefold() + '|'.join(extra_urls)).encode()).hexdigest()
    cached = None if config.HOSTED else cache.get(key)
    if cached:
        result = copy.deepcopy(cached)
        result['cached'] = True
        for stage in STAGES:
            emit(stage, 'cached')
        return result
    warnings, services, candidates, checks = [], {}, [], []
    claim = re.sub(r'\s+', ' ', text).strip()
    emit(STAGES[0], 'running')
    input_article = None
    if text.lower().startswith(('https://', 'http://')):
        try:
            input_article = extract(text)
            claim = input_article['title'] or claim
            warnings.append('The article headline is the claim under investigation. Edit and resubmit if it is not a factual statement.')
            extra_urls = [text] + extra_urls
        except (ServiceError, ValueError):
            warnings.append('Could not read the submitted URL. Paste the factual claim as text for a useful search.')
    emit(STAGES[0], 'done')
    emit(STAGES[1], 'running')
    candidates, services['search'], messages = providers.search(claim)
    warnings.extend(messages)
    emit(STAGES[1], services['search'])
    emit(STAGES[2], 'running')
    checks, services['factCheck'], messages = providers.fact_checks(claim)
    warnings.extend(messages)
    emit(STAGES[2], services['factCheck'])
    emit(STAGES[3], 'running')
    queue, seen = PriorityQueue(), set()
    by_candidate_url = {canonical_url(row.get('url', '')): row for row in candidates}
    for row in [dict(by_candidate_url.get(canonical_url(u), {}), url=u, score=2) for u in extra_urls] + candidates:
        url = canonical_url(row.get('url', ''))
        if not url or url in seen:
            continue
        seen.add(url)
        row['url'] = url
        try:
            score = float(row.get('score', 0))
        except (ValueError, TypeError):
            score = 0
        queue.push(row, score)
    sources = [source_from(queue.pop(), i) for i in range(min(8, len(queue)))]
    def enrich(s):
        try:
            article = input_article if input_article and canonical_url(text) == s['url'] else extract(s['url'])
            s.update(title=article['title'] or s['title'], publishedAt=article['publishedAt'] or s['publishedAt'], publisher=article['publisher'] or s['publisher'], _text=article['text'], _links=article['links'], extraction='Article text retrieved', excerpt=' '.join(article['text'].split()[:24]))
            s['signals'].append('Article text retrieved directly')
            if s['publishedAt']:
                s['signals'].append('Publication date supplied by page metadata')
            return s, article['factChecks']
        except (ServiceError, ValueError):
            if len(s.get('_raw', '').strip()) >= 80:
                s.update(_text=s['_raw'][:45000], extraction='Article text supplied by search provider', excerpt=' '.join(s['_raw'].split()[:24]))
                s['signals'].append('Direct fetch unavailable; using provider-retrieved article text. Citation links cannot be observed from this fallback.')
            else:
                s['signals'].append('Article fetch blocked or unavailable; snippet is not sufficient for a verdict')
            return s, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(enrich, s) for s in sources]
        for f in as_completed(futures):
            _, found_checks = f.result()
            checks.extend(found_checks)
    # Follow only a small relevant citation frontier; never build edges from arbitrary site navigation.
    frontier = PriorityQueue()
    tokens = set(re.findall(r'[a-z]{4,}', claim.lower()))
    for s in sources:
        for link in s['_links']:
            if link in seen:
                continue
            relevance = len(tokens & set(re.findall(r'[a-z]{4,}', urlsplit(link).path.lower())))
            if relevance >= 2:
                seen.add(link)
                frontier.push({'url': link, 'title': link}, relevance)
    follow = [source_from(frontier.pop(), len(sources) + i) for i in range(min(4, len(frontier)))]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for s, found_checks in pool.map(enrich, follow):
            sources.append(s)
            checks.extend(found_checks)
    read_count = sum(bool(s['_text']) for s in sources)
    services['extraction'] = 'available' if read_count == len(sources) and sources else 'limited' if read_count else 'unavailable'
    if read_count < len(sources):
        warnings.append('Some pages could not be read. Their snippets are context only.')
    emit(STAGES[3], services['extraction'])
    emit(STAGES[4], 'running')
    check_map = {}
    for check in checks:
        url = canonical_url(check.get('url', ''))
        if url:
            check['url'] = url
            check_map[(url, check.get('reviewedClaim', ''))] = check
    checks = list(check_map.values())[:6]
    for source in sources:
        source['_analysisText'] = analysis_window(claim, source['_text'])
    classifications, services['llm'], messages = providers.classify(claim, sources, checks)
    warnings.extend(messages)
    rejected = 0
    for source in sources:
        item = classifications.get(source['id'], {})
        quote = str(item.get('quote') or '')
        stance = item.get('stance')
        confidence = item.get('confidence')
        verified = verified_quote(quote, source['_analysisText'], source['_text'])
        valid = (stance in ('supports', 'refutes', 'context') and isinstance(confidence, (float, int)) and not isinstance(confidence, bool) and 0 <= confidence <= 1 and verified is not None)
        if valid:
            source.update(stance=stance, confidence=confidence, excerpt=verified, directEvidence=item.get('directEvidence') is True)
            source['signals'].append('AI stance; excerpt verified against retrieved text')
        elif item:
            rejected += 1
    if rejected:
        warnings.append(f'{rejected} AI classifications failed quote validation and were left as context.')
    emit(STAGES[4], services['llm'])
    emit(STAGES[5], 'running')
    match_checks(claim, checks, classifications)
    if checks and services['factCheck'] == 'not_configured':
        services['factCheck'] = 'limited'
    graph = make_graph(claim, sources, checks)
    groups = evidence_groups(sources, graph)
    emit(STAGES[5], 'done')
    emit(STAGES[6], 'running')
    decision = decide(sources, groups, checks, services)
    verdict, confidence = decision['verdict'], decision['confidence']
    cited, explanation = decision['citations'], decision['explanation']
    dated = sorted([s for s in sources if s['publishedAt'] and any(e['source'] == s['id'] and e['target'] == 'claim' for e in graph['edges'])], key=lambda s: s['publishedAt'])
    report = {'version': '2.0', 'reasonCode': decision['reasonCode'], 'id': str(uuid.uuid4()), 'originalInput': text, 'claim': claim, 'createdAt': datetime.now(timezone.utc).isoformat(), 'demo': False, 'cached': False, 'status': 'partial' if any(v != 'available' for v in services.values()) else 'complete', 'verdict': verdict, 'confidence': confidence, 'explanation': explanation, 'citations': cited, 'services': services, 'warnings': list(dict.fromkeys(warnings)), 'evidence': [{k: v for k, v in s.items() if not k.startswith('_')} for s in sources], 'factChecks': checks, 'graph': graph, 'earliestSourceId': dated[0]['id'] if dated else None, 'sourceGroups': len(set(groups.values())), 'independentSources': None, 'analyzedCount': sum(s['confidence'] is not None for s in sources)}
    emit(STAGES[6], 'done')
    if not config.HOSTED and services['search'] == 'available' and services['llm'] == 'available':
        cache.put(key, copy.deepcopy(report))
    return report
