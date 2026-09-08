"""Fresh official-source collection with validation, atomic publish and history.

Python stdlib + pdftotext only. GitHub workflow handles authentication/deployment.
No long-lived credentials, API tokens or user data are sent to the public client.
"""
import argparse,calendar,concurrent.futures,csv,copy,hashlib,io,json,os,pathlib,re,subprocess,sys,tempfile,threading,time,urllib.request,urllib.parse
from datetime import datetime,timezone
from html.parser import HTMLParser
from collect import parse as parse_spl

ROOT=pathlib.Path(__file__).resolve().parents[1]
DOWNLOADS='https://purplebooksearch.fda.gov/downloads'
PARSER_VERSION=2
class CollectionError(Exception):pass
class Links(HTMLParser):
 def __init__(self):super().__init__();self.urls=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   u=dict(attrs).get('href','')
   if u:self.urls.append(urllib.parse.urljoin(DOWNLOADS,u))

class Sources:
 def __init__(self):self.cache={};self.lock=threading.Lock()
 def get(self,url):
  with self.lock:
   if url in self.cache:return self.cache[url]
  if urllib.parse.urlparse(url).hostname not in {'purplebooksearch.fda.gov','www.accessdata.fda.gov','api.fda.gov','dailymed.nlm.nih.gov'}:raise CollectionError('Unexpected source host')
  for attempt in range(3):
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'Biosimilar-Market-Dashboard/2.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=60) as response:
     value=response.read(30_000_001)
     if len(value)>30_000_000:raise CollectionError('Source exceeds 30 MB')
    with self.lock:self.cache[url]=value
    return value
   except urllib.error.HTTPError as e:
    if e.code==404:raise
    if attempt==2:raise CollectionError(f'HTTP {e.code}: {url}') from e
   except Exception as e:
    if attempt==2:raise CollectionError(f'{url}: {e}') from e
   time.sleep(2**attempt)

def discover_latest(html,now):
 parser=Links();parser.feed(html);found=[]
 for url in parser.urls:
  match=re.search(r'/PurpleBook/(\d{4})/purplebook-search-([A-Za-z]+)-data-download\.csv',url,re.I)
  if not match:continue
  try:month=list(calendar.month_name).index(match[2].capitalize())
  except ValueError:continue
  year=int(match[1])
  if (year,month)<=(now.year,now.month):found.append((year,month,url.replace('http:','https:')))
 if not found:raise CollectionError('No official monthly CSV link found; previous data retained')
 year,month,url=max(found);return f'{year:04d}-{month:02d}',url

def read_purple(raw):
 text=raw.decode('utf-8-sig');records=list(csv.reader(io.StringIO(text)))
 headers=[i for i,r in enumerate(records) if 'BLA Number' in r and 'License Type' in r]
 if not headers:raise CollectionError('Purple Book schema changed: header missing')
 h=headers[-1];required={'BLA Number','Proper Name','Proprietary Name','Ref. Product Proper Name','Ref. Product Proprietary Name','Approval Date','License Type','Licensure'}
 if not required.issubset(records[h]):raise CollectionError('Purple Book required columns missing')
 rows=[{k:v.strip() for k,v in zip(records[h],r)} for r in records[h+1:] if len(r)>6]
 rows=[r for r in rows if r.get('BLA Number','').isdigit() and r.get('Licensure')=='Licensed']
 bios=[r for r in rows if r['License Type'].startswith('351(k)')]
 if not bios:raise CollectionError('No biosimilars parsed')
 refs={r['Ref. Product Proprietary Name'].casefold() for r in bios}
 selected=[r for r in rows if r in bios or r['Proprietary Name'].casefold() in refs]
 groups={}
 for r in selected:groups.setdefault((r['BLA Number'],r['Proprietary Name']),[]).append(r)
 products=[]
 for (bla,brand),pr in groups.items():
  first=pr[0];kind='biosimilar' if first['License Type'].startswith('351(k)') else 'reference'
  products.append({'id':re.sub('[^a-z0-9]+','-',brand.lower())+'-'+bla,'brand':brand,'bla':bla,'molecule':(first['Ref. Product Proper Name'] or first['Proper Name']).lower(),'proper':first['Proper Name'],'applicant':first['Applicant'],'reference':first['Ref. Product Proprietary Name'] or brand,'kind':kind,'presentations':pr,'labels':[],'issues':[]})
 return products,selected

def parse_fda_pdf(raw,product,doc):
 with tempfile.TemporaryDirectory() as td:
  pdf=pathlib.Path(td)/'label.pdf';txt=pathlib.Path(td)/'label.txt';pdf.write_bytes(raw)
  subprocess.run(['pdftotext','-layout',str(pdf),str(txt)],check=True,capture_output=True,timeout=90)
  text=txt.read_text()
 starts=list(re.finditer(r'(?m)^[ \t\f]*1[ \t]+INDICATIONS[ \t]+AND[ \t]*USAGE[ \t]*$',text))
 # Some two-column contents pages put the heading on its own line too.
 starts=[m for m in starts if re.search(r'\bindicated\b',text[m.end():m.end()+1600],re.I)]
 if not starts:raise CollectionError(product['brand']+': full PI boundary not found')
 if len(starts)>1:
  mapping={'Immgolis':0,'Immgolis Intri':1,'Eticovo':0,'Ospomyv':0,'Xbryk':1,'Ponlimsi':0}
  if product['brand'] not in mapping:raise CollectionError(product['brand']+': multiple PIs require explicit brand mapping')
  idx=mapping[product['brand']]
  if idx>=len(starts):raise CollectionError('Configured PI block not present')
 else:idx=0
 body=text[starts[idx].start():starts[idx+1].start() if idx+1<len(starts) else len(text)]
 sections={}
 for key,num,title in [('indications',1,'INDICATIONS AND USAGE'),('dosage',2,'DOSAGE AND ADMINISTRATION'),('strengths',3,'DOSAGE FORMS AND STRENGTHS'),('description',11,'DESCRIPTION'),('supplied',16,'HOW SUPPLIED')]:
  start=re.search(r'(?m)^[ \t\f]*'+str(num)+r'[ \t]'+r'+'+r'[ \t]*'.join(title.split())+r'[^\n]*',body)
  if not start:sections[key]=[];continue
  tail=body[start.end():];end=re.search(r'(?m)^\s*'+str(num+1)+r'\s+[A-Z][A-Z /&-]+',tail)
  value=tail[:end.start()] if end else tail
  value=re.sub(r'Reference ID:\s*\d+','',value).replace('\f','\n')
  value=re.sub(r'(?m)^\s*\d+\s*$','',value)
  sections[key]=[re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n\s*\n',value) if len(p.strip())>3]
 sections['storage']=[p for p in sections['supplied'] if re.search(r'stor|refriger|temperatur|freez|expir|light',p,re.I)]
 if not all(sections[k] for k in ['indications','dosage','supplied']):raise CollectionError(product['brand']+': critical PI section missing')
 manufacturer=[]
 for m in re.finditer(r'(?im)^[ \t]*(Manufactured (?:by|for)|Distributed by)[^\n]*',body):
  v=re.sub(r'\s+',' ',body[m.start():].split('\n\n')[0]).strip()
  if v not in manufacturer:manufacturer.append(v)
 return {'provider':'FDA','title':product['brand']+' FDA prescribing information','url':doc['url'].replace('http:','https:'),'published_date':doc.get('date',''),'labelEffective':doc.get('date',''),'sections':sections,'storage':sections['storage'],'latex':[p for k in ['supplied','description'] for p in sections[k] if re.search('latex|natural rubber',p,re.I)],'products':[],'labelOrganizations':[],'manufacturerText':manufacturer[:3],'pdfTextExtracted':True,'sourceHash':hashlib.sha256(raw).hexdigest()}

def fetch_label(product,old,sources,force):
 previous=old.get('labels',[None])[0] if old.get('labels') else None
 q=product['brand'].replace(' Onbody','')
 listing=json.loads(sources.get('https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?'+urllib.parse.urlencode({'drug_name':q,'pagesize':100})))
 candidates=listing.get('data',[])
 if not isinstance(candidates,list):raise CollectionError('DailyMed response schema changed')
 def rank(x):
  title=x['title'].upper();app=product['applicant'].upper().split()[0].strip(',')
  return (app in title,not any(y in title for y in ['REPACK','A-S MEDICATION','CARDINAL HEALTH','MCKESSON','NUVAILA']),x['setid']==(previous or {}).get('setid'),datetime.strptime(x['published_date'],'%b %d, %Y'))
 candidates.sort(key=rank,reverse=True)
 for item in candidates[:8]:
  if previous and not force and old.get('parserVersion')==PARSER_VERSION and item['setid']==previous.get('setid') and item['spl_version']==previous.get('spl_version'):
   return copy.deepcopy(previous)
  raw=sources.get('https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/'+item['setid']+'.xml')
  label=parse_spl(raw,item,product['bla'])
  if label:
   if not all(label['sections'][k] for k in ['indications','dosage','supplied']):raise CollectionError(product['brand']+': DailyMed PI incomplete')
   label['sourceHash']=hashlib.sha256(raw).hexdigest();return label
 try:
  query=urllib.parse.urlencode({'search':'application_number:"BLA'+product['bla']+'"'})
  data=json.loads(sources.get('https://api.fda.gov/drug/drugsfda.json?'+query))
 except urllib.error.HTTPError as e:
  if e.code==404 and not previous:return None
  raise CollectionError(product['brand']+': FDA record not available; previous PI retained') from e
 app=data['results'][0]
 if app.get('application_number')!='BLA'+product['bla']:raise CollectionError('FDA BLA mismatch')
 docs=sorted([d for s in app.get('submissions',[]) for d in s.get('application_docs',[]) if d.get('type')=='Label'],key=lambda x:x.get('date',''),reverse=True)
 if not docs:
  if previous:raise CollectionError(product['brand']+': previous PI no longer discoverable')
  return None
 doc=docs[0];url=doc['url'].replace('http:','https:')
 if previous and not force and old.get('parserVersion')==PARSER_VERSION and previous.get('url')==url and previous.get('published_date')==doc.get('date'):return copy.deepcopy(previous)
 return parse_fda_pdf(sources.get(url),product,doc)

def compare_fields(p):
 label=(p.get('labels') or [{}])[0];sections=label.get('sections',{});prs=p['presentations']
 reg=lambda ks:sorted(set(json.dumps([r.get(k,'') for k in ks],ensure_ascii=False) for r in prs))
 return {'허가·presentation':reg(['BLA Number','Proprietary Name','Proper Name','Approval Date','Strength','Dosage Form','Route of Administration','Product Presentation','Marketing Status','Licensure']), 'Interchangeability':reg(['License Type','Inter. Approval Date','Strength','Product Presentation']), 'Manufacturer': [p['applicant'],label.get('manufacturerText',[])], 'NDC·조성':label.get('products',[]),'Dosage':sections.get('dosage',[]),'Indications':sections.get('indications',[]),'Storage·latex': [label.get('storage',[]),label.get('latex',[]),sections.get('supplied',[])],'PI version': [label.get('url'),label.get('spl_version'),label.get('published_date')], 'Approval letter':p.get('approvalLetter',{}).get('facts',[])}

def changes(old,new):
 before={p['id']:p for p in old.get('products',[])};after={p['id']:p for p in new['products']}
 changed=[]
 for key in sorted(before.keys()&after.keys()):
  a,b=compare_fields(before[key]),compare_fields(after[key]);fields=[f for f in a if a[f]!=b[f]]
  if fields:changed.append({'id':key,'brand':after[key]['brand'],'bla':after[key]['bla'],'fields':fields})
 brief=lambda p:{'id':p['id'],'brand':p['brand'],'bla':p['bla'],'molecule':p['molecule']}
 return {'added':[brief(after[k]) for k in sorted(after.keys()-before.keys())],'removed':[brief(before[k]) for k in sorted(before.keys()-after.keys())],'changed':changed}

def validate(payload,previous):
 products=payload['products'];ids=[p['id'] for p in products]
 if not products or len(ids)!=len(set(ids)):raise CollectionError('Empty or duplicate product IDs')
 if previous and len(products)<len(previous['products'])*.8:raise CollectionError('More than 20% of product records disappeared; manual review required')
 for p in products:
  if not p['bla'].isdigit() or not p['presentations']:raise CollectionError('Invalid BLA or presentation')
  if p['kind']=='biosimilar' and not any(r['kind']=='reference' and r['brand'].casefold()==p['reference'].casefold() and r['molecule']==p['molecule'] for r in products):raise CollectionError('Reference product not resolved: '+p['brand'])
  if p['labels'] and not all(p['labels'][0]['sections'].get(k) for k in ['indications','dosage','supplied']):raise CollectionError('Incomplete parsed PI: '+p['brand'])
 return True

def atomic_json(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(re.sub('[\ue000-\uf8ff]','•',json.dumps(value,ensure_ascii=False,indent=2)));temp.replace(path)

def refresh(args):
 now=datetime.now(timezone.utc);stamp=now.isoformat(timespec='seconds');out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=True)
 previous=json.loads((out/'data.json').read_text()) if (out/'data.json').exists() else {}
 sources=Sources();month,url=discover_latest(sources.get(DOWNLOADS).decode('utf-8'),now)
 if month<previous.get('purpleBookDate',''):raise CollectionError('Latest discoverable Purple Book is older than published dataset')
 raw=sources.get(url);products,rows=read_purple(raw);old={p['id']:p for p in previous.get('products',[])}
 print(f'Official snapshot {month}; {len(products)} product records',flush=True)
 if args.catalog_only:
  print(json.dumps({'month':month,'url':url,'products':len(products),'presentations':len(rows)},indent=2));return
 errors=[]
 def one(p):
  try:
   label=fetch_label(p,old.get(p['id'],{}),sources,args.force)
   p['labels']=[label] if label else [];p['parserVersion']=PARSER_VERSION;p['piCheckedAt']=stamp
   if not label:p['issues']=['신규 허가: 공식 PI 미확보. 후속 확인 필요.']
   print(p['brand']+(' ✓' if label else ' PI pending'),flush=True)
  except Exception as e:errors.append({'product':p['id'],'error':str(e)});print(p['brand']+' ERROR '+str(e),flush=True)
  return p
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:products=list(pool.map(one,products))
 # Optional FDA-letter evidence must not make a PI collection failure disappear.
 if not errors:
  from approval_letters import enrich_products
  cachepath=ROOT/'data/approval-letter-cache.json'
  cache=json.loads(cachepath.read_text()) if cachepath.exists() else {}
  for p in products:
   if old.get(p['id'],{}).get('approvalLetter'):p['approvalLetter']=copy.deepcopy(old[p['id']]['approvalLetter'])
  letter_report=enrich_products(products,sources,cache,args.force)
  if not args.check_only:
   atomic_json(cachepath,cache);atomic_json(ROOT/'reports/approval-letters.json',letter_report)
 payload={'schemaVersion':2,'purpleBookDate':month,'purpleBookAsOf':f'{month}-{calendar.monthrange(int(month[:4]),int(month[5:]))[1]:02d}','retrievedAt':stamp,'purpleBookUrl':url,'purpleBookHash':hashlib.sha256(raw).hexdigest(),'products':products}
 if errors:
  atomic_json(ROOT/'reports/refresh-errors.json',{'checkedAt':stamp,'errors':errors});raise CollectionError(f'{len(errors)} source errors; published data unchanged')
 validate(payload,previous);delta=changes(previous,payload)
 if args.check_only:print('Validation passed; no published files changed',flush=True);return
 history=out/'history';history.mkdir(exist_ok=True)
 index=json.loads((history/'index.json').read_text()) if (history/'index.json').exists() else []
 if previous and not index:
  atomic_json(history/'baseline.json',previous);index.append({'id':'baseline','path':'history/baseline.json','checkedAt':previous['retrievedAt'],'purpleBookDate':previous['purpleBookDate'],'changes':{'added':[],'removed':[],'changed':[]},'baseline':True})
 revision=now.strftime('%Y%m%dT%H%M%SZ');payload['revision']=revision
 atomic_json(history/(revision+'.json'),payload)
 index.insert(0,{'id':revision,'path':'history/'+revision+'.json','checkedAt':stamp,'purpleBookDate':month,'productCount':len(products),'changes':delta})
 atomic_json(history/'index.json',index)
 atomic_json(out/'data.json',payload) # last write: all validation completed
 rawdir=ROOT/'data/sources';rawdir.mkdir(exist_ok=True);(rawdir/(month+'.csv')).write_bytes(raw)
 atomic_json(ROOT/'reports/latest-refresh.json',{'checkedAt':stamp,'snapshot':month,'products':len(products),'piObtained':sum(bool(p['labels']) for p in products),'changes':delta})
 print(f'Published snapshot: {len(delta["added"])} added, {len(delta["removed"])} removed, {len(delta["changed"])} changed',flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT/'dist'));ap.add_argument('--force',action='store_true');ap.add_argument('--check-only',action='store_true');ap.add_argument('--catalog-only',action='store_true');ap.add_argument('--workers',type=int,default=6)
 args=ap.parse_args()
 try:refresh(args)
 except Exception as e:print('REFRESH FAILED: '+str(e),file=sys.stderr);sys.exit(1)
