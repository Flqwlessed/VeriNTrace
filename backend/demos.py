import uuid
from datetime import datetime, timezone

DEMO_LABELS = [
    ('metro', 'Metrovale is closing its entire metro network for six months.'),
    ('library', 'Riverford Library is selling every book and becoming a hotel.'),
    ('festival', 'The Eastport science festival has been permanently cancelled.')
]


def demo(slug):
    index = next((i for i, (s, _) in enumerate(DEMO_LABELS) if s == slug), None)
    if index is None:
        return None
    claim = DEMO_LABELS[index][1]
    titles = [
        ['Six-month closure claim appears in a community post', 'Local blog repeats the closure claim', 'Another page cites the community post', 'Newsletter cites the local blog', 'Transit notice: only one station will close', 'Fact check: network-wide closure claim is incorrect'],
        ['Post claims every library book will be sold', 'Community blog repeats the hotel story', 'Reading group links to the original post', 'Newsletter links to the community blog', 'Library notice: one room is being renovated', 'Fact check: no hotel conversion is planned'],
        ['Post claims science festival is cancelled forever', 'Events blog repeats the cancellation story', 'Community page cites the initial post', 'Newsletter links to the events blog', 'Organizer notice: festival postponed by one week', 'Fact check: permanent cancellation claim is incorrect']
    ][index]
    publishers = ['Community post', 'Local blog', 'Community page', 'Neighborhood newsletter', 'Official notice', 'Independent review']
    stances = ['supports', 'supports', 'supports', 'supports', 'refutes', 'refutes']
    evidence = []
    for i, title in enumerate(titles):
        evidence.append({'id': 's'+str(i), 'title': title, 'publisher': publishers[i] + ' (fictional)', 'url': None, 'domain': '', 'publishedAt': f'2026-05-{10+i:02d}T10:00:00+00:00', 'sourceType': 'Official source' if i == 4 else 'Fact-check organization' if i == 5 else 'Community source', 'stance': stances[i], 'confidence': .95, 'excerpt': title + '. This is a fictional training example, not a real article.', 'extraction': 'Fictional preloaded fixture', 'signals': ['Synthetic teaching data; no real publisher or article']})
    edges = []
    for a,b in [(1,0),(2,0),(3,1),(5,4),(5,0)]:
        edges.append({'source':'s'+str(a),'target':'s'+str(b),'relationship':'links_to','isInferred':False,'confidence':1,'proof':'Fictional example of an observed article-body link. This is demonstration data only.'})
    for i in range(6):
        edges.append({'source':'s'+str(i),'target':'claim','relationship':'fact_checks' if i == 5 else 'repeats_claim','isInferred':False,'confidence':1,'proof':'Fictional fixture: this source explicitly discusses the claim.'})
    edges.append({'source':'s3','target':'s2','relationship':'references','isInferred':True,'confidence':.55,'proof':'Possible relationship: similar wording in a fictional example; transmission is unproven.'})
    nodes = [{'id':'claim','type':'claim','label':claim,'title':claim,'url':None,'publisher':'','publishedAt':None,'stance':'context','confidence':None,'excerpt':''}] + [dict(s, type='factcheck' if i == 5 else 'article', label=s['publisher']) for i,s in enumerate(evidence)]
    return {'id':str(uuid.uuid4()),'originalInput':claim,'claim':claim,'createdAt':datetime.now(timezone.utc).isoformat(),'demo':True,'cached':False,'status':'demo','verdict':'DISPUTED','confidence':'Demo only','explanation':'This fictional case shows a narrow announcement being exaggerated, repeated and corrected. Follow the branches to inspect each citation. It demonstrates the interface and does not document a real event.','citations':['s4','s5'],'services':{'search':'demo','factCheck':'demo','extraction':'demo','llm':'demo'},'warnings':['All names, dates, evidence and relationships in this demo are fictional. No live services were called.'],'evidence':evidence,'factChecks':[{'publisher':publishers[5]+' (fictional)','reviewedClaim':claim,'rating':'Incorrect — fictional example','url':None,'publishedAt':evidence[5]['publishedAt'],'match':'Demo fixture'}],'graph':{'nodes':nodes,'edges':edges},'earliestSourceId':'s0','sourceGroups':3,'independentSources':None,'analyzedCount':0}
