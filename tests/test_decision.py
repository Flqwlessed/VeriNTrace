import unittest
from unittest.mock import patch
from backend.decision import decide, match_checks, verified_quote, analysis_window
from backend.provenance import evidence_groups
from backend.pipeline import investigate
from backend.net import ServiceError


def source(node='s0', url='https://factcheck.org/test', stance='refutes', text='This synthetic statement is incorrect.'):
    return {'id': node, 'url': url, 'domain': url.split('/')[2], 'publisher': url.split('/')[2], 'stance': stance, 'confidence': .93, 'directEvidence': True, '_text': text}


class DecisionTests(unittest.TestCase):
    def test_single_direct_debunk_is_false(self):
        s=source()
        result=decide([s],{'s0':'s0'},[],{'llm':'available'})
        self.assertEqual(result['verdict'],'FALSE');self.assertEqual(result['citations'],['s0'])
    def test_direct_official_evidence_is_true(self):
        s=source(url='https://science.nasa.gov/test',stance='supports')
        self.assertEqual(decide([s],{'s0':'s0'},[],{})['verdict'],'TRUE')
    def test_rumor_repetition_cannot_determine_truth(self):
        s=source(stance='supports');s['directEvidence']=False
        self.assertEqual(decide([s],{'s0':'s0'},[],{})['verdict'],'UNABLE TO VERIFY')
    def test_mixed_evidence_stays_unresolved(self):
        a,b=source(),source('s1','https://nasa.gov/test','supports')
        result=decide([a,b],{'s0':'s0','s1':'s1'},[],{})
        self.assertEqual(result['reasonCode'],'CONFLICTING_EVIDENCE')
    def test_citations_do_not_merge_distinct_reporting(self):
        a,b=source(url='https://alpha.org/a',text='Distinct first evidence.'),source('s1','https://beta.org/b',text='Another separately written account.')
        groups=evidence_groups([a,b],{'edges':[{'source':'s1','target':'s0','relationship':'links_to'}]})
        self.assertEqual(len(set(groups.values())),2)
        self.assertEqual(decide([a,b],groups,[],{})['verdict'],'FALSE')
    def test_short_and_whitespace_quotes_accepted_but_invented_rejected(self):
        self.assertEqual(verified_quote('This claim is false.', 'This  claim\nis false.', 'This  claim\nis false.'),'This claim is false.')
        self.assertIsNone(verified_quote('NASA verified this claim.', 'Unrelated paragraph.', 'Unrelated paragraph.'))
    def test_matching_fact_check_works_without_groq(self):
        checks=[{'url':'https://factcheck.org/test','reviewedClaim':'The fictional bridge closed in 2020.','rating':'False'}]
        match_checks('The fictional bridge closed in 2020.',checks,{})
        result=decide([],{},checks,{'llm':'not_configured'})
        self.assertEqual(result['verdict'],'FALSE');self.assertEqual(result['citations'],['fc0'])
    def test_wrong_year_and_partial_rating_do_not_become_false(self):
        checks=[{'url':'https://factcheck.org/test','reviewedClaim':'The fictional bridge closed in 2020.','rating':'False'}]
        match_checks('The fictional bridge closed in 2021.',checks,{'_factCheckMatches':{'fc0':{'match':'same','confidence':.99}}})
        self.assertFalse(checks[0]['matched'])
        checks[0]['rating']='Mostly false'
        match_checks(checks[0]['reviewedClaim'],checks,{})
        self.assertEqual(decide([],{},checks,{})['verdict'],'UNABLE TO VERIFY')
    def test_raw_article_fallback_produces_cited_verdict(self):
        body='Synthetic example for testing only. The proposed closure did not happen. This story is false.'
        rows=[{'url':'https://factcheck.org/test-retrieval','title':'Synthetic correction','raw_content':body}]
        answers={'s0':{'stance':'refutes','confidence':.94,'directEvidence':True,'quote':'The proposed closure did not happen.'}}
        with patch('backend.pipeline.providers.search',return_value=(rows,'available',[])),patch('backend.pipeline.providers.fact_checks',return_value=([],'not_configured',[])),patch('backend.pipeline.extract',side_effect=ServiceError('Page blocked')),patch('backend.pipeline.providers.classify',return_value=(answers,'available',[])):
            report=investigate('The fictional bridge was closed for this retrieval test.',[])
        self.assertEqual(report['verdict'],'FALSE')
        self.assertEqual(report['evidence'][0]['extraction'],'Article text supplied by search provider')
        self.assertEqual(report['citations'],['s0'])
        self.assertFalse(any(e['relationship']=='links_to' for e in report['graph']['edges']))
    def test_windows_keep_lead_and_relevant_correction(self):
        text='Opening context for this source. '+('Background material about weather. '*100)+'The railway closure story is false and the service continues.'
        window=analysis_window('The railway closure story.',text)
        self.assertIn('Opening context',window);self.assertIn('story is false',window)

if __name__=='__main__':unittest.main()
