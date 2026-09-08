import copy,json,pathlib,sys,unittest
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from news import article,alias_map,match_molecules,discovery,iso_date
from approval_letters import extract_periods,letter_documents,pi_has_unopened_period

class NewsTests(unittest.TestCase):
 def test_article_date_not_request_time_and_body_not_sidebar(self):
  raw='''<meta property="og:title" content="Humira market"><meta property="article:published_time" content="2026-09-09T10:00:00Z"><script type="application/ld+json">{"@type":"NewsArticle","headline":"Humira market","datePublished":"2026-07-09T10:00:00Z"}</script><div class="article-body"><p>Hyrimoz share increased.</p><aside>Pyzchiva</aside><div class="related-content">Stelara</div></div>'''
  facts=article(raw,'https://example.com/a');self.assertTrue(facts['publishedAt'].startswith('2026-07-09'));self.assertIn('Hyrimoz',facts['body']);self.assertNotIn('Pyzchiva',facts['body']);self.assertNotIn('Stelara',facts['body'])
 def test_brand_suffix_and_multi_molecule_word_boundaries(self):
  aliases=alias_map([{'brand':'Hyrimoz','molecule':'adalimumab','proper':'adalimumab-adaz'},{'brand':'Pyzchiva','molecule':'ustekinumab','proper':'ustekinumab-ttwe'}])
  self.assertEqual(match_molecules('Hyrimoz® and ustekinumab-ttwe',aliases),['adalimumab','ustekinumab'])
  self.assertEqual(match_molecules('NotHyrimoz',aliases),[])
 def test_tracking_link_resolved_from_feed_original(self):
  raw='<rss xmlns:f="urn:feed"><channel><item><title>Test</title><link>https://tracker.test/a</link><f:origLink>https://www.drugchannels.net/2026/09/a.html</f:origLink><pubDate>Tue, 01 Sep 2026 10:30:00 +0000</pubDate></item></channel></rss>'
  rows=discovery(raw,{'host':'www.drugchannels.net'},None);self.assertEqual(len(rows),1);self.assertIn('drugchannels.net',rows[0]['url'])
 def test_sitemap_lastmod_not_publication_date(self):
  rows=discovery('<urlset><url><loc>https://example.com/news/a</loc><lastmod>2026-09-09</lastmod></url></urlset>',{'host':'example.com'},None)
  self.assertIsNone(rows[0]['publishedAt'])

class LetterTests(unittest.TestCase):
 def setUp(self):
  self.p={'bla':'761024','brand':'Amjevita'};self.doc={'date':'2016-09-23','url':'https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/761024orig1s000ltr.pdf'}
 def test_finished_product_not_substance(self):
  text='BLA 761024\nAmjevita 20 mg/0.4 mL and 40 mg/0.8 mL\nDATING PERIOD\nThe dating period for Amjevita shall be 30 months from the date of manufacture when stored at 2-8 °C. The dating period for your drug substance shall be 48 months when stored at 2-8 °C.\nFDA LOT RELEASE\n'
  facts=extract_periods(text,self.p,self.doc);self.assertEqual([f['months'] for f in facts],[30]);self.assertEqual(len(facts[0]['strengths']),2);self.assertTrue(facts[0]['historical'])
 def test_protocol_redaction_wrong_bla_and_temperature_never_fill(self):
  for body in ['We have approved the protocol for extending the dating period for Amjevita to 36 months at 2-8 °C.','The dating period for Amjevita shall be (b)(4) months when stored at 2-8 °C.','The dating period for Amjevita shall be 36 months at -20 °C.']:
   self.assertFalse(extract_periods('BLA 761024\nDATING PERIOD\n'+body,self.p,self.doc))
  self.assertFalse(extract_periods('BLA 123456\nDATING PERIOD\nThe dating period for Amjevita shall be 30 months at 2-8 °C.',self.p,self.doc))
 def test_shared_bla_generic_period_requires_brand_scope(self):
  text='BLA 761024\nAmjevita Otherbrand\nDATING PERIOD\nThe dating period for the drug product shall be 30 months when stored at 2-8 °C.'
  self.assertFalse(extract_periods(text,self.p,self.doc,['Amjevita','Otherbrand']))
 def test_only_approved_letters_and_newest_first(self):
  make=lambda dt,status:{'submission_status':status,'submission_status_date':dt,'submission_type':'SUPPL','submission_number':'001','application_docs':[{'url':self.doc['url'].replace('2016/','2020/' if dt.startswith('2020') else '2016/'),'type':'Letter'}]}
  docs=letter_documents({'application_number':'BLA761024','submissions':[make('20160923','AP'),make('20200101','AP'),make('20230101','TA')]},'761024')
  self.assertEqual([x['date'] for x in docs],['2020-01-01','2016-09-23'])
 def test_pi_priority_excludes_prepared_duration(self):
  p={'labels':[{'sections':{'storage':['Unopened shelf life is 24 months at 2 to 8°C.']}}]};self.assertTrue(pi_has_unopened_period(p))
  p['labels'][0]['sections']['storage']=['After dilution, store for 24 months at 2 to 8°C.'];self.assertFalse(pi_has_unopened_period(p))

if __name__=='__main__':unittest.main()
