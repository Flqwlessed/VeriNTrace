import re
import unicodedata
from urllib.parse import urlsplit

# These identities are source-role signals, not universal website truth scores.
PUBLISHERS = {
    'factcheck.org': ('FactCheck.org', 'Fact-check organization'),
    'snopes.com': ('Snopes', 'Fact-check organization'),
    'politifact.com': ('PolitiFact', 'Fact-check organization'),
    'fullfact.org': ('Full Fact', 'Fact-check organization'),
    'factcheck.afp.com': ('AFP Fact Check', 'Fact-check organization'),
    'altnews.in': ('Alt News', 'Fact-check organization'),
    'boomlive.in': ('BOOM', 'Fact-check organization'),
    'reuters.com': ('Reuters', 'Wire service'),
    'apnews.com': ('Associated Press', 'Wire service'),
    'nasa.gov': ('NASA', 'Official source'),
}


def publisher_role(url):
    host = (urlsplit(url or '').hostname or '').lower()
    for domain, role in PUBLISHERS.items():
        if host == domain or host.endswith('.' + domain):
            return role
    return host, 'Unknown'


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(text))).strip()


def same_wording(a, b):
    a, b = normalized(a).casefold(), normalized(b).casefold()
    return bool(a) and a.rstrip('.!?') == b.rstrip('.!?')


def verified_quote(quote, analysis, full_text):
    quote = normalized(quote)
    if 3 <= len(quote.split()) <= 45 and quote in normalized(analysis) and quote in normalized(full_text):
        return quote
    return None


def analysis_window(claim, text):
    text = normalized(text)
    terms = set(re.findall(r'\w{4,}', claim.casefold()))
    chunks = [text[i:i + 1200] for i in range(0, len(text), 850)]
    verdict_terms = {'false', 'incorrect', 'hoax', 'fabricated', 'untrue', 'true', 'confirmed', 'debunked'}
    def rank(chunk):
        words = set(re.findall(r'\w{4,}', chunk.casefold()))
        return len(terms & words) + min(2, len(verdict_terms & words))
    best = max(chunks, key=rank, default='')
    if text.startswith(best):
        return text[:1800]
    return text[:550] + '\n[Separate passage]\n' + best


def rating_stance(value):
    label = normalized(value).casefold().strip(' .!')
    if label in {'false', 'incorrect', 'fake', 'hoax', 'pants on fire', 'pants on fire!'}:
        return 'refutes'
    if label in {'true', 'correct', 'accurate'}:
        return 'supports'
    return None


def match_checks(claim, checks, classifications):
    matches = classifications.get('_factCheckMatches', {})
    for index, check in enumerate(checks):
        check['id'] = 'fc' + str(index)
        check['stance'] = rating_stance(check.get('rating', '')) or 'context'
        candidate = matches.get(check['id'], {})
        exact = same_wording(claim, check.get('reviewedClaim', ''))
        score = candidate.get('confidence', 0)
        numbers_agree = set(re.findall(r'\d+', claim)) == set(re.findall(r'\d+', check.get('reviewedClaim', '')))
        semantic = (numbers_agree and candidate.get('match') == 'same' and isinstance(score, (int, float))
                    and not isinstance(score, bool) and .9 <= score <= 1)
        check['matched'] = exact or semantic
        check['matchInferred'] = not exact
        check['match'] = ('Exact reviewed wording' if exact else 'AI-matched claim; inspect wording' if semantic else 'Candidate — claim match not established')


def decide(sources, groups, checks, services):
    candidates = []
    for source in sources:
        if source.get('stance') not in ('supports', 'refutes'):
            continue
        confidence = source.get('confidence') or 0
        direct = source.get('directEvidence') is True
        if confidence < .75 or not direct:
            continue
        role = publisher_role(source.get('url'))[1]
        strong = role != 'Unknown' and confidence >= .85
        candidates.append({'id': source['id'], 'stance': source['stance'], 'group': groups[source['id']], 'strong': strong, 'review': False})
    for check in checks:
        if not check.get('matched') or check.get('stance') not in ('supports', 'refutes'):
            continue
        role = publisher_role(check.get('url'))[1]
        if role not in ('Fact-check organization', 'Wire service'):
            continue
        candidates.append({'id': check['id'], 'stance': check['stance'], 'group': check['url'], 'strong': True, 'review': True})
    support = [c for c in candidates if c['stance'] == 'supports']
    refute = [c for c in candidates if c['stance'] == 'refutes']
    cited = list(dict.fromkeys(c['id'] for c in candidates))
    if support and refute:
        return {'verdict': 'UNABLE TO VERIFY', 'confidence': 'Unrated', 'citations': cited,
                'reasonCode': 'CONFLICTING_EVIDENCE', 'explanation': 'The retrieved evidence conflicts about the exact claim. A single true/false label would hide that disagreement; inspect the linked passages and their dates.'}
    for stance, items, verdict in [('refutes', refute, 'FALSE'), ('supports', support, 'TRUE')]:
        grouped = {item['group'] for item in items}
        if any(item['strong'] for item in items) or len(grouped) >= 2:
            reviews = any(item['review'] for item in items)
            description = 'A matching published fact check rates this claim as ' if reviews else 'The cited retrieved evidence directly ' + ('contradicts' if stance == 'refutes' else 'supports') + ' this claim.'
            explanation = description + verdict.lower() + '.' if reviews else description
            explanation += ' This is an automated evidence-based assessment; the linked sources show the basis for it.'
            return {'verdict': verdict, 'confidence': 'Moderate', 'citations': list(dict.fromkeys(item['id'] for item in items)), 'reasonCode': 'MATCHED_FACT_CHECK' if reviews else 'DIRECT_EVIDENCE', 'explanation': explanation}
    if not sources and not checks:
        reason, explanation = 'NO_SOURCES', 'No usable sources were retrieved. Check the search service status or add a public article URL; this is not a judgment that the claim is true or false.'
    elif services.get('llm') in ('unavailable', 'not_configured'):
        reason, explanation = 'ANALYSIS_UNAVAILABLE', 'Evidence analysis could not run. Check the Groq service message below and your key/model setting, then retry; the retrieved links are still available.'
    elif not any(s.get('_text') for s in sources):
        reason, explanation = 'NO_READABLE_EVIDENCE', 'Sources were found, but their article text could not be read. A search snippet alone is not enough for a true/false verdict; try an accessible source URL.'
    else:
        reason, explanation = 'INCONCLUSIVE_EVIDENCE', 'The sources do not clearly settle this exact claim. Check the date, place and wording, or add a direct source; unrelated material and repetition of a rumor are not proof.'
    return {'verdict': 'UNABLE TO VERIFY', 'confidence': 'Unrated', 'citations': cited, 'reasonCode': reason, 'explanation': explanation}
