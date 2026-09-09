import pathlib,sys,unittest
from unittest.mock import patch
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from news import match_topics,alias_map,match_molecules,classification_signature,collect_source,article

class TopicTests(unittest.TestCase):
 def test_product_only_names_match_without_molecule_or_biosimilar(self):
  aliases=alias_map([dict(brand='Hadlima',proper='adalimumab-bwwd',molecule='adalimumab'),dict(brand='Humira',proper='adalimumab',molecule='adalimumab')])
  for text in ['HADLIMA launch','Humira® market']:
   self.assertEqual(match_molecules(text,aliases),['adalimumab'])
  self.assertEqual(match_molecules('NotHadlima',aliases),[])
 def test_every_requested_market_keyword(self):
  for word in ['CMS','Medicare','Medicaid','PBM','PBMs','health plan','health-plans','payers','payer','insurance','Veterans affairs','Federal','patient','patients']:
   with self.subTest(word=word):self.assertEqual(match_topics('Biosimilars and '+word),['Market overall'])
 def test_every_requested_policy_keyword(self):
  for word in ['Policy','policies','regulation','regulations','scheme','schemes','administration','executive order','executive orders']:
   with self.subTest(word=word):self.assertEqual(match_topics('Biosimilar '+word),['Policy'])
 def test_cooccurrence_boundaries_and_overlap(self):
  self.assertEqual(match_topics('CMS executive order'),[])
  self.assertEqual(match_topics('biosimilars impatient deregulation'),[])
  self.assertEqual(match_topics('biosimilar-based CMS policies'),['Market overall','Policy'])
  self.assertEqual(match_topics('biosimilarity CMS'),[])
 def test_related_links_do_not_classify_article(self):
  facts=article('<h1>Research update</h1><div class="article-body">A study reports new findings.<aside>biosimilar CMS policy</aside></div>','https://example.com/a')
  self.assertEqual(match_topics(facts['title']+' '+facts['body']),[])
 def test_archive_reclassification_and_topic_only_collection(self):
  source=dict(id='test',name='Test',host='example.com',discovery='https://example.com/feed',kind='rss')
  old=[dict(url='https://example.com/archived',sourceId='test',title='Hadlima update',publishedAt='2026-01-01T00:00:00+00:00',firstSeenAt='2026-01-02',molecules=['adalimumab'])]
  aliases=alias_map([dict(brand='Hadlima',proper='adalimumab-bwwd',molecule='adalimumab')]);now=datetime(2026,9,9,tzinfo=timezone.utc)
  def get(client,url):
   if url.endswith('/feed'):return '<rss><channel><item><link>https://example.com/new</link><title>Biosimilar CMS policy</title><pubDate>Tue, 08 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>'
   return '<h1>Biosimilar CMS policy</h1><div class="article-body">Biosimilars and Medicare policy changes are examined in this article. '+('Evidence and analysis. '*6)+'</div>'
  with patch('news.Client.get',get):rows,status=collect_source(source,old,aliases,now,4)
  self.assertEqual(len(rows),2);self.assertEqual(status['reclassified'],1)
  new=next(x for x in rows if x['url'].endswith('/new'));self.assertEqual(new['molecules'],[]);self.assertEqual(new['topics'],['Market overall','Policy'])
  back=next(x for x in rows if x['url'].endswith('/archived'));self.assertEqual(back['firstSeenAt'],'2026-01-02');self.assertEqual(back['classificationSignature'],classification_signature(aliases))
  self.assertFalse(any(k in new for k in ['body','description']))
  with patch('news.Client.get',get):repeat,status=collect_source(source,rows,aliases,now,4)
  self.assertEqual(repeat,[])

if __name__=='__main__':unittest.main()
