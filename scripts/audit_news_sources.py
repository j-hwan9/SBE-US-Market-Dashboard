"""Read-only publisher feed audit; never stores article bodies or changes production sources."""
import concurrent.futures,json,os,re,time,urllib.request,urllib.error,urllib.parse,urllib.robotparser,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime,timezone
UA='SBE-Market-News/1.1 (+https://github.com/j-hwan9/SBE-US-Market-Dashboard)'
SOURCES=[
 ('STAT','https://www.statnews.com/',['/category/pharma/feed/','/category/biotech/feed/']),
 ('GEN','https://www.genengnews.com/',['/feed/']),
 ('Fierce Biotech','https://www.fiercebiotech.com/',['/rss/biotech/xml']),
 ('Fierce Healthcare','https://www.fiercehealthcare.com/',['/rss/healthcare/xml']),
 ('Drug Discovery & Development','https://www.drugdiscoverytrends.com/',['/feed/']),
 ('Bio.News','https://bio.news/',['/feed/']),
 ('Biosimilar Development','https://www.biosimilardevelopment.com/',[]),
 ('Life Science Leader','https://www.lifescienceleader.com/',[]),
 ('BioPharm International','https://www.biopharminternational.com/',['/sitemap-news.xml']),
 ('Pharmaceutical Technology','https://www.pharmtech.com/',['/sitemap-news.xml']),
 ('Endpoints News','https://endpts.com/',['/feed/']),
 ('FDA Law Blog','https://www.thefdalawblog.com/',['/feed/']),
 ('Biosimilars Law Bulletin','https://www.biosimilarsip.com/',['/feed/']),
 ('KFF Health News','https://kffhealthnews.org/',['/feed/']),
 ('BioPharma Dive','https://www.biopharmadive.com/',['/feeds/news/']),
 ('Center for Biosimilars','https://www.centerforbiosimilars.com/',['/sitemap-news.xml']),
 ('Managed Healthcare Executive','https://www.managedhealthcareexecutive.com/',['/sitemap-news.xml']),
 ('Drug Topics','https://www.drugtopics.com/',['/sitemap-news.xml']),
 ('Pharmacy Times','https://www.pharmacytimes.com/',['/sitemap-news.xml']),
 ('AJMC','https://www.ajmc.com/',['/sitemap-news.xml']),
]
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
opener=urllib.request.build_opener(NoRedirect)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.feeds=[];self.meta={};self.articles=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=='link' and ('rss' in a.get('type','') or 'atom' in a.get('type','')):self.feeds.append(a.get('href',''))
  if t=='a' and re.search(r'(?:/rss(?:/|$)|/feed/?$|feedburner)',a.get('href',''),re.I):self.feeds.append(a.get('href',''))
  if t=='a' and '/doc/' in a.get('href',''):self.articles.append(a['href'])
  if t=='meta':self.meta[a.get('property',a.get('name',''))]=a.get('content','')
def raw(url):
 time.sleep(.8)
 try:
  with opener.open(urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/atom+xml, application/xml, text/html;q=0.9,*/*;q=0.5'}),timeout=15) as r:
   return r.status,dict(r.headers),r.read(2500000).decode('utf-8',errors='replace')
 except urllib.error.HTTPError as e:return e.code,dict(e.headers),''
class Client:
 def __init__(self):self.robots={};self.robotlog=[]
 def policy(self,url):
  p=urllib.parse.urlsplit(url);origin=p.scheme+'://'+p.netloc
  if origin not in self.robots:
   target=origin+'/robots.txt';code,h,s=raw(target)
   for _ in range(3):
    if code not in (301,302,303,307,308):break
    target=urllib.parse.urljoin(target,h.get('Location',h.get('location','')));code,h,s=raw(target)
   rp=urllib.robotparser.RobotFileParser();valid=code==200 and not s.lstrip().lower().startswith(('<html','<!doctype'))
   if valid:rp.parse(s.splitlines())
   self.robots[origin]=(code,rp,valid);self.robotlog.append({'origin':origin,'status':code,'valid':valid})
  code,rp,valid=self.robots[origin]
  if code in (404,410):return True
  if not valid:raise RuntimeError('robots unavailable '+str(code))
  if not rp.can_fetch(UA,url):raise RuntimeError('robots disallow')
  delay=rp.crawl_delay(UA) or rp.crawl_delay('*') or 0
  if delay>30:raise RuntimeError('crawl delay exceeds audit budget')
  if delay:time.sleep(delay)
  return True
 def get(self,url):
  url=urllib.parse.quote(url,safe=':/?=&%+#')
  for _ in range(5):
   if urllib.parse.urlsplit(url).scheme not in ('http','https'):raise RuntimeError('unsupported URL')
   self.policy(url);code,h,s=raw(url)
   if code in (301,302,303,307,308):url=urllib.parse.urljoin(url,h.get('Location',h.get('location','')));continue
   return code,url,s
  raise RuntimeError('redirect limit')
def local(e):return e.tag.rsplit('}',1)[-1]
def entries(s):
 root=ET.fromstring(s);rows=[]
 for e in root.iter():
  kind=local(e)
  if kind not in ('item','entry','url'):continue
  row={}
  for n in e.iter():
   k=local(n);v=''.join(n.itertext()).strip()
   if k=='title' and v:row['title']=v
   if k in ('pubDate','published','publication_date') and v:row['date']=v
   if k in ('link','loc'):
    val=n.attrib.get('href',v)
    if val.startswith('http') and (k!='link' or n.attrib.get('rel','alternate')=='alternate'):row['url']=val
   if k in ('description','summary') and v:row['hasSummary']=True
  if row.get('url'):rows.append(row)
 return rows

def audit(src):
 name,home,seeds=src;c=Client();out={'name':name,'home':home,'feeds':[],'checkedAt':datetime.now(timezone.utc).isoformat()}
 try:
  code,url,s=c.get(home);out['homeStatus']=code;p=Links()
  if code==200:p.feed(s)
  urls=list(dict.fromkeys([urllib.parse.urljoin(home,x) for x in seeds+p.feeds if x]))[:5]
  out['discoveredFeeds']=p.feeds
  if not urls:
   out['htmlArticles']=[]
   for link in list(dict.fromkeys(p.articles))[:3]:
    item={'url':urllib.parse.urljoin(home,link)}
    try:
     ac,au,ab=c.get(item['url']);ap=Links()
     if ac==200:ap.feed(ab)
     dates=re.findall(r'"datePublished"\s*:\s*"([^"]+)"',ab)
     item.update(status=ac,titleMeta=bool(ap.meta.get('og:title') or ap.meta.get('twitter:title')),date=ap.meta.get('article:published_time') or ap.meta.get('date') or (dates[0] if dates else None))
    except Exception as e:item['error']=str(e)
    out['htmlArticles'].append(item)
  for u in urls:
   f={'requested':u}
   try:
    code,url,body=c.get(u);f.update(status=code,url=url)
    if code==200:
     try:
      rows=entries(body);f.update(count=len(rows),complete=sum(bool(r.get('title') and r.get('date')) for r in rows),sample=rows[:2])
      if rows and rows[0].get('title') and 'sampleArticle' not in out:
       try:
        ac,au,ab=c.get(rows[0]['url']);ap=Links();ap.feed(ab) if ac==200 else None
        out['sampleArticle']={'url':au,'status':ac,'titleMeta':bool(ap.meta.get('og:title')),'dateMeta':ap.meta.get('article:published_time') or ap.meta.get('date')}
       except Exception as e:out['sampleArticle']={'url':rows[0]['url'],'error':str(e)}
     except ET.ParseError:f['error']='not XML feed'
   except Exception as e:f['error']=str(e)
   out['feeds'].append(f)
 except Exception as e:out['error']=str(e)
 out['robots']=c.robotlog
 print('AUDIT_RESULT '+json.dumps(out,ensure_ascii=False),flush=True);return out
if __name__=='__main__':
 SOURCES=[s for s in SOURCES if s[0] in ('Fierce Biotech','Fierce Healthcare','Biosimilar Development','Life Science Leader')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:results=list(p.map(audit,SOURCES))
 with open('news-source-audit.json','w') as f:json.dump({'attempt':os.getenv('AUDIT_ATTEMPT'),'results':results},f,ensure_ascii=False,indent=2)
