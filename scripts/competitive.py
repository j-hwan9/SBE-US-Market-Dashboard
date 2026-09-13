"""Official-site snapshots and deterministic change detection. No AI or login bypass.
Official catalog links establish provenance; Purple Book establishes product scope.
"""
import asyncio,hashlib,io,json,re,sys,os
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode
from urllib.robotparser import RobotFileParser
ROOT=Path(__file__).resolve().parents[1]
UA='SBEUSMonitor/1.0 (+https://github.com/j-hwan9/SBE-US-Market-Dashboard)'
STAMP=datetime.now(timezone.utc).isoformat()
SKIP=re.compile(r'privacy|cookie|terms|legal|login|sign.in|register|unsubscribe|careers|search|facebook|linkedin|twitter|youtube|instagram',re.I)
TOPICS=[('Access / support',r'access|reimburse|copay|co-pay|saving|support|coverage|insurance'),('Resources',r'resource|download|material|brochure|guide'),('Clinical data',r'clinical|efficacy|study|studies|data'),('Safety',r'safety|warning'),('HCP',r'hcp|professional|provider'),('Patient',r'patient|caregiver'),('Events',r'congress|event|symposium')]
def digest(v):return hashlib.sha256(v if isinstance(v,bytes) else v.encode()).hexdigest()
def canonical(url,base=''):
 try:
  u=urlsplit(urljoin(base,url));h=(u.hostname or '').lower()
  if u.scheme not in ('https','http') or not h or u.username or u.port not in (None,80,443) or h in ('localhost','127.0.0.1') or ':' in h or re.fullmatch(r'[\d.]+',h):return None
  query=urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith(('utm_','gclid','fbclid'))])
  return urlunsplit((u.scheme,h,u.path or '/',query,''))
 except ValueError:return None
def host(u):return (urlsplit(u).hostname or '').removeprefix('www.')
def brand_match(brand,text):return bool(re.search(r'(?<![a-z0-9])'+re.escape(brand.lower())+r'(?![a-z0-9])',text.lower()))
def category(url,title=''):return next((name for name,pattern in TOPICS if re.search(pattern,url+' '+title,re.I)),'Product page')
def lines(text):
 out=[]
 for s in text.splitlines():
  s=' '.join(s.split())
  if len(s)>3 and not re.search(r'^(©|copyright|all rights reserved|cookie settings)',s,re.I):out.append(s)
 return list(dict.fromkeys(out))
def text_state(text):return [{'hash':digest(s),'excerpt':s[:220]} for s in lines(text)]
def difference(old,new):
 a={v['hash']:v['excerpt'] for v in old['text']};b={v['hash']:v['excerpt'] for v in new['text']}
 added=[b[k] for k in b.keys()-a.keys()];removed=[a[k] for k in a.keys()-b.keys()]
 x={v['url']:v for v in old.get('links',[])};y={v['url']:v for v in new.get('links',[])}
 la=[y[k] for k in sorted(y.keys()-x.keys())];lr=[x[k] for k in sorted(x.keys()-y.keys())]
 files=[{'url':k,'label':y[k]['label']} for k in x.keys()&y.keys() if y[k].get('fileHash') and x[k].get('fileHash') and x[k]['fileHash']!=y[k]['fileHash']]
 images=sorted(set(new.get('images',[]))^set(old.get('images',[])))
 types=[]
 if added or removed:types.append('Text')
 if la or lr:types.append('Links / resources')
 if files:types.append('PDF updated')
 if images:types.append('Images')
 if new.get('visualChanged'):types.append('Visual review')
 return dict(types=types,added=added[:8],removed=removed[:8],addedCount=len(added),removedCount=len(removed),linksAdded=la[:12],linksRemoved=lr[:12],filesChanged=files,imagesChanged=len(images))
class Monitor:
 def __init__(self):
  self.cfg=json.loads((ROOT/'data/competitive-watchlist.json').read_text());self.robot={};self.sem=asyncio.Semaphore(5);self.hostlocks={};self.catalogResults=[]
  self.output=ROOT/'dist/competitive';self.output.mkdir(exist_ok=True);(self.output/'images').mkdir(exist_ok=True)
  self.old=json.loads((self.output/'index.json').read_text()) if (self.output/'index.json').exists() else {'pages':[],'events':[]}
  self.states=json.loads((ROOT/'data/competitive-state.json').read_text()) if (ROOT/'data/competitive-state.json').exists() else {}
  self.events=self.old['events'][:];self.pages=[];self.initial=not self.old.get('checkedAt')
 async def allowed(self,url):
  import requests
  origin=urlsplit(url).scheme+'://'+urlsplit(url).netloc
  if origin not in self.robot:
   def get():
    try:
     r=requests.get(origin+'/robots.txt',headers={'User-Agent':UA},timeout=15)
     if r.status_code in (404,410):return True
     if r.status_code!=200:return False
     p=RobotFileParser();p.parse(r.text.splitlines());return p
    except Exception:return False
   self.robot[origin]=asyncio.create_task(asyncio.to_thread(get))
  p=await self.robot[origin];return p if isinstance(p,bool) else p.can_fetch(UA,url)
 async def capture(self,url,screenshot=False):
  if not await self.allowed(url):raise ValueError('robots.txt disallows access or could not be checked')
  async with self.sem:
   lock=self.hostlocks.setdefault(host(url),asyncio.Semaphore(1))
   async with lock:
    p=await self.browser.new_page(viewport={'width':1280,'height':900},locale='en-US',reduced_motion='reduce',user_agent=UA)
    try:
     response=await p.goto(url,wait_until='domcontentloaded',timeout=35000)
     if not response or response.status>=400:raise ValueError('HTTP '+str(response.status if response else 'no response'))
     final=canonical(p.url)
     if host(final)!=host(url):raise ValueError('Redirect needs official-site review: '+final)
     await p.wait_for_timeout(1200)
     text=await p.locator('body').inner_text(timeout=10000)
     if len(text)<120 or re.search(r'just a moment|verify you are human|access denied|captcha|request blocked',text[:1600],re.I):raise ValueError('Blocked, verification required, or empty page')
     result=await p.evaluate('''()=>{const root=document.querySelector('main')||document.body;const clone=root.cloneNode(true);clone.querySelectorAll('script,style,nav,footer,[id*="onetrust"],[class*="cookie-banner"]').forEach(x=>x.remove());return {title:document.title,text:clone.innerText||clone.textContent,links:Array.from(document.querySelectorAll('a[href]')).map(a=>({url:a.href,label:(a.innerText||a.title||a.querySelector('img')?.alt||'').trim().slice(0,160),context:a.parentElement.innerText.slice(0,1000)})),images:Array.from(root.querySelectorAll('img[src]')).map(i=>i.currentSrc||i.src)}}''')
     result['finalUrl']=final
     if screenshot:
      await p.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important} #onetrust-banner-sdk,.onetrust-pc-dark-filter{visibility:hidden!important}')
      height=min(2400,await p.evaluate('document.documentElement.scrollHeight'))
      result['image']=await p.screenshot(type='jpeg',quality=50,clip={'x':0,'y':0,'width':1280,'height':height},timeout=15000)
     return result
    finally:await p.close()
 async def discover_catalog(self,source,products):
  found=[]
  try:
   r=await self.capture(source['url']);self.catalogResults.append(dict(source,status='Checked',checkedAt=STAMP))
   for p in products:
    for link in r['links']:
     u=canonical(link['url'],source['url'])
     if not u or SKIP.search(u) or re.search(r'\.(pdf|zip|docx?)$',urlsplit(u).path,re.I):continue
     direct=brand_match(p['brand'],u+' '+link['label'])
     contextual=brand_match(p['brand'],link['context']) and bool(re.search('product website|visit.*site|learn more',link['label'],re.I))
     if not (direct or contextual):continue
     # Cross-domain discovery must identify the brand in the destination hostname.
     if host(u)!=host(source['url']) and p['brand'].lower().replace(' ','') not in host(u).replace('-',''):continue
     if re.search(r'/news|press.release|/media|/investor',u,re.I):continue
     found.append(dict(brand=p['brand'],operator=source['operator'],url=u,evidence=source['url']))
  except Exception as e:self.catalogResults.append(dict(source,status='Needs review',error=str(e)[:220],checkedAt=STAMP))
  return found
 async def file_hash(self,url):
  import requests
  if not await self.allowed(url):return None
  def get():
   try:
    with requests.get(url,headers={'User-Agent':UA},timeout=20,stream=True,allow_redirects=False) as r:
     if r.status_code!=200:return None
     data=b''
     for chunk in r.iter_content(65536):
      data+=chunk
      if len(data)>8_000_000:return None
     return digest(data) if data.startswith(b'%PDF') else None
   except Exception:return None
  return await asyncio.to_thread(get)
 async def visit(self,product,site,url,depth):
  key=digest(product['brand']+'|'+url)[:20];old=self.states.get(key);prior=next((x for x in self.old['pages'] if x['id']==key),{})
  row=dict(id=key,brand=product['brand'],molecule=product['molecule'],kind=product['kind'],operator=site['operator'],url=url,evidence=site['evidence'],depth=depth,checkedAt=STAMP,firstSeen=prior.get('firstSeen',STAMP),lastSuccess=prior.get('lastSuccess'),status='Pending',pageType=category(url))
  children=[]
  try:
   r=await self.capture(url,True);row.update(title=r['title'],pageType=category(url,r['title']),lastSuccess=STAMP)
   links=[]
   for x in r['links']:
    u=canonical(x['url'],url)
    if not u or SKIP.search(u):continue
    if u not in {v['url'] for v in links}:links.append(dict(url=u,label=x['label']))
    if host(u)==host(url) and u!=url and not re.search(r'\.(pdf|zip|docx?|jpe?g|png|mp4)$',urlsplit(u).path,re.I):
     # Corporate sites stay inside the product subtree; brand sites can discover all relevant pages.
     branded=product['brand'].lower().replace(' ','') in host(url).replace('-','')
     if branded or brand_match(product['brand'],u):children.append(u)
   pdfs=[v for v in links if urlsplit(v['url']).path.lower().endswith('.pdf')][:6]
   hashes=await asyncio.gather(*(self.file_hash(v['url']) for v in pdfs))
   for v,h in zip(pdfs,hashes):
    if h:v['fileHash']=h
   shot=r.pop('image');imagePath='competitive/images/'+digest(shot)[:24]+'.jpg';(ROOT/'dist'/imagePath).write_bytes(shot)
   current=dict(text=text_state(r['text']),links=links[:250],images=sorted(set(canonical(x,url) for x in r['images'] if canonical(x,url)))[:100],screenshot=imagePath)
   if old:
    from PIL import Image,ImageChops,ImageStat
    try:
     a=Image.open(ROOT/'dist'/old['screenshot']).convert('RGB').resize((128,240));b=Image.open(io.BytesIO(shot)).convert('RGB').resize((128,240))
     current['visualChanged']=sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3/255>0.12
    except Exception:current['visualChanged']=False
    change=difference(old,current);row['status']='Changed' if change['types'] else 'Unchanged'
    if change['types']:
     event=dict(id=digest(key+STAMP)[:24],pageId=key,brand=row['brand'],molecule=row['molecule'],operator=row['operator'],pageType=row['pageType'],url=url,detectedAt=STAMP,previousCheckedAt=prior.get('lastSuccess'),quarter=f'{STAMP[:4]} Q{(int(STAMP[5:7])-1)//3+1}',before=old['screenshot'],after=imagePath,**change)
     self.events.append(event);row['lastChanged']=STAMP
   else:row['status']='Baseline'
   row.update(currentScreenshot=imagePath,previousScreenshot=old.get('screenshot') if old else None,lastChanged=row.get('lastChanged',prior.get('lastChanged')),linkCount=len(links),pdfCount=len(pdfs))
   self.states[key]=current
  except Exception as e:
   row.update(status='Needs review',error=str(e)[:240],currentScreenshot=prior.get('currentScreenshot'),previousScreenshot=prior.get('previousScreenshot'),lastChanged=prior.get('lastChanged'))
  self.pages.append(row)
  return sorted(set(children),key=lambda u:(category(u)=='Product page',u))
 async def product(self,p,sites):
  queue=[(s,s['url'],0) for s in sites[:2]];seen=set();limit=self.cfg['maxPagesPerProduct']
  # Previously tracked URLs remain in scope even when removed from navigation.
  queue += [(sites[0],r['url'],r.get('depth',1)) for r in self.old['pages'] if r['brand']==p['brand'] and r['url'] not in [v[1] for v in queue]]
  while queue and len(seen)<limit:
   site,u,depth=queue.pop(0)
   if u in seen:continue
   seen.add(u);children=await self.visit(p,site,u,depth)
   if depth<self.cfg['maxDepth']:queue.extend((site,x,depth+1) for x in children if x not in seen)
  for r in self.pages:
   if r['brand']==p['brand']:r['scopeLimited']=bool(queue)
 async def run(self):
  from playwright.async_api import async_playwright
  pb=json.loads((ROOT/'dist/data.json').read_text());products=list({(p['molecule'],p['brand']):{k:p[k] for k in ['brand','molecule','kind']} for p in pb['products']}.values())
  async with async_playwright() as playwright:
   self.browser=await playwright.chromium.launch(headless=True,args=['--no-sandbox'])
   discovered=await asyncio.gather(*(self.discover_catalog(s,products) for s in self.cfg['catalogs']))
   sites=self.cfg['sites'][:]+[x for group in discovered for x in group]
   # Preserve previously proven official links through temporary catalog failures.
   sites+=self.old.get('sites',[])
   sites=list({(s['brand'],s['url']):s for s in sites}.values())
   mapped={p['brand']:[s for s in sites if s['brand']==p['brand']] for p in products}
   await asyncio.gather(*(self.product(p,mapped[p['brand']]) for p in products if mapped[p['brand']]))
   await self.browser.close()
  coverage=[]
  for p in products:
   pages=[r for r in self.pages if r['brand']==p['brand']];coverage.append(dict(p,sites=len(mapped[p['brand']]),pages=len(pages),successful=sum(r['status']!='Needs review' for r in pages),status='Not mapped' if not pages else 'Needs review' if all(r['status']=='Needs review' for r in pages) else 'Tracking'))
  out=dict(schemaVersion=1,checkedAt=STAMP,schedule=self.cfg['schedule'],maxPagesPerProduct=self.cfg['maxPagesPerProduct'],maxDepth=self.cfg['maxDepth'],catalogs=self.catalogResults,sites=sites,coverage=coverage,pages=self.pages,events=self.events)
  if not any(r.get('lastSuccess')==STAMP for r in self.pages):raise RuntimeError('No successful captures; published baseline preserved')
  (self.output/'index.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n')
  (ROOT/'data/competitive-state.json').write_text(json.dumps(self.states,ensure_ascii=False,separators=(',',':'))+'\n')
  # Keep immutable evidence referenced by current pages and historical events.
  keep={r.get(k) for r in self.pages for k in ['currentScreenshot','previousScreenshot']}|{e.get(k) for e in self.events for k in ['before','after']}
  for f in (self.output/'images').glob('*.jpg'):
   if str(f.relative_to(ROOT/'dist')) not in keep:f.unlink()
  print(json.dumps({'brands':len(coverage),'tracking':sum(x['status']=='Tracking' for x in coverage),'pages':len(self.pages),'successful':sum(r['status']!='Needs review' for r in self.pages),'events':len(self.events),'catalogs':self.catalogResults},ensure_ascii=False),flush=True)
if __name__=='__main__':asyncio.run(Monitor().run())
