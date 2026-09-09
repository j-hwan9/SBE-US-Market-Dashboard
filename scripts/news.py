"""Publisher metadata feed. Article bodies are transient and NEVER written to disk.

No AI service or API key required. Only configured publisher hosts are accessed;
robots rules and per-host pacing apply to discovery, articles and redirects.
"""
import argparse, concurrent.futures, hashlib, html, json, pathlib, re, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = 'SBE-Market-News/1.1 (+https://github.com/j-hwan9/SBE-US-Market-Dashboard)'
SOURCES = [
 {'id':'brr','name':'BR&R','host':'biosimilarsrr.com','discovery':'https://biosimilarsrr.com/feed/','kind':'rss'},
 {'id':'drugchannels','name':'Drug Channels','host':'www.drugchannels.net','feedHosts':['feeds.feedblitz.com'],'discovery':'https://www.drugchannels.net/feeds/posts/default?alt=rss','kind':'rss'},
 {'id':'fierce','name':'Fierce Pharma','host':'www.fiercepharma.com','discovery':'https://www.fiercepharma.com/keyword/biosimilar','kind':'html'},
 {'id':'biospace','name':'BioSpace','host':'www.biospace.com','discovery':'https://www.biospace.com/news-sitemap.xml','kind':'sitemap'},
 {'id':'pharmexec','name':'Pharmaceutical Executive','host':'www.pharmexec.com','discovery':'https://www.pharmexec.com/sitemap-news.xml','kind':'sitemap'},
]

def iso_date(s):
 if not s:return None
 try:
  d=datetime.fromisoformat(str(s).replace('Z','+00:00'))
 except ValueError:
  try:d=parsedate_to_datetime(str(s))
  except (ValueError,TypeError):return None
 if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
 return d.astimezone(timezone.utc).isoformat(timespec='seconds')

def norm(s):
 return re.sub(r'\s+',' ',html.unescape(str(s)).replace('®','').replace('™','').replace('–','-').replace('‑','-')).strip().casefold()

def alias_map(products):
 out={}
 for p in products:
  for v in (p['brand'],p['molecule'],p['proper']):
   v=norm(v)
   if len(v)>3:out.setdefault(v,set()).add(p['molecule'])
 return [(re.compile(r'(?<![\w])'+re.escape(a).replace(r'\ ',r'[\s-]+')+r'(?![\w])'),ms,a) for a,ms in out.items()]

def match_molecules(text,aliases):
 value=norm(text);molecules=set()
 for pattern,ms,_ in aliases:
  if pattern.search(value):molecules.update(ms)
 return sorted(molecules)

# Matching rules are deterministic and versioned; bodies remain transient.
CLASSIFICATION_VERSION = 2
TOPIC_RULES = {
 'Market overall': r'cms|medicare|medicaid|pbms?|health[\s-]+plans?|payers?|insurance|veterans?[\s-]+affairs|federal|patients?',
 'Policy': r'polic(?:y|ies)|regulations?|schemes?|administrations?|executive[\s-]+orders?',
}

def match_topics(text):
 value=norm(text)
 if not re.search(r'(?<!\w)biosimilars?(?!\w)',value):return []
 return [topic for topic,pattern in TOPIC_RULES.items() if re.search(r'(?<!\w)(?:'+pattern+r')(?!\w)',value)]

def classification_signature(aliases):
 return hashlib.sha256(json.dumps({'version':CLASSIFICATION_VERSION,'topics':TOPIC_RULES,'aliases':sorted((a,sorted(ms)) for _,ms,a in aliases)},sort_keys=True).encode()).hexdigest()

class Node:
 def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
 def text(self):return ' '.join(c.text() if isinstance(c,Node) else c for c in self.children)
 def walk(self):
  yield self
  for c in self.children:
   if isinstance(c,Node):yield from c.walk()

class Page(HTMLParser):
 VOID={'meta','link','img','input','br','hr','source','wbr','area','base','embed','param','track','col'}
 def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
 def handle_starttag(self,t,a):
  n=Node(t,a);self.stack[-1].children.append(n)
  if t not in self.VOID:self.stack.append(n)
 def handle_startendtag(self,t,a):self.handle_starttag(t,a);self.handle_endtag(t)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,s):self.stack[-1].children.append(s)

def json_nodes(v):
 if isinstance(v,dict):
  yield v
  for x in v.values():yield from json_nodes(x)
 elif isinstance(v,list):
  for x in v:yield from json_nodes(x)

def editorial_text(n):
 if n.tag in {'script','style','nav','aside','footer','header','form'}:return ''
 cls=n.attrs.get('class','')+' '+n.attrs.get('id','')
 if re.search(r'\b(?:related|recommended|newsletter|advert|social-share|comments)',cls,re.I):return ''
 return ' '.join(editorial_text(c) if isinstance(c,Node) else c for c in n.children)

def article(raw,url):
 page=Page();page.feed(raw);nodes=list(page.root.walk());meta={};ld=[]
 for n in nodes:
  if n.tag=='meta':meta[n.attrs.get('property',n.attrs.get('name','')).lower()]=n.attrs.get('content','')
  if n.tag=='script' and n.attrs.get('type')=='application/ld+json':
   try:ld.extend(json_nodes(json.loads(n.text())))
   except ValueError:pass
 title=meta.get('og:title') or next((n.text() for n in nodes if n.tag=='h1'),'')
 candidates=[n for n in ld if any(t in ('NewsArticle','Article','BlogPosting','Report') for t in ([n.get('@type')] if isinstance(n.get('@type'),str) else n.get('@type',[])))]
 candidates.sort(key=lambda n:norm(n.get('headline','')) in norm(title),reverse=True)
 own=candidates[0] if candidates else {}
 # MJH HTML article:published_time can be request time; structured article date wins.
 date=iso_date(own.get('datePublished')) or iso_date(meta.get('article:published_time'))
 body=own.get('articleBody','')
 if not isinstance(body,str):body=''
 if not body:
  containers=[n for n in nodes if re.search(r'(?:article[-_]?body|article[-_]content|ArticleBody|post-body|entry-content|articleBody|body-content)',n.attrs.get('class','')+' '+n.attrs.get('id','')) or n.attrs.get('itemprop')=='articleBody']
  body=max((editorial_text(n) for n in containers),key=len,default='')
 # No whole-page matching: navigation and related articles must never add molecules.
 return {'title':html.unescape(title).strip(),'publishedAt':date,'body':body,'description':meta.get('description',''),'bodyAvailable':len(body.strip())>80}

class SafeRedirect(urllib.request.HTTPRedirectHandler):
 def __init__(self,client):self.client=client
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  target=urllib.parse.urljoin(req.full_url,newurl).replace('http:','https:',1)
  self.client.check_host(target)
  if urllib.parse.urlsplit(target).path!='/robots.txt':self.client.allowed(target)
  return super().redirect_request(req,fp,code,msg,headers,target)

class Client:
 def __init__(self,host,feed_hosts=None):self.children={h:Client(h) for h in feed_hosts or []};self.host=host;self.robots=None;self.last=0;self.delay=1;self.opener=urllib.request.build_opener(SafeRedirect(self))
 def check_host(self,url):
  p=urllib.parse.urlsplit(url)
  if p.scheme!='https' or p.hostname not in {self.host,*self.children} or p.username:raise ValueError('Unexpected publisher redirect/host: '+str(p.hostname))
 def request(self,url):
  self.check_host(url);time.sleep(max(0,self.delay-(time.monotonic()-self.last)))
  try:
   with self.opener.open(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=25) as r:
    raw=r.read(6_000_001)
    if len(raw)>6_000_000:raise ValueError('Publisher document too large')
    return raw.decode('utf-8','replace')
  finally:self.last=time.monotonic()
 def allowed(self,url):
  hostname=urllib.parse.urlsplit(url).hostname
  if hostname!=self.host:
   self.check_host(url);child=self.children[hostname];child.allowed(url);time.sleep(max(0,child.delay-(time.monotonic()-child.last)));child.last=time.monotonic();return
  if self.robots is None:
   try:raw=self.request('https://'+self.host+'/robots.txt')
   except urllib.error.HTTPError as e:
    if e.code not in (404,410):raise
    raw='User-agent: *\nDisallow:'
   if '<html' in raw.lower():raise ValueError('Unverified robots response')
   rp=urllib.robotparser.RobotFileParser();rp.parse(raw.splitlines());self.robots=rp
   self.delay=max(1,rp.crawl_delay(UA) or 0)
  if not self.robots.can_fetch(UA,url):raise ValueError('Path excluded by robots.txt')
 def get(self,url):self.check_host(url);self.allowed(url);return self.request(url)

def canonical(url,host):
 p=urllib.parse.urlsplit(url)
 if p.hostname!=host or p.scheme not in ('http','https'):return None
 return urllib.parse.urlunsplit(('https',p.netloc,p.path,'',''))

def discovery(raw,source,client,depth=0):
 if source.get('kind')=='html':
  page=Page();page.feed(raw);out=[]
  for n in page.root.walk():
   if n.tag in ('h2','h3'):
    for a in n.walk():
     url=canonical(urllib.parse.urljoin(source['discovery'],a.attrs.get('href','')),source['host']) if a.tag=='a' else None
     if url and url!=source['discovery']:out.append({'url':url,'title':'','publishedAt':None})
  return out
 root=ET.fromstring(raw);kind=root.tag.split('}')[-1];out=[]
 if kind in ('rss','feed'):
  for item in root.findall('.//item'):
   url=item.findtext('link','');title=item.findtext('title','');date=iso_date(item.findtext('pubDate'))
   # Blogger RSS uses tracking URLs; original article is carried by FeedBurner/FeedBlitz origLink.
   links=[e.text or '' for e in item if e.tag.split('}')[-1] in ('origLink','link','guid')]
   url=next((canonical(u,source['host']) for u in links if canonical(u,source['host'])),None)
   if url:out.append({'url':url,'title':title,'publishedAt':date})
 elif kind=='sitemapindex' and depth<2:
  maps=[{e.tag.split('}')[-1]:e.text for e in item} for item in root]
  maps.sort(key=lambda m:('news' in m.get('loc',''),m.get('lastmod',''),int(re.findall(r'\d+',m.get('loc',''))[-1]) if re.findall(r'\d+',m.get('loc','')) else 0),reverse=True)
  locations=[m['loc'] for m in maps if m.get('loc')]
  for url in locations[:3]:
   if canonical(url,source['host']):out.extend(discovery(client.get(url),source,client,depth+1))
 elif kind=='urlset':
  for item in root:
   fields={e.tag.split('}')[-1]:e.text for e in item.iter()}
   url=canonical(fields.get('loc',''),source['host'])
   if url:out.append({'url':url,'title':fields.get('title',''),'publishedAt':iso_date(fields.get('publication_date')),'discoveryDate':iso_date(fields.get('lastmod'))})
 # lastmod is NOT an article publication date.
 return out

def collect_source(source,old,aliases,now,limit,scanned=None,signature=None):
 status={'id':source['id'],'name':source['name'],'checkedAt':now.isoformat(),'status':'ok','discovered':0,'new':0,'errors':0,'bodyMatched':0}
 signature=signature or classification_signature(aliases)
 previous={x['url']:x for x in old if x.get('sourceId')==source['id']}
 collected=[];seen={x['url'] for x in old if x.get('classificationSignature')==signature};client=Client(source['host'],source.get('feedHosts'));scanned=scanned or {};status['scanned']=[]
 try:
  entries=discovery(client.get(source['discovery']),source,client);status['discovered']=len(entries)
  if not entries:raise ValueError('No article links discovered')
  entries=list({x['url']:x for x in entries}.values());entries.sort(key=lambda x:x.get('publishedAt') or x.get('discoveryDate') or '',reverse=True)
  # Revisit the archive after alias/rule changes, including URLs no longer in the feed.
  archived=[dict(url=x['url'],title=x['title'],publishedAt=x['publishedAt']) for x in previous.values() if x['url'] not in seen]
  archived_urls={x['url'] for x in archived}
  fresh=[x for x in entries if x['url'] not in seen and x['url'] not in archived_urls and (x['url'] not in scanned or scanned[x['url']]<(now-timedelta(days=30)).isoformat())]
  # Reserve capacity for both backfill and discovery, so neither starves the other.
  quota=min(len(archived),max(1,limit//2)) if fresh else limit
  todo=(archived[:quota]+fresh[:max(0,limit-quota)])[:limit]
  if len(todo)<limit:todo+=archived[quota:quota+limit-len(todo)]
  status['deferred']=max(0,sum(x['url'] not in seen for x in entries)-len(todo))
  for entry in todo:
   try:
    facts=article(client.get(entry['url']),entry['url'])
    date=entry.get('publishedAt') or facts['publishedAt'];title=entry.get('title') or facts['title']
    if not date or not title:raise ValueError('Missing article publication date/title')
    if datetime.fromisoformat(date)>now+timedelta(minutes=10):raise ValueError('Future article publication date')
    text=title+' '+(facts['body'] if facts['bodyAvailable'] else facts['description'])
    molecules=match_molecules(text,aliases);topics=match_topics(text)
    prior=previous.get(entry['url'])
    if prior and not facts['bodyAvailable']:
     molecules=sorted(set(molecules+prior.get('molecules',[])))
     topics=sorted(set(topics+prior.get('topics',[])))
    status['scanned'].append(entry['url'])
    if not molecules and not topics:continue
    collected.append({'id':hashlib.sha256(entry['url'].encode()).hexdigest()[:20],'title':title,'url':entry['url'],'source':source['name'],'sourceId':source['id'],'publishedAt':date,'molecules':molecules,'topics':topics,'classificationSignature':signature,'matchBasis':'article' if facts['bodyAvailable'] else 'title-description','firstSeenAt':prior.get('firstSeenAt',now.isoformat()) if prior else now.isoformat(),'type':'press-release' if '/press-releases/' in entry['url'] else 'sponsored' if '/sponsored/' in entry['url'] or '/spons/' in entry['url'] else 'article'})
    status['bodyMatched']+=facts['bodyAvailable']
    if prior:status['reclassified']=status.get('reclassified',0)+1
    else:status['new']+=1
   except Exception as e:
    status['errors']+=1;status['lastError']=str(e)[:240]
  if status['errors']:status['status']='partial'
 except Exception as e:status.update(status='unavailable',lastError=str(e)[:240])
 return collected,status

def refresh_news(output=None,limit=40):
 output=pathlib.Path(output or ROOT/'dist');path=output/'news.json'
 old=json.loads(path.read_text()) if path.exists() else {'articles':[],'sources':[]}
 products=json.loads((output/'data.json').read_text())['products'];aliases=alias_map(products);now=datetime.now(timezone.utc)
 results=[];scanpath=ROOT/'data/news-scan-index.json';scan=json.loads(scanpath.read_text()) if scanpath.exists() else {};signature=classification_signature(aliases)
 scanned=scan.get('urls',{}) if scan.get('aliasHash')==signature else {}
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  futures=[pool.submit(collect_source,s,old['articles'],aliases,now,limit,scanned,signature) for s in SOURCES]
  for f in futures:results.append(f.result())
 articles={x['url']:{**x,'type':'sponsored' if '/sponsored/' in x['url'] or '/spons/' in x['url'] else x.get('type','article')} for x in old['articles']}
 for rows,status in results:
  for url in status.pop('scanned',[]):scanned[url]=now.isoformat()
  for row in rows:articles[row['url']]=row
  print(json.dumps(status),flush=True)
 sources=[s for _,s in results]
 if not any(s['status'] in ('ok','partial') and s['discovered'] for s in sources):
  # Retain archive and last successful timestamp, while exposing this failed attempt.
  updated=old.get('updatedAt')
 else:updated=now.isoformat()
 payload={'schemaVersion':2,'topics':list(TOPIC_RULES),'classificationVersion':CLASSIFICATION_VERSION,'classificationPending':sum(x.get('classificationSignature')!=signature for x in articles.values()),'updatedAt':updated,'checkedAt':now.isoformat(),'articles':sorted(articles.values(),key=lambda x:(x['publishedAt'],x['id']),reverse=True),'sources':sources,'molecules':sorted(set(p['molecule'] for p in products)),'coverageNote':'수집 시작 이후 누적 기사입니다. 피드 제공 범위와 매체 접근 상태에 따라 과거 기사·일부 기사가 누락될 수 있습니다.'}
 scanpath.parent.mkdir(parents=True,exist_ok=True);scanpath.write_text(json.dumps({'aliasHash':signature,'urls':scanned},ensure_ascii=False,indent=2))
 output.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2));tmp.replace(path)
 return payload

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output');ap.add_argument('--limit',type=int,default=40);args=ap.parse_args();refresh_news(args.output,args.limit)
