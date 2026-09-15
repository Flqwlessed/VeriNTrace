import re
from .structures import DirectedGraph, UnionFind
from .net import canonical_url


def norm(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def make_graph(claim, sources, fact_checks):
    nodes = [{'id': 'claim', 'type': 'claim', 'label': claim, 'title': claim, 'url': None, 'publisher': '', 'publishedAt': None, 'stance': 'context', 'confidence': None, 'excerpt': ''}]
    edges = []
    by_url = {canonical_url(s['url']): s['id'] for s in sources if s['url']}
    for source in sources:
        node = {k: v for k, v in source.items() if not k.startswith('_')}
        node.update(type='article', label=source['publisher'])
        nodes.append(node)
        text = norm(source.get('_text', ''))
        exact = len(claim.split()) >= 5 and norm(claim) in text
        classified = source['stance'] in ('supports', 'refutes')
        if exact or classified:
            edges.append({'source': source['id'], 'target': 'claim', 'relationship': 'repeats_claim' if exact else 'references', 'isInferred': not exact, 'confidence': 1 if exact else source['confidence'], 'proof': 'Exact claim wording appears in retrieved text. Repetition is not endorsement.' if exact else 'Possible relationship: AI classified an exact retrieved excerpt against this claim.'})
        for link in source.get('_links', []):
            target = by_url.get(canonical_url(link))
            if target and target != source['id']:
                edges.append({'source': source['id'], 'target': target, 'relationship': 'links_to', 'isInferred': False, 'confidence': 1, 'proof': 'An article-body hyperlink in this page points to the target URL. A link alone does not prove transmission.'})
    for i, check in enumerate(fact_checks):
        node_id = 'fc' + str(i)
        nodes.append({'id': node_id, 'type': 'factcheck', 'label': check['publisher'], 'title': check['reviewedClaim'], 'publisher': check['publisher'], 'url': check['url'], 'publishedAt': check['publishedAt'], 'stance': 'context', 'confidence': None, 'excerpt': 'Publisher rating: ' + check['rating']})
        exact = norm(check['reviewedClaim']).rstrip('.!?') == norm(claim).rstrip('.!?')
        if exact:
            edges.append({'source': node_id, 'target': 'claim', 'relationship': 'fact_checks', 'isInferred': False, 'confidence': 1, 'proof': 'The fact-check database or ClaimReview metadata names the same claim wording.'})
        target = by_url.get(canonical_url(check['url']))
        if target:
            edges.append({'source': node_id, 'target': target, 'relationship': 'references', 'isInferred': False, 'confidence': 1, 'proof': 'The fact-check record points to this article URL.'})
    unique = {(e['source'], e['target'], e['relationship']): e for e in edges}
    observed = DirectedGraph()
    for node in nodes:
        observed.add_node(node['id'])
    for edge in unique.values():
        if not edge['isInferred']:
            observed.add_edge(edge['source'], edge['target'])
    return {'nodes': nodes, 'edges': list(unique.values()), 'adjacency': {node: sorted(neighbors) for node, neighbors in observed.adjacency.items()}}



def evidence_groups(sources, graph):
    union = UnionFind(s['id'] for s in sources)
    for a in sources:
        for b in sources:
            if a['id'] == b['id']:
                continue
            same_publisher = a['domain'] == b['domain'] or (a['publisher'].casefold() == b['publisher'].casefold())
            words_a = set(re.findall(r'\w+', a.get('_text', '').casefold()))
            words_b = set(re.findall(r'\w+', b.get('_text', '').casefold()))
            overlap = len(words_a & words_b) / max(1, len(words_a | words_b))
            if same_publisher or (len(words_a) >= 10 and (norm(a.get('_text', '')) == norm(b.get('_text', '')) or (len(words_a) > 30 and overlap > 0.8))):
                union.union(a['id'], b['id'])
    for edge in graph['edges']:
        if edge['relationship'] == 'links_to' and edge['source'] in union.parent and edge['target'] in union.parent:
            union.union(edge['source'], edge['target'])
    return {s['id']: union.find(s['id']) for s in sources}


def verdict_for(sources, groups):
    support = {groups[s['id']] for s in sources if s['stance'] == 'supports' and (s['confidence'] or 0) >= .8}
    refute = {groups[s['id']] for s in sources if s['stance'] == 'refutes' and (s['confidence'] or 0) >= .8}
    if support and refute:
        return 'MIXED', 'Low'
    if len(refute) >= 2:
        return 'DISPUTED', 'Moderate'
    if len(support) >= 2:
        return 'MOSTLY SUPPORTED', 'Moderate'
    return 'NOT ENOUGH EVIDENCE', 'Unrated'
