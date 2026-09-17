import pathlib,sys,unittest
from unittest.mock import patch
from datetime import datetime,timezone
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from news import SOURCES,discovery,canonical,iso_date,collect_source,alias_map

class SourceTests(unittest.TestCase):
 def test_nested_title_date_and_tracking(self):
  source=next(s for s in SOURCES if s['id']=='fiercebiotech')
  raw='<rss><channel><item><title><b>Hadlima</b> approval</title><link>https://www.fiercebiotech.com/a?utm_campaign=rss</link><pubDate>Sep 16, 2026 8:32am</pubDate></item></channel></rss>'
  row=discovery(raw,source,None)[0]
  self.assertEqual(row['title'],'Hadlima approval')
  self.assertEqual(row['publishedAt'],'2026-09-16T12:32:00+00:00')
  self.assertEqual(row['url'],'https://www.fiercebiotech.com/a')
  self.assertEqual(iso_date('Jan 16, 2026 8:32am','America/New_York'),'2026-01-16T13:32:00+00:00')
  self.assertEqual(canonical('https://example.com/a?id=5&utm_source=rss#x','example.com'),'https://example.com/a?id=5')

 def test_feed_only_duplicate_feeds_and_brand_topic_matching(self):
  source=dict(id='test',name='Test',host='example.com',discovery='https://example.com/feed',feeds=['https://example.com/feed','https://example.com/feed2'],kind='rss',feedOnly=True)
  raw='<rss><channel><item><title>Coverage update</title><link>https://example.com/a</link><pubDate>Wed, 16 Sep 2026 12:00:00 GMT</pubDate><description>&lt;p&gt;Hadlima biosimilar Medicare policy&lt;/p&gt;</description></item></channel></rss>'
  calls=[]
  def get(client,url):
   calls.append(url)
   if url not in source['feeds']:raise AssertionError('RSS-only must not request articles')
   return raw
  aliases=alias_map([dict(brand='Hadlima',molecule='adalimumab',proper='adalimumab-bwwd')])
  with patch('news.Client.get',get):rows,status=collect_source(source,[],aliases,datetime(2026,9,17,tzinfo=timezone.utc),40)
  self.assertEqual(status['status'],'ok');self.assertEqual(status['discovered'],1)
  self.assertEqual(len(rows),1);self.assertEqual(calls,source['feeds'])
  self.assertEqual(rows[0]['molecules'],['adalimumab'])
  self.assertEqual(rows[0]['topics'],['Market overall','Policy'])
  self.assertEqual(rows[0]['matchBasis'],'feed-title-description')
  self.assertFalse({'description','body'} & rows[0].keys())

 def test_one_feed_failure_retains_other_feed(self):
  source=dict(id='test',name='Test',host='example.com',discovery='https://example.com/feed',feeds=['https://example.com/feed','https://example.com/fail'],kind='rss',feedOnly=True)
  def get(client,url):
   if url.endswith('fail'):raise ValueError('Temporary feed failure')
   return '<rss><channel><item><title>Biosimilar CMS policy</title><link>https://example.com/a</link><pubDate>Wed, 16 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'
  with patch('news.Client.get',get):rows,status=collect_source(source,[],[],datetime(2026,9,17,tzinfo=timezone.utc),40)
  self.assertEqual(status['status'],'partial');self.assertEqual(len(rows),1)

if __name__=='__main__':unittest.main()
